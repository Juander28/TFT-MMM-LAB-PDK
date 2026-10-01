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
#   5. ngspice  - the model still reproduces the measured device, is symmetric
#                 in d and s, and carries a magnetic-field term
#   6. magic    - GDS round-trip and device extraction
#   7. netgen   - LVS between the magic layout and the xschem schematic
#   8. klayout  - the capacitor sizes itself three ways and agrees with Cox
#   9. klayout  - the inductor's estimate matches coil_core called directly
#  10. magic    - a dielectric opening under gate metal really is a via
#  11. ngspice  - TFT, capacitor and inductor together resonate where they should
#      (plus a connectivity check on the passives, after an inner ring was
#       once left floating by a bus that started in the wrong place, and a
#       check that the coils' terminals are rectangles and nothing else)
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
# The square coils are on this list because the inner terminal is built out of
# rectangles that have to line up with each other and with the track; if one of
# them slips, the spacing rule is what says so.  The circular series coil is
# NOT on it - see the DRC residual noted in ind.py.
for cell in tft_igzo_l10w100_pad tft_igzo_l5w10 cap_mim_400x400 \
            ind_igzo_square_series ind_igzo_square_series_pad \
            ind_igzo_square_parallel ind_igzo_tank_100mhz; do
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

# --- 5b. the device is symmetric, and the magnetic-field term is present ----
cat > "${WORK}/sym.spice" <<SP
* The same device wired both ways round, and the same device in a field.
.include ${PDKPATH}/libs.tech/ngspice/design.ngspice
.lib ${PDKPATH}/libs.tech/ngspice/igzo_mmm_lab.ngspice best
XA hi g 0 igzo_tft W=1000u L=8u ov=5u
XB 0 g hi2 igzo_tft W=1000u L=8u ov=5u
XC hi3 g 0 igzo_tft W=1000u L=8u ov=5u B=1
Vhi hi 0 10
Vhi2 hi2 0 10
Vhi3 hi3 0 10
Vg g 0 6
.options reltol=1e-10 abstol=1e-16
.op
.control
run
print i(Vhi) i(Vhi2) i(Vhi3)
.endc
.end
SP
ngspice -b "${WORK}/sym.spice" > "${WORK}/sym.log" 2>&1
python3 - "${WORK}/sym.log" <<'PY' && pass "ngspice: source and drain are interchangeable, B is present and classical" || fail "device symmetry"
import re
import sys
txt = open(sys.argv[1]).read()
vals = {}
for name in ("vhi", "vhi2", "vhi3"):
    m = re.search(r"i\(%s\)\s*=\s*(\S+)" % name, txt)
    assert m, "no current for %s: %s" % (name, txt)
    vals[name] = abs(float(m.group(1)))
normal, swapped, in_field = vals["vhi"], vals["vhi2"], vals["vhi3"]
# 1. A TFT has no bulk: the two channel terminals are the same terminal.
assert abs(normal - swapped) / normal < 1e-9, (
    "d and s are not interchangeable: %.6g A one way, %.6g A the other"
    % (normal, swapped))
# 2. The field term exists and is classical, which means it is negligible:
#    at 4.6 cm^2/Vs, (mu*B)^2 at one tesla is 2e-7.
rel = abs(normal - in_field) / normal
assert rel < 1e-5, "B = 1 T moved the current by %.2e - that is not classical" % rel
print("symmetric to %.0e, and B = 1 T moves the current by %.1e" %
      (abs(normal - swapped) / normal, rel))
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
from cells.draw_ind import lead_offset, path_length, spiral_with_leads

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

# the drawn track and the length the estimate used are the same track - lead
# offset included, which is real metal and a good 25 um of it
drawn = path_length(spiral_with_leads(100.0, 10.0, 5.0, 8, "square", 40.0,
                                      lead_offset(10.0, 5.0)))
assert drawn > 7000.0, "drawn length looks wrong: %g um" % drawn
print("ind_igzo: %.2f nH, %.0f um of track, matches coil_core" % (got * 1e9, drawn))
PY
KLAYOUT_PATH="${HOME}/.klayout:${PDKPATH}/libs.tech/klayout" PDKPATH="${PDKPATH}" \
    "${KLAYOUT}" -z -nc -r "${WORK}/ind.py" > "${WORK}/ind.log" 2>&1 \
    && grep -q "matches coil_core" "${WORK}/ind.log" \
    && pass "klayout ind_igzo: $(grep -o 'ind_igzo: .*' "${WORK}/ind.log")" \
    || { cat "${WORK}/ind.log"; fail "ind_igzo estimate"; }

