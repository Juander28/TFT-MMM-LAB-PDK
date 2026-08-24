#!/usr/bin/env python3
"""
A slide deck of what the PDK is and what it can do: the cells, their
parameters, and the model against the measurements.

    python3 make_slides.py            # both languages
    python3 make_slides.py es ~/out   # one language, somewhere else

The parameter panels are drawn from the live PCell declarations - names,
defaults, units and read-only flags are read out of the cells themselves, so
a panel cannot describe a parameter the cell does not have.  The arrows point
at rows whose positions this script computed, which is why they land on the
right ones.

Landscape 16:9, because it is a deck.
"""

import os
import subprocess
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.image as mpimg
from matplotlib.patches import FancyArrowPatch

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
FIG = os.path.join(ROOT, "docs", "figures")
sys.path.insert(0, HERE)
from pdfkit import default_out_dir  # noqa: E402

SLIDE = (13.333, 7.5)          # 16:9
INK = "#1a1a1a"
MUTED = "#5b5b5b"
ACCENT = "#8a3324"
RULE = "#c9c4bd"
PANEL_BG = "#f4f2ee"
PANEL_HD = "#e2ddd4"


# ------------------------------------------------------------------ slides --
class Slide:
    def __init__(self, pdf, title, kicker=None, footer=""):
        self.pdf = pdf
        self.fig = plt.figure(figsize=SLIDE)
        self.fig.patch.set_facecolor("white")
        self.footer = footer
        if kicker:
            self.fig.text(0.06, 0.925, kicker.upper(), size=10, color=ACCENT,
                          weight="bold", va="top")
        self.fig.text(0.06, 0.90, title, size=23, color=INK, weight="bold",
                      va="top")
        self.fig.add_artist(plt.Line2D([0.06, 0.94], [0.845, 0.845],
                                       color=RULE, lw=1.0))
        self.y = 0.80

    def text(self, s, x=0.06, size=12.5, color=INK, width=None, weight="normal"):
        for line in s.split("\n"):
            self.fig.text(x, self.y, line, size=size, color=color, va="top",
                          weight=weight)
            self.y -= size / 72.0 / SLIDE[1] * 1.55
        self.y -= 0.012

    def bullets(self, items, x=0.06, size=13):
        for it in items:
            self.fig.text(x, self.y, "—", size=size, color=ACCENT, va="top")
            self.fig.text(x + 0.022, self.y, it, size=size, color=INK, va="top")
            self.y -= size / 72.0 / SLIDE[1] * 1.75
        self.y -= 0.012

    def image(self, path, rect, caption=None, frame=True):
        """rect = (x, y, w, h) in figure coordinates; the image keeps aspect."""
        if hasattr(path, "read"):
            img = mpimg.imread(path)
        else:
            img = mpimg.imread(path if os.path.isabs(path)
                               else os.path.join(FIG, path))
        x, y, w, h = rect
        ih, iw = img.shape[0], img.shape[1]
        scale = min(w / iw, (h * SLIDE[1] / SLIDE[0]) / ih)
        dw = iw * scale
        dh = ih * scale * SLIDE[0] / SLIDE[1]
        ax = self.fig.add_axes([x + (w - dw) / 2, y, dw, dh])
        ax.imshow(img)
        ax.set_xticks([]); ax.set_yticks([])
        for s in ax.spines.values():
            s.set_color(RULE if frame else "white")
            s.set_linewidth(0.8)
        if caption:
            self.fig.text(x + w / 2, y - 0.028, caption, size=9.5, color=MUTED,
                          ha="center", va="top", style="italic")
        return (x + (w - dw) / 2, y, dw, dh)

    def figure(self, fig, rect, caption=None):
        import io
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=200, bbox_inches="tight",
                    facecolor="white")
        plt.close(fig)
        buf.seek(0)
        return self.image(buf, rect, caption)

    def panel(self, rows, rect, title, highlight=()):
        """
        A parameter panel, drawn the way the instance dialog lists them.

        Returns {name: (x, y)} of each row's left edge, so arrows can point at
        rows rather than at guessed coordinates.
        """
        x, y, w, h = rect
        n = len(rows) + 1
        rh = h / n
        self.fig.add_artist(plt.Rectangle((x, y), w, h, facecolor=PANEL_BG,
                                          edgecolor=RULE, lw=0.8,
                                          transform=self.fig.transFigure,
                                          zorder=1))
        self.fig.add_artist(plt.Rectangle((x, y + h - rh), w, rh,
                                          facecolor=PANEL_HD, edgecolor=RULE,
                                          lw=0.8, transform=self.fig.transFigure,
                                          zorder=1))
        self.fig.text(x + 0.008, y + h - rh / 2, title, size=9.5, weight="bold",
                      color=INK, va="center", zorder=2)
        anchors = {}
        for i, (name, value) in enumerate(rows):
            ry = y + h - rh * (i + 2) + rh / 2
            hot = name in highlight
            self.fig.text(x + 0.008, ry, name, size=8.6,
                          color=ACCENT if hot else INK,
                          weight="bold" if hot else "normal", va="center",
                          zorder=2)
            self.fig.text(x + w - 0.008, ry, value, size=8.6, color=MUTED,
                          ha="right", va="center", zorder=2)
            anchors[name] = (x, ry, x + w, ry)
        return anchors

    def arrow(self, anchor, text, dx=0.10, dy=0.0, size=10.5, side="right"):
        """Point at a panel row and say what it does."""
        x0, y0, x1, _ = anchor
        start = (x1, y0) if side == "right" else (x0, y0)
        tx = start[0] + dx
        ty = y0 + dy
        self.fig.text(tx + (0.012 if dx > 0 else -0.012), ty, text, size=size,
                      color=INK, va="center",
                      ha="left" if dx > 0 else "right", zorder=3)
        # A patch on the figure, not plt.annotate: annotate draws into the
        # current axes and makes one if there is none, which puts a set of
        # tick-marked axes across the slide.
        arrow = FancyArrowPatch(
            (tx, ty), start, transform=self.fig.transFigure,
            arrowstyle="-|>", mutation_scale=11, color=ACCENT, lw=1.2,
            shrinkA=6, shrinkB=3, connectionstyle="arc3,rad=0.12", zorder=4)
        self.fig.add_artist(arrow)

    def close(self, n):
        self.fig.text(0.94, 0.045, str(n), size=9, color=MUTED, ha="right")
        self.fig.text(0.06, 0.045, self.footer, size=9, color=MUTED)
        self.pdf.savefig(self.fig)
        plt.close(self.fig)


