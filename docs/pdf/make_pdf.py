#!/usr/bin/env python3
"""
Build the "cells and tools" guide for TFT-MMM-LAB-PDK, in English and Spanish.

    python3 make_pdf.py            # both languages
    python3 make_pdf.py en         # one of them
    python3 make_pdf.py es ~/out   # and somewhere else

Figures come from ../figures; regenerate them with make_figures.sh after any
change to the PCells or the tech files.  PDFs go to ~/Documents/PDK-TFT-MMM-LAB
by default.
"""

import os
import sys

from pdfkit import ACCENT, INK, MUTED, Page, PdfPages, default_out_dir

# ---------------------------------------------------------------------------
# Code blocks are the same in both languages; only their comments change.
# ---------------------------------------------------------------------------

CODE = {
    "install": {
        "en": """$ cd /foss/designs/TFT-MMM-LAB-PDK
$ ./install.sh
$ source ~/.bashrc        # or just open a new terminal""",
        "es": """$ cd /foss/designs/TFT-MMM-LAB-PDK
$ ./install.sh
$ source ~/.bashrc        # o simplemente abre una terminal nueva""",
    },
    "symlink": {
        "en": "ln -s /foss/designs/TFT-MMM-LAB-PDK /foss/pdks/TFT-MMM-LAB-PDK",
        "es": "ln -s /foss/designs/TFT-MMM-LAB-PDK /foss/pdks/TFT-MMM-LAB-PDK",
    },
    "usepdk": {
        "en": """$ use-pdk TFT-MMM-LAB-PDK      # the IGZO TFT process
$ use-pdk gf180mcuD            # GlobalFoundries 180 nm
$ use-pdk sky130A              # SkyWater 130 nm
$ use-pdk ihp-sg13g2           # IHP SiGe BiCMOS 130 nm
$ use-pdk ihp-sg13cmos5l       # IHP CMOS variant""",
        "es": """$ use-pdk TFT-MMM-LAB-PDK      # el proceso IGZO TFT
$ use-pdk gf180mcuD            # GlobalFoundries 180 nm
$ use-pdk sky130A              # SkyWater 130 nm
$ use-pdk ihp-sg13g2           # IHP SiGe BiCMOS 130 nm
$ use-pdk ihp-sg13cmos5l       # variante CMOS de IHP""",
    },
    "generate": {
        "en": """$ python3 scripts/build_libs_ref.py    # PCells  ->  gds/tft_primitives.gds
$ ./scripts/build_mag_views.sh        # that GDS ->  mag/*.mag  (32 magic views)""",
        "es": """$ python3 scripts/build_libs_ref.py    # PCells  ->  gds/tft_primitives.gds
$ ./scripts/build_mag_views.sh        # ese GDS  ->  mag/*.mag  (32 vistas magic)""",
    },
    "regression": """$ python3 libs.tech/klayout/tech/pymacros/testing/test_pcell_vs_gds.py \\
          libs.ref/igzo_mmm_lab_pr/gds/TFT_layout.gds

OK  sd 6/0    [(-502.5, -200.0, -5.0, 200.0), (5.0, -200.0, 502.5, 200.0)]
OK  igzo 4/0  [(-15.0, -55.0, 15.0, 55.0)]
OK  gate 2/0  [(-200.0, -495.0, 200.0, 495.0)]
OK  gate 2/0  PCell stripe 20 um over the island, overlap [5.0, 5.0] um per side
OK  gate 2/0  GDS   stripe 20 um over the island, overlap [5.0, 5.0] um per side
OK  nf=1/2/5  shared electrodes, W_total = 100 / 200 / 500 um
OK  drawn channel gap 10 um - the +3 um print bias is reported, not drawn""",
    "netlist": "XM1 D G S igzo_tft W=1000u L=8u ov=5u nf=1",
    "extract": """% load $PDKPATH/libs.ref/igzo_mmm_lab_pr/mag/tft_igzo_l10w100
% extract all
% ext2spice lvs
% ext2spice -o layout.spice

.subckt tft_igzo_l10w100 S D G
X0 D G S igzo_tft w=0.11333m l=10u
.ends""",
    "lvs": """$ netgen -batch lvs "layout.spice tft_igzo_l10w100" \\
                     "schematic.spice tft_igzo_l10w100" \\
                     $PDKPATH/libs.tech/netgen/setup.tcl

Circuit 1 contains 1 devices, Circuit 2 contains 1 devices.
Circuit 1 contains 4 nets,    Circuit 2 contains 4 nets.

Final result:
Circuits match uniquely.""",
    "spice": """.include $PDK_ROOT/$PDK/libs.tech/ngspice/design.ngspice
.lib     $PDK_ROOT/$PDK/libs.tech/ngspice/igzo_mmm_lab.ngspice tt

XM1 d g s igzo_tft W=100u L=10u ov=5u""",
    "validation": {
        "en": """W = 1000 um, L = 8 um, VGS = 6 V, VDS = 10 V
    simulated   654.4 uA
    measured    670 - 701 uA""",
        "es": """W = 1000 um, L = 8 um, VGS = 6 V, VDS = 10 V
    simulado    654.4 uA
    medido      670 - 701 uA""",
    },
    "checks": """$ use-pdk TFT-MMM-LAB-PDK
$ echo $PDKPATH
/headless/pdks/TFT-MMM-LAB-PDK
$ ./scripts/run_checks.sh""",
}


# ---------------------------------------------------------------------------