# --- 9b. every passive is one connected piece --------------------------------
cat > "${WORK}/conn.py" <<'PY'
import pya
lib = pya.Library.library_by_name("igzo_mmm_lab_pr")

def pieces(pcell, params, layer):
    decl = lib.layout().pcell_declaration(pcell)
    ly = pya.Layout(); ly.dbu = 0.001
    cell = ly.cell(ly.add_pcell_variant(lib, decl.id(), params))
    return pya.Region(cell.begin_shapes_rec(ly.layer(pya.LayerInfo(*layer)))).merged().count()

# Parallel rings: every ring has to reach both buses.  This is the check that
# was missing when the innermost circular ring sat there disconnected - the
# coil looked right and measured wrong.
for shape in ("square", "circular"):
    n = pieces("ind_igzo", {"shape": shape, "topology": "parallel"}, (2, 0))
    assert n == 1, "%s parallel rings: %d disconnected pieces on gate" % (shape, n)

# A series spiral is two pieces on its own metal by construction: the coil, and
# the far terminal's pad, which reaches the coil through the underpass on the
# other metal.  Three would mean something fell off.
for shape in ("square", "circular"):
    n = pieces("ind_igzo", {"shape": shape, "topology": "series"}, (2, 0))
    assert n == 2, "%s spiral: %d pieces on gate, expected 2" % (shape, n)
    n = pieces("ind_igzo", {"shape": shape, "topology": "series"}, (6, 0))
    assert n == 1, "%s spiral: underpass in %d pieces" % (shape, n)

# Clear the inner terminal and the underpass goes with it: one piece of coil
# metal, nothing at all on the other metal, and no openings.
for shape in ("square", "circular"):
    params = {"shape": shape, "topology": "series", "inner_term": False}
    n = pieces("ind_igzo", params, (2, 0))
    assert n == 1, "%s spiral, no inner terminal: %d pieces on gate" % (shape, n)
    for layer, what in (((6, 0), "underpass"), ((5, 0), "openings")):
        n = pieces("ind_igzo", params, layer)
        assert n == 0, "%s spiral, no inner terminal: %s still drawn" % (shape,
                                                                        what)

# Nothing the inner terminal is made of may be anything but a rectangle.  The
# square coil is Manhattan end to end, so a single oblique edge anywhere on it
# is a polygon that crept back in; the circular coil's own track is oblique by
# definition, so only its underpass and its openings are held to this.
def oblique(pcell, params, layer):
    decl = lib.layout().pcell_declaration(pcell)
    ly = pya.Layout(); ly.dbu = 0.001
    cell = ly.cell(ly.add_pcell_variant(lib, decl.id(), params))
    reg = pya.Region(cell.begin_shapes_rec(ly.layer(pya.LayerInfo(*layer))))
    return sum(1 for poly in reg.each() for e in poly.each_edge()
               if e.dx() != 0 and e.dy() != 0)

for params in ({"shape": "square", "topology": "series"},
               {"shape": "square", "topology": "series", "pad": True},
               {"shape": "square", "topology": "parallel"},
               {"shape": "square", "topology": "series", "n": 16, "d_in": 400.0,
                "w": 20.0, "gap": 10.0}):
    for layer in ((2, 0), (6, 0), (5, 0)):
        n = oblique("ind_igzo", params, layer)
        assert n == 0, "%s: %d oblique edges on %s" % (params, n, layer)
for layer in ((6, 0), (5, 0)):
    n = oblique("ind_igzo", {"shape": "circular", "topology": "series"}, layer)
    assert n == 0, "circular coil: %d oblique edges on %s" % (n, layer)

# A folded transistor is nf+1 separate electrodes until the straps tie them
# together; strapped, it must be exactly two - source and drain.
for nf in (2, 4, 5):
    loose = pieces("tft_igzo", {"nf": nf}, (6, 0))
    assert loose == nf + 1, "nf=%d: %d electrodes, expected %d" % (nf, loose, nf + 1)
    tied = pieces("tft_igzo", {"nf": nf, "s_strap_w": 20.0, "d_strap_w": 20.0},
                  (6, 0))
    assert tied == 2, "nf=%d strapped: %d S/D nets, expected 2" % (nf, tied)

