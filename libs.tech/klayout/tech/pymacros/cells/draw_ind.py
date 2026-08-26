"""
Geometry generator for the planar inductors of the UCI/INRF IGZO TFT process.

Two topologies, because they are electrically different animals:

  series   one spiral of n turns - the usual planar inductor.  The inner end
           has to get out, and it does so on the other metal, through two
           openings in the dielectric.  That is only possible because the gate
           is deposited after the etch, so an opening under gate metal is a
           via.
  parallel n concentric open rings sharing two buses.  All the rings are cut
           at the same angle and the buses run through that slot, so nothing
           crosses anything and no via is needed.

Both are drawn as pya.Path, so the drawn length is exact and can be measured
back out - which is what the resistance is computed from, rather than from a
closed-form guess at the length.

Coordinates are micrometres and the centre of the coil is the origin.  A
spiral brings its outer end out to the right and its inner end out to the left,
on the other metal; the rings bring both buses out to the right.
"""

import math

import pya

from .draw_tft import grid
from .layers import (GATE, GATE_PIN, OXETCH, SD, SD_PIN, TEXT,
                     layer)


def _path(cell, li, points_um, width_um):
    """
    Insert one path given in micrometres, snapped to the grid.

    The path goes in as a polygon rather than as a pya.Path because a path's
    mitred corners are computed, not given: on a curve they land wherever the
    arithmetic puts them, off the grid, and magic then rescales the whole cell
    when it reads the GDS and gets its capacitances wrong.  Snapping the
    rendered outline costs at most half a grid step - 10 nm, a five-hundredth
    of the smallest feature this process can print.
    """
    dbu = cell.layout().dbu
    g = int(round(GRID_UM / dbu))
    pts = [pya.Point(int(round(x / dbu)), int(round(y / dbu)))
           for x, y in points_um]
    path = pya.Path(pts, int(round(width_um / dbu)))
    region = pya.Region(path.polygon()).snapped(g, g)
    cell.shapes(layer(cell.layout(), li)).insert(region)
    return path


def _box(cell, li, x1, y1, x2, y2):
    dbu = cell.layout().dbu
    cell.shapes(layer(cell.layout(), li)).insert(
        pya.Box(int(round(x1 / dbu)), int(round(y1 / dbu)),
                int(round(x2 / dbu)), int(round(y2 / dbu))))


# A polygon drawn through points on a circle runs inside the curve between its
# vertices, and the outer of two neighbouring turns cuts the corner by more
# than the inner one - so the gap between them comes out a few nanometres short
# of what was asked for, and a spacing rule is exact.  Everything circular is
# drawn on this slightly opened-up pitch.  The 20 nm on the end is three orders
# of magnitude below anything this process can print - the smallest feature the
# process has been shown to make is 5 um, and 50 nm is 1/100 of that.
CIRCULAR_STEP_DEG = 2.0
CIRCULAR_ALLOWANCE = 0.1           # um


def circular_pitch(w, gap, step_deg=CIRCULAR_STEP_DEG):
    """Track pitch to draw with, so that the drawn gap is never less than gap."""
    return (w + gap) / math.cos(math.radians(step_deg) / 2.0) + CIRCULAR_ALLOWANCE


def path_length(points_um):
    """Length of a polyline in micrometres."""
    return sum(math.hypot(points_um[i + 1][0] - points_um[i][0],
                          points_um[i + 1][1] - points_um[i][1])
               for i in range(len(points_um) - 1))


def _snap(x, y):
    """A point on magic's grid.  See the note on grid() in draw_tft.py."""
    return (round(x / GRID_UM) * GRID_UM, round(y / GRID_UM) * GRID_UM)


GRID_UM = 0.02


