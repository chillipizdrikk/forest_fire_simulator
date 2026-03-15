from __future__ import annotations

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from src.app.utils.palette import PALETTE


class GridWidget(QWidget):
    cell_painted = Signal(int, int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._grid: np.ndarray | None = None
        self._rgb: np.ndarray | None = None

        self._painting = False
        self._paint_button = Qt.LeftButton
        self._last_cell: tuple[int, int] | None = None
        self._grid_rect = QRectF()

        self.setMinimumSize(420, 420)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)

    def set_grid(self, grid: np.ndarray):
        self._grid = grid
        self._rgb = PALETTE[grid]
        self.update()

    def _compute_grid_rect(self) -> QRectF:
        rect = self.rect()
        if self._grid is None or rect.width() <= 0 or rect.height() <= 0:
            return QRectF()

        h, w = self._grid.shape
        side = min(rect.width(), rect.height())
        if side <= 0:
            return QRectF()

        cell = side / max(h, w)
        draw_w = cell * w
        draw_h = cell * h
        x = (rect.width() - draw_w) / 2
        y = (rect.height() - draw_h) / 2
        return QRectF(x, y, draw_w, draw_h)

    def _pos_to_cell(self, pos: QPointF):
        if self._grid is None:
            return None

        rect = self._grid_rect
        if rect.isNull() or not rect.contains(pos):
            return None

        h, w = self._grid.shape
        rel_x = (pos.x() - rect.left()) / rect.width()
        rel_y = (pos.y() - rect.top()) / rect.height()
        col = int(rel_x * w)
        row = int(rel_y * h)
        col = max(0, min(w - 1, col))
        row = max(0, min(h - 1, row))
        return row, col

    def mousePressEvent(self, event):
        if self._grid is None:
            return
        if event.button() not in (Qt.LeftButton, Qt.RightButton):
            return

        self._painting = True
        self._paint_button = event.button()

        cell = self._pos_to_cell(event.position())
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

        cell = self._pos_to_cell(event.position())
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

        self._grid_rect = self._compute_grid_rect()
        if self._grid_rect.isNull():
            return

        h, w = self._grid.shape
        img = QImage(self._rgb.data, w, h, 3 * w, QImage.Format_RGB888)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, False)
        painter.fillRect(self.rect(), QColor("#0b1220"))

        border_rect = self._grid_rect.adjusted(-2, -2, 2, 2)
        painter.setPen(QPen(QColor("#22324b"), 2))
        painter.setBrush(QColor("#111827"))
        painter.drawRoundedRect(border_rect, 12, 12)

        painter.drawImage(self._grid_rect, img)

        if max(h, w) <= 45:
            pen = QPen(QColor(255, 255, 255, 25), 1)
            painter.setPen(pen)
            cell_w = self._grid_rect.width() / w
            cell_h = self._grid_rect.height() / h
            for col in range(1, w):
                x = self._grid_rect.left() + col * cell_w
                painter.drawLine(int(x), int(self._grid_rect.top()), int(x), int(self._grid_rect.bottom()))
            for row in range(1, h):
                y = self._grid_rect.top() + row * cell_h
                painter.drawLine(int(self._grid_rect.left()), int(y), int(self._grid_rect.right()), int(y))

        painter.end()
