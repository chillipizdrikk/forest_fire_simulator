from __future__ import annotations
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSlider, QComboBox
)
from PySide6.QtCore import Qt

from src.app.core.ca import ForestFireCA, CAConfig
from src.app.ui.grid_widget import GridWidget

def slider_float(label: str, min_v: float, max_v: float, init: float, steps: int = 1000):
    """Хелпер: слайдер 0..steps, мапиться в float min..max"""
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
        self.setWindowTitle("Forest Fire CA Simulator")

        self.cfg = CAConfig(width=200, height=200, p=0.01, f=0.001, neighborhood="moore")
        self.ca = ForestFireCA(self.cfg)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)

        # Ліва частина: сітка
        self.grid_widget = GridWidget()
        root.addWidget(self.grid_widget, 4)

        # Права частина: панель керування
        panel = QWidget()
        panel_l = QVBoxLayout(panel)
        root.addWidget(panel, 2)

        # Кнопки
        btn_row = QHBoxLayout()
        self.btn_start = QPushButton("Start")
        self.btn_pause = QPushButton("Pause")
        self.btn_step = QPushButton("Step")
        self.btn_reset = QPushButton("Reset")
        btn_row.addWidget(self.btn_start)
        btn_row.addWidget(self.btn_pause)
        btn_row.addWidget(self.btn_step)
        btn_row.addWidget(self.btn_reset)
        panel_l.addLayout(btn_row)

        # Neighborhood
        self.cmb_neigh = QComboBox()
        self.cmb_neigh.addItems(["moore", "von_neumann"])
        self.cmb_neigh.setCurrentText(self.cfg.neighborhood)
        panel_l.addWidget(QLabel("Neighborhood:"))
        panel_l.addWidget(self.cmb_neigh)

        # Слайдери p і f
        p_row, self.p_lab, self.p_slider, self.p_to_float = slider_float("p (growth)", 0.0, 0.05, self.cfg.p)
        f_row, self.f_lab, self.f_slider, self.f_to_float = slider_float("f (lightning)", 0.0, 0.01, self.cfg.f)
        panel_l.addWidget(p_row)
        panel_l.addWidget(f_row)

        # Швидкість
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

        # Таймер симуляції
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.on_tick)

        # Сигнали
        self.btn_start.clicked.connect(self.on_start)
        self.btn_pause.clicked.connect(self.on_pause)
        self.btn_step.clicked.connect(self.on_step)
        self.btn_reset.clicked.connect(self.on_reset)

        self.p_slider.valueChanged.connect(self.on_params_changed)
        self.f_slider.valueChanged.connect(self.on_params_changed)
        self.cmb_neigh.currentTextChanged.connect(self.on_neigh_changed)
        self.speed_slider.valueChanged.connect(self.on_speed_changed)

        # Перший рендер
        self.grid_widget.set_grid(self.ca.grid)

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

    def on_tick(self):
        self.ca.step()
        self.grid_widget.set_grid(self.ca.grid)
        self.stats.setText(f"Step: {self.ca.step_count}")

    def on_params_changed(self):
        self.cfg.p = float(self.p_to_float(self.p_slider.value()))
        self.cfg.f = float(self.f_to_float(self.f_slider.value()))
        self.p_lab.setText(f"p (growth): {self.cfg.p:.4f}")
        self.f_lab.setText(f"f (lightning): {self.cfg.f:.4f}")

    def on_neigh_changed(self, text: str):
        self.cfg.neighborhood = text

    def on_speed_changed(self, v: int):
        self.speed_lab.setText(f"Speed (ms): {v}")
        if self.timer.isActive():
            self.timer.start(v)
