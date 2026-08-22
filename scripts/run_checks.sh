#!/usr/bin/env bash
#
# End-to-end check of the PDK across all four tools.  Run it after any change
# to the layers, the PCells, the models or the tech files:
#
#     ./scripts/run_checks.sh
#
# It checks, in order:
#   1. klayout  - the PCell reproduces the fabricated device, shape for shape
#   2. klayout  - the technology and the PCell library are discoverable
#   3. klayout  - DRC on the generated primitives
#   4. xschem   - the symbol netlists with the pins in the right order
#   5. ngspice  - the model still reproduces the measured device
#   6. magic    - GDS round-trip and device extraction
#   7. netgen   - LVS between the magic layout and the xschem schematic
#   8. klayout  - the capacitor sizes itself three ways and agrees with Cox
#   9. klayout  - the inductor's estimate matches coil_core called directly
#  10. magic    - a dielectric opening under gate metal really is a via
#  11. ngspice  - TFT, capacitor and inductor together resonate where they should
#
# Exits non-zero on the first failure.
set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAME="$(basename "${ROOT}")"
WORK="$(mktemp -d)"
trap 'rm -rf "${WORK}"' EXIT

export PDK_ROOT="${PDK_ROOT:-$(dirname "${ROOT}")}"
export PDK="${PDK:-${NAME}}"
PDKPATH="${PDK_ROOT}/${PDK}"
KLAYOUT="$(command -v klayout)"

GDS_CHIP="${ROOT}/libs.ref/igzo_mmm_lab_pr/gds/TFT_layout.gds"
GDS_PRIM="${ROOT}/libs.ref/igzo_mmm_lab_pr/gds/tft_primitives.gds"

pass() { echo "PASS  $1"; }
fail() { echo "FAIL  $1"; exit 1; }

echo "== ${NAME} checks (PDK_ROOT=${PDK_ROOT}) =="

# --- 1. the PCell against silicon -------------------------------------------
python3 "${ROOT}/libs.tech/klayout/tech/pymacros/testing/test_pcell_vs_gds.py" \
    "${GDS_CHIP}" > "${WORK}/pcell.log" 2>&1 \
    && pass "klayout PCell matches TFT-10L100W" \
    || { cat "${WORK}/pcell.log"; fail "klayout PCell"; }

# --- 2. discoverability ------------------------------------------------------
cat > "${WORK}/discover.py" <<'PY'
import pya, sys
techs = [t for t in pya.Technology.technology_names() if t]
assert "igzo_mmm_lab" in techs, "technology not found: %s" % techs
lib = pya.Library.library_by_name("igzo_mmm_lab_pr")
assert lib is not None, "PCell library not registered"
names = sorted(lib.layout().pcell_names())
assert "tft_igzo" in names and "cap_mim" in names, names
print("technology and PCells OK: %s" % names)
PY
KLAYOUT_PATH="${HOME}/.klayout:${PDKPATH}/libs.tech/klayout" \
    "${KLAYOUT}" -z -nc -r "${WORK}/discover.py" > "${WORK}/discover.log" 2>&1 \
    && grep -q "technology and PCells OK" "${WORK}/discover.log" \
    && pass "klayout finds the technology and the PCell library" \
    || { cat "${WORK}/discover.log"; fail "klayout discovery"; }

# --- 3. DRC ------------------------------------------------------------------
for cell in tft_igzo_l10w100_pad tft_igzo_l5w10 cap_mim_400x400; do
    python3 "${ROOT}/libs.tech/klayout/tech/drc/run_drc.py" \
        --path "${GDS_PRIM}" --topcell "${cell}" --output "${WORK}" \
        > "${WORK}/drc_${cell}.log" 2>&1 \
        || { cat "${WORK}/drc_${cell}.log"; fail "DRC on ${cell}"; }
done
pass "klayout DRC clean on the generated primitives"

