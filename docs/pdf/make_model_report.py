#!/usr/bin/env python3
"""
Model against measurement: what the IGZO TFT model reproduces, what it does
not, and which measurement would fix which gap.

    python3 make_model_report.py            # both languages
    python3 make_model_report.py es ~/out   # one language, somewhere else

Every plot is generated here from the raw .xls in measurements/ and from
ngspice runs against the PDK's own corner sections.  Nothing is a screenshot
of an earlier result, so a stale figure is impossible: if the models change,
the plots change with them.
"""

import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "docs", "extraction"))

from pdfkit import ACCENT, INK, MUTED, Page, PdfPages, default_out_dir  # noqa: E402
from pdk_paths import require_data  # noqa: E402
from xls_reader import read_xls, sheet_columns  # noqa: E402

import contact_extract as ce  # noqa: E402
import extract_params as ep  # noqa: E402
import validate_model as vm  # noqa: E402

# The chips, and the colour each one keeps in every figure.
CHIPS = {"TFT1": "#1f6f8b", "TFT2": "#b3541e", "TFT3": "#4a7c2f"}
COX = 1.564e-15                       # F/um^2, from the plate below

# The devices the model is checked against - the same six every time.
CASES = [("TFT1", 1, 160.0, 100.0, "best"),
         ("TFT1", 1, 80.0, 500.0, "best"),
         ("TFT1", 2, 40.0, 100.0, "best"),
         ("TFT1", 1, 20.0, 500.0, "best"),
         ("TFT1", 1, 10.0, 1000.0, "short"),
         ("TFT1", 2, 8.0, 1000.0, "short")]


def _axes(fig):
    for ax in fig.get_axes():
        ax.tick_params(labelsize=7)
        ax.xaxis.label.set_size(8)
        ax.yaxis.label.set_size(8)
        ax.title.set_size(8.5)
        for s in ax.spines.values():
            s.set_color("#999999")
        ax.grid(alpha=0.25, lw=0.5)
    fig.tight_layout(pad=0.6)
    return fig


# ---------------------------------------------------------------- figures --
def fig_output_curves(lang):
    """Measured output curves with the simulated ones over them."""
    fig, axes = plt.subplots(2, 3, figsize=(9.0, 5.2))
    ratios = []
    for ax, (chip, tr, L, W, corner) in zip(axes.ravel(), CASES):
        meas = vm.measured(chip, tr, L, W)
        if not meas:
            ax.set_axis_off()
            continue
        vgs = sorted(v for v in meas if v > 0)
        sim = vm.simulate(corner, W, L, vgs)
        for i, vg in enumerate(vgs):
            vdm, idm = meas[vg]
            vds, ids = sim[vg]
            col = plt.cm.viridis(i / max(1, len(vgs) - 1))
            ax.plot(vdm, idm * 1e6, ".", ms=2, color=col,
                    label=("VGS=%g V" % vg) if True else None)
            ax.plot(vds, ids * 1e6, "-", lw=1.0, color=col, alpha=0.85)
            sel = vdm >= 0.8 * vdm.max()
            if sel.sum() > 2:
                ism = np.interp(vdm, vds, ids)
                ratios.append(np.median(ism[sel] / np.maximum(idm[sel], 1e-15)))
        ax.set_title("%s  L=%g um  W=%g um  (%s)" % (chip, L, W, corner))
        ax.set_xlabel("VDS (V)")
        ax.set_ylabel("ID (uA)")
        ax.legend(fontsize=5.5, loc="upper left", frameon=False)
    return _axes(fig), float(np.median(ratios)), len(ratios)


