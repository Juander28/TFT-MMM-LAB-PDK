"""
coil_ui.py
Shared GUI components for microcoil_calculator.py and awg_coil_calculator.py
- Theme (stylesheet)
- Translation helper + LanguageManager
- DimensionInput, FreqInput
- MplCanvas (matplotlib in PyQt)
- BibliographyDialog
- ExportDialog
- About / language toggle dialog
- Drawing helpers (microcoil + AWG) with modern aesthetic
"""

import os
import csv
import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets

import matplotlib
matplotlib.use("Qt5Agg")
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle, Circle, FancyBboxPatch, Wedge
from matplotlib.collections import PatchCollection
import matplotlib.patheffects as pe

import coil_core as cc

PALETTE = cc.PALETTE


# =====================================================================
# Language manager — singleton-ish (global current language)
# =====================================================================

class LanguageManager(QtCore.QObject):
    languageChanged = QtCore.pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._lang = "en"

    @property
    def lang(self):
        return self._lang

    def set_lang(self, lang):
        if lang == self._lang:
            return
        self._lang = lang
        self.languageChanged.emit(lang)

    def tr(self, text):
        return cc.tr(text, self._lang)


LM = LanguageManager()


def tr(text):
    """Atajo global."""
    return LM.tr(text)


# =====================================================================
# Input widgets with unit selectors
# =====================================================================

class DimensionInput(QtWidgets.QWidget):
    valueChanged = QtCore.pyqtSignal()

    def __init__(self, label_text, default_value=10.0, default_unit="um",
                 label_width=130, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self._label_key = label_text
        self.label = QtWidgets.QLabel(tr(label_text))
        self.label.setMinimumWidth(label_width)
        self.spin = QtWidgets.QDoubleSpinBox()
        self.spin.setRange(0.0, 1e9)
        self.spin.setDecimals(6)
        self.spin.setValue(default_value)
        self.spin.setMaximumWidth(110)
        self.unit = QtWidgets.QComboBox()
        self.unit.addItems(cc.UNIT_ORDER)
        self.unit.setCurrentText(default_unit)
        self.unit.setMaximumWidth(60)
        layout.addWidget(self.label)
        layout.addWidget(self.spin)
        layout.addWidget(self.unit)
        self.spin.valueChanged.connect(self.valueChanged.emit)
        self.unit.currentTextChanged.connect(self.valueChanged.emit)
        LM.languageChanged.connect(self._retranslate)

    def _retranslate(self, _lang):
        self.label.setText(tr(self._label_key))

    def value_in_meters(self):
        return cc.to_meters(self.spin.value(), self.unit.currentText())

    def setEnabled(self, enabled):
        self.spin.setEnabled(enabled)
        self.unit.setEnabled(enabled)


class FreqInput(QtWidgets.QWidget):
    valueChanged = QtCore.pyqtSignal()

    def __init__(self, label_text, default_value=1.0, default_unit="MHz",
                 label_width=130, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self._label_key = label_text
        self.label = QtWidgets.QLabel(tr(label_text))
        self.label.setMinimumWidth(label_width)
        self.spin = QtWidgets.QDoubleSpinBox()
        self.spin.setRange(0.0, 1e6)
        self.spin.setDecimals(4)
        self.spin.setValue(default_value)
        self.spin.setMaximumWidth(110)
        self.unit = QtWidgets.QComboBox()
        self.unit.addItems(cc.FREQ_ORDER)
        self.unit.setCurrentText(default_unit)
        self.unit.setMaximumWidth(60)
        layout.addWidget(self.label)
        layout.addWidget(self.spin)
        layout.addWidget(self.unit)
        self.spin.valueChanged.connect(self.valueChanged.emit)
        self.unit.currentTextChanged.connect(self.valueChanged.emit)
        LM.languageChanged.connect(self._retranslate)

    def _retranslate(self, _lang):
        self.label.setText(tr(self._label_key))

    def value_in_hz(self):
        return cc.to_hz(self.spin.value(), self.unit.currentText())


# =====================================================================
# Matplotlib canvas
# =====================================================================

class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100, n_axes=1):
        self.fig = Figure(figsize=(width, height), dpi=dpi,
                          constrained_layout=True, facecolor=PALETTE["bg_canvas"])
        if n_axes == 1:
            self.ax = self.fig.add_subplot(111)
            self.axes = [self.ax]
        else:
            self.axes = [self.fig.add_subplot(n_axes, 1, i + 1) for i in range(n_axes)]
            self.ax = self.axes[0]
        for a in self.axes:
            a.set_facecolor(PALETTE["bg_axes"])
            for spine in a.spines.values():
                spine.set_color(PALETTE["grid"])
            a.tick_params(colors=PALETTE["text"])
        super().__init__(self.fig)
        self.setParent(parent)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)