def square_spiral(d_in, w, gap, n):
    """
    Centreline of a square spiral, from the inner end outwards.

    The inner end starts on the -x side and the spiral ends on the +x side, so
    the two terminals leave the coil from opposite quadrants and the underpass
    never has to pass beneath its own outer lead.
    """
    pitch = w + gap
    a = d_in / 2.0 + w / 2.0          # centreline of the innermost track
    pts = [(-a, 0.0)]
    for k in range(int(n)):
        r = a + k * pitch             # this turn
        r_next = a + (k + 1) * pitch  # the next one, stepped out on the top
        pts.append((-r, -r))          # down the left wall
        pts.append((r, -r))           # across the bottom
        pts.append((r, r))            # up the right wall
        pts.append((-r_next, r))      # across the top, stepping out
    # the last "step out" leaves us on the left again: bring the outer end
    # round to the +x side so both terminals face the same way
    r_last = a + int(n) * pitch
    pts.append((-r_last, -r_last))
    pts.append((r_last, -r_last))
    pts.append((r_last, 0.0))
    return pts


def circular_spiral(d_in, w, gap, n, step_deg=2.0):
    """
    Centreline of an Archimedean spiral, sampled every step_deg.

    Same convention as the square one: inner end at angle 180 degrees, outer
    end brought round to 0 degrees.

    The pitch is opened up by 1/cos(step/2).  A polygon drawn through points on
    a spiral runs inside the curve between its vertices, and the outer turn
    cuts the corner by more than the inner one because its radius is larger -
    so the gap between two turns comes out a few tens of nanometres short of
    what was asked for, and every one of those is a spacing violation.  The
    allowance is well under a rounding error of the geometry and is folded into
    the value the physics is given, so the drawn coil and the estimated coil
    stay the same coil.
    """
    pitch = circular_pitch(w, gap, step_deg)
    a = d_in / 2.0 + w / 2.0
    pts = []
    theta = math.pi                                  # start on the -x side
    # n turns plus a closing half turn, so the outer end finishes on the +x
    # side - the same closing the square spiral does.  Without it the spiral
    # ends where it started and the outer lead is drawn back across the coil.
    theta_end = math.pi + 2.0 * math.pi * float(n) + math.pi
    step = math.radians(step_deg)
    while theta < theta_end:
        r = a + pitch * (theta - math.pi) / (2.0 * math.pi)
        pts.append(_snap(r * math.cos(theta), r * math.sin(theta)))
        theta += step
    r = a + pitch * (theta_end - math.pi) / (2.0 * math.pi)
    pts.append(_snap(r * math.cos(theta_end), r * math.sin(theta_end)))
    return pts


def spiral_with_leads(d_in, w, gap, n, shape="square", lead=40.0):
    """
    The full centreline of a spiral: the turns, the run in to the centre, and
    the run out past the edge.  One function, used both to draw the coil and to
    work out its resistance, so the two cannot disagree about how much metal
    there is.
    """
    pts = (square_spiral(d_in, w, gap, n) if shape == "square"
           else circular_spiral(d_in, w, gap, n))
    return pts + [(pts[-1][0] + lead, pts[-1][1])]


def _pin(cell, on_gate, name, x, y, size):
    """A pin box and its label, on the coil's own metal."""
    li = GATE_PIN if on_gate else SD_PIN
    size = grid(size)
    _box(cell, li, x - size / 2.0, y - size / 2.0, x + size / 2.0, y + size / 2.0)
    dbu = cell.layout().dbu
    t = pya.Text(name, pya.Trans(int(round(x / dbu)), int(round(y / dbu))))
    t.size = int(round(size / dbu))
    cell.shapes(layer(cell.layout(), li)).insert(t)