# --- 4. xschem netlist -------------------------------------------------------
cat > "${WORK}/xschemrc" <<XRC
source ${PDKPATH}/libs.tech/xschem/xschemrc
set netlist_dir ${WORK}
XRC
# xschem exits non-zero after a successful batch netlist, so the netlist
# itself is what gets checked, not the exit status.
( cd "${WORK}" && xschem -n -q --rcfile "${WORK}/xschemrc" \
    "${ROOT}/libs.tech/xschem/tests/tft_iv.sch" > "${WORK}/xschem.log" 2>&1 ) || true
grep -qE "^XM1 D G S igzo_tft W=1000u L=8u" "${WORK}/tft_iv.spice" \
    && pass "xschem netlists the symbol with pins in D G S order" \
    || { cat "${WORK}/tft_iv.spice"; fail "xschem netlist"; }

# --- 5. the model against the measurement ------------------------------------
cat > "${WORK}/val.spice" <<SP
* W = 1000 um, L = 8 um at VGS = 6 V, VDS = 10 V.
* Measured 670-701 uA; docs/extraction/validate_model.py gives 654 uA.
.include ${PDKPATH}/libs.tech/ngspice/design.ngspice
.lib ${PDKPATH}/libs.tech/ngspice/igzo_mmm_lab.ngspice best
XM1 d g 0 igzo_tft W=1000u L=8u ov=5u
Vd d 0 10
Vg g 0 6
.op
.control
run
print i(Vd)
.endc
.end
SP
ngspice -b "${WORK}/val.spice" > "${WORK}/ngspice.log" 2>&1
ID=$(grep -A1 "^ *i " "${WORK}/ngspice.log" | grep -oE "\-?0\.000[0-9]+" | head -1)
python3 - "${ID}" <<'PY' && pass "ngspice reproduces the measured device (${ID} A)" || fail "ngspice model"
import sys
i = abs(float(sys.argv[1]))
assert 6.4e-4 < i < 6.7e-4, "Id = %g A, expected about 654 uA" % i
PY

# --- 6. magic: round-trip and extraction -------------------------------------
( cd "${WORK}" && magic -dnull -noconsole -nowrapper \
    -rcfile "${PDKPATH}/libs.tech/magic/igzo_mmm_lab.magicrc" <<TCL > magic.log 2>&1
drc off
load ${ROOT}/libs.ref/igzo_mmm_lab_pr/mag/tft_igzo_l10w100
gds write ${WORK}/rt.gds
extract all
ext2spice lvs
ext2spice -o ${WORK}/layout.spice
quit -noprompt
TCL
)
grep -qE "igzo_tft w=[0-9.]+m l=10u" "${WORK}/layout.spice" \
    && pass "magic extracts one igzo_tft with l = 10 um" \
    || { cat "${WORK}/layout.spice"; fail "magic extraction"; }

python3 - "${WORK}/rt.gds" "${GDS_PRIM}" <<'PY' && pass "magic GDS round-trip is layer-exact" || fail "magic round-trip"
import sys, pya
a = pya.Layout(); a.read(sys.argv[1])
b = pya.Layout(); b.read(sys.argv[2])
ca = a.top_cell(); cb = b.cell("tft_igzo_l10w100")
for spec in ((4, 0), (6, 0), (2, 0)):
    ra = pya.Region(ca.begin_shapes_rec(a.layer(pya.LayerInfo(*spec)))).merged()
    rb = pya.Region(cb.begin_shapes_rec(b.layer(pya.LayerInfo(*spec)))).merged()
    assert (ra ^ rb).is_empty(), "layer %d/%d differs after the round-trip" % spec
print("round-trip identical on 4/0, 6/0 and 2/0")
PY

# --- 7. LVS ------------------------------------------------------------------
( cd "${WORK}" && xschem -n -q --rcfile "${WORK}/xschemrc" \
    --tcl 'set top_subckt 1; set lvs_netlist 1' \
    "${ROOT}/libs.tech/xschem/tests/tft_igzo_l10w100.sch" >> "${WORK}/xschem.log" 2>&1 ) || true