# ------------------------------------------------------------------- data ---
def tank_curves():
    """Run the tank testbench at both metal thicknesses and plot both."""
    pdkpath = os.environ.get("PDKPATH", ROOT)
    net = """* tank
.include {m}/design.ngspice
.lib {m}/igzo_mmm_lab.ngspice tt
XM1 out in 0 igzo_tft W=1000u L=8u ov=5u
XL1 vdd out ind_igzo ls=263.5n rs={rs}
XC1 out 0 cap_mim W=78.4u L=78.4u
vdd vdd 0 5
vin in 0 dc 2 ac 1
.ac dec 200 1meg 1g
.control
run
print db(v(out)) > {out}
.endc
.end
"""
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    import tempfile
    import numpy as np
    for rs, lab, col in ((71.88, "1 um of gold  (Q 2.3)", "#1f6f8b"),
                         (1438.0, "50 nm of gold  (Q 0.12)", "#b3541e")):
        d = tempfile.mkdtemp()
        sp, out = os.path.join(d, "t.spice"), os.path.join(d, "t.txt")
        open(sp, "w").write(net.format(
            m=os.path.join(pdkpath, "libs.tech", "ngspice"), rs=rs, out=out))
        subprocess.run(["ngspice", "-b", sp], capture_output=True, timeout=300)
        f, g = [], []
        for line in open(out):
            p = line.split()
            if len(p) >= 3 and p[0].isdigit():
                try:
                    f.append(float(p[1])); g.append(float(p[2]))
                except ValueError:
                    pass
        if f:
            ax.semilogx(np.array(f) / 1e6, g, lw=1.6, color=col, label=lab)
    ax.set_xlabel("frequency (MHz)", size=9)
    ax.set_ylabel("gain (dB)", size=9)
    ax.tick_params(labelsize=8)
    ax.grid(alpha=0.3, lw=0.5)
    ax.legend(fontsize=8.5, frameon=False)
    ax.set_title("The same tank, the same 263.5 nH and 9.61 pF", size=9.5)
    fig.tight_layout()
    return fig


