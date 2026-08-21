#!/usr/bin/env python3
"""
Extract SPICE level-1 parameters (Kp*(W/L), Vth, lambda) for the IGZO TFTs.

Three independent routes, deliberately kept separate so they can be compared:

  (a) LINEAR from the transfer sweeps in TFT/test/ (VDS = 0.1 / 1 / 2 V).
      gm = Kp*(W/L)*VDS  ->  Kp*(W/L) = gm / VDS.  No quadratic fit needed.
      Only 2 devices, and their W/L is not recorded, so this validates the
      METHOD rather than feeding the design.

  (b) LINEAR from the low-VDS end of the output curves (VDS -> 0).
      gd = dId/dVDS|_{VDS->0} = Kp*(W/L)*(VGS - Vth).  Fitting gd vs VGS gives
      both Kp*(W/L) and Vth over the FULL W x L matrix.

  (c) SATURATION from the same output curves at VDS = 10 V.
      Isat = (Kp/2)*(W/L)*(VGS - Vth)^2, fitted as sqrt(Isat) vs VGS.

(b)/(c) disagreeing is the fingerprint of series/contact resistance: the linear
regime is far more sensitive to it than saturation.
"""

import re
import sys
import os

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "tools"))
from pdk_paths import DATA, MODEL_FILE, require_data  # noqa: E402
from xls_reader import read_xls, sheet_columns  # noqa: E402

ROOT = DATA
CHIPS = ("TFT1", "TFT2", "TFT3")
VDS_FILE = {"TFT1": "TFT1.xls", "TFT2": "TFT2.xls", "TFT3": "tft3.xls"}


# --------------------------------------------------------------------------
# (a) transfer sweeps
# --------------------------------------------------------------------------
def transfer_runs():
    """Yield dicts for every transfer sweep found in TFT/test/."""
    for fn in ("TEST2.xls", "vgs-id_GDL#1.xls"):
        path = os.path.join(ROOT, "test", fn)
        if not os.path.exists(path):
            continue
        for run, cells in read_xls(path).items():
            if run in ("Calc", "Settings"):
                continue
            cols = sheet_columns(cells)
            # DrainI | DrainV | GateV | GM | IDLIN | VT | IDRAIN
            Id, Vd, Vg, gm = cols.get(0), cols.get(1), cols.get(2), cols.get(3)
            vt = cols.get(5)
            if not Id or not Vg or len(Vg) < 20:
                continue
            n = min(len(Id), len(Vd), len(Vg), len(gm or []))
            yield {
                "file": fn, "run": run,
                "vds": float(np.median(Vd[:n])),
                "vgs": np.array(Vg[:n]), "id": np.array(Id[:n]),
                "gm": np.array(gm[:n]) if gm else None,
                "vt_tool": vt[0] if vt else None,
            }


