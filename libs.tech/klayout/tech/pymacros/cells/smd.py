"""
Surface-mount capacitor land pattern for the UCI/INRF IGZO TFT process.

The capacitor itself is a bought part, soldered or glued on after the four
masks.  What the process makes is its two pads - and, for extraction and LVS
to see a capacitor there at all, two marker layers that are never fabricated:

  smd.term 70/1   a 10 um wire from the middle of each pad towards the gap
  smd.body 70/0   the rectangle that closes the gap between the two wires

The cell is smd_cap_pads, NOT smd_cap: that is the name of the device it
extracts to, and a layout cell with the device's own name makes the
extracted netlist call itself - netgen aborts on it.

Magic reads the pair as one smd_cap device between the two pads (the smd.term
wire becomes a contact onto whichever metal it lands on), and the value it
reports is the AREA of the body: 1 um^2 per nF.  The cell draws that area
exactly, on the 10 nm grid, for the value typed in - 10 uF is a 100 x 100 um
body, 471 pF a 0.1 x 4.71 um one.  So the capacitance extracted from the
layout is the capacitance you asked for, and netgen checks it against the
schematic's c to 1 %.

LAND PATTERNS.  The package presets are typical IPC-7351 nominal lands; the
part's own datasheet wins where they differ, and "custom" takes any pads.
They are drawn in whichever metal you choose.  A NOTE ON ATTACHING PARTS TO
THIS PROCESS: the pads are the process gold, 10 nm Cr + 50 nm Au unless the
metal is thickened.  Solder dissolves thin gold and does not wet chromium, so
conductive epoxy is the safer attach unless the pads are plated.
"""

import math

import pya

from .draw_tft import _box, _text
from .layers import GATE, SD, SMD_BODY, SMD_TERM, TEXT

# package: (pad length along the part, pad width across it, gap between pads,
#           body length, body width) - all um
PACKAGES = {
    "0201": (300.0, 300.0, 300.0, 600.0, 300.0),
    "0402": (500.0, 550.0, 450.0, 1000.0, 500.0),
    "0603": (800.0, 950.0, 700.0, 1600.0, 800.0),
    "0805": (1000.0, 1350.0, 900.0, 2000.0, 1250.0),
    "1206": (1150.0, 1800.0, 1800.0, 3200.0, 1600.0),
}
WIRE = 10.0                 # um, width of the smd.term runs
GRID_NM = 10                # magic's internal grid
NF_PER_UM2 = 1.0            # the encoding magic's techfile decodes

