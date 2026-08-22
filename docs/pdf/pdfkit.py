"""
The page engine behind the PDK's documents.

One Page class, used by make_pdf.py, make_sop.py and make_model_report.py, so
the three documents look like one set rather than three efforts.  Text, code
blocks, tables and figures, laid out top-down on A4 with a margin the caller
never has to think about.

Everything is positioned in figure coordinates (0..1).  Line heights come from
the font size rather than from constants, which is what stops paragraphs
overlapping when someone changes a size.
"""

import os
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.backends.backend_pdf import PdfPages   # noqa: F401  (re-export)

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.normpath(os.path.join(HERE, "..", "figures"))

A4 = (8.27, 11.69)
INK = "#1a1a1a"
MUTED = "#555555"
ACCENT = "#8a3324"
RULE = "#c9c4bd"
CODEBG = "#f2f0ec"
L, R = 0.075, 0.925
TOP = 0.945


def lh(size, lead=1.45):
    """Line height in figure coordinates for a font size in points."""
    return size / 72.0 / A4[1] * lead


DEFAULT_OUT = os.path.expanduser("~/Documents/PDK-TFT-MMM-LAB/docs")


def default_out_dir(argv_dir=None):
    """Where the PDFs go: the argument if given, otherwise the Documents folder."""
    out = argv_dir or os.environ.get("PDK_DOC_DIR") or DEFAULT_OUT
    os.makedirs(out, exist_ok=True)
    return out


class Page:
    def __init__(self, pdf, title, kicker=None, footer=""):
        self.pdf = pdf
        self.footer = footer
        self.fig = plt.figure(figsize=A4)
        self.fig.patch.set_facecolor("white")
        self.y = TOP
        if kicker:
            self.fig.text(L, self.y, kicker.upper(), size=7.5, color=ACCENT,
                          weight="bold", family="DejaVu Sans", va="top")
            self.y -= lh(7.5, 2.2)
        for line in title.split("\n"):
            self.fig.text(L, self.y, line, size=17, color=INK, weight="bold",
                          family="DejaVu Sans", va="top")
            self.y -= lh(17, 1.25)
        self.y -= 0.012
        self.rule()

    def rule(self, gap=0.014):
        self.fig.add_artist(plt.Line2D([L, R], [self.y, self.y],
                                       color=RULE, lw=0.8))
        self.y -= gap

    def text(self, s, size=9.2, color=INK, gap=None, weight="normal"):
        step = gap if gap else lh(size)
        for line in s.split("\n"):
            self.fig.text(L, self.y, line, size=size, color=color,
                          family="DejaVu Sans", va="top", weight=weight)
            self.y -= step
        self.y -= 0.006

    def head(self, s):
        self.y -= 0.012
        self.fig.text(L, self.y, s, size=11, color=ACCENT, weight="bold",
                      family="DejaVu Sans", va="top")
        self.y -= lh(11, 2.0)

    def code(self, s, size=8.2, pad=0.010):
        step = lh(size, 1.5)
        lines = s.strip("\n").split("\n")
        h = len(lines) * step + 2 * pad
        self.fig.add_artist(plt.Rectangle((L - 0.012, self.y - h + step * 0.25),
                                          R - L + 0.024, h, facecolor=CODEBG,
                                          edgecolor="none",
                                          transform=self.fig.transFigure))
        self.y -= pad
        for line in lines:
            self.fig.text(L, self.y, line, size=size, color=INK,
                          family="DejaVu Sans Mono", va="top")
            self.y -= step
        self.y -= pad + 0.006

    def table(self, rows, widths, size=8.6, header=True, gap=None):
        step = gap if gap else lh(size, 1.7)
        xs = [L]
        for w in widths[:-1]:
            xs.append(xs[-1] + w * (R - L))
        for i, row in enumerate(rows):
            bold = "bold" if (header and i == 0) else "normal"
            col = INK if (header and i == 0) else MUTED
            for x, cell in zip(xs, row):
                self.fig.text(x, self.y, cell, size=size, color=col,
                              family="DejaVu Sans", va="top", weight=bold)
            self.y -= step
            if header and i == 0:
                self.y += step * 0.25
                self.rule(gap=0.010)
        self.y -= 0.006

    def figure(self, fig, caption=None, width=1.0):
        """Place a matplotlib figure that was drawn on the fly."""
        import io
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=200, bbox_inches="tight",
                    facecolor="white")
        plt.close(fig)
        buf.seek(0)
        return self._place(mpimg.imread(buf), caption, width)

    def image(self, path, caption=None, width=1.0, crop=None):
        img = mpimg.imread(path if os.path.isabs(path)
                           else os.path.join(FIG, path))
        if crop:
            x0, y0, x1, y1 = crop
            img = img[y0:y1, x0:x1]
        return self._place(img, caption, width)

    def _place(self, img, caption, width):
        ih, iw = img.shape[0], img.shape[1]
        w_fig = (R - L) * width
        h_fig = w_fig * (ih / iw) * (A4[0] / A4[1])
        avail = self.y - 0.085 - (0.048 if caption else 0.0)
        if h_fig > avail:
            scale = avail / h_fig
            h_fig *= scale
            w_fig *= scale
        x0 = L + ((R - L) - w_fig) / 2
        ax = self.fig.add_axes([x0, self.y - h_fig, w_fig, h_fig])
        ax.imshow(img)
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_color(RULE)
            spine.set_linewidth(0.6)
        self.y -= h_fig + 0.008
        if caption:
            for line in textwrap.wrap(caption, 118):
                self.fig.text(L, self.y, line, size=7.8, color=MUTED,
                              family="DejaVu Sans", va="top", style="italic")
                self.y -= lh(7.8)
        self.y -= 0.010

    def close(self, n):
        if self.y < 0.075:
            print("  ! page %d overflows: y=%.3f" % (n, self.y))
        self.fig.text(R, 0.035, str(n), size=8, color=MUTED, ha="right")
        self.fig.text(L, 0.035, self.footer, size=8, color=MUTED)
        self.pdf.savefig(self.fig)
        plt.close(self.fig)


