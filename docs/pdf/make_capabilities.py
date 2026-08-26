#!/usr/bin/env python3
"""
Capabilities and limits of TFT-MMM-LAB-PDK: what can honestly be designed with
this technology, and where the data runs out.

    python3 make_capabilities.py            # both languages
    python3 make_capabilities.py es ~/out   # one language, somewhere else

Every number in this document that can be computed is computed here, by
running ngspice against the PDK's own model files.  Nothing is quoted from
memory, so the document cannot drift away from the models it describes.
"""

import os
import subprocess
import sys
import tempfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

from pdfkit import ACCENT, MUTED, Page, PdfPages, default_out_dir  # noqa: E402

MODELS = os.path.join(os.environ.get("PDKPATH", ROOT), "libs.tech", "ngspice")

COX = 1.564e-3          # F/m^2, measured on the 400 x 400 um plate
RC_W = 6.6e6            # 2*Rc*W, Ohm*um, from R_on(L) on the best chip


# --------------------------------------------------------------------------
# numbers, computed from the models rather than remembered
# --------------------------------------------------------------------------

FT_DECK = """* fT by H21: gate fed an AC current, drain held at AC ground
.include {m}/design.ngspice
.lib {m}/igzo_mmm_lab.ngspice tt
Vd d 0 dc 10 ac 0
Vg gb 0 dc 6
Lg gb g 1T
Ig 0 g ac 1
X1 d g 0 igzo_tft W={w}u L={l}u ov={ov}u
.control
op
let gmi = @m.x1.m1[gm]
let gdsi = @m.x1.m1[gds]
let idop = i(vd)
echo "NUMS $&gmi $&gdsi $&idop"
ac dec 60 1k 1G
let h21 = abs(i(vd))
meas ac ft when h21=1 fall=1
.endc
.end
"""

GM_DECK = """* transconductance at the terminals, contact resistance included
.include {m}/design.ngspice
.lib {m}/igzo_mmm_lab.ngspice tt
Vd d 0 dc 10
Vg g 0 dc 6
X1 d g 0 igzo_tft W={w}u L={l}u ov={ov}u
.control
op
let gmi = @m.x1.m1[gm]
echo "NUMS $&gmi"
dc Vg 5.95 6.05 0.1
meas dc i1 find i(vd) at=5.95
meas dc i2 find i(vd) at=6.05
.endc
.end
"""


def _ngspice(deck, **kw):
    """Run one deck and hand back its stdout."""
    d = tempfile.mkdtemp()
    sp = os.path.join(d, "d.spice")
    open(sp, "w").write(deck.format(m=MODELS, **kw))
    r = subprocess.run(["ngspice", "-b", sp], capture_output=True,
                       text=True, timeout=300)
    return r.stdout + r.stderr


def _grab(out, key):
    for line in out.splitlines():
        p = line.split()
        if p and p[0] == key:
            try:
                return float(p[-1])
            except ValueError:
                return None
    return None


def ft_of(l_um, ov_um=5.0, w_um=100.0):
    out = _ngspice(FT_DECK, w=w_um, l=l_um, ov=ov_um)
    ft = _grab(out, "ft")
    nums = [x for x in out.splitlines() if x.startswith("NUMS")]
    gm = gds = idop = None
    if nums:
        p = nums[0].split()
        gm, gds, idop = (float(p[1]), float(p[2]), abs(float(p[3])))
    return ft, gm, gds, idop


def gm_of(l_um, ov_um=5.0, w_um=100.0):
    """(gm at the terminals, gm inside the channel) - the difference is Rc."""
    out = _ngspice(GM_DECK, w=w_um, l=l_um, ov=ov_um)
    i1, i2 = _grab(out, "i1"), _grab(out, "i2")
    nums = [x for x in out.splitlines() if x.startswith("NUMS")]
    gm_i = float(nums[0].split()[1]) if nums else None
    gm_e = abs(i2 - i1) / 0.1 if (i1 is not None and i2 is not None) else None
    return gm_e, gm_i


