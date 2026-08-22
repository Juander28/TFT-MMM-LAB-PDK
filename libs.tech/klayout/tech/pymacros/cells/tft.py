"""
PCell declarations for the UCI/INRF IGZO TFT process.

The declaration says which knobs appear in the KLayout GUI; draw_tft.py holds
the geometry.  The split is the one used by gf180mcuD (fet.py / draw_fet.py).
"""

import math

import pya

from .draw_tft import draw_cap_mim, draw_tft


def _format_c(c_ff):
    """
    Engineering notation for a capacitance given in fF.

    The unit is chosen after rounding, not before: 999.98 fF rounds to "1000"
    at four significant figures, and printing "1000fF" on a cell that is one
    picofarad reads like a mistake.
    """
    for scale, unit in ((1e6, "nF"), (1e3, "pF"), (1.0, "fF")):
        value = c_ff / scale
        if value >= 0.9995:
            if float("%.4g" % value) >= 1000.0 and scale < 1e6:
                continue
            return "%.4g%s" % (value, unit)
    return "%.4gfF" % c_ff

# Defaults are the fabricated device TFT-10L100W, read off TFT_layout.GDS.
TFT_W = 100.0
TFT_L = 10.0
TFT_GATE_OV = 5.0
TFT_SD_LEN = 97.5
TFT_IGZO_EXT_X = 10.0
TFT_IGZO_EXT_Y = 5.0
TFT_GATE_EXT_Y = 10.0
TFT_PAD = 400.0
# The oxide-etch window inside a pad: 400 x 400 um pad, 360 x 360 um opening.
TFT_ETCH_INSET = 20.0

# Measured on the 400 x 400 um crossing of Test_capacitance: 250.2 pF.
COX_AREA = 1.564          # fF/um^2
# Clearance between the S/D pads and the gate pad, from the drawn test chip.
TFT_PAD_GAP = 325.0

# Drawn-to-printed bias: cells drawn as TFT-5L come back with an 8 um channel.
# One sample of one cell - reported, never applied.  See PDK_GUIDE.md section 8.
TFT_L_BIAS = 3.0


class tft_igzo(pya.PCellDeclarationHelper):
    """Top-gate coplanar IGZO thin-film transistor."""

    def __init__(self):
        super(tft_igzo, self).__init__()

        self.param("w_gate", self.TypeDouble, "Width (per finger)",
                   default=TFT_W, unit="um")
        self.param("l_gate", self.TypeDouble, "Length (drawn)",
                   default=TFT_L, unit="um")
        self.param("nf", self.TypeInt, "Number of Fingers", default=1)
        self.param("gate_ov", self.TypeDouble, "Gate Overlap per side",
                   default=TFT_GATE_OV, unit="um")
        self.param("sd_len", self.TypeDouble, "S/D Electrode Length",
                   default=TFT_SD_LEN, unit="um")
        self.param("igzo_ext_x", self.TypeDouble, "IGZO over Electrode",
                   default=TFT_IGZO_EXT_X, unit="um")
        self.param("igzo_ext_y", self.TypeDouble, "IGZO past Electrode End",
                   default=TFT_IGZO_EXT_Y, unit="um")
        self.param("gate_ext_y", self.TypeDouble, "Gate past IGZO",
                   default=TFT_GATE_EXT_Y, unit="um")
        self.param("pad", self.TypeBoolean, "Probe Pads", default=False)
        self.param("pad_size", self.TypeDouble, "Pad Size",
                   default=TFT_PAD, unit="um")
        self.param("pad_gap", self.TypeDouble, "Gate Pad Clearance",
                   default=TFT_PAD_GAP, unit="um")
        self.param("etch_inset", self.TypeDouble, "Dielectric Window Inset",
                   default=TFT_ETCH_INSET, unit="um")
        self.param("lbl", self.TypeBoolean, "Pins and Labels", default=False)

        self.param("l_bias", self.TypeDouble, "Drawn-to-printed bias",
                   default=TFT_L_BIAS, unit="um")
        self.param("l_printed", self.TypeDouble, "Length (printed, expected)",
                   default=TFT_L + TFT_L_BIAS, unit="um", readonly=True)
        self.param("w_total", self.TypeDouble, "Width (total, nf fingers)",
                   default=TFT_W, unit="um", readonly=True)

    def display_text_impl(self):
        return "tft_igzo(L=%.3gu,W=%.3gu,nf=%d)" % (
            self.l_gate, self.w_gate, self.nf)

    def coerce_parameters_impl(self):
        # Geometry that cannot be built is clamped, not silently accepted.
        self.nf = max(1, int(self.nf))
        self.w_gate = max(1.0, self.w_gate)
        self.l_gate = max(1.0, self.l_gate)
        self.gate_ov = max(0.0, self.gate_ov)
        self.sd_len = max(1.0, self.sd_len)
        # The island has to reach over both electrodes, or there is no channel.
        self.igzo_ext_x = max(0.5, self.igzo_ext_x)
        # Readonly read-outs.
        self.l_printed = self.l_gate + self.l_bias
        self.w_total = self.w_gate * self.nf

    def produce_impl(self):
        draw_tft(
            self.cell,
            w_gate=self.w_gate,
            l_gate=self.l_gate,
            nf=self.nf,
            gate_ov=self.gate_ov,
            sd_len=self.sd_len,
            igzo_ext_x=self.igzo_ext_x,
            igzo_ext_y=self.igzo_ext_y,
            gate_ext_y=self.gate_ext_y,
            pad=self.pad,
            pad_size=self.pad_size,
            pad_gap=self.pad_gap,
            etch_inset=self.etch_inset,
            lbl=self.lbl,
        )