EN = {
    "footer": "TFT-MMM-LAB-PDK  ·  igzo_mmm_lab",
    # page 1
    "p1_kicker": "UCI/INRF IGZO TFT process",
    "p1_title": "Cells, and how they look in\nklayout, xschem and magic",
    "p1_intro":
        "This is a walk through what the PDK actually contains - the generated cell\n"
        "library - and what each of the four tools shows you when you open it. It also\n"
        "covers how to activate the PDK and how to move between it and the open-source\n"
        "PDKs already installed in the container.",
    "p1_h1": "The process in one paragraph",
    "p1_process":
        "A top-gate coplanar IGZO thin-film transistor, four masks. The IGZO island goes\n"
        "down first, the Au source/drain lands directly on it - the contact is the overlap,\n"
        "there is no via layer - a blanket 50 nm Al2O3 follows, opened only over the probe\n"
        "pads, and the Au gate is the last metal.",
    "p1_layers": [
        ["#", "Layer", "GDS", "What it is"],
        ["1", "igzo", "4/0", "semiconductor island, deposited first"],
        ["2", "sd", "6/0", "Au source/drain, directly on the IGZO"],
        ["3", "oxetch", "5/0", "openings in the blanket Al2O3, over the S/D pads only"],
        ["4", "gate", "2/0", "Au gate, last metal, above the dielectric"],
        ["", "align", "8/0", "alignment marks"],
    ],
    "p1_h2": "Where everything lives",
    "p1_where": [
        ["Repository", "github.com/Juander28/TFT-MMM-LAB-PDK"],
        ["Working copy", "/foss/designs/TFT-MMM-LAB-PDK   (= C:\\TFT-MMM-LAB-PDK)"],
        ["Installed as", "$PDK_ROOT/TFT-MMM-LAB-PDK, with PDK_ROOT = ~/pdks"],
        ["This document", "~/Documents/PDK-TFT-MMM-LAB"],
        ["Technology name", "igzo_mmm_lab"],
        ["Device library", "igzo_mmm_lab_pr"],
    ],
    "p1_cap": "The 39 generated cells in KLayout, technology igzo_mmm_lab selected. "
              "Cell list on the left, layer palette on the right.",
    # page 2
    "p2_kicker": "setup",
    "p2_title": "Activating the PDK",
    "p2_once": "Once, after cloning:",
    "p2_what":
        "install.sh does two things. It builds a writable PDK_ROOT at ~/pdks holding a\n"
        "symlink to every PDK in /foss/pdks plus this one, and it adds a use-pdk function\n"
        "to ~/.bashrc. Nothing is copied and the vendor PDKs are untouched.",
    "p2_h1": "Why not simply put it in /foss/pdks",
    "p2_why":
        "/foss/pdks belongs to root and the designer account cannot write there, so a new\n"
        "directory cannot be created next to sky130A and gf180mcuD. With a root shell in\n"
        "the container one symlink makes it native, and install.sh does it automatically\n"
        "whenever /foss/pdks happens to be writable:",
    "p2_h2": "Switching PDKs",
    "p2_then": "Then, in any terminal:",
    "p2_one":
        "One command switches all four tools at once: they all read the same four variables.\n"
        "use-pdk only makes that a single command instead of four exports.",
    "p2_vars": [
        ["Variable", "Set to", "Who reads it"],
        ["PDK", "TFT-MMM-LAB-PDK", "everything, by name"],
        ["PDKPATH", "$PDK_ROOT/$PDK", "scripts, .magicrc, xschemrc"],
        ["KLAYOUT_PATH", "~/.klayout:$PDKPATH/libs.tech/klayout", "klayout: technology + PCells"],
        ["SPICE_USERINIT_DIR", "$PDKPATH/libs.tech/ngspice", "ngspice: model search path"],
    ],
    "p2_h3": "What each tool picks up",
    "p2_tools": [
        ["klayout", "technology igzo_mmm_lab, its layer colours, the igzo_mmm_lab_pr PCells"],
        ["xschem", "$::IGZO_MODELS, the tft_igzo symbol, the example testbenches"],
        ["ngspice", "design.ngspice (device wrappers) and the corner sections"],
        ["magic", "igzo_mmm_lab.tech, the .mag device views, extraction rules"],
        ["netgen", "libs.tech/netgen/setup.tcl for LVS"],
    ],
    # page 3
    "p3_kicker": "libs.ref / igzo_mmm_lab_pr",
    "p3_title": "The cell library",
    "p3_intro":
        "Three PCells generate everything. The library ships 39 cells: the transistor matrix\n"
        "drawn on the test chip, the same device with its probe pads, three capacitors and\n"
        "five inductors. The passives have their own document - the cell SOP - which goes\n"
        "through every parameter and where its default came from.",
    "p3_cells": [
        ["Cell", "Count", "What it is"],
        ["tft_igzo_l{L}w{W}", "30", "L in {5,10,20,40,80,160} um x W in {10,50,100,500,1000} um"],
        ["tft_igzo_l10w100_pad", "1", "the fabricated device, 400x400 um probe pads included"],
        ["cap_mim_400x400", "1", "the overlap capacitor Cox was measured on"],
        ["cap_mim_40p36 / _9p61", "2", "sized by capacitance instead of by dimensions"],
        ["ind_igzo_*", "5", "square/circular x series/parallel, plus the 100 MHz tank coil"],
    ],
    "p3_h1": "They are generated, not drawn",
    "p3_gen":
        "There is one description of the geometry - the KLayout PCell - and every other\n"
        "view is derived from it, so they cannot drift apart:",
    "p3_nohand": "Do not hand-edit the .mag files; they are output, not source.",
    "p3_h2": "The defaults are the fabricated device",
    "p3_def":
        "tft_igzo with its default parameters reproduces cell TFT-10L100W of the test chip\n"
        "shape for shape, on all three drawn layers. That is asserted by a regression test,\n"
        "not by eye:",
    "p3_h3": "Naming",
    "p3_name":
        "l10w100 means L = 10 um, W = 100 um, both drawn. The process prints the channel\n"
        "about 3 um longer; the PCell reports that as l_printed and never applies it to the\n"
        "geometry, because a PCell writes a mask and the bias is one sample of one cell.",
    # page 4
    "p4_kicker": "layout, PCells, DRC",
    "p4_title": "In KLayout",
    "p4_intro":
        "Library igzo_mmm_lab_pr appears in the library browser with two PCells. Drop one in\n"
        "and edit its parameters in the instance dialog.",
    "p4_cap": "tft_igzo with pad=true: S/D pads left and right (orange, with the red "
              "dielectric openings inside them), gate pad above, device in the middle. "
              "This is the fabricated TFT-10L100W.",
    "p4_h1": "tft_igzo parameters",
    "p4_params": [
        ["Parameter", "Default", "Meaning"],
        ["w_gate", "100 um", "channel width, per finger"],
        ["l_gate", "10 um", "drawn channel length = the electrode gap"],
        ["nf", "1", "fingers; they share electrodes"],
        ["gate_ov", "5 um", "gate overlap per side - the dominant parasitic"],
        ["sd_len", "97.5 um", "S/D electrode length"],
        ["igzo_ext_x / _y", "10 / 5 um", "island over the electrode / past its end"],
        ["pad", "off", "400x400 um probe pads + dielectric openings"],
        ["l_bias", "3 um", "drawn-to-printed bias, reported only"],
        ["l_printed", "read-only", "l_gate + l_bias"],
        ["w_total", "read-only", "w_gate x nf"],
    ],
    # page 5
    "p5_kicker": "geometry",
    "p5_title": "In KLayout: the device itself",
    "p5_cap": "The channel region of tft_igzo_l10w100. Teal is the IGZO island, orange the "
              "S/D electrodes, grey the gate stripe crossing them. The gap between the two "
              "orange electrodes is L; the height over which they face the island is W.",
    "p5_read": "Read off the picture, and identical to what the test chip draws:",
    "p5_dims": [
        ["L = 10 um", "the gap between the S/D electrodes"],
        ["W = 100 um", "the electrode height, not the island height"],
        ["overlap = 5 um", "how far the gate reaches over each electrode"],
        ["island = 30 x 110 um", "10 um over each electrode in x, 5 um past each end in y"],
    ],
    "p5_h1": "The capacitor",
    "p5_capcap": "cap_mim_400x400: the lower plate is S/D metal running down, the upper plate "
                 "is gate metal running sideways, and the capacitance is their 400 x 400 um "
                 "crossing - 250.2 pF measured, which is where Cox = 1.564 fF/um2 comes from.",
    # page 6
    "p6_kicker": "schematic",
    "p6_title": "In xschem",
    "p6_cap": "symbols/tft_igzo.sym. Three pins in the order D, G, S - the same order the "
              "igzo_tft subcircuit declares. There is no bulk pin: a TFT sits on glass, and "
              "the wrapper keeps the intrinsic device's bulk tied to its own source.",
    "p6_h1": "What it netlists to",
    "p6_expl":
        "W, L and ov are drawn dimensions in metres. spiceprefix=X because the device is a\n"
        "subcircuit: the wrapper adds the measured contact resistance and the overlap\n"
        "capacitance around a level-1 core, so ov can be swept - which is the point, since\n"
        "the overlap is what decides whether a tuned stage works.",
    "p6_tbcap": "tests/tft_iv.sch - the output-characteristics testbench on the device the "
                "model was validated against (W = 1000 um, L = 8 um). The MODELS block pulls "
                "in the wrappers and one corner; the NGSPICE block holds the sweep.",
    # page 7
    "p7_kicker": "layout and extraction",
    "p7_title": "In magic",
    "p7_cap": "tft_igzo_l10w100_pad in magic. Blue is sdmetal, red gatemetal, and the "
              "hatched squares inside the S/D pads are the dielectric openings. The layer "
              "palette on the right is this process, not a MOS one.",
    "p7_h1": "How magic decomposes the device",
    "p7_cap2": "Zoomed in: blue sdmetal electrodes, teal sdcontact where the Au meets the "
               "IGZO, the hatched tftfet channel between them, green semiconductor stubs "
               "above and below - the island overhang - and red gatemetal top and bottom.",
    # page 8
    "p8_kicker": "extraction and LVS",
    "p8_title": "In magic: what comes out",
    "p8_h1": "Extraction",
    "p8_w":
        "l comes out exactly: 10 um, the gap between the electrodes. w does not, and the\n"
        "picture on the previous page shows why - the extractor measures the gated island,\n"
        "and the green stubs are drawn 5 um past each electrode for alignment margin. They\n"
        "are gated but carry no source-to-drain current, so the device width is the\n"
        "electrode height, 100 um, while extraction reports about 13 % more.",
    "p8_w2":
        "This is a property of how the test chip is drawn, not a bug in the deck. An island\n"
        "flush with the electrodes extracts exactly. Until then netgen is told to allow it.",
    "p8_h2": "LVS",
    "p8_setup":
        "setup.tcl permutes source and drain, holds l to 1 % and allows 20 % on w, and says\n"
        "in the file itself why the two tolerances differ. Setting W wrong in the schematic\n"
        "does fail - it was checked: W = 500u against the extracted 113 um reports property\n"
        "errors rather than passing quietly.",
    "p8_h3": "Three terminals, on both sides",
    "p8_gnd":
        "Magic emits three terminals because the msubcircuit line in the techfile carries no\n"
        "substrate arguments. The other form, \"device subcircuit\", also emits three - but in\n"
        "the order G S D, which would disagree with the symbol silently. Pin order is the\n"
        "first thing LVS checks, and a swapped gate is the one mistake that still simulates.",
    # page 9
    "p9_kicker": "models",
    "p9_title": "In ngspice",
    "p9_intro": "Two lines pull in the process. The first is the device wrappers, the second a corner:",
    "p9_xschem": "In xschem the same two lines read $::IGZO_MODELS/... - the variable the PDK's xschemrc sets.",
    "p9_h1": "Corners",
    "p9_corners": [
        ["Section", "What it is"],
        ["tt", "typical: median over every working device of the best chip"],
        ["best", "long-channel devices of the best chip, not contact-limited"],
        ["short", "L <= 10 um, contact-limited; prefer tt plus the wrapper instead"],
        ["all", "across all three chips, including the bad ones - worst case"],
    ],
    "p9_h2": "What the wrapper adds",
    "p9_wrap": [
        ["Contact resistance", "Rc = 3.3 Ohm*m / W per contact, measured from R_on against L"],
        ["Overlap capacitance", "Cox * ov * W per side; 7.82 fF per um of width at ov = 5 um"],
        ["An inert bulk", "b is held through a 1 Tohm resistor; the core ties its own bulk to source"],
    ],
    "p9_cgso":
        "Cgso and Cgdo are zero in the model cards on purpose. The overlap capacitance is not\n"
        "a property of the process alone - it is Cox times the drawn overlap - so it lives in\n"
        "the wrapper where it tracks ov, instead of being frozen at the 5 um of the test chip.",
    "p9_h3": "The number that says the model still works",
    "p9_val":
        "That is the same figure the original extraction reported, and run_checks.sh asserts\n"
        "it, so a change to the models that breaks it fails loudly.",
    # page 10
    "p10_kicker": "verification",
    "p10_title": "The four tools agree",
    "p10_intro": "run_checks.sh runs the whole chain and stops at the first failure:",
    "p10_checks": [
        ["Check", "Tool", "Result"],
        ["PCell against the fabricated cell", "klayout", "identical on all three layers"],
        ["Technology and library discovery", "klayout", "igzo_mmm_lab, igzo_mmm_lab_pr"],
        ["DRC on the generated primitives", "klayout", "clean"],
        ["Symbol netlists with D G S", "xschem", "pin order correct"],
        ["Model against the measurement", "ngspice", "654.4 uA"],
        ["GDS round-trip", "magic", "layer-exact"],
        ["Device extraction", "magic", "one igzo_tft, l = 10 um"],
        ["Layout against schematic", "netgen", "match uniquely"],
    ],
    "p10_h1": "What the PDK does not know",
    "p10_limits":
        "1.  The models are DC-only. They reproduce the measured output curves - median\n"
        "    simulated/measured = 1.01 over 18 devices - and nothing else has been checked.\n"
        "    Cox is measured, but no C-V or S-parameter measurement backs the AC behaviour.\n"
        "\n"
        "2.  Level 1 imposes a square law; the measured saturation exponent is 2.31, so the\n"
        "    model runs about 20 % pessimistic on gm. Valid to VGS <= 6 V, VDS <= 10 V.\n"
        "\n"
        "3.  The +3 um print bias is one sample. The PCell reports it, never applies it.\n"
        "\n"
        "4.  The DRC deck is preliminary. Every rule is measured or read off the test chip;\n"
        "    there is no foundry rule document. 5 um is the minimum drawn dimension because\n"
        "    the smallest drawn device is 5 um and it prints at 8 um.\n"
        "\n"
        "5.  TFT2 is not represented: its saturation exponent is 0.87, which no square-law\n"
        "    model can express.",
    "p10_h2": "Running the deck over the fabricated chip",
    "p10_drc": [
        ["The transistor matrix", "clean, except the 5 um cells - they are drawn with"],
        ["", "3.5 um of gate overlap instead of 5 um"],
        ["Test_capacitance", "clean"],
        ["Test_mobility", "violates several rules - it is a measurement structure,"],
        ["", "drawn before any rules existed"],
    ],
    "p10_end":
        "None of these are reasons not to use the PDK. They are the things a PDK that looks\n"
        "authoritative should not hide.",
}

