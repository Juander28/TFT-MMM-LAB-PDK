#!/usr/bin/env python3
"""
Series / contact resistance of the IGZO TFTs.

Primary method - transistor channel-resistance scaling (no external geometry
needed, unlike TLM whose pad spacing is not recorded in the .xls files):

    R_on(L) * W  =  2*Rc*W  +  Rsh_ch * L        at fixed VGS, VDS -> 0

Plotting width-normalised on-resistance against channel length gives the
width-normalised contact resistance (Ohm*um) as the intercept and the gated
sheet resistance as the slope.  The contact-limited length is
L_c = 2*Rc*W / Rsh_ch: below it the contacts dominate the device.

Secondary - the TLM pad-pair resistances are reported as measured, with the
unknown spacing made explicit.
"""

import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from xls_reader import read_xls, sheet_columns  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..", "TFT")
VDS_FILE = {"TFT1": "TFT1.xls", "TFT2": "TFT2.xls", "TFT3": "tft3.xls"}


def on_resistance(chip, vds_lin=0.5):
    """{(VGS, L, W): R_on} from the low-VDS slope of every output curve."""
    out = {}
    for name, cells in read_xls(os.path.join(ROOT, chip, "VDS", VDS_FILE[chip])).items():
        m = re.match(r"(\d+)_(\d+)_L(\d+)_W(\d+)$", name)
        if not m:
            continue
        _, tr, L, W = m.groups()
        cols = sheet_columns(cells)
        for g in range((max(cols) + 1) // 4):
            Id, Vd, Vg = cols.get(4 * g), cols.get(4 * g + 1), cols.get(4 * g + 3)
            if not Id or not Vd or not Vg:
                continue
            n = min(len(Id), len(Vd), len(Vg))
            vd, idr = np.array(Vd[:n]), np.array(Id[:n])
            vg = round(float(np.median(Vg[:n])))
            sel = (vd >= 0) & (vd <= vds_lin)
            if sel.sum() < 4:
                continue
            gd = np.polyfit(vd[sel], idr[sel], 1)[0]
            if gd > 0:
                out.setdefault((vg, float(L), float(W)), []).append(1.0 / gd)
    return {k: float(np.median(v)) for k, v in out.items()}


def main():
    print("=" * 78)
    print("CONTACT RESISTANCE FROM CHANNEL-LENGTH SCALING  (R_on*W vs L)")
    print("=" * 78)
    print(f"{'chip':5} {'VGS':>4} {'n':>3} {'2Rc*W [Ohm*um]':>16} {'Rsh_ch [Ohm/sq]':>17} "
          f"{'L_c [um]':>9} {'R2':>6}")
    summary = {}
    for chip in ("TFT1", "TFT2", "TFT3"):
        ron = on_resistance(chip)
        for vgs in (2, 4, 6):
            pts = [(L, R * W) for (vg, L, W), R in ron.items() if vg == vgs]
            if len(pts) < 5:
                continue
            L = np.array([p[0] for p in pts])
            RW = np.array([p[1] for p in pts])
            # width-normalised on-resistance is log-normally scattered; fit in
            # linear space but drop the worst decile to stay robust
            keep = RW < np.quantile(RW, 0.9)
            a, b = np.polyfit(L[keep], RW[keep], 1)
            pred = a * L[keep] + b
            ss = 1 - np.sum((RW[keep] - pred) ** 2) / np.sum((RW[keep] - RW[keep].mean()) ** 2)
            Lc = b / a if a > 0 else np.nan
            summary[(chip, vgs)] = (b, a, Lc)
            print(f"{chip:5} {vgs:4d} {keep.sum():3d} {b:16.3e} {a:17.3e} "
                  f"{Lc:9.1f} {ss:6.3f}")

    print()
    print("Interpretation: L_c is the channel length at which the contacts")
    print("contribute as much resistance as the channel itself.  Devices with")
    print("L < L_c are contact-limited and under-report the intrinsic Kp.")

    print()
    print("=" * 78)
    print("TLM PAD-PAIR RESISTANCES (as measured)")
    print("=" * 78)
    print("NOTE: pad spacing is NOT recorded in the .xls files, so absolute Rc")
    print("and sheet resistance cannot be pinned from TLM alone.  Reported for")
    print("cross-reference only; the channel-scaling fit above is the usable one.")
    for chip in ("TFT1", "TFT2", "TFT3"):
        d = read_xls(os.path.join(ROOT, chip, "TLM", f"TLM_{chip}.xls"
                                  if chip != "TFT3" else "TLM_TFT3.xls"))
        pairs = {}
        for n, cells in d.items():
            if n in ("Calc", "Settings"):
                continue
            cols = sheet_columns(cells)
            I, V = cols.get(0), cols.get(1)
            if I and V and len(I) > 10:
                m = min(len(I), len(V))
                pairs[n] = np.polyfit(np.array(I[:m]), np.array(V[:m]), 1)[0]
        order = sorted(pairs, key=lambda s: (int(s[0]), int(s[1])))
        consec = [pairs[k] for k in ("12", "23", "34", "45") if k in pairs]
        print(f"  {chip}: " + "  ".join(f"{k}={pairs[k]/1e6:.2f}M" for k in order))
        if len(consec) == 4:
            print(f"        consecutive gaps ratio "
                  f"{' : '.join(f'{c/consec[0]:.2f}' for c in consec)}"
                  f"   (equal spacing would give 1 : 1 : 1 : 1)")


if __name__ == "__main__":
    main()
