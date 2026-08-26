"""
Geometry generator for the UCI/INRF IGZO TFT.

TOP-GATE COPLANAR device.  Four masks, in the order the process runs them:
IGZO island (4/0), Au source/drain on top of it (6/0), openings in the blanket
50 nm Al2O3 (5/0), Au gate last (2/0).

Everything here reproduces what is drawn in TFT/TFT_layout.GDS.  Read out of
cell TFT-10L100W (dbu = 1 nm), with the origin moved to the centre of the
channel:

    layer 6 (S/D)  x [ l/2, l/2 + sd_len ]     y [ -w/2, w/2 ]   drain
    layer 6 (S/D)  x [ -l/2 - sd_len, -l/2 ]   y [ -w/2, w/2 ]   source
    layer 4 (IGZO) x [ -l/2 - ext_x, l/2 + ext_x ]
                   y [ -w/2 - ext_y, w/2 + ext_y ]               island
    layer 2 (gate) x [ -l/2 - ov, l/2 + ov ]                     gate stripe
    layer 6 / 2    400 x 400 um probe pads
    layer 5 (etch) 360 x 360 um window inside each S/D pad (20 um inset),
                   which is how a probe reaches the Au through the dielectric;
                   the gate pad is above the dielectric and needs none

so for the fabricated device (l = 10, w = 100, ov = 5, ext_x = 10, ext_y = 5,
sd_len = 97.5) the numbers come back out as the GDS has them.

The channel length is the *drawn* gap between the source and drain electrodes.
The process prints it about 3 um wider (l_bias); that bias is reported, never
applied to the geometry - the PCell writes a mask, and the mask is what is
drawn.  See docs/PDK_GUIDE.md section 8.
"""

import pya

from .layers import (GATE, GATE_PIN, IGZO, OXETCH, SD, SD_PIN, TEXT,
                     layer)


# Magic's internal grid is 10 nm.  Anything that lands off it makes magic
# rescale the whole cell (magscale 1 10) when it reads the GDS, and after that
# the extracted capacitances are wrong - quietly, with no warning.  Sizes that
# come out of a division go through here first.
GRID = 0.02          # um


def grid(value, g=GRID):
    """Snap a length to the grid, keeping it positive."""
    return max(g, round(value / g) * g)


def _box(cell, li, x1, y1, x2, y2):
    """Insert a box given in micrometres."""
    dbu = cell.layout().dbu
    cell.shapes(layer(cell.layout(), li)).insert(
        pya.Box(
            int(round(x1 / dbu)),
            int(round(y1 / dbu)),
            int(round(x2 / dbu)),
            int(round(y2 / dbu)),
        )
    )


def _text(cell, li, text, x, y, size):
    dbu = cell.layout().dbu
    trans = pya.Trans(int(round(x / dbu)), int(round(y / dbu)))
    t = pya.Text(text, trans)
    t.size = int(round(size / dbu))
    cell.shapes(layer(cell.layout(), li)).insert(t)


