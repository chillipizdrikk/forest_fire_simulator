from __future__ import annotations

from src.app.core.ca import BARRIER, BURNT, BURNING_STATES, EMPTY, TREE_CONIF, TREE_DECID


class MainWindowStateMixin:
    def _sync_initial_state(self):
        self.grid_widget.set_grid(self.ca.grid)
        self._update_f_label_and_state()
        self._update_rain_status()
        self._update_stats()
        self.on_wind_toggled(self.cfg.wind_enabled)

    def _cell_counts(self):
        g = self.ca.grid
        return {
            "empty": int((g == EMPTY).sum()),
            "decid": int((g == TREE_DECID).sum()),
            "conif": int((g == TREE_CONIF).sum()),
            "burning": int(sum((g == state).sum() for state in BURNING_STATES)),
            "barrier": int((g == BARRIER).sum()),
            "burnt": int((g == BURNT).sum()),
        }

    def _update_stats(self):
        counts = self._cell_counts()
        living_trees = counts["decid"] + counts["conif"]
        self.step_value.setText(str(self.ca.step_count))
        self.fire_value.setText(str(counts["burning"]))
        self.tree_value.setText(str(living_trees))
        current_rain = self.ca.current_rain_intensity()
        self.rain_value.setText("OFF" if current_rain <= 0 else f"{current_rain:.2f}")
        self.status_chip.setText("RUNNING" if self.timer.isActive() else "READY")

    def _update_rain_status(self):
        if self.cfg.rain_scenario_start_step >= self.cfg.rain_scenario_end_step:
            self.rain_status_lab.setText("Invalid scenario range: End must be greater than Start")
            return

        current = self.ca.current_rain_intensity()
        if current > 0:
            self.rain_status_lab.setText(f"Rain active now: {current:.2f}")
        else:
            self.rain_status_lab.setText("Rain active now: OFF")

    def _update_f_label_and_state(self):
        self.f_slider.setEnabled(self.cfg.lightning_enabled)
        self.strikes_spin.setEnabled(self.cfg.lightning_enabled)
        self.cooldown_spin.setEnabled(self.cfg.lightning_enabled)

        effective = self.cfg.f if self.cfg.lightning_enabled else 0.0
        self.f_value.setText(f"{self.cfg.f:.4f}")
        state = "ON" if self.cfg.lightning_enabled else "OFF"
        self.lightning_status.setText(f"Lightning: {state} | effective probability: {effective:.4f}")