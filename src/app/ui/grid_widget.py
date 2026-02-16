from __future__ import annotations
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QWidget

from src.app.utils.palette import PALETTE

class GridWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._grid = None
        self._rgb = None  # важливо тримати посилання, щоб QImage не “вмер”
        self.setMinimumSize(400, 400)

    def set_grid(self, grid: np.ndarray):
        self._grid = grid
        self._rgb = PALETTE[grid]  # (h,w,3) uint8
        self.update()

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
