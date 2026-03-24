from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QSlider,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.app.ui.panels.common import create_card, create_tab_page, labeled_widget, slider_float, slider_row


def build_controls_tabs(window, parent_layout: QVBoxLayout) -> None:
    window.tabs = QTabWidget()
    parent_layout.addWidget(window.tabs, 1)

    window.tab_general = create_tab_page()
    window.tab_environment = create_tab_page()
    window.tab_advanced = create_tab_page()

    window.tabs.addTab(window.tab_general["scroll"], "General")
    window.tabs.addTab(window.tab_environment["scroll"], "Environment")
    window.tabs.addTab(window.tab_advanced["scroll"], "Advanced")

    window.general_layout = window.tab_general["layout"]
    window.environment_layout = window.tab_environment["layout"]
    window.advanced_layout = window.tab_advanced["layout"]


def build_controls_group(window):
    card = create_card()
    layout = QVBoxLayout(card)
    layout.setSpacing(14)

    title = QLabel("Map and playback")
    title.setObjectName("SectionTitle")
    layout.addWidget(title)

    row = QHBoxLayout()
    window.tool_combo = QComboBox()
    window.tool_combo.addItems(["Ignite", "Plant decid", "Plant conif", "Barrier", "Erase"])
    window.tool_combo.setCurrentText("Ignite")
    row.addWidget(labeled_widget("Tool", window.tool_combo), 1)
    layout.addLayout(row)

    btn_row = QGridLayout()
    btn_row.setHorizontalSpacing(10)
    btn_row.setVerticalSpacing(10)
    window.btn_start = QPushButton("Start")
    window.btn_pause = QPushButton("Pause")
    window.btn_pause.setObjectName("SecondaryBtn")
    window.btn_step = QPushButton("Step")
    window.btn_step.setObjectName("SecondaryBtn")
    window.btn_reset = QPushButton("Reset map")
    window.btn_reset.setObjectName("DangerBtn")
    btn_row.addWidget(window.btn_start, 0, 0)
    btn_row.addWidget(window.btn_pause, 0, 1)
    btn_row.addWidget(window.btn_step, 1, 0)
    btn_row.addWidget(window.btn_reset, 1, 1)
    layout.addLayout(btn_row)

    size_row = QHBoxLayout()
    window.w_spin = QSpinBox()
    window.h_spin = QSpinBox()
    window.w_spin.setRange(10, 500)
    window.h_spin.setRange(10, 500)
    window.w_spin.setValue(window.cfg.width)
    window.h_spin.setValue(window.cfg.height)
    window.btn_apply_size = QPushButton("Apply size")
    window.btn_apply_size.setObjectName("SecondaryBtn")
    size_row.addWidget(labeled_widget("Width", window.w_spin), 1)
    size_row.addWidget(labeled_widget("Height", window.h_spin), 1)
    layout.addLayout(size_row)
    layout.addWidget(window.btn_apply_size)

    speed_row = QWidget()
    speed_layout = QVBoxLayout(speed_row)
    speed_layout.setContentsMargins(0, 0, 0, 0)
    speed_layout.setSpacing(6)
    speed_head = QHBoxLayout()
    speed_title = QLabel("Playback speed")
    speed_title.setObjectName("FieldLabel")
    window.speed_lab = QLabel("60 ms")
    window.speed_lab.setObjectName("ValueBadge")
    speed_head.addWidget(speed_title)
    speed_head.addStretch(1)
    speed_head.addWidget(window.speed_lab)
    window.speed_slider = QSlider(Qt.Horizontal)
    window.speed_slider.setRange(10, 300)
    window.speed_slider.setValue(60)
    speed_layout.addLayout(speed_head)
    speed_layout.addWidget(window.speed_slider)
    layout.addWidget(speed_row)

    window.general_layout.addWidget(card)


def build_environment_group(window):
    group = QGroupBox("Environment")
    layout = QVBoxLayout(group)
    layout.setSpacing(12)

    window.chk_wind = QCheckBox("Enable wind")
    window.chk_wind.setChecked(window.cfg.wind_enabled)
    layout.addWidget(window.chk_wind)

    window.cmb_wind = QComboBox()
    window.cmb_wind.addItems(["N", "NE", "E", "SE", "S", "SW", "W", "NW"])
    window.cmb_wind.setCurrentText(window.cfg.wind_dir)
    layout.addWidget(labeled_widget("Wind direction", window.cmb_wind))

    window.wind_lab, window.wind_slider = slider_row(layout, "Wind strength", int(window.cfg.wind_strength * 100), "{:.2f}", scale=100)
    window.hum_lab, window.hum_slider = slider_row(layout, "Humidity", int(window.cfg.humidity * 100), "{:.2f}", scale=100)

    temp_widget = QWidget()
    temp_layout = QVBoxLayout(temp_widget)
    temp_layout.setContentsMargins(0, 0, 0, 0)
    temp_layout.setSpacing(6)
    head = QHBoxLayout()
    title = QLabel("Temperature")
    title.setObjectName("FieldLabel")
    window.temp_lab = QLabel(f"{int(window.cfg.temperature_c)} °C")
    window.temp_lab.setObjectName("ValueBadge")
    head.addWidget(title)
    head.addStretch(1)
    head.addWidget(window.temp_lab)
    window.temp_slider = QSlider(Qt.Horizontal)
    window.temp_slider.setRange(-10, 40)
    window.temp_slider.setValue(int(window.cfg.temperature_c))
    temp_layout.addLayout(head)
    temp_layout.addWidget(window.temp_slider)
    layout.addWidget(temp_widget)

    window.environment_layout.addWidget(group)