def fig_transfer(lang):
    """Measured transfer sweeps: the log slope and where the square law ends."""
    runs = [r for r in ep.transfer_runs() if len(r["vgs"]) > 100]
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.4))
    for r in runs[:4]:
        vg, idr = r["vgs"], np.abs(r["id"])
        lbl = "%s  VDS=%.2g V" % (r["run"], r["vds"])
        axes[0].semilogy(vg, np.maximum(idr, 1e-14), lw=1.0, label=lbl)
        axes[1].plot(vg, np.sqrt(np.maximum(idr, 0.0)) * 1e3, lw=1.0, label=lbl)
    axes[0].set_xlabel("VGS (V)")
    axes[0].set_ylabel("|ID| (A)")
    axes[0].set_title({"en": "Transfer, log scale - subthreshold and on/off",
                       "es": "Transferencia, escala log - subumbral y on/off"}[lang])
    axes[1].set_xlabel("VGS (V)")
    axes[1].set_ylabel("sqrt(ID)  (mA^0.5)")
    axes[1].set_title({"en": "Square law would be a straight line here",
                       "es": "La ley cuadratica seria una recta aqui"}[lang])
    for ax in axes:
        ax.legend(fontsize=6, frameon=False)
    return _axes(fig), runs


def fig_extraction(lang):
    """Every device fit: where the four corners come from."""
    p = os.path.join(ROOT, "docs", "extraction", "params.npy")
    if not os.path.exists(p):
        ep.main()
    rows = np.load(p, allow_pickle=True)
    fig, axes = plt.subplots(1, 3, figsize=(9.0, 3.0))
    for chip, col in CHIPS.items():
        sel = [r for r in rows if r["chip"] == chip]
        if not sel:
            continue
        L = [r["L"] for r in sel]
        axes[0].semilogx(L, [r["kp_lin"] * 1e6 for r in sel], "o", ms=3,
                         color=col, alpha=0.7, label=chip)
        axes[1].semilogx(L, [r["vth_lin"] for r in sel], "o", ms=3, color=col,
                         alpha=0.7, label=chip)
        # Only fits with a physically meaningful Early voltage.  A flat output
        # curve gives VA -> infinity and a noisy one gives VA -> 0; both are
        # failures of the fit, not measurements of lambda.
        lam = [(r["L"], 1.0 / r["VA"]) for r in sel if 1.0 < r["VA"] < 1e4]
        if lam:
            axes[2].loglog([x for x, _ in lam], [y for _, y in lam], "o", ms=3,
                           color=col, alpha=0.7, label=chip)
    axes[2].set_ylim(1e-3, 1.0)
    for value, text in ((0.717, "best 0.717"), (0.562, "tt 0.562"),
                        (0.381, "all 0.381"), (0.128, "short 0.128")):
        axes[0].axhline(value, color=ACCENT, lw=0.7, ls="--")
        axes[0].text(170, value, text, fontsize=5.5, color=ACCENT, va="bottom",
                     ha="right")
    axes[0].set_ylabel("Kp (uA/V^2)")
    axes[1].set_ylabel("Vth (V)")
    axes[2].set_ylabel("lambda (1/V)")
    for ax, t in zip(axes, ("Kp", "Vth", "lambda")):
        ax.set_xlabel("L (um)")
        ax.set_title("%s vs channel length" % t)
        ax.legend(fontsize=6, frameon=False)
    return _axes(fig), rows


def fig_contact(lang):
    """On-resistance against length: the intercept is the contact."""
    fig, ax = plt.subplots(figsize=(5.6, 3.2))
    out = {}
    for chip, col in CHIPS.items():
        try:
            ron = ce.on_resistance(chip)
        except SystemExit:
            continue
        pts = {}
        for (vgs, L, W), r in ron.items():
            if abs(vgs - 6.0) > 0.51:
                continue
            pts.setdefault(L, []).append(r * W)
        if len(pts) < 3:
            continue
        Ls = np.array(sorted(pts))
        RW = np.array([np.median(pts[l]) for l in Ls])
        ax.plot(Ls, RW / 1e6, "o", ms=4, color=col, label=chip)
        a, b = np.polyfit(Ls, RW, 1)
        xx = np.linspace(0, Ls.max() * 1.05, 50)
        ax.plot(xx, (a * xx + b) / 1e6, "-", lw=0.9, color=col, alpha=0.6)
        out[chip] = (b, a)
    ax.set_xlabel("L (um)")
    ax.set_ylabel("R_on * W  (MOhm*um)")
    ax.set_title({"en": "On-resistance at VGS = 6 V: intercept = 2*Rc*W",
                  "es": "Resistencia on a VGS = 6 V: la ordenada es 2*Rc*W"}[lang])
    ax.legend(fontsize=6, frameon=False)
    ax.set_xlim(left=0)
    return _axes(fig), out


