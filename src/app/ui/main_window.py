from __future__ import annotations
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSlider, QComboBox,
    QCheckBox, QSpinBox
)

from src.app.core.ca import ForestFireCA, CAConfig, EMPTY, TREE_DECID, TREE_CONIF, BURNING, BARRIER
from src.app.ui.grid_widget import GridWidget


def slider_float(label: str, min_v: float, max_v: float, init: float, steps: int = 1000):
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)

    lab = QLabel(f"{label}: {init:.4f}")
    s = QSlider(Qt.Horizontal)
    s.setMinimum(0)
    s.setMaximum(steps)

    def to_slider(x):
        return int((x - min_v) / (max_v - min_v) * steps)

    def to_float(v):
        return min_v + (max_v - min_v) * (v / steps)

    s.setValue(to_slider(init))

    layout.addWidget(lab, 1)
    layout.addWidget(s, 4)
    return row, lab, s, to_float


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Forest Fire CA Simulator (Moore)")

        self.cfg = CAConfig(
            width=20,
            height=20,
            p=0.01,
            f=0.001,
            lightning_enabled=True,
            humidity=0.20,

            # NEW vegetation defaults
            conifer_ratio=0.50,
            flamm_decid=0.85,
            flamm_conif=1.00,
        )
        self.ca = ForestFireCA(self.cfg)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)

        # Grid
        self.grid_widget = GridWidget()
        root.addWidget(self.grid_widget, 4)

        # Panel
        panel = QWidget()
        panel_l = QVBoxLayout(panel)
        root.addWidget(panel, 2)

        panel_l.addWidget(QLabel("Left-click: ignite | Right-click: toggle barrier"))
        panel_l.addWidget(QLabel("Neighborhood: Moore (8-neighbor)"))

        # Buttons
        btn_row = QHBoxLayout()
        self.btn_start = QPushButton("Start")
        self.btn_pause = QPushButton("Pause")
        self.btn_step = QPushButton("Step")
        self.btn_reset = QPushButton("Reset (regen forest)")
        btn_row.addWidget(self.btn_start)
        btn_row.addWidget(self.btn_pause)
        btn_row.addWidget(self.btn_step)
        btn_row.addWidget(self.btn_reset)
        panel_l.addLayout(btn_row)

        # Grid size
        panel_l.addWidget(QLabel("Grid size:"))
        size_row = QHBoxLayout()
        self.w_spin = QSpinBox()
        self.h_spin = QSpinBox()
        self.w_spin.setRange(10, 500)
        self.h_spin.setRange(10, 500)
        self.w_spin.setValue(self.cfg.width)
        self.h_spin.setValue(self.cfg.height)
        self.btn_apply_size = QPushButton("Apply")
        size_row.addWidget(QLabel("W"))
        size_row.addWidget(self.w_spin)
        size_row.addWidget(QLabel("H"))
        size_row.addWidget(self.h_spin)
        size_row.addWidget(self.btn_apply_size)
        panel_l.addLayout(size_row)

        # Wind
        self.chk_wind = QCheckBox("Wind enabled")
        self.chk_wind.setChecked(self.cfg.wind_enabled)
        panel_l.addWidget(self.chk_wind)

        self.cmb_wind = QComboBox()
        self.cmb_wind.addItems(["N", "NE", "E", "SE", "S", "SW", "W", "NW"])
        self.cmb_wind.setCurrentText(self.cfg.wind_dir)
        panel_l.addWidget(QLabel("Wind direction:"))
        panel_l.addWidget(self.cmb_wind)

        wind_row = QWidget()
        wind_l = QHBoxLayout(wind_row)
        wind_l.setContentsMargins(0, 0, 0, 0)
        self.wind_lab = QLabel(f"Wind strength: {self.cfg.wind_strength:.2f}")
        self.wind_slider = QSlider(Qt.Horizontal)
        self.wind_slider.setRange(0, 100)
        self.wind_slider.setValue(int(self.cfg.wind_strength * 100))
        wind_l.addWidget(self.wind_lab, 1)
        wind_l.addWidget(self.wind_slider, 4)
        panel_l.addWidget(wind_row)

        self.cmb_wind.setEnabled(self.cfg.wind_enabled)
        self.wind_slider.setEnabled(self.cfg.wind_enabled)

        # Humidity
        hum_row = QWidget()
        hum_l = QHBoxLayout(hum_row)
        hum_l.setContentsMargins(0, 0, 0, 0)
        self.hum_lab = QLabel(f"Humidity: {self.cfg.humidity:.2f}")
        self.hum_slider = QSlider(Qt.Horizontal)
        self.hum_slider.setRange(0, 100)
        self.hum_slider.setValue(int(self.cfg.humidity * 100))
        hum_l.addWidget(self.hum_lab, 1)
        hum_l.addWidget(self.hum_slider, 4)
        panel_l.addWidget(hum_row)

        # --- Vegetation (NEW) ---
        panel_l.addWidget(QLabel("Vegetation:"))

        # Conifer ratio 0..1
        conif_row = QWidget()
        conif_l = QHBoxLayout(conif_row)
        conif_l.setContentsMargins(0, 0, 0, 0)
        self.conif_lab = QLabel(f"Conifer ratio: {self.cfg.conifer_ratio:.2f}")
        self.conif_slider = QSlider(Qt.Horizontal)
        self.conif_slider.setRange(0, 100)
        self.conif_slider.setValue(int(self.cfg.conifer_ratio * 100))
        conif_l.addWidget(self.conif_lab, 1)
        conif_l.addWidget(self.conif_slider, 4)
        panel_l.addWidget(conif_row)

        # Flammability sliders (0..2)
        d_row, self.flamm_d_lab, self.flamm_d_slider, self.flamm_d_to_float = slider_float(
            "Flammability (decid)", 0.0, 2.0, self.cfg.flamm_decid
        )
        c_row, self.flamm_c_lab, self.flamm_c_slider, self.flamm_c_to_float = slider_float(
            "Flammability (conif)", 0.0, 2.0, self.cfg.flamm_conif
        )
        panel_l.addWidget(d_row)
        panel_l.addWidget(c_row)

        # Lightning (Variant C)
        self.chk_lightning = QCheckBox("Lightning enabled (random ignition)")
        self.chk_lightning.setChecked(self.cfg.lightning_enabled)
        panel_l.addWidget(self.chk_lightning)

        # p, f sliders
        p_row, self.p_lab, self.p_slider, self.p_to_float = slider_float("p (growth)", 0.0, 0.05, self.cfg.p)
        f_row, self.f_lab, self.f_slider, self.f_to_float = slider_float("f (lightning)", 0.0, 0.01, self.cfg.f)
        panel_l.addWidget(p_row)
        panel_l.addWidget(f_row)

        # Speed
        sp_row = QWidget()
        sp_l = QHBoxLayout(sp_row)
        sp_l.setContentsMargins(0, 0, 0, 0)
        self.speed_lab = QLabel("Speed (ms): 60")
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setMinimum(10)
        self.speed_slider.setMaximum(300)
        self.speed_slider.setValue(60)
        sp_l.addWidget(self.speed_lab, 1)
        sp_l.addWidget(self.speed_slider, 4)
        panel_l.addWidget(sp_row)

        self.stats = QLabel("Step: 0")
        panel_l.addWidget(self.stats)
        panel_l.addStretch(1)

        # Timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.on_tick)

        # Signals
        self.btn_start.clicked.connect(self.on_start)
        self.btn_pause.clicked.connect(self.on_pause)
        self.btn_step.clicked.connect(self.on_step)
        self.btn_reset.clicked.connect(self.on_reset)
        self.btn_apply_size.clicked.connect(self.on_apply_size)

        self.p_slider.valueChanged.connect(self.on_params_changed)
        self.f_slider.valueChanged.connect(self.on_params_changed)
        self.speed_slider.valueChanged.connect(self.on_speed_changed)

        self.chk_lightning.toggled.connect(self.on_lightning_toggled)

        self.chk_wind.toggled.connect(self.on_wind_toggled)
        self.cmb_wind.currentTextChanged.connect(self.on_wind_dir_changed)
        self.wind_slider.valueChanged.connect(self.on_wind_strength_changed)

        self.hum_slider.valueChanged.connect(self.on_humidity_changed)

        # Vegetation signals
        self.conif_slider.valueChanged.connect(self.on_conifer_ratio_changed)
        self.flamm_d_slider.valueChanged.connect(self.on_flammability_changed)
        self.flamm_c_slider.valueChanged.connect(self.on_flammability_changed)

        self.grid_widget.cell_clicked.connect(self.on_cell_clicked)
        self.grid_widget.cell_right_clicked.connect(self.on_cell_right_clicked)

        # First render
        self.grid_widget.set_grid(self.ca.grid)
        self._update_f_label_and_state()

    def on_start(self):
        self.timer.start(self.speed_slider.value())

    def on_pause(self):
        self.timer.stop()

    def on_step(self):
        self.on_tick()

    def on_reset(self):
        self.timer.stop()
        self.ca.reset()
        self.grid_widget.set_grid(self.ca.grid)
        self.stats.setText(f"Step: {self.ca.step_count}")

    def on_apply_size(self):
        self.timer.stop()
        self.cfg.width = int(self.w_spin.value())
        self.cfg.height = int(self.h_spin.value())
        self.ca = ForestFireCA(self.cfg)
        self.grid_widget.set_grid(self.ca.grid)
        self.stats.setText(f"Step: {self.ca.step_count}")

    def on_cell_clicked(self, row: int, col: int):
        before = self.ca.grid[row, col]
        self.ca.ignite(row, col)
        self.grid_widget.set_grid(self.ca.grid)

        if int(before) not in (TREE_DECID, TREE_CONIF):
            self.statusBar().showMessage("Підпал можливий тільки на клітинках з деревом", 2000)

    def on_cell_right_clicked(self, row: int, col: int):
        self.ca.toggle_barrier(row, col)
        self.grid_widget.set_grid(self.ca.grid)

    def on_tick(self):
        self.ca.step()
        self.grid_widget.set_grid(self.ca.grid)
        self.stats.setText(f"Step: {self.ca.step_count}")

    def on_params_changed(self):
        self.cfg.p = float(self.p_to_float(self.p_slider.value()))
        self.cfg.f = float(self.f_to_float(self.f_slider.value()))
        self.p_lab.setText(f"p (growth): {self.cfg.p:.4f}")
        self._update_f_label_and_state()

    def on_speed_changed(self, v: int):
        self.speed_lab.setText(f"Speed (ms): {v}")
        if self.timer.isActive():
            self.timer.start(v)

    def on_lightning_toggled(self, checked: bool):
        self.cfg.lightning_enabled = bool(checked)
        self._update_f_label_and_state()

    def on_wind_toggled(self, checked: bool):
        self.cfg.wind_enabled = bool(checked)
        self.cmb_wind.setEnabled(self.cfg.wind_enabled)
        self.wind_slider.setEnabled(self.cfg.wind_enabled)

    def on_wind_dir_changed(self, text: str):
        self.cfg.wind_dir = text

    def on_wind_strength_changed(self, v: int):
        self.cfg.wind_strength = v / 100.0
        self.wind_lab.setText(f"Wind strength: {self.cfg.wind_strength:.2f}")

    def on_humidity_changed(self, v: int):
        self.cfg.humidity = v / 100.0
        self.hum_lab.setText(f"Humidity: {self.cfg.humidity:.2f}")

    def on_conifer_ratio_changed(self, v: int):
        self.cfg.conifer_ratio = v / 100.0
        self.conif_lab.setText(f"Conifer ratio: {self.cfg.conifer_ratio:.2f}")
        self.statusBar().showMessage("Conifer ratio впливає на новий ріст і на Reset (regen forest).", 2000)

    def on_flammability_changed(self):
        self.cfg.flamm_decid = float(self.flamm_d_to_float(self.flamm_d_slider.value()))
        self.cfg.flamm_conif = float(self.flamm_c_to_float(self.flamm_c_slider.value()))
        self.flamm_d_lab.setText(f"Flammability (decid): {self.cfg.flamm_decid:.4f}")
        self.flamm_c_lab.setText(f"Flammability (conif): {self.cfg.flamm_conif:.4f}")

    def _update_f_label_and_state(self):
        self.f_slider.setEnabled(self.cfg.lightning_enabled)
        status = "ON" if self.cfg.lightning_enabled else "OFF"
        eff = self.cfg.f if self.cfg.lightning_enabled else 0.0
        self.f_lab.setText(f"f (lightning): {self.cfg.f:.4f}  | effective: {eff:.4f} ({status})")
