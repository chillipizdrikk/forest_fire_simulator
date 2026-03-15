from __future__ import annotations

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

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
from src.app.ui.grid_widget import GridWidget


def slider_float(label: str, min_v: float, max_v: float, init: float, steps: int = 1000):
    row = QWidget()
    layout = QVBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)

    head = QHBoxLayout()
    head.setContentsMargins(0, 0, 0, 0)
    title = QLabel(label)
    title.setObjectName("FieldLabel")
    value = QLabel(f"{init:.4f}")
    value.setObjectName("ValueBadge")
    head.addWidget(title)
    head.addStretch(1)
    head.addWidget(value)

    slider = QSlider(Qt.Horizontal)
    slider.setMinimum(0)
    slider.setMaximum(steps)

    def to_slider(x):
        return int((x - min_v) / (max_v - min_v) * steps)

    def to_float(v):
        return min_v + (max_v - min_v) * (v / steps)

    slider.setValue(to_slider(init))

    layout.addLayout(head)
    layout.addWidget(slider)
    return row, title, value, slider, to_float


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

        self._apply_styles()
        self._build_ui()
        self._connect_signals()
        self._sync_initial_state()

    def _apply_styles(self):
        self.setStyleSheet(
            """
            QMainWindow {
                background: #0b1220;
                color: #e5eefc;
            }

            QWidget {
                color: #e5eefc;
            }

            QLabel#Title {
                font-size: 26px;
                font-weight: 700;
                color: #f8fafc;
            }

            QLabel#Subtitle {
                font-size: 13px;
                color: #9fb1c9;
            }

            QLabel#SectionTitle {
                font-size: 15px;
                font-weight: 700;
                color: #f8fafc;
            }

            QLabel#FieldLabel {
                color: #cbd5e1;
                font-weight: 600;
            }

            QLabel#ValueBadge {
                background: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 4px 8px;
                color: #f8fafc;
                font-weight: 600;
                min-width: 72px;
            }

            QLabel#Hint, QLabel#LegendLabel {
                color: #94a3b8;
            }

            QLabel#StatValue {
                font-size: 20px;
                font-weight: 700;
                color: #f8fafc;
            }

            QLabel#StatCaption {
                color: #94a3b8;
                font-size: 12px;
            }

            QFrame#Card, QGroupBox {
                background: #111827;
                border: 1px solid #243244;
                border-radius: 16px;
            }

            QGroupBox {
                margin-top: 16px;
                padding: 18px 16px 16px 16px;
                font-weight: 700;
            }

            QGroupBox::title {
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 6px;
                color: #f8fafc;
            }

            QPushButton {
                background: #1d4ed8;
                border: none;
                border-radius: 10px;
                padding: 10px 14px;
                color: white;
                font-weight: 600;
            }

            QPushButton:hover {
                background: #2563eb;
            }

            QPushButton:pressed {
                background: #1e40af;
            }

            QPushButton#SecondaryBtn {
                background: #1f2937;
                border: 1px solid #334155;
            }

            QPushButton#SecondaryBtn:hover {
                background: #273449;
            }

            QPushButton#DangerBtn {
                background: #7f1d1d;
            }

            QPushButton#DangerBtn:hover {
                background: #991b1b;
            }

            QComboBox, QSpinBox {
                background: #0f172a;
                border: 1px solid #334155;
                border-radius: 10px;
                padding: 8px 10px;
                min-height: 18px;
                color: #f8fafc;
                selection-background-color: #1d4ed8;
            }

            QComboBox QAbstractItemView {
                background: #0f172a;
                color: #f8fafc;
                border: 1px solid #334155;
                selection-background-color: #2563eb;
                selection-color: white;
            }

            QSpinBox::up-button, QSpinBox::down-button,
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }

            QSlider::groove:horizontal {
                border: none;
                height: 6px;
                border-radius: 3px;
                background: #334155;
            }

            QSlider::handle:horizontal {
                background: #60a5fa;
                border: 2px solid #dbeafe;
                width: 16px;
                margin: -6px 0;
                border-radius: 8px;
            }

            QCheckBox {
                spacing: 10px;
                color: #e2e8f0;
            }

            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 5px;
                border: 1px solid #475569;
                background: #0f172a;
            }

            QCheckBox::indicator:checked {
                background: #2563eb;
                border: 1px solid #60a5fa;
            }

            QScrollArea {
                border: none;
                background: transparent;
            }

            QStatusBar {
                background: #0f172a;
                color: #cbd5e1;
            }
            """
        )

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(18)

        left_col = QVBoxLayout()
        left_col.setSpacing(14)
        root.addLayout(left_col, 5)

        header_card = self._create_card()
        header_layout = QVBoxLayout(header_card)
        header_layout.setSpacing(8)
        title = QLabel("Forest Fire Cellular Automata Simulator")
        title.setObjectName("Title")
        subtitle = QLabel(
            "Охайний інтерфейс для демонстрації сценаріїв займання, впливу вітру, вологості, дощу та блискавки."
        )
        subtitle.setWordWrap(True)
        subtitle.setObjectName("Subtitle")
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        left_col.addWidget(header_card)

        self.sim_card = self._create_card()
        sim_layout = QVBoxLayout(self.sim_card)
        sim_layout.setSpacing(14)

        top_bar = QHBoxLayout()
        text_col = QVBoxLayout()
        sim_title = QLabel("Simulation field")
        sim_title.setObjectName("SectionTitle")
        sim_hint = QLabel("Ліва кнопка миші — активний інструмент, права — стирання. Для редагування карта має бути на паузі.")
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
        sim_layout.addWidget(self._build_legend())
        left_col.addWidget(self.sim_card, 1)

        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setMinimumWidth(410)
        right_scroll.setMaximumWidth(470)
        root.addWidget(right_scroll, 2)

        panel = QWidget()
        right_scroll.setWidget(panel)
        self.panel_layout = QVBoxLayout(panel)
        self.panel_layout.setContentsMargins(0, 0, 4, 0)
        self.panel_layout.setSpacing(14)

        self._build_stats_card()
        self._build_controls_card()
        self._build_environment_group()
        self._build_rain_group()
        self._build_vegetation_group()
        self._build_lightning_group()
        self.panel_layout.addStretch(1)

        self.statusBar().showMessage("Готово до редагування карти.")

    def _connect_signals(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.on_tick)

        self.btn_start.clicked.connect(self.on_start)
        self.btn_pause.clicked.connect(self.on_pause)
        self.btn_step.clicked.connect(self.on_step)
        self.btn_reset.clicked.connect(self.on_reset)
        self.btn_apply_size.clicked.connect(self.on_apply_size)

        self.f_slider.valueChanged.connect(self.on_params_changed)
        self.speed_slider.valueChanged.connect(self.on_speed_changed)

        self.chk_lightning.toggled.connect(self.on_lightning_toggled)
        self.strikes_spin.valueChanged.connect(self.on_lightning_event_params_changed)
        self.cooldown_spin.valueChanged.connect(self.on_lightning_event_params_changed)

        self.chk_wind.toggled.connect(self.on_wind_toggled)
        self.cmb_wind.currentTextChanged.connect(self.on_wind_dir_changed)
        self.wind_slider.valueChanged.connect(self.on_wind_strength_changed)

        self.hum_slider.valueChanged.connect(self.on_humidity_changed)
        self.temp_slider.valueChanged.connect(self.on_temperature_changed)

        self.chk_rain.toggled.connect(self.on_rain_toggled)
        self.rain_slider.valueChanged.connect(self.on_rain_intensity_changed)

        self.chk_rain_scenario.toggled.connect(self.on_rain_scenario_toggled)
        self.rain_scen_slider.valueChanged.connect(self.on_rain_scenario_intensity_changed)
        self.rain_start_spin.valueChanged.connect(self.on_rain_scenario_steps_changed)
        self.rain_end_spin.valueChanged.connect(self.on_rain_scenario_steps_changed)

        self.conif_slider.valueChanged.connect(self.on_conifer_ratio_changed)
        self.flamm_d_slider.valueChanged.connect(self.on_flammability_changed)
        self.flamm_c_slider.valueChanged.connect(self.on_flammability_changed)

        self.grid_widget.cell_painted.connect(self.on_cell_painted)

    def _sync_initial_state(self):
        self.grid_widget.set_grid(self.ca.grid)
        self._update_f_label_and_state()
        self._update_rain_status()
        self._update_stats()
        self.on_wind_toggled(self.cfg.wind_enabled)

    def _build_stats_card(self):
        card = self._create_card()
        layout = QVBoxLayout(card)
        layout.setSpacing(12)

        title = QLabel("Overview")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)

        self.step_card, self.step_value = self._stat_card("0", "Simulation step")
        self.fire_card, self.fire_value = self._stat_card("0", "Burning cells")
        self.tree_card, self.tree_value = self._stat_card("0", "Living trees")
        self.rain_card, self.rain_value = self._stat_card("OFF", "Rain now")

        cards = [
            self.step_card,
            self.fire_card,
            self.tree_card,
            self.rain_card,
        ]

        for i, stat_card in enumerate(cards):
            grid.addWidget(stat_card, i // 2, i % 2)

        layout.addLayout(grid)
        self.panel_layout.addWidget(card)

    def _build_controls_card(self):
        card = self._create_card()
        layout = QVBoxLayout(card)
        layout.setSpacing(14)

        title = QLabel("Map and playback")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        row = QHBoxLayout()
        self.tool_combo = QComboBox()
        self.tool_combo.addItems(["Ignite", "Plant decid", "Plant conif", "Barrier", "Erase"])
        self.tool_combo.setCurrentText("Ignite")
        row.addWidget(self._labeled_widget("Tool", self.tool_combo), 1)
        layout.addLayout(row)

        btn_row = QGridLayout()
        btn_row.setHorizontalSpacing(10)
        btn_row.setVerticalSpacing(10)
        self.btn_start = QPushButton("Start")
        self.btn_pause = QPushButton("Pause")
        self.btn_pause.setObjectName("SecondaryBtn")
        self.btn_step = QPushButton("Step")
        self.btn_step.setObjectName("SecondaryBtn")
        self.btn_reset = QPushButton("Reset map")
        self.btn_reset.setObjectName("DangerBtn")
        btn_row.addWidget(self.btn_start, 0, 0)
        btn_row.addWidget(self.btn_pause, 0, 1)
        btn_row.addWidget(self.btn_step, 1, 0)
        btn_row.addWidget(self.btn_reset, 1, 1)
        layout.addLayout(btn_row)

        size_row = QHBoxLayout()
        self.w_spin = QSpinBox()
        self.h_spin = QSpinBox()
        self.w_spin.setRange(10, 500)
        self.h_spin.setRange(10, 500)
        self.w_spin.setValue(self.cfg.width)
        self.h_spin.setValue(self.cfg.height)
        self.btn_apply_size = QPushButton("Apply size")
        self.btn_apply_size.setObjectName("SecondaryBtn")
        size_row.addWidget(self._labeled_widget("Width", self.w_spin), 1)
        size_row.addWidget(self._labeled_widget("Height", self.h_spin), 1)
        layout.addLayout(size_row)
        layout.addWidget(self.btn_apply_size)

        speed_row = QWidget()
        speed_layout = QVBoxLayout(speed_row)
        speed_layout.setContentsMargins(0, 0, 0, 0)
        speed_layout.setSpacing(6)
        speed_head = QHBoxLayout()
        speed_title = QLabel("Playback speed")
        speed_title.setObjectName("FieldLabel")
        self.speed_lab = QLabel("60 ms")
        self.speed_lab.setObjectName("ValueBadge")
        speed_head.addWidget(speed_title)
        speed_head.addStretch(1)
        speed_head.addWidget(self.speed_lab)
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(10, 300)
        self.speed_slider.setValue(60)
        speed_layout.addLayout(speed_head)
        speed_layout.addWidget(self.speed_slider)
        layout.addWidget(speed_row)

        self.panel_layout.addWidget(card)

    def _build_environment_group(self):
        group = QGroupBox("Environment")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        self.chk_wind = QCheckBox("Enable wind")
        self.chk_wind.setChecked(self.cfg.wind_enabled)
        layout.addWidget(self.chk_wind)

        self.cmb_wind = QComboBox()
        self.cmb_wind.addItems(["N", "NE", "E", "SE", "S", "SW", "W", "NW"])
        self.cmb_wind.setCurrentText(self.cfg.wind_dir)
        layout.addWidget(self._labeled_widget("Wind direction", self.cmb_wind))

        self.wind_lab, self.wind_slider = self._slider_row(layout, "Wind strength", int(self.cfg.wind_strength * 100), "{:.2f}", scale=100)
        self.hum_lab, self.hum_slider = self._slider_row(layout, "Humidity", int(self.cfg.humidity * 100), "{:.2f}", scale=100)

        temp_widget = QWidget()
        temp_layout = QVBoxLayout(temp_widget)
        temp_layout.setContentsMargins(0, 0, 0, 0)
        temp_layout.setSpacing(6)
        head = QHBoxLayout()
        title = QLabel("Temperature")
        title.setObjectName("FieldLabel")
        self.temp_lab = QLabel(f"{int(self.cfg.temperature_c)} °C")
        self.temp_lab.setObjectName("ValueBadge")
        head.addWidget(title)
        head.addStretch(1)
        head.addWidget(self.temp_lab)
        self.temp_slider = QSlider(Qt.Horizontal)
        self.temp_slider.setRange(-10, 40)
        self.temp_slider.setValue(int(self.cfg.temperature_c))
        temp_layout.addLayout(head)
        temp_layout.addWidget(self.temp_slider)
        layout.addWidget(temp_widget)

        self.panel_layout.addWidget(group)

    def _build_rain_group(self):
        group = QGroupBox("Rain settings")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        self.chk_rain = QCheckBox("Manual rain")
        self.chk_rain.setChecked(self.cfg.rain_enabled)
        layout.addWidget(self.chk_rain)
        self.rain_lab, self.rain_slider = self._slider_row(layout, "Rain intensity", int(self.cfg.rain_intensity * 100), "{:.2f}", scale=100)

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("background:#243244; max-height:1px; border:none;")
        layout.addWidget(divider)

        self.chk_rain_scenario = QCheckBox("Automatic rain scenario")
        self.chk_rain_scenario.setChecked(self.cfg.rain_scenario_enabled)
        layout.addWidget(self.chk_rain_scenario)
        self.rain_scen_lab, self.rain_scen_slider = self._slider_row(layout, "Scenario intensity", int(self.cfg.rain_scenario_intensity * 100), "{:.2f}", scale=100)

        steps_row = QHBoxLayout()
        self.rain_start_spin = QSpinBox()
        self.rain_end_spin = QSpinBox()
        self.rain_start_spin.setRange(0, 100000)
        self.rain_end_spin.setRange(0, 100000)
        self.rain_start_spin.setValue(self.cfg.rain_scenario_start_step)
        self.rain_end_spin.setValue(self.cfg.rain_scenario_end_step)
        steps_row.addWidget(self._labeled_widget("Start step", self.rain_start_spin), 1)
        steps_row.addWidget(self._labeled_widget("End step", self.rain_end_spin), 1)
        layout.addLayout(steps_row)

        self.rain_status_lab = QLabel("Rain active now: OFF")
        self.rain_status_lab.setObjectName("Hint")
        layout.addWidget(self.rain_status_lab)
        self.panel_layout.addWidget(group)

    def _build_vegetation_group(self):
        group = QGroupBox("Vegetation")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        self.conif_lab, self.conif_slider = self._slider_row(layout, "Conifer ratio", int(self.cfg.conifer_ratio * 100), "{:.2f}", scale=100)
        d_row, _, self.flamm_d_value, self.flamm_d_slider, self.flamm_d_to_float = slider_float(
            "Flammability (deciduous)", 0.0, 2.0, self.cfg.flamm_decid
        )
        c_row, _, self.flamm_c_value, self.flamm_c_slider, self.flamm_c_to_float = slider_float(
            "Flammability (coniferous)", 0.0, 2.0, self.cfg.flamm_conif
        )
        layout.addWidget(d_row)
        layout.addWidget(c_row)
        self.panel_layout.addWidget(group)

    def _build_lightning_group(self):
        group = QGroupBox("Lightning")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        self.chk_lightning = QCheckBox("Enable lightning events")
        self.chk_lightning.setChecked(self.cfg.lightning_enabled)
        layout.addWidget(self.chk_lightning)

        f_row, _, self.f_value, self.f_slider, self.f_to_float = slider_float(
            "Event probability", 0.0, 0.20, self.cfg.f
        )
        layout.addWidget(f_row)

        steps_row = QHBoxLayout()
        self.strikes_spin = QSpinBox()
        self.cooldown_spin = QSpinBox()
        self.strikes_spin.setRange(1, 20)
        self.cooldown_spin.setRange(0, 500)
        self.strikes_spin.setValue(self.cfg.lightning_max_strikes_per_event)
        self.cooldown_spin.setValue(self.cfg.lightning_cooldown_steps)
        steps_row.addWidget(self._labeled_widget("Max strikes", self.strikes_spin), 1)
        steps_row.addWidget(self._labeled_widget("Cooldown", self.cooldown_spin), 1)
        layout.addLayout(steps_row)

        self.lightning_status = QLabel("")
        self.lightning_status.setObjectName("Hint")
        layout.addWidget(self.lightning_status)
        self.panel_layout.addWidget(group)

    def _build_legend(self):
        card = self._create_card()
        layout = QHBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(14)
        items = [
            ("#091017", "Empty"),
            ("#46b060", "Deciduous"),
            ("#1c7849", "Coniferous"),
            ("#ff8429", "Fire"),
            ("#94a3b8", "Barrier"),
            ("#6e4c34", "Burnt"),
        ]
        for color, text in items:
            item = QWidget()
            row = QHBoxLayout(item)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(8)
            swatch = QLabel()
            swatch.setFixedSize(14, 14)
            swatch.setStyleSheet(f"background:{color}; border-radius:7px; border:1px solid #475569;")
            label = QLabel(text)
            label.setObjectName("LegendLabel")
            row.addWidget(swatch)
            row.addWidget(label)
            layout.addWidget(item)
        layout.addStretch(1)
        return card

    def _create_card(self):
        card = QFrame()
        card.setObjectName("Card")
        return card

    def _labeled_widget(self, text: str, widget: QWidget):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        label = QLabel(text)
        label.setObjectName("FieldLabel")
        layout.addWidget(label)
        layout.addWidget(widget)
        return container

    def _slider_row(self, parent_layout: QVBoxLayout, text: str, value: int, fmt: str, scale: int = 1):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        head = QHBoxLayout()
        title = QLabel(text)
        title.setObjectName("FieldLabel")
        value_label = QLabel(fmt.format(value / scale))
        value_label.setObjectName("ValueBadge")
        head.addWidget(title)
        head.addStretch(1)
        head.addWidget(value_label)
        slider = QSlider(Qt.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(value)
        layout.addLayout(head)
        layout.addWidget(slider)
        parent_layout.addWidget(container)
        return value_label, slider

    def _stat_card(self, value: str, caption: str):
        card = self._create_card()

        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        value_label = QLabel(value)
        value_label.setObjectName("StatValue")

        caption_label = QLabel(caption)
        caption_label.setObjectName("StatCaption")

        layout.addWidget(value_label)
        layout.addWidget(caption_label)

        return card, value_label

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