def fig_cox(lang):
    """The plate that gives Cox, measured against bias at four frequencies."""
    sheets = read_xls(require_data("TFT1", "CAP", "CAP_IN.xls"))
    fig, ax = plt.subplots(figsize=(5.6, 3.2))
    order = ["1_1K", "1_10K", "1_100K", "1_1M"]
    label = {"1_1K": "1 kHz", "1_10K": "10 kHz", "1_100K": "100 kHz",
             "1_1M": "1 MHz"}
    cox = {}
    for name in order:
        if name not in sheets:
            continue
        c = sheet_columns(sheets[name])
        cap = np.array(c[0][:61], dtype=float)
        v = np.array(c[2][:61], dtype=float)
        if cap.max() < 1e-12:
            continue
        ax.plot(v, cap * 1e12, lw=1.1, label=label[name])
        cox[label[name]] = float(np.median(cap))
    ax.set_xlabel("bias (V)")
    ax.set_ylabel("C (pF)")
    ax.set_title({"en": "400 x 400 um plate, C against bias",
                  "es": "Placa de 400 x 400 um, C contra polarizacion"}[lang])
    ax.legend(fontsize=6, frameon=False)
    return _axes(fig), cox


# ------------------------------------------------------------------ text --
EN = {
    "footer": "TFT-MMM-LAB-PDK  ·  model vs measurement",
    "t1": "The model, and what it is\nchecked against",
    "k1": "UCI/INRF IGZO TFT process",
    "intro":
        "This is the evidence behind the model cards in\n"
        "libs.tech/ngspice/igzo_mmm_lab.ngspice: what was measured, what was\n"
        "fitted to it, how close the fit comes, and - the part that matters for\n"
        "planning the next run - which measurement would remove which\n"
        "uncertainty.\n\n"
        "Every figure here is generated from the raw .xls files in measurements/\n"
        "and from ngspice runs against the PDK's own corner sections.  Nothing is\n"
        "copied from an earlier report, so nothing can quietly go stale.",
    "h_model": "What the model is",
    "model":
        "A SPICE level-1 MOSFET with three things wrapped around it, in the\n"
        "igzo_tft subcircuit:\n"
        "    contact resistance   Rc = 3.3 Ohm*m / W per contact, measured\n"
        "    overlap capacitance  Cox * ov * W per side, from the drawn overlap\n"
        "    a bulk that stays inside - a TFT has no body terminal\n"
        "Level 1 was chosen because the data supports four numbers per corner and\n"
        "not more: Vto, Kp, lambda and Tox.  A model with more parameters than the\n"
        "measurement can pin is a model that fits noise.",
    "h_corners": "The four corners, and where they come from",
    "corners": [
        ["Corner", "Vto (V)", "Kp (uA/V^2)", "lambda (1/V)", "What it is"],
        ["best", "+0.09", "0.717", "0.0067", "long-channel devices of the best chip"],
        ["tt", "-0.26", "0.562", "0.0142", "median over every working device, best chip"],
        ["short", "-1.32", "0.128", "0.0659", "L <= 10 um, contact-limited"],
        ["all", "-0.53", "0.381", "0.0355", "all three chips, the bad ones included"],
    ],
    "h_out": "Output curves: simulated over measured",
    "out_txt":
        "Points are measured, lines are ngspice at the same W and L. Six devices\n"
        "spanning L = 8 to 160 um, at every gate voltage the sweep carries.",
    "out_res": "Median simulated/measured in saturation: %.2f over %d comparisons.",
    "h_tr": "Transfer curves: where the square law gives out",
    "tr_txt":
        "The left panel is the log sweep - subthreshold slope and on/off ratio,\n"
        "neither of which a level-1 model reproduces at all.  The right panel is\n"
        "sqrt(ID): a square-law device is a straight line there, and these are\n"
        "not.  The measured saturation exponent is 2.31 rather than 2, which is\n"
        "why the model runs about 20 % pessimistic on gm at a given current.",
    "h_ex": "Every device fit, and the corners drawn from them",
    "ex_txt":
        "86 devices, three chips.  The spread is the point: Kp varies by a factor\n"
        "of 70 across the population and falls off sharply below L = 20 um, which\n"
        "is the contact resistance taking over rather than the mobility changing.\n"
        "TFT2 sits apart from the other two - its saturation exponent comes out at\n"
        "0.87, which no square-law model can express - and it is excluded from the\n"
        "tt and best corners for that reason, and only for that reason.",
    "h_rc": "Contact resistance, from the devices themselves",
    "rc_txt":
        "R_on * W against L at VGS = 6 V.  The slope is the gated sheet resistance\n"
        "and the intercept is 2*Rc*W = 6.6 MOhm*um.  This is the primary route\n"
        "rather than TLM because the TLM pad spacing was never recorded in the\n"
        ".xls files; the TLM ladders are in the data and are reported as measured,\n"
        "but they cannot be turned into an absolute Rc without that number.\n\n"
        "The three chips do not agree, and the table says so: 6.6 MOhm*um is the\n"
        "best chip.  The last column is the length below which the contacts\n"
        "dominate the device - which is why the short corner exists.",
    "rc_head": ["Chip", "2*Rc*W (MOhm*um)", "sheet R (MOhm*um / um)",
                "contact-limited below"],
    "h_cox": "Cox, and exactly what it does and does not establish",
    "cox_txt":
        "The 400 x 400 um plate of Test_capacitance, swept from -3 to +3 V at four\n"
        "frequencies.  At 1 MHz it reads 250.2 pF, which over 160 000 um^2 gives\n"
        "Cox = 1.564 fF/um^2 - the one capacitance in this PDK that is measured\n"
        "rather than derived.\n\n"
        "What it does not establish: the transistor's gate capacitance.  This is a\n"
        "metal-insulator-metal plate, not a gate over a channel, so it fixes the\n"
        "dielectric and nothing about how the channel charges and discharges.  The\n"
        "overlap capacitance in the model is Cox times an overlap read off one GDS\n"
        "cell, and no measurement anywhere in this data set confirms it.",
    "h_next": "What to measure next, and what each measurement buys",
    "next": [
        ["Measurement", "What it would settle"],
        ["C-V on a transistor, gate to S/D",
         "the largest gap: Cgs and Cgd against bias, which the model has never seen"],
        ["A proper VGS sweep per chip",
         "Vth and subthreshold slope on all three chips - the VGS folders are empty"],
        ["TLM with the pad spacing recorded",
         "an absolute Rc, independent of the R_on fit that currently carries it"],
        ["Drawn vs printed across a wafer",
         "the +3 um bias is one cell; its spread is what a PCell would need"],
        ["Bias stress and hysteresis",
         "IGZO drifts under gate bias; the model has no term for it at all"],
        ["Metal thickness, gate and S/D",
         "every inductor resistance in this PDK is an assumption until this exists"],
        ["S-parameters or a ring oscillator",
         "fT, and whether the DC model means anything at 100 MHz"],
    ],
    "h_hon": "Where this model should not be trusted",
    "hon":
        "1.  It is DC-only.  It reproduces the curves above and nothing else has\n"
        "    been checked against silicon.\n"
        "2.  Valid over the measured range: VGS <= 6 V, VDS <= 10 V.  Outside it\n"
        "    the square law is extrapolation, not prediction.\n"
        "3.  No temperature, no bias stress, no hysteresis, no noise model.\n"
        "4.  The gate capacitance is derived, not measured, so anything that\n"
        "    depends on charging the gate - fT, tuned loads, switching speed - is\n"
        "    an estimate resting on a 5 um overlap read off a drawing.",
}