def style_axes(ax, title=None, xlabel=None, ylabel=None):
    ax.set_facecolor(PALETTE["bg_axes"])
    if title:
        ax.set_title(title, color=PALETTE["text"], fontweight="600", fontsize=11)
    if xlabel:
        ax.set_xlabel(xlabel, color=PALETTE["text"], fontsize=10)
    if ylabel:
        ax.set_ylabel(ylabel, color=PALETTE["text"], fontsize=10)
    ax.grid(True, alpha=0.4, color=PALETTE["grid"], linewidth=0.7)
    ax.tick_params(colors=PALETTE["text"])
    for spine in ax.spines.values():
        spine.set_color(PALETTE["grid"])


# =====================================================================
# Bibliography Dialog
# =====================================================================

class BibliographyDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Bibliography"))
        self.resize(720, 620)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(10)
        self.browser = QtWidgets.QTextBrowser()
        self.browser.setHtml(cc.bibliography_html(LM.lang))
        layout.addWidget(self.browser)
        self.btn = QtWidgets.QPushButton(tr("Close"))
        self.btn.setProperty("secondary", True)
        self.btn.clicked.connect(self.accept)
        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(self.btn)
        layout.addLayout(btn_row)
        LM.languageChanged.connect(self._retranslate)

    def _retranslate(self, _lang):
        self.setWindowTitle(tr("Bibliography"))
        self.browser.setHtml(cc.bibliography_html(LM.lang))
        self.btn.setText(tr("Close"))


# =====================================================================
# About / Language dialog
# =====================================================================

class AboutDialog(QtWidgets.QDialog):
    def __init__(self, parent, app_title_key, body_key):
        super().__init__(parent)
        self.app_title_key = app_title_key
        self.body_key = body_key
        self.setWindowTitle(tr("About"))
        self.resize(460, 360)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(12)

        self.title_lbl = QtWidgets.QLabel(tr(app_title_key))
        self.title_lbl.setProperty("header", True)
        layout.addWidget(self.title_lbl)

        self.body_lbl = QtWidgets.QLabel(tr(body_key))
        self.body_lbl.setWordWrap(True)
        layout.addWidget(self.body_lbl)

        self.refs_lbl = QtWidgets.QLabel(
            tr("Equations: Mohan 1999, Greenhouse 1974, Babic-Akyel 2008.\nSee Bibliography menu for full references.")
            if "Microcoil" in app_title_key else
            tr("Equations: Wheeler 1928 (multilayer), Babic-Akyel 2008 (coupling).")
        )
        self.refs_lbl.setStyleSheet("color:#6b6b6b; font-size: 9pt;")
        self.refs_lbl.setWordWrap(True)
        layout.addWidget(self.refs_lbl)

        layout.addSpacing(8)
        # Language toggle
        lang_box = QtWidgets.QGroupBox(tr("Language"))
        lang_layout = QtWidgets.QHBoxLayout(lang_box)
        self.rb_en = QtWidgets.QRadioButton(tr("English"))
        self.rb_es = QtWidgets.QRadioButton(tr("Spanish"))
        if LM.lang == "en":
            self.rb_en.setChecked(True)
        else:
            self.rb_es.setChecked(True)
        self.rb_en.toggled.connect(lambda c: c and LM.set_lang("en"))
        self.rb_es.toggled.connect(lambda c: c and LM.set_lang("es"))
        lang_layout.addWidget(self.rb_en)
        lang_layout.addWidget(self.rb_es)
        layout.addWidget(lang_box)

        layout.addStretch()
        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch()
        self.btn = QtWidgets.QPushButton(tr("Close"))
        self.btn.clicked.connect(self.accept)
        btn_row.addWidget(self.btn)
        layout.addLayout(btn_row)

        LM.languageChanged.connect(self._retranslate)

    def _retranslate(self, _lang):
        self.setWindowTitle(tr("About"))
        self.title_lbl.setText(tr(self.app_title_key))
        self.body_lbl.setText(tr(self.body_key))
        self.btn.setText(tr("Close"))