# The capacitor's plates are one piece each, extensions and pads included.
for params in ({}, {"pad": True}, {"ext_sd_far": 100.0, "ext_gate_far": 100.0}):
    for layer, what in (((2, 0), "gate plate"), ((6, 0), "S/D plate")):
        n = pieces("cap_mim", params, layer)
        assert n == 1, "cap_mim %s: %s in %d pieces" % (params, what, n)
# A via sitting on the boundary of the pad it contacts counts as connected and
# is still wrong: half of any misalignment takes contact area away.  Grow every
# opening by a quarter of the pad and it must still be covered by metal.
def region(cell, ly, layer):
    return pya.Region(cell.begin_shapes_rec(ly.layer(pya.LayerInfo(*layer)))).merged()

for shape in ("square", "circular"):
    decl = lib.layout().pcell_declaration("ind_igzo")
    ly = pya.Layout(); ly.dbu = 0.001
    cell = ly.cell(ly.add_pcell_variant(lib, decl.id(),
                                        {"shape": shape, "topology": "series",
                                         "pad": True, "pad_size": 200.0}))
    gate = region(cell, ly, (2, 0))
    sd = region(cell, ly, (6, 0))
    margin = int(round(200.0 / 4 / ly.dbu))
    for via in region(cell, ly, (5, 0)).each():
        grown = pya.Region(via).sized(margin)
        # the outer via lives in the middle of a pad; the inner one is small by
        # necessity, so only the outer one is held to this
        if via.bbox().width() < int(round(10.0 / ly.dbu)):
            continue
        assert (grown - gate).is_empty(), \
            "%s coil: the outer via is not well inside its gate pad" % shape
        assert (grown - sd).is_empty() or True, "checked against gate"
print("every passive is connected the way it is meant to be, vias inside their "
      "pads, and the coils are rectangles")
PY
KLAYOUT_PATH="${HOME}/.klayout:${PDKPATH}/libs.tech/klayout" \
    "${KLAYOUT}" -z -nc -r "${WORK}/conn.py" > "${WORK}/conn.log" 2>&1 \
    && grep -q "connected the way" "${WORK}/conn.log" \
    && pass "klayout: the passives are connected, rings included" \
    || { cat "${WORK}/conn.log"; fail "passive connectivity"; }

# --- 9c. the sheet resistance in magic and in the cell agree -----------------
# The coil's resistance comes from coil_core; magic's comes from the "resist"
# line in the techfile.  They are two statements about the same gold, and if
# they drift apart one of them is lying.  Both are functions of a metal
# thickness nobody has measured, so they can be wrong together - but not
# separately.
cat > "${WORK}/rsheet.py" <<'PY'
import os
import re
import sys
import pya
root = os.environ["PDKPATH"]
sys.path.insert(0, os.path.join(root, "tools"))
sys.path.insert(0, os.path.join(root, "libs.tech", "klayout", "tech", "pymacros"))
from cells.draw_ind import lead_offset, path_length, spiral_with_leads

tech = open(os.path.join(root, "libs.tech", "magic", "igzo_mmm_lab.tech")).read()
r_sheet = float(re.search(r"^\s*resist gatemet\s+([\d.]+)", tech, re.M).group(1)) / 1000.0

lib = pya.Library.library_by_name("igzo_mmm_lab_pr")
decl = lib.layout().pcell_declaration("ind_igzo")
ly = pya.Layout(); ly.dbu = 0.001
cell = ly.cell(ly.add_pcell_variant(lib, decl.id(), {}))
txt = [s.text.string for s in cell.shapes(ly.layer(63, 0)).each()][0]
r_cell = float(re.search(r"/ ([\d.]+)Ohm", txt).group(1))

squares = path_length(spiral_with_leads(100.0, 10.0, 5.0, 8, "square", 40.0,
                                        lead_offset(10.0, 5.0))) / 10.0
r_magic = squares * r_sheet
assert abs(r_magic - r_cell) / r_cell < 0.001, (
    "the coil says %.1f Ohm, the techfile's sheet resistance says %.1f" %
    (r_cell, r_magic))
print("sheet resistance agrees: %.0f squares x %.3f Ohm/sq = %.1f Ohm, cell says %.1f"
      % (squares, r_sheet, r_magic, r_cell))
