"""
awg_coil_calculator.py
Calculator for large copper coils made with AWG wire (multilayer).
PyQt5 GUI — modern Claude-style theme, English UI with Spanish toggle.

Run:  python awg_coil_calculator.py
"""

import sys
import numpy as np

from PyQt5 import QtCore, QtGui, QtWidgets
import mplcursors

import coil_core as cc
import coil_ui as ui
from coil_ui import tr, LM, PALETTE


RANGE_VAR_KEYS = ["AWG", "Inner diameter", "Turns per layer", "Number of layers", "Frequency"]


class AwgCoilWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self._title_key = "AWG Coil Calculator — Multi-layer Copper Coils"
        self._about_body_key = ("Calculator for large copper coils made with AWG wire.\n"
                                "Supports cylindrical multi-layer solenoids and pancake stacks.")
        self.setWindowTitle(tr(self._title_key))
        self.resize(1550, 920)
        self._last_range = None
        self._build_ui()
        self._build_menu()
        LM.languageChanged.connect(self._retranslate)
        self.compute()

    # ---------- Menu ----------
    def _build_menu(self):
        mb = self.menuBar()
        self.m_file = mb.addMenu(tr("File"))
        self.a_export = QtWidgets.QAction(tr("Export…"), self)
        self.a_export.setShortcut("Ctrl+E")
        self.a_export.triggered.connect(self.show_export)
        self.m_file.addAction(self.a_export)
        self.m_file.addSeparator()
        self.a_quit = QtWidgets.QAction(tr("Exit"), self)
        self.a_quit.triggered.connect(self.close)
        self.m_file.addAction(self.a_quit)

        self.m_bib = mb.addMenu(tr("Bibliography"))
        self.a_bib = QtWidgets.QAction(tr("View references"), self)
        self.a_bib.triggered.connect(self.show_bibliography)
        self.m_bib.addAction(self.a_bib)

        self.m_help = mb.addMenu(tr("Help"))
        self.a_about = QtWidgets.QAction(tr("About"), self)
        self.a_about.triggered.connect(self.show_about)
        self.m_help.addAction(self.a_about)

    def show_bibliography(self):
        ui.BibliographyDialog(self).exec_()

    def show_about(self):
        ui.AboutDialog(self, "AWG Coil Calculator", self._about_body_key).exec_()

    def show_export(self):
        has_range = self.chk_range.isChecked() and self._last_range is not None
        dlg = ui.ExportDialog(
            self,
            has_range_data=has_range,
            range_data=self._last_range if has_range else None,
            plot_fig=self.plot_canvas.fig,
            plot_axes=self.plot_canvas.axes,
            draw_fig=self.draw_canvas.fig,
        )
        dlg.exec_()

    # ---------- UI ----------
    def _build_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root = QtWidgets.QHBoxLayout(central)
        root.setSpacing(10)
        root.setContentsMargins(10, 10, 10, 10)

        # LEFT
        left = QtWidgets.QFrame()
        left.setProperty("panel", True)
        left.setMaximumWidth(420)
        ll = QtWidgets.QVBoxLayout(left)
        ll.setContentsMargins(12, 12, 12, 12)
        ll.setSpacing(8)
        hdr = QtWidgets.QLabel("AWG Coil Calculator")
        hdr.setProperty("header", True)
        ll.addWidget(hdr)

        # Geometry type
        self.gb_geomtype = QtWidgets.QGroupBox(tr("Geometry type"))
        gtl = QtWidgets.QVBoxLayout(self.gb_geomtype)
        self.rb_cyl = QtWidgets.QRadioButton(tr("Cylindrical multi-layer solenoid"))
        self.rb_pan = QtWidgets.QRadioButton(tr("Multi-layer pancake (planar)"))
        self.rb_cyl.setChecked(True)
        gtl.addWidget(self.rb_cyl)
        gtl.addWidget(self.rb_pan)
        ll.addWidget(self.gb_geomtype)

        # Material
        self.gb_mat = QtWidgets.QGroupBox(tr("Conductor material"))
        ml = QtWidgets.QGridLayout(self.gb_mat)
        self.lbl_preset = QtWidgets.QLabel(tr("Preset:"))
        ml.addWidget(self.lbl_preset, 0, 0)
        self.cmb_material = QtWidgets.QComboBox()
        self.cmb_material.addItems(list(cc.MATERIALS.keys()) + [tr("Custom")])
        self.cmb_material.currentTextChanged.connect(self._on_material)
        ml.addWidget(self.cmb_material, 0, 1)
        ml.addWidget(QtWidgets.QLabel("ρ (Ω·m):"), 1, 0)
        self.spin_rho = QtWidgets.QDoubleSpinBox()
        self.spin_rho.setRange(1e-12, 1e6)
        self.spin_rho.setDecimals(12)
        self.spin_rho.setValue(cc.MATERIALS["Cobre"])
        ml.addWidget(self.spin_rho, 1, 1)
        ll.addWidget(self.gb_mat)

        # Winding params
        self.gb_wind = QtWidgets.QGroupBox(tr("Winding parameters"))
        wl = QtWidgets.QVBoxLayout(self.gb_wind)
        # AWG
        awg_row = QtWidgets.QHBoxLayout()
        self.lbl_awg = QtWidgets.QLabel(tr("AWG:"))
        self.lbl_awg.setMinimumWidth(130)
        self.spin_awg = QtWidgets.QSpinBox()
        self.spin_awg.setRange(0, 40)
        self.spin_awg.setValue(24)
        self.spin_awg.valueChanged.connect(self._update_awg_label)
        awg_row.addWidget(self.lbl_awg)
        awg_row.addWidget(self.spin_awg)
        self.lbl_awg_d = QtWidgets.QLabel("Ø = — mm")
        self.lbl_awg_d.setStyleSheet("color:#cc785c; font-weight: 600;")
        awg_row.addWidget(self.lbl_awg_d)
        awg_row.addStretch()
        awg_wrap = QtWidgets.QWidget(); awg_wrap.setLayout(awg_row)
        wl.addWidget(awg_wrap)

        self.in_din = ui.DimensionInput("Inner Ø:", 10.0, "mm")
        wl.addWidget(self.in_din)

        # Turns/layer
        n_row = QtWidgets.QHBoxLayout()
        self.lbl_npl = QtWidgets.QLabel(tr("Turns/layer:"))
        self.lbl_npl.setMinimumWidth(130)
        self.spin_npl = QtWidgets.QSpinBox()
        self.spin_npl.setRange(1, 10000)
        self.spin_npl.setValue(20)
        self.spin_npl.setMaximumWidth(110)
        n_row.addWidget(self.lbl_npl); n_row.addWidget(self.spin_npl); n_row.addStretch()
        wrap = QtWidgets.QWidget(); wrap.setLayout(n_row); wl.addWidget(wrap)
        # Layers
        l_row = QtWidgets.QHBoxLayout()
        self.lbl_nl = QtWidgets.QLabel(tr("# Layers:"))
        self.lbl_nl.setMinimumWidth(130)
        self.spin_nl = QtWidgets.QSpinBox()
        self.spin_nl.setRange(1, 1000)
        self.spin_nl.setValue(3)
        self.spin_nl.setMaximumWidth(110)
        l_row.addWidget(self.lbl_nl); l_row.addWidget(self.spin_nl); l_row.addStretch()
        wrap2 = QtWidgets.QWidget(); wrap2.setLayout(l_row); wl.addWidget(wrap2)

        self.in_freq = ui.FreqInput("Eval. frequency:", 100.0, "kHz")
        wl.addWidget(self.in_freq)
        ll.addWidget(self.gb_wind)

        # Range
        self.gb_range = QtWidgets.QGroupBox(tr("Range mode (plot)"))
        rl = QtWidgets.QGridLayout(self.gb_range)
        self.chk_range = QtWidgets.QCheckBox(tr("Enable range"))
        rl.addWidget(self.chk_range, 0, 0, 1, 2)
        self.lbl_var = QtWidgets.QLabel(tr("Variable:"))
        rl.addWidget(self.lbl_var, 1, 0)
        self.cmb_range_var = QtWidgets.QComboBox()
        self.cmb_range_var.addItems([tr(k) for k in RANGE_VAR_KEYS])
        self.cmb_range_var.currentIndexChanged.connect(self._on_range_var_change)
        rl.addWidget(self.cmb_range_var, 1, 1)
        self.lbl_min = QtWidgets.QLabel(tr("Min:"))
        rl.addWidget(self.lbl_min, 2, 0)
        self.spin_range_min = QtWidgets.QDoubleSpinBox()
        self.spin_range_min.setRange(0.0, 1e9); self.spin_range_min.setDecimals(4)
        self.spin_range_min.setValue(10.0)
        rl.addWidget(self.spin_range_min, 2, 1)
        self.lbl_max = QtWidgets.QLabel(tr("Max:"))
        rl.addWidget(self.lbl_max, 3, 0)
        self.spin_range_max = QtWidgets.QDoubleSpinBox()
        self.spin_range_max.setRange(0.0, 1e9); self.spin_range_max.setDecimals(4)
        self.spin_range_max.setValue(40.0)
        rl.addWidget(self.spin_range_max, 3, 1)
        self.lbl_steps = QtWidgets.QLabel(tr("Steps:"))
        rl.addWidget(self.lbl_steps, 4, 0)
        self.spin_range_steps = QtWidgets.QSpinBox()
        self.spin_range_steps.setRange(2, 1000); self.spin_range_steps.setValue(40)
        rl.addWidget(self.spin_range_steps, 4, 1)
        self.lbl_unit = QtWidgets.QLabel(tr("Unit:"))
        rl.addWidget(self.lbl_unit, 5, 0)
        self.cmb_range_unit = QtWidgets.QComboBox()
        self.cmb_range_unit.addItems(cc.UNIT_ORDER)
        self.cmb_range_unit.setCurrentText("mm")
        rl.addWidget(self.cmb_range_unit, 5, 1)
        ll.addWidget(self.gb_range)

        self.btn_calc = QtWidgets.QPushButton(tr("Calculate / Redraw"))
        self.btn_calc.clicked.connect(self.compute)
        ll.addWidget(self.btn_calc)
        ll.addStretch()

        root.addWidget(left)

        # CENTER
        center = QtWidgets.QFrame()
        center.setProperty("panel", True)
        cl = QtWidgets.QVBoxLayout(center)
        cl.setContentsMargins(12, 12, 12, 12); cl.setSpacing(8)
        self.lbl_draw_cap = QtWidgets.QLabel(tr("Coil drawing"))
        self.lbl_draw_cap.setProperty("caption", True)
        cl.addWidget(self.lbl_draw_cap)
        self.draw_canvas = ui.MplCanvas(self, width=6, height=5, n_axes=1)
        cl.addWidget(self.draw_canvas, stretch=1)
        self.lbl_plots_cap = QtWidgets.QLabel(tr("Plots (range mode)"))
        self.lbl_plots_cap.setProperty("caption", True)
        cl.addWidget(self.lbl_plots_cap)
        self.plot_canvas = ui.MplCanvas(self, width=6, height=6, n_axes=3)
        cl.addWidget(self.plot_canvas, stretch=2)
        root.addWidget(center, stretch=2)

        # RIGHT
        right = QtWidgets.QFrame()
        right.setProperty("panel", True)
        right.setMaximumWidth(360)
        rl2 = QtWidgets.QVBoxLayout(right)
        rl2.setContentsMargins(12, 12, 12, 12); rl2.setSpacing(8)
        self.lbl_results_hdr = QtWidgets.QLabel(tr("Results"))
        self.lbl_results_hdr.setProperty("header", True)
        rl2.addWidget(self.lbl_results_hdr)
        self.lbl_dwire = QtWidgets.QLabel("Ø wire = —")
        self.lbl_L = QtWidgets.QLabel("L = —")
        self.lbl_Rdc = QtWidgets.QLabel("R_dc = —")
        self.lbl_Rac = QtWidgets.QLabel("R_ac = —")
        self.lbl_Q = QtWidgets.QLabel("Q = —")
        self.lbl_fskin = QtWidgets.QLabel("f_skin = —")
        self.lbl_length = QtWidgets.QLabel("ℓ = —")
        self.lbl_height = QtWidgets.QLabel("h = —")
        self.lbl_dout = QtWidgets.QLabel("d_out = —")
        self.lbl_ntotal = QtWidgets.QLabel("N_total = —")
        for lbl in [self.lbl_dwire, self.lbl_L, self.lbl_Rdc, self.lbl_Rac,
                    self.lbl_Q, self.lbl_fskin, self.lbl_length,
                    self.lbl_height, self.lbl_dout, self.lbl_ntotal]:
            lbl.setProperty("result", True)
            lbl.setWordWrap(True)
            rl2.addWidget(lbl)
        rl2.addStretch()
        self._bib_btn = QtWidgets.QPushButton(tr("View Bibliography"))
        self._bib_btn.setProperty("secondary", True)
        self._bib_btn.clicked.connect(self.show_bibliography)
        rl2.addWidget(self._bib_btn)
        self._exp_btn = QtWidgets.QPushButton(tr("Export…"))
        self._exp_btn.clicked.connect(self.show_export)
        rl2.addWidget(self._exp_btn)
        root.addWidget(right)

        self._update_awg_label()

    def _update_awg_label(self):
        d = cc.awg_to_diameter(self.spin_awg.value())
        self.lbl_awg_d.setText(f"Ø = {d*1e3:.4f} mm")

    def _on_material(self, name):
        if name in cc.MATERIALS:
            self.spin_rho.setValue(cc.MATERIALS[name])

    def _on_range_var_change(self):
        key = RANGE_VAR_KEYS[self.cmb_range_var.currentIndex()]
        if key == "Frequency":
            self.cmb_range_unit.clear()
            self.cmb_range_unit.addItems(cc.FREQ_ORDER)
            self.cmb_range_unit.setCurrentText("kHz")
            self.spin_range_min.setValue(1.0)
            self.spin_range_max.setValue(1000.0)
        elif key == "AWG":
            self.cmb_range_unit.clear()
            self.cmb_range_unit.addItems(["—"])
            self.spin_range_min.setValue(10.0)
            self.spin_range_max.setValue(40.0)
        elif key in ("Turns per layer", "Number of layers"):
            self.cmb_range_unit.clear()
            self.cmb_range_unit.addItems(["—"])
            self.spin_range_min.setValue(1.0)
            self.spin_range_max.setValue(50.0)
        else:  # Inner diameter
            self.cmb_range_unit.clear()
            self.cmb_range_unit.addItems(cc.UNIT_ORDER)
            self.cmb_range_unit.setCurrentText("mm")
            self.spin_range_min.setValue(1.0)
            self.spin_range_max.setValue(50.0)

    # ---------- Logic ----------
    def collect_params(self):
        return {
            "geom": "cilindrico" if self.rb_cyl.isChecked() else "pancake",
            "rho": self.spin_rho.value(),
            "awg": self.spin_awg.value(),
            "d_in": self.in_din.value_in_meters(),
            "n_per": self.spin_npl.value(),
            "n_lay": self.spin_nl.value(),
            "freq": self.in_freq.value_in_hz(),
        }

    def compute_single(self, p):
        d_wire = cc.awg_to_diameter(p["awg"])
        N_total = p["n_per"] * p["n_lay"]
        if p["geom"] == "cilindrico":
            altura = p["n_per"] * d_wire
            d_ext = p["d_in"] + 2.0 * p["n_lay"] * d_wire
            a = (p["d_in"] + d_ext) / 4.0
            h = altura
            b = p["n_lay"] * d_wire
            L = cc.wheeler_multilayer(a, h, b, N_total)
            length = 0.0
            for k in range(p["n_lay"]):
                r_k = p["d_in"] / 2.0 + d_wire / 2.0 + k * d_wire
                length += 2.0 * np.pi * r_k * p["n_per"]
        else:
            d_ext = p["d_in"] + 2.0 * p["n_per"] * d_wire
            altura = p["n_lay"] * d_wire
            L = cc.pancake_multilayer(p["d_in"], d_wire, p["n_per"], p["n_lay"])
            length_layer = cc.spiral_length_circular(p["d_in"], d_ext, p["n_per"])
            length = length_layer * p["n_lay"]
        R_dc = cc.dc_resistance(p["rho"], length, np.pi * (d_wire / 2.0) ** 2)
        R_ac = cc.ac_resistance_round(p["rho"], length, d_wire, p["freq"])
        Q = cc.quality_factor(L, R_ac, p["freq"])
        f_sk = cc.f_skin_threshold(p["rho"], d_wire / 2.0)
        return {
            "d_wire": d_wire, "L": L, "R_dc": R_dc, "R_ac": R_ac,
            "Q": Q, "f_skin": f_sk,
            "length": length, "altura": altura, "d_ext": d_ext, "N_total": N_total,
        }

    def compute(self):
        p = self.collect_params()
        res = self.compute_single(p)
        self.update_results(res, p)
        self.update_drawing(p, res)
        if self.chk_range.isChecked():
            self.plot_range(p)
        else:
            self._last_range = None
            self.clear_plots()

    def update_results(self, res, p):
        self.lbl_dwire.setText(f"Ø wire (AWG {p['awg']}) = {res['d_wire']*1e3:.4f} mm")
        self.lbl_L.setText(f"<b>L = {_fmt_L(res['L'])}</b>")
        self.lbl_Rdc.setText(f"R_dc       = {_fmt_R(res['R_dc'])}")
        self.lbl_Rac.setText(f"R_ac@{_fmt_f(p['freq'])} = {_fmt_R(res['R_ac'])}")
        self.lbl_Q.setText(f"<b>Q = {res['Q']:.3g}</b>  @ {_fmt_f(p['freq'])}")
        self.lbl_fskin.setText(f"f_skin (δ=a) = {_fmt_f(res['f_skin'])}")
        self.lbl_length.setText(f"ℓ (wire)  = {_fmt_len(res['length'])}")
        self.lbl_height.setText(f"h (height) = {_fmt_len(res['altura'])}")
        self.lbl_dout.setText(f"d_out     = {_fmt_len(res['d_ext'])}")
        self.lbl_ntotal.setText(f"N_total   = {res['N_total']} turns")

    def update_drawing(self, p, res):
        ax = self.draw_canvas.ax
        d_wire = res["d_wire"]
        if p["geom"] == "cilindrico":
            ui.draw_cylindrical_solenoid(ax, d_in=p["d_in"], d_wire=d_wire,
                                         N_per_layer=p["n_per"], N_layers=p["n_lay"])
            title = tr("Cylindrical multi-layer solenoid")
        else:
            ui.draw_pancake(ax, d_in=p["d_in"], d_wire=d_wire,
                            N_per_layer=p["n_per"], N_layers=p["n_lay"])
            title = tr("Multi-layer pancake (planar)")
        ax.set_title(title, color=PALETTE["text"], fontweight="700", fontsize=12, pad=12)
        self.draw_canvas.draw()

    def clear_plots(self):
        for ax in self.plot_canvas.axes:
            ax.clear()
            ui.style_axes(ax)
            ax.text(0.5, 0.5, tr("Enable range") + " ↑",
                    ha="center", va="center", transform=ax.transAxes,
                    color="#9c9285", fontsize=11, style="italic")
        self.plot_canvas.draw()

    def plot_range(self, p):
        idx = self.cmb_range_var.currentIndex()
        key = RANGE_VAR_KEYS[idx]
        n_steps = self.spin_range_steps.value()
        vmin = self.spin_range_min.value()
        vmax = self.spin_range_max.value()
        unit = self.cmb_range_unit.currentText()

        if key == "AWG":
            xs = np.arange(max(0, int(vmin)), min(40, int(vmax)) + 1)
            xs_si = xs
            xlabel = "AWG"
        elif key == "Inner diameter":
            xs = np.linspace(vmin, vmax, n_steps)
            xs_si = xs * cc.UNITS.get(unit, 1.0)
            xlabel = f"{tr('Inner diameter')} [{unit}]"
        elif key == "Turns per layer":
            xs = np.arange(max(1, int(vmin)), int(vmax) + 1)
            xs_si = xs
            xlabel = tr("Turns per layer")
        elif key == "Number of layers":
            xs = np.arange(max(1, int(vmin)), int(vmax) + 1)
            xs_si = xs
            xlabel = tr("Number of layers")
        else:  # Frequency
            xs = np.linspace(vmin, vmax, n_steps)
            xs_si = xs * cc.FREQ_UNITS.get(unit, 1.0)
            xlabel = f"{tr('Frequency')} [{unit}]"

        Ls, Rs, Qs = [], [], []
        for x in xs_si:
            pp = dict(p)
            if key == "AWG":
                pp["awg"] = int(x)
            elif key == "Inner diameter":
                pp["d_in"] = float(x)
            elif key == "Turns per layer":
                pp["n_per"] = int(x)
            elif key == "Number of layers":
                pp["n_lay"] = int(x)
            else:
                pp["freq"] = float(x)
            try:
                r = self.compute_single(pp)
                Ls.append(r["L"]); Rs.append(r["R_ac"]); Qs.append(r["Q"])
            except Exception:
                Ls.append(np.nan); Rs.append(np.nan); Qs.append(np.nan)
        Ls = np.array(Ls); Rs = np.array(Rs); Qs = np.array(Qs)

        def auto_L(arr):
            m = np.nanmedian(np.abs(arr))
            if m >= 1: return arr, "L [H]", "H"
            if m >= 1e-3: return arr * 1e3, "L [mH]", "mH"
            if m >= 1e-6: return arr * 1e6, "L [μH]", "μH"
            return arr * 1e9, "L [nH]", "nH"

        L_p, L_lbl, L_unit = auto_L(Ls)
        ax1, ax2, ax3 = self.plot_canvas.axes
        for a in (ax1, ax2, ax3):
            a.clear()

        line1, = ax1.plot(xs, L_p, "-o", color=PALETTE["line_L"],
                          markersize=3.5, linewidth=1.8)
        ui.style_axes(ax1, title=tr("Inductance"), xlabel=xlabel, ylabel=L_lbl)
        line2, = ax2.plot(xs, Rs, "-o", color=PALETTE["line_R"],
                          markersize=3.5, linewidth=1.8)
        ui.style_axes(ax2, title=tr("AC resistance"), xlabel=xlabel,
                      ylabel=f"R [Ω] @ {_fmt_f(p['freq'])}")
        line3, = ax3.plot(xs, Qs, "-o", color=PALETTE["line_Q"],
                          markersize=3.5, linewidth=1.8)
        ui.style_axes(ax3, title=tr("Quality factor"), xlabel=xlabel, ylabel="Q")

        cursor = mplcursors.cursor([line1, line2, line3], hover=True)

        @cursor.connect("add")
        def _on_add(sel):
            xv, yv = sel.target
            sel.annotation.set_text(f"{xlabel} = {xv:.4g}\nvalue = {yv:.4g}")
            sel.annotation.get_bbox_patch().set(fc="#fffce8", ec=PALETTE["accent"],
                                                lw=1.2, alpha=0.95)

        self.plot_canvas.draw()
        self._last_range = {
            "xs": xs, "xlabel": xlabel,
            "L": Ls, "R": Rs, "Q": Qs, "L_unit": "H",
        }

    # ---------- Retranslate ----------
    def _retranslate(self, lang):
        self.setWindowTitle(tr(self._title_key))
        self.m_file.setTitle(tr("File"))
        self.a_export.setText(tr("Export…"))
        self.a_quit.setText(tr("Exit"))
        self.m_bib.setTitle(tr("Bibliography"))
        self.a_bib.setText(tr("View references"))
        self.m_help.setTitle(tr("Help"))
        self.a_about.setText(tr("About"))
        self.gb_geomtype.setTitle(tr("Geometry type"))
        self.rb_cyl.setText(tr("Cylindrical multi-layer solenoid"))
        self.rb_pan.setText(tr("Multi-layer pancake (planar)"))
        self.gb_mat.setTitle(tr("Conductor material"))
        self.lbl_preset.setText(tr("Preset:"))
        self.gb_wind.setTitle(tr("Winding parameters"))
        self.lbl_awg.setText(tr("AWG:"))
        self.lbl_npl.setText(tr("Turns/layer:"))
        self.lbl_nl.setText(tr("# Layers:"))
        self.gb_range.setTitle(tr("Range mode (plot)"))
        self.chk_range.setText(tr("Enable range"))
        self.lbl_var.setText(tr("Variable:"))
        cur = self.cmb_range_var.currentIndex()
        self.cmb_range_var.blockSignals(True)
        self.cmb_range_var.clear()
        self.cmb_range_var.addItems([tr(k) for k in RANGE_VAR_KEYS])
        self.cmb_range_var.setCurrentIndex(cur)
        self.cmb_range_var.blockSignals(False)
        self.lbl_min.setText(tr("Min:"))
        self.lbl_max.setText(tr("Max:"))
        self.lbl_steps.setText(tr("Steps:"))
        self.lbl_unit.setText(tr("Unit:"))
        self.btn_calc.setText(tr("Calculate / Redraw"))
        self.lbl_results_hdr.setText(tr("Results"))
        self.lbl_draw_cap.setText(tr("Coil drawing"))
        self.lbl_plots_cap.setText(tr("Plots (range mode)"))
        self._bib_btn.setText(tr("View Bibliography"))
        self._exp_btn.setText(tr("Export…"))
        self.compute()


