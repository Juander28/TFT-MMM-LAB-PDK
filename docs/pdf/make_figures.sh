#!/usr/bin/env bash
#
# Regenerate every figure the guide uses, from the installed PDK.
#
#     ./make_figures.sh
#
# Run it after changing the PCells or the tech files, then rebuild the PDFs
# with make_pdf.py.  Nothing here is hand-drawn: the KLayout images come from
# the generated primitives, and the xschem and magic pictures are real windows.
#
# The windows are opened on a private X server of our own, on a display number
# nobody else is using, and it is torn down at the end.  Two reasons: your VNC
# desktop stays untouched, and the screen is guaranteed empty - a stale window
# left over from an earlier run would otherwise sit on top of the one we mean
# to photograph, which is exactly the trap this script used to fall into.
set -e

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIG="$(cd "${HERE}/.." && pwd)/figures"
mkdir -p "${FIG}"

export PDK_ROOT="${PDK_ROOT:-$HOME/pdks}"
export PDK="${PDK:-TFT-MMM-LAB-PDK}"
PDKPATH="${PDK_ROOT}/${PDK}"

[ -d "${PDKPATH}" ] || { echo "no PDK at ${PDKPATH} - run install.sh first" >&2; exit 1; }

# ---------------------------------------------------------------- KLayout ---
# Offscreen, no X server needed.  command -v bypasses the container's klayout
# alias, which adds -geometry and would make batch mode fail.
echo "== KLayout (offscreen) =="
"$(command -v klayout)" -z -nc -r "${HERE}/klayout_shots.py"

# ------------------------------------------------------------- private X ----
DISP=""
for n in $(seq 90 99); do
    if [ ! -e "/tmp/.X11-unix/X${n}" ]; then DISP=":${n}"; break; fi
done
[ -n "${DISP}" ] || { echo "no free X display between :90 and :99" >&2; exit 1; }

echo "== private X server on ${DISP} =="
Xvfb "${DISP}" -screen 0 1800x1300x24 >/dev/null 2>&1 &
XVFB_PID=$!
trap 'kill ${XVFB_PID} 2>/dev/null || true' EXIT
sleep 3
export DISPLAY="${DISP}"

# ----------------------------------------------------------------- xschem ---
echo "== xschem =="
cat > "${HERE}/.xschemrc_fig" <<XRC
source ${PDKPATH}/libs.tech/xschem/xschemrc
set netlist_dir ${HERE}
XRC
for pair in "symbols/tft_igzo.sym:xschem_sym.png" \
            "tests/tft_iv.sch:xschem_tb.png" \
            "tests/tft_igzo_l10w100.sch:xschem_lvs.png"; do
    src="${pair%%:*}"; png="${pair##*:}"
    # xschem exits non-zero after a successful batch export, hence the || true
    timeout 60 xschem --rcfile "${HERE}/.xschemrc_fig" \
        --tcl "after 1500 {xschem zoom_full; xschem print png ${FIG}/${png}; exit}" \
        "${PDKPATH}/libs.tech/xschem/${src}" >/dev/null 2>&1 || true
    echo "wrote ${FIG}/${png}"
done
rm -f "${HERE}/.xschemrc_fig"

# ------------------------------------------------------------------ magic ---
echo "== magic =="
grab() {   # grab <cell> <output.png> <crop|->  - retried, see grab_once
    local cell="$1" out="$2" crop="$3" try
    for try in 1 2 3; do
        if grab_once "$@"; then return 0; fi
        echo "  retrying ${out} (attempt $((try + 1)))"
    done
    echo "  ! ${out} came out blank three times - the window never painted."
    echo "    Re-run this script; if it keeps happening, open magic by hand on"
    echo "    the cell and take the screenshot yourself."
}

grab_once() {
    local cell="$1" out="$2" crop="$3"
    # "select top cell" and "view" force a redraw before "after" parks the
    # interpreter: "after" blocks Tk's event loop, so a window that has not
    # painted by then never will, and the grab comes out black.  The cell is
    # named on the command line too, which is what frames it.
    printf "select top cell\nview\nafter 60000\n" | timeout 70 magic -d XR \
        -rcfile "${PDKPATH}/libs.tech/magic/igzo_mmm_lab.magicrc" \
        "${PDKPATH}/libs.ref/igzo_mmm_lab_pr/mag/${cell}" >/dev/null 2>&1 &
    local mpid=$!
    DISP="${DISPLAY}" python3 - "${FIG}/${out}" "${crop}" <<'PY'
import os, sys, time
from PIL import ImageGrab
out, crop = sys.argv[1], sys.argv[2]
display = os.environ["DISP"]
deadline = time.time() + 50
best = None
filled = False
while time.time() < deadline:
    time.sleep(6)
    im = ImageGrab.grab(xdisplay=display)
    if crop != "-":
        im = im.crop(tuple(int(v) for v in crop.split(",")))
    # Only the drawing area: the title bar and the layer palette always have
    # colour in them.  A four-mask layout has few colours, so the bar is low.
    canvas = im.crop((30, 40, int(im.width * 0.85), im.height - 20)).convert("RGB")
    best = im
    if len(canvas.getcolors(400000) or []) > 6:
        filled = True
        break
# Only overwrite the figure when the capture actually worked.  A failed grab
# leaves the previous, good picture in place instead of replacing it with a
# black rectangle.
if filled:
    best.save(out)
    print("wrote", out)
else:
    print("  ! %s: canvas never painted, keeping the previous figure" % out)
sys.exit(0 if filled else 1)
PY
    local rc=$?
    # Close this magic before the next figure, or its window stays on top and
    # gets photographed instead.  By pid: magic runs under wish, so matching on
    # the name would either miss it or hit something else.
    kill "${mpid}" 2>/dev/null || true
    wait "${mpid}" 2>/dev/null || true
    sleep 3
    return ${rc}
}

grab tft_igzo_l10w100_pad magic_screen_pad.png 100,100,1460,1075
grab tft_igzo_l10w100     magic_screen_core.png 100,100,1460,1075

# ---------------------------------------------------------------- KLayout ---
# One GUI screenshot as well, for the cell list and the layer palette.
echo "== KLayout (window) =="
export KLAYOUT_PATH="${HOME}/.klayout:${PDKPATH}/libs.tech/klayout"
timeout 70 "$(command -v klayout)" -e -nn \
    "${PDKPATH}/libs.tech/klayout/tech/igzo_mmm_lab.lyt" \
    -c "${HERE}/klayoutrc_notips" \
    -l "${PDKPATH}/libs.tech/klayout/tech/igzo_mmm_lab.lyp" \
    "${PDKPATH}/libs.ref/igzo_mmm_lab_pr/gds/tft_primitives.gds" >/dev/null 2>&1 &
KL_PID=$!
DISP="${DISPLAY}" python3 - "${FIG}/klayout_screen_crop.png" <<'PY'
import os, sys, time
from PIL import ImageGrab
deadline = time.time() + 50
best = None
while time.time() < deadline:
    time.sleep(6)
    im = ImageGrab.grab(xdisplay=os.environ["DISP"]).crop((0, 0, 1680, 1020))
    best = im
    if len(im.convert("RGB").getcolors(400000) or []) > 200:
        break
else:
    print("  ! klayout window never appeared, using the last grab")
best.save(sys.argv[1])
print("wrote", sys.argv[1])
PY
kill "${KL_PID}" 2>/dev/null || true
wait "${KL_PID}" 2>/dev/null || true

echo
echo "Figures are in ${FIG}.  Rebuild the documents with:"
echo "    python3 ${HERE}/make_pdf.py"