ES = {
    "footer": "TFT-MMM-LAB-PDK  ·  igzo_mmm_lab",
    # page 1
    "p1_kicker": "Proceso IGZO TFT de UCI/INRF",
    "p1_title": "Las celdas, y cómo se ven en\nklayout, xschem y magic",
    "p1_intro":
        "Este documento recorre lo que el PDK contiene de verdad - la librería de celdas\n"
        "generada - y lo que cada una de las cuatro herramientas te muestra al abrirlo.\n"
        "También explica cómo activar el PDK y cómo moverte entre él y los PDK open source\n"
        "que ya vienen instalados en el contenedor.",
    "p1_h1": "El proceso en un párrafo",
    "p1_process":
        "Un transistor de película delgada de IGZO, top-gate coplanar, cuatro máscaras. La\n"
        "isla de IGZO se deposita primero, el Au de fuente/drenaje cae directamente sobre\n"
        "ella - el contacto es el solape, no hay capa de vía -, sigue una película continua\n"
        "de 50 nm de Al2O3 que solo se abre sobre los pads, y el gate de Au es el último metal.",
    "p1_layers": [
        ["#", "Capa", "GDS", "Qué es"],
        ["1", "igzo", "4/0", "isla semiconductora, se deposita primero"],
        ["2", "sd", "6/0", "fuente/drenaje de Au, directamente sobre el IGZO"],
        ["3", "oxetch", "5/0", "aberturas en el Al2O3, solo sobre los pads de S/D"],
        ["4", "gate", "2/0", "gate de Au, último metal, encima del dieléctrico"],
        ["", "align", "8/0", "marcas de alineación"],
    ],
    "p1_h2": "Dónde vive cada cosa",
    "p1_where": [
        ["Repositorio", "github.com/Juander28/TFT-MMM-LAB-PDK"],
        ["Copia de trabajo", "/foss/designs/TFT-MMM-LAB-PDK   (= C:\\TFT-MMM-LAB-PDK)"],
        ["Instalado como", "$PDK_ROOT/TFT-MMM-LAB-PDK, con PDK_ROOT = ~/pdks"],
        ["Este documento", "~/Documents/PDK-TFT-MMM-LAB"],
        ["Nombre de la tecnología", "igzo_mmm_lab"],
        ["Librería de dispositivos", "igzo_mmm_lab_pr"],
    ],
    "p1_cap": "Las 39 celdas generadas en KLayout, con la tecnología igzo_mmm_lab "
              "seleccionada. Lista de celdas a la izquierda, paleta de capas a la derecha.",
    # page 2
    "p2_kicker": "instalación",
    "p2_title": "Cómo activar el PDK",
    "p2_once": "Una sola vez, después de clonar:",
    "p2_what":
        "install.sh hace dos cosas. Construye un PDK_ROOT escribible en ~/pdks con un enlace\n"
        "a cada PDK de /foss/pdks más este, y añade la función use-pdk a ~/.bashrc. No copia\n"
        "nada y los PDK del contenedor quedan intactos.",
    "p2_h1": "Por qué no se pone directamente en /foss/pdks",
    "p2_why":
        "/foss/pdks pertenece a root y la cuenta designer no puede escribir ahí, así que no\n"
        "se puede crear un directorio nuevo junto a sky130A y gf180mcuD. Con una shell de\n"
        "root en el contenedor, un enlace lo vuelve nativo, e install.sh lo hace solo cada\n"
        "vez que /foss/pdks resulte ser escribible:",
    "p2_h2": "Cambiar de PDK",
    "p2_then": "Después, en cualquier terminal:",
    "p2_one":
        "Un solo comando cambia las cuatro herramientas a la vez: todas leen las mismas cuatro\n"
        "variables. use-pdk solo convierte eso en un comando en lugar de cuatro exports.",
    "p2_vars": [
        ["Variable", "Se pone en", "Quién la lee"],
        ["PDK", "TFT-MMM-LAB-PDK", "todo, por nombre"],
        ["PDKPATH", "$PDK_ROOT/$PDK", "scripts, .magicrc, xschemrc"],
        ["KLAYOUT_PATH", "~/.klayout:$PDKPATH/libs.tech/klayout", "klayout: tecnología + PCells"],
        ["SPICE_USERINIT_DIR", "$PDKPATH/libs.tech/ngspice", "ngspice: ruta de modelos"],
    ],
    "p2_h3": "Qué recoge cada herramienta",
    "p2_tools": [
        ["klayout", "la tecnología igzo_mmm_lab, sus colores de capa, los PCells igzo_mmm_lab_pr"],
        ["xschem", "$::IGZO_MODELS, el símbolo tft_igzo, los testbenches de ejemplo"],
        ["ngspice", "design.ngspice (los envoltorios del dispositivo) y las esquinas"],
        ["magic", "igzo_mmm_lab.tech, las vistas .mag, las reglas de extracción"],
        ["netgen", "libs.tech/netgen/setup.tcl para el LVS"],
    ],
    # page 3
    "p3_kicker": "libs.ref / igzo_mmm_lab_pr",
    "p3_title": "La librería de celdas",
    "p3_intro":
        "Tres PCells generan todo. La librería trae 39 celdas: la matriz de transistores del\n"
        "chip de prueba, el mismo dispositivo con sus pads, tres capacitores y cinco\n"
        "inductores. Las pasivas tienen su propio documento - el SOP de celdas - que recorre\n"
        "cada parámetro y de dónde salió su valor por defecto.",
    "p3_cells": [
        ["Celda", "Cantidad", "Qué es"],
        ["tft_igzo_l{L}w{W}", "30", "L en {5,10,20,40,80,160} um x W en {10,50,100,500,1000} um"],
        ["tft_igzo_l10w100_pad", "1", "el dispositivo fabricado, con sus pads de 400x400 um"],
        ["cap_mim_400x400", "1", "el capacitor de solape con el que se midió Cox"],
        ["cap_mim_40p36 / _9p61", "2", "dimensionados por capacitancia, no por medidas"],
        ["ind_igzo_*", "5", "cuadrado/circular x serie/paralelo, más la bobina del tanque"],
    ],
    "p3_h1": "Están generadas, no dibujadas a mano",
    "p3_gen":
        "Hay una sola descripción de la geometría - el PCell de KLayout - y todas las demás\n"
        "vistas se derivan de ella, así que no se pueden desincronizar:",
    "p3_nohand": "No edites los .mag a mano: son salida, no fuente.",
    "p3_h2": "Los valores por defecto son el dispositivo fabricado",
    "p3_def":
        "tft_igzo con sus parámetros por defecto reproduce la celda TFT-10L100W del chip de\n"
        "prueba forma por forma, en las tres capas dibujadas. Eso lo afirma un test de\n"
        "regresión, no la vista:",
    "p3_h3": "Nomenclatura",
    "p3_name":
        "l10w100 significa L = 10 um, W = 100 um, ambas dibujadas. El proceso imprime el canal\n"
        "unas 3 um más largo; el PCell lo reporta como l_printed y nunca lo aplica a la\n"
        "geometría, porque un PCell escribe una máscara y ese bias es una muestra de una celda.",
    # page 4
    "p4_kicker": "layout, PCells, DRC",
    "p4_title": "En KLayout",
    "p4_intro":
        "La librería igzo_mmm_lab_pr aparece en el navegador de librerías con dos PCells.\n"
        "Instancias uno y editas sus parámetros en el diálogo de la instancia.",
    "p4_cap": "tft_igzo con pad=true: pads de S/D a izquierda y derecha (naranja, con las "
              "aberturas del dieléctrico en rojo dentro de ellos), pad de gate arriba y el "
              "dispositivo en medio. Este es el TFT-10L100W fabricado.",
    "p4_h1": "Parámetros de tft_igzo",
    "p4_params": [
        ["Parámetro", "Por defecto", "Significado"],
        ["w_gate", "100 um", "ancho de canal, por dedo"],
        ["l_gate", "10 um", "longitud de canal dibujada = el hueco entre electrodos"],
        ["nf", "1", "dedos; comparten electrodos"],
        ["gate_ov", "5 um", "solape del gate por lado - el parásito dominante"],
        ["sd_len", "97.5 um", "longitud del electrodo de S/D"],
        ["igzo_ext_x / _y", "10 / 5 um", "isla sobre el electrodo / más allá de su extremo"],
        ["pad", "off", "pads de 400x400 um + aberturas del dieléctrico"],
        ["l_bias", "3 um", "bias de dibujado a impreso, solo se reporta"],
        ["l_printed", "solo lectura", "l_gate + l_bias"],
        ["w_total", "solo lectura", "w_gate x nf"],
    ],
    # page 5
    "p5_kicker": "geometría",
    "p5_title": "En KLayout: el dispositivo",
    "p5_cap": "La zona del canal de tft_igzo_l10w100. En turquesa la isla de IGZO, en naranja "
              "los electrodos de S/D, en gris la franja de gate que los cruza. El hueco entre "
              "los dos electrodos naranjas es L; la altura en que enfrentan a la isla es W.",
    "p5_read": "Leído de la imagen, e idéntico a lo que dibuja el chip de prueba:",
    "p5_dims": [
        ["L = 10 um", "el hueco entre los electrodos de S/D"],
        ["W = 100 um", "la altura del electrodo, no la de la isla"],
        ["solape = 5 um", "cuánto se monta el gate sobre cada electrodo"],
        ["isla = 30 x 110 um", "10 um sobre cada electrodo en x, 5 um más allá en y"],
    ],
    "p5_h1": "El capacitor",
    "p5_capcap": "cap_mim_400x400: la placa inferior es metal de S/D bajando, la superior es "
                 "metal de gate cruzando de lado, y la capacitancia es su cruce de 400 x 400 um "
                 "- 250.2 pF medidos, de donde sale Cox = 1.564 fF/um2.",
    # page 6
    "p6_kicker": "esquemático",
    "p6_title": "En xschem",
    "p6_cap": "symbols/tft_igzo.sym. Tres pines en el orden D, G, S - el mismo orden en que el "
              "subcircuito igzo_tft los declara. No hay pin de bulk: un TFT esta sobre vidrio, y "
              "el envoltorio deja el bulk del dispositivo intrinseco atado a su propia fuente.",
    "p6_h1": "Qué netlist produce",
    "p6_expl":
        "W, L y ov son dimensiones dibujadas, en metros. spiceprefix=X porque el dispositivo es\n"
        "un subcircuito: el envoltorio añade la resistencia de contacto medida y la capacitancia\n"
        "de solape alrededor de un núcleo nivel 1, así que ov se puede barrer - que es el punto,\n"
        "porque el solape es lo que decide si una etapa sintonizada funciona.",
    "p6_tbcap": "tests/tft_iv.sch - el testbench de curvas de salida sobre el dispositivo con "
                "el que se validó el modelo (W = 1000 um, L = 8 um). El bloque MODELS trae los "
                "envoltorios y una esquina; el bloque NGSPICE lleva el barrido.",
    # page 7
    "p7_kicker": "layout y extracción",
    "p7_title": "En magic",
    "p7_cap": "tft_igzo_l10w100_pad en magic. En azul sdmetal, en rojo gatemetal, y los "
              "cuadros rayados dentro de los pads de S/D son las aberturas del dieléctrico. "
              "La paleta de capas de la derecha es este proceso, no uno MOS.",
    "p7_h1": "Cómo descompone magic el dispositivo",
    "p7_cap2": "Con zoom: electrodos sdmetal azules, sdcontact turquesa donde el Au toca el "
               "IGZO, el canal tftfet rayado entre ellos, muñones verdes de semiconductor "
               "arriba y abajo - el sobrante de la isla - y gatemetal rojo arriba y abajo.",
    # page 8
    "p8_kicker": "extracción y LVS",
    "p8_title": "En magic: qué sale",
    "p8_h1": "Extracción",
    "p8_w":
        "l sale exacta: 10 um, el hueco entre electrodos. w no, y la imagen de la página\n"
        "anterior explica por qué - el extractor mide la isla bajo el gate, y los muñones\n"
        "verdes están dibujados 5 um más allá de cada electrodo como margen de alineación.\n"
        "Están bajo el gate pero no llevan corriente de fuente a drenaje, así que el ancho\n"
        "real es la altura del electrodo, 100 um, mientras la extracción reporta ~13 % más.",
    "p8_w2":
        "Es una propiedad de cómo está dibujado el chip, no un fallo del deck. Una isla a ras\n"
        "de los electrodos extrae exacto. Mientras tanto, a netgen se le dice que lo tolere.",
    "p8_h2": "LVS",
    "p8_setup":
        "setup.tcl permuta fuente y drenaje, exige 1 % en l y admite 20 % en w, y explica en el\n"
        "propio archivo por qué las dos tolerancias son distintas. Poner mal W en el esquemático\n"
        "sí falla - se comprobó: W = 500u contra las 113 um extraídas reporta errores de\n"
        "propiedad en vez de pasar en silencio.",
    "p8_h3": "Tres terminales, de los dos lados",
    "p8_gnd":
        "Magic emite tres terminales porque la linea msubcircuit del techfile no lleva\n"
        "argumentos de sustrato. La otra forma, \"device subcircuit\", tambien emite tres - pero\n"
        "en el orden G S D, que discreparia del simbolo en silencio. El orden de pines es lo\n"
        "primero que revisa el LVS, y una compuerta cambiada es el unico error que aun simula.",
    # page 9
    "p9_kicker": "modelos",
    "p9_title": "En ngspice",
    "p9_intro": "Dos líneas traen el proceso. La primera son los envoltorios, la segunda una esquina:",
    "p9_xschem": "En xschem esas dos líneas usan $::IGZO_MODELS/... - la variable que fija el xschemrc del PDK.",
    "p9_h1": "Esquinas",
    "p9_corners": [
        ["Sección", "Qué es"],
        ["tt", "típica: mediana de todos los dispositivos buenos del mejor chip"],
        ["best", "canal largo del mejor chip, sin limitación por contacto"],
        ["short", "L <= 10 um, limitado por contacto; mejor usa tt con el envoltorio"],
        ["all", "sobre los tres chips, incluidos los malos - peor caso"],
    ],
    "p9_h2": "Qué añade el envoltorio",
    "p9_wrap": [
        ["Resistencia de contacto", "Rc = 3.3 Ohm*m / W por contacto, medida de R_on contra L"],
        ["Capacitancia de solape", "Cox * ov * W por lado; 7.82 fF por um de ancho con ov = 5 um"],
        ["Un bulk inerte", "b se sujeta con 1 Tohm; el núcleo ata su propio bulk a la fuente"],
    ],
    "p9_cgso":
        "Cgso y Cgdo valen cero en las tarjetas de modelo a propósito. La capacitancia de solape\n"
        "no es una propiedad solo del proceso - es Cox por el solape dibujado -, así que vive en\n"
        "el envoltorio, donde sigue a ov, en vez de quedar congelada en las 5 um del chip.",
    "p9_h3": "El número que dice que el modelo sigue sirviendo",
    "p9_val":
        "Es la misma cifra que reportó la extracción original, y run_checks.sh la verifica, así\n"
        "que un cambio en los modelos que la rompa falla de forma ruidosa.",
    # page 10
    "p10_kicker": "verificación",
    "p10_title": "Las cuatro herramientas coinciden",
    "p10_intro": "run_checks.sh corre toda la cadena y se detiene en el primer fallo:",
    "p10_checks": [
        ["Comprobación", "Herramienta", "Resultado"],
        ["PCell contra la celda fabricada", "klayout", "idéntico en las tres capas"],
        ["Tecnología y librería visibles", "klayout", "igzo_mmm_lab, igzo_mmm_lab_pr"],
        ["DRC sobre las primitivas generadas", "klayout", "limpio"],
        ["El símbolo netlista con D G S", "xschem", "orden de pines correcto"],
        ["Modelo contra la medición", "ngspice", "654.4 uA"],
        ["Ida y vuelta de GDS", "magic", "exacto por capa"],
        ["Extracción del dispositivo", "magic", "un igzo_tft, l = 10 um"],
        ["Layout contra esquemático", "netgen", "coinciden de forma única"],
    ],
    "p10_h1": "Lo que el PDK no sabe",
    "p10_limits":
        "1.  Los modelos son solo DC. Reproducen las curvas de salida medidas - mediana\n"
        "    simulado/medido = 1.01 sobre 18 dispositivos - y nada más se ha comprobado.\n"
        "    Cox está medida, pero ninguna medición C-V o de parámetros S respalda la AC.\n"
        "\n"
        "2.  El nivel 1 impone ley cuadrática; el exponente de saturación medido es 2.31, así\n"
        "    que el modelo es ~20 % pesimista en gm. Válido hasta VGS <= 6 V, VDS <= 10 V.\n"
        "\n"
        "3.  El bias de impresión de +3 um es una sola muestra. El PCell lo reporta, no lo aplica.\n"
        "\n"
        "4.  El deck de DRC es preliminar. Cada regla está medida o leída del chip de prueba;\n"
        "    no hay documento de reglas de foundry. 5 um es la dimensión mínima dibujada porque\n"
        "    el dispositivo más pequeño dibujado es de 5 um y se imprime a 8 um.\n"
        "\n"
        "5.  TFT2 no está representado: su exponente de saturación es 0.87, que ningún modelo\n"
        "    de ley cuadrática puede expresar.",
    "p10_h2": "Al correr el deck sobre el chip fabricado",
    "p10_drc": [
        ["La matriz de transistores", "limpia, salvo las celdas de 5 um - están dibujadas con"],
        ["", "3.5 um de solape de gate en lugar de 5 um"],
        ["Test_capacitance", "limpia"],
        ["Test_mobility", "viola varias reglas - es una estructura de medición,"],
        ["", "dibujada antes de que existiera regla alguna"],
    ],
    "p10_end":
        "Nada de esto es razón para no usar el PDK. Son las cosas que un PDK con aspecto de\n"
        "autoridad no debería esconder.",
}


