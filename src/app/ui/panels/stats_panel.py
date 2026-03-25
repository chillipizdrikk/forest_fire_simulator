from __future__ import annotations

from PySide6.QtWidgets import QGridLayout, QLabel, QPushButton, QVBoxLayout

from src.app.ui.panels.common import create_card


def stat_card(value: str, caption: str):
    card = create_card()

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


def build_live_stats_card(window):
    window.stats_card = create_card()
    layout = QVBoxLayout(window.stats_card)
    layout.setSpacing(12)

    title = QLabel("Огляд")
    title.setObjectName("SectionTitle")
    layout.addWidget(title)

    grid = QGridLayout()
    grid.setHorizontalSpacing(12)
    grid.setVerticalSpacing(12)

    window.step_card, window.step_value = stat_card("0", "Крок симуляції")
    window.fire_card, window.fire_value = stat_card("0", "Клітин, що горять")
    window.tree_card, window.tree_value = stat_card("0", "Живих дерев")
    window.rain_card, window.rain_value = stat_card("ВИМК", "Дощ зараз")

    cards = [window.step_card, window.fire_card, window.tree_card, window.rain_card]
    for i, card in enumerate(cards):
        grid.addWidget(card, i // 2, i % 2)

    layout.addLayout(grid)


def build_final_metrics_panel(window):
    panel = create_card()
    layout = QVBoxLayout(panel)
    layout.setSpacing(12)

    final_title = QLabel("Фінальні KPI (після завершення/паузи)")
    final_title.setObjectName("Hint")
    layout.addWidget(final_title)

    final_grid = QGridLayout()
    final_grid.setHorizontalSpacing(12)
    final_grid.setVerticalSpacing(12)

    window.baf_card, window.baf_value = stat_card("—", "BAF")
    window.peak_fire_card, window.peak_fire_value = stat_card("—", "Peak fire size")
    window.time_to_peak_card, window.time_to_peak_value = stat_card("—", "Time to peak")
    window.fire_duration_card, window.fire_duration_value = stat_card("—", "Fire duration")
    window.auc_card, window.auc_value = stat_card("—", "AUC")

    final_cards = [
        window.baf_card,
        window.peak_fire_card,
        window.time_to_peak_card,
        window.fire_duration_card,
        window.auc_card,
    ]
    for i, card in enumerate(final_cards):
        final_grid.addWidget(card, i // 2, i % 2)

    layout.addLayout(final_grid)

    window.metrics_hint = QLabel(
        "Підказка: JSON з метриками можна відкрити у notebook і побудувати plot за `burning_cells_t`."
    )
    window.metrics_hint.setWordWrap(True)
    window.metrics_hint.setObjectName("Hint")
    layout.addWidget(window.metrics_hint)

    window.btn_export_metrics = QPushButton("Експорт метрик")
    layout.addWidget(window.btn_export_metrics)

    return panel
