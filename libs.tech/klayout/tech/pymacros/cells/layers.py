"""
Layer table for the UCI/INRF IGZO TFT process (igzo_mmm_lab).

Four masks plus alignment, in process order (bottom of the stack first):

    igzo   4/0   semiconductor island, deposited first
    sd     6/0   source/drain Au, directly on the IGZO
    oxetch 5/0   openings in the blanket 50 nm Al2O3 gate dielectric
    gate   2/0   gate Au, last metal - this is a TOP-GATE COPLANAR TFT
    align  8/0   alignment marks
    text   63/0  annotation only, never fabricated
    smd    70/0  surface-mount part body marker (value = area), never fabricated
    smd    70/1  surface-mount terminal marker, never fabricated
    ind.id 71/0  inductor marker (value = overlap with metal), never fabricated

The dielectric itself has no mask: it is a blanket ALD film, and only its
openings are drawn - and an opening covered by gate metal is a via between the
two metals, since the gate goes down after the etch.  Single source of truth for the PCell generators; it
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
# Not a mask: what a parametric cell prints on itself - its value, its size.
TEXT = pya.LayerInfo(63, 0, "text")
# Not masks either: markers that let extraction see a surface-mount part that
# is soldered on afterwards.  smd.body carries the value in its area; see
# cells/smd.py and the smd_cap device in the magic techfile.
SMD_BODY = pya.LayerInfo(70, 0, "smd.body")
SMD_TERM = pya.LayerInfo(70, 1, "smd.term")
# Not a mask: the marker that turns a stretch of coil track into the
# ind_igzo device for extraction.  Its overlap with the metal is the
# inductance (1 um^2 per nH).
IND_ID = pya.LayerInfo(71, 0, "ind.id")


def layer(layout, info):
    """Index of `info` in `layout`, creating it if needed."""
    return layout.layer(info)