class cap_mim(pya.PCellDeclarationHelper):
    """
    S/D-metal / Al2O3 / gate-metal overlap capacitor.

    Three ways to size it, because that is how the question actually arrives:
    sometimes you know the plate you want to draw, sometimes the area you have
    room for, and sometimes the capacitance the circuit needs.  Whichever one
    you set, the other two are read out - it is one formula, C = Cox * W * L,
    solved in whichever direction the mode asks for.

    Cox = 1.564 fF/um^2 is measured, not assumed: 250.2 pF on the 400 x 400 um
    crossing of Test_capacitance.
    """

    def __init__(self):
        super(cap_mim, self).__init__()

        self.mode_handle = self.param("mode", self.TypeList, "Sizing mode",
                              default="by dimensions")
        self.mode_handle.add_choice("by dimensions", "by dimensions")
        self.mode_handle.add_choice("by area", "by area")
        self.mode_handle.add_choice("by capacitance", "by capacitance")

        self.param("w", self.TypeDouble, "Width (by dimensions)",
                   default=TFT_PAD, unit="um")
        self.param("l", self.TypeDouble, "Length (by dimensions)",
                   default=TFT_PAD, unit="um")
        self.param("area_target", self.TypeDouble, "Area (by area)",
                   default=TFT_PAD * TFT_PAD, unit="um^2")
        self.param("c_target", self.TypeDouble, "Capacitance (by capacitance)",
                   default=COX_AREA * TFT_PAD * TFT_PAD, unit="fF")

        self.param("ext", self.TypeDouble, "Plate Extension",
                   default=200.0, unit="um")
        self.param("etch_inset", self.TypeDouble, "Dielectric Window Inset",
                   default=TFT_ETCH_INSET, unit="um")
        self.param("show_value", self.TypeBoolean, "Print the value on the cell",
                   default=True)
        self.param("lbl", self.TypeBoolean, "Pins and Labels", default=False)

        self.param("area", self.TypeDouble, "Area", default=0.0,
                   unit="um^2", readonly=True)
        self.param("c", self.TypeDouble, "Capacitance", default=0.0,
                   unit="fF", readonly=True)

    def display_text_impl(self):
        return "cap_mim(%s)" % _format_c(COX_AREA * self.w * self.l)

    def coerce_parameters_impl(self):
        # Snapped to a 10 nm grid: half of it is then a whole number of
        # nanometres, so insetting the etch window by an exact 20 um stays an
        # exact 20 um instead of rounding to 19.999 and failing its own rule.
        if self.mode == "by area":
            side = math.sqrt(max(1.0, self.area_target))
            self.w = self.l = round(side, 2)
        elif self.mode == "by capacitance":
            side = math.sqrt(max(1.0, self.c_target) / COX_AREA)
            self.w = self.l = round(side, 2)
        else:
            self.w = max(1.0, self.w)
            self.l = max(1.0, self.l)

        self.area = self.w * self.l
        self.c = COX_AREA * self.area
        # The two modes that were not used follow along, so the dialog always
        # shows a consistent set of numbers rather than a stale one.
        self.area_target = self.area
        self.c_target = self.c

    def produce_impl(self):
        text = _format_c(self.c) if self.show_value else None
        draw_cap_mim(self.cell, w=self.w, l=self.l, ext=self.ext,
                     etch_inset=self.etch_inset, lbl=self.lbl,
                     value_text=("cap_mim %s" % text) if text else None)