def content(pdf, S, lang):
    """Lay out the ten pages from the string table S."""
    def page(key_title, key_kicker):
        return Page(pdf, S[key_title], kicker=S[key_kicker], footer=S["footer"])

    n = 1
    p = page("p1_title", "p1_kicker")
    p.text(S["p1_intro"], size=10)
    p.head(S["p1_h1"])
    p.text(S["p1_process"])
    p.table(S["p1_layers"], widths=[0.05, 0.14, 0.10, 0.71])
    p.head(S["p1_h2"])
    p.table(S["p1_where"], widths=[0.24, 0.76], header=False)
    p.image("klayout_screen_crop.png", S["p1_cap"])
    p.close(n)

    n += 1
    p = page("p2_title", "p2_kicker")
    p.text(S["p2_once"])
    p.code(CODE["install"][lang])
    p.text(S["p2_what"])
    p.head(S["p2_h1"])
    p.text(S["p2_why"])
    p.code(CODE["symlink"][lang])
    p.head(S["p2_h2"])
    p.text(S["p2_then"])
    p.code(CODE["usepdk"][lang])
    p.text(S["p2_one"])
    p.table(S["p2_vars"], widths=[0.24, 0.40, 0.36])
    p.head(S["p2_h3"])
    p.table(S["p2_tools"], widths=[0.16, 0.84], header=False)
    p.close(n)

    n += 1
    p = page("p3_title", "p3_kicker")
    p.text(S["p3_intro"])
    p.table(S["p3_cells"], widths=[0.30, 0.12, 0.58])
    p.head(S["p3_h1"])
    p.text(S["p3_gen"])
    p.code(CODE["generate"][lang])
    p.text(S["p3_nohand"])
    p.head(S["p3_h2"])
    p.text(S["p3_def"])
    p.code(CODE["regression"])
    p.head(S["p3_h3"])
    p.text(S["p3_name"])
    p.close(n)

    n += 1
    p = page("p4_title", "p4_kicker")
    p.text(S["p4_intro"])
    p.image("klayout_tft_pad.png", S["p4_cap"], width=0.80)
    p.head(S["p4_h1"])
    p.table(S["p4_params"], widths=[0.24, 0.16, 0.60])
    p.close(n)

    n += 1
    p = page("p5_title", "p5_kicker")
    p.image("klayout_tft_zoom.png", S["p5_cap"], width=0.92)
    p.text(S["p5_read"])
    p.table(S["p5_dims"], widths=[0.26, 0.74], header=False)
    p.head(S["p5_h1"])
    p.image("klayout_cap.png", S["p5_capcap"], width=0.62)
    p.close(n)

    n += 1
    p = page("p6_title", "p6_kicker")
    p.image("xschem_sym.png", S["p6_cap"], width=0.52)
    p.head(S["p6_h1"])
    p.code(CODE["netlist"])
    p.text(S["p6_expl"])
    p.image("xschem_tb.png", S["p6_tbcap"], width=0.95)
    p.close(n)

    n += 1
    p = page("p7_title", "p7_kicker")
    # the figures are already cropped to the magic window by make_figures.sh
    p.image("magic_screen_pad.png", S["p7_cap"], width=0.98)
    p.head(S["p7_h1"])
    p.image("magic_screen_core.png", S["p7_cap2"], width=0.98)
    p.close(n)

    n += 1
    p = page("p8_title", "p8_kicker")
    p.head(S["p8_h1"])
    p.code(CODE["extract"])
    p.text(S["p8_w"])
    p.text(S["p8_w2"])
    p.head(S["p8_h2"])
    p.code(CODE["lvs"])
    p.text(S["p8_setup"])
    p.head(S["p8_h3"])
    p.text(S["p8_gnd"])
    p.close(n)

    n += 1
    p = page("p9_title", "p9_kicker")
    p.text(S["p9_intro"])
    p.code(CODE["spice"])
    p.text(S["p9_xschem"])
    p.head(S["p9_h1"])
    p.table(S["p9_corners"], widths=[0.16, 0.84])
    p.head(S["p9_h2"])
    p.table(S["p9_wrap"], widths=[0.24, 0.76], header=False)
    p.text(S["p9_cgso"])
    p.head(S["p9_h3"])
    p.code(CODE["validation"][lang])
    p.text(S["p9_val"])
    p.close(n)

    n += 1
    p = page("p10_title", "p10_kicker")
    p.code(CODE["checks"])
    p.text(S["p10_intro"])
    p.table(S["p10_checks"], widths=[0.42, 0.18, 0.40])
    p.head(S["p10_h1"])
    p.text(S["p10_limits"])
    p.head(S["p10_h2"])
    p.table(S["p10_drc"], widths=[0.26, 0.74], header=False)
    p.text(S["p10_end"], color=MUTED)
    p.close(n)


def build(lang, out_dir=None):
    strings = {"en": EN, "es": ES}[lang]
    name = {"en": "TFT-MMM-LAB-PDK_cells_and_tools_en.pdf",
            "es": "TFT-MMM-LAB-PDK_celdas_y_herramientas_es.pdf"}[lang]
    out = os.path.join(default_out_dir(out_dir), name)
    with PdfPages(out) as pdf:
        content(pdf, strings, lang)
        info = pdf.infodict()
        info["Title"] = ("TFT-MMM-LAB-PDK - cells and tools" if lang == "en"
                         else "TFT-MMM-LAB-PDK - celdas y herramientas")
        info["Author"] = "UCI/INRF - MMM Lab"
        info["Subject"] = "IGZO TFT PDK (igzo_mmm_lab)"
    print("wrote %s (%d bytes)" % (out, os.path.getsize(out)))


if __name__ == "__main__":
    args = sys.argv[1:]
    out_dir = None
    if args and args[-1].startswith(("/", "~", ".")):
        out_dir = os.path.expanduser(args.pop())
    for lg in (args or ["en", "es"]):
        build(lg, out_dir)
