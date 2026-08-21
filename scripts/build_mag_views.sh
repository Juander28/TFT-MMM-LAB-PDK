#!/usr/bin/env bash
# Generate the magic views in libs.ref/igzo_mmm_lab_pr/mag from the GDS that
# scripts/build_libs_ref.py writes.  Run it after that script; never edit the
# .mag files by hand, or they will drift away from the PCells.
set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GDS="${ROOT}/libs.ref/igzo_mmm_lab_pr/gds/tft_primitives.gds"
MAG="${ROOT}/libs.ref/igzo_mmm_lab_pr/mag"
RC="${ROOT}/libs.tech/magic/igzo_mmm_lab.magicrc"

[ -f "${GDS}" ] || { echo "run scripts/build_libs_ref.py first" >&2; exit 1; }
mkdir -p "${MAG}"

cd "${MAG}"
magic -dnull -noconsole -nowrapper -rcfile "${RC}" <<TCL
drc off
gds read ${GDS}
foreach cell [cellname list allcells] {
    if {\$cell eq "(UNNAMED)"} { continue }
    load \$cell
    save \$cell
}
quit -noprompt
TCL
echo "wrote $(ls -1 "${MAG}"/*.mag | wc -l) magic views in ${MAG}"
