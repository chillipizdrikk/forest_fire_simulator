from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from src.app.ui.panels.common import create_card


def build_legend_card():
    card = create_card()
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