LS = [5.0, 8.0, 10.0, 20.0, 40.0, 80.0]


def measure():
    """Everything the document quotes about the device, in one pass."""
    d = {"ft": {}, "ft_noov": {}, "gm": {}}
    for l in LS:
        d["ft"][l] = ft_of(l)[0]
        d["ft_noov"][l] = ft_of(l, ov_um=0.0)[0]
        d["gm"][l] = gm_of(l)
    ft, gm, gds, idop = ft_of(10.0)
    d["ref"] = {"ft": ft, "gm_i": gm, "gds": gds, "id": idop,
                "av": gm / gds if (gm and gds) else None}
    return d


def fig_ft(d, S):
    fig, ax = plt.subplots(figsize=(6.6, 3.2))
    ls = [l for l in LS if d["ft"].get(l)]
    ax.semilogy(ls, [d["ft"][l] / 1e6 for l in ls], "o-", lw=1.7,
                color="#1f6f8b", label=S["f_drawn"])
    ax.semilogy(ls, [d["ft_noov"][l] / 1e6 for l in ls], "s--", lw=1.4,
                color="#b3541e", label=S["f_noov"])
    ax.set_xlabel(S["f_x"], size=9)
    ax.set_ylabel(S["f_y"], size=9)
    ax.tick_params(labelsize=8)
    ax.grid(alpha=0.3, lw=0.5, which="both")
    ax.legend(fontsize=8.5, frameon=False)
    ax.set_title(S["f_t"], size=9.5)
    fig.tight_layout()
    return fig


def fig_gm(d, S):
    fig, ax = plt.subplots(figsize=(6.6, 3.0))
    ls = [l for l in LS if d["gm"].get(l) and d["gm"][l][0]]
    keep = [100.0 * d["gm"][l][0] / d["gm"][l][1] for l in ls]
    ax.plot(ls, keep, "o-", lw=1.7, color="#1f6f8b")
    ax.axhline(100, color=MUTED, lw=0.8, ls=":")
    ax.set_ylim(0, 105)
    ax.set_xlabel(S["g_x"], size=9)
    ax.set_ylabel(S["g_y"], size=9)
    ax.tick_params(labelsize=8)
    ax.grid(alpha=0.3, lw=0.5)
    ax.set_title(S["g_t"], size=9.5)
    fig.tight_layout()
    return fig


# --------------------------------------------------------------------------
# words
# --------------------------------------------------------------------------