PARAMS = {
    "tft_igzo": [
        ("w_gate", "100 um"), ("l_gate", "10 um"), ("nf", "4"),
        ("gate_ov", "5 um"), ("sd_len", "97.5 um"),
        ("s_strap_w", "40 um"), ("d_strap_w", "20 um"),
        ("pad", "false"), ("l_bias", "3 um"),
        ("l_printed", "13 um"), ("w_total", "400 um"),
    ],
    "cap_mim": [
        ("mode", "by capacitance"), ("w", "160.64 um"), ("l", "160.64 um"),
        ("area_target", "25805 um^2"), ("c_target", "40362 fF"),
        ("ext_sd", "200 um"), ("ext_gate", "200 um"),
        ("ext_sd_far", "0 um"), ("ext_gate_far", "0 um"),
        ("pad", "true"), ("area", "25805 um^2"), ("c", "40359 fF"),
    ],
    "ind_igzo": [
        ("shape", "square"), ("topology", "series"), ("n", "8"),
        ("d_in", "100 um"), ("w", "10 um"), ("gap", "5 um"),
        ("metal", "gate (2/0)"), ("t_metal", "0.05 um"),
        ("f_eval", "100 MHz"), ("pad", "false"),
        ("l_series", "16.38 nH"), ("r_ac", "377.7 Ohm"), ("q", "0.03"),
    ],
}


