"""Activity menu: what happened overnight, and the full log of everything you've done."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QScrollArea, QVBoxLayout, QWidget

from ...formatting import esc
from ..theme import W_NORMAL, T
from ..widgets import label
from . import Menu


def tone_col(tone):
    return {"good": T["green"], "bad": T["red"], "warn": T["amber"], "invest": T["blue"],
            "card": T["purple"], "gold": T["gold"]}.get(tone, T["text2"])


def log_html(entries):
    return "<br>".join(f"<span style='color:{T['dim']}'>{esc(lb)}</span>&nbsp;&nbsp;"
                       f"<span style='color:{tone_col(tone)}'>{esc(text)}</span>" for lb, text, tone in entries)


class ActivityMenu(Menu):
    def __init__(self, ui, desktop):
        super().__init__(ui, desktop, "Activity", "Every paycheck, purchase, bill and credit change, newest first.")
        left, right = self.columns(1, 1)
        nc, nl = self.card("Last night")
        self.night = label("", 22, W_NORMAL, wrap=True, rich=True)
        nl.addWidget(self.night)
        left.addWidget(nc)
        if desktop:
            left.addStretch(1)
        lc, ll = self.card("Full log")
        self.log = label("", 22, W_NORMAL, wrap=True, rich=True)
        self.log.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        holder = QWidget()
        hl = QVBoxLayout(holder)
        hl.setContentsMargins(0, 0, 14, 0)
        hl.addWidget(self.log)
        hl.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(holder)
        ll.addWidget(scroll, 1)
        right.addWidget(lc, 1)

    def refresh(self):
        g = self.g
        self.night.setText(log_html(g.night_report) if g.night_report else
                           f"<span style='color:{T['muted']}'>Nothing yet: go to sleep at Home to end your first "
                           "quarter.</span>")
        self.log.setText(log_html(reversed(g.log)))