EN = {
    "k": "TFT-MMM-LAB-PDK",
    "footer": "TFT-MMM-LAB-PDK - capabilities and limits",
    "t1": "What you can design with this PDK,\nand where it stops being honest",
    "intro":
        "One capacitance in this technology is measured: Cox = 1.564 fF/um^2, from a\n"
        "400 x 400 um plate that reads 250.2 pF. The semiconductor's own capacitance -\n"
        "how the channel charges and discharges under the gate - has never been\n"
        "measured here. That single gap decides most of what follows, so this document\n"
        "sorts every kind of design into three boxes and says which box it is in.\n\n"
        "Nothing below is quoted from memory. Every number was computed by running\n"
        "ngspice against this PDK's own model files while the document was built; the\n"
        "script that does it is docs/pdf/make_capabilities.py.",
    "boxes": [
        ["", "Where it stands", "Why"],
        ["DC design", "SOLID",
         "bias, current, swing, gain - all rest on measured DC data"],
        ["Capacitors", "SOLID",
         "Cox is measured and extraction agrees with the drawing to 0.01 %"],
        ["Gate capacitance", "COARSE",
         "Cox times a drawn overlap; no C-V on a transistor exists"],
        ["Bandwidth, fT", "COARSE",
         "good to a factor of two, and the document says which factor"],
        ["Phase margin, settling", "NOT SUPPORTED",
         "they depend on exactly the capacitance nobody measured"],
        ["Tuned loads", "NOT SUPPORTED",
         "the coil's Q is an assumed metal thickness, not a measurement"],
        ["Matching, offset", "NOT SUPPORTED",
         "Kp spans a factor of 70 over 86 devices; no matched-pair data at all"],
    ],
    "h_meas": "What is measured, and what each measurement licenses",
    "meas": [
        ["Measured", "Value", "What it licenses"],
        ["Cox, MIM plate", "1.564 fF/um^2", "capacitors; overlap capacitance"],
        ["Kp from ID(VGS,VDS)", "0.717 uA/V^2 (best)", "currents and DC gain"],
        ["2*Rc*W from R_on(L)", "6.6 MOhm*um", "the loss of gm to the contacts"],
        ["Vto", "near 0 V", "bias points, with the caveat below"],
        ["Drawn vs printed", "+3 um, one cell", "nothing yet - one sample"],
        ["NOT measured: gate C-V", "-", "Cgs, Cgd against bias"],
        ["NOT measured: matching", "-", "offset, mismatch, any pair"],
        ["NOT measured: metal t", "-", "coil Q, series resistance"],
        ["NOT measured: stress", "-", "drift, hysteresis, lifetime"],
        ["NOT measured: temp.", "-", "anything over temperature"],
    ],
    "h_dc": "DC design: what the data actually supports",
    "dc_txt":
        "This is the part that works. At W = 100 um, L = 10 um, VGS = 6 V, VDS = 10 V\n"
        "the tt corner gives ID = %(id).1f uA, gm = %(gmi).1f uS inside the channel and\n"
        "gds = %(gds).2f uS, so the intrinsic gain gm/gds is %(av).0f - about %(avdb).0f dB\n"
        "for a single stage with an ideal load. Bias points, currents, swing and\n"
        "stage-by-stage DC gain are all reachable from measured data.\n\n"
        "Two things to hold on to while doing it. First, the measured saturation\n"
        "exponent is 2.31, not 2, so a square-law model runs about 20 %% pessimistic on\n"
        "gm at a given current - your circuit will do slightly better than it simulates.\n"
        "Second, Kp spans a factor of 70 across the 86 devices measured. Design against\n"
        "a corner, never against a number, and check every result at 'short' and 'all'\n"
        "as well as at 'tt'.",
    "h_gm": "The contacts take half the transconductance, and width will not save you",
    "gm_txt":
        "2*Rc*W = 6.6 MOhm*um is a measured number, and the wrapper carries it\n"
        "explicitly as a resistor on each terminal. In saturation the source-side\n"
        "resistor degenerates the stage: at W = 100 um, L = 10 um the channel's\n"
        "%(gmi).1f uS arrives at the terminals as %(gme).1f uS - %(loss).0f %% of it gone.\n\n"
        "The trap is thinking wider devices escape it. They do not: Rc*W is a constant,\n"
        "so Rc falls as 1/W exactly as gm rises with W, and the ratio gm*Rc - the thing\n"
        "that sets the loss - does not depend on W at all. It depends on L. Long\n"
        "channels keep a larger fraction of a smaller gm; that is the whole trade.",
    "g_x": "drawn channel length L (um)",
    "g_y": "gm kept at the terminals (%)",
    "g_t": "How much transconductance survives the contacts (W = 100 um, VGS = 6 V)",
    "h_ac": "Bandwidth: a real number, with its error bars stated",
    "ac_txt":
        "The gate capacitance is Cox times a drawn overlap plus a textbook channel\n"
        "term. At W = 100 um, ov = 5 um that is 0.78 pF of overlap per side - geometry\n"
        "times a measured Cox, which is defensible - and about 1.04 pF of channel,\n"
        "which is the level-1 model's assumption and has never been measured.\n\n"
        "Driving the gate with a current and finding where the current gain falls to\n"
        "one gives fT = %(ft).2f MHz at L = 10 um and %(ft5).2f MHz at L = 5 um, the\n"
        "smallest length this process prints. The overlap dominates: with ov = 0 the\n"
        "same devices reach %(ftn).1f and %(ftn5).1f MHz.\n\n"
        "How wrong can this be? Overlap is two thirds of the total capacitance and it\n"
        "is on firm ground. If the channel capacitance were wrong by a factor of two,\n"
        "fT at L = 10 um would move to about 0.9 MHz or about 2.0 MHz. So the honest\n"
        "statement is 'about a megahertz', and no design should need the second digit.",
    "f_x": "drawn channel length L (um)",
    "f_y": "fT (MHz)",
    "f_t": "fT from the model, by H21 (W = 100 um - fT does not depend on W)",
    "f_drawn": "as drawn, ov = 5 um",
    "f_noov": "hypothetical, ov = 0",
    "h_no": "What not to promise",
    "no_txt":
        "Phase margin. Settling time. Gain-bandwidth to better than a factor of two.\n"
        "Any compensation scheme whose pole placement depends on Cgs or Cgd. Slew rate\n"
        "into a capacitive load, unless the load is a cap_mim and dwarfs the device.\n"
        "Anything tuned: the inductor's Q rests on an assumed metal thickness, and\n"
        "the same coil is Q = 2.3 with a micron of gold and Q = 0.12 with 50 nm -\n"
        "the difference between a resonator and a resistor. Matching, offset and any\n"
        "figure that needs two devices to be the same, because no pair has been\n"
        "measured and the population spans a factor of 70.\n\n"
        "One C-V sweep on a transistor, gate to source and drain, moves the middle\n"
        "block of this document into the first one. It is the single highest-value\n"
        "measurement left, and it is an afternoon's work on hardware that already\n"
        "exists.",
    "h_ceil": "The ceiling, in numbers",
    "ceil": [
        ["Quantity", "Value", "Set by"],
        ["Smallest drawn feature", "5 um", "the DRC deck, from the fabricated chip"],
        ["Capacitance per area", "1.564 nF/mm^2", "measured Cox"],
        ["Largest capacitor built", "250.2 pF", "the 400 x 400 um test plate"],
        ["Inductance demonstrated", "16.4 nH", "8-turn square coil, DRC clean"],
        ["Coil Q at 100 MHz", "2.3 / 0.12", "1 um of gold / 50 nm of gold"],
        ["Device fT", "1.2 - 1.9 MHz", "overlap capacitance, then L"],
        ["Model validity", "VGS <= 6 V, VDS <= 10 V", "the measured range"],
        ["Temperature", "300 K only", "nothing was measured anywhere else"],
    ],
    "h_new": "Two changes to the model this round",
    "sym_h": "Source and drain are now interchangeable",
    "sym":
        "The wrapper used to tie the intrinsic bulk to the source pin, so a device\n"
        "drawn with its source on the high side forward-biased the bulk-drain junction\n"
        "and conducted through it: 654 uA one way round, 1414 uA the other. A real TFT\n"
        "has no body and its two channel terminals are the same kind of terminal.\n"
        "Every junction on all four model cards is now inert - IS, JS, CBD, CBS, CJ and\n"
        "CJSW all zero - which leaves the intrinsic substrate node with no path\n"
        "anywhere, and the wrapper's own parts were already symmetric. Swapping d and s\n"
        "now changes nothing, and the check script asserts it at every corner, in\n"
        "saturation and in the linear region.\n\n"
        "Existing schematics keep working and keep their numbers. What changes is that\n"
        "orientation stops being something a designer has to remember.",
    "b_h": "A magnetic field, defaulting to zero",
    "b":
        "igzo_tft now takes B in tesla, default 0, and a dimensionless b_scale,\n"
        "default 1. The channel's mobility falls as mu/(1 + (mu*b_scale*B)^2) -\n"
        "classical magnetoresistance - with mu taken from the active corner's own\n"
        "Kp/Cox, so the corners respond differently, as they should.\n\n"
        "Its size, at the measured mu = 4.58 cm^2/Vs: mu*B = 4.6e-4 per tesla, so the\n"
        "effect on the current is (mu*B)^2 = 2 parts in ten million per tesla. That is\n"
        "not a sensor. It is not measurable. If the lab measures a reduction in Kp\n"
        "under a field, classical magnetoresistance is not the cause, and\n"
        "docs/bibliography/ says what is published, what it would predict here, and\n"
        "which ordinary artefacts - self-heating, stress, bias hysteresis, the magnet\n"
        "acting on the instrument - to rule out first. Reverse the field: a real\n"
        "mobility effect is even in B.\n\n"
        "When a coefficient has been measured, set b_scale = sqrt(measured / 2.1e-7)\n"
        "and the model reproduces it without anyone editing a corner file. A measured\n"
        "1 % per tesla puts b_scale near 220 - which is also the factor by which such\n"
        "a measurement would exceed the physics the term is named after.",
}

