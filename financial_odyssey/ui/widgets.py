"""Reusable painted widgets: labels, buttons, cards, icons, the credit gauge and more."""

import math

from PyQt6.QtCore import QPointF, QRect, QRectF, QSize, Qt
from PyQt6.QtGui import QColor, QFontMetrics, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..formatting import money
from .theme import AL_C, AL_L, W_BOLD, W_MED, W_NORMAL, W_SEMI, T, make_font, set_color


class WrapLabel(QLabel):
    """QLabel that never demands a wide minimum width when word-wrapping."""

    def minimumSizeHint(self):
        s = super().minimumSizeHint()
        return QSize(min(s.width(), 40), s.height()) if self.wordWrap() else s


def label(text="", px=24, weight=W_NORMAL, color=None, wrap=False, align=None, rich=False):
    lb = WrapLabel(text)
    lb.setFont(make_font(px, weight))
    set_color(lb, color or T["text"])
    lb.setWordWrap(wrap)
    lb.setTextFormat(Qt.TextFormat.RichText if rich else Qt.TextFormat.PlainText)
    if align is not None:
        lb.setAlignment(align)
    if wrap:
        lb.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
    return lb


def tone_color(tone):
    return {"info": T["text2"], "good": T["green"], "bad": T["red"], "warn": T["amber"],
            "card": T["purple"], "invest": T["blue"], "gold": T["gold"]}.get(tone, T["text"])


def score_color(score):
    if score >= 800:
        return T["green"]
    if score >= 700:
        return T["lime"]
    if score >= 600:
        return T["gold"]
    if score >= 450:
        return T["amber"]
    return T["red"]


def variant_fg(v):
    if v in T["tints"]:
        return T["tints"][v][2]
    return {"primary": T["primary_text"], "accent": T["accent_text"], "danger": T["danger_text"],
            "solid_green": T["solid_green_text"], "seg": T["muted"], "segon": T["primary_text"]}.get(v, T["text"])


def restyle(w):
    w.style().unpolish(w)
    w.style().polish(w)
    w.update()