def draw_spiral(cell, d_in=100.0, w=10.0, gap=5.0, n=8, shape="square",
                on_gate=True, lead=40.0, via=20.0, via_enc=5.0,
                pad=False, pad_size=200.0, lbl=True, value_text=None):
    pad_probe = pad
    """
    One spiral, plus the underpass that brings the inner end out.

    Returns the centreline points - including the two leads, which are as much
    of the coil's resistance as the turns are - so the caller can measure the
    length it actually drew.
    """
    coil_layer = GATE if on_gate else SD
    under_layer = SD if on_gate else GATE

    # The inner end runs on to the centre of the coil and the outer end runs on
    # past the edge, both as part of the same path: two paths butted end to end
    # leave a notch at the join, and a notch is a width violation.
    pts = spiral_with_leads(d_in, w, gap, n, shape, lead)
    x_out = pts[-2][0]
    _path(cell, coil_layer, pts, w)

    # The inner terminal drops onto the other metal at the inner end of the
    # first turn and runs out underneath the coil.  Its pad extends inwards,
    # into the empty middle, and never towards the second turn.
    #
    # Note what is NOT done here: a lead on the coil's own metal running from
    # the inner end to the centre.  It would be the obvious thing to draw, and
    # it pinches against the first turn where the two run tangentially - a slot
    # that narrows to nothing and cannot be etched.  Dropping to the other
    # metal immediately avoids the geometry rather than arguing with it.
    via_w = max(via, w)
    pad = via_w / 2.0 + via_enc
    via_in = max(5.0, min(via, w / 2.0))
    pad_in = via_in / 2.0 + via_enc
    x_in = pts[0][0] + pad_in              # pad centre, shifted inwards
    x_exit = -(x_out + lead)

    # Where the outer terminal ends up.  With a probe pad it is the middle of
    # that pad, not its edge: a via sitting on the boundary of the metal it
    # contacts looks marginal and is marginal - half of any misalignment takes
    # contact area away.  In the middle it is surrounded by pad on every side.
    if pad_probe:
        x_out_via = x_exit - pad_size / 2.0 + w
        via_out = min(max(via, w), pad_size / 2.0)
    else:
        x_out_via = x_exit
        via_out = max(via, w)
    pad_out = via_out / 2.0 + via_enc

    # The underpass runs from the inner end all the way to that via.
    _box(cell, under_layer, min(x_out_via - pad_out, x_exit - pad_out), -pad_out,
         x_in + pad_in, pad_out)
    for x, vw, enc in ((x_in, via_in, pad_in), (x_out_via, via_out, pad_out)):
        _box(cell, coil_layer, x - enc, -enc, x + enc, enc)
        _box(cell, OXETCH, x - vw / 2.0, -vw / 2.0, x + vw / 2.0, vw / 2.0)

    # --- probe pads ---------------------------------------------------------
    # Each pad swallows the track that feeds it: the outer lead runs on to the
    # middle of its pad instead of stopping at the edge.  A 10 um trace butting
    # against a 200 um pad is a connection you have to squint at; a trace that
    # crosses it is one you cannot mistake.
    if pad_probe:
        half_p = pad_size / 2.0
        x_a = x_out + lead - w
        _box(cell, coil_layer, x_a, -half_p, x_a + pad_size, half_p)
        _path(cell, coil_layer, [(x_out, 0.0), (x_a + half_p, 0.0)], w)
        x_b = x_exit + w
        _box(cell, coil_layer, x_b - pad_size, -half_p, x_b, half_p)

    # Terminals.  Without these the extracted coil has no named nodes, and
    # neither LVS nor a resistance extraction has anything to report.
    if lbl:
        size = grid(min(w, 2.0 * pad_out))
        x_a = x_out + lead + (pad_size / 2.0 - w if pad_probe else -w)
        x_b = x_exit - (pad_size / 2.0 - w if pad_probe else 0.0)
        _pin(cell, on_gate, "A", x_a, 0.0, size)
        _pin(cell, on_gate, "B", x_b, 0.0, size)

    if value_text:
        # below the coil: the middle is taken by the via
        y_txt = -grid(abs(min(p[1] for p in pts)) + 3.0 * w)
        _text(cell, value_text, 0.0, y_txt, grid(max(4.0, d_in / 8.0)))
    return pts


def ring_centrelines(d_in, w, gap, n, shape="square", slot=None):
    """
    Centrelines of n concentric open rings, each ending on the two buses.

    Every ring lands on its bus through a short straight stub at right angles
    to it.  A circular ring that simply stops where its arc crosses the bus
    meets it almost tangentially, and the sliver between the two is both a
    width and a spacing violation - the stub costs a couple of track widths and
    removes the whole class of problem.
    """
    steps = 144
    pitch = (w + gap if shape == "square"
             else circular_pitch(w, gap, 360.0 / steps))
    a = d_in / 2.0 + w / 2.0
    if slot is None:
        slot = w + 2.0 * gap
    out = []
    for k in range(int(n)):
        r = a + k * pitch
        if shape == "square":
            out.append([(r, slot), (r, r), (-r, r), (-r, -r), (r, -r),
                        (r, -slot)])
        else:
            sin_th = min(0.95, (slot + 2.0 * w) / r)
            th0 = math.asin(sin_th)
            x0 = r * math.cos(th0)
            span = 2.0 * math.pi - 2.0 * th0
            arc = [_snap(r * math.cos(th0 + span * i / steps),
                         r * math.sin(th0 + span * i / steps))
                   for i in range(steps + 1)]
            x0 = round(x0 / GRID_UM) * GRID_UM
            out.append([(x0, slot)] + arc + [(x0, -slot)])
    return out


