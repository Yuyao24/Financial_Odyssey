"""The status bar across the top of the game: age, free weeks, money, credit, happiness and
the Cash / Card switch that decides how town purchases are paid."""

from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from ..formatting import money
from .theme import W_BOLD, W_MED, W_SEMI, T, set_color
from .town import season_name
from .widgets import (
    Card,
    FitLabel,
    IconButton,
    SegmentBar,
    Segmented,
    Tile,
    label,
    score_color,
)


class Hud(Card):
    def __init__(self, ui, desktop):
        super().__init__("card")
        self.ui = ui
        self.desktop = desktop
        tile_h, tile_px = (132, 38) if desktop else (112, 32)
        self.t_cash = Tile("Cash", tile_h, tile_px)
        self.t_card = Tile("Credit card", tile_h, tile_px)
        self.t_credit = Tile("Credit score", tile_h, tile_px)
        self.t_happy = Tile("Happiness", tile_h, tile_px)
        self.t_nw = Tile("Net worth", tile_h, tile_px)
        self.age_lbl = label("", 54 if desktop else 46, rich=True)
        self.sub_lbl = label("", 21, W_MED, T["muted"])
        self.weeks_bar = SegmentBar(12, 30)
        self.weeks_lbl = FitLabel("", 21, W_SEMI, T["muted"])
        self.pay = Segmented([("Cash", "cash", "cash"), ("Card", "card", "card")], self._set_pay, 66, 22)
        self.pay.setFixedWidth(300)

        weeks = QVBoxLayout()
        weeks.setSpacing(8)
        weeks.addWidget(self.weeks_lbl)
        weeks.addWidget(self.weeks_bar)
        paybox = QVBoxLayout()
        paybox.setSpacing(6)
        paybox.addWidget(label("PAY WITH", 17, W_BOLD, T["dim"]))
        paybox.addWidget(self.pay)
        self.pay_box = QWidget()
        self.pay_box.setLayout(paybox)
        paybox.setContentsMargins(0, 0, 0, 0)

        if desktop:
            lay = QHBoxLayout(self)
            lay.setContentsMargins(40, 24, 40, 24)
            lay.setSpacing(24)
            info = QVBoxLayout()
            info.setSpacing(4)
            info.addWidget(self.age_lbl)
            info.addWidget(self.sub_lbl)
            info.addSpacing(6)
            info.addLayout(weeks)
            self.time_box = QWidget()
            self.time_box.setLayout(info)
            info.setContentsMargins(0, 0, 0, 0)
            self.time_box.setFixedWidth(470)
            lay.addWidget(self.time_box)
            for t in (self.t_cash, self.t_card, self.t_credit, self.t_happy, self.t_nw):
                lay.addWidget(t, 1)
            lay.addWidget(self.pay_box)
        else:
            lay = QVBoxLayout(self)
            lay.setContentsMargins(26, 18, 26, 20)
            lay.setSpacing(14)
            top = QHBoxLayout()
            top.setSpacing(16)
            tv = QVBoxLayout()
            tv.setSpacing(0)
            tv.addWidget(self.age_lbl)
            tv.addWidget(self.sub_lbl)
            top.addLayout(tv, 1)
            nv = QVBoxLayout()
            nv.setSpacing(0)
            self.nw_cap = label("Net worth", 20, W_MED, T["muted"], align=None)
            self.nw_val = FitLabel("", 40, W_BOLD)
            self.nw_val.setFixedWidth(250)
            nv.addWidget(self.nw_cap)
            nv.addWidget(self.nw_val)
            top.addLayout(nv)
            gear = IconButton("gear", 76)
            gear.clicked.connect(ui.open_settings)
            top.addWidget(gear)
            lay.addLayout(top)
            row = QHBoxLayout()
            row.setSpacing(12)
            for t in (self.t_cash, self.t_card, self.t_credit, self.t_happy):
                row.addWidget(t, 1)
            lay.addLayout(row)
            bottom = QHBoxLayout()
            bottom.setSpacing(24)
            self.time_box = QWidget()
            self.time_box.setLayout(weeks)
            weeks.setContentsMargins(0, 0, 0, 0)
            bottom.addWidget(self.time_box, 1)
            bottom.addWidget(self.pay_box)
            lay.addLayout(bottom)

    def _set_pay(self, method):
        g = self.ui.game
        if g.pay_method != method:
            self.ui.act("pay_card" if method == "card" else None, lambda: g.set_pay_method(method))

    def refresh(self):
        g = self.ui.game
        self.age_lbl.setText(f"<span style='font-weight:300'>Age </span><span style='font-weight:700'>{g.age_years}"
                             f"</span><span style='font-weight:300; color:{T['muted']}'>  ·  Q{g.quarter()}</span>")
        self.sub_lbl.setText(f"{season_name(g.quarter())}  ·  {65 - g.age_years} years to retirement  ·  "
                             f"Turn {g.turns_played}")
        left = g.weeks_left()
        self.weeks_lbl.setText(f"Free time: {left} of {g.WEEKS_PER_QTR} weeks left this quarter")
        self.weeks_bar.set_value(left / g.WEEKS_PER_QTR, T["seg_fill"] if left > 2 else T["amber"])

        od = g.overdraft_used()
        self.t_cash.set(g.cash, T["red"] if g.cash < 0 else T["green"],
                        f"Overdraft {money(od)}" if od else "in the bank", T["red"] if od else None)
        util = g.card / max(1, g.card_limit())
        self.t_card.set(g.card, T["purple"] if g.card <= g.card_limit() else T["red"],
                        f"{util:.0%} of {money(g.card_limit())}",
                        T["red"] if util > g.HIGH_UTILIZATION else (T["amber"] if util > 0.30 else None))
        self.t_credit.set(str(g.credit_score), score_color(g.credit_score), g.tier()[1])
        hcol = T["green"] if g.happiness > 50 else (T["amber"] if g.happiness > 25 else T["red"])
        burn = f"  ·  burnout {g.zero_happiness_turns}/{g.DEPRESSION_TURNS}" if g.zero_happiness_turns else ""
        self.t_happy.set(f"{g.happiness}/100", hcol, f"−{g.happiness_decay()} per quarter{burn}",
                         T["red"] if burn else None)
        nw = g.get_net_worth()
        self.t_nw.set(nw, T["text"] if nw >= 0 else T["red"], "cash + invested − debt")
        if not self.desktop:
            self.nw_val.setText(money(nw))
            set_color(self.nw_val, T["text"] if nw >= 0 else T["red"])
        self.pay.set_value(g.pay_method)
