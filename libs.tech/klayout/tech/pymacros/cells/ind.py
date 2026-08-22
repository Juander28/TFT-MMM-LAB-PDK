"""
Planar inductor PCell for the UCI/INRF IGZO TFT process.

The physics is not reimplemented here.  It comes from tools/coil_core.py, the
library written for the coil calculator - Mohan-Wheeler and Greenhouse for the
spiral, Neumann via elliptic integrals for the mutually coupled rings, and the
usual skin-effect resistance.  One copy, used by both the calculator and the
PCell, so the two can never disagree.

WHAT THESE NUMBERS ARE WORTH.  L comes from a closed-form fit, R from the
length actually drawn and the resistivity of gold.  Neither has been measured
on this process, and the metal thickness - the term R depends on most - is an
assumption until somebody measures it.  At the 50 nm the models assume, an
8-turn 100 um coil comes out at Q = 0.03 at 100 MHz: drawable, estimable, and
useless as a tank element until the gold is much thicker.  The cell reports
that rather than hiding it.

ONE KNOWN DRC RESIDUAL.  The circular series coil leaves seven violations at
its inner terminal - five spacing, two width, all between 2.5 and 4.8 um
against a 5 um rule.  A circular turn and the pad that takes its inner end
away meet almost tangentially, and the slot between them narrows to nothing
however the pad is shaped; it is a property of a curve meeting a straight
edge, not of this particular drawing.  The square coil does not have it, and
neither do the parallel rings.  If you need a circular coil, either open the
gap up or accept the pinch and say so on the mask release.  Everything else in
this library is DRC clean.
"""

import math
import os
import sys

import pya

from .draw_ind import (circular_pitch, draw_rings, draw_spiral, path_length,
                       ring_centrelines, spiral_with_leads)

# tools/ sits at the root of the PDK, five levels up from this file.
_TOOLS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                       "..", "..", "..", "..", "..", "tools"))
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

try:
    import coil_core
    PHYSICS_ERROR = None
except Exception as exc:                    # numpy or scipy missing
    coil_core = None
    PHYSICS_ERROR = str(exc)

# Gold.  coil_core carries the resistivities; this is the one we use.
RHO_AU = 2.44e-8                            # Ohm*m

IND_D_IN = 100.0
IND_W = 10.0
IND_GAP = 5.0
IND_N = 8
IND_T = 0.05                                # um - ASSUMED, not measured
IND_FREQ = 100.0                            # MHz


def _format_l(l_h):
    """Engineering notation for an inductance in henries."""
    for scale, unit in ((1e-6, "uH"), (1e-9, "nH"), (1e-12, "pH")):
        if abs(l_h) >= 0.9995 * scale:
            return "%.4g%s" % (l_h / scale, unit)
    return "%.3gpH" % (l_h / 1e-12)


def _format_r(r_ohm):
    if r_ohm >= 1e3:
        return "%.4gkOhm" % (r_ohm / 1e3)
    return "%.4gOhm" % r_ohm


