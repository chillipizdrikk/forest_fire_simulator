from __future__ import annotations

from PySide6.QtCore import QTimer


def connect_main_window_signals(window) -> None:
    window.timer = QTimer(window)
    window.timer.timeout.connect(window.on_tick)

    window.btn_start.clicked.connect(window.on_start)
    window.btn_pause.clicked.connect(window.on_pause)
    window.btn_step.clicked.connect(window.on_step)
    window.btn_reset.clicked.connect(window.on_reset)
    window.btn_apply_size.clicked.connect(window.on_apply_size)
    window.btn_export_metrics.clicked.connect(window.on_export_metrics)


    window.f_slider.valueChanged.connect(window.on_params_changed)
    window.speed_slider.valueChanged.connect(window.on_speed_changed)

    window.chk_lightning.toggled.connect(window.on_lightning_toggled)
    window.strikes_spin.valueChanged.connect(window.on_lightning_event_params_changed)
    window.cooldown_spin.valueChanged.connect(window.on_lightning_event_params_changed)

    window.chk_wind.toggled.connect(window.on_wind_toggled)
    window.cmb_wind.currentTextChanged.connect(window.on_wind_dir_changed)
    window.wind_slider.valueChanged.connect(window.on_wind_strength_changed)

    window.hum_slider.valueChanged.connect(window.on_humidity_changed)
    window.temp_slider.valueChanged.connect(window.on_temperature_changed)

    window.chk_rain.toggled.connect(window.on_rain_toggled)
    window.rain_slider.valueChanged.connect(window.on_rain_intensity_changed)

    window.chk_rain_scenario.toggled.connect(window.on_rain_scenario_toggled)
    window.rain_scen_slider.valueChanged.connect(window.on_rain_scenario_intensity_changed)
    window.rain_start_spin.valueChanged.connect(window.on_rain_scenario_steps_changed)
    window.rain_end_spin.valueChanged.connect(window.on_rain_scenario_steps_changed)

    window.conif_slider.valueChanged.connect(window.on_conifer_ratio_changed)
    window.flamm_d_slider.valueChanged.connect(window.on_flammability_changed)
    window.flamm_c_slider.valueChanged.connect(window.on_flammability_changed)

    window.grid_widget.cell_painted.connect(window.on_cell_painted)