# =====================================================================
# Export dialog
# =====================================================================

class ExportDialog(QtWidgets.QDialog):
    """
    Selecciona qué exportar: CSV de L/R/Q (datos de rango), PNG de gráficas
    individuales o combinada, PNG del dibujo de la bobina.
    """

    def __init__(self, parent, *, has_range_data, range_data=None,
                 plot_fig=None, plot_axes=None, draw_fig=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Export options"))
        self.resize(480, 520)
        self.has_range = has_range_data
        self.range_data = range_data or {}
        self.plot_fig = plot_fig
        self.plot_axes = plot_axes or []
        self.draw_fig = draw_fig

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(10)

        self.hdr = QtWidgets.QLabel(tr("Export options"))
        self.hdr.setProperty("header", True)
        layout.addWidget(self.hdr)

        self.note = QtWidgets.QLabel(tr("Choose what to export. CSV requires range mode to be active."))
        self.note.setWordWrap(True)
        self.note.setStyleSheet("color:#6b6b6b;")
        layout.addWidget(self.note)

        # Data section
        self.box_data = QtWidgets.QGroupBox(tr("Data (CSV)"))
        dl = QtWidgets.QVBoxLayout(self.box_data)
        self.chk_csv_L = QtWidgets.QCheckBox(tr("Inductance data"))
        self.chk_csv_R = QtWidgets.QCheckBox(tr("Resistance data"))
        self.chk_csv_Q = QtWidgets.QCheckBox(tr("Q-factor data"))
        for c in [self.chk_csv_L, self.chk_csv_R, self.chk_csv_Q]:
            c.setEnabled(self.has_range)
            dl.addWidget(c)
        layout.addWidget(self.box_data)

        # Image section
        self.box_img = QtWidgets.QGroupBox(tr("Images (PNG)"))
        il = QtWidgets.QVBoxLayout(self.box_img)
        self.chk_png_L = QtWidgets.QCheckBox(tr("Inductance plot"))
        self.chk_png_R = QtWidgets.QCheckBox(tr("Resistance plot"))
        self.chk_png_Q = QtWidgets.QCheckBox(tr("Q-factor plot"))
        self.chk_png_all = QtWidgets.QCheckBox(tr("All three plots (combined)"))
        self.chk_png_draw = QtWidgets.QCheckBox(tr("Coil drawing"))
        for c in [self.chk_png_L, self.chk_png_R, self.chk_png_Q, self.chk_png_all]:
            c.setEnabled(self.has_range)
            il.addWidget(c)
        il.addWidget(self.chk_png_draw)  # drawing siempre disponible
        layout.addWidget(self.box_img)

        # Folder + prefix
        folder_box = QtWidgets.QGroupBox(tr("Output folder:"))
        fl = QtWidgets.QGridLayout(folder_box)
        self.le_folder = QtWidgets.QLineEdit(os.path.expanduser("~"))
        self.btn_browse = QtWidgets.QPushButton(tr("Browse…"))
        self.btn_browse.setProperty("secondary", True)
        self.btn_browse.clicked.connect(self._browse)
        fl.addWidget(self.le_folder, 0, 0)
        fl.addWidget(self.btn_browse, 0, 1)
        fl.addWidget(QtWidgets.QLabel(tr("File prefix:")), 1, 0)
        self.le_prefix = QtWidgets.QLineEdit("coil_export")
        fl.addWidget(self.le_prefix, 1, 1)
        layout.addWidget(folder_box)

        layout.addStretch()

        # Buttons
        brow = QtWidgets.QHBoxLayout()
        brow.addStretch()
        self.btn_cancel = QtWidgets.QPushButton(tr("Cancel"))
        self.btn_cancel.setProperty("secondary", True)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_export = QtWidgets.QPushButton(tr("Export"))
        self.btn_export.clicked.connect(self._do_export)
        brow.addWidget(self.btn_cancel)
        brow.addWidget(self.btn_export)
        layout.addLayout(brow)

    def _browse(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self, tr("Choose output folder"), self.le_folder.text()
        )
        if folder:
            self.le_folder.setText(folder)

    def _selected_csv(self):
        out = []
        if self.chk_csv_L.isChecked():
            out.append(("L", "Inductance", self.range_data.get("L"), self.range_data.get("L_unit")))
        if self.chk_csv_R.isChecked():
            out.append(("R", "Resistance_Ohm", self.range_data.get("R"), "Ohm"))
        if self.chk_csv_Q.isChecked():
            out.append(("Q", "Q_factor", self.range_data.get("Q"), ""))
        return out

    def _do_export(self):
        folder = self.le_folder.text().strip()
        prefix = self.le_prefix.text().strip() or "coil_export"
        if not folder or not os.path.isdir(folder):
            QtWidgets.QMessageBox.warning(self, tr("Export"), tr("Select an output folder."))
            return

        written = []
        # CSV
        csv_items = self._selected_csv()
        if csv_items and not self.has_range:
            QtWidgets.QMessageBox.warning(self, tr("Export"),
                                          tr("Range mode is not active — no data to export."))
            return

        xs = self.range_data.get("xs")
        xlabel = self.range_data.get("xlabel", "x")
        for key, name, ys, unit in csv_items:
            if ys is None:
                continue
            path = os.path.join(folder, f"{prefix}_{key}.csv")
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow([xlabel, f"{name} [{unit}]" if unit else name])
                for x, y in zip(xs, ys):
                    w.writerow([x, y])
            written.append(path)

        # PNG plots (individuales)
        if self.has_range and self.plot_axes:
            singles = [
                (0, self.chk_png_L, "Lplot"),
                (1, self.chk_png_R, "Rplot"),
                (2, self.chk_png_Q, "Qplot"),
            ]
            for idx, chk, key in singles:
                if not chk.isChecked() or idx >= len(self.plot_axes):
                    continue
                ax = self.plot_axes[idx]
                # Salvar el subplot a una nueva figura aislada
                from matplotlib.figure import Figure as _F
                tmp_fig = _F(figsize=(6, 4), dpi=120, facecolor=PALETTE["bg_canvas"])
                tmp_ax = tmp_fig.add_subplot(111)
                tmp_ax.set_facecolor(PALETTE["bg_axes"])
                for line in ax.get_lines():
                    tmp_ax.plot(line.get_xdata(), line.get_ydata(),
                                color=line.get_color(), linewidth=line.get_linewidth(),
                                marker=line.get_marker(), markersize=line.get_markersize())
                tmp_ax.set_xlabel(ax.get_xlabel())
                tmp_ax.set_ylabel(ax.get_ylabel())
                tmp_ax.set_title(ax.get_title())
                tmp_ax.grid(True, alpha=0.4, color=PALETTE["grid"], linewidth=0.7)
                tmp_fig.tight_layout()
                path = os.path.join(folder, f"{prefix}_{key}.png")
                tmp_fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=PALETTE["bg_canvas"])
                written.append(path)

        # PNG combinado
        if self.has_range and self.chk_png_all.isChecked() and self.plot_fig is not None:
            path = os.path.join(folder, f"{prefix}_plots_combined.png")
            self.plot_fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=PALETTE["bg_canvas"])
            written.append(path)

        # PNG dibujo
        if self.chk_png_draw.isChecked() and self.draw_fig is not None:
            path = os.path.join(folder, f"{prefix}_drawing.png")
            self.draw_fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=PALETTE["bg_canvas"])
            written.append(path)

        if not written:
            QtWidgets.QMessageBox.information(self, tr("Export"), tr("No items selected."))
            return

        msg = tr("Files written to:") + "\n\n" + folder + "\n\n" + "\n".join(
            "• " + os.path.basename(p) for p in written
        )
        QtWidgets.QMessageBox.information(self, tr("Export complete"), msg)
        self.accept()