# ------------------------------------------------------------------- icons --
def draw_icon(p, kind, rect, color):
    s = min(rect.width(), rect.height())
    c = rect.center()
    cx, cy = c.x(), c.y()
    pen = QPen(QColor(color), max(2.0, s * 0.09), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
               Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    if kind == "menu":
        for dy in (-0.18, 0.18):
            p.drawLine(QPointF(cx - s * 0.4, cy + s * dy), QPointF(cx + s * 0.4, cy + s * dy))
    elif kind == "close":
        d = s * 0.32
        p.drawLine(QPointF(cx - d, cy - d), QPointF(cx + d, cy + d))
        p.drawLine(QPointF(cx - d, cy + d), QPointF(cx + d, cy - d))
    elif kind == "gear":
        p.drawEllipse(QPointF(cx, cy), s * 0.15, s * 0.15)
        p.drawEllipse(QPointF(cx, cy), s * 0.32, s * 0.32)
        for i in range(8):
            a = math.radians(i * 45)
            p.drawLine(QPointF(cx + math.cos(a) * s * 0.36, cy + math.sin(a) * s * 0.36),
                       QPointF(cx + math.cos(a) * s * 0.48, cy + math.sin(a) * s * 0.48))
    elif kind == "book":
        w, h = s * 0.42, s * 0.40
        p.drawRoundedRect(QRectF(cx - w, cy - h, w * 2, h * 2), s * 0.06, s * 0.06)
        p.drawLine(QPointF(cx, cy - h), QPointF(cx, cy + h))
    elif kind == "power":
        r = s * 0.36
        p.drawArc(QRectF(cx - r, cy - r + s * 0.05, 2 * r, 2 * r), 125 * 16, 290 * 16)
        p.drawLine(QPointF(cx, cy - s * 0.42), QPointF(cx, cy - s * 0.02))
    elif kind == "sun":
        p.drawEllipse(QPointF(cx, cy), s * 0.18, s * 0.18)
        for i in range(8):
            a = math.radians(i * 45)
            p.drawLine(QPointF(cx + math.cos(a) * s * 0.30, cy + math.sin(a) * s * 0.30),
                       QPointF(cx + math.cos(a) * s * 0.44, cy + math.sin(a) * s * 0.44))
    elif kind == "moon":
        path = QPainterPath()
        path.addEllipse(QPointF(cx, cy), s * 0.38, s * 0.38)
        cut = QPainterPath()
        cut.addEllipse(QPointF(cx + s * 0.2, cy - s * 0.16), s * 0.32, s * 0.32)
        p.drawPath(path.subtracted(cut))
    elif kind == "home":
        p.drawPolyline([QPointF(cx - s * 0.4, cy - s * 0.02), QPointF(cx, cy - s * 0.4), QPointF(cx + s * 0.4, cy - s * 0.02)])
        p.drawPolyline([QPointF(cx - s * 0.28, cy - s * 0.12), QPointF(cx - s * 0.28, cy + s * 0.38),
                        QPointF(cx + s * 0.28, cy + s * 0.38), QPointF(cx + s * 0.28, cy - s * 0.12)])
    elif kind == "play":
        p.drawPolygon([QPointF(cx - s * 0.22, cy - s * 0.34), QPointF(cx + s * 0.34, cy), QPointF(cx - s * 0.22, cy + s * 0.34)])
    elif kind == "back":
        p.drawLine(QPointF(cx + s * 0.36, cy), QPointF(cx - s * 0.34, cy))
        p.drawPolyline([QPointF(cx - s * 0.04, cy - s * 0.3), QPointF(cx - s * 0.36, cy), QPointF(cx - s * 0.04, cy + s * 0.3)])
    elif kind == "chart":
        p.drawPolyline([QPointF(cx - s * 0.42, cy - s * 0.42), QPointF(cx - s * 0.42, cy + s * 0.4),
                        QPointF(cx + s * 0.44, cy + s * 0.4)])
        p.drawPolyline([QPointF(cx - s * 0.28, cy + s * 0.16), QPointF(cx - s * 0.06, cy - s * 0.06),
                        QPointF(cx + s * 0.1, cy + s * 0.08), QPointF(cx + s * 0.38, cy - s * 0.28)])
    elif kind == "trophy":
        p.drawArc(QRectF(cx - s * 0.3, cy - s * 0.46, s * 0.6, s * 0.7), 180 * 16, 180 * 16)
        p.drawLine(QPointF(cx - s * 0.3, cy - s * 0.11), QPointF(cx - s * 0.3, cy - s * 0.42))
        p.drawLine(QPointF(cx + s * 0.3, cy - s * 0.11), QPointF(cx + s * 0.3, cy - s * 0.42))
        p.drawLine(QPointF(cx - s * 0.3, cy - s * 0.42), QPointF(cx + s * 0.3, cy - s * 0.42))
        p.drawLine(QPointF(cx, cy + s * 0.24), QPointF(cx, cy + s * 0.38))
        p.drawLine(QPointF(cx - s * 0.22, cy + s * 0.42), QPointF(cx + s * 0.22, cy + s * 0.42))
    elif kind == "replay":
        r = s * 0.34
        p.drawArc(QRectF(cx - r, cy - r, 2 * r, 2 * r), 60 * 16, 290 * 16)
        p.drawPolyline([QPointF(cx + s * 0.06, cy - s * 0.46), QPointF(cx + s * 0.2, cy - s * 0.3), QPointF(cx + s * 0.02, cy - s * 0.2)])


class IconWidget(QWidget):
    def __init__(self, kind, size, color_fn):
        super().__init__()
        self.kind, self.color_fn = kind, color_fn
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        draw_icon(p, self.kind, QRectF(2, 2, self.width() - 4, self.height() - 4), self.color_fn())
        p.end()


class FitLabel(QLabel):
    """Single-line label that shrinks its font until the text fits its width."""

    def __init__(self, text="", px=32, weight=W_BOLD, color=None, min_px=12, align=AL_L):
        super().__init__()
        self._px, self._min, self._weight = px, min_px, weight
        self.setFont(make_font(px, weight))
        self.setAlignment(align)
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(int(px * 1.32))
        set_color(self, color or T["text"])
        self.setText(text)

    def setFixedWidth(self, w):
        # an 'Ignored' policy breaks box layouts when combined with a fixed width
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        super().setFixedWidth(w)

    def setText(self, text):
        super().setText(text)
        self._fit()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._fit()

    def _fit(self):
        text = self.text()
        avail = self.width() - 4 - self.contentsMargins().left() - self.contentsMargins().right()
        if avail <= 0:
            return
        px = self._px
        f = make_font(px, self._weight)
        while px > self._min and QFontMetrics(f).horizontalAdvance(text) > avail:
            px -= 1
            f.setPixelSize(px)
        if self.font().pixelSize() != px:
            self.setFont(f)


class Badge(FitLabel):
    """Flat, square-ish status tag. Deliberately NOT button-shaped (no pill, no edge)."""

    def __init__(self, text="", px=19, height=40):
        super().__init__(text, px, W_BOLD, align=AL_C)
        self.setFixedHeight(height)
        self._h = height
        self.setContentsMargins(14, 0, 14, 0)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        bg, _, fg = T["tints"]["slate"]
        self.set_style(bg, fg)

    def set_style(self, bg, fg):
        self.setStyleSheet(f"color:{fg}; background:{bg}; border-radius:10px;")

    def set_tint(self, tint):
        bg, _, fg = T["tints"][tint]
        self.set_style(bg, fg)

    def sizeHint(self):
        fm = QFontMetrics(make_font(self._px, self._weight))
        return QSize(fm.horizontalAdvance(self.text()) + 40, self._h)

    def minimumSizeHint(self):
        return QSize(min(self.sizeHint().width(), 80), self._h)


class WrapButton(QPushButton):
    """Clearly clickable button: raised edge, hover state, hand cursor. Text wraps/shrinks
    to always fit; optional painted icon."""

    def __init__(self, text="", variant="soft", px=24, weight=W_SEMI, height=None, pad=20, icon=None):
        super().__init__()
        self.setProperty("variant", variant)
        self._px, self._weight, self._pad = px, weight, pad
        self.icon_w = None
        if icon:
            lay = QHBoxLayout(self)
            lay.setContentsMargins(pad, 6, pad, 10)
            lay.setSpacing(int(px * 0.55))
            lay.addStretch(1)
            self.icon_w = IconWidget(icon, int(px * 1.15), self._icon_color)
            lay.addWidget(self.icon_w)
        else:
            lay = QVBoxLayout(self)
            lay.setContentsMargins(pad, 6, pad, 10)
        self.lbl = WrapLabel()
        self.lbl.setWordWrap(icon is None)
        self.lbl.setAlignment(AL_C)
        self.lbl.setTextFormat(Qt.TextFormat.PlainText)
        self.lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.lbl.setFont(make_font(px, weight))
        lay.addWidget(self.lbl)
        if icon:
            lay.addStretch(1)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if height:
            self.setFixedHeight(height)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._text = ""
        self.setText(text)

    def _icon_color(self):
        return variant_fg(self.property("variant")) if self.isEnabled() else T["disabled_text"]

    def setText(self, text):
        self._text = text
        self.lbl.setText(text)
        self._fit()

    def text(self):
        return self._text

    def set_variant(self, v):
        if self.property("variant") != v:
            self.setProperty("variant", v)
            restyle(self)
            restyle(self.lbl)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._fit()

    def _fit(self):
        icon_space = (self.icon_w.width() + int(self._px * 0.55)) if self.icon_w else 0
        w, h = self.width() - 2 * self._pad - icon_space - 4, self.height() - 18
        if w <= 0 or h <= 0:
            return
        px = self._px
        f = make_font(px, self._weight)
        flags = (int(Qt.TextFlag.TextWordWrap) if not self.icon_w else 0) | int(AL_C)
        while px > 12:
            fm = QFontMetrics(f)
            r = fm.boundingRect(QRect(0, 0, w, 10000), flags, self._text)
            longest = max((fm.horizontalAdvance(word) for word in self._text.split()), default=0)
            if r.height() <= h and longest <= w and r.width() <= w:
                break
            px -= 1
            f.setPixelSize(px)
        if self.lbl.font().pixelSize() != px:
            self.lbl.setFont(f)


class Card(QFrame):
    def __init__(self, name="card"):
        super().__init__()
        self.setObjectName(name)

    def set_kind(self, name):
        if self.objectName() != name:
            self.setObjectName(name)
            restyle(self)


class IconButton(QPushButton):
    """Round icon-only button (used for 'close')."""

    def __init__(self, kind, size=76):
        super().__init__()
        self.kind = kind
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("background:transparent; border:none;")

    def enterEvent(self, e):
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.update()
        super().leaveEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        s = self.width()
        hover = self.underMouse()
        p.setPen(QPen(QColor(T["text"] if hover else T["border_strong"]), 2.5))
        p.setBrush(QColor(T["surface"] if hover else T["card"]))
        p.drawEllipse(QRectF(2, 2, s - 4, s - 4))
        draw_icon(p, self.kind, QRectF(s * 0.32, s * 0.32, s * 0.36, s * 0.36), T["text"])
        p.end()


class SegmentBar(QWidget):
    """Row of rounded segments, filled / dashed-empty (like the usage meters in the examples)."""

    def __init__(self, segments=10, height=58):
        super().__init__()
        self.n, self.frac, self.color = segments, 0.0, T["seg_fill"]
        self.setFixedHeight(height)

    def set_value(self, frac, color):
        self.frac, self.color = max(0.0, min(1.0, frac)), color
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        gap = 8
        w = (self.width() - gap * (self.n - 1)) / self.n
        h = self.height()
        filled = math.ceil(self.frac * self.n - 1e-9) if self.frac > 0 else 0
        for i in range(self.n):
            r = QRectF(i * (w + gap) + 1, 1, w - 2, h - 2)
            rad = min(w, h) * 0.42
            if i < filled:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(self.color))
            else:
                p.setPen(QPen(QColor(T["border_strong"]), 2, Qt.PenStyle.DashLine))
                p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(r, rad, rad)
        p.end()


