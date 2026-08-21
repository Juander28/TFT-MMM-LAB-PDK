#!/usr/bin/env python3
"""
Does the extracted level-1 model actually reproduce the devices it came from?

Simulates each measured device's output curves in ngspice with the extracted
model at its own W and L, and compares against the measurement point by point.
This is the check that says whether the model is usable, not just fitted.
"""

import os
import re
import subprocess
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from xls_reader import read_xls, sheet_columns  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
VDSF = {"TFT1": "TFT1.xls", "TFT2": "TFT2.xls", "TFT3": "tft3.xls"}
MODEL_LIB = os.path.join(ROOT, "test1", "models", "tft_igzo_test1.lib")
SC = os.environ.get("SCRATCH", tempfile.gettempdir())


def measured(chip, want_tr, want_L, want_W):
    for name, cells in read_xls(os.path.join(ROOT, "TFT", chip, "VDS", VDSF[chip])).items():
        m = re.match(r"(\d+)_(\d+)_L(\d+)_W(\d+)$", name)
        if not m:
            continue
        _, tr, L, W = int(m.group(1)), int(m.group(2)), float(m.group(3)), float(m.group(4))
        if (tr, L, W) != (want_tr, want_L, want_W):
            continue
        c = sheet_columns(cells)
        out = {}
        for g in range((max(c) + 1) // 4):
            Id, Vd, Vg = c.get(4 * g), c.get(4 * g + 1), c.get(4 * g + 3)
            if not Id or not Vd or not Vg:
                continue
            n = min(len(Id), len(Vd), len(Vg))
            out[round(float(np.median(Vg[:n])))] = (np.array(Vd[:n]), np.array(Id[:n]))
        return out
    return None


def simulate(model, W, L, vgs_list, vdmax=10.0, npts=201):
    """Return {vgs: (vd, id)} from ngspice for one device."""
    out = {}
    for vg in vgs_list:
        net = f"""* device check
.include {MODEL_LIB}
VD d 0 1
VG g 0 {vg}
M1 d g 0 0 {model} w={W}u l={L}u
.dc VD 0 {vdmax} {vdmax/(npts-1)}
.control
run
wrdata {SC}/dev.csv i(VD)
quit
.endc
.end
"""
        open(f"{SC}/dev.spice", "w").write(net)
        subprocess.run(["ngspice", "-b", f"{SC}/dev.spice"],
                       capture_output=True, timeout=120)
        d = np.loadtxt(f"{SC}/dev.csv")
        out[vg] = (d[:, 0], -d[:, 1])   # ngspice reports source current
    return out


def compare(chip, tr, L, W, model):
    meas = measured(chip, tr, L, W)
    if not meas:
        return None
    vgs = sorted(v for v in meas if v > 0)
    sim = simulate(model, W, L, vgs)
    rows = []
    for vg in vgs:
        vdm, idm = meas[vg]
        vds, ids = sim[vg]
        ism = np.interp(vdm, vds, ids)
        sel = vdm >= 0.8 * vdm.max()          # compare in saturation
        if sel.sum() < 3:
            continue
        ratio = np.median(ism[sel] / np.maximum(idm[sel], 1e-15))
        rows.append((vg, float(np.median(idm[sel])), float(np.median(ism[sel])), ratio))
    return rows


def main():
    print("=" * 78)
    print("MODEL vs MEASUREMENT - simulated in ngspice at the device's own W, L")
    print("=" * 78)
    cases = [
        ("TFT1", 1, 160.0, 100.0, "TFT_IGZO_BEST"),
        ("TFT1", 1, 80.0, 500.0, "TFT_IGZO_BEST"),
        ("TFT1", 2, 40.0, 100.0, "TFT_IGZO_BEST"),
        ("TFT1", 1, 20.0, 500.0, "TFT_IGZO_BEST"),
        ("TFT1", 1, 10.0, 1000.0, "TFT_IGZO_SHORT"),
        ("TFT1", 2, 8.0, 1000.0, "TFT_IGZO_SHORT"),
    ]
    print(f"{'chip':5} {'tr':>2} {'L':>4} {'W':>6} {'model':16} {'VGS':>4} "
          f"{'Isat meas':>11} {'Isat sim':>11} {'sim/meas':>9}")
    allr = []
    for chip, tr, L, W, model in cases:
        rows = compare(chip, tr, L, W, model)
        if not rows:
            print(f"{chip} {tr} L{L:.0f} W{W:.0f}: not found")
            continue
        for vg, im, isim, r in rows:
            allr.append(r)
            flag = "" if 0.5 <= r <= 2.0 else "   <-- off"
            print(f"{chip:5} {tr:2d} {L:4.0f} {W:6.0f} {model:16} {vg:4.0f} "
                  f"{im*1e6:9.2f}uA {isim*1e6:9.2f}uA {r:9.2f}{flag}")
    a = np.array(allr)
    print()
    print(f"median sim/meas = {np.median(a):.2f}   "
          f"within 2x: {100*np.mean((a>0.5)&(a<2.0)):.0f} %   "
          f"within 1.5x: {100*np.mean((a>1/1.5)&(a<1.5)):.0f} %")


if __name__ == "__main__":
    main()