def draw_rings(cell, d_in=100.0, w=10.0, gap=5.0, n=8, shape="square",
               on_gate=True, lead=40.0, slot=None, pad=False, pad_size=200.0,
               lbl=True, value_text=None):
    """
    n concentric open rings on one metal, tied to two buses.

    Every ring is cut at the same angle and the two buses run through that
    slot, one to each side, so a ring's ends reach a bus without crossing any
    other ring.  This is why the parallel topology needs no via.

    Returns the list of centrelines, one per ring.
    """
    coil_layer = GATE if on_gate else SD
    pitch = w + gap
    a = d_in / 2.0 + w / 2.0
    if slot is None:
        slot = w + 2.0 * gap          # half-height of the bus channel

    rings = ring_centrelines(d_in, w, gap, n, shape, slot)
    for pts in rings:
        _path(cell, coil_layer, pts, w)

    # The two buses, running out through the slot.  They start half a track
    # width inside the innermost stub - not at the origin, which would add a
    # spur into the empty middle that connects nothing, and not at the
    # innermost radius either: a circular ring's stub stands further in than
    # its radius, so a bus starting at the radius misses the inner ring
    # altogether and leaves it floating.  That is exactly what happened here
    # before, and it is why the cells now get a connectivity check.
    x_start = min(pts[0][0] for pts in rings) - w / 2.0
    x_end = max(max(x for x, _ in pts) for pts in rings) + lead
    _path(cell, coil_layer, [(x_start, slot), (x_end, slot)], w)
    _path(cell, coil_layer, [(x_start, -slot), (x_end, -slot)], w)

    # A pad on the end of each bus.  They are offset outwards from the slot so
    # that two pads of any size do not run into each other.
    if pad:
        half_p = pad_size / 2.0
        x_pad_l = x_end - w
        x_pad_c = x_pad_l + half_p
        for sign in (1.0, -1.0):
            y_c = sign * (slot + half_p - w / 2.0)
            _box(cell, coil_layer, x_pad_l, y_c - half_p,
                 x_pad_l + pad_size, y_c + half_p)
            # The bus runs on to the middle of its pad and the jog to the pad
            # centre stands there, inside the metal.  A bus that stops at the
            # pad's edge and turns is a connection made at a boundary: it is
            # the one place where a misalignment takes contact away instead of
            # just moving it.
            _path(cell, coil_layer, [(x_start, sign * slot),
                                     (x_pad_c, sign * slot)], w)
            _box(cell, coil_layer, x_pad_c - w / 2.0,
                 min(y_c, sign * slot) - w / 2.0, x_pad_c + w / 2.0,
                 max(y_c, sign * slot) + w / 2.0)

    if lbl:
        size = grid(min(w, 20.0))
        for name, sign in (("A", 1.0), ("B", -1.0)):
            if pad:
                y_c = sign * (slot + pad_size / 2.0 - w / 2.0)
                _pin(cell, on_gate, name, x_end - w + pad_size / 2.0, y_c, size)
            else:
                _pin(cell, on_gate, name, x_end - w, sign * slot, size)

    if value_text:
        y_txt = -grid(a + int(n) * pitch + 3.0 * w)
        _text(cell, value_text, 0.0, y_txt, grid(max(4.0, d_in / 8.0)))
    return rings


def _text(cell, text, x, y, size):
    dbu = cell.layout().dbu
    t = pya.Text(text, pya.Trans(int(round(x / dbu)), int(round(y / dbu))))
    t.size = int(round(size / dbu))
    cell.shapes(layer(cell.layout(), TEXT)).insert(t)