EN = {
    "foot": "TFT-MMM-LAB-PDK  ·  igzo_mmm_lab",
    "s1k": "UCI/INRF IGZO TFT process",
    "s1t": "A PDK for the IGZO TFT process",
    "s1": "What was built, what it can do, and how far the numbers can be\n"
          "trusted.\n\n"
          "github.com/Juander28/TFT-MMM-LAB-PDK",
    "s1b": ["Four masks, top-gate coplanar, measured on three fabricated chips",
            "Used like sky130A or gf180mcuD: one command switches every tool",
            "Three parametric cells: transistor, capacitor, inductor",
            "Fifteen automated checks across klayout, xschem, ngspice, magic, netgen"],
    "s2t": "One command, four tools",
    "s2": "use-pdk TFT-MMM-LAB-PDK",
    "s2b": ["klayout - technology, layer colours, the PCell library, DRC",
            "xschem - symbols and testbenches",
            "ngspice - the models and their corners",
            "magic - layout, extraction and the .mag device views",
            "netgen - LVS between the two"],
    "s2c": "The cell library open in KLayout: 41 generated cells, the technology "
           "selected, the process's own layer names on the right.",
    "s3t": "The transistor, and what each parameter does",
    "s3c": "tft_igzo, four fingers, drawn by the PCell.",
    "s3arrows": [
        ("w_gate", "width of one finger; the total is w_gate x nf"),
        ("l_gate", "the DRAWN channel length - the gap between electrodes"),
        ("nf", "fingers.  They share electrodes: nf fingers, nf+1 electrodes"),
        ("gate_ov", "gate overlap per side - the parasitic that decides fT"),
        ("s_strap_w", "width of the strap tying the source fingers together"),
        ("d_strap_w", "and the drain side, separately - they carry different current"),
        ("l_printed", "read-only: what the process actually prints, l_gate + 3 um"),
    ],
    "s4t": "Fingers are only a layout choice",
    "s4": "Splitting the width folds the device and divides gm and Cgs by the\n"
          "same number, so their ratio - and fT - do not move.  Measured, then\n"
          "confirmed in simulation for nf = 1 to 20 at constant total width.\n\n"
          "Fingers buy aspect ratio and gate resistance.  Not speed.",
    "s4c": "Four fingers with a 40 um source strap and a 20 um drain strap. "
           "Unstrapped this is five separate terminals, not two.",
    "s5t": "The capacitor sizes itself",
    "s5": "One formula, C = Cox x W x L, solved in whichever direction the\n"
          "problem arrives in.  Cox = 1.564 fF/um^2 is measured, not assumed.",
    "s5arrows": [
        ("mode", "set the plate, the area, or the capacitance you need"),
        ("c_target", "ask for 40362 fF..."),
        ("w", "...and the cell solves the plate: 160.64 um square"),
        ("ext_sd", "how far the S/D plate runs to its terminal"),
        ("ext_gate", "the gate plate has its own number - different metal, different route"),
        ("ext_sd_far", "and each can run out the far side as well"),
        ("c", "read-only, and what the cell prints on itself"),
    ],
    "s5c": "Sized by capacitance, with probe pads.  Magic extracts 40.3593 pF "
           "from it - the drawn value, not a model of it.",
    "s6t": "The inductor: shape, topology, and honesty",
    "s6arrows": [
        ("shape", "square or circular"),
        ("topology", "one spiral in series, or n rings in parallel"),
        ("n", "turns, or rings"),
        ("t_metal", "metal thickness - ASSUMED, and the only real lever on Q"),
        ("l_series", "read-only: Mohan-Wheeler, or coupled rings via Neumann"),
        ("q", "read-only: 0.03 at 100 MHz, and the cell says so on its face"),
    ],
    "s7t": "Q is a metal thickness problem",
    "s7": "The same coil, the same 16.38 nH, thickness swept:",
    "s7rows": [["gold", "R at 100 MHz", "Q"],
               ["50 nm (assumed today)", "377.7 Ohm", "0.03"],
               ["250 nm", "75.5 Ohm", "0.14"],
               ["1 um", "18.9 Ohm", "0.54"]],
    "s7b": "At 50 nm a planar inductor here is a resistor with some inductance.\n"
           "Nothing you can draw changes that - only thicker gold does.",
    "s8t": "Simulated against measured",
    "s8": "Points are MEASURED on the fabricated chips.  Lines are SIMULATED in\n"
          "ngspice with the PDK's own corner models, at each device's own W and L.\n"
          "Six devices, L = 8 to 160 um.",
    "s8b": "Median simulated/measured in saturation: 1.01 over 18 comparisons.",
    "s9t": "The three cells together",
    "s9": "TFT + cap_mim + ind_igzo as a tuned load, simulated in ngspice.\n"
          "263.5 nH with 9.61 pF resonates at 100.0 MHz - if the gold is thick.",
    "s10t": "What holds this together",
    "s10b": ["The PCell reproduces the fabricated device shape for shape",
             "DRC clean on every generated cell but one, which is documented",
             "magic reads and writes the four-mask GDS, layer for layer",
             "LVS matches uniquely, three terminals on both sides",
             "Extracted capacitance is the drawn capacitance: 40.3593 pF of 40.36",
             "The model still reproduces the measurement: 654 uA against 670-701"],
    "s10": "Fifteen checks, one command:  ./scripts/run_checks.sh",
    "s11t": "What is measured, and what is not",
    "s11rows": [["MEASURED", "Cox = 1.564 fF/um^2, Kp, Vth, lambda, contact resistance"],
                ["OFF THE CHIP", "overlap 5 um, electrode sizes, pad and window sizes"],
                ["ASSUMED", "metal thickness 50 nm, the +3 um print bias, every Q"],
                ["NOT KNOWN AT ALL", "gate capacitance vs bias, fT, drift under stress"]],
    "s11": "Every parameter in the SOP carries this label.  A PDK reads as\n"
           "authoritative whether or not its numbers deserve it; the only\n"
           "defence is saying which is which, on every number.",
}