class CreditGauge(QWidget):
    def __init__(self):
        super().__init__()
        self.score, self.tier, self.color = 550, "Poor", T["amber"]
        self.setMinimumHeight(180)

    def set_score(self, score, tier, color):
        self.score, self.tier, self.color = score, tier, color
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        pen_w = max(18, int(min(w, h) * 0.10))
        r = min((w - pen_w * 2) / 2, (h - pen_w) / 1.52)
        cx = w / 2
        cy = (h - (1.5 * r + pen_w)) / 2 + pen_w / 2 + r
        rect = QRectF(cx - r, cy - r, 2 * r, 2 * r)
        p.setPen(QPen(QColor(T["track"]), pen_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(rect, 210 * 16, -240 * 16)
        p.setPen(QPen(QColor(T["border_strong"]), 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        for s in (300, 450, 600, 700, 800):
            ang = math.radians(210 - 240 * s / 1000)
            r1, r2 = r - pen_w / 2 - 8, r - pen_w / 2 - 18
            p.drawLine(QPointF(cx + r1 * math.cos(ang), cy - r1 * math.sin(ang)),
                       QPointF(cx + r2 * math.cos(ang), cy - r2 * math.sin(ang)))
        span = -240 * max(0.0, min(1.0, self.score / 1000))
        if span < 0:
            p.setPen(QPen(QColor(self.color), pen_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(rect, 210 * 16, int(span * 16))
        p.setPen(QColor(T["text"]))
        p.setFont(make_font(int(r * 0.56), W_BOLD))
        p.drawText(QRectF(cx - r, cy - r * 0.58, 2 * r, r * 0.66), AL_C, str(self.score))
        p.setPen(QColor(self.color))
        p.setFont(make_font(int(r * 0.19), W_BOLD))
        p.drawText(QRectF(cx - r, cy + r * 0.10, 2 * r, r * 0.30), AL_C, self.tier.upper())
        p.end()


def clear_layout(layout):
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w is not None:
            w.hide()
            w.setParent(None)               # detach now so nothing old is painted
            w.deleteLater()
        elif item.layout():
            clear_layout(item.layout())


class Tile(Card):
    def __init__(self, caption, height=118, value_px=40):
        super().__init__("tile")
        self.setFixedHeight(height)
        lay = QVBoxLayout(self)
        pad = 24 if height < 140 else 32
        lay.setContentsMargins(pad, 10 if height < 140 else 22, pad, 10 if height < 140 else 22)
        lay.setSpacing(2)
        self.cap = FitLabel(caption, 20, W_MED, T["muted"])
        self.val = FitLabel("", value_px, W_BOLD)
        self.sub = FitLabel("", 18, W_MED, T["muted"])
        lay.addWidget(self.cap)
        lay.addWidget(self.val)
        lay.addWidget(self.sub)

    def set(self, value, color, sub, sub_color=None):
        self.val.setText(money(value) if isinstance(value, (int, float)) else value)
        set_color(self.val, color)
        self.sub.setText(sub)
        set_color(self.sub, sub_color or T["muted"])
