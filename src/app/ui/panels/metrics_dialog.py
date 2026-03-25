from __future__ import annotations

from PySide6.QtWidgets import QDialog, QVBoxLayout

from src.app.ui.panels.stats_panel import build_final_metrics_panel


class MetricsDialog(QDialog):
    def __init__(self, window):
        super().__init__(window)
        self.setWindowTitle("Аналітика пожежі")
        self.setModal(False)
        self.resize(640, 460)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        layout.addWidget(build_final_metrics_panel(window))
