from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)


def create_card() -> QFrame:
    card = QFrame()
    card.setObjectName("Card")
    return card


def create_tab_page() -> dict[str, QWidget | QVBoxLayout | QScrollArea]:
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)

    content = QWidget()
    content.setStyleSheet("background: #111827;")
    scroll.setWidget(content)

    layout = QVBoxLayout(content)
    layout.setContentsMargins(4, 6, 4, 6)
    layout.setSpacing(14)

    return {
        "scroll": scroll,
        "content": content,
        "layout": layout,
    }


def labeled_widget(text: str, widget: QWidget) -> QWidget:
    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)
    label = QLabel(text)
    label.setObjectName("FieldLabel")
    layout.addWidget(label)
    layout.addWidget(widget)
    return container


def slider_row(parent_layout: QVBoxLayout, text: str, value: int, fmt: str, scale: int = 1):
    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)

    head = QHBoxLayout()
    head.setContentsMargins(0, 0, 0, 0)

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
    slider.setMinimumHeight(24)

    layout.addLayout(head)
    layout.addWidget(slider)

    parent_layout.addWidget(container)
    return value_label, slider


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
    slider.setMinimumHeight(24)

    def to_slider(x):
        return int((x - min_v) / (max_v - min_v) * steps)

    def to_float(v):
        return min_v + (max_v - min_v) * (v / steps)

    slider.setValue(to_slider(init))

    layout.addLayout(head)
    layout.addWidget(slider)
    return row, title, value, slider, to_float
