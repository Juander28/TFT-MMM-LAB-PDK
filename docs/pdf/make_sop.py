#!/usr/bin/env python3
"""
The standard operating procedure for the cells of TFT-MMM-LAB-PDK: every
parameter of every cell, what it does, and - the column that matters - where
its number comes from.

    python3 make_sop.py            # both languages
    python3 make_sop.py es ~/out   # one language, somewhere else

Figures come from ../figures; regenerate them with make_figures.sh.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from pdfkit import ACCENT, MUTED, Page, PdfPages, default_out_dir  # noqa: E402

# Where a number comes from.  Four kinds, and the document never blurs them.
EN_SRC = {"m": "measured", "c": "off the chip", "a": "ASSUMED", "d": "your choice"}
ES_SRC = {"m": "medido", "c": "del chip", "a": "SUPUESTO", "d": "tu decides"}


def _tft_rows(src):
    return [
        ["Parameter", "Default", "What it does", "Source"],
        ["w_gate", "100 um", "channel width per finger", src["d"]],
        ["l_gate", "10 um", "drawn channel length = electrode gap", src["d"]],
        ["nf", "1", "fingers; they share electrodes", src["d"]],
        ["gate_ov", "5 um", "gate overlap per side - the dominant parasitic", src["c"]],
        ["sd_len", "97.5 um", "S/D electrode length", src["c"]],
        ["igzo_ext_x", "10 um", "island over each electrode", src["c"]],
        ["igzo_ext_y", "5 um", "island past the electrode end", src["c"]],
        ["gate_ext_y", "10 um", "gate past the island", src["c"]],
        ["pad", "off", "400 x 400 um probe pads + dielectric windows", src["d"]],
        ["pad_size", "400 um", "pad side", src["c"]],
        ["pad_gap", "325 um", "clearance between S/D pads and gate pad", src["c"]],
        ["etch_inset", "20 um", "window inset inside the pad", src["c"]],
        ["l_bias", "3 um", "drawn-to-printed bias, reported not applied", src["a"]],
        ["l_printed", "read-only", "l_gate + l_bias", "-"],
        ["w_total", "read-only", "w_gate x nf", "-"],
    ]


def _cap_rows(src):
    return [
        ["Parameter", "Default", "What it does", "Source"],
        ["mode", "by dimensions", "which of W/L, area or C you set", src["d"]],
        ["w, l", "400 um", "plate, used in 'by dimensions'", src["d"]],
        ["area_target", "160000 um^2", "used in 'by area' - square plate", src["d"]],
        ["c_target", "250240 fF", "used in 'by capacitance' - square plate", src["d"]],
        ["ext_sd", "200 um", "S/D plate past the crossing, terminal side", src["d"]],
        ["ext_gate", "200 um", "gate plate past the crossing, terminal side", src["d"]],
        ["ext_sd_far", "0", "S/D plate past the crossing, opposite side", src["d"]],
        ["ext_gate_far", "0", "gate plate past the crossing, opposite side", src["d"]],
        ["pad", "off", "probe pad on the end of each plate", src["d"]],
        ["pad_size", "400 um", "pad side", src["c"]],
        ["etch_inset", "20 um", "window inset in the lower plate's tail", src["c"]],
        ["show_value", "on", "print the capacitance on layer 63/0", src["d"]],
        ["area, c", "read-only", "always Cox * W * L, Cox = 1.564 fF/um^2", src["m"]],
    ]


def _ind_rows(src):
    return [
        ["Parameter", "Default", "What it does", "Source"],
        ["shape", "square", "square or circular", src["d"]],
        ["topology", "series", "one spiral, or n rings in parallel", src["d"]],
        ["n", "8", "turns (series) or rings (parallel)", src["d"]],
        ["d_in", "100 um", "inner diameter", src["d"]],
        ["w", "10 um", "track width - sets R, barely touches L", src["d"]],
        ["gap", "5 um", "spacing between turns", src["d"]],
        ["metal", "gate (2/0)", "which gold to draw it on", src["d"]],
        ["t_metal", "0.05 um", "metal thickness - the lever on R", src["a"]],
        ["f_eval", "100 MHz", "frequency the R_ac and Q read-outs use", src["d"]],
        ["lead", "40 um", "terminal lead length", src["d"]],
        ["pad", "off", "probe pad on each terminal", src["d"]],
        ["pad_size", "200 um", "pad side", src["d"]],
        ["lbl", "on", "pins and labels A and B - needed for extraction", src["d"]],
        ["l_series", "read-only", "Mohan-Wheeler (series) or coupled rings", "-"],
        ["r_dc, r_ac", "read-only", "from the drawn track length and rho_Au", "-"],
        ["q, d_out, wire_len", "read-only", "Q at f_eval, outer size, track length", "-"],
    ]


EN = {
    "footer": "TFT-MMM-LAB-PDK  ·  cell SOP",
    "k": "UCI/INRF IGZO TFT process",
    "t1": "Standard operating procedure\nfor the cells",
    "intro":
        "Three parametric cells, and every parameter of each one: what it is,\n"
        "what moves when you move it, and where its default came from.\n\n"
        "That last column is the reason this document exists.  A PDK looks\n"
        "authoritative whether or not its numbers are: a default of 5 um reads\n"
        "the same whether it was measured on silicon, read off a drawing, or\n"
        "picked because it seemed reasonable.  Here they are labelled.",
    "srcs": [
        ["measured", "measured on this process, on these chips"],
        ["off the chip", "read off the fabricated test chip's GDS"],
        ["ASSUMED", "nobody has measured this - treat any result that leans on it as provisional"],
        ["your choice", "a design decision; nothing about the process fixes it"],
    ],
    "h_place": "Placing a cell",
    "place":
        "In KLayout: Instance (I), library igzo_mmm_lab_pr, one of tft_igzo,\n"
        "cap_mim, ind_igzo.  The parameters below appear in the instance dialog;\n"
        "the read-only ones update as you type.\n"
        "In xschem: the symbols are on the library path once use-pdk has run.\n"
        "Both are described cell by cell in the pages that follow.",
    "h_tft": "tft_igzo - the transistor",
    "tft_txt":
        "Three terminals, D G S, in that order.  There is no bulk: a TFT sits on\n"
        "glass, and the wrapper subcircuit keeps the intrinsic device's bulk tied\n"
        "to its own source.\n\n"
        "The defaults reproduce TFT-10L100W of the test chip shape for shape - so\n"
        "an unmodified tft_igzo is a device that has actually been fabricated and\n"
        "measured, not a guess at one.",
    "tft_cap": "Left: the drawn device with its probe pads. Right: the symbol.",
    "h_tftnote": "Two things worth knowing before you size one",
    "tftnote":
        "FINGERS DO NOTHING ELECTRICALLY.  nf splits the width and folds the\n"
        "layout; gm and Cgs split with it, so their ratio - and fT - do not move.\n"
        "Measured, then confirmed in simulation for nf = 1..20 at constant total\n"
        "width.  Use fingers for aspect ratio and gate resistance, not for speed.\n\n"
        "L IS THE DRAWN LENGTH.  The process prints it about 3 um longer.  The\n"
        "cell reports l_printed and leaves the geometry alone, because that +3 um\n"
        "is one measurement of one cell: applying it silently would assert more\n"
        "than anyone knows.  If you want the printed device, pass the printed L.",
    "h_model": "The model side of the same device",
    "model_txt":
        "In a netlist the device is a subcircuit call with its own parameters,\n"
        "which are not quite the PCell's:",
    "model_rows": [
        ["Netlist parameter", "Meaning"],
        ["W, L", "drawn width and length, in metres"],
        ["ov", "gate overlap per side; sets the overlap capacitance, Cox*ov*W"],
        ["nf", "carried for LVS only - it changes nothing electrically"],
        ["corner", "chosen by the .lib line, not by the instance"],
    ],
    "h_cap": "cap_mim - the capacitor",
    "cap_txt":
        "Set the plate, or the area, or the capacitance - whichever the problem\n"
        "hands you.  It is one formula solved in three directions:\n"
        "        C = Cox * W * L,   Cox = 1.564 fF/um^2 (measured)\n"
        "The two you did not set are read back, and the cell prints the result on\n"
        "itself on layer 63/0, which is annotation and never fabricated.",
    "cap_modes": [
        ["mode", "you set", "you get"],
        ["by dimensions", "w = l = 400 um", "area 160000 um^2, C = 250.2 pF"],
        ["by area", "area = 160000 um^2", "w = l = 400 um, C = 250.2 pF"],
        ["by capacitance", "c = 40362 fF", "w = l = 160.64 um, area 25805 um^2"],
    ],
    "h_ind": "ind_igzo - the inductor",
    "ind_txt":
        "Square or circular, and either one spiral in series or n concentric\n"
        "rings in parallel.  The estimates come from tools/coil_core.py - the\n"
        "same library as the coil calculator, so the two always agree - and the\n"
        "resistance is computed from the length of track actually drawn, leads\n"
        "included, rather than from a closed form for it.",
    "ind_topo": [
        ["shape / topology", "L", "R at 100 MHz", "Q"],
        ["square, series", "16.38 nH", "377.7 Ohm", "0.03"],
        ["circular, series", "20.59 nH", "312.6 Ohm", "0.04"],
        ["square, parallel", "129.6 pH", "5.00 Ohm", "0.02"],
        ["circular, parallel", "129.5 pH", "3.87 Ohm", "0.02"],
    ],
    "ind_topo_txt":
        "All four at the default size, n = 8, 50 nm of gold.  Parallel rings buy\n"
        "a low resistance and almost no inductance - they are a current path, not\n"
        "a tank element.  A circular spiral gives about 25 % more L than a square\n"
        "one of the same inner diameter, and slightly less resistance.",
    "h_thick": "The number that decides whether any of this is usable",
    "thick": [
        ["gold thickness", "R at 100 MHz", "Q", ""],
        ["50 nm (assumed today)", "377.7 Ohm", "0.03", ""],
        ["100 nm", "188.9 Ohm", "0.05", ""],
        ["250 nm", "75.5 Ohm", "0.14", ""],
        ["500 nm", "37.8 Ohm", "0.27", ""],
        ["1 um", "18.9 Ohm", "0.54", ""],
    ],
    "thick_txt":
        "Same coil, same inductance, thickness swept.  At the 50 nm the process\n"
        "is assumed to have, a planar inductor here is not a tank element - it is\n"
        "a resistor with some inductance.  Q scales with thickness and with\n"
        "nothing else you can draw.\n\n"
        "The 100 MHz tank in tests/tank_ac.sch shows the same thing end to end:\n"
        "263.5 nH with 9.61 pF resonates at 100.0 MHz in 1 um of gold, and in\n"
        "50 nm the peak does not exist at all.\n\n"
        "And the thickness itself is assumed.  Until somebody measures the gold,\n"
        "every resistance and every Q in this PDK is provisional - which is why\n"
        "t_metal is a parameter on the cell and not a constant inside it.",
    "h_via": "The layers, and the one rule that changed",
    "via_txt":
        "Four masks, in process order: igzo (4/0), sd (6/0), oxetch (5/0),\n"
        "gate (2/0), plus align (8/0) and text (63/0), which is annotation.\n\n"
        "oxetch does two jobs.  Over a pad with nothing above it, it is a probe\n"
        "window.  Under gate metal it is a VIA: the gate is deposited after the\n"
        "etch, so the two metals touch.  That is what lets a spiral inductor\n"
        "bring its inner end out, and it is why the DRC deck has via rules where\n"
        "it used to have a rule forbidding gate over an opening.",
    "rules": [
        ["Rule", "Value", "What it protects"],
        ["IGZO.1 / SD.1 / GATE.1", "5 um", "minimum drawn width of anything"],
        ["SD.2", "5 um", "S/D spacing - this is the drawn channel length"],
        ["GATE.2 / IGZO.3", "5 um", "spacing on gate and on the island"],
        ["GATE.3", "5 um", "gate overlap of the electrode, where there is a channel"],
        ["IGZO.2", "5 um", "S/D contact overlap on the IGZO"],
        ["OX.1 / OX.2", "- / 20 um", "openings land on metal; probe window inset"],
        ["VIA.1 / VIA.2 / VIA.3", "5 um", "via size, and both metals' enclosure of it"],
    ],
    "h_check": "Before you release anything",
    "check":
        "1.  DRC:    python3 libs.tech/klayout/tech/drc/run_drc.py --path x.gds\n"
        "2.  Extract in magic and read the netlist: the device should come out as\n"
        "    igzo_tft with the L you drew.  W will read about 13 % high, because\n"
        "    the extractor measures the gated island and the island is drawn past\n"
        "    the electrodes for alignment margin.\n"
        "3.  LVS through libs.tech/netgen/setup.tcl, which allows for exactly\n"
        "    that difference and holds L to 1 %.\n"
        "4.  ./scripts/run_checks.sh - the whole PDK, twelve checks, end to end.\n\n"
        "One known residual: the circular series inductor leaves seven violations\n"
        "where its inner terminal meets the first turn tangentially.  Every other\n"
        "cell in the library is clean.",
}

ES = {
    "footer": "TFT-MMM-LAB-PDK  ·  SOP de celdas",
    "k": "Proceso IGZO TFT de UCI/INRF",
    "t1": "Procedimiento de operacion\nde las celdas",
    "intro":
        "Tres celdas parametricas, y cada parametro de cada una: que es, que se\n"
        "mueve cuando lo mueves, y de donde salio su valor por defecto.\n\n"
        "Esa ultima columna es la razon de este documento.  Un PDK se ve\n"
        "autoritario tenga o no respaldo en sus numeros: un valor de 5 um se lee\n"
        "igual si se midio en silicio, si se leyo de un dibujo o si se eligio\n"
        "porque parecia razonable.  Aqui estan etiquetados.",
    "srcs": [
        ["medido", "medido en este proceso, en estos chips"],
        ["del chip", "leido del GDS del chip de prueba fabricado"],
        ["SUPUESTO", "nadie lo ha medido - todo resultado que dependa de esto es provisional"],
        ["tu decides", "una decision de diseno; el proceso no la fija"],
    ],
    "h_place": "Como instanciar una celda",
    "place":
        "En KLayout: Instance (I), libreria igzo_mmm_lab_pr, y una de tft_igzo,\n"
        "cap_mim, ind_igzo.  Los parametros de abajo aparecen en el dialogo de la\n"
        "instancia; los de solo lectura se actualizan mientras escribes.\n"
        "En xschem: los simbolos estan en la ruta de librerias en cuanto corre\n"
        "use-pdk.  Las paginas siguientes describen celda por celda.",
    "h_tft": "tft_igzo - el transistor",
    "tft_txt":
        "Tres terminales, D G S, en ese orden.  No hay bulk: un TFT esta sobre\n"
        "vidrio, y el subcircuito envoltorio deja el bulk del dispositivo\n"
        "intrinseco atado a su propia fuente.\n\n"
        "Los valores por defecto reproducen TFT-10L100W del chip de prueba forma\n"
        "por forma - asi que un tft_igzo sin modificar es un dispositivo que se\n"
        "fabrico y se midio de verdad, no una suposicion de uno.",
    "tft_cap": "Izquierda: el dispositivo dibujado con sus pads. Derecha: el simbolo.",
    "h_tftnote": "Dos cosas que conviene saber antes de dimensionarlo",
    "tftnote":
        "LOS DEDOS NO HACEN NADA ELECTRICAMENTE.  nf reparte el ancho y dobla el\n"
        "layout; gm y Cgs se reparten con el, asi que su relacion - y fT - no se\n"
        "mueven.  Medido, y confirmado en simulacion para nf = 1..20 a ancho total\n"
        "constante.  Usa dedos por forma y por resistencia de compuerta, no por\n"
        "velocidad.\n\n"
        "L ES LA LONGITUD DIBUJADA.  El proceso la imprime unas 3 um mas larga.\n"
        "La celda reporta l_printed y no toca la geometria, porque ese +3 um es\n"
        "una medicion de una celda: aplicarlo en silencio afirmaria mas de lo que\n"
        "se sabe.  Si quieres el dispositivo impreso, pasa la L impresa.",
    "h_model": "El lado de modelo del mismo dispositivo",
    "model_txt":
        "En un netlist el dispositivo es una llamada a subcircuito con sus propios\n"
        "parametros, que no son exactamente los del PCell:",
    "model_rows": [
        ["Parametro del netlist", "Significado"],
        ["W, L", "ancho y largo dibujados, en metros"],
        ["ov", "solape de compuerta por lado; fija la capacitancia Cox*ov*W"],
        ["nf", "se lleva solo para LVS - no cambia nada electricamente"],
        ["esquina", "la elige la linea .lib, no la instancia"],
    ],
    "h_cap": "cap_mim - el capacitor",
    "cap_txt":
        "Pon la placa, o el area, o la capacitancia - lo que te de el problema.\n"
        "Es una sola formula resuelta en tres direcciones:\n"
        "        C = Cox * W * L,   Cox = 1.564 fF/um^2 (medido)\n"
        "Las dos que no fijaste se leen de vuelta, y la celda escribe el resultado\n"
        "sobre si misma en la capa 63/0, que es anotacion y nunca se fabrica.",
    "cap_modes": [
        ["modo", "pones", "obtienes"],
        ["by dimensions", "w = l = 400 um", "area 160000 um^2, C = 250.2 pF"],
        ["by area", "area = 160000 um^2", "w = l = 400 um, C = 250.2 pF"],
        ["by capacitance", "c = 40362 fF", "w = l = 160.64 um, area 25805 um^2"],
    ],
    "h_ind": "ind_igzo - el inductor",
    "ind_txt":
        "Cuadrado o circular, y una espiral en serie o n anillos concentricos en\n"
        "paralelo.  Las estimaciones salen de tools/coil_core.py - la misma\n"
        "libreria del calculador de bobinas, asi que las dos siempre coinciden -\n"
        "y la resistencia se calcula con la longitud de pista realmente dibujada,\n"
        "salidas incluidas, no con una formula cerrada para ella.",
    "ind_topo": [
        ["forma / topologia", "L", "R a 100 MHz", "Q"],
        ["cuadrada, serie", "16.38 nH", "377.7 Ohm", "0.03"],
        ["circular, serie", "20.59 nH", "312.6 Ohm", "0.04"],
        ["cuadrada, paralelo", "129.6 pH", "5.00 Ohm", "0.02"],
        ["circular, paralelo", "129.5 pH", "3.87 Ohm", "0.02"],
    ],
    "ind_topo_txt":
        "Las cuatro al tamano por defecto, n = 8, 50 nm de oro.  Los anillos en\n"
        "paralelo compran baja resistencia y casi nada de inductancia - son un\n"
        "camino de corriente, no un elemento de tanque.  Una espiral circular da\n"
        "~25 % mas L que una cuadrada del mismo diametro interno, y algo menos de\n"
        "resistencia.",
    "h_thick": "El numero que decide si algo de esto sirve",
    "thick": [
        ["espesor de oro", "R a 100 MHz", "Q", ""],
        ["50 nm (lo supuesto hoy)", "377.7 Ohm", "0.03", ""],
        ["100 nm", "188.9 Ohm", "0.05", ""],
        ["250 nm", "75.5 Ohm", "0.14", ""],
        ["500 nm", "37.8 Ohm", "0.27", ""],
        ["1 um", "18.9 Ohm", "0.54", ""],
    ],
    "thick_txt":
        "La misma bobina, la misma inductancia, barriendo el espesor.  Con los\n"
        "50 nm que se le suponen al proceso, un inductor planar aqui no es un\n"
        "elemento de tanque - es una resistencia con algo de inductancia.  Q\n"
        "escala con el espesor y con nada mas que puedas dibujar.\n\n"
        "El tanque de 100 MHz de tests/tank_ac.sch muestra lo mismo de punta a\n"
        "punta: 263.5 nH con 9.61 pF resuenan a 100.0 MHz en 1 um de oro, y en\n"
        "50 nm el pico simplemente no existe.\n\n"
        "Y el espesor mismo es supuesto.  Hasta que alguien mida el oro, toda\n"
        "resistencia y todo Q de este PDK son provisionales - por eso t_metal es\n"
        "un parametro de la celda y no una constante dentro de ella.",
    "h_via": "Las capas, y la regla que cambio",
    "via_txt":
        "Cuatro mascaras, en orden de proceso: igzo (4/0), sd (6/0), oxetch (5/0),\n"
        "gate (2/0), mas align (8/0) y text (63/0), que es anotacion.\n\n"
        "oxetch hace dos trabajos.  Sobre un pad sin nada encima es una ventana de\n"
        "sonda.  Bajo metal de compuerta es una VIA: el gate se deposita despues\n"
        "del etch, asi que los dos metales se tocan.  Eso es lo que permite que\n"
        "una espiral saque su extremo interno, y por eso el deck de DRC tiene\n"
        "reglas de via donde antes tenia una que prohibia gate sobre una abertura.",
    "rules": [
        ["Regla", "Valor", "Que protege"],
        ["IGZO.1 / SD.1 / GATE.1", "5 um", "ancho minimo dibujado de cualquier cosa"],
        ["SD.2", "5 um", "separacion S/D - es la longitud de canal dibujada"],
        ["GATE.2 / IGZO.3", "5 um", "separacion en compuerta y en la isla"],
        ["GATE.3", "5 um", "solape de compuerta sobre el electrodo, donde hay canal"],
        ["IGZO.2", "5 um", "solape del contacto S/D sobre el IGZO"],
        ["OX.1 / OX.2", "- / 20 um", "las aberturas caen sobre metal; margen de ventana"],
        ["VIA.1 / VIA.2 / VIA.3", "5 um", "tamano de via y encierro de ambos metales"],
    ],
    "h_check": "Antes de liberar cualquier cosa",
    "check":
        "1.  DRC:    python3 libs.tech/klayout/tech/drc/run_drc.py --path x.gds\n"
        "2.  Extrae en magic y lee el netlist: el dispositivo debe salir como\n"
        "    igzo_tft con la L que dibujaste.  W saldra ~13 % alta, porque el\n"
        "    extractor mide la isla bajo compuerta y la isla se dibuja mas alla de\n"
        "    los electrodos por margen de alineacion.\n"
        "3.  LVS con libs.tech/netgen/setup.tcl, que admite exactamente esa\n"
        "    diferencia y exige 1 % en L.\n"
        "4.  ./scripts/run_checks.sh - todo el PDK, doce comprobaciones.\n\n"
        "Un residual conocido: el inductor circular en serie deja siete\n"
        "violaciones donde su terminal interno toca tangencialmente la primera\n"
        "vuelta.  Todas las demas celdas de la libreria salen limpias.",
}


EXTRA_EN = {
    "h": "Extraction, parasitics and LVS",
    "q1": "Can a netlist be extracted from layout, and LVS'd with netgen?",
    "a1":
        "Yes, and both are checked on every run of scripts/run_checks.sh.\n\n"
        "    magic -rcfile $PDKPATH/libs.tech/magic/igzo_mmm_lab.magicrc\n"
        "    load <cell> ; extract all ; ext2spice lvs ; ext2spice\n"
        "    netgen -batch lvs \"layout.spice cell\" \"schematic.spice cell\" \\\n"
        "                     $PDKPATH/libs.tech/netgen/setup.tcl\n\n"
        "The transistor extracts as an igzo_tft subcircuit with the L you drew\n"
        "and pins in D G S order, and LVS against the xschem netlist matches\n"
        "uniquely.  The capacitor extracts as a capacitance between its two\n"
        "ports.  The inductor does not extract as a device at all - see below.",
    "q2": "Can parasitic capacitance be extracted?",
    "a2":
        "Yes, and it is exact for this process because there is only one\n"
        "dielectric to know about:\n\n"
        "    ext2spice cthresh 0        (0 = keep every capacitance)\n\n"
        "Drawn 40.36 pF, extracted 40.3593 pF; drawn 250.24 pF, extracted\n"
        "0.25024 nF.  The same number appears wherever gate metal happens to\n"
        "run over S/D metal in a design, which is the parasitic worth having:\n"
        "at 1.564 fF/um^2 a crossing is not free.\n\n"
        "There is no substrate capacitance in this technology and the PDK does\n"
        "not invent one.  A TFT sits on glass; there is nothing underneath to\n"
        "couple to.",
    "q3": "Can parasitic resistance be extracted?",
    "a3":
        "Partly, and this is where the honest answer is longer than yes.\n\n"
        "The techfile carries the sheet resistance - 488 mOhm/square, which is\n"
        "gold at the assumed 50 nm - so anything that uses it gets the right\n"
        "number, and run_checks.sh asserts that it agrees with what the coil\n"
        "cell reports: 774 squares x 0.488 = 377.7 Ohm, which is what ind_igzo\n"
        "prints on itself.  Change the thickness and both move together.\n\n"
        "What does not work is magic's extresist pipeline.  On a coil it warns\n"
        "that the two ports are electrically shorted - which is true, a coil is\n"
        "a short at DC - and then crashes; on simpler shapes it produces no\n"
        "output.  So interconnect resistance in this PDK comes from the cell\n"
        "estimate and from the sheet resistance, not from extresist.  If you\n"
        "need it per-net on a real block, the route is squares x 0.488 Ohm on\n"
        "the geometry, not magic.",
    "h_ind": "What this means for an inductor in LVS",
    "ind":
        "A coil extracts as one net: its two terminals are the same piece of\n"
        "metal.  Nothing in the layout says 'inductor', because nothing in the\n"
        "layout is one - it is a wire whose shape happens to store energy.\n\n"
        "So an ind_igzo instance in a schematic will not match an extracted\n"
        "coil pin for pin.  Treat the coil as a black box for LVS: keep it as a\n"
        "fixed cell, compare the block around it, and check the coil itself by\n"
        "geometry - which is what the connectivity check in run_checks.sh does,\n"
        "after an inner ring was once left floating by a bus that started in\n"
        "the wrong place and nothing noticed.",
}

EXTRA_ES = {
    "h": "Extraccion, parasitos y LVS",
    "q1": "Se puede extraer netlist del layout y hacer LVS con netgen?",
    "a1":
        "Si, y las dos cosas se comprueban en cada corrida de\n"
        "scripts/run_checks.sh.\n\n"
        "    magic -rcfile $PDKPATH/libs.tech/magic/igzo_mmm_lab.magicrc\n"
        "    load <celda> ; extract all ; ext2spice lvs ; ext2spice\n"
        "    netgen -batch lvs \"layout.spice celda\" \"esquematico.spice celda\" \\\n"
        "                     $PDKPATH/libs.tech/netgen/setup.tcl\n\n"
        "El transistor sale como un subcircuito igzo_tft con la L que\n"
        "dibujaste y los pines en orden D G S, y el LVS contra el netlist de\n"
        "xschem cuadra de forma unica.  El capacitor sale como una capacitancia\n"
        "entre sus dos puertos.  El inductor no sale como dispositivo - ver\n"
        "abajo.",
    "q2": "Se puede extraer capacitancia parasita?",
    "a2":
        "Si, y en este proceso sale exacta porque solo hay un dielectrico que\n"
        "conocer:\n\n"
        "    ext2spice cthresh 0        (0 = conserva todas las capacitancias)\n\n"
        "Dibujados 40.36 pF, extraidos 40.3593 pF; dibujados 250.24 pF,\n"
        "extraidos 0.25024 nF.  El mismo numero aparece donde sea que el metal\n"
        "de compuerta cruce por encima del de S/D, que es el parasito que vale\n"
        "la pena tener: a 1.564 fF/um^2 un cruce no es gratis.\n\n"
        "No hay capacitancia al sustrato en esta tecnologia y el PDK no se la\n"
        "inventa.  Un TFT esta sobre vidrio; no hay nada debajo con que\n"
        "acoplarse.",
    "q3": "Se puede extraer resistencia parasita?",
    "a3":
        "En parte, y aqui la respuesta honesta es mas larga que un si.\n\n"
        "El techfile lleva la resistencia de hoja - 488 mOhm/cuadro, que es oro\n"
        "con los 50 nm supuestos - asi que lo que la use obtiene el numero\n"
        "correcto, y run_checks.sh verifica que coincide con lo que reporta la\n"
        "celda de la bobina: 774 cuadros x 0.488 = 377.7 Ohm, que es lo que\n"
        "ind_igzo escribe sobre si misma.  Cambia el espesor y las dos se\n"
        "mueven juntas.\n\n"
        "Lo que no funciona es el flujo extresist de magic.  En una bobina\n"
        "avisa que los dos puertos estan en corto - lo cual es cierto, una\n"
        "bobina es un corto en DC - y luego se cae; en formas mas simples no\n"
        "produce salida.  Asi que la resistencia de interconexion en este PDK\n"
        "sale de la estimacion de la celda y de la resistencia de hoja, no de\n"
        "extresist.  Si la necesitas por red en un bloque real, el camino es\n"
        "cuadros x 0.488 Ohm sobre la geometria, no magic.",
    "h_ind": "Que significa esto para un inductor en LVS",
    "ind":
        "Una bobina extrae como una sola red: sus dos terminales son el mismo\n"
        "pedazo de metal.  Nada en el layout dice 'inductor', porque nada en el\n"
        "layout lo es - es un cable cuya forma resulta almacenar energia.\n\n"
        "Asi que una instancia de ind_igzo en un esquematico no va a cuadrar\n"
        "pin a pin con una bobina extraida.  Trata la bobina como caja negra en\n"
        "el LVS: dejala como celda fija, compara el bloque alrededor, y revisa\n"
        "la bobina por geometria - que es lo que hace la comprobacion de\n"
        "conectividad de run_checks.sh, despues de que un anillo interno quedara\n"
        "flotando por un bus que empezaba en el lugar equivocado sin que nadie\n"
        "lo notara.",
}


def build(lang, out_dir=None):
    S = {"en": EN, "es": ES}[lang]
    src = EN_SRC if lang == "en" else ES_SRC
    name = {"en": "TFT-MMM-LAB-PDK_cell_sop_en.pdf",
            "es": "TFT-MMM-LAB-PDK_sop_de_celdas_es.pdf"}[lang]
    out = os.path.join(default_out_dir(out_dir), name)

    with PdfPages(out) as pdf:
        n = 1
        p = Page(pdf, S["t1"], kicker=S["k"], footer=S["footer"])
        p.text(S["intro"], size=9.6)
        p.table([[a, b] for a, b in S["srcs"]], widths=[0.18, 0.82], header=False)
        p.head(S["h_place"])
        p.text(S["place"])
        p.head(S["h_tft"])
        p.text(S["tft_txt"])
        p.image("xschem_sym.png", S["tft_cap"], width=0.42)
        p.close(n)

        n += 1
        p = Page(pdf, S["h_tft"], kicker=S["k"], footer=S["footer"])
        p.table(_tft_rows(src), widths=[0.17, 0.14, 0.50, 0.19])
        p.head(S["h_tftnote"])
        p.text(S["tftnote"])
        p.head(S["h_model"])
        p.text(S["model_txt"])
        p.table(S["model_rows"], widths=[0.24, 0.76])
        p.close(n)

        n += 1
        p = Page(pdf, S["h_cap"], kicker=S["k"], footer=S["footer"])
        p.text(S["cap_txt"])
        p.table(S["cap_modes"], widths=[0.22, 0.30, 0.48])
        p.table(_cap_rows(src), widths=[0.17, 0.17, 0.47, 0.19])
        p.image("klayout_cap_40p36.png",
                {"en": "cap_mim sized by capacitance: 40.36 pF, and it says so on itself.",
                 "es": "cap_mim dimensionado por capacitancia: 40.36 pF, y lo dice sobre si mismo."}[lang],
                width=0.5)
        p.close(n)

        n += 1
        p = Page(pdf, S["h_ind"], kicker=S["k"], footer=S["footer"])
        p.text(S["ind_txt"])
        p.table(_ind_rows(src), widths=[0.20, 0.15, 0.46, 0.19])
        p.image("klayout_ind_sq_series.png",
                {"en": "Series spiral: the turns on gate metal, the inner end taken out "
                       "underneath on S/D metal through two openings in the dielectric.",
                 "es": "Espiral en serie: las vueltas en metal de compuerta y el extremo "
                       "interno saliendo por debajo en metal S/D, por dos aberturas."}[lang],
                width=0.42)
        p.close(n)

        n += 1
        p = Page(pdf, S["h_ind"], kicker=S["k"], footer=S["footer"])
        p.table(S["ind_topo"], widths=[0.30, 0.20, 0.28, 0.22])
        p.text(S["ind_topo_txt"])
        p.image("klayout_ind_sq_parallel.png",
                {"en": "Parallel rings: cut at the same angle, both buses running out "
                       "through the slot. No via needed - nothing crosses.",
                 "es": "Anillos en paralelo: cortados al mismo angulo y los dos buses "
                       "saliendo por la ranura. No hace falta via - nada se cruza."}[lang],
                width=0.42)
        p.head(S["h_thick"])
        p.table(S["thick"], widths=[0.34, 0.24, 0.14, 0.28])
        p.close(n)

        n += 1
        p = Page(pdf, S["h_thick"], kicker=S["k"], footer=S["footer"])
        p.text(S["thick_txt"])
        p.image("xschem_tank.png",
                {"en": "tests/tank_ac.sch - the three cells together.",
                 "es": "tests/tank_ac.sch - las tres celdas juntas."}[lang], width=0.95)
        p.close(n)

        n += 1
        X = EXTRA_EN if lang == "en" else EXTRA_ES
        p = Page(pdf, X["h"], kicker=S["k"], footer=S["footer"])
        p.head(X["q1"])
        p.text(X["a1"])
        p.head(X["q2"])
        p.text(X["a2"])
        p.close(n)

        n += 1
        p = Page(pdf, X["h"], kicker=S["k"], footer=S["footer"])
        p.head(X["q3"])
        p.text(X["a3"])
        p.head(X["h_ind"])
        p.text(X["ind"])
        p.close(n)

        n += 1
        p = Page(pdf, S["h_via"], kicker=S["k"], footer=S["footer"])
        p.text(S["via_txt"])
        p.table(S["rules"], widths=[0.30, 0.16, 0.54])
        p.head(S["h_check"])
        p.text(S["check"])
        p.close(n)

        info = pdf.infodict()
        info["Title"] = ("TFT-MMM-LAB-PDK - cell SOP" if lang == "en"
                         else "TFT-MMM-LAB-PDK - SOP de celdas")
        info["Author"] = "UCI/INRF - MMM Lab"
    print("wrote %s (%d bytes)" % (out, os.path.getsize(out)))


if __name__ == "__main__":
    args = sys.argv[1:]
    out_dir = None
    if args and args[-1].startswith(("/", "~", ".")):
        out_dir = os.path.expanduser(args.pop())
    for lg in (args or ["en", "es"]):
        build(lg, out_dir)