# =====================================================================
# Drawing helpers — microcoil
# =====================================================================

def _coil_lw(w_m, lim):
    """Ancho de linea visual proporcional al ancho de pista en pantalla."""
    # Aprox: 1 unidad axes ≈ 200 px en figura típica.
    return max(1.5, min(20.0, w_m / lim * 60))


def draw_microcoil(ax, *, d_in, w, gap, N, shape, topology):
    """Dibuja la bobina microcoil. shape: 'circular'|'cuadrada'.
    topology: 'serie'|'paralelo'.
    Aestética: gradiente cobre/oro, pads coloridos, fondo crema."""
    ax.clear()
    ax.set_aspect("equal")
    ax.set_facecolor(PALETTE["bg_axes"])
    d_out = cc.outer_diameter(d_in, w, gap, N)
    lim = d_out * 0.65
    pad_size = max(w * 4, d_in * 0.5, d_out * 0.08)
    pad_y_top = -d_out / 2 - pad_size * 0.8
    pad_y_bot = pad_y_top - pad_size

    # Linewidth visual
    LW = _coil_lw(w, d_out)

    if topology == "serie":
        if shape == "circular":
            pitch = w + gap
            theta = np.linspace(0, 2 * np.pi * N, max(500, int(220 * N)))
            r0 = d_in / 2.0 + w / 2.0
            r = r0 + (pitch / (2 * np.pi)) * theta
            x = r * np.cos(theta)
            y = r * np.sin(theta)
            # Trazo doble: sombra + cobre
            ax.plot(x, y, color=PALETTE["copper_dark"], linewidth=LW + 1.5, solid_capstyle="round")
            ax.plot(x, y, color=PALETTE["copper"], linewidth=LW, solid_capstyle="round",
                    path_effects=[pe.Stroke(linewidth=LW + 0.5, foreground=PALETTE["copper_dark"]),
                                  pe.Normal()])
            # Conector hacia pads
            x_end, y_end = x[-1], y[-1]
            ax.plot([x_end, x_end], [y_end, pad_y_top], color=PALETTE["copper"], linewidth=LW)
            ax.plot([x_end, x_end], [y_end, pad_y_top], color=PALETTE["copper_dark"], linewidth=LW + 1, zorder=-1)
            # Conector del centro (cruce) hacia otro pad
            ax.plot([0, -pad_size * 1.5], [0, pad_y_top + pad_size * 0.3],
                    color=PALETTE["copper_light"], linewidth=LW * 0.9, linestyle="--", alpha=0.85)
        else:
            # Cuadrada serie
            pts = [(d_in / 2.0 + w / 2.0, 0.0)]
            direction = 0
            side = d_in
            pitch = w + gap
            quarters = int(np.ceil(N * 4))
            for q in range(quarters):
                if q / 4.0 >= N:
                    break
                x, y = pts[-1]
                if direction == 0:
                    y += side
                elif direction == 1:
                    x -= side + pitch
                    side += pitch
                elif direction == 2:
                    y -= side + pitch
                    side += pitch
                else:
                    x += side + pitch
                    side += pitch
                pts.append((x, y))
                direction = (direction + 1) % 4
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            ax.plot(xs, ys, color=PALETTE["copper_dark"], linewidth=LW + 1.5,
                    solid_capstyle="round", solid_joinstyle="miter")
            ax.plot(xs, ys, color=PALETTE["copper"], linewidth=LW,
                    solid_capstyle="round", solid_joinstyle="miter")
            # Conector central
            ax.plot([0, -pad_size * 1.5], [0, pad_y_top + pad_size * 0.3],
                    color=PALETTE["copper_light"], linewidth=LW * 0.9, linestyle="--", alpha=0.85)
            ax.plot([xs[-1], xs[-1]], [ys[-1], pad_y_top], color=PALETTE["copper"], linewidth=LW)
    else:
        # Paralelo: anillos concéntricos rellenados (annulus)
        pitch = w + gap
        for k in range(int(np.floor(N))):
            r_in = d_in / 2.0 + k * pitch
            r_out = r_in + w
            if shape == "circular":
                ring_color = PALETTE["copper"]
                # Annulus: dos circulos con relleno usando Wedge / fill_between
                theta = np.linspace(0, 2 * np.pi, 200)
                ax.fill(np.concatenate([r_out * np.cos(theta), r_in * np.cos(theta)[::-1]]),
                        np.concatenate([r_out * np.sin(theta), r_in * np.sin(theta)[::-1]]),
                        color=ring_color, edgecolor=PALETTE["copper_dark"], linewidth=1.2, alpha=0.95)
            else:
                # Cuadrada: dos rectángulos
                outer = Rectangle((-r_out, -r_out), 2 * r_out, 2 * r_out,
                                  facecolor=PALETTE["copper"], edgecolor=PALETTE["copper_dark"],
                                  linewidth=1.2, alpha=0.95)
                ax.add_patch(outer)
                inner = Rectangle((-r_in, -r_in), 2 * r_in, 2 * r_in,
                                  facecolor=PALETTE["bg_axes"], edgecolor=PALETTE["copper_dark"],
                                  linewidth=0.8)
                ax.add_patch(inner)
        # Conectores ramificados desde pads a cada anillo
        for k in range(int(np.floor(N))):
            r_mid = d_in / 2.0 + k * pitch + w / 2.0
            ax.plot([-pad_size * 0.5, -r_mid * 0.6], [pad_y_top + pad_size * 0.5, -d_out / 2],
                    color=PALETTE["copper_dark"], linewidth=1.0, alpha=0.6)
            ax.plot([pad_size * 0.5, r_mid * 0.6], [pad_y_top + pad_size * 0.5, -d_out / 2],
                    color=PALETTE["copper_dark"], linewidth=1.0, alpha=0.6)

    # Pads
    pad_left = FancyBboxPatch((-pad_size * 1.5, pad_y_bot), pad_size, pad_size,
                              boxstyle="round,pad=0.0,rounding_size=0.0",
                              facecolor=PALETTE["pad"], edgecolor=PALETTE["pad_edge"], linewidth=1.5)
    pad_right = FancyBboxPatch((pad_size * 0.5, pad_y_bot), pad_size, pad_size,
                               boxstyle="round,pad=0.0,rounding_size=0.0",
                               facecolor=PALETTE["pad"], edgecolor=PALETTE["pad_edge"], linewidth=1.5)
    ax.add_patch(pad_left)
    ax.add_patch(pad_right)
    # Hatching diagonal en pads (para parecerse al render del usuario)
    pad_left_h = Rectangle((-pad_size * 1.5, pad_y_bot), pad_size, pad_size,
                           facecolor="none", edgecolor=PALETTE["pad_edge"], hatch="///",
                           linewidth=0.0, alpha=0.6)
    pad_right_h = Rectangle((pad_size * 0.5, pad_y_bot), pad_size, pad_size,
                            facecolor="none", edgecolor=PALETTE["pad_edge"], hatch="///",
                            linewidth=0.0, alpha=0.6)
    ax.add_patch(pad_left_h)
    ax.add_patch(pad_right_h)

    # Cotas
    annotate_dimensions(ax, d_in, w, gap, N, d_out)

    ax.set_xlim(-lim * 1.4, lim * 1.4)
    ax.set_ylim(pad_y_bot - pad_size * 0.6, lim * 1.1)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)