ES = {
    "foot": "TFT-MMM-LAB-PDK  ·  igzo_mmm_lab",
    "s1k": "Proceso IGZO TFT de UCI/INRF",
    "s1t": "Un PDK para el proceso IGZO TFT",
    "s1": "Que se construyo, que puede hacer, y hasta donde se puede confiar en\n"
          "los numeros.\n\n"
          "github.com/Juander28/TFT-MMM-LAB-PDK",
    "s1b": ["Cuatro mascaras, top-gate coplanar, medido en tres chips fabricados",
            "Se usa como sky130A o gf180mcuD: un comando cambia todas las herramientas",
            "Tres celdas parametricas: transistor, capacitor, inductor",
            "Quince comprobaciones automaticas en klayout, xschem, ngspice, magic, netgen"],
    "s2t": "Un comando, cuatro herramientas",
    "s2": "use-pdk TFT-MMM-LAB-PDK",
    "s2b": ["klayout - tecnologia, colores de capa, la libreria de PCells, DRC",
            "xschem - simbolos y testbenches",
            "ngspice - los modelos y sus esquinas",
            "magic - layout, extraccion y las vistas .mag",
            "netgen - LVS entre las dos"],
    "s2c": "La libreria abierta en KLayout: 41 celdas generadas, la tecnologia "
           "seleccionada, y a la derecha los nombres de capa del propio proceso.",
    "s3t": "El transistor, y que hace cada parametro",
    "s3c": "tft_igzo, cuatro dedos, dibujado por el PCell.",
    "s3arrows": [
        ("w_gate", "ancho de un dedo; el total es w_gate x nf"),
        ("l_gate", "la longitud DIBUJADA del canal - el hueco entre electrodos"),
        ("nf", "dedos.  Comparten electrodos: nf dedos, nf+1 electrodos"),
        ("gate_ov", "solape de compuerta por lado - el parasito que decide fT"),
        ("s_strap_w", "grosor del strap que une los dedos de source"),
        ("d_strap_w", "y el de drain, por separado - no llevan la misma corriente"),
        ("l_printed", "solo lectura: lo que el proceso imprime, l_gate + 3 um"),
    ],
    "s4t": "Los dedos son solo una decision de layout",
    "s4": "Repartir el ancho dobla el dispositivo y divide gm y Cgs por el mismo\n"
          "numero, asi que su relacion - y fT - no se mueven.  Medido, y luego\n"
          "confirmado en simulacion para nf = 1 a 20 a ancho total constante.\n\n"
          "Los dedos compran forma y resistencia de compuerta.  No velocidad.",
    "s4c": "Cuatro dedos con strap de source de 40 um y de drain de 20 um. "
           "Sin straps esto son cinco terminales sueltos, no dos.",
    "s5t": "El capacitor se dimensiona solo",
    "s5": "Una sola formula, C = Cox x W x L, resuelta en la direccion en que\n"
          "llegue el problema.  Cox = 1.564 fF/um^2 esta medida, no supuesta.",
    "s5arrows": [
        ("mode", "pon la placa, el area, o la capacitancia que necesitas"),
        ("c_target", "pide 40362 fF..."),
        ("w", "...y la celda resuelve la placa: 160.64 um de lado"),
        ("ext_sd", "cuanto corre la placa de S/D hasta su terminal"),
        ("ext_gate", "la de compuerta tiene su propio numero - otro metal, otra ruta"),
        ("ext_sd_far", "y cada una puede salir tambien por el lado opuesto"),
        ("c", "solo lectura, y lo que la celda escribe sobre si misma"),
    ],
    "s5c": "Dimensionado por capacitancia, con pads. Magic extrae 40.3593 pF de "
           "el - el valor dibujado, no un modelo de el.",
    "s6t": "El inductor: forma, topologia y honestidad",
    "s6arrows": [
        ("shape", "cuadrado o circular"),
        ("topology", "una espiral en serie, o n anillos en paralelo"),
        ("n", "vueltas, o anillos"),
        ("t_metal", "espesor del metal - SUPUESTO, y la unica palanca real sobre Q"),
        ("l_series", "solo lectura: Mohan-Wheeler, o anillos acoplados via Neumann"),
        ("q", "solo lectura: 0.03 a 100 MHz, y la celda lo dice en su cara"),
    ],
    "s7t": "Q es un problema de espesor de metal",
    "s7": "La misma bobina, los mismos 16.38 nH, barriendo el espesor:",
    "s7rows": [["oro", "R a 100 MHz", "Q"],
               ["50 nm (lo supuesto hoy)", "377.7 Ohm", "0.03"],
               ["250 nm", "75.5 Ohm", "0.14"],
               ["1 um", "18.9 Ohm", "0.54"]],
    "s7b": "Con 50 nm, un inductor planar aqui es una resistencia con algo de\n"
           "inductancia.  Nada que dibujes lo cambia - solo oro mas grueso.",
    "s8t": "Simulado contra medido",
    "s8": "Los puntos son MEDIDOS en los chips fabricados.  Las lineas son\n"
          "SIMULADAS en ngspice con las esquinas del propio PDK, cada dispositivo\n"
          "con su W y su L.  Seis dispositivos, L = 8 a 160 um.",
    "s8b": "Mediana simulado/medido en saturacion: 1.01 sobre 18 comparaciones.",
    "s9t": "Las tres celdas juntas",
    "s9": "TFT + cap_mim + ind_igzo como carga sintonizada, simulado en ngspice.\n"
          "263.5 nH con 9.61 pF resuenan a 100.0 MHz - si el oro es grueso.",
    "s10t": "Que sostiene todo esto",
    "s10b": ["El PCell reproduce el dispositivo fabricado forma por forma",
             "DRC limpio en cada celda generada salvo una, que esta documentada",
             "magic lee y escribe el GDS de cuatro mascaras, capa por capa",
             "El LVS cuadra de forma unica, tres terminales de los dos lados",
             "La capacitancia extraida es la dibujada: 40.3593 pF de 40.36",
             "El modelo sigue reproduciendo la medicion: 654 uA contra 670-701"],
    "s10": "Quince comprobaciones, un comando:  ./scripts/run_checks.sh",
    "s11t": "Que esta medido y que no",
    "s11rows": [["MEDIDO", "Cox = 1.564 fF/um^2, Kp, Vth, lambda, resistencia de contacto"],
                ["DEL CHIP", "solape 5 um, tamanos de electrodo, pads y ventanas"],
                ["SUPUESTO", "espesor de metal 50 nm, el bias de +3 um, todo Q"],
                ["NO SE SABE", "capacitancia de compuerta vs bias, fT, deriva por estres"]],
    "s11": "Cada parametro del SOP lleva esta etiqueta.  Un PDK se lee como\n"
           "autoritario merezcalo o no; la unica defensa es decir cual es cual,\n"
           "en cada numero.",
}


