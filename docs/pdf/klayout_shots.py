"""
Render the KLayout figures used by the guide.

    klayout -z -nc -r klayout_shots.py

Runs offscreen: it draws the generated primitives with the PDK's own layer
properties, so the colours are the ones the layout editor shows.
"""

import os

import pya

PDK = os.path.join(os.environ.get("PDK_ROOT", os.path.expanduser("~/pdks")),
                   os.environ.get("PDK", "TFT-MMM-LAB-PDK"))
GDS = PDK + "/libs.ref/igzo_mmm_lab_pr/gds/tft_primitives.gds"
LYP = PDK + "/libs.tech/klayout/tech/igzo_mmm_lab.lyp"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "figures")


def shot(cell, name, w=1400, h=1000, margin=0.08, box=None):
    lv = pya.LayoutView()
    lv.load_layout(GDS, 0)
    layout = lv.cellview(0).layout()
    lv.cellview(0).cell = layout.cell(cell)
    lv.load_layer_props(LYP)
    lv.max_hier()
    lv.zoom_fit()
    if box:
        lv.zoom_box(pya.DBox(*box))
    else:
        b = lv.box()
        lv.zoom_box(b.enlarged(b.width() * margin, b.height() * margin))
    path = os.path.join(OUT, name)
    lv.save_image(path, w, h)
    print("wrote", os.path.normpath(path))


shot("tft_igzo_l10w100", "klayout_tft_core.png")
shot("tft_igzo_l10w100_pad", "klayout_tft_pad.png")
shot("tft_igzo_l10w100", "klayout_tft_zoom.png", box=(-30, -70, 30, 70))
shot("cap_mim_400x400", "klayout_cap.png")
shot("tft_igzo_l160w1000", "klayout_tft_big.png")
