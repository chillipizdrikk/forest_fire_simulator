from __future__ import annotations

from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog

from src.app.core.ca import CAConfig, ForestFireCA, TREE_CONIF, TREE_DECID


class MainWindowActionsMixin:
    def _save_metrics_snapshot(self):
        self.ca.finalize_run_metrics()
        self.last_run_metrics = self.ca.metrics_payload()
        self.last_run_metrics_json = self.ca.metrics_payload_json()
        self.show_final_metrics = True

    def on_start(self):
        if self.timer.isActive():
            return

        self.run_has_seen_fire = self.ca.has_active_fire()
        has_trees = bool(np.any((self.ca.grid == TREE_DECID) | (self.ca.grid == TREE_CONIF)))

        if not has_trees:
            self.statusBar().showMessage("На карті немає дерев для симуляції.", 3500)
            return

        if not self.ca.has_active_fire() and (not self.cfg.lightning_enabled or self.cfg.f <= 0.0):
            self.statusBar().showMessage("Немає активного займання, а блискавка вимкнена або має нульову ймовірність.", 3500)
            return
        
        if not self.run_in_progress:
            self.ca.start_run_tracking()
            self.run_has_seen_fire = self.ca.has_active_fire()
        self.show_final_metrics = False

        self.timer.start(self.speed_slider.value())
        self.run_in_progress = True
        self._update_stats()

    def on_pause(self):
        self.timer.stop()
        self._save_metrics_snapshot()
        self._update_stats()

    def on_step(self):
        self.on_tick()

    def on_reset(self):
        self.timer.stop()
        if self.run_in_progress:
            self._save_metrics_snapshot()
        self.ca.reset()
        self.run_has_seen_fire = False
        self.run_in_progress = False
        self.show_final_metrics = False
        self.grid_widget.set_grid(self.ca.grid)
        self._update_rain_status()
        self._update_stats()
        self.statusBar().showMessage("Мапу скинуто до початкового стану.", 2500)

    def on_apply_size(self):
        self.timer.stop()
        if self.run_in_progress:
            self._save_metrics_snapshot()
        self.cfg.width = int(self.w_spin.value())
        self.cfg.height = int(self.h_spin.value())
        self.ca = ForestFireCA(self.cfg)
        self.run_has_seen_fire = False
        self.run_in_progress = False
        self.show_final_metrics = False
        self.grid_widget.set_grid(self.ca.grid)
        self._update_rain_status()
        self._update_stats()
        self.statusBar().showMessage("Розмір ґратки оновлено.", 2500)

    def on_export_metrics(self):
        default_name = f"forest_fire_metrics_step_{self.ca.step_count}.json"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Експорт метрик",
            default_name,
            "JSON Files (*.json);;All Files (*)",
        )
        if not file_path:
            return

        Path(file_path).write_text(self.last_run_metrics_json, encoding="utf-8")
        self.statusBar().showMessage(f"Метрики збережено: {file_path}", 3500)

    def on_tick(self):
        self.ca.step()
        self.grid_widget.set_grid(self.ca.grid)
        self._update_rain_status()
        self._update_stats()

        has_active_fire = self.ca.has_active_fire()
        has_trees = bool(np.any((self.ca.grid == TREE_DECID) | (self.ca.grid == TREE_CONIF)))
        has_future_ignition_sources = self.cfg.lightning_enabled and self.cfg.f > 0.0

        if has_active_fire:
            self.run_has_seen_fire = True

        if self.timer.isActive() and not has_trees:
            self.timer.stop()
            self._save_metrics_snapshot()
            self.run_in_progress = False
            self._update_stats()
            self.statusBar().showMessage("На карті більше немає дерев. Симуляцію зупинено.", 2500)
            return

        if self.timer.isActive() and not has_active_fire and not has_future_ignition_sources:
            self.timer.stop()
            self._save_metrics_snapshot()
            self.run_in_progress = False
            self._update_stats()
            self.statusBar().showMessage("Активного вогню немає і нові займання неможливі. Симуляцію зупинено.", 2500)
            return

        if self.run_has_seen_fire and not has_active_fire:
            self.timer.stop()
            self._save_metrics_snapshot()
            self.run_in_progress = False
            self._update_stats()
            self.statusBar().showMessage("Пожежний інцидент завершився.", 2500)

    def on_cell_painted(self, row: int, col: int, button: int):
        if self.timer.isActive():
            self.statusBar().showMessage("Натисни «Пауза», щоб редагувати мапу.", 1400)
            return
        
        if self.run_in_progress:
            self._save_metrics_snapshot()
            self.run_in_progress = False
            self.run_has_seen_fire = self.ca.has_active_fire()

        if button == Qt.RightButton.value:
            self.ca.set_empty(row, col)
            self.grid_widget.set_grid(self.ca.grid)
            self._update_stats()
            return

        tool = self.tool_combo.currentText()
        if tool == "Підпал":
            self.ca.ignite(row, col)
        elif tool == "Посадити листяне дерево":
            self.ca.plant_decid(row, col)
        elif tool == "Посадити хвойне дерево":
            self.ca.plant_conif(row, col)
        elif tool == "Бар'єр":
            self.ca.set_barrier(row, col, True)
        elif tool == "Стерти":
            self.ca.set_empty(row, col)

        self.grid_widget.set_grid(self.ca.grid)
        self._update_stats()

    def on_params_changed(self):
        self.cfg.f = float(self.f_to_float(self.f_slider.value()))
        self._update_f_label_and_state()

    def on_lightning_event_params_changed(self):
        self.cfg.lightning_max_strikes_per_event = int(self.strikes_spin.value())
        self.cfg.lightning_cooldown_steps = int(self.cooldown_spin.value())

    def on_speed_changed(self, value: int):
        self.speed_lab.setText(f"{value} ms")
        if self.timer.isActive():
            self.timer.start(value)

    def on_lightning_toggled(self, checked: bool):
        self.cfg.lightning_enabled = bool(checked)
        self._update_f_label_and_state()

    def on_wind_toggled(self, checked: bool):
        self.cfg.wind_enabled = bool(checked)
        self.cmb_wind.setEnabled(self.cfg.wind_enabled)
        self.wind_slider.setEnabled(self.cfg.wind_enabled)

    def on_wind_dir_changed(self, text: str):
        self.cfg.wind_dir = text

    def on_wind_strength_changed(self, value: int):
        self.cfg.wind_strength = value / 100.0
        self.wind_lab.setText(f"{self.cfg.wind_strength:.2f}")

    def on_humidity_changed(self, value: int):
        self.cfg.humidity = value / 100.0
        self.hum_lab.setText(f"{self.cfg.humidity:.2f}")

    def on_temperature_changed(self, value: int):
        self.cfg.temperature_c = float(value)
        self.temp_lab.setText(f"{value} °C")

    def on_rain_toggled(self, checked: bool):
        self.cfg.rain_enabled = bool(checked)
        if self.cfg.rain_enabled and self.cfg.rain_scenario_enabled:
            self.cfg.rain_scenario_enabled = False
            self.chk_rain_scenario.blockSignals(True)
            self.chk_rain_scenario.setChecked(False)
            self.chk_rain_scenario.blockSignals(False)
        self._update_rain_status()
        self._update_stats()

    def on_rain_intensity_changed(self, value: int):
        self.cfg.rain_intensity = value / 100.0
        self.rain_lab.setText(f"{self.cfg.rain_intensity:.2f}")
        self._update_rain_status()
        self._update_stats()

    def on_rain_scenario_toggled(self, checked: bool):
        self.cfg.rain_scenario_enabled = bool(checked)
        if self.cfg.rain_scenario_enabled and self.cfg.rain_enabled:
            self.cfg.rain_enabled = False
            self.chk_rain.blockSignals(True)
            self.chk_rain.setChecked(False)
            self.chk_rain.blockSignals(False)
        self._update_rain_status()
        self._update_stats()

    def on_rain_scenario_intensity_changed(self, value: int):
        self.cfg.rain_scenario_intensity = value / 100.0
        self.rain_scen_lab.setText(f"{self.cfg.rain_scenario_intensity:.2f}")
        self._update_rain_status()
        self._update_stats()

    def on_rain_scenario_steps_changed(self):
        start_step = int(self.rain_start_spin.value())
        end_step = int(self.rain_end_spin.value())

        if start_step >= end_step:
            end_step = start_step + 1
            self.rain_end_spin.blockSignals(True)
            self.rain_end_spin.setValue(end_step)
            self.rain_end_spin.blockSignals(False)
            self.statusBar().showMessage("Діапазон сценарію дощу авто-виправлено: кінець = початок + 1.", 3000)

        self.cfg.rain_scenario_start_step = start_step
        self.cfg.rain_scenario_end_step = end_step
        self._update_rain_status()
        self._update_stats()

    def on_conifer_ratio_changed(self, value: int):
        self.cfg.conifer_ratio = value / 100.0
        self.conif_lab.setText(f"{self.cfg.conifer_ratio:.2f}")

    def on_flammability_changed(self):
        self.cfg.flamm_decid = float(self.flamm_d_to_float(self.flamm_d_slider.value()))
        self.cfg.flamm_conif = float(self.flamm_c_to_float(self.flamm_c_slider.value()))
        self.flamm_d_value.setText(f"{self.cfg.flamm_decid:.4f}")
        self.flamm_c_value.setText(f"{self.cfg.flamm_conif:.4f}")