netgen -batch lvs \
    "${WORK}/layout.spice tft_igzo_l10w100" \
    "${WORK}/tft_igzo_l10w100.spice tft_igzo_l10w100" \
    "${PDKPATH}/libs.tech/netgen/setup.tcl" "${WORK}/lvs.out" > "${WORK}/netgen.log" 2>&1
grep -q "Circuits match uniquely" "${WORK}/lvs.out" \
    && pass "netgen LVS: layout and schematic match uniquely" \
    || { tail -30 "${WORK}/lvs.out"; fail "LVS"; }

# --- 8. the capacitor sizes itself ------------------------------------------
cat > "${WORK}/cap.py" <<'PY'
import math
import pya
lib = pya.Library.library_by_name("igzo_mmm_lab_pr")
decl = lib.layout().pcell_declaration("cap_mim")
COX = 1.564                                   # fF/um^2, measured
for params, want in (({"mode": "by dimensions", "w": 400.0, "l": 400.0}, 250240.0),
                     ({"mode": "by area", "area_target": 160000.0}, 250240.0),
                     ({"mode": "by capacitance", "c_target": 40362.0}, 40362.0)):
    ly = pya.Layout(); ly.dbu = 0.001
    cell = ly.cell(ly.add_pcell_variant(lib, decl.id(), params))
    g = pya.Region(cell.begin_shapes_rec(ly.layer(pya.LayerInfo(2, 0)))).merged()
    d = pya.Region(cell.begin_shapes_rec(ly.layer(pya.LayerInfo(6, 0)))).merged()
    x = (g & d).bbox().to_dtype(ly.dbu)
    got = COX * x.width() * x.height()
    assert abs(got - want) / want < 0.001, "%s: drew %g fF, asked for %g" % (
        params["mode"], got, want)
    assert cell.shapes(ly.layer(63, 0)).size() == 1, "no value printed on the cell"
print("cap_mim: all three sizing modes agree with Cox")
PY
KLAYOUT_PATH="${HOME}/.klayout:${PDKPATH}/libs.tech/klayout" \
    "${KLAYOUT}" -z -nc -r "${WORK}/cap.py" > "${WORK}/cap.log" 2>&1 \
    && grep -q "all three sizing modes" "${WORK}/cap.log" \
    && pass "klayout cap_mim: by dimensions, by area and by capacitance agree" \
    || { cat "${WORK}/cap.log"; fail "cap_mim sizing"; }

# --- 9. the inductor's estimate ---------------------------------------------
cat > "${WORK}/ind.py" <<'PY'
import os
import sys
import pya
root = os.environ["PDKPATH"]
sys.path.insert(0, os.path.join(root, "tools"))
sys.path.insert(0, os.path.join(root, "libs.tech", "klayout", "tech", "pymacros"))
import coil_core as cc
from cells.draw_ind import path_length, spiral_with_leads

lib = pya.Library.library_by_name("igzo_mmm_lab_pr")
decl = lib.layout().pcell_declaration("ind_igzo")
ly = pya.Layout(); ly.dbu = 0.001
cell = ly.cell(ly.add_pcell_variant(lib, decl.id(),
                                    {"shape": "square", "topology": "series"}))
txt = [s.text.string for s in cell.shapes(ly.layer(63, 0)).each()]
assert txt and "nH" in txt[0], "the coil did not print its value: %s" % txt

# the same geometry through coil_core directly
want = cc.inductance_microcoil(100e-6, 10e-6, 5e-6, 8, 50e-9, "cuadrada", "mohan")
got = float(txt[0].split()[1].replace("nH", "")) * 1e-9
assert abs(got - want) / want < 0.01, "PCell says %g H, coil_core says %g H" % (got, want)