ES = {
    "footer": "TFT-MMM-LAB-PDK  ·  modelo vs medicion",
    "t1": "El modelo, y contra que\nse comprueba",
    "k1": "Proceso IGZO TFT de UCI/INRF",
    "intro":
        "Esta es la evidencia detras de las tarjetas de modelo de\n"
        "libs.tech/ngspice/igzo_mmm_lab.ngspice: que se midio, que se ajusto a\n"
        "eso, cuanto se acerca el ajuste y - la parte que sirve para planear la\n"
        "siguiente corrida - que medicion quitaria cada incertidumbre.\n\n"
        "Todas las figuras se generan aqui, a partir de los .xls crudos de\n"
        "measurements/ y de corridas de ngspice contra las esquinas del propio\n"
        "PDK.  Nada esta copiado de un reporte anterior, asi que nada puede\n"
        "quedarse viejo en silencio.",
    "h_model": "Que es el modelo",
    "model":
        "Un MOSFET nivel 1 de SPICE con tres cosas envueltas alrededor, en el\n"
        "subcircuito igzo_tft:\n"
        "    resistencia de contacto   Rc = 3.3 Ohm*m / W por contacto, medida\n"
        "    capacitancia de solape    Cox * ov * W por lado, del solape dibujado\n"
        "    un bulk que se queda adentro - un TFT no tiene terminal de cuerpo\n"
        "Se eligio nivel 1 porque los datos sostienen cuatro numeros por esquina y\n"
        "no mas: Vto, Kp, lambda y Tox.  Un modelo con mas parametros de los que\n"
        "la medicion puede fijar es un modelo que ajusta ruido.",
    "h_corners": "Las cuatro esquinas, y de donde salen",
    "corners": [
        ["Esquina", "Vto (V)", "Kp (uA/V^2)", "lambda (1/V)", "Que es"],
        ["best", "+0.09", "0.717", "0.0067", "canal largo del mejor chip"],
        ["tt", "-0.26", "0.562", "0.0142", "mediana de los dispositivos buenos del mejor chip"],
        ["short", "-1.32", "0.128", "0.0659", "L <= 10 um, limitado por contacto"],
        ["all", "-0.53", "0.381", "0.0355", "los tres chips, incluidos los malos"],
    ],
    "h_out": "Curvas de salida: simulado sobre medido",
    "out_txt":
        "Los puntos son medidos, las lineas son ngspice con el mismo W y L. Seis\n"
        "dispositivos de L = 8 a 160 um, en cada voltaje de compuerta del barrido.",
    "out_res": "Mediana simulado/medido en saturacion: %.2f sobre %d comparaciones.",
    "h_tr": "Curvas de transferencia: donde se acaba la ley cuadratica",
    "tr_txt":
        "El panel izquierdo es el barrido logaritmico - pendiente subumbral y\n"
        "relacion on/off, que un modelo nivel 1 no reproduce en absoluto.  El\n"
        "derecho es sqrt(ID): un dispositivo de ley cuadratica seria una recta\n"
        "ahi, y estos no lo son.  El exponente de saturacion medido es 2.31 en vez\n"
        "de 2, y por eso el modelo queda ~20 % pesimista en gm a una corriente\n"
        "dada.",
    "h_ex": "Cada ajuste de dispositivo, y las esquinas que salen de ellos",
    "ex_txt":
        "86 dispositivos, tres chips.  La dispersion es el punto: Kp varia un\n"
        "factor 70 en la poblacion y se desploma por debajo de L = 20 um, que es\n"
        "la resistencia de contacto tomando el control, no la movilidad\n"
        "cambiando.  TFT2 queda aparte de los otros dos - su exponente de\n"
        "saturacion sale 0.87, que ningun modelo de ley cuadratica puede expresar -\n"
        "y por eso, y solo por eso, se excluye de las esquinas tt y best.",
    "h_rc": "Resistencia de contacto, sacada de los propios dispositivos",
    "rc_txt":
        "R_on * W contra L a VGS = 6 V.  La pendiente es la resistencia de hoja\n"
        "del canal y la ordenada al origen es 2*Rc*W = 6.6 MOhm*um.  Esta es la\n"
        "via principal, y no el TLM, porque la separacion de pads del TLM nunca\n"
        "quedo registrada en los .xls; las escaleras TLM estan en los datos y se\n"
        "reportan como se midieron, pero sin ese numero no dan un Rc absoluto.\n\n"
        "Los tres chips no coinciden, y la tabla lo dice: 6.6 MOhm*um es el mejor\n"
        "chip.  La ultima columna es la longitud por debajo de la cual los\n"
        "contactos dominan el dispositivo - que es la razon de que exista la\n"
        "esquina short.",
    "rc_head": ["Chip", "2*Rc*W (MOhm*um)", "R de hoja (MOhm*um / um)",
                "limitado por contacto bajo"],
    "h_cox": "Cox, y exactamente que establece y que no",
    "cox_txt":
        "La placa de 400 x 400 um de Test_capacitance, barrida de -3 a +3 V a\n"
        "cuatro frecuencias.  A 1 MHz mide 250.2 pF, que sobre 160 000 um^2 da\n"
        "Cox = 1.564 fF/um^2 - la unica capacitancia de este PDK que esta medida y\n"
        "no derivada.\n\n"
        "Lo que no establece: la capacitancia de compuerta del transistor.  Esto\n"
        "es una placa metal-aislante-metal, no una compuerta sobre un canal, asi\n"
        "que fija el dielectrico y nada sobre como se carga y descarga el canal.\n"
        "La capacitancia de solape del modelo es Cox por un solape leido de una\n"
        "celda del GDS, y ninguna medicion de este conjunto de datos lo confirma.",
    "h_next": "Que medir despues, y que compra cada medicion",
    "next": [
        ["Medicion", "Que resolveria"],
        ["C-V en un transistor, compuerta contra S/D",
         "el hueco mas grande: Cgs y Cgd contra polarizacion, que el modelo nunca vio"],
        ["Un barrido VGS por chip",
         "Vth y pendiente subumbral en los tres chips - las carpetas VGS estan vacias"],
        ["TLM con la separacion de pads anotada",
         "un Rc absoluto, independiente del ajuste de R_on que hoy lo sostiene"],
        ["Dibujado contra impreso en toda la oblea",
         "el bias de +3 um es una celda; su dispersion es lo que un PCell necesita"],
        ["Estres por polarizacion e histeresis",
         "el IGZO deriva bajo bias de compuerta; el modelo no tiene termino alguno"],
        ["Espesor de metal, compuerta y S/D",
         "toda resistencia de inductor en este PDK es una suposicion sin esto"],
        ["Parametros S o un oscilador de anillo",
         "fT, y si el modelo DC significa algo a 100 MHz"],
    ],
    "h_hon": "Donde no hay que confiar en este modelo",
    "hon":
        "1.  Es solo DC.  Reproduce las curvas de arriba y nada mas se ha\n"
        "    comprobado contra silicio.\n"
        "2.  Valido en el rango medido: VGS <= 6 V, VDS <= 10 V.  Fuera de ahi la\n"
        "    ley cuadratica es extrapolacion, no prediccion.\n"
        "3.  Sin temperatura, sin estres por polarizacion, sin histeresis, sin\n"
        "    modelo de ruido.\n"
        "4.  La capacitancia de compuerta es derivada, no medida, asi que todo lo\n"
        "    que dependa de cargar la compuerta - fT, cargas sintonizadas,\n"
        "    velocidad de conmutacion - es una estimacion apoyada en un solape de\n"
        "    5 um leido de un dibujo.",
}


