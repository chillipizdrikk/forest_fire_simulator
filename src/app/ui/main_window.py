from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QHBoxLayout, QLabel, QMainWindow, QVBoxLayout, QWidget

from src.app.core.ca import (
    BARRIER,
    BURNT,
    BURNING_STATES,
    CAConfig,
    EMPTY,
    ForestFireCA,
    TREE_CONIF,
    TREE_DECID,
)
from src.app.ui.bindings import connect_main_window_signals
from src.app.ui.grid_widget import GridWidget
from src.app.ui.panels import build_all_controls, build_controls_tabs, build_legend_card, build_stats_card
from src.app.ui.panels.common import create_card
from src.app.ui.styles import apply_main_window_styles


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Forest Fire CA Simulator")
        self.resize(1520, 920)
        self.setMinimumSize(1280, 760)

        self.cfg = CAConfig(
            width=20,
            height=20,
            f=0.01,
            lightning_enabled=True,
            lightning_max_strikes_per_event=1,
            lightning_cooldown_steps=20,
            humidity=0.30,
            temperature_c=25.0,
            conifer_ratio=0.50,
            flamm_decid=0.75,
            flamm_conif=0.80,
            burn_stage_factors=(1.00, 0.55, 0.25),
            rain_enabled=False,
            rain_intensity=0.0,
            rain_scenario_enabled=False,
            rain_scenario_start_step=20,
            rain_scenario_end_step=40,
            rain_scenario_intensity=0.3,
        )
        self.ca = ForestFireCA(self.cfg)
        self.run_has_seen_fire = False

        apply_main_window_styles(self)
        self._build_ui()
        connect_main_window_signals(self)
        self._sync_initial_state()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(18)

        left_col = QVBoxLayout()
        left_col.setSpacing(14)
        root.addLayout(left_col, 5)

        header_card = create_card()
        header_layout = QVBoxLayout(header_card)
        header_layout.setSpacing(8)

        title = QLabel("Forest Fire Cellular Automata Simulator")
        title.setObjectName("Title")
        header_layout.addWidget(title)
        left_col.addWidget(header_card)

        self.sim_card = create_card()
        sim_layout = QVBoxLayout(self.sim_card)
        sim_layout.setSpacing(14)

        top_bar = QHBoxLayout()
        text_col = QVBoxLayout()

        sim_title = QLabel("Simulation field")
        sim_title.setObjectName("SectionTitle")

        sim_hint = QLabel(
            "Ліва кнопка миші — активний інструмент, права — стирання. Для редагування карта має бути на паузі."
        )
        sim_hint.setWordWrap(True)
        sim_hint.setObjectName("Hint")

        text_col.addWidget(sim_title)
        text_col.addWidget(sim_hint)
        top_bar.addLayout(text_col, 1)

        self.status_chip = QLabel("READY")
        self.status_chip.setObjectName("ValueBadge")
        top_bar.addWidget(self.status_chip, 0, Qt.AlignTop)

        sim_layout.addLayout(top_bar)

        self.grid_widget = GridWidget()
        sim_layout.addWidget(self.grid_widget, 1)
        sim_layout.addWidget(build_legend_card())
        left_col.addWidget(self.sim_card, 1)

        self.right_card = create_card()
        self.right_card.setMinimumWidth(430)
        self.right_card.setMaximumWidth(500)
        root.addWidget(self.right_card, 2)

        right_layout = QVBoxLayout(self.right_card)
        right_layout.setContentsMargins(14, 14, 14, 14)
        right_layout.setSpacing(12)

        side_title = QLabel("Control panel")
        side_title.setObjectName("SectionTitle")
        right_layout.addWidget(side_title)

        build_stats_card(self)
        right_layout.addWidget(self.stats_card)

        build_controls_tabs(self, right_layout)
        build_all_controls(self)

        self.statusBar().showMessage("Готово до редагування карти.")

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

    def on_start(self):
        self.run_has_seen_fire = self.ca.has_active_fire()

        if not self.ca.has_active_fire() and (not self.cfg.lightning_enabled or self.cfg.f <= 0.0):
            self.statusBar().showMessage("Немає активного займання, а блискавка вимкнена або має нульову ймовірність.", 3500)
            return

        self.timer.start(self.speed_slider.value())
        self._update_stats()

    def on_pause(self):
        self.timer.stop()
        self._update_stats()

    def on_step(self):
        self.on_tick()

    def on_reset(self):
        self.timer.stop()
        self.ca.reset()
        self.run_has_seen_fire = False
        self.grid_widget.set_grid(self.ca.grid)
        self._update_rain_status()
        self._update_stats()
        self.statusBar().showMessage("Карту скинуто до початкового стану.", 2500)

    def on_apply_size(self):
        self.timer.stop()
        self.cfg.width = int(self.w_spin.value())
        self.cfg.height = int(self.h_spin.value())
        self.ca = ForestFireCA(self.cfg)
        self.run_has_seen_fire = False
        self.grid_widget.set_grid(self.ca.grid)
        self._update_rain_status()
        self._update_stats()
        self.statusBar().showMessage("Розмір сітки оновлено.", 2500)

    def on_tick(self):
        self.ca.step()
        self.grid_widget.set_grid(self.ca.grid)
        self._update_rain_status()
        self._update_stats()

        if self.ca.has_active_fire():
            self.run_has_seen_fire = True

        if self.run_has_seen_fire and not self.ca.has_active_fire():
            self.timer.stop()
            self._update_stats()
            self.statusBar().showMessage("Пожежний інцидент завершився.", 2500)

    def on_cell_painted(self, row: int, col: int, button: int):
        if self.timer.isActive():
            self.statusBar().showMessage("Натисни Pause, щоб редагувати карту.", 1400)
            return

        if button == Qt.RightButton.value:
            self.ca.set_empty(row, col)
            self.grid_widget.set_grid(self.ca.grid)
            self._update_stats()
            return

        tool = self.tool_combo.currentText()
        if tool == "Ignite":
            self.ca.ignite(row, col)
        elif tool == "Plant decid":
            self.ca.plant_decid(row, col)
        elif tool == "Plant conif":
            self.ca.plant_conif(row, col)
        elif tool == "Barrier":
            self.ca.set_barrier(row, col, True)
        elif tool == "Erase":
            self.ca.set_empty(row, col)

        self.grid_widget.set_grid(self.ca.grid)
        self._update_stats()

    def on_params_changed(self):
        self.cfg.f = float(self.f_to_float(self.f_slider.value()))
        self._update_f_label_and_state()

    def on_lightning_event_params_changed(self):
        self.cfg.lightning_max_strikes_per_event = int(self.strikes_spin.value())
        self.cfg.lightning_cooldown_steps = int(self.cooldown_spin.value())

    def on_speed_changed(self, v: int):
        self.speed_lab.setText(f"{v} ms")
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
        self.wind_lab.setText(f"{self.cfg.wind_strength:.2f}")

    def on_humidity_changed(self, v: int):
        self.cfg.humidity = v / 100.0
        self.hum_lab.setText(f"{self.cfg.humidity:.2f}")

    def on_temperature_changed(self, v: int):
        self.cfg.temperature_c = float(v)
        self.temp_lab.setText(f"{v} °C")

    def on_rain_toggled(self, checked: bool):
        self.cfg.rain_enabled = bool(checked)
        self._update_rain_status()
        self._update_stats()

    def on_rain_intensity_changed(self, v: int):
        self.cfg.rain_intensity = v / 100.0
        self.rain_lab.setText(f"{self.cfg.rain_intensity:.2f}")
        self._update_rain_status()
        self._update_stats()

    def on_rain_scenario_toggled(self, checked: bool):
        self.cfg.rain_scenario_enabled = bool(checked)
        self._update_rain_status()

    def on_rain_scenario_intensity_changed(self, v: int):
        self.cfg.rain_scenario_intensity = v / 100.0
        self.rain_scen_lab.setText(f"{self.cfg.rain_scenario_intensity:.2f}")
        self._update_rain_status()

    def on_rain_scenario_steps_changed(self):
        self.cfg.rain_scenario_start_step = int(self.rain_start_spin.value())
        self.cfg.rain_scenario_end_step = int(self.rain_end_spin.value())
        self._update_rain_status()

    def _update_rain_status(self):
        current = self.ca.current_rain_intensity()
        if current > 0:
            self.rain_status_lab.setText(f"Rain active now: {current:.2f}")
        else:
            self.rain_status_lab.setText("Rain active now: OFF")

    def on_conifer_ratio_changed(self, v: int):
        self.cfg.conifer_ratio = v / 100.0
        self.conif_lab.setText(f"{self.cfg.conifer_ratio:.2f}")

    def on_flammability_changed(self):
        self.cfg.flamm_decid = float(self.flamm_d_to_float(self.flamm_d_slider.value()))
        self.cfg.flamm_conif = float(self.flamm_c_to_float(self.flamm_c_slider.value()))
        self.flamm_d_value.setText(f"{self.cfg.flamm_decid:.4f}")
        self.flamm_c_value.setText(f"{self.cfg.flamm_conif:.4f}")

    def _update_f_label_and_state(self):
        self.f_slider.setEnabled(self.cfg.lightning_enabled)
        self.strikes_spin.setEnabled(self.cfg.lightning_enabled)
        self.cooldown_spin.setEnabled(self.cfg.lightning_enabled)

        eff = self.cfg.f if self.cfg.lightning_enabled else 0.0
        self.f_value.setText(f"{self.cfg.f:.4f}")
        state = "ON" if self.cfg.lightning_enabled else "OFF"
        self.lightning_status.setText(f"Lightning: {state} | effective probability: {eff:.4f}")

    def get_cell_color(self, state: int) -> QColor:
        if state == TREE_DECID:
            return QColor("#46b060")
        if state == TREE_CONIF:
            return QColor("#1c7849")
        if state in BURNING_STATES:
            return QColor("#ff8429")
        if state == BURNT:
            return QColor("#6e4c34")
        if state == BARRIER:
            return QColor("#94a3b8")
        return QColor("#091017")
