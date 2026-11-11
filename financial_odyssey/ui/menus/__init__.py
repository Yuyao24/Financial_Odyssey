"""The menus reached from the nav bar: Bank, Credit, Invest and Activity."""

from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from ..theme import W_BOLD, W_NORMAL, T
from ..widgets import Card, label


class Menu(QWidget):
    """A menu screen: big title, one-line subtitle, then content."""

    def __init__(self, ui, desktop, title, subtitle):
        super().__init__()
        self.ui, self.desktop = ui, desktop
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(0, 4, 0, 0)
        self.lay.setSpacing(26 if desktop else 18)
        head = QVBoxLayout()
        head.setSpacing(2)
        head.addWidget(label(title, 56 if desktop else 50, W_BOLD))
        head.addWidget(label(subtitle, 23, W_NORMAL, T["muted"], wrap=True))
        self.lay.addLayout(head)

    @property
    def g(self):
        return self.ui.game

    def card(self, title=None, kind="card"):
        c = Card(kind)
        cl = QVBoxLayout(c)
        pad = 40 if self.desktop else 30
        cl.setContentsMargins(pad, pad - 6, pad, pad - 4)
        cl.setSpacing(16)
        if title:
            cl.addWidget(label(title, 30, W_BOLD))
        return c, cl

    def columns(self, *stretches):
        """Side by side on desktop, stacked on mobile. Returns one layout per column."""
        if self.desktop:
            row = QHBoxLayout()
            row.setSpacing(36)
            cols = []
            for s in stretches:
                v = QVBoxLayout()
                v.setSpacing(36)
                row.addLayout(v, s)
                cols.append(v)
            self.lay.addLayout(row, 1)
            return cols
        return [self.lay] * len(stretches)