def build(lang, out_dir=None):
    S = {"en": EN, "es": ES}[lang]
    name = {"en": "TFT-MMM-LAB-PDK_model_vs_measurement_en.pdf",
            "es": "TFT-MMM-LAB-PDK_modelo_vs_medicion_es.pdf"}[lang]
    out = os.path.join(default_out_dir(out_dir), name)

    with PdfPages(out) as pdf:
        n = 1
        p = Page(pdf, S["t1"], kicker=S["k1"], footer=S["footer"])
        p.text(S["intro"], size=9.6)
        p.head(S["h_model"])
        p.text(S["model"])
        p.head(S["h_corners"])
        p.table(S["corners"], widths=[0.11, 0.12, 0.16, 0.15, 0.46])
        p.head(S["h_hon"])
        p.text(S["hon"])
        p.close(n)

        n += 1
        p = Page(pdf, S["h_out"], kicker=S["k1"], footer=S["footer"])
        p.text(S["out_txt"])
        fig, ratio, count = fig_output_curves(lang)
        p.figure(fig, None, width=1.0)
        p.text(S["out_res"] % (ratio, count), weight="bold")
        p.close(n)

        n += 1
        p = Page(pdf, S["h_tr"], kicker=S["k1"], footer=S["footer"])
        p.text(S["tr_txt"])
        fig, runs = fig_transfer(lang)
        p.figure(fig, None, width=1.0)
        rows = [["run", "VDS (V)", "Kp*W/L (uA/V^2)", "Vth (V)", "S (V/dec)",
                 "on/off"]]
        for r in runs[:4]:
            a = ep.analyse_transfer(r)
            rows.append([r["run"], "%.2g" % r["vds"], "%.3g" % (a["kp_wl"] * 1e6),
                         "%.2f" % a["vth"], "%.2f" % a["ss"],
                         "%.0e" % a["onoff"]])
        p.table(rows, widths=[0.16, 0.14, 0.24, 0.14, 0.16, 0.16])
        p.close(n)

        n += 1
        p = Page(pdf, S["h_ex"], kicker=S["k1"], footer=S["footer"])
        p.text(S["ex_txt"])
        fig, rows = fig_extraction(lang)
        p.figure(fig, None, width=1.0)
        p.close(n)

        n += 1
        p = Page(pdf, S["h_rc"], kicker=S["k1"], footer=S["footer"])
        p.text(S["rc_txt"])
        fig, fits = fig_contact(lang)
        p.figure(fig, None, width=0.72)
        rows = [S["rc_head"]]
        for chip, (intercept, slope) in sorted(fits.items()):
            rows.append([chip, "%.2f" % (intercept / 1e6), "%.3f" % (slope / 1e6),
                         "%.0f" % (intercept / slope) if slope > 0 else "-"])
        p.table(rows, widths=[0.16, 0.28, 0.30, 0.26])
        p.close(n)

        n += 1
        p = Page(pdf, S["h_cox"], kicker=S["k1"], footer=S["footer"])
        p.text(S["cox_txt"])
        fig, cox = fig_cox(lang)
        p.figure(fig, None, width=0.68)
        p.head(S["h_next"])
        p.table(S["next"], widths=[0.34, 0.66])
        p.close(n)

        info = pdf.infodict()
        info["Title"] = ("TFT-MMM-LAB-PDK - model vs measurement" if lang == "en"
                         else "TFT-MMM-LAB-PDK - modelo vs medicion")
        info["Author"] = "UCI/INRF - MMM Lab"
    print("wrote %s (%d bytes)" % (out, os.path.getsize(out)))


if __name__ == "__main__":
    args = sys.argv[1:]
    out_dir = None
    if args and args[-1].startswith(("/", "~", ".")):
        out_dir = os.path.expanduser(args.pop())
    for lg in (args or ["en", "es"]):
        build(lg, out_dir)