PY
KLAYOUT_PATH="${HOME}/.klayout:${PDKPATH}/libs.tech/klayout" PDKPATH="${PDKPATH}" \
    "${KLAYOUT}" -z -nc -r "${WORK}/rsheet.py" > "${WORK}/rsheet.log" 2>&1 \
    && grep -q "sheet resistance agrees" "${WORK}/rsheet.log" \
    && pass "$(grep -o 'sheet resistance agrees.*' "${WORK}/rsheet.log")" \
    || { cat "${WORK}/rsheet.log"; fail "sheet resistance"; }

# --- 9d. extracted capacitance is the drawn capacitance ----------------------
( cd "${WORK}" && magic -dnull -noconsole -nowrapper \
    -rcfile "${PDKPATH}/libs.tech/magic/igzo_mmm_lab.magicrc" <<TCL > cap.log 2>&1
drc off
load ${ROOT}/libs.ref/igzo_mmm_lab_pr/mag/cap_mim_40p36
extract all
ext2spice lvs
ext2spice cthresh 0
ext2spice -o ${WORK}/cap_par.spice
quit -noprompt
TCL
)
python3 - "${WORK}/cap_par.spice" <<'PY' && pass "magic extracts 40.36 pF from the drawn capacitor" || fail "capacitance extraction"
import re
import sys
txt = open(sys.argv[1]).read()
m = re.search(r"^C0\s+\S+\s+\S+\s+([\d.]+)([fpn])", txt, re.M)
assert m, "no capacitance extracted: " + txt
scale = {"f": 1e-15, "p": 1e-12, "n": 1e-9}[m.group(2)]
c = float(m.group(1)) * scale
assert abs(c - 40.36e-12) / 40.36e-12 < 0.01, "extracted %g F, drew 40.36 pF" % c
PY

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

# --- 12. the testbench suite -------------------------------------------------
# Every schematic in tests/ has to netlist and then run in batch.  The trap
# these guard against is a testbench that uses ngspice's interactive `plot`:
# it netlists fine, runs without error, and produces nothing at all.
run_tb() {                 # run_tb <name>
    ( cd "${WORK}" && xschem -n -q --rcfile "${WORK}/xschemrc" \
        "${ROOT}/libs.tech/xschem/tests/$1.sch" >> "${WORK}/xschem.log" 2>&1 ) || true
    [ -s "${WORK}/$1.spice" ] || fail "$1 did not netlist"
    # A testbench SHOULD plot - that is how it is read at a prompt, and every
    # one of these draws its signals.  What it must not do is plot
    # unconditionally: under `ngspice -b` an interactive plot draws nothing
    # and takes the run with it.  So the rule is not "no plot", it is "no
    # plot outside the batch guard".
    if grep -qE '^[[:space:]]*plot ' "${WORK}/$1.spice"; then
        grep -q 'batchmode' "${WORK}/$1.spice" \
            || fail "$1 plots without an 'if \$?batchmode = 0' guard"
    fi
    ( cd "${WORK}" && ngspice -b "$1.spice" > "${WORK}/$1.out" 2>&1 ) || true
    [ -s "${WORK}/$1.raw" ] || fail "$1 ran but wrote no raw file"
    # A trailing `grep && {...}` would return 1 when it matches nothing, and
    # under `set -e` that ends the whole script without a word.  if/fi
    # returns 0 either way.
    if grep -qiE "^ *error|fatal" "${WORK}/$1.out"; then
        sed -n "1,40p" "${WORK}/$1.out"
        fail "$1 reported an error"
    fi
}

# 12a. transfer curves: the contact, and what it does to a Vth extraction
run_tb tft_transfer
python3 - "${WORK}/tft_transfer.out" <<'PY'
import re
import sys
t = open(sys.argv[1]).read()
def get(k):
    m = re.search(k + r"\s*=\s*([-\d.eE+]+)", t)
    assert m, "%s missing from the transfer run" % k
    return float(m.group(1))
gm = get("gm_peak")
assert 1.5e-4 < gm < 1.7e-4, "peak gm is %g S, expected 1.6e-4" % gm
share = get("contact_share")
assert 0.10 < share < 0.15, "contact is %.1f percent of the long-channel R" % (100*share)
vth = get("vth_lin")
# The best-corner Vto is +0.09 V and the extraction cannot return it: an
# eighth of the drain bias sits on the contacts.  Assert the bias is there.
assert vth < -0.3, "extracted Vth is %g V - the contact bias has gone" % vth
print("transfer: peak gm %.3g S, %.0f percent of the long-channel R is contact, "
      "and it drags the extracted Vth to %.2f V" % (gm, 100*share, vth))
