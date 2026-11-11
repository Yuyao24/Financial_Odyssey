"""A small line-chart widget with hover tooltips, used by the Insights page."""

import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFontMetrics,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PyQt6.QtWidgets import QWidget

from ..formatting import money
from .theme import AL_C, AL_L, AL_R, W_BOLD, W_MED, W_SEMI, T, make_font


def nice_ticks(lo, hi, n=5):
    if hi <= lo:
        hi = lo + 1
    span = hi - lo
    raw = span / n
    mag = 10 ** math.floor(math.log10(raw))
    step = mag
    for m in (1, 2, 2.5, 5, 10):
        step = m * mag
        if span / step <= n:
            break
    v = math.floor(lo / step) * step
    ticks = []
    while v <= hi + step * 0.001:
        ticks.append(v)
        v += step
    return ticks


def short_money(v):
    a = abs(v)
    sign = "-" if v < 0 else ""
    if a >= 1_000_000:
        return f"{sign}${a / 1_000_000:.1f}M"
    if a >= 10_000:
        return f"{sign}${a / 1000:.0f}k"
    if a >= 1000:
        return f"{sign}${a / 1000:.1f}k"
    return f"{sign}${a:.0f}"


class LineChart(QWidget):
    """Line/area chart with gridlines, shaded bands, event markers and a hover tooltip."""

    L, R, T, B = 120, 34, 26, 64

    def __init__(self):
        super().__init__()
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.labels, self.series, self.bands, self.markers = [], [], [], []
        self.fmt, self.tick_fmt = money, short_money
        self.y_range = None
        self.hover = None
        self.empty_text = "Advance a few quarters to see your history here."

    def set_data(self, labels, series, fmt=money, tick_fmt=short_money, bands=(), markers=(), y_range=None):
        """series: list of (name, values, color, filled)."""
        self.labels, self.series = labels, series
        self.fmt, self.tick_fmt = fmt, tick_fmt
        self.bands, self.markers, self.y_range = list(bands), list(markers), y_range
        self.hover = None
        self.update()

    # ---- geometry
    def _plot(self):
        return QRectF(self.L, self.T, max(10, self.width() - self.L - self.R), max(10, self.height() - self.T - self.B))

    def _yrange(self):
        if self.y_range:
            return self.y_range
        vals = [v for _, vs, _, _ in self.series for v in vs]
        lo, hi = min(vals + [0]), max(vals + [1])
        pad = (hi - lo) * 0.08 or 1
        return lo - (pad if lo < 0 else 0), hi + pad

    def _x(self, i, plot, n):
        return plot.left() + (plot.width() * i / (n - 1) if n > 1 else plot.width() / 2)

    def mouseMoveEvent(self, e):
        n = len(self.labels)
        if n < 2:
            return
        plot = self._plot()
        x = e.position().x()
        i = round((x - plot.left()) / plot.width() * (n - 1))
        i = max(0, min(n - 1, i))
        if i != self.hover:
            self.hover = i
            self.update()

    def leaveEvent(self, e):
        self.hover = None
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        n = len(self.labels)
        plot = self._plot()
        if n < 2 or not self.series:
            p.setPen(QColor(T["muted"]))
            p.setFont(make_font(26, W_MED))
            p.drawText(QRectF(self.rect()), AL_C, self.empty_text)
            p.end()
            return
        lo, hi = self._yrange()
        ticks = [t for t in nice_ticks(lo, hi) if lo <= t <= hi] or [lo, hi]

        def y(v):
            return plot.bottom() - (v - lo) / (hi - lo) * plot.height()

        # bands (e.g. credit tiers, danger zone)
        for b0, b1, color, text in self.bands:
            top, bot = y(min(hi, b1)), y(max(lo, b0))
            if bot <= top:
                continue
            c = QColor(color)
            c.setAlpha(30)
            p.fillRect(QRectF(plot.left(), top, plot.width(), bot - top), c)
            if text and bot - top > 30:
                c.setAlpha(200)
                p.setPen(c)
                p.setFont(make_font(18, W_BOLD))
                p.drawText(QRectF(plot.right() - 260, top + 4, 250, 26),
                           Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop, text)
        # grid + y labels
        p.setFont(make_font(19, W_MED))
        for t in ticks:
            yy = y(t)
            p.setPen(QPen(QColor(T["border"]), 1.5))
            p.drawLine(QPointF(plot.left(), yy), QPointF(plot.right(), yy))
            p.setPen(QColor(T["muted"]))
            p.drawText(QRectF(0, yy - 14, self.L - 16, 28), AL_R, self.tick_fmt(t))
        if lo < 0 < hi:
            p.setPen(QPen(QColor(T["border_strong"]), 2, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(plot.left(), y(0)), QPointF(plot.right(), y(0)))
        # x labels (ages)
        p.setPen(QColor(T["muted"]))
        count = min(7, n)
        shown = set()
        for k in range(count):
            i = round(k * (n - 1) / (count - 1)) if count > 1 else 0
            if i in shown:
                continue
            shown.add(i)
            xx = self._x(i, plot, n)
            p.drawText(QRectF(xx - 70, plot.bottom() + 14, 140, 30), AL_C, self.labels[i])

        # series
        p.save()
        p.setClipRect(QRectF(plot.left() - 10, 0, plot.width() + 20, self.height()))
        for name, vals, color, filled in self.series:
            path = QPainterPath()
            for i, v in enumerate(vals):
                pt = QPointF(self._x(i, plot, n), y(v))
                if i == 0:
                    path.moveTo(pt)
                else:
                    path.lineTo(pt)
            if filled:
                area = QPainterPath(path)
                area.lineTo(QPointF(self._x(n - 1, plot, n), y(max(lo, 0) if lo < 0 < hi else lo)))
                area.lineTo(QPointF(self._x(0, plot, n), y(max(lo, 0) if lo < 0 < hi else lo)))
                area.closeSubpath()
                grad = QLinearGradient(0, plot.top(), 0, plot.bottom())
                c1, c2 = QColor(color), QColor(color)
                c1.setAlpha(90)
                c2.setAlpha(5)
                grad.setColorAt(0, c1)
                grad.setColorAt(1, c2)
                p.fillPath(area, QBrush(grad))
            p.setPen(QPen(QColor(color), 4.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)
        # markers on the first series
        if self.series:
            vals = self.series[0][1]
            for i, text, color in self.markers:
                if 0 <= i < n:
                    p.setPen(QPen(QColor(T["card"]), 3))
                    p.setBrush(QColor(color))
                    p.drawEllipse(QPointF(self._x(i, plot, n), y(vals[i])), 9, 9)
        p.restore()

        # hover crosshair + tooltip
        if self.hover is not None:
            i = self.hover
            xx = self._x(i, plot, n)
            p.setPen(QPen(QColor(T["text"]), 1.5, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(xx, plot.top()), QPointF(xx, plot.bottom()))
            rows = [(self.labels[i], T["text"], True)]
            for name, vals, color, _ in self.series:
                p.setPen(QPen(QColor(T["card"]), 3))
                p.setBrush(QColor(color))
                p.drawEllipse(QPointF(xx, y(vals[i])), 8, 8)
                rows.append((f"{name}: {self.fmt(vals[i])}", color, False))
            for mi, text, color in self.markers:
                if mi == i:
                    rows.append((text, color, False))
            f_b, f_n = make_font(21, W_BOLD), make_font(21, W_SEMI)
            w = max(QFontMetrics(f_b if b else f_n).horizontalAdvance(t) for t, _, b in rows) + 52
            h = 34 * len(rows) + 22
            bx = xx + 20 if xx + 20 + w < self.width() else xx - 20 - w
            by = max(4, min(self.height() - h - 4, plot.top() + 10))
            p.setPen(QPen(QColor(T["border_strong"]), 1.5))
            p.setBrush(QColor(T["modal"]))
            p.drawRoundedRect(QRectF(bx, by, w, h), 16, 16)
            for k, (t, color, bold) in enumerate(rows):
                ty = by + 12 + k * 34
                if not bold:
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(QColor(color))
                    p.drawEllipse(QPointF(bx + 22, ty + 17), 6, 6)
                p.setPen(QColor(T["text"]))
                p.setFont(f_b if bold else f_n)
                p.drawText(QRectF(bx + (16 if bold else 38), ty, w - 40, 34), AL_L, t)
        p.end()
