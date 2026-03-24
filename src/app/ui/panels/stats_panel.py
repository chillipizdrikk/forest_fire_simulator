from __future__ import annotations

from PySide6.QtWidgets import QGridLayout, QLabel, QVBoxLayout

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


def build_stats_card(window):
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
