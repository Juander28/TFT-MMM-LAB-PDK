"""
Regression test: the PCell must reproduce the fabricated device.

The reference is TFT-10L100W in the test-chip GDS, the cell the model was
extracted from.  Run it with the real GDS:

    python3 test_pcell_vs_gds.py /path/to/TFT_layout.GDS

Structure follows gf180mcuD/.../pymacros/testing/pcell_reg_Pytest.py: build the
cell through the PCell, then compare against what is drawn in silicon.

Only the device layers are compared shape-for-shape.  The gate of the drawn
cell also carries the routing up to its probe pad, which is chip-specific and
not part of the device, so for the gate only the x extent (the part that sets
the overlap) is checked.
"""

import os
import sys

import pya

CELLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.abspath(CELLS))

from cells import igzo_mmm_lab_pr  # noqa: E402

REFERENCE_CELL = "TFT-10L100W"
# Device parameters of that cell, from PDK_GUIDE.md section 5.  The drawn cell
# carries its 400 x 400 um probe pads, butted against the electrodes, so the
# PCell is built with pads too or the S/D shapes cannot match.
PARAMS = {"w_gate": 100.0, "l_gate": 10.0, "nf": 1, "pad": True}


def boxes(cell, layer_info, layout):
    """Merged shapes of one layer as a sorted list of um boxes."""
    idx = layout.layer(layer_info)
    region = pya.Region(cell.begin_shapes_rec(idx)).merged()
    out = []
    for poly in region.each():
        b = poly.bbox().to_dtype(layout.dbu)
        out.append((round(b.left, 3), round(b.bottom, 3),
                    round(b.right, 3), round(b.top, 3)))
    return sorted(out)


def normalise(boxes_list):
    """Shift a list of boxes so that its bounding box is centred on 0,0."""
    if not boxes_list:
        return []
    x1 = min(b[0] for b in boxes_list)
    x2 = max(b[2] for b in boxes_list)
    y1 = min(b[1] for b in boxes_list)
    y2 = max(b[3] for b in boxes_list)
    dx, dy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    return sorted((round(b[0] - dx, 3), round(b[1] - dy, 3),
                   round(b[2] - dx, 3), round(b[3] - dy, 3))
                  for b in boxes_list)


def build_pcell(**params):
    layout = pya.Layout()
    layout.dbu = 0.001
    lib = pya.Library.library_by_name("igzo_mmm_lab_pr")
    assert lib is not None, "PCell library did not register"
    decl = lib.layout().pcell_declaration("tft_igzo")
    pcell = layout.add_pcell_variant(lib, decl.id(), params)
    top = layout.create_cell("TOP")
    top.insert(pya.CellInstArray(pcell, pya.Trans()))
    return layout, top


def main(gds_path):
    igzo_mmm_lab_pr()

    ref = pya.Layout()
    ref.read(gds_path)
    ref_cell = ref.cell(REFERENCE_CELL)
    assert ref_cell is not None, "%s not in %s" % (REFERENCE_CELL, gds_path)

    layout, top = build_pcell(**PARAMS)

    failures = []

    # --- every device layer, shape for shape --------------------------------
    for name, info in (("sd 6/0", pya.LayerInfo(6, 0)),
                       ("igzo 4/0", pya.LayerInfo(4, 0)),
                       ("gate 2/0", pya.LayerInfo(2, 0))):
        got = normalise(boxes(top, info, layout))
        want = normalise(boxes(ref_cell, info, ref))
        if got != want:
            failures.append("%s: PCell %s != GDS %s" % (name, got, want))
        else:
            print("OK  %-9s %s" % (name, got))

    # --- gate: compared where it is a device, not where it is routing ------
    # The drawn cell routes its gate up to a probe pad, which is chip-specific.
    # What the process defines is the stripe over the island and the overlap
    # onto each electrode - so those are what is compared.
    def region(cell, layout, li):
        return pya.Region(cell.begin_shapes_rec(layout.layer(li))).merged()

    for src, cell, lay in (("PCell", top, layout), ("GDS", ref_cell, ref)):
        gate = region(cell, lay, pya.LayerInfo(2, 0))
        igzo = region(cell, lay, pya.LayerInfo(4, 0))
        sd = region(cell, lay, pya.LayerInfo(6, 0))
        stripe = (gate & igzo).bbox().to_dtype(lay.dbu)
        overlaps = sorted(round(p.bbox().to_dtype(lay.dbu).width(), 3)
                          for p in (gate & sd).each())
        w = round(stripe.width(), 3)
        if abs(w - 20.0) > 1e-6:
            failures.append("gate 2/0 (%s): stripe over the island is %s um, "
                            "expected 20" % (src, w))
        elif overlaps != [5.0, 5.0]:
            failures.append("gate 2/0 (%s): overlaps onto the electrodes are "
                            "%s um, expected [5.0, 5.0]" % (src, overlaps))
        else:
            print("OK  gate 2/0  %-5s stripe %g um over the island, overlap "
                  "%s um per side" % (src, w, overlaps))

    # --- fingers share electrodes and add up in width -----------------------
    for nf in (1, 2, 5):
        params = dict(PARAMS, nf=nf, pad=False)
        lay, cell = build_pcell(**params)
        sd = boxes(cell, pya.LayerInfo(6, 0), lay)
        if len(sd) != nf + 1:
            failures.append("nf=%d: %d electrodes, expected %d"
                            % (nf, len(sd), nf + 1))
            continue
        w_total = sum(b[3] - b[1] for b in sd[:1]) * nf
        if abs(w_total - PARAMS["w_gate"] * nf) > 1e-6:
            failures.append("nf=%d: total width %s" % (nf, w_total))
        else:
            print("OK  nf=%d    %d shared electrodes, W_total = %g um"
                  % (nf, len(sd), w_total))

    # --- the printed length is reported, not applied ------------------------
    lay, cell = build_pcell(**dict(PARAMS, pad=False))
    sd = boxes(cell, pya.LayerInfo(6, 0), lay)
    gap = sd[1][0] - sd[0][2]
    if abs(gap - PARAMS["l_gate"]) > 1e-6:
        failures.append("drawn channel gap %s um, expected %s (the +3 um "
                        "process bias must NOT be in the geometry)"
                        % (gap, PARAMS["l_gate"]))
    else:
        print("OK  drawn channel gap %g um - the +3 um print bias is reported "
              "by l_printed, not drawn" % gap)

    if failures:
        print("\nFAILED:")
        for f in failures:
            print("  " + f)
        return 1
    print("\nAll PCell checks passed against %s." % REFERENCE_CELL)
    return 0


if __name__ == "__main__":
    gds = (sys.argv[1] if len(sys.argv) > 1
           else os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "..", "..", "..", "..", "..", "libs.ref",
                             "igzo_mmm_lab_pr", "gds", "TFT_layout.gds"))
    sys.exit(main(gds))