def annotate_dimensions(ax, d_in, w, gap, N, d_out):
    """Cotas con flechas pulidas."""
    arrow_kw = dict(arrowstyle="<->", color="#2c2c2c", lw=1.0,
                    shrinkA=0, shrinkB=0)
    # d_in (en blanco superior)
    ax.annotate("", xy=(d_in / 2, 0), xytext=(-d_in / 2, 0),
                arrowprops=dict(arrowstyle="<->", color="#1d4ed8", lw=1.2))
    ax.text(0, d_in * 0.10 + w * 0.5,
            f"d_in = {fmt_dim(d_in)}",
            color="#1d4ed8", ha="center", fontsize=8.5, fontweight="600",
            bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor="#1d4ed8", alpha=0.85))
    # d_out
    y_top = d_out / 2 * 1.08
    ax.annotate("", xy=(d_out / 2, y_top), xytext=(-d_out / 2, y_top),
                arrowprops=dict(arrowstyle="<->", color="#15803d", lw=1.2))
    ax.text(0, y_top + d_out * 0.04,
            f"d_out = {fmt_dim(d_out)}",
            color="#15803d", ha="center", fontsize=8.5, fontweight="600",
            bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor="#15803d", alpha=0.85))
    # w + gap
    x_right = d_out / 2 * 1.18
    ax.annotate("", xy=(x_right, w / 2), xytext=(x_right, -w / 2),
                arrowprops=dict(arrowstyle="<->", color="#7c3aed", lw=1.0))
    ax.text(x_right + d_out * 0.02, 0,
            f"w = {fmt_dim(w)}\ngap = {fmt_dim(gap)}",
            color="#7c3aed", fontsize=8, fontweight="600",
            bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor="#7c3aed", alpha=0.85),
            va="center")
    # N counter
    ax.text(-d_out / 2 * 1.18, d_out / 2 * 0.85,
            f"N = {N:.1f}",
            color=PALETTE["accent"], fontsize=10, fontweight="700",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                      edgecolor=PALETTE["accent"], alpha=0.95))


