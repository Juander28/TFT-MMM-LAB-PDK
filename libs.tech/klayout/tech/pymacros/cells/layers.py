"""
Layer table for the UCI/INRF IGZO TFT process (igzo_mmm_lab).

Four masks plus alignment, in process order (bottom of the stack first):

    igzo   4/0   semiconductor island, deposited first
    sd     6/0   source/drain Au, directly on the IGZO
    oxetch 5/0   openings in the blanket 50 nm Al2O3 gate dielectric
    gate   2/0   gate Au, last metal - this is a TOP-GATE COPLANAR TFT
    align  8/0   alignment marks

The dielectric itself has no mask: it is a blanket ALD film, and only its
openings are drawn.  Single source of truth for the PCell generators; it
mirrors libs.tech/klayout/tech/igzo_mmm_lab.map, so keep the two in step.
"""

import pya

IGZO = pya.LayerInfo(4, 0, "igzo")
SD = pya.LayerInfo(6, 0, "sd")
SD_PIN = pya.LayerInfo(6, 10, "sd.pin")
SD_LBL = pya.LayerInfo(6, 20, "sd.label")
OXETCH = pya.LayerInfo(5, 0, "oxetch")
GATE = pya.LayerInfo(2, 0, "gate")
GATE_PIN = pya.LayerInfo(2, 10, "gate.pin")
GATE_LBL = pya.LayerInfo(2, 20, "gate.label")
ALIGN = pya.LayerInfo(8, 0, "align")


def layer(layout, info):
    """Index of `info` in `layout`, creating it if needed."""
    return layout.layer(info)
