#!/usr/bin/env python3
"""
Can a measured IGZO TFT deliver the transconductance the resonator needs?

The required gm is set by the TANK, not by the device: Q-enhancement cancels the
tank loss when gm*Rp/2 = 1, so the verified two-channel design point fixes a
hard gm target.  Back-calculated from the verified netlist parameters
(Kp = 1 mA/V^2, W/L = 1, gm = sqrt(2*Kp*(W/L)*Itail/2)):

    channel A (55.89 MHz):  Itail = 4.07509 mA  ->  gm = 2.019 mS
    channel B (100.00 MHz): Itail = 0.65260 mA  ->  gm = 0.808 mS

This script asks, for the measured Kp: what (W/L, I_D) reaches that gm, and does
the answer fit the 150 x 150 um footprint and the 100 uW/channel power budget?
"""

import numpy as np

VDD = 1.5
GM_REQ = {"A (55.89 MHz)": 2.019e-3, "B (100.00 MHz)": 0.808e-3}

# measured Kp (A/V^2), from tft/extract_params.py
KP = {
    "assumed NMOSGEN":            1000e-6,
    "TFT1 long-channel (L>=40)":    0.70e-6,
    "TFT1 median all L":            0.52e-6,
    "TFT1 short-channel (L=8)":     0.12e-6,
    "TFT2 (worst chip)":            0.20e-6,
}

FOOTPRINT = 150.0 * 150.0        # um^2, one channel
PAIR_FRACTION = 0.5              # half the cell for the cross-coupled pair
L_MIN = 8.0                      # um, smallest channel length measured
P_BUDGET = 100e-6                # W per channel


def wl_max(L=L_MIN, frac=PAIR_FRACTION):
    """Largest W/L for a 2-transistor pair inside the area budget."""
    area_pair = FOOTPRINT * frac
    W = area_pair / (2.0 * L)
    return W / L, W


def main():
    wlmax, wmax = wl_max()
    print("=" * 78)
    print("REQUIRED gm vs WHAT THE MEASURED DEVICES CAN GIVE")
    print("=" * 78)
    print(f"footprint {FOOTPRINT:.0f} um^2/channel, {PAIR_FRACTION:.0%} to the pair, "
          f"L = {L_MIN:.0f} um (smallest measured)")
    print(f"  -> W_max = {wmax:.0f} um per device,  (W/L)_max = {wlmax:.0f}")
    print(f"power budget {P_BUDGET*1e6:.0f} uW at VDD = {VDD} V "
          f"-> Itail_max = {P_BUDGET/VDD*1e6:.1f} uA  (I_D = {P_BUDGET/VDD/2*1e6:.1f} uA)")
    print()

    id_budget = P_BUDGET / VDD / 2.0

    for label, gm_req in GM_REQ.items():
        print("-" * 78)
        print(f"CHANNEL {label}:  gm required = {gm_req*1e3:.3f} mS")
        print(f"{'Kp source':28} {'W/L needed':>11} {'W @L=8um':>11} "
              f"{'I_D needed':>11} {'P/channel':>11} {'verdict':>9}")
        for name, kp in KP.items():
            # (1) at the area limit, what I_D reaches gm_req?
            id_need = gm_req ** 2 / (2 * kp * wlmax)
            p_need = id_need * 2 * VDD
            # (2) at the power limit, what W/L reaches gm_req?
            wl_need = gm_req ** 2 / (2 * kp * id_budget)
            w_need = wl_need * L_MIN
            ok = (id_need * 2 * VDD <= P_BUDGET)
            print(f"{name:28} {wl_need:11.0f} {w_need:10.0f}u "
                  f"{id_need*1e3:10.3f}m {p_need*1e3:10.2f}m "
                  f"{'OK' if ok else 'FAIL':>9}")
        print()

    print("=" * 78)
    print("MINIMUM Kp TO CLOSE THE DESIGN (both constraints at once)")
    print("=" * 78)
    print(f"{'channel':18} {'Kp_min [uA/V^2]':>16} {'vs TFT1 long-ch':>17} "
          f"{'vs assumed':>12}")
    kp_best = KP["TFT1 long-channel (L>=40)"]
    for label, gm_req in GM_REQ.items():
        kp_min = gm_req ** 2 / (2 * wlmax * id_budget)
        print(f"{label:18} {kp_min*1e6:16.1f} {kp_min/kp_best:16.0f}x "
              f"{kp_min/1000e-6:11.1f}x")

    print()
    print("=" * 78)
    print("WHAT THE MEASURED DEVICE ACTUALLY REACHES (area + power both honoured)")
    print("=" * 78)
    print(f"{'Kp source':28} {'gm_max':>10} {'vs ch A':>9} {'vs ch B':>9} "
          f"{'Q_enh factor':>13}")
    for name, kp in KP.items():
        gm_max = np.sqrt(2 * kp * wlmax * id_budget)
        print(f"{name:28} {gm_max*1e6:8.1f}uS {gm_max/GM_REQ['A (55.89 MHz)']:8.4f} "
              f"{gm_max/GM_REQ['B (100.00 MHz)']:8.4f} "
              f"{1/(1-min(gm_max/GM_REQ['B (100.00 MHz)'], 0.999)):12.2f}x")
    print()
    print("Q_enh factor = 1/(1 - gm/gm_req): the multiplier applied to the bare")
    print("tank Q0.  Reaching QL >= 1667 from Q0 ~ 31 needs a factor of ~54.")


if __name__ == "__main__":
    main()