# ---------- formatters ----------
def _fmt_L(v):
    if v >= 1: return f"{v:.4g} H"
    if v >= 1e-3: return f"{v*1e3:.4g} mH"
    if v >= 1e-6: return f"{v*1e6:.4g} μH"
    if v >= 1e-9: return f"{v*1e9:.4g} nH"
    return f"{v*1e12:.4g} pH"


def _fmt_R(v):
    if v >= 1e3: return f"{v*1e-3:.4g} kΩ"
    if v >= 1: return f"{v:.4g} Ω"
    return f"{v*1e3:.4g} mΩ"


def _fmt_f(v):
    if v >= 1e9: return f"{v*1e-9:.4g} GHz"
    if v >= 1e6: return f"{v*1e-6:.4g} MHz"
    if v >= 1e3: return f"{v*1e-3:.4g} kHz"
    return f"{v:.4g} Hz"


def _fmt_len(v):
    if v >= 1: return f"{v:.4g} m"
    if v >= 1e-3: return f"{v*1e3:.4g} mm"
    if v >= 1e-6: return f"{v*1e6:.4g} μm"
    return f"{v*1e9:.4g} nm"


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(cc.STYLESHEET)
    app.setFont(QtGui.QFont("Segoe UI", 10))
    w = AwgCoilWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
