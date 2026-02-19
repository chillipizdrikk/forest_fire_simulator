from __future__ import annotations
import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QWidget

from src.app.utils.palette import PALETTE

class GridWidget(QWidget):
    cell_clicked = Signal(int, int)  # row, col

    def __init__(self, parent=None):
        super().__init__(parent)
        self._grid: np.ndarray | None = None
        self._rgb: np.ndarray | None = None  # важливо тримати посилання, щоб QImage не “вмер”
        self.setMinimumSize(400, 400)

    def set_grid(self, grid: np.ndarray):
        self._grid = grid
        self._rgb = PALETTE[grid]  # (h,w,3) uint8
        self.update()

    def mousePressEvent(self, event):
        if self._grid is None:
            return
        if event.button() != Qt.LeftButton:
            return

        rect = self.rect()
        if rect.width() <= 0 or rect.height() <= 0:
            return

        # координати кліку у віджеті
        pos = event.position()
        x = pos.x()
        y = pos.y()

        h, w = self._grid.shape

        # мапимо координати кліку на індекси сітки
        col = int(x / rect.width() * w)
        row = int(y / rect.height() * h)

        # clamp
        if col < 0: col = 0
        if row < 0: row = 0
        if col >= w: col = w - 1
        if row >= h: row = h - 1

        self.cell_clicked.emit(row, col)

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
