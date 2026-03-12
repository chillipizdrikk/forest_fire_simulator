from __future__ import annotations
import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QWidget, QSizePolicy

from src.app.utils.palette import PALETTE


class GridWidget(QWidget):
    # row, col, button (Qt.LeftButton / Qt.RightButton)
    cell_painted = Signal(int, int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._grid: np.ndarray | None = None
        self._rgb: np.ndarray | None = None

        self._painting = False
        self._paint_button = Qt.LeftButton
        self._last_cell: tuple[int, int] | None = None

        self.setMinimumSize(280, 280)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)

    def set_grid(self, grid: np.ndarray):
        self._grid = grid
        self._rgb = PALETTE[grid]
        self.update()

    def _pos_to_cell(self, x: float, y: float):
        if self._grid is None:
            return None
        rect = self.rect()
        if rect.width() <= 0 or rect.height() <= 0:
            return None

        h, w = self._grid.shape
        col = int(x / rect.width() * w)
        row = int(y / rect.height() * h)
        col = max(0, min(w - 1, col))
        row = max(0, min(h - 1, row))
        return (row, col)

    def mousePressEvent(self, event):
        if self._grid is None:
            return
        if event.button() not in (Qt.LeftButton, Qt.RightButton):
            return

        self._painting = True
        self._paint_button = event.button()

        pos = event.position()
        cell = self._pos_to_cell(pos.x(), pos.y())
        if cell is None:
            return

        self._last_cell = cell
        r, c = cell
        self.cell_painted.emit(r, c, self._paint_button.value)

    def mouseMoveEvent(self, event):
        if not self._painting or self._grid is None:
            return
        if not (event.buttons() & self._paint_button):
            return

        pos = event.position()
        cell = self._pos_to_cell(pos.x(), pos.y())
        if cell is None or cell == self._last_cell:
            return

        self._last_cell = cell
        r, c = cell
        self.cell_painted.emit(r, c, self._paint_button.value)

    def mouseReleaseEvent(self, event):
        self._painting = False
        self._last_cell = None

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