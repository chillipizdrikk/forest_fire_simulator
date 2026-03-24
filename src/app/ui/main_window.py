from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QMainWindow, QVBoxLayout, QWidget

from src.app.core.ca import CAConfig, ForestFireCA
from src.app.ui.bindings import connect_main_window_signals
from src.app.ui.grid_widget import GridWidget
from src.app.ui.main_window_actions import MainWindowActionsMixin
from src.app.ui.main_window_state import MainWindowStateMixin
from src.app.ui.panels import build_all_controls, build_controls_tabs, build_legend_card, build_stats_card
from src.app.ui.panels.common import create_card
from src.app.ui.styles import apply_main_window_styles


class MainWindow(MainWindowActionsMixin, MainWindowStateMixin, QMainWindow):
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