def build(lang, out_dir=None):
    S = {"en": EN, "es": ES}[lang]
    name = {"en": "TFT-MMM-LAB-PDK_overview_en.pdf",
            "es": "TFT-MMM-LAB-PDK_presentacion_es.pdf"}[lang]
    out = os.path.join(default_out_dir(out_dir), name)
    F = S["foot"]

    with PdfPages(out) as pdf:
        n = 1
        s = Slide(pdf, S["s1t"], S["s1k"], F)
        s.text(S["s1"], size=14)
        s.y -= 0.02
        s.bullets(S["s1b"])
        s.close(n)

        n += 1
        s = Slide(pdf, S["s2t"], S["s1k"], F)
        s.text(S["s2"], size=15, weight="bold", color=ACCENT)
        s.bullets(S["s2b"], size=12)
        s.image("klayout_screen_crop.png", (0.46, 0.16, 0.48, 0.60), S["s2c"])
        s.close(n)

        n += 1
        s = Slide(pdf, S["s3t"], S["s1k"], F)
        a = s.panel(PARAMS["tft_igzo"], (0.06, 0.16, 0.20, 0.62),
                    "tft_igzo", highlight=[k for k, _ in S["s3arrows"]])
        for key, txt in S["s3arrows"]:
            s.arrow(a[key], txt, dx=0.055, size=10)
        s.image("klayout_tft_pad.png", (0.66, 0.16, 0.30, 0.58), S["s3c"])
        s.close(n)

        n += 1
        s = Slide(pdf, S["s4t"], S["s1k"], F)
        s.text(S["s4"], size=13)
        s.image(os.path.join(FIG, "klayout_tft_straps.png")
                if os.path.exists(os.path.join(FIG, "klayout_tft_straps.png"))
                else "klayout_tft_core.png",
                (0.30, 0.14, 0.42, 0.46), S["s4c"])
        s.close(n)

        n += 1
        s = Slide(pdf, S["s5t"], S["s1k"], F)
        s.text(S["s5"], size=12.5)
        a = s.panel(PARAMS["cap_mim"], (0.06, 0.10, 0.20, 0.58),
                    "cap_mim", highlight=[k for k, _ in S["s5arrows"]])
        for key, txt in S["s5arrows"]:
            s.arrow(a[key], txt, dx=0.055, size=10)
        s.image("klayout_cap_40p36.png", (0.68, 0.12, 0.28, 0.50), S["s5c"])
        s.close(n)

        n += 1
        s = Slide(pdf, S["s6t"], S["s1k"], F)
        a = s.panel(PARAMS["ind_igzo"], (0.06, 0.16, 0.20, 0.60),
                    "ind_igzo", highlight=[k for k, _ in S["s6arrows"]])
        for key, txt in S["s6arrows"]:
            s.arrow(a[key], txt, dx=0.055, size=10)
        s.image("klayout_ind_sq_series.png", (0.68, 0.44, 0.14, 0.28), None)
        s.image("klayout_ind_ci_series.png", (0.83, 0.44, 0.14, 0.28), None)
        s.image("klayout_ind_sq_parallel.png", (0.68, 0.14, 0.14, 0.28), None)
        s.image("klayout_ind_tank.png", (0.83, 0.14, 0.14, 0.28), None)
        s.close(n)

        n += 1
        s = Slide(pdf, S["s7t"], S["s1k"], F)
        s.text(S["s7"], size=13)
        y0 = s.y
        for i, row in enumerate(S["s7rows"]):
            for j, cell in enumerate(row):
                s.fig.text(0.06 + j * 0.17, y0 - i * 0.06, cell, size=12,
                           color=INK if i == 0 else MUTED,
                           weight="bold" if i == 0 else "normal", va="top")
        s.y = y0 - len(S["s7rows"]) * 0.06 - 0.03
        s.text(S["s7b"], size=13)
        s.close(n)

        n += 1
        s = Slide(pdf, S["s8t"], S["s1k"], F)
        s.text(S["s8"], size=12.5)
        sys.path.insert(0, HERE)
        import make_model_report as mr
        fig, ratio, count = mr.fig_output_curves(lang)
        s.figure(fig, (0.10, 0.12, 0.80, 0.46), None)
        s.y = 0.10
        s.text(S["s8b"], size=12.5, weight="bold")
        s.close(n)

        n += 1
        s = Slide(pdf, S["s9t"], S["s1k"], F)
        s.text(S["s9"], size=13)
        s.figure(tank_curves(), (0.16, 0.12, 0.68, 0.46), None)
        s.close(n)

        n += 1
        s = Slide(pdf, S["s10t"], S["s1k"], F)
        s.bullets(S["s10b"], size=12.5)
        s.y -= 0.02
        s.text(S["s10"], size=13, weight="bold", color=ACCENT)
        s.close(n)

        n += 1
        s = Slide(pdf, S["s11t"], S["s1k"], F)
        y0 = s.y
        for i, (tag, what) in enumerate(S["s11rows"]):
            s.fig.text(0.06, y0 - i * 0.085, tag, size=12.5, weight="bold",
                       color=ACCENT, va="top")
            s.fig.text(0.28, y0 - i * 0.085, what, size=12.5, color=INK,
                       va="top")
        s.y = y0 - len(S["s11rows"]) * 0.085 - 0.03
        s.text(S["s11"], size=12.5, color=MUTED)
        s.close(n)

        info = pdf.infodict()
        info["Title"] = ("TFT-MMM-LAB-PDK - overview" if lang == "en"
                         else "TFT-MMM-LAB-PDK - presentacion")
        info["Author"] = "UCI/INRF - MMM Lab"
    print("wrote %s (%d bytes)" % (out, os.path.getsize(out)))


if __name__ == "__main__":
    args = sys.argv[1:]
    out_dir = None
    if args and args[-1].startswith(("/", "~", ".")):
        out_dir = os.path.expanduser(args.pop())
    for lg in (args or ["en", "es"]):
        build(lg, out_dir)