def draw_tft(
    cell,
    w_gate=100.0,
    l_gate=10.0,
    nf=1,
    gate_ov=5.0,
    sd_len=97.5,
    igzo_ext_x=10.0,
    igzo_ext_y=5.0,
    gate_ext_y=10.0,
    pad=False,
    pad_size=400.0,
    pad_gap=325.0,
    etch_inset=20.0,
    s_strap_w=0.0,
    d_strap_w=0.0,
    strap_gap=10.0,
    lbl=False,
):
    """
    Draw one IGZO TFT into `cell`.

    nf fingers share their electrodes: nf channels need nf + 1 electrodes, so
    the total width is nf * w_gate while the area grows far more slowly.  Note
    that fingering this device does not change fT - it was measured, and gm and
    Cgs both split with W (docs/PDK_GUIDE.md, model file header).  Fingers buy
    gate resistance and aspect ratio, nothing else.
    """
    nf = max(1, int(nf))
    half_w = w_gate / 2.0
    pitch = l_gate + sd_len

    # --- source/drain electrodes -------------------------------------------
    # Electrode i spans [x_i, x_i + sd_len]; channel i is the gap that follows.
    x0 = -(nf * pitch + sd_len) / 2.0
    electrodes = []
    for i in range(nf + 1):
        xa = x0 + i * pitch
        electrodes.append((xa, xa + sd_len))
        _box(cell, SD, xa, -half_w, xa + sd_len, half_w)

    # --- IGZO island --------------------------------------------------------
    # One island covering every channel, overlapping the outer electrodes by
    # igzo_ext_x and overhanging the electrode ends by igzo_ext_y.
    isl_x1 = electrodes[0][1] - igzo_ext_x
    isl_x2 = electrodes[-1][0] + igzo_ext_x
    _box(cell, IGZO, isl_x1, -half_w - igzo_ext_y, isl_x2, half_w + igzo_ext_y)

    # --- gate ---------------------------------------------------------------
    # One stripe per channel, overlapping both electrodes by gate_ov.  Several
    # fingers are tied together by a bus at each end of the array.
    gate_y1 = -half_w - igzo_ext_y - gate_ext_y
    gate_y2 = half_w + igzo_ext_y + gate_ext_y
    for i in range(nf):
        xc = electrodes[i][1] + l_gate / 2.0
        _box(cell, GATE, xc - l_gate / 2.0 - gate_ov, gate_y1,
             xc + l_gate / 2.0 + gate_ov, gate_y2)
    bus_x1 = electrodes[0][1] - gate_ov
    bus_x2 = electrodes[-1][0] + gate_ov
    bus_y1, bus_y2 = gate_y1, gate_y2
    if nf > 1:
        bus_y1 = gate_y1 - gate_ext_y
        bus_y2 = gate_y2 + gate_ext_y
        _box(cell, GATE, bus_x1, bus_y1, bus_x2, gate_y1)
        _box(cell, GATE, bus_x1, gate_y2, bus_x2, bus_y2)

    # --- source and drain straps --------------------------------------------
    # Fingers share electrodes, so the electrodes alternate: even ones are
    # source, odd ones drain.  Left unconnected they are nf+1 separate
    # terminals; the straps are what make them two.
    #
    # Each strap runs outside the gate, on the S/D metal, and the electrodes it
    # serves are extended to reach it.  Their widths are separate parameters
    # because the two sides rarely carry the same current: in a common-source
    # stage the source strap carries every finger's current and the drain strap
    # carries it back out, but in a differential pair the source side is the
    # tail and wants to be much wider.  Zero on either one leaves that side
    # unstrapped, which is what a single-finger device wants.
    #
    # THE SOURCE SIDE CROSSES THE GATE BUS.  With more than one finger the gate
    # stripes have to be tied together too, and its bus runs along the bottom -
    # the same side the source strap leaves from.  The two are on different
    # metals with the dielectric between them, so it is a capacitance, not a
    # short: about Cox * (electrode width) * (bus width) per source electrode.
    # The drain side, at the top, crosses nothing.
    strap_y_s = bus_y1 - strap_gap - s_strap_w / 2.0
    strap_y_d = bus_y2 + strap_gap + d_strap_w / 2.0
    if s_strap_w > 0.0:
        for i in range(0, len(electrodes), 2):
            xa, xb = electrodes[i]
            _box(cell, SD, xa, strap_y_s, xb, -half_w)
        _box(cell, SD, electrodes[0][0], strap_y_s - s_strap_w / 2.0,
             electrodes[-1 if len(electrodes) % 2 else -2][1],
             strap_y_s + s_strap_w / 2.0)
    if d_strap_w > 0.0 and len(electrodes) > 1:
        for i in range(1, len(electrodes), 2):
            xa, xb = electrodes[i]
            _box(cell, SD, xa, half_w, xb, strap_y_d)
        _box(cell, SD, electrodes[1][0], strap_y_d - d_strap_w / 2.0,
             electrodes[-1 if len(electrodes) % 2 == 0 else -2][1],
             strap_y_d + d_strap_w / 2.0)

    # --- probe pads ---------------------------------------------------------
    # 400 x 400 um, placed as on the test chip: the source and drain pads butt
    # against the outer electrodes, and the gate pad sits clear above them,
    # reached by running the gate stripe up past the S/D pads (pad_gap).  The
    # gate must not run alongside a S/D pad - the two would face each other
    # across 50 nm of Al2O3 and add a large parasitic.
    #
    # Each S/D pad gets a window in the gate dielectric, inset by etch_inset
    # per side (400 x 400 um pad, 360 x 360 um opening on the test chip), so a
    # probe can land on the Au.  The gate pad is above the dielectric already.
    if pad:
        half_p = pad_size / 2.0
        s_pad = (electrodes[0][0] - pad_size, electrodes[0][0])
        d_pad = (electrodes[-1][1], electrodes[-1][1] + pad_size)
        for x1, x2 in (s_pad, d_pad):
            _box(cell, SD, x1, -half_p, x2, half_p)
            _box(cell, OXETCH, x1 + etch_inset, -half_p + etch_inset,
                 x2 - etch_inset, half_p - etch_inset)
        route_w = min(pad_size, max(l_gate + 2 * gate_ov, bus_x2 - bus_x1))
        pad_y1 = half_p + pad_gap
        _box(cell, GATE, -route_w / 2.0, bus_y2, route_w / 2.0, pad_y1)
        _box(cell, GATE, -half_p, pad_y1, half_p, pad_y1 + pad_size)

    # --- pins and labels ----------------------------------------------------
    if lbl:
        s_x = (electrodes[0][0] + electrodes[0][1]) / 2.0
        d_x = (electrodes[-1][0] + electrodes[-1][1]) / 2.0
        g_x = 0.0
        size = grid(max(1.0, min(w_gate, sd_len) / 10.0))
        # The text goes on the pin purpose, not the label purpose: that is
        # what magic's cifinput turns into a port (`labels SDPIN port`), and
        # what KLayout's netlist extraction reads as the net name.
        for name, x, li_pin, y in (
            ("S", s_x, SD_PIN, 0.0),
            ("D", d_x, SD_PIN, 0.0),
            ("G", g_x, GATE_PIN, bus_y2 - gate_ext_y / 2.0),
        ):
            _box(cell, li_pin, x - size / 2.0, y - size / 2.0,
                 x + size / 2.0, y + size / 2.0)
            _text(cell, li_pin, name, x, y, size)

    return cell