_SI = {"f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6, "m": 1e-3, "": 1.0}


def parse_value(text):
    """'10u', '22uF', '471p', '4.7e-6' -> farads.  A trailing F after a
    prefix is dropped ('22uF'); a bare trailing f is femto ('10f')."""
    low = str(text).strip().replace(" ", "").lower()
    if len(low) > 1 and low.endswith("f") and low[-2] in "fpnum":
        low = low[:-1]
    if low and low[-1] in "fpnum":
        return float(low[:-1]) * _SI[low[-1]]
    return float(low)


def format_value(c):
    for scale, unit in ((1e-6, "u"), (1e-9, "n"), (1e-12, "p"), (1e-15, "f")):
        if c >= scale * 0.9995:
            return "%g%sF" % (float("%.4g" % (c / scale)), unit)
    return "%gF" % c


def body_units(c):
    """Body length and width, in 10 nm units, whose product is c in nF.

    The value is held to three significant figures - a bought part carries
    two - so it factors into a small integer times a power of ten.  The body
    is then drawn as close to square as that factoring allows: the length
    is the largest power of ten, not above the square root, that divides it.
    10 uF comes out 100 x 100 um, 22 uF 100 x 220 um, 471 pF 0.1 x 4.71 um."""
    n_units2 = c / 1e-9 / NF_PER_UM2 * 1e4          # 1 um^2 = 1e4 units^2
    if n_units2 < 1:
        raise ValueError("%s is below the 0.1 pF the 10 nm grid can encode"
                         % format_value(c))
    exp = int(math.floor(math.log10(n_units2)))
    if exp >= 2:
        step = 10 ** (exp - 2)
        n = int(round(n_units2 / step)) * step
    else:
        n = int(round(n_units2))
    length = 10 ** int(math.floor(math.log10(math.sqrt(n))))
    while length > 1 and n % length:
        length //= 10
    return length, n // length, n


class smd_cap_pads(pya.PCellDeclarationHelper):
    """Land pattern and LVS markers for a surface-mount capacitor."""

    def __init__(self):
        super(smd_cap_pads, self).__init__()
        self.param("value", self.TypeString, "Capacitance (e.g. 10u, 22uF, 471p)",
                   default="10u")
        pk = self.param("package", self.TypeList, "Package", default="0603")
        for name in list(PACKAGES) + ["custom"]:
            pk.add_choice(name, name)
        mt = self.param("metal", self.TypeList, "Pad metal", default="gate")
        mt.add_choice("gate (2/0)", "gate")
        mt.add_choice("source/drain (6/0)", "sd")
        self.param("pad_l", self.TypeDouble, "Pad length (custom)",
                   default=800.0, unit="um")
        self.param("pad_w", self.TypeDouble, "Pad width (custom)",
                   default=950.0, unit="um")
        self.param("gap", self.TypeDouble, "Gap between pads (custom)",
                   default=700.0, unit="um")
        self.param("outline", self.TypeBoolean,
                   "Draw the part outline (text layer)", default=True)
        self.param("show_value", self.TypeBoolean, "Print the value on the cell",
                   default=True)
        self.param("c", self.TypeDouble, "Capacitance encoded", default=0.0,
                   unit="F", readonly=True)
        self.param("body", self.TypeString, "Marker body (l x w)",
                   default="", readonly=True)

    def _dims(self):
        if self.package in PACKAGES:
            return PACKAGES[self.package]
        return (self.pad_l, self.pad_w, self.gap, 0.0, 0.0)

    def display_text_impl(self):
        return "smd_cap_pads(%s, %s)" % (self.value, self.package)

    def coerce_parameters_impl(self):
        try:
            c = parse_value(self.value)
            ln, wd, n = body_units(c)
            self.c = n * 1e-4 * NF_PER_UM2 * 1e-9
            self.body = "%g x %g um" % (ln * GRID_NM / 1e3, wd * GRID_NM / 1e3)
        except (ValueError, TypeError) as err:
            self.c = 0.0
            self.body = "invalid value: %s" % err

    def produce_impl(self):
        pl, pw, gap, bl, bw = self._dims()
        c = parse_value(self.value)
        ln, wd, _ = body_units(c)
        if ln * GRID_NM / 1e3 > gap - 2.0:
            raise ValueError("value too large for this gap")
        metal = GATE if self.metal == "gate" else SD
        cell = self.cell
        # pads, centred on the origin, along x
        x_in = gap / 2.0
        _box(cell, metal, -x_in - pl, -pw / 2.0, -x_in, pw / 2.0)
        _box(cell, metal, x_in, -pw / 2.0, x_in + pl, pw / 2.0)
        # the body on the 10 nm grid: integer database units throughout
        dbu = cell.layout().dbu
        u = int(round(GRID_NM * 1e-3 / dbu))            # grid step in dbu
        l_db, w_db = ln * u, wd * u
        x1 = -(l_db // (2 * u)) * u
        y1 = -(w_db // (2 * u)) * u
        li_b = cell.layout().layer(SMD_BODY)
        cell.shapes(li_b).insert(pya.Box(x1, y1, x1 + l_db, y1 + w_db))
        # the two runs from the middle of each pad to the body
        li_t = cell.layout().layer(SMD_TERM)
        hw = int(round(WIRE / 2.0 / dbu))
        xpl = int(round((-x_in - pl / 2.0) / dbu))
        xpr = int(round((x_in + pl / 2.0) / dbu))
        cell.shapes(li_t).insert(pya.Box(xpl, -hw, x1, hw))
        cell.shapes(li_t).insert(pya.Box(x1 + l_db, -hw, xpr, hw))
        if self.outline and bl > 0:
            poly = pya.DBox(-bl / 2.0, -bw / 2.0, bl / 2.0, bw / 2.0)
            cell.shapes(cell.layout().layer(TEXT)).insert(
                pya.DPath([poly.p1, pya.DPoint(poly.right, poly.bottom),
                           poly.p2, pya.DPoint(poly.left, poly.top), poly.p1],
                          2.0))
        if self.show_value:
            _text(cell, TEXT, "%s %s" % (format_value(c), self.package), 0.0,
                  pw / 2.0 + 60.0, max(20.0, pw / 10.0))
