from __future__ import annotations
import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QWidget

from src.app.utils.palette import PALETTE


class GridWidget(QWidget):
    cell_clicked = Signal(int, int)         # left click
    cell_right_clicked = Signal(int, int)   # NEW: right click

    def __init__(self, parent=None):
        super().__init__(parent)
        self._grid: np.ndarray | None = None
        self._rgb: np.ndarray | None = None
        self.setMinimumSize(400, 400)

    def set_grid(self, grid: np.ndarray):
        self._grid = grid
        self._rgb = PALETTE[grid]
        self.update()

    def mousePressEvent(self, event):
        if self._grid is None:
            return

        rect = self.rect()
        if rect.width() <= 0 or rect.height() <= 0:
            return

        pos = event.position()
        x, y = pos.x(), pos.y()

        h, w = self._grid.shape
        col = int(x / rect.width() * w)
        row = int(y / rect.height() * h)

        col = max(0, min(w - 1, col))
        row = max(0, min(h - 1, row))

        if event.button() == Qt.LeftButton:
            self.cell_clicked.emit(row, col)
        elif event.button() == Qt.RightButton:
            self.cell_right_clicked.emit(row, col)

    def paintEvent(self, event):
        if self._grid is None or self._rgb is None:
            return

        h, w = self._grid.shape
        img = QImage(self._rgb.data, w, h, 3 * w, QImage.Format_RGB888)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, False)
        painter.fillRect(self.rect(), Qt.black)
        painter.drawImage(self.rect(), img)
        painter.end()