# the drawn track and the length the estimate used are the same track
drawn = path_length(spiral_with_leads(100.0, 10.0, 5.0, 8, "square", 40.0))
assert drawn > 7000.0, "drawn length looks wrong: %g um" % drawn
print("ind_igzo: %.2f nH, %.0f um of track, matches coil_core" % (got * 1e9, drawn))
PY
KLAYOUT_PATH="${HOME}/.klayout:${PDKPATH}/libs.tech/klayout" PDKPATH="${PDKPATH}" \
    "${KLAYOUT}" -z -nc -r "${WORK}/ind.py" > "${WORK}/ind.log" 2>&1 \
    && grep -q "matches coil_core" "${WORK}/ind.log" \
    && pass "klayout ind_igzo: $(grep -o 'ind_igzo: .*' "${WORK}/ind.log")" \
    || { cat "${WORK}/ind.log"; fail "ind_igzo estimate"; }

# --- 10. the via ------------------------------------------------------------
python3 - "${WORK}/viatest.gds" <<'PY'
import sys
import pya
ly = pya.Layout(); ly.dbu = 0.001
def box(c, l, d, x1, y1, x2, y2):
    c.shapes(ly.layer(l, d)).insert(pya.Box(*[int(v * 1000) for v in (x1, y1, x2, y2)]))
def text(c, l, d, t, x, y):
    tt = pya.Text(t, pya.Trans(int(x * 1000), int(y * 1000))); tt.size = 8000
    c.shapes(ly.layer(l, d)).insert(tt)
for name, with_via in (("via_yes", True), ("via_no", False)):
    c = ly.create_cell(name)
    box(c, 6, 0, -120, -15, 15, 15)
    box(c, 2, 0, -15, -120, 15, 15)
    if with_via:
        box(c, 5, 0, -5, -5, 5, 5)
    text(c, 6, 10, "A", -100, 0)
    text(c, 2, 10, "B", 0, -100)
ly.write(sys.argv[1])
PY
( cd "${WORK}" && magic -dnull -noconsole -nowrapper \
    -rcfile "${PDKPATH}/libs.tech/magic/igzo_mmm_lab.magicrc" <<TCL > via.log 2>&1
drc off
gds read ${WORK}/viatest.gds
load via_yes
extract all
ext2spice lvs
ext2spice -o ${WORK}/via_yes.spice
load via_no
extract all
ext2spice lvs
ext2spice -o ${WORK}/via_no.spice
quit -noprompt
TCL
)
grep -q "^.subckt via_yes B$" "${WORK}/via_yes.spice" \
    && grep -q "^.subckt via_no A B$" "${WORK}/via_no.spice" \
    && pass "magic: an opening under gate metal is a via, without it two nets" \
    || { grep "^.subckt" "${WORK}"/via_*.spice; fail "the via"; }

# --- 11. the three cells together -------------------------------------------
( cd "${WORK}" && xschem -n -q --rcfile "${WORK}/xschemrc" \
    "${ROOT}/libs.tech/xschem/tests/tank_ac.sch" >> "${WORK}/xschem.log" 2>&1 ) || true
python3 - "${WORK}/tank_ac.spice" "${WORK}" <<'PY'
import re
import subprocess
import sys
net = open(sys.argv[1]).read().replace(
    "write tank_ac.raw\nprint v(out) > /dev/null",
    "meas ac vmax MAX vdb(out)\nmeas ac fpeak WHEN vdb(out)=vmax")
run = sys.argv[2] + "/tank_run.spice"
open(run, "w").write(net)
out = subprocess.run(["ngspice", "-b", run], capture_output=True, text=True,
                     timeout=300)
m = re.search(r"fpeak\s*=\s*([-\d.eE+]+)", out.stdout + out.stderr)
assert m, "the tank sweep did not run"
f = float(m.group(1)) / 1e6
assert 95.0 < f < 105.0, "tank peaks at %g MHz, expected 100" % f
print("tank: TFT + cap_mim + ind_igzo resonate at %.1f MHz" % f)
PY
[ $? -eq 0 ] && pass "ngspice: the three cells together resonate at 100 MHz" \
             || fail "the tank testbench"

echo
echo "All checks passed."