def fmt_dim(v_m):
    """Formatea longitud en unidad apropiada."""
    av = abs(v_m)
    if av >= 1e-3:
        return f"{v_m*1e3:.2f} mm"
    if av >= 1e-6:
        return f"{v_m*1e6:.2f} μm"
    if av >= 1e-9:
        return f"{v_m*1e9:.2f} nm"
    return f"{v_m:.2e} m"


# =====================================================================
# Drawing helpers — AWG coil
# =====================================================================

def draw_cylindrical_solenoid(ax, *, d_in, d_wire, N_per_layer, N_layers):
    """Vista de corte axial del solenoide cilíndrico multicapa.
    Eje X = posición axial; Eje Y = radio (top y bottom)."""
    ax.clear()
    ax.set_aspect("equal")
    ax.set_facecolor(PALETTE["bg_axes"])
    r_in = d_in / 2.0
    H = N_per_layer * d_wire
    d_out = d_in + 2 * N_layers * d_wire
    # Núcleo (hueco)
    core = Rectangle((0, -r_in), H, 2 * r_in,
                     facecolor="#fefefe", edgecolor=PALETTE["core_hatch"],
                     hatch="...", linewidth=0.8)
    ax.add_patch(core)
    # Cables (un círculo por vuelta, vista superior e inferior)
    for layer in range(N_layers):
        # alterna ligeramente para mostrar empaquetamiento (offset cada otra capa)
        x_off = (layer % 2) * d_wire * 0.05
        for turn in range(N_per_layer):
            x = turn * d_wire + d_wire / 2.0 + x_off
            y_top = r_in + layer * d_wire + d_wire / 2.0
            y_bot = -(r_in + layer * d_wire + d_wire / 2.0)
            # Top
            c1 = Circle((x, y_top), d_wire / 2.0 * 0.92,
                        facecolor=PALETTE["copper"], edgecolor=PALETTE["copper_dark"],
                        linewidth=0.6)
            # highlight pequeño
            h1 = Circle((x - d_wire * 0.15, y_top + d_wire * 0.15),
                        d_wire * 0.15, facecolor=PALETTE["copper_light"],
                        edgecolor="none", alpha=0.75)
            ax.add_patch(c1)
            ax.add_patch(h1)
            c2 = Circle((x, y_bot), d_wire / 2.0 * 0.92,
                        facecolor=PALETTE["copper"], edgecolor=PALETTE["copper_dark"],
                        linewidth=0.6)
            h2 = Circle((x - d_wire * 0.15, y_bot + d_wire * 0.15),
                        d_wire * 0.15, facecolor=PALETTE["copper_light"],
                        edgecolor="none", alpha=0.75)
            ax.add_patch(c2)
            ax.add_patch(h2)
    # Cotas
    arrow_axial = dict(arrowstyle="<->", color="#1d4ed8", lw=1.2)
    ax.annotate("", xy=(H, -d_out / 2 * 1.18), xytext=(0, -d_out / 2 * 1.18),
                arrowprops=arrow_axial)
    ax.text(H / 2, -d_out / 2 * 1.28, f"height = {fmt_dim(H)}",
            ha="center", color="#1d4ed8", fontsize=9, fontweight="600",
            bbox=dict(boxstyle="round,pad=0.25", facecolor="white",
                      edgecolor="#1d4ed8", alpha=0.9))
    ax.annotate("", xy=(H * 1.12, d_out / 2), xytext=(H * 1.12, -d_out / 2),
                arrowprops=dict(arrowstyle="<->", color="#15803d", lw=1.2))
    ax.text(H * 1.18, 0, f"d_out\n{fmt_dim(d_out)}",
            ha="left", va="center", color="#15803d", fontsize=9, fontweight="600",
            bbox=dict(boxstyle="round,pad=0.25", facecolor="white",
                      edgecolor="#15803d", alpha=0.9))
    ax.annotate("", xy=(-H * 0.06, r_in), xytext=(-H * 0.06, -r_in),
                arrowprops=dict(arrowstyle="<->", color="#7c3aed", lw=1.2))
    ax.text(-H * 0.12, -r_in - d_wire * 2,
            f"d_in\n{fmt_dim(d_in)}",
            ha="right", color="#7c3aed", fontsize=9, fontweight="600",
            bbox=dict(boxstyle="round,pad=0.25", facecolor="white",
                      edgecolor="#7c3aed", alpha=0.9))
    # Labels capa/vuelta
    ax.text(H + d_wire * 2, r_in + (N_layers / 2.0) * d_wire,
            f"{N_layers} layers", color=PALETTE["accent"], fontsize=9, fontweight="700",
            bbox=dict(boxstyle="round,pad=0.25", facecolor="white",
                      edgecolor=PALETTE["accent"], alpha=0.95))
    ax.text(H / 2, d_out / 2 * 1.15,
            f"{N_per_layer} turns/layer (N = {N_per_layer * N_layers})",
            ha="center", color=PALETTE["accent"], fontsize=9, fontweight="700",
            bbox=dict(boxstyle="round,pad=0.25", facecolor="white",
                      edgecolor=PALETTE["accent"], alpha=0.95))

    ax.set_xlim(-H * 0.35, H * 1.45)
    ax.set_ylim(-d_out * 0.85, d_out * 0.85)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)