def stamp(cell, text, x, y, size):
    """
    Write a value onto the cell, the way a foundry cell carries its own name.

    Layer 63/0 is annotation only - it is not a mask and is never fabricated.
    The point is that a layout opened six months from now says what it is
    without anyone having to reopen the parameter dialog.
    """
    _text(cell, TEXT, text, x, y, size)


def draw_cap_mim(cell, w=400.0, l=400.0, ext_sd=200.0, ext_gate=200.0,
                 ext_sd_far=0.0, ext_gate_far=0.0, etch_inset=20.0,
                 pad=False, pad_size=400.0, lbl=False, value_text=None):
    """
    Overlap capacitor: source/drain Au below, blanket 50 nm Al2O3, gate Au on
    top.  The capacitance is the crossing area, w * l.

    This reproduces Test_capacitance on the test chip, where a gate stripe
    (2/0, 400 um tall) crosses three S/D plates (6/0) of 400, 800 and 1200 um.
    The 400 x 400 um crossing measured 250.2 pF, which is where
    Cox = 156.4 nF/cm^2 = 1.564 fF/um^2 comes from - the one number in this PDK
    that is a direct capacitance measurement.

    Each plate runs past the crossing on its terminal side by ext_*, and can
    also run past it on the far side by ext_*_far.  The two metals get their
    own numbers because they are not the same conductor and rarely want the
    same shape: the S/D plate usually reaches down to whatever it connects to,
    while the gate plate reaches sideways.  A far-side extension is there for
    when the plate has to be caught from both ends - a tank capacitor sitting
    between two nodes, for instance - and it costs nothing but area when it is
    zero, which is the default.

    The dielectric is opened over the S/D plate's terminal tail: that metal is
    under the blanket film, and without a window nothing can touch it.  The
    gate plate is on top of the film and needs none.
    """
    half_w, half_l = w / 2.0, l / 2.0
    # Lower plate: S/D metal, running down to its terminal and optionally up.
    sd_bot = -half_l - ext_sd
    sd_top = half_l + ext_sd_far
    _box(cell, SD, -half_w, sd_bot, half_w, sd_top)
    # Upper plate: gate metal, running right to its terminal and optionally left.
    g_left = -half_w - ext_gate_far
    g_right = half_w + ext_gate
    _box(cell, GATE, g_left, -half_l, g_right, half_l)

    # Window in the gate dielectric over the lower plate's tail.
    if ext_sd > 2.0 * etch_inset:
        _box(cell, OXETCH, -half_w + etch_inset, sd_bot + etch_inset,
             half_w - etch_inset, -half_l - etch_inset)

    # --- probe pads ---------------------------------------------------------
    if pad:
        half_p = pad_size / 2.0
        # S/D pad hangs below the lower plate, with its own window.
        pad_top, pad_bot = sd_bot, sd_bot - pad_size
        _box(cell, SD, -half_p, pad_bot, half_p, pad_top)
        # The window belongs inside the pad that was just drawn - taking
        # pad_size off sd_bot first and then again here put it a whole pad
        # below the metal, opening the dielectric onto nothing.
        _box(cell, OXETCH, -half_p + etch_inset, pad_bot + etch_inset,
             half_p - etch_inset, pad_top - etch_inset)
        sd_bot = pad_bot
        # Gate pad sits beyond the upper plate; it is above the dielectric.
        _box(cell, GATE, g_right, -half_p, g_right + pad_size, half_p)
        g_right += pad_size

    if value_text:
        stamp(cell, value_text, 0.0, 0.0, grid(max(2.0, min(w, l) / 12.0)))
    if lbl:
        size = grid(max(1.0, min(w, l) / 20.0))
        # Inside the metal, not past the end of it: a pin outside the shape it
        # names attaches to nothing, and the extracted net comes out unnamed.
        y_lo = sd_bot + (pad_size / 2.0 if pad else max(ext_sd, size) / 2.0)
        _box(cell, SD_PIN, -size / 2.0, y_lo - size / 2.0,
             size / 2.0, y_lo + size / 2.0)
        _text(cell, SD_PIN, "MINUS", 0.0, y_lo, size)
        x_hi = g_right - (pad_size / 2.0 if pad else max(ext_gate, size) / 2.0)
        _box(cell, GATE_PIN, x_hi - size / 2.0, -size / 2.0,
             x_hi + size / 2.0, size / 2.0)
        _text(cell, GATE_PIN, "PLUS", x_hi, 0.0, size)
    return cell