class ind_igzo(pya.PCellDeclarationHelper):
    """Planar inductor: square or circular, one spiral or n rings in parallel."""

    def __init__(self):
        super(ind_igzo, self).__init__()

        self.shape_handle = self.param("shape", self.TypeList, "Shape",
                               default="square")
        self.shape_handle.add_choice("square", "square")
        self.shape_handle.add_choice("circular", "circular")

        self.topo_handle = self.param("topology", self.TypeList, "Topology",
                              default="series")
        self.topo_handle.add_choice("series spiral", "series")
        self.topo_handle.add_choice("parallel rings", "parallel")

        self.param("n", self.TypeInt, "Turns (series) or rings (parallel)",
                   default=IND_N)
        self.param("d_in", self.TypeDouble, "Inner diameter",
                   default=IND_D_IN, unit="um")
        self.param("w", self.TypeDouble, "Track width",
                   default=IND_W, unit="um")
        self.param("gap", self.TypeDouble, "Gap between tracks",
                   default=IND_GAP, unit="um")

        self.metal_handle = self.param("metal", self.TypeList, "Metal",
                               default="gate")
        self.metal_handle.add_choice("gate (2/0)", "gate")
        self.metal_handle.add_choice("source/drain (6/0)", "sd")

        self.param("t_metal", self.TypeDouble, "Metal thickness (ASSUMED)",
                   default=IND_T, unit="um")
        self.param("f_eval", self.TypeDouble, "Frequency for R_ac and Q",
                   default=IND_FREQ, unit="MHz")
        self.param("lead", self.TypeDouble, "Terminal lead length",
                   default=40.0, unit="um")
        self.param("show_value", self.TypeBoolean, "Print the value on the cell",
                   default=True)

        self.param("l_series", self.TypeDouble, "Series inductance",
                   default=0.0, unit="nH", readonly=True)
        self.param("r_dc", self.TypeDouble, "Series resistance (DC)",
                   default=0.0, unit="Ohm", readonly=True)
        self.param("r_ac", self.TypeDouble, "Series resistance at f_eval",
                   default=0.0, unit="Ohm", readonly=True)
        self.param("q", self.TypeDouble, "Q at f_eval",
                   default=0.0, readonly=True)
        self.param("d_out", self.TypeDouble, "Outer diameter",
                   default=0.0, unit="um", readonly=True)
        self.param("wire_len", self.TypeDouble, "Drawn track length",
                   default=0.0, unit="um", readonly=True)

    def display_text_impl(self):
        return "ind_igzo(%s,%s,n=%d,%s)" % (
            self.shape, self.topology, self.n, _format_l(self.l_series * 1e-9))

    # ------------------------------------------------------------------ maths
    def _estimate(self):
        """
        Fill in the read-only outputs.

        Length comes from the geometry that is actually drawn, not from a
        closed-form approximation of it - the drawn spiral carries a closing
        half turn to bring both terminals out, and that copper is real.
        """
        n = max(1, int(self.n))
        d_in, w = self.d_in * 1e-6, self.w * 1e-6
        gap = self.gap * 1e-6
        if self.shape == "circular":
            # draw_ind opens the pitch up to keep the drawn gap honest; the
            # estimate is given the same geometry that gets drawn.
            gap = (circular_pitch(self.w, self.gap) - self.w) * 1e-6
        t = max(1e-9, self.t_metal * 1e-6)
        freq = max(1.0, self.f_eval) * 1e6

        if self.topology == "series":
            pts = self._centreline()
            length = path_length(pts) * 1e-6
        else:
            rings = self._centreline()
            length = sum(path_length(r) for r in rings) * 1e-6

        if coil_core is None:
            self.l_series = self.r_dc = self.r_ac = self.q = 0.0
            self.wire_len = length * 1e6
            self.d_out = (d_in + 2 * n * w + 2 * (n - 1) * gap) * 1e6
            return

        shape = "cuadrada" if self.shape == "square" else "circular"
        if self.topology == "series":
            l_h = coil_core.inductance_microcoil(d_in, w, gap, n, t, shape,
                                                 "mohan")
            r_dc = coil_core.dc_resistance(RHO_AU, length, w * t)
            r_ac = coil_core.ac_resistance_rectangular(RHO_AU, length, w, t,
                                                       freq)
        else:
            # Concentric rings sharing two buses: coil_core solves the coupled
            # system, which is the whole point - ignoring the mutual terms
            # would overstate the benefit of putting rings in parallel.
            res = coil_core.parallel_rings_inductance(d_in, w, gap, n, t)
            l_h = float(res["L_total"])
            # n rings in parallel, each carrying its own share of the length
            r_one_dc = coil_core.dc_resistance(RHO_AU, length / n, w * t)
            r_one_ac = coil_core.ac_resistance_rectangular(RHO_AU, length / n,
                                                           w, t, freq)
            r_dc, r_ac = r_one_dc / n, r_one_ac / n

        self.l_series = float(l_h) * 1e9
        self.r_dc = float(r_dc)
        self.r_ac = float(r_ac)
        self.q = float(coil_core.quality_factor(l_h, r_ac, freq))
        self.d_out = float(coil_core.outer_diameter(d_in, w, gap, n)) * 1e6
        self.wire_len = length * 1e6

    def _centreline(self):
        n = max(1, int(self.n))
        if self.topology == "series":
            return spiral_with_leads(self.d_in, self.w, self.gap, n,
                                     self.shape, self.lead)
        return ring_centrelines(self.d_in, self.w, self.gap, n, self.shape)

    # ------------------------------------------------------------- the PCell
    def coerce_parameters_impl(self):
        self.n = max(1, int(self.n))
        self.d_in = max(2.0 * self.w, self.d_in)
        self.w = max(1.0, self.w)
        self.gap = max(1.0, self.gap)
        self.t_metal = max(0.001, self.t_metal)
        self._estimate()

    def produce_impl(self):
        text = None
        if self.show_value:
            if coil_core is None:
                text = "ind_igzo (no estimate: %s)" % PHYSICS_ERROR
            else:
                text = "ind_igzo %s / %s @ %gMHz / Q %.2f" % (
                    _format_l(self.l_series * 1e-9), _format_r(self.r_ac),
                    self.f_eval, self.q)
        on_gate = (self.metal == "gate")
        if self.topology == "series":
            draw_spiral(self.cell, d_in=self.d_in, w=self.w, gap=self.gap,
                        n=self.n, shape=self.shape, on_gate=on_gate,
                        lead=self.lead, value_text=text)
        else:
            draw_rings(self.cell, d_in=self.d_in, w=self.w, gap=self.gap,
                       n=self.n, shape=self.shape, on_gate=on_gate,
                       lead=self.lead, value_text=text)
