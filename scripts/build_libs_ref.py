#!/usr/bin/env python3
"""
Generate the primitive-device library in libs.ref from the KLayout PCells.

    python3 scripts/build_libs_ref.py

Writes libs.ref/igzo_mmm_lab_pr/gds/tft_primitives.gds with one cell per
device of the test-chip matrix, plus the capacitor.  The magic views in
libs.ref/igzo_mmm_lab_pr/mag are then generated from that GDS by
scripts/build_mag_views.sh, so the two never drift apart: there is one
description of the geometry, the PCell, and everything else is derived.

The matrix is the one drawn on the test chip: L in {5, 10, 20, 40, 80, 160} um
and W in {10, 50, 100, 500, 1000} um.
"""

import os
import sys

import pya

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "libs.tech", "klayout", "tech",
                                "pymacros"))

from cells import igzo_mmm_lab_pr  # noqa: E402

LENGTHS = [5, 10, 20, 40, 80, 160]
WIDTHS = [10, 50, 100, 500, 1000]


def add(layout, lib, pcell_name, cell_name, params):
    decl = lib.layout().pcell_declaration(pcell_name)
    variant = layout.add_pcell_variant(lib, decl.id(), params)
    top = layout.create_cell(cell_name)
    top.insert(pya.CellInstArray(variant, pya.Trans()))
    top.flatten(True)
    return top


def main():
    igzo_mmm_lab_pr()
    lib = pya.Library.library_by_name("igzo_mmm_lab_pr")
    if lib is None:
        raise SystemExit("PCell library did not register")

    layout = pya.Layout()
    layout.dbu = 0.001

    count = 0
    for length in LENGTHS:
        for width in WIDTHS:
            name = "tft_igzo_l%dw%d" % (length, width)
            add(layout, lib, "tft_igzo", name,
                {"l_gate": float(length), "w_gate": float(width),
                 "pad": False, "lbl": True})
            count += 1
    # The device as it is drawn on the test chip, probe pads and all.
    add(layout, lib, "tft_igzo", "tft_igzo_l10w100_pad",
        {"l_gate": 10.0, "w_gate": 100.0, "pad": True, "lbl": True})
    # The structure Cox was measured on.
    add(layout, lib, "cap_mim", "cap_mim_400x400",
        {"w": 400.0, "l": 400.0, "lbl": True})
    count += 2

    out = os.path.join(ROOT, "libs.ref", "igzo_mmm_lab_pr", "gds",
                       "tft_primitives.gds")
    layout.write(out)
    print("wrote %s (%d cells)" % (out, count))


if __name__ == "__main__":
    main()
