from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from src.app.core.constants import BARRIER, BURNING1, BURNING2, BURNING3, BURNT, EMPTY, TREE_CONIF, TREE_DECID
from src.app.ui.panels.common import create_card
from src.app.utils.palette import PALETTE


def _state_to_hex(state: int) -> str:
    rgb = PALETTE[state]
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def build_legend_card():
    card = create_card()
    layout = QHBoxLayout(card)
    layout.setContentsMargins(14, 12, 14, 12)
    layout.setSpacing(14)
    items = [
         (_state_to_hex(EMPTY), "Порожньо"),
        (_state_to_hex(TREE_DECID), "Листяне"),
        (_state_to_hex(TREE_CONIF), "Хвойне"),
        (_state_to_hex(BURNING1), "Вогонь (1)"),
        (_state_to_hex(BURNING2), "Вогонь (2)"),
        (_state_to_hex(BURNING3), "Вогонь (3)"),
        (_state_to_hex(BARRIER), "Бар'єр"),
        (_state_to_hex(BURNT), "Випалено"),
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
