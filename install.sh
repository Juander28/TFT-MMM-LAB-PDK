#!/usr/bin/env bash
#
# Install this PDK so that it can be selected the same way as the open-source
# PDKs in the container - sky130A, gf180mcuD, ihp-sg13g2.
#
#     ./install.sh                 install and add the environment to ~/.bashrc
#     ./install.sh --no-bashrc     install only, print the environment
#     ./install.sh --root <dir>    use a different PDK_ROOT (default ~/pdks)
#
# WHY A SECOND PDK_ROOT.  /foss/pdks belongs to root and cannot be written by
# the designer account, so a directory cannot simply be created next to the
# others.  Instead this builds a writable PDK_ROOT that carries symlinks to all
# of them plus this one, and points PDK_ROOT at it.  Nothing is copied, the
# vendor PDKs keep working exactly as before, and
#
#     use-pdk TFT-MMM-LAB-PDK
#
# then switches klayout, xschem, ngspice and magic over in one command.  If you
# ever do have root in the container, the script also drops a symlink straight
# into /foss/pdks, and then this PDK really does sit beside the others.
set -e

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NAME="$(basename "${SRC}")"
PDK_ROOT_NEW="${HOME}/pdks"
DESIGNS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENDOR_ROOT="/foss/pdks"
DO_BASHRC=1
MARKER="# >>> ${NAME} <<<"

while [ $# -gt 0 ]; do
    case "$1" in
        --no-bashrc) DO_BASHRC=0; shift ;;
        --root) PDK_ROOT_NEW="$2"; shift 2 ;;
        -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
        *) echo "unknown option: $1" >&2; exit 1 ;;
    esac
done

echo "Installing ${NAME} from ${SRC}"

# --- 1. the writable PDK_ROOT ------------------------------------------------
mkdir -p "${PDK_ROOT_NEW}"
if [ -d "${VENDOR_ROOT}" ]; then
    for pdk in "${VENDOR_ROOT}"/*; do
        base="$(basename "${pdk}")"
        [ "${base}" = "${NAME}" ] && continue
        ln -sfn "${pdk}" "${PDK_ROOT_NEW}/${base}"
    done
fi
ln -sfn "${SRC}" "${PDK_ROOT_NEW}/${NAME}"
echo "  PDK_ROOT ${PDK_ROOT_NEW}:"
ls -1 "${PDK_ROOT_NEW}" | sed 's/^/    /'

# --- 2. next to the vendor PDKs, if that is possible at all ------------------
if [ -w "${VENDOR_ROOT}" ]; then
    ln -sfn "${SRC}" "${VENDOR_ROOT}/${NAME}"
    echo "  also linked into ${VENDOR_ROOT}/${NAME}"
else
    echo "  ${VENDOR_ROOT} is not writable - skipping the native symlink."
    echo "  With a root shell in the container this would make it native:"
    echo "      ln -s ${SRC} ${VENDOR_ROOT}/${NAME}"
fi

# --- 3. xschem ---------------------------------------------------------------
# klayout, ngspice and magic are all reached through environment variables, so
# use-pdk is enough for them.  xschem is not: it reads a Tcl rc file, and the
# stock ~/.xschem/xschemrc knows nothing about any PDK.  Inside the container
# the mount's own rc file sources ours; on a bare machine nothing does, and
# xschem comes up unable to find even its own devices/ library - every symbol
# on a test sheet reads "IS MISSING".
#
# So the same marked-block trick as for .bashrc, in the xschem rc file.
XSCHEMRC="${HOME}/.xschem/xschemrc"
mkdir -p "$(dirname "${XSCHEMRC}")"
touch "${XSCHEMRC}"
if grep -qF "${MARKER}" "${XSCHEMRC}"; then
    sed -i "\|^${MARKER}$|,\|^${MARKER}$|d" "${XSCHEMRC}"
    echo "  replaced the previous block in ${XSCHEMRC}"
else
    echo "  added the PDK to ${XSCHEMRC}"
fi
cat >> "${XSCHEMRC}" <<XEOF

${MARKER}
# Load whichever PDK use-pdk selected.  Guarded, because xschem is also used
# without a PDK and this file must not break that.
if { [info exists env(PDK_ROOT)] && [info exists env(PDK)] } {
  set _rc \$env(PDK_ROOT)/\$env(PDK)/libs.tech/xschem/xschemrc
  if { [file exists \$_rc] } { source \$_rc }
}
# The design tree, so a cell can be instanced by a path relative to it -
# "MMM-LAB DESIGN/OPAM/OPAM2.sym" - from wherever xschem was started.
if { [info exists env(DESIGNS)] && \$env(DESIGNS) ne {} } {
  append XSCHEM_LIBRARY_PATH :\$env(DESIGNS)
  # Netlists and raw files.  Created if missing: pointing netlist_dir at a
  # directory that is not there makes xschem fail to write WITHOUT SAYING SO.
  set netlist_dir \$env(DESIGNS)/simulations
  file mkdir \$netlist_dir
}
${MARKER}
XEOF

# --- 4. the environment ------------------------------------------------------
ENVBLOCK=$(cat <<ENVEOF
${MARKER}
# Writable PDK_ROOT holding the vendor PDKs and ${NAME}.
export PDK_ROOT=${PDK_ROOT_NEW}
# The design tree.  Inside the container .designinit sets this; on a bare
# machine nothing does, so fall back to whatever directory this PDK was
# cloned into.  xschem uses it to find cells by a path relative to the tree,
# and to put netlists somewhere that exists.
export DESIGNS="\${DESIGNS:-${DESIGNS_DIR}}"
# Switch PDK in one command:  use-pdk TFT-MMM-LAB-PDK  |  use-pdk gf180mcuD
use-pdk() {
    export PDK="\$1"
    export PDKPATH="\$PDK_ROOT/\$PDK"
    export SPICE_USERINIT_DIR="\$PDKPATH/libs.tech/ngspice"
    export KLAYOUT_PATH="\$HOME/.klayout:\$PDKPATH/libs.tech/klayout"
}
use-pdk "\${PDK:-gf180mcuD}"
${MARKER}
ENVEOF
)

if [ "${DO_BASHRC}" = "1" ]; then
    if grep -qF "${MARKER}" "${HOME}/.bashrc" 2>/dev/null; then
        python3 - "$HOME/.bashrc" "${MARKER}" <<'PYEOF' > /tmp/.bashrc.$$
import sys
path, marker = sys.argv[1], sys.argv[2]
lines = open(path).read().split("\n")
out, skip = [], False
for line in lines:
    if line.strip() == marker:
        skip = not skip
        continue
    if not skip:
        out.append(line)
sys.stdout.write("\n".join(out))
PYEOF
        mv /tmp/.bashrc.$$ "${HOME}/.bashrc"
        echo "  replaced the previous block in ~/.bashrc"
    fi
    printf '\n%s\n' "${ENVBLOCK}" >> "${HOME}/.bashrc"
    echo "  added the environment to ~/.bashrc"
    echo
    echo "Open a new shell (or 'source ~/.bashrc'), then:  use-pdk ${NAME}"
else
    echo
    echo "Add this to your shell:"
    echo "${ENVBLOCK}"
fi
