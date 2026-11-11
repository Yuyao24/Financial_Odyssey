"""Invest menu: put spare cash in the stock market or take it out, and retire early at $1M."""

from PyQt6.QtWidgets import QHBoxLayout

from ...formatting import money
from ..theme import W_BOLD, W_NORMAL, T
from ..widgets import AmountBox, Tile, WrapButton, label
from . import Menu


class InvestMenu(Menu):
    def __init__(self, ui, desktop):
        super().__init__(ui, desktop, "Invest", "Money you won't need for a while can grow in the stock market.")
        left, right = self.columns(11, 9)
        th, tp = (150, 42) if desktop else (124, 36)
        tiles = QHBoxLayout()
        tiles.setSpacing(18)
        self.t_inv = Tile("Invested", th, tp)
        self.t_cash = Tile("Cash", th, tp)
        self.t_nw = Tile("Net worth", th, tp)
        for t in (self.t_inv, self.t_cash, self.t_nw):
            tiles.addWidget(t, 1)
        left.addLayout(tiles)

        mc, ml = self.card("Buy or sell")
        self.amount = AmountBox(self.refresh, all_value=lambda: self.g.cash)
        ml.addWidget(self.amount)
        row = QHBoxLayout()
        row.setSpacing(16)
        self.b_invest = WrapButton("", "blue", 24, W_BOLD, height=100)
        self.b_withdraw = WrapButton("", "purple", 24, W_BOLD, height=100)
        self.b_invest.clicked.connect(lambda: ui.act("invest", lambda: ui.game.invest(self.amount.value())))
        self.b_withdraw.clicked.connect(lambda: ui.act("withdraw", lambda: ui.game.withdraw(self.amount.value())))
        row.addWidget(self.b_invest)
        row.addWidget(self.b_withdraw)
        ml.addLayout(row)
        self.hint = label("", 21, W_NORMAL, T["muted"], wrap=True)
        ml.addWidget(self.hint)
        left.addWidget(mc)

        self.retire_card, rl = self.card(None, "tint_green")
        fg = T["tints"]["green"][2]
        rl.addWidget(label("You're a millionaire!", 32, W_BOLD, fg))
        self.retire_text = label("", 22, W_NORMAL, fg, wrap=True)
        rl.addWidget(self.retire_text)
        rb = WrapButton("Retire early", "solid_green", 28, W_BOLD, height=96)
        rb.clicked.connect(ui.confirm_retire)
        rl.addWidget(rb)
        left.addWidget(self.retire_card)

        ic, il = self.card("How investing works")
        il.addWidget(label(
            "<b>Growth:</b> about 5–6% a year on average. Some quarters go down.<br><br>"
            "<b>Crashes:</b> roughly once every 20 years the market falls 10–22%. Staying invested through one "
            "earns an award.<br><br>"
            "<b>Withdrawing:</b> a 5% fee before age 60, free after. Keep an emergency fund in cash for rent "
            "and surprises.<br><br>"
            "<b>Debt first:</b> card interest is far higher than market returns, so pay the card before you invest.",
            22, W_NORMAL, T["text2"], wrap=True, rich=True))
        right.addWidget(ic)
        if desktop:
            left.addStretch(1)
            right.addStretch(1)
        else:
            self.lay.addStretch(1)

    def refresh(self):
        g = self.g
        amt = self.amount.value()
        self.t_inv.set(g.investments, T["blue"],
                       "No withdrawal fee (60+)" if g.withdraw_fee_rate() == 0 else "5% fee to withdraw before 60")
        self.t_cash.set(g.cash, T["red"] if g.cash < 0 else T["green"], "available to invest")
        nw = g.get_net_worth()
        self.t_nw.set(nw, T["text"] if nw >= 0 else T["red"], f"{money(g.MILLION - nw)} to $1M" if nw < g.MILLION
                      else "Retire any time")
        fee = int(min(amt, g.investments) * g.withdraw_fee_rate())
        self.b_invest.setText(f"Invest\n{money(amt)}")
        self.b_invest.setEnabled(0 < amt <= g.cash)
        self.b_withdraw.setText(f"Withdraw\n{money(min(amt, g.investments))}" + (f"  (−{money(fee)} fee)" if fee else ""))
        self.b_withdraw.setEnabled(g.investments > 0 and amt > 0)
        rent = g.essentials_total()
        if g.card > 0:
            self.hint.setText(f"You owe {money(g.card)} on your card at {g.card_rate():.2%} a quarter — paying that off "
                              "beats investing.")
        elif g.cash - amt < rent:
            self.hint.setText(f"Careful: keep at least {money(rent)} in cash for tonight's rent & bills.")
        else:
            self.hint.setText("Spare cash invested early has decades to grow.")
        self.retire_card.setVisible(g.can_retire_early())
        mult = g.credit_multiplier()
        self.retire_text.setText(f"Retire now: net worth {money(nw)} × {mult:.2f} credit multiplier = "
                                 f"{int(nw * mult):,} final score. Or keep going to grow it.")