def build_rain_group(window):
    group = QGroupBox("Rain settings")
    layout = QVBoxLayout(group)
    layout.setSpacing(12)

    window.chk_rain = QCheckBox("Manual rain")
    window.chk_rain.setChecked(window.cfg.rain_enabled)
    layout.addWidget(window.chk_rain)
    window.rain_lab, window.rain_slider = slider_row(layout, "Rain intensity", int(window.cfg.rain_intensity * 100), "{:.2f}", scale=100)

    divider = QFrame()
    divider.setFrameShape(QFrame.HLine)
    divider.setStyleSheet("background:#243244; max-height:1px; border:none;")
    layout.addWidget(divider)

    window.chk_rain_scenario = QCheckBox("Automatic rain scenario")
    window.chk_rain_scenario.setChecked(window.cfg.rain_scenario_enabled)
    layout.addWidget(window.chk_rain_scenario)
    window.rain_scen_lab, window.rain_scen_slider = slider_row(
        layout, "Scenario intensity", int(window.cfg.rain_scenario_intensity * 100), "{:.2f}", scale=100
    )

    steps_row = QHBoxLayout()
    window.rain_start_spin = QSpinBox()
    window.rain_end_spin = QSpinBox()
    window.rain_start_spin.setRange(0, 100000)
    window.rain_end_spin.setRange(0, 100000)
    window.rain_start_spin.setValue(window.cfg.rain_scenario_start_step)
    window.rain_end_spin.setValue(window.cfg.rain_scenario_end_step)
    steps_row.addWidget(labeled_widget("Start step", window.rain_start_spin), 1)
    steps_row.addWidget(labeled_widget("End step", window.rain_end_spin), 1)
    layout.addLayout(steps_row)

    window.rain_status_lab = QLabel("Rain active now: OFF")
    window.rain_status_lab.setObjectName("Hint")
    layout.addWidget(window.rain_status_lab)
    window.environment_layout.addWidget(group)


def build_vegetation_group(window):
    group = QGroupBox("Vegetation")
    layout = QVBoxLayout(group)
    layout.setSpacing(12)

    window.conif_lab, window.conif_slider = slider_row(
        layout,
        "Conifer ratio",
        int(window.cfg.conifer_ratio * 100),
        "{:.2f}",
        scale=100,
    )
    d_row, _, window.flamm_d_value, window.flamm_d_slider, window.flamm_d_to_float = slider_float(
        "Flammability (deciduous)", 0.0, 2.0, window.cfg.flamm_decid
    )
    c_row, _, window.flamm_c_value, window.flamm_c_slider, window.flamm_c_to_float = slider_float(
        "Flammability (coniferous)", 0.0, 2.0, window.cfg.flamm_conif
    )
    layout.addWidget(d_row)
    layout.addWidget(c_row)
    window.advanced_layout.addWidget(group)


def build_lightning_group(window):
    group = QGroupBox("Lightning")
    layout = QVBoxLayout(group)
    layout.setSpacing(12)

    window.chk_lightning = QCheckBox("Enable lightning events")
    window.chk_lightning.setChecked(window.cfg.lightning_enabled)
    layout.addWidget(window.chk_lightning)

    f_row, _, window.f_value, window.f_slider, window.f_to_float = slider_float("Event probability", 0.0, 0.20, window.cfg.f)
    layout.addWidget(f_row)

    steps_row = QHBoxLayout()
    window.strikes_spin = QSpinBox()
    window.cooldown_spin = QSpinBox()
    window.strikes_spin.setRange(1, 20)
    window.cooldown_spin.setRange(0, 500)
    window.strikes_spin.setValue(window.cfg.lightning_max_strikes_per_event)
    window.cooldown_spin.setValue(window.cfg.lightning_cooldown_steps)
    steps_row.addWidget(labeled_widget("Max strikes", window.strikes_spin), 1)
    steps_row.addWidget(labeled_widget("Cooldown", window.cooldown_spin), 1)
    layout.addLayout(steps_row)

    window.lightning_status = QLabel("")
    window.lightning_status.setObjectName("Hint")
    layout.addWidget(window.lightning_status)
    window.advanced_layout.addWidget(group)


def build_all_controls(window):
    build_controls_group(window)
    build_environment_group(window)
    build_rain_group(window)
    build_vegetation_group(window)
    build_lightning_group(window)

    window.general_layout.addStretch(1)
    window.environment_layout.addStretch(1)
    window.advanced_layout.addStretch(1)
