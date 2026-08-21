"""
microcoil_calculator.py
Planar microcoil (microfabricated) calculator — PyQt5 GUI.
Modern Claude-style theme. English UI with Spanish toggle in About.

Run:  python microcoil_calculator.py
"""

import sys
import numpy as np

from PyQt5 import QtCore, QtGui, QtWidgets
import mplcursors

import coil_core as cc
import coil_ui as ui
from coil_ui import tr, LM, PALETTE


RANGE_VAR_KEYS = ["N turns", "Inner diameter", "Width", "Gap", "Thickness", "Frequency"]


class MicrocoilWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self._title_key = "Microcoil Calculator — Planar Microfabricated Coils"
        self._about_body_key = ("Inductance, resistance and quality-factor calculator\n"
                                "for planar microfabricated coils.")
        self.setWindowTitle(tr(self._title_key))
        self.resize(1550, 920)
        self._last_range = None  # dict con xs, xlabel, L, R, Q, L_unit
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
        ui.AboutDialog(self, "Microcoil Calculator", self._about_body_key).exec_()

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

        # =====  LEFT: parameters =====
        left = QtWidgets.QFrame()
        left.setProperty("panel", True)
        left.setMaximumWidth(400)
        left_l = QtWidgets.QVBoxLayout(left)
        left_l.setSpacing(8)
        left_l.setContentsMargins(12, 12, 12, 12)

        hdr = QtWidgets.QLabel("Microcoil Calculator")
        hdr.setProperty("header", True)
        left_l.addWidget(hdr)

        # Topology
        self.gb_topo = QtWidgets.QGroupBox(tr("Topology"))
        topo_l = QtWidgets.QVBoxLayout(self.gb_topo)
        self.rb_series = QtWidgets.QRadioButton(tr("Series (spiral)"))
        self.rb_parallel = QtWidgets.QRadioButton(tr("Parallel (rings)"))
        self.rb_series.setChecked(True)
        self.chk_coupling = QtWidgets.QCheckBox(tr("With mutual coupling (parallel)"))
        self.chk_coupling.setChecked(True)
        topo_l.addWidget(self.rb_series)
        topo_l.addWidget(self.rb_parallel)
        topo_l.addWidget(self.chk_coupling)
        left_l.addWidget(self.gb_topo)

        # Shape
        self.gb_shape = QtWidgets.QGroupBox(tr("Shape"))
        shape_l = QtWidgets.QHBoxLayout(self.gb_shape)
        self.rb_circular = QtWidgets.QRadioButton(tr("Circular"))
        self.rb_square = QtWidgets.QRadioButton(tr("Square"))
        self.rb_circular.setChecked(True)
        shape_l.addWidget(self.rb_circular)
        shape_l.addWidget(self.rb_square)
        left_l.addWidget(self.gb_shape)

        # Formula
        self.gb_formula = QtWidgets.QGroupBox(tr("Inductance formula"))
        fl = QtWidgets.QHBoxLayout(self.gb_formula)
        self.lbl_method = QtWidgets.QLabel(tr("Method:"))
        fl.addWidget(self.lbl_method)
        self.cmb_formula = QtWidgets.QComboBox()
        self.cmb_formula.addItems(["Mohan-Wheeler", "Greenhouse"])
        fl.addWidget(self.cmb_formula, 1)
        left_l.addWidget(self.gb_formula)

        # Material
        self.gb_mat = QtWidgets.QGroupBox(tr("Conductor material"))
        ml = QtWidgets.QGridLayout(self.gb_mat)
        self.lbl_preset = QtWidgets.QLabel(tr("Preset:"))
        ml.addWidget(self.lbl_preset, 0, 0)
        self.cmb_material = QtWidgets.QComboBox()
        self._mat_names = list(cc.MATERIALS.keys())
        self.cmb_material.addItems(self._mat_names + [tr("Custom")])
        self.cmb_material.currentTextChanged.connect(self._on_material)
        ml.addWidget(self.cmb_material, 0, 1)
        ml.addWidget(QtWidgets.QLabel("ρ (Ω·m):"), 1, 0)
        self.spin_rho = QtWidgets.QDoubleSpinBox()
        self.spin_rho.setRange(1e-12, 1e6)
        self.spin_rho.setDecimals(12)
        self.spin_rho.setValue(cc.MATERIALS["Cobre"])
        ml.addWidget(self.spin_rho, 1, 1)
        left_l.addWidget(self.gb_mat)

        # Geometry
        self.gb_geom = QtWidgets.QGroupBox(tr("Geometry"))
        gl = QtWidgets.QVBoxLayout(self.gb_geom)
        n_row = QtWidgets.QHBoxLayout()
        self.lbl_N = QtWidgets.QLabel(tr("Number of turns:"))
        self.lbl_N.setMinimumWidth(130)
        self.spin_N = QtWidgets.QDoubleSpinBox()
        self.spin_N.setRange(1.0, 1000.0)
        self.spin_N.setDecimals(1)
        self.spin_N.setValue(10.0)
        self.spin_N.setMaximumWidth(110)
        n_row.addWidget(self.lbl_N)
        n_row.addWidget(self.spin_N)
        n_row.addStretch()
        n_wrap = QtWidgets.QWidget(); n_wrap.setLayout(n_row)
        gl.addWidget(n_wrap)

        self.in_din = ui.DimensionInput("Inner Ø:", 200.0, "um")
        self.in_w = ui.DimensionInput("Width w:", 10.0, "um")
        self.in_gap = ui.DimensionInput("Gap:", 5.0, "um")
        self.in_t = ui.DimensionInput("Thickness t:", 1.0, "um")
        self.in_freq = ui.FreqInput("Eval. frequency:", 1.0, "MHz")
        for w in [self.in_din, self.in_w, self.in_gap, self.in_t, self.in_freq]:
            gl.addWidget(w)
        left_l.addWidget(self.gb_geom)

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
        self.spin_range_min.setRange(0.0, 1e9)
        self.spin_range_min.setDecimals(4)
        self.spin_range_min.setValue(1.0)
        rl.addWidget(self.spin_range_min, 2, 1)
        self.lbl_max = QtWidgets.QLabel(tr("Max:"))
        rl.addWidget(self.lbl_max, 3, 0)
        self.spin_range_max = QtWidgets.QDoubleSpinBox()
        self.spin_range_max.setRange(0.0, 1e9)
        self.spin_range_max.setDecimals(4)
        self.spin_range_max.setValue(20.0)
        rl.addWidget(self.spin_range_max, 3, 1)
        self.lbl_steps = QtWidgets.QLabel(tr("Steps:"))
        rl.addWidget(self.lbl_steps, 4, 0)
        self.spin_range_steps = QtWidgets.QSpinBox()
        self.spin_range_steps.setRange(2, 1000)
        self.spin_range_steps.setValue(50)
        rl.addWidget(self.spin_range_steps, 4, 1)
        self.lbl_unit = QtWidgets.QLabel(tr("Unit:"))
        rl.addWidget(self.lbl_unit, 5, 0)
        self.cmb_range_unit = QtWidgets.QComboBox()
        self.cmb_range_unit.addItems(cc.UNIT_ORDER)
        self.cmb_range_unit.setCurrentText("um")
        rl.addWidget(self.cmb_range_unit, 5, 1)
        left_l.addWidget(self.gb_range)

        self.btn_calc = QtWidgets.QPushButton(tr("Calculate / Redraw"))
        self.btn_calc.clicked.connect(self.compute)
        left_l.addWidget(self.btn_calc)
        left_l.addStretch()

        root.addWidget(left)

        # =====  CENTER: drawing + plots =====
        center = QtWidgets.QFrame()
        center.setProperty("panel", True)
        cl = QtWidgets.QVBoxLayout(center)
        cl.setContentsMargins(12, 12, 12, 12)
        cl.setSpacing(8)
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

        # =====  RIGHT: results =====
        right = QtWidgets.QFrame()
        right.setProperty("panel", True)
        right.setMaximumWidth(340)
        rrl = QtWidgets.QVBoxLayout(right)
        rrl.setContentsMargins(12, 12, 12, 12)
        rrl.setSpacing(8)
        self.lbl_results_hdr = QtWidgets.QLabel(tr("Results"))
        self.lbl_results_hdr.setProperty("header", True)
        rrl.addWidget(self.lbl_results_hdr)
        self.lbl_L = QtWidgets.QLabel("L = —")
        self.lbl_L_alt = QtWidgets.QLabel("")
        self.lbl_Rdc = QtWidgets.QLabel("R_dc = —")
        self.lbl_Rac = QtWidgets.QLabel("R_ac = —")
        self.lbl_Q = QtWidgets.QLabel("Q = —")
        self.lbl_fskin = QtWidgets.QLabel("f_skin = —")
        self.lbl_length = QtWidgets.QLabel("ℓ = —")
        self.lbl_dout = QtWidgets.QLabel("d_out = —")
        for lbl in [self.lbl_L, self.lbl_L_alt, self.lbl_Rdc, self.lbl_Rac,
                    self.lbl_Q, self.lbl_fskin, self.lbl_length, self.lbl_dout]:
            lbl.setProperty("result", True)
            lbl.setWordWrap(True)
            rrl.addWidget(lbl)
        rrl.addStretch()
        bib_btn = QtWidgets.QPushButton(tr("View Bibliography"))
        bib_btn.setProperty("secondary", True)
        bib_btn.clicked.connect(self.show_bibliography)
        rrl.addWidget(bib_btn)
        exp_btn = QtWidgets.QPushButton(tr("Export…"))
        exp_btn.clicked.connect(self.show_export)
        rrl.addWidget(exp_btn)
        self._bib_btn = bib_btn
        self._exp_btn = exp_btn
        root.addWidget(right)

    def _on_material(self, name):
        if name in cc.MATERIALS:
            self.spin_rho.setValue(cc.MATERIALS[name])

    def _on_range_var_change(self):
        # cuando Frecuencia se selecciona, cambiar el dropdown de unidad
        key = RANGE_VAR_KEYS[self.cmb_range_var.currentIndex()]
        if key == "Frequency":
            self.cmb_range_unit.clear()
            self.cmb_range_unit.addItems(cc.FREQ_ORDER)
            self.cmb_range_unit.setCurrentText("MHz")
            self.spin_range_min.setValue(0.01)
            self.spin_range_max.setValue(100.0)
        elif key == "N turns":
            self.cmb_range_unit.clear()
            self.cmb_range_unit.addItems(["—"])
            self.spin_range_min.setValue(1.0)
            self.spin_range_max.setValue(20.0)
        else:
            self.cmb_range_unit.clear()
            self.cmb_range_unit.addItems(cc.UNIT_ORDER)
            self.cmb_range_unit.setCurrentText("um")
            self.spin_range_min.setValue(1.0)
            self.spin_range_max.setValue(100.0)

    # ---------- Computation ----------
    def collect_params(self):
        return {
            "topology": "serie" if self.rb_series.isChecked() else "paralelo",
            "coupling": self.chk_coupling.isChecked(),
            "shape": "cuadrada" if self.rb_square.isChecked() else "circular",
            "formula": self.cmb_formula.currentText(),
            "rho": self.spin_rho.value(),
            "N": self.spin_N.value(),
            "d_in": self.in_din.value_in_meters(),
            "w": self.in_w.value_in_meters(),
            "gap": self.in_gap.value_in_meters(),
            "t": self.in_t.value_in_meters(),
            "freq": self.in_freq.value_in_hz(),
        }

    def compute_single(self, p):
        if p["topology"] == "serie":
            L = cc.inductance_microcoil(p["d_in"], p["w"], p["gap"], p["N"], p["t"],
                                        p["shape"], p["formula"])
            if p["shape"] == "cuadrada":
                length = cc.spiral_length_square(p["d_in"], p["w"], p["gap"], p["N"])
            else:
                d_out = cc.outer_diameter(p["d_in"], p["w"], p["gap"], p["N"])
                length = cc.spiral_length_circular(p["d_in"], d_out, p["N"])
            R_dc = cc.dc_resistance(p["rho"], length, p["w"] * p["t"])
            R_ac = cc.ac_resistance_rectangular(p["rho"], length, p["w"], p["t"], p["freq"])
            out_L_no = None
        else:
            res = cc.parallel_rings_inductance(p["d_in"], p["w"], p["gap"], p["N"],
                                               p["t"], coupling=p["coupling"])
            L = res["L_total"]
            radii = res.get("radii", [])
            R_each = []
            R_ac_each = []
            for r in radii:
                length_k = 2.0 * np.pi * r
                R_each.append(cc.dc_resistance(p["rho"], length_k, p["w"] * p["t"]))
                R_ac_each.append(cc.ac_resistance_rectangular(p["rho"], length_k,
                                                              p["w"], p["t"], p["freq"]))
            R_dc = 1.0 / sum(1.0 / R for R in R_each if R > 0) if R_each else 0.0
            R_ac = 1.0 / sum(1.0 / R for R in R_ac_each if R > 0) if R_ac_each else 0.0
            length = sum(2.0 * np.pi * r for r in radii)
            res_no = cc.parallel_rings_inductance(p["d_in"], p["w"], p["gap"], p["N"],
                                                  p["t"], coupling=False)
            out_L_no = res_no["L_total"]
        Q = cc.quality_factor(L, R_ac, p["freq"])
        f_sk = cc.f_skin_threshold(p["rho"], p["t"])
        out = {
            "L": L, "R_dc": R_dc, "R_ac": R_ac, "Q": Q, "f_skin": f_sk,
            "length": length,
            "d_out": cc.outer_diameter(p["d_in"], p["w"], p["gap"], p["N"]),
        }
        if out_L_no is not None:
            out["L_no_coupling"] = out_L_no
        return out

    def compute(self):
        p = self.collect_params()
        res = self.compute_single(p)
        self.update_results(res, p)
        self.update_drawing(p)
        if self.chk_range.isChecked():
            self.plot_range(p)
        else:
            self._last_range = None
            self.clear_plots()

    # ---------- Display ----------
    def update_results(self, res, p):
        self.lbl_L.setText(f"<b>L = {_fmt_L(res['L'])}</b>")
        if "L_no_coupling" in res and res["L_no_coupling"] > 0:
            delta_pct = (res['L'] - res['L_no_coupling']) / res['L_no_coupling'] * 100
            self.lbl_L_alt.setText(
                f"L ({tr('no coupling') if False else 'no coupling'}) = {_fmt_L(res['L_no_coupling'])}\n"
                f"Δ coupling: {delta_pct:+.1f}%"
            )
        else:
            self.lbl_L_alt.setText("")
        self.lbl_Rdc.setText(f"R_dc       = {_fmt_R(res['R_dc'])}")
        self.lbl_Rac.setText(f"R_ac@{_fmt_f(p['freq'])} = {_fmt_R(res['R_ac'])}")
        self.lbl_Q.setText(f"<b>Q = {res['Q']:.3g}</b>  @ {_fmt_f(p['freq'])}")
        self.lbl_fskin.setText(f"f_skin (δ=t) = {_fmt_f(res['f_skin'])}")
        self.lbl_length.setText(f"ℓ (wire)   = {_fmt_len(res['length'])}")
        self.lbl_dout.setText(f"d_out      = {_fmt_len(res['d_out'])}")

    def update_drawing(self, p):
        ax = self.draw_canvas.ax
        ui.draw_microcoil(ax, d_in=p["d_in"], w=p["w"], gap=p["gap"],
                          N=p["N"], shape=p["shape"], topology=p["topology"])
        # Título
        topology_lbl = tr("Series (spiral)") if p["topology"] == "serie" else tr("Parallel (rings)")
        shape_lbl = tr("Circular") if p["shape"] == "circular" else tr("Square")
        ax.set_title(f"{shape_lbl} — {topology_lbl}", color=PALETTE["text"],
                     fontweight="700", fontsize=12, pad=12)
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
        var_key = RANGE_VAR_KEYS[idx]
        n_steps = self.spin_range_steps.value()
        vmin = self.spin_range_min.value()
        vmax = self.spin_range_max.value()
        unit = self.cmb_range_unit.currentText()

        if var_key == "N turns":
            xs = np.linspace(max(vmin, 1.0), vmax, n_steps)
            xs_si = xs
            xlabel = tr("N turns")
        elif var_key == "Frequency":
            xs = np.linspace(vmin, vmax, n_steps)
            xs_si = xs * cc.FREQ_UNITS.get(unit, 1.0)
            xlabel = f"{tr('Frequency')} [{unit}]"
        else:
            xs = np.linspace(vmin, vmax, n_steps)
            xs_si = xs * cc.UNITS.get(unit, 1.0)
            xlabel = f"{tr(var_key)} [{unit}]"

        Ls, Rs, Qs = [], [], []
        for x in xs_si:
            pp = dict(p)
            if var_key == "N turns":
                pp["N"] = float(x)
            elif var_key == "Inner diameter":
                pp["d_in"] = float(x)
            elif var_key == "Width":
                pp["w"] = float(x)
            elif var_key == "Gap":
                pp["gap"] = float(x)
            elif var_key == "Thickness":
                pp["t"] = float(x)
            elif var_key == "Frequency":
                pp["freq"] = float(x)
            try:
                r = self.compute_single(pp)
                Ls.append(r["L"])
                Rs.append(r["R_ac"])
                Qs.append(r["Q"])
            except Exception:
                Ls.append(np.nan); Rs.append(np.nan); Qs.append(np.nan)

        Ls = np.array(Ls); Rs = np.array(Rs); Qs = np.array(Qs)

        # Auto unit
        def auto_L(arr):
            m = np.nanmedian(np.abs(arr))
            if m >= 1e-3: return arr * 1e3, "L [mH]", "mH"
            if m >= 1e-6: return arr * 1e6, "L [μH]", "μH"
            if m >= 1e-9: return arr * 1e9, "L [nH]", "nH"
            return arr * 1e12, "L [pH]", "pH"

        L_p, L_lbl, L_unit = auto_L(Ls)
        ax1, ax2, ax3 = self.plot_canvas.axes
        for a in (ax1, ax2, ax3):
            a.clear()

        line1, = ax1.plot(xs, L_p, "-o", color=PALETTE["line_L"], markersize=3.5, linewidth=1.8)
        ui.style_axes(ax1, title=tr("Inductance"), xlabel=xlabel, ylabel=L_lbl)
        line2, = ax2.plot(xs, Rs, "-o", color=PALETTE["line_R"], markersize=3.5, linewidth=1.8)
        ui.style_axes(ax2, title=tr("AC resistance"),
                      xlabel=xlabel, ylabel=f"R [Ω] @ {_fmt_f(p['freq'])}")
        line3, = ax3.plot(xs, Qs, "-o", color=PALETTE["line_Q"], markersize=3.5, linewidth=1.8)
        ui.style_axes(ax3, title=tr("Quality factor"), xlabel=xlabel, ylabel="Q")

        # Hover tooltips
        cursor = mplcursors.cursor([line1, line2, line3], hover=True)

        @cursor.connect("add")
        def _on_add(sel):
            xv, yv = sel.target
            sel.annotation.set_text(f"{xlabel} = {xv:.4g}\nvalue = {yv:.4g}")
            sel.annotation.get_bbox_patch().set(fc="#fffce8", ec=PALETTE["accent"],
                                                lw=1.2, alpha=0.95)

        self.plot_canvas.draw()
        # Cache for export
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
        self.gb_topo.setTitle(tr("Topology"))
        self.rb_series.setText(tr("Series (spiral)"))
        self.rb_parallel.setText(tr("Parallel (rings)"))
        self.chk_coupling.setText(tr("With mutual coupling (parallel)"))
        self.gb_shape.setTitle(tr("Shape"))
        self.rb_circular.setText(tr("Circular"))
        self.rb_square.setText(tr("Square"))
        self.gb_formula.setTitle(tr("Inductance formula"))
        self.lbl_method.setText(tr("Method:"))
        self.gb_mat.setTitle(tr("Conductor material"))
        self.lbl_preset.setText(tr("Preset:"))
        self.gb_geom.setTitle(tr("Geometry"))
        self.lbl_N.setText(tr("Number of turns:"))
        self.gb_range.setTitle(tr("Range mode (plot)"))
        self.chk_range.setText(tr("Enable range"))
        self.lbl_var.setText(tr("Variable:"))
        # rebuild range var dropdown
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
        # rerun compute to refresh dynamic labels
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
    w = MicrocoilWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