def analyse_transfer(run):
    """Kp*(W/L) from gm/VDS, plus Vth and subthreshold swing."""
    vds, vgs, idr = run["vds"], run["vgs"], run["id"]
    gm = run["gm"]
    if gm is None:
        gm = np.gradient(idr, vgs)

    # Kp*(W/L) from the plateau of gm (median of the top decile, robust to spikes)
    top = np.sort(gm[np.isfinite(gm)])[-max(3, len(gm) // 10):]
    kp_wl = float(np.median(top)) / vds

    # Vth by linear extrapolation from the point of maximum slope
    k = int(np.nanargmax(gm))
    vth = float(vgs[k] - idr[k] / gm[k]) if gm[k] > 0 else np.nan

    # subthreshold swing over the decades below threshold
    ss = np.nan
    pos = idr > 0
    if pos.sum() > 10:
        lg = np.log10(idr[pos])
        vg = vgs[pos]
        sel = (lg > lg.min() + 0.5) & (lg < lg.min() + 2.5)
        if sel.sum() > 5:
            slope = np.polyfit(vg[sel], lg[sel], 1)[0]
            if slope > 0:
                ss = 1.0 / slope  # V/decade

    onoff = float(idr.max() / max(idr[idr > 0].min(), 1e-15)) if pos.any() else np.nan
    return {"kp_wl": kp_wl, "vth": vth, "ss": ss, "onoff": onoff}


# --------------------------------------------------------------------------
# (b) + (c) output curves
# --------------------------------------------------------------------------
def output_curves(chip):
    """Yield (transistor, L_um, W_um, {vgs: (VDS array, Id array)})."""
    path = os.path.join(ROOT, chip, "VDS", VDS_FILE[chip])
    for name, cells in read_xls(path).items():
        m = re.match(r"(\d+)_(\d+)_L(\d+)_W(\d+)$", name)
        if not m:
            continue
        _, tr, L, W = m.groups()
        cols = sheet_columns(cells)
        curves = {}
        for g in range((max(cols) + 1) // 4):
            Id, Vd, Vg = cols.get(4 * g), cols.get(4 * g + 1), cols.get(4 * g + 3)
            if not Id or not Vd or not Vg:
                continue
            n = min(len(Id), len(Vd), len(Vg))
            curves[round(float(np.median(Vg[:n])))] = (
                np.array(Vd[:n]), np.array(Id[:n]))
        if curves:
            yield int(tr), float(L), float(W), curves


def fit_device(curves, vds_lin=0.5):
    """Return linear-regime and saturation-regime (Kp*(W/L), Vth) for one device."""
    out = {}

    # (b) linear: gd = dId/dVDS as VDS -> 0, then gd vs VGS
    vg_list, gd_list = [], []
    for vg, (vd, idr) in sorted(curves.items()):
        sel = (vd >= 0) & (vd <= vds_lin)
        if sel.sum() < 4:
            continue
        slope = np.polyfit(vd[sel], idr[sel], 1)[0]
        vg_list.append(vg)
        gd_list.append(slope)
    if len(vg_list) >= 3:
        a, b = np.polyfit(vg_list, gd_list, 1)
        if a > 0:
            out["kp_wl_lin"] = float(a)
            out["vth_lin"] = float(-b / a)

    # (c) saturation: sqrt(Isat) vs VGS at the top of the VDS sweep
    vg_list, sq_list = [], []
    for vg, (vd, idr) in sorted(curves.items()):
        if vg <= 0:            # VGS = 0 sits in depletion conduction; skip
            continue
        isat = float(idr[int(np.argmax(vd))])
        if isat <= 0:
            continue
        vg_list.append(vg)
        sq_list.append(np.sqrt(isat))
    if len(vg_list) >= 3:
        a, b = np.polyfit(vg_list, sq_list, 1)
        if a > 0:
            out["kp_wl_sat"] = float(2 * a * a)
            out["vth_sat"] = float(-b / a)
            out["isat_max"] = float(sq_list[-1] ** 2)

    # lambda from the saturation slope of the highest-VGS curve
    vg_top = max(curves)
    vd, idr = curves[vg_top]
    sel = vd >= 0.7 * vd.max()
    if sel.sum() > 5:
        slope, inter = np.polyfit(vd[sel], idr[sel], 1)
        if slope > 0 and inter != 0:
            out["lambda"] = float(slope / inter)
            out["VA"] = float(inter / slope)
    return out


def main():
    print("=" * 78)
    print("(a) LINEAR-REGIME EXTRACTION FROM TRANSFER SWEEPS  (TFT/test/)")
    print("=" * 78)
    print(f"{'file':22} {'run':6} {'VDS':>5} {'Kp*(W/L)':>11} {'Vth':>7} "
          f"{'Vth_tool':>9} {'SS':>8} {'on/off':>9}")
    for run in transfer_runs():
        r = analyse_transfer(run)
        vt = run["vt_tool"]
        print(f"{run['file']:22} {run['run']:6} {run['vds']:5.2f} "
              f"{r['kp_wl'] * 1e6:8.2f} uA/V2 {r['vth']:7.2f} "
              f"{(f'{vt:9.2f}' if vt is not None else ' ' * 9)} "
              f"{r['ss']:8.2f} {r['onoff']:9.2e}")

    print()
    print("=" * 78)
    print("(b)+(c) OUTPUT CURVES: LINEAR (VDS->0) vs SATURATION (VDS=10 V)")
    print("=" * 78)
    print(f"{'chip':5} {'tr':>2} {'L':>4} {'W':>5} {'W/L':>6} "
          f"{'Kp_lin':>9} {'Vth_lin':>8} {'Kp_sat':>9} {'Vth_sat':>8} "
          f"{'lin/sat':>8} {'VA':>7}")
    rows = []
    for chip in CHIPS:
        for tr, L, W, curves in output_curves(chip):
            f = fit_device(curves)
            if "kp_wl_lin" not in f or "kp_wl_sat" not in f:
                continue
            wl = W / L
            kl, ks = f["kp_wl_lin"] / wl, f["kp_wl_sat"] / wl
            rows.append(dict(chip=chip, tr=tr, L=L, W=W, wl=wl,
                             kp_lin=kl, kp_sat=ks,
                             vth_lin=f["vth_lin"], vth_sat=f["vth_sat"],
                             VA=f.get("VA", np.nan),
                             isat=f.get("isat_max", np.nan)))
            print(f"{chip:5} {tr:2d} {L:4.0f} {W:5.0f} {wl:6.1f} "
                  f"{kl * 1e6:7.3f}uA {f['vth_lin']:8.2f} "
                  f"{ks * 1e6:7.3f}uA {f['vth_sat']:8.2f} "
                  f"{kl / ks:8.2f} {f.get('VA', np.nan):7.1f}")

    if rows:
        kl = np.array([r["kp_lin"] for r in rows])
        ks = np.array([r["kp_sat"] for r in rows])
        va = np.array([r["VA"] for r in rows])
        va = va[np.isfinite(va)]
        print()
        print("-" * 78)
        print(f"Kp linear     : median {np.median(kl)*1e6:7.3f} uA/V^2   "
              f"range {kl.min()*1e6:.3f} .. {kl.max()*1e6:.3f}   (n={len(kl)})")
        print(f"Kp saturation : median {np.median(ks)*1e6:7.3f} uA/V^2   "
              f"range {ks.min()*1e6:.3f} .. {ks.max()*1e6:.3f}")
        print(f"ratio lin/sat : median {np.median(kl/ks):7.2f}  "
              f"(>1 means saturation is being suppressed - series resistance)")
        if len(va):
            print(f"Early voltage : median {np.median(np.abs(va)):7.1f} V  "
                  f"-> lambda = {1/np.median(np.abs(va)):.4f} 1/V")
        np.save(os.path.join(os.path.dirname(__file__), "params.npy"),
                np.array(rows, dtype=object), allow_pickle=True)
        print(f"\nsaved {len(rows)} device fits -> docs/extraction/params.npy")


if __name__ == "__main__":
    main()
