from __future__ import annotations

MAIN_WINDOW_QSS = """
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
    background-color: #111827;
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
    background-color: #1d4ed8;
    border: 1px solid #3b82f6;
    border-radius: 10px;
    padding: 10px 14px;
    color: white;
    font-weight: 600;
    min-height: 18px;
}

QPushButton:hover {
    background-color: #2563eb;
    border: 1px solid #60a5fa;
}

QPushButton:pressed {
    background-color: #1e40af;
    border: 1px solid #93c5fd;
}

QPushButton#SecondaryBtn {
    background-color: #1f2937;
    border: 1px solid #334155;
    color: #f8fafc;
}

QPushButton#SecondaryBtn:hover {
    background-color: #273449;
    border: 1px solid #475569;
}

QPushButton#DangerBtn {
    background-color: #7f1d1d;
    border: 1px solid #b91c1c;
    color: white;
}

QPushButton#DangerBtn:hover {
    background-color: #991b1b;
    border: 1px solid #ef4444;
}

QComboBox, QSpinBox {
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 8px 10px;
    min-height: 20px;
    color: #f8fafc;
    selection-background-color: #1d4ed8;
    selection-color: white;
}

QComboBox:hover, QSpinBox:hover {
    border: 1px solid #475569;
}

QComboBox:focus, QSpinBox:focus {
    border: 1px solid #60a5fa;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 28px;
    border: none;
    background-color: #162033;
    border-top-right-radius: 10px;
    border-bottom-right-radius: 10px;
}

QComboBox::down-arrow {
    width: 10px;
    height: 10px;
}

QComboBox QAbstractItemView {
    background-color: #0f172a;
    color: #f8fafc;
    border: 1px solid #334155;
    outline: 0px;
    selection-background-color: #2563eb;
    selection-color: white;
}

QSpinBox::up-button, QSpinBox::down-button {
    border: none;
    width: 24px;
    background-color: #162033;
}

QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background-color: #1d2940;
}

QSlider {
    min-height: 24px;
}

QSlider::groove:horizontal {
    border: none;
    height: 8px;
    border-radius: 4px;
    background: #334155;
    margin: 0 2px;
}

QSlider::handle:horizontal {
    background: #60a5fa;
    border: 2px solid #dbeafe;
    width: 14px;
    height: 14px;
    margin: -4px 0;
    border-radius: 9px;
}

QSlider::sub-page:horizontal {
    background: #3b82f6;
    border-radius: 4px;
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
    background-color: #0f172a;
}

QCheckBox::indicator:hover {
    border: 1px solid #60a5fa;
}

QCheckBox::indicator:checked {
    background-color: #1d4ed8;
    border: 1px solid #93c5fd;
}

QCheckBox::indicator:checked::after {
    color: white;
}

QScrollArea {
    border: none;
    background-color: transparent;
}

QScrollArea > QWidget > QWidget {
    background-color: transparent;
}

QTabWidget::pane {
    border: 1px solid #243244;
    background-color: #111827;
    border-radius: 16px;
    top: -1px;
}

QTabBar::tab {
    background-color: #0f172a;
    color: #cbd5e1;
    border: 1px solid #243244;
    padding: 10px 14px;
    margin-right: 6px;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    min-width: 96px;
}

QTabBar::tab:selected {
    background-color: #111827;
    color: #f8fafc;
    border-bottom-color: #111827;
}

QTabBar::tab:hover:!selected {
    background-color: #162033;
}

QStatusBar {
    background-color: #0f172a;
    color: #cbd5e1;
}
"""


def apply_main_window_styles(window) -> None:
    window.setStyleSheet(MAIN_WINDOW_QSS)