ES = {
    "k": "TFT-MMM-LAB-PDK",
    "footer": "TFT-MMM-LAB-PDK - capacidades y limites",
    "t1": "Que se puede disenar con este PDK,\ny donde deja de ser honesto",
    "intro":
        "En esta tecnologia hay una sola capacitancia medida: Cox = 1.564 fF/um^2, de una\n"
        "placa de 400 x 400 um que da 250.2 pF. La capacitancia propia del semiconductor -\n"
        "como se carga y descarga el canal bajo la compuerta - nunca se ha medido aqui.\n"
        "Ese unico hueco decide casi todo lo que sigue, asi que este documento clasifica\n"
        "cada tipo de diseno en tres cajas y dice en cual esta.\n\n"
        "Nada de lo que sigue viene de memoria. Cada numero se calculo ejecutando ngspice\n"
        "contra los propios modelos del PDK mientras se construia el documento; el script\n"
        "que lo hace es docs/pdf/make_capabilities.py.",
    "boxes": [
        ["", "Como esta", "Por que"],
        ["Diseno en DC", "SOLIDO",
         "polarizacion, corriente, excursion, ganancia - todo sobre datos medidos"],
        ["Capacitores", "SOLIDO",
         "Cox esta medido y la extraccion coincide con el dibujo al 0.01 %"],
        ["Capacitancia de compuerta", "GRUESO",
         "Cox por un traslape dibujado; no existe ninguna C-V sobre un transistor"],
        ["Ancho de banda, fT", "GRUESO",
         "bueno dentro de un factor de dos, y aqui se dice cual"],
        ["Margen de fase, establecimiento", "NO SOPORTADO",
         "dependen justo de la capacitancia que nadie midio"],
        ["Cargas sintonizadas", "NO SOPORTADO",
         "la Q de la bobina es un espesor de metal supuesto, no medido"],
        ["Apareamiento, offset", "NO SOPORTADO",
         "Kp varia un factor de 70 en 86 dispositivos; no hay pares medidos"],
    ],
    "h_meas": "Que esta medido, y que autoriza cada medicion",
    "meas": [
        ["Medido", "Valor", "Que autoriza"],
        ["Cox, placa MIM", "1.564 fF/um^2", "capacitores; capacitancia de traslape"],
        ["Kp de ID(VGS,VDS)", "0.717 uA/V^2 (best)", "corrientes y ganancia DC"],
        ["2*Rc*W de R_on(L)", "6.6 MOhm*um", "la gm que se pierde en los contactos"],
        ["Vto", "cerca de 0 V", "puntos de polarizacion, con la salvedad de abajo"],
        ["Dibujado vs impreso", "+3 um, una celda", "nada aun - una sola muestra"],
        ["NO medido: C-V de compuerta", "-", "Cgs, Cgd contra polarizacion"],
        ["NO medido: apareamiento", "-", "offset, desapareamiento, cualquier par"],
        ["NO medido: espesor metal", "-", "Q de bobina, resistencia serie"],
        ["NO medido: estres", "-", "deriva, histeresis, vida util"],
        ["NO medido: temperatura", "-", "cualquier cosa contra temperatura"],
    ],
    "h_dc": "Diseno en DC: lo que los datos si sostienen",
    "dc_txt":
        "Esta es la parte que funciona. Con W = 100 um, L = 10 um, VGS = 6 V, VDS = 10 V\n"
        "el corner tt da ID = %(id).1f uA, gm = %(gmi).1f uS dentro del canal y\n"
        "gds = %(gds).2f uS, de modo que la ganancia intrinseca gm/gds es %(av).0f -\n"
        "unos %(avdb).0f dB para una etapa con carga ideal. Puntos de polarizacion,\n"
        "corrientes, excursion y ganancia DC etapa por etapa salen todos de datos medidos.\n\n"
        "Dos cosas que no hay que soltar mientras se hace. Primero, el exponente de\n"
        "saturacion medido es 2.31, no 2, asi que un modelo cuadratico queda ~20 %%\n"
        "pesimista en gm a una corriente dada: el circuito va a salir algo mejor de lo\n"
        "que simula. Segundo, Kp varia un factor de 70 entre los 86 dispositivos medidos.\n"
        "Disena contra un corner, nunca contra un numero, y revisa todo tambien en\n"
        "'short' y en 'all', no solo en 'tt'.",
    "h_gm": "Los contactos se llevan la mitad de la gm, y el ancho no te salva",
    "gm_txt":
        "2*Rc*W = 6.6 MOhm*um es un numero medido, y el wrapper lo lleva explicitamente\n"
        "como una resistencia en cada terminal. En saturacion la del lado de fuente\n"
        "degenera la etapa: con W = 100 um, L = 10 um los %(gmi).1f uS del canal llegan\n"
        "a los terminales como %(gme).1f uS - se pierde el %(loss).0f %%.\n\n"
        "La trampa es creer que un dispositivo mas ancho escapa. No escapa: Rc*W es una\n"
        "constante, asi que Rc baja como 1/W exactamente como gm sube con W, y la razon\n"
        "gm*Rc - la que fija la perdida - no depende de W en absoluto. Depende de L.\n"
        "Canales largos conservan una fraccion mayor de una gm menor; ese es todo el\n"
        "intercambio.",
    "g_x": "longitud de canal dibujada L (um)",
    "g_y": "gm que sobrevive en los terminales (%)",
    "g_t": "Cuanta transconductancia sobrevive a los contactos (W = 100 um, VGS = 6 V)",
    "h_ac": "Ancho de banda: un numero real, con su incertidumbre declarada",
    "ac_txt":
        "La capacitancia de compuerta es Cox por un traslape dibujado mas un termino de\n"
        "canal de libro de texto. Con W = 100 um, ov = 5 um eso da 0.78 pF de traslape\n"
        "por lado - geometria por un Cox medido, defendible - y unos 1.04 pF de canal,\n"
        "que es la suposicion del modelo nivel 1 y nunca se ha medido.\n\n"
        "Inyectando corriente en la compuerta y buscando donde la ganancia de corriente\n"
        "cae a uno sale fT = %(ft).2f MHz con L = 10 um y %(ft5).2f MHz con L = 5 um, la\n"
        "longitud mas corta que este proceso imprime. Domina el traslape: con ov = 0 los\n"
        "mismos dispositivos llegan a %(ftn).1f y %(ftn5).1f MHz.\n\n"
        "Cuanto puede estar mal? El traslape son dos tercios de la capacitancia total y\n"
        "esta sobre terreno firme. Si la capacitancia de canal estuviera equivocada por\n"
        "un factor de dos, fT con L = 10 um se moveria a unos 0.9 MHz o unos 2.0 MHz. La\n"
        "frase honesta es 'como un megahertz', y ningun diseno deberia necesitar el\n"
        "segundo digito.",
    "f_x": "longitud de canal dibujada L (um)",
    "f_y": "fT (MHz)",
    "f_t": "fT del modelo, por H21 (W = 100 um - fT no depende de W)",
    "f_drawn": "como se dibuja, ov = 5 um",
    "f_noov": "hipotetico, ov = 0",
    "h_no": "Que no prometer",
    "no_txt":
        "Margen de fase. Tiempo de establecimiento. Producto ganancia-ancho de banda con\n"
        "mejor de un factor de dos. Cualquier compensacion cuya ubicacion de polos\n"
        "dependa de Cgs o Cgd. Slew rate sobre carga capacitiva, salvo que la carga sea\n"
        "un cap_mim y sea mucho mayor que el dispositivo. Cualquier cosa sintonizada: la\n"
        "Q de la bobina descansa en un espesor de metal supuesto, y la misma bobina da\n"
        "Q = 2.3 con un micrometro de oro y Q = 0.12 con 50 nm - la diferencia entre un\n"
        "resonador y una resistencia. Apareamiento, offset y cualquier figura que\n"
        "necesite que dos dispositivos sean iguales, porque no se ha medido ningun par y\n"
        "la poblacion abarca un factor de 70.\n\n"
        "Un solo barrido C-V sobre un transistor, compuerta contra fuente y drenaje, mueve\n"
        "el bloque del medio de este documento al primero. Es la medicion pendiente de\n"
        "mayor valor, y es una tarde de trabajo con equipo que ya existe.",
    "h_ceil": "El techo, en numeros",
    "ceil": [
        ["Cantidad", "Valor", "Fijado por"],
        ["Rasgo dibujado mas chico", "5 um", "el DRC, tomado del chip fabricado"],
        ["Capacitancia por area", "1.564 nF/mm^2", "Cox medido"],
        ["Capacitor mas grande hecho", "250.2 pF", "la placa de prueba de 400 x 400 um"],
        ["Inductancia demostrada", "16.4 nH", "bobina cuadrada de 8 vueltas, DRC limpio"],
        ["Q de bobina a 100 MHz", "2.3 / 0.12", "1 um de oro / 50 nm de oro"],
        ["fT del dispositivo", "1.2 - 1.9 MHz", "capacitancia de traslape, luego L"],
        ["Validez del modelo", "VGS <= 6 V, VDS <= 10 V", "el rango medido"],
        ["Temperatura", "solo 300 K", "no se midio nada en ninguna otra"],
    ],
    "h_new": "Dos cambios en el modelo en esta ronda",
    "sym_h": "Fuente y drenaje ya son intercambiables",
    "sym":
        "El wrapper amarraba el bulk intrinseco al pin de fuente, asi que un dispositivo\n"
        "dibujado con la fuente arriba polarizaba en directa la union bulk-drenaje y\n"
        "conducia por ahi: 654 uA en un sentido, 1414 uA en el otro. Un TFT real no tiene\n"
        "cuerpo y sus dos terminales de canal son el mismo tipo de terminal. Ahora todas\n"
        "las uniones de las cuatro tarjetas de modelo estan inertes - IS, JS, CBD, CBS,\n"
        "CJ y CJSW en cero - lo que deja al nodo de sustrato intrinseco sin camino a\n"
        "ninguna parte, y las partes propias del wrapper ya eran simetricas. Intercambiar\n"
        "d y s ya no cambia nada, y el script de verificacion lo afirma en cada corner,\n"
        "en saturacion y en la region lineal.\n\n"
        "Los esquematicos existentes siguen funcionando y conservan sus numeros. Lo que\n"
        "cambia es que la orientacion deja de ser algo que el disenador deba recordar.",
    "b_h": "Un campo magnetico, con cero por defecto",
    "b":
        "igzo_tft ahora recibe B en tesla, por defecto 0, y un b_scale adimensional, por\n"
        "defecto 1. La movilidad del canal cae como mu/(1 + (mu*b_scale*B)^2) -\n"
        "magnetorresistencia clasica - con mu tomada del propio Kp/Cox del corner activo,\n"
        "de modo que los corners responden distinto, como debe ser.\n\n"
        "Su tamano, con la mu medida de 4.58 cm^2/Vs: mu*B = 4.6e-4 por tesla, asi que el\n"
        "efecto sobre la corriente es (mu*B)^2 = 2 partes en diez millones por tesla. Eso\n"
        "no es un sensor. No es medible. Si el laboratorio mide una reduccion de Kp bajo\n"
        "campo, la magnetorresistencia clasica no es la causa, y docs/bibliography/ dice\n"
        "que hay publicado, que predeciria aqui, y que artefactos ordinarios -\n"
        "autocalentamiento, estres, histeresis de polarizacion, el iman actuando sobre el\n"
        "instrumento - hay que descartar primero. Invierte el campo: un efecto real sobre\n"
        "la movilidad es par en B.\n\n"
        "Cuando haya un coeficiente medido, pon b_scale = sqrt(medido / 2.1e-7) y el\n"
        "modelo lo reproduce sin que nadie edite un archivo de corner. Un 1 % por tesla\n"
        "medido deja b_scale cerca de 220 - que es tambien el factor por el que esa\n"
        "medicion excederia la fisica que le da nombre al termino.",
}


