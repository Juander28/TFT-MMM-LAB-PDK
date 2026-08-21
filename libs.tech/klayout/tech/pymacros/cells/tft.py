"""
PCell declarations for the UCI/INRF IGZO TFT process.

The declaration says which knobs appear in the KLayout GUI; draw_tft.py holds
the geometry.  The split is the one used by gf180mcuD (fet.py / draw_fet.py).
"""

import pya

from .draw_tft import draw_cap_mim, draw_tft

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
    """S/D-metal / Al2O3 / gate-metal overlap capacitor."""

    def __init__(self):
        super(cap_mim, self).__init__()
        self.param("w", self.TypeDouble, "Width", default=TFT_PAD, unit="um")
        self.param("l", self.TypeDouble, "Length", default=TFT_PAD, unit="um")
        self.param("ext", self.TypeDouble, "Plate Extension",
                   default=200.0, unit="um")
        self.param("etch_inset", self.TypeDouble, "Dielectric Window Inset",
                   default=TFT_ETCH_INSET, unit="um")
        self.param("lbl", self.TypeBoolean, "Pins and Labels", default=False)
        self.param("c", self.TypeDouble, "Capacitance", default=0.0,
                   unit="fF", readonly=True)

    def display_text_impl(self):
        return "cap_mim(%.4gx%.4gu)" % (self.w, self.l)

    def coerce_parameters_impl(self):
        self.w = max(1.0, self.w)
        self.l = max(1.0, self.l)
        # Cox = 1.564 fF/um^2, measured on the 400 x 400 um test plate.
        self.c = 1.564 * self.w * self.l

    def produce_impl(self):
        draw_cap_mim(self.cell, w=self.w, l=self.l, ext=self.ext,
                     etch_inset=self.etch_inset, lbl=self.lbl)