def draw_pancake(ax, *, d_in, d_wire, N_per_layer, N_layers):
    """Vista superior de pancake multicapa. Capas con leve offset y diferentes tonos."""
    ax.clear()
    ax.set_aspect("equal")
    ax.set_facecolor(PALETTE["bg_axes"])
    r_in = d_in / 2.0
    d_out = d_in + 2 * N_per_layer * d_wire
    layer_colors = [PALETTE["copper_dark"], PALETTE["copper"], PALETTE["copper_light"]]
    # iterar de afuera hacia adentro (de capa más al fondo a la superior)
    for layer in range(N_layers):
        color = layer_colors[layer % len(layer_colors)]
        theta = np.linspace(0, 2 * np.pi * N_per_layer, max(400, int(180 * N_per_layer)))
        r = r_in + d_wire / 2.0 + (d_wire / (2 * np.pi)) * theta
        x_off = layer * d_wire * 0.25
        y_off = -layer * d_wire * 0.25
        alpha = 1.0 - 0.15 * layer
        ax.plot(r * np.cos(theta) + x_off, r * np.sin(theta) + y_off,
                color=color, linewidth=2.2, alpha=max(0.4, alpha),
                solid_capstyle="round", label=f"Layer {layer+1}")
    # Núcleo interior
    inner = Circle((0, 0), r_in, facecolor="#fefefe",
                   edgecolor=PALETTE["core_hatch"], linewidth=0.8,
                   hatch="..."); ax.add_patch(inner)

    # Cotas
    ax.annotate("", xy=(d_in / 2, 0), xytext=(-d_in / 2, 0),
                arrowprops=dict(arrowstyle="<->", color="#7c3aed", lw=1.2))
    ax.text(0, d_in * 0.10 + d_wire * 0.5, f"d_in = {fmt_dim(d_in)}",
            ha="center", color="#7c3aed", fontsize=9, fontweight="600",
            bbox=dict(boxstyle="round,pad=0.25", facecolor="white",
                      edgecolor="#7c3aed", alpha=0.9))
    y_top = d_out / 2 * 1.10
    ax.annotate("", xy=(d_out / 2, y_top), xytext=(-d_out / 2, y_top),
                arrowprops=dict(arrowstyle="<->", color="#15803d", lw=1.2))
    ax.text(0, y_top + d_out * 0.04, f"d_out = {fmt_dim(d_out)}",
            ha="center", color="#15803d", fontsize=9, fontweight="600",
            bbox=dict(boxstyle="round,pad=0.25", facecolor="white",
                      edgecolor="#15803d", alpha=0.9))
    # info
    ax.text(d_out / 2 * 1.15, -d_out / 2 * 0.85,
            f"thickness\n{fmt_dim(N_layers * d_wire)}",
            color="#1d4ed8", fontsize=9, fontweight="600",
            bbox=dict(boxstyle="round,pad=0.25", facecolor="white",
                      edgecolor="#1d4ed8", alpha=0.9))
    ax.text(-d_out / 2 * 1.15, d_out / 2 * 0.85,
            f"{N_layers} layers × {N_per_layer} t/L\nN = {N_layers * N_per_layer}",
            color=PALETTE["accent"], fontsize=9, fontweight="700",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                      edgecolor=PALETTE["accent"], alpha=0.95))

    lim = d_out * 0.75
    ax.set_xlim(-lim, lim * 1.35)
    ax.set_ylim(-lim, lim * 1.2)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