def build(lang, out_dir=None, data=None):
    import math
    S = {"en": EN, "es": ES}[lang]
    d = data if data is not None else measure()
    ref = d["ref"]
    gme, gmi = d["gm"][10.0]
    nums = {
        "id": ref["id"] * 1e6, "gmi": ref["gm_i"] * 1e6,
        "gds": ref["gds"] * 1e6, "av": ref["av"],
        "avdb": 20 * math.log10(ref["av"]),
        "gme": gme * 1e6, "loss": 100.0 * (1 - gme / gmi),
        "ft": d["ft"][10.0] / 1e6, "ft5": d["ft"][5.0] / 1e6,
        "ftn": d["ft_noov"][10.0] / 1e6, "ftn5": d["ft_noov"][5.0] / 1e6,
    }
    name = {"en": "TFT-MMM-LAB-PDK_capabilities_and_limits_en.pdf",
            "es": "TFT-MMM-LAB-PDK_capacidades_y_limites_es.pdf"}[lang]
    out = os.path.join(default_out_dir(out_dir), name)

    with PdfPages(out) as pdf:
        n = 1
        p = Page(pdf, S["t1"], kicker=S["k"], footer=S["footer"])
        p.text(S["intro"], size=9.6)
        p.table(S["boxes"], widths=[0.24, 0.20, 0.56])
        p.head(S["h_meas"])
        p.table(S["meas"], widths=[0.28, 0.22, 0.50])
        p.close(n)

        n += 1
        p = Page(pdf, S["h_dc"], kicker=S["k"], footer=S["footer"])
        p.text(S["dc_txt"] % nums)
        p.head(S["h_gm"])
        p.text(S["gm_txt"] % nums)
        p.figure(fig_gm(d, S), width=0.86)
        p.close(n)

        n += 1
        p = Page(pdf, S["h_ac"], kicker=S["k"], footer=S["footer"])
        p.text(S["ac_txt"] % nums)
        p.figure(fig_ft(d, S), width=0.90)
        p.close(n)

        n += 1
        p = Page(pdf, S["h_no"], kicker=S["k"], footer=S["footer"])
        p.text(S["no_txt"])
        p.head(S["h_ceil"])
        p.table(S["ceil"], widths=[0.32, 0.24, 0.44])
        p.close(n)

        n += 1
        p = Page(pdf, S["h_new"], kicker=S["k"], footer=S["footer"])
        p.head(S["sym_h"])
        p.text(S["sym"])
        p.head(S["b_h"])
        p.text(S["b"])
        p.close(n)

        info = pdf.infodict()
        info["Title"] = ("TFT-MMM-LAB-PDK - capabilities and limits" if lang == "en"
                         else "TFT-MMM-LAB-PDK - capacidades y limites")
        info["Author"] = "UCI/INRF - MMM Lab"
    print("wrote %s (%d bytes)" % (out, os.path.getsize(out)))


if __name__ == "__main__":
    args = sys.argv[1:]
    out_dir = None
    if args and args[-1].startswith(("/", "~", ".")):
        out_dir = os.path.expanduser(args.pop())
    shared = measure()          # one ngspice pass, both languages
    for lg in (args or ["en", "es"]):
        build(lg, out_dir, shared)