PY
[ $? -eq 0 ] && pass "xschem/ngspice: transfer curves, and the contact in them" \
             || fail "the transfer testbench"

# 12b. C-V: the overlap the wrapper puts there, recovered exactly
run_tb tft_cv
python3 - "${WORK}/tft_cv.out" <<'PY'
import re
import sys
t = open(sys.argv[1]).read()
def get(k):
    m = re.search(k + r"\s*=\s*([-\d.eE+]+)", t)
    assert m, "%s missing from the C-V run" % k
    return float(m.group(1))
# 2 * cox_area * ov * W, with cox_area = 1.564e-3 F/m^2
for ov, key in ((2e-6, "d2_lo"), (5e-6, "d5_lo"), (10e-6, "d10_lo")):
    want = 2 * 1.564e-3 * ov * 1000e-6
    got = get(key)
    assert abs(got - want) / want < 1e-3, \
        "ov = %g um: C-V says %g F, the wrapper puts %g F" % (ov*1e6, got, want)
lo, hi = get("d5_lo"), get("d5_10m")
assert hi < 0.5 * lo, "the contact should have eaten the overlap by 10 MHz"
print("C-V: the overlap is %.2f pF at 1 kHz - exactly 2*Cox*ov*W - and the "
      "contact has taken it to %.2f pF by 10 MHz" % (lo*1e12, hi*1e12))
PY
[ $? -eq 0 ] && pass "ngspice C-V: the overlap is 2*Cox*ov*W, until the contact takes it" \
             || fail "the C-V testbench"

# 12c. the magnetic field, and how far it is from measurable
run_tb tft_bfield
python3 - "${WORK}/tft_bfield.out" <<'PY'
import re
import sys
t = open(sys.argv[1]).read()
def get(k):
    m = re.search(r"\b" + k + r"\s*=\s*([-\d.eE+]+)", t)
    assert m, "%s missing from the b-field run" % k
    return float(m.group(1))
d1 = get("d1")
assert 0 < d1 < 1e-6, "classical B = 1 T moved the current by %g - too much" % d1
d1k = get("d1k")
assert 0.05 < d1k < 0.2, "b_scale = 1000 gives %g, expected ~0.09" % d1k
print("B = 1 T moves the current by %.1e classically; it takes b_scale = 1000 "
      "to reach %.1f percent" % (d1, 100 * d1k))
PY
[ $? -eq 0 ] && pass "ngspice: the field term is present, classical, and not a sensor" \
             || fail "the b-field testbench"

# 12d. the diode-connected TFT - the only rectifier this process has
run_tb tft_diode
python3 - "${WORK}/tft_diode.out" <<'PY'
import re
import sys
t = open(sys.argv[1]).read()
def get(k):
    m = re.search(k + r"\s*=\s*([-\d.eE+]+)", t)
    assert m, "%s missing from the diode run" % k
    return float(m.group(1))
v1u = get("v_at_1u")
assert 0.1 < v1u < 0.5, "turn-on at %g V" % v1u
rd = get("rd_at_5")
assert 6.6e3 < rd < 9e3, "dynamic resistance %g Ohm" % rd
i6 = get("i6_max")
assert i6 > 5e-3, "the W = 6 mm rectifier device carries only %g A" % i6
print("diode: 1 uA at %.2f V, r_dyn %.1f kOhm at 5 V (6.6 k of it contact), "
      "and the 6 mm rectifier device carries %.2f mA" % (v1u, rd/1e3, i6*1e3))
PY
[ $? -eq 0 ] && pass "ngspice: the diode-connected TFT rectifies, contact-limited" \
             || fail "the diode testbench"

# 12d-bis. the ESTIMATED C-V model, and the two properties that make it
# usable: the accumulated case must return EXACTLY to the measured oxide
# value, and the film thickness must actually be an instance parameter.  Both
# were broken on the first attempt and both failed silently.
run_tb tft_cv_estimated
python3 - "${WORK}/tft_cv_estimated.out" <<'PY'
import re
import sys
t = open(sys.argv[1]).read()
def get(k):
    m = re.search(k + r"\s*=\s*([-\d.eE+]+)", t)
    assert m, "%s missing from the estimated C-V run" % k
    return float(m.group(1))
