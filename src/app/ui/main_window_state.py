from __future__ import annotations


class MainWindowStateMixin:
    def _sync_initial_state(self):
        self.grid_widget.set_grid(self.ca.grid)
        self._update_f_label_and_state()
        self._update_rain_status()
        self._update_stats()
        self.on_wind_toggled(self.cfg.wind_enabled)

    def _cell_counts(self):
        return self.ca.cell_counts()

    def _set_text_if_widget_exists(self, attr_name: str, value: str):
        widget = getattr(self, attr_name, None)
        if widget is not None:
            widget.setText(value)

    def _update_stats(self):
        counts = self._cell_counts()
        living_trees = counts["decid"] + counts["conif"]
        self.step_value.setText(str(self.ca.step_count))
        self.fire_value.setText(str(counts["burning"]))
        self.tree_value.setText(str(living_trees))
        current_rain = self.ca.current_rain_intensity()
        self.rain_value.setText("ВИМК" if current_rain <= 0 else f"{current_rain:.2f}")
        self.status_chip.setText("ВИКОНАННЯ" if self.timer.isActive() else "ГОТОВО")

        metrics = self.last_run_metrics.get("metrics", {})
        show_final_metrics = bool(self.show_final_metrics and isinstance(metrics, dict))

        baf_text = f"{float(metrics.get('baf', 0.0)):.4f}" if show_final_metrics else "—"
        peak_text = str(int(metrics.get("peak_fire_size", 0))) if show_final_metrics else "—"
        time_to_peak_text = str(int(metrics.get("time_to_peak", 0))) if show_final_metrics else "—"
        fire_duration_text = str(int(metrics.get("fire_duration", 0))) if show_final_metrics else "—"
        auc_text = str(int(metrics.get("auc", 0))) if show_final_metrics else "—"

        self._set_text_if_widget_exists("baf_value", baf_text)
        self._set_text_if_widget_exists("peak_fire_value", peak_text)
        self._set_text_if_widget_exists("time_to_peak_value", time_to_peak_text)
        self._set_text_if_widget_exists("fire_duration_value", fire_duration_text)
        self._set_text_if_widget_exists("auc_value", auc_text)
        self._set_text_if_widget_exists(
            "metrics_data_state",
            "Фінальні метрики готові до перегляду та експорту." if show_final_metrics else "Дані ще не зібрано",
        )

        if hasattr(self, "btn_open_analytics"):
            self.btn_open_analytics.setEnabled(show_final_metrics)
        if hasattr(self, "btn_export_metrics"):
            self.btn_export_metrics.setEnabled(show_final_metrics)

    def _update_rain_status(self):
        if self.cfg.rain_scenario_start_step >= self.cfg.rain_scenario_end_step:
            self.rain_status_lab.setText("Некоректний діапазон сценарію: кінець має бути більшим за початок")
            return

        current = self.ca.current_rain_intensity()
        if current > 0:
            self.rain_status_lab.setText(f"Дощ зараз: {current:.2f}")
        else:
            self.rain_status_lab.setText("Дощ зараз: ВИМК")

    def _update_f_label_and_state(self):
        self.f_slider.setEnabled(self.cfg.lightning_enabled)
        self.strikes_spin.setEnabled(self.cfg.lightning_enabled)
        self.cooldown_spin.setEnabled(self.cfg.lightning_enabled)

        effective = self.cfg.f if self.cfg.lightning_enabled else 0.0
        self.f_value.setText(f"{self.cfg.f:.4f}")
        state = "УВІМК" if self.cfg.lightning_enabled else "ВИМК"
        self.lightning_status.setText(f"Блискавка: {state} | ефективна ймовірність: {effective:.4f}")
