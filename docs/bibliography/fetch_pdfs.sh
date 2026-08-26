#!/usr/bin/env bash
#
# Pull down the open-access papers listed in README.md.  They are not tracked
# in git - this repository carries no PDFs - so run this once on a fresh
# clone.  Everything paywalled stays as a DOI in magnetic_tft.bib.
set -e
cd "$(dirname "$0")"
mkdir -p pdf

get() {  # get <url> <file>
    [ -s "pdf/$2" ] && { echo "  have $2"; return; }
    if curl -sSL --max-time 120 -A "Mozilla/5.0" -o "pdf/$2" "$1" \
       && [ "$(file -b --mime-type "pdf/$2")" = application/pdf ]; then
        echo "  got  $2"
    else
        rm -f "pdf/$2"
        echo "  MISS $2 - fetch it by hand from $1"
    fi
}

get https://arxiv.org/pdf/1703.04007 wang2017_apl_wl_wal_igzo_tft.pdf
get https://arxiv.org/pdf/1705.05010 wang2017_apex_universal_wl_wal.pdf
get https://arxiv.org/pdf/1712.07618 wang2017_double_gate_wl_wal.pdf
get https://jart.icat.unam.mx/index.php/jart/article/download/566/562 \
    garcia2004_jart_magfet_lowtemp.pdf
# Open access, but the publishers refuse scripted downloads.  Both open in a
# browser from their DOI:
#   10.3390/mi11090822          Hall offset voltage in InGaZnO
#   10.1088/1674-4926/35/9/094004   split-drain MAGFET on a poly-Si TFT