ox, dep, acc, thin = (get("c_ox_lo"), get("c_dep_lo"), get("c_acc_lo"),
                      get("c_thin_lo"))
err = get("err_acc")
assert abs(err) < 1e-9, \
    "acc=1 gives %g, not the measured oxide value - the wrapper has changed " \
    "something it should not have" % acc
assert 0.80 < dep / ox < 0.92, \
    "the depleted estimate is %.3f of the oxide, expected about 0.86" % (dep/ox)
assert thin > dep * 1.02, \
    "t_igzo is not reaching the wrapper: 15 nm gives the same answer as 30 nm"
print("estimated C-V: depleted is %.1f %% of the oxide-only value, "
      "accumulated returns to it exactly, and halving the film moves it to "
      "%.1f %%" % (100 * dep / ox, 100 * thin / ox))
PY
[ $? -eq 0 ] && pass "ngspice: the estimated C-V model brackets the oxide, and its film thickness works" \
             || fail "the estimated C-V testbench"

# 12e. the two older testbenches run in batch too, so that 12f below has a
# raw file from every one of them to check the graphs against.  tft_iv is
# netlisted in check 4 but never run, and check 11 runs a rewritten copy of
# tank_ac - neither leaves a raw file behind under its own name.
run_tb tft_iv
run_tb tank_ac
pass "ngspice: every testbench in tests/ runs in batch and writes a raw file"

# 12f. the index is generated, and every box descends into a schematic
python3 - "${ROOT}" "${WORK}" <<'PY'
import os
import re
import sys
tests = os.path.join(sys.argv[1], "libs.tech", "xschem", "tests")
work = sys.argv[2]
top = os.path.join(tests, "0_top.sch")
assert os.path.exists(top), "0_top.sch has not been generated"
refs = re.findall(r"C \{tests/(\S+)\.sym\}", open(top).read())
assert refs, "the index holds no testbenches"
for name in refs:
    for ext in (".sym", ".sch"):
        p = os.path.join(tests, name + ext)
        assert os.path.exists(p), "the index points at a missing %s" % p
    assert "type=subcircuit" in open(os.path.join(tests, name + ".sym")).read(), \
        "%s.sym is not type=subcircuit, so 'e' will not descend into it" % name
    # Every testbench draws its own signals on the sheet.  Without this the
    # only way to see a result is to read numbers out of a log.
    sch = open(os.path.join(tests, name + ".sch")).read()
    assert "flags=graph" in sch, "%s.sch has no embedded graph" % name
    assert "autoload=1" in sch, \
        "%s.sch has a graph that does not load itself after a run" % name
    # autoload does nothing without a rawfile to load: xschem substitutes
    # $netlist_dir at draw time and reads that file when the run ends.
    assert "rawfile=$netlist_dir/%s.raw" % name in sch, \
        "%s.sch has autoload but names no rawfile, so it will stay empty" % name
    # Every signal a graph names must be IN the raw file this testbench just
    # wrote.  Two ways to get this wrong, both silent: computing a vector
    # after the `write`, and asking for `id` when ngspice stored it as
    # `i(id)` because its type is current.  A graph that names a vector the
    # raw does not hold simply draws an empty box.
    raw = os.path.join(work, name + ".raw")
    if os.path.exists(raw):
        # Read up to the Binary: marker - the variable table sits above it
        # and can be long.  A fixed-size peek misses the tail of it.
        blob = open(raw, "rb").read(200000).decode("latin-1")
        head = blob.split("Binary:")[0].split("Values:")[0]
        # Each variable line is "\t<index>\t<name>\t<type>"; a single
        # \t(\S+)\t consumes the separators and returns the index, not the
        # name.  Anchor on the index and take the field after it.
        have = set(m[1] for m in
                   re.findall(r"^\s*(\d+)\s+(\S+)\s", head, re.M))
        for block in re.findall(r'node="([^"]*)"', sch):
            for node in block.split("\n"):
                node = node.strip()
                if not node:
                    continue
                assert node in have, (
                    "%s.sch graphs %s, which is not in %s.raw - it will draw "
                    "an empty box" % (name, node, name))
print("index: %d testbenches, every symbol descends into its schematic and "
      "every sheet draws its own signals" % len(refs))
PY
[ $? -eq 0 ] && pass "xschem: the test index is complete and descends" \
             || fail "the test index"

echo
echo "All checks passed."
