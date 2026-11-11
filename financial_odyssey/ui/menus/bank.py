"""Bank menu: balances, this quarter's statement, paying debt and borrowing."""

from PyQt6.QtWidgets import QCheckBox, QGridLayout, QHBoxLayout

from ...formatting import money
from ..theme import W_BOLD, W_MED, W_NORMAL, W_SEMI, T, make_font, set_color
from ..widgets import AmountBox, Badge, Tile, WrapButton, label
from . import Menu


class BankMenu(Menu):
    def __init__(self, ui, desktop):
        super().__init__(ui, desktop, "Bank", "Your accounts, this quarter's bill, payments and loans.")
        left, right = self.columns(11, 9)
        th, tp = (150, 42) if desktop else (124, 36)
        tiles = QHBoxLayout()
        tiles.setSpacing(18)
        self.t_cash = Tile("Cash", th, tp)
        self.t_card = Tile("Credit card", th, tp)
        self.t_loan = Tile("Bank loans", th, tp)
        for t in (self.t_cash, self.t_card, self.t_loan):
            tiles.addWidget(t, 1)
        left.addLayout(tiles)

        self.bill, bl = self.card(None, "soft")
        top = QHBoxLayout()
        self.bill_cap = label("Minimum payment due this quarter", 22, W_SEMI, T["muted"])
        top.addWidget(self.bill_cap, 1)
        self.bill_chip = Badge("", 18, 40)
        top.addWidget(self.bill_chip)
        bl.addLayout(top)
        self.bill_val = label("", 44, W_BOLD)
        bl.addWidget(self.bill_val)
        self.bill_note = label("", 22, W_NORMAL, wrap=True)
        bl.addWidget(self.bill_note)
        self.autopay = QCheckBox("Charge rent && bills to my credit card (builds credit)")
        self.autopay.setFont(make_font(22, W_MED))
        self.autopay.toggled.connect(self._toggle_autopay)
        bl.addWidget(self.autopay)
        left.addWidget(self.bill)

        mv, ml = self.card("Make a payment or borrow")
        self.amount = AmountBox(self.refresh, all_value=lambda: self.g.cash)
        ml.addWidget(self.amount)
        grid = QGridLayout()
        grid.setSpacing(16)
        h = 96
        self.b_min = WrapButton("", "green", 23, W_BOLD, height=h)
        self.b_all = WrapButton("", "teal", 23, W_BOLD, height=h)
        self.b_pay = WrapButton("", "teal", 23, W_BOLD, height=h)
        self.b_loan = WrapButton("", "amber", 23, W_BOLD, height=h)
        self.b_min.clicked.connect(lambda: ui.act("pay_min", ui.game.pay_minimum))
        self.b_all.clicked.connect(lambda: ui.act("pay_card_all", ui.game.pay_card_all))
        self.b_pay.clicked.connect(lambda: ui.act("pay", lambda: ui.game.pay_debt(self.amount.value())))
        self.b_loan.clicked.connect(lambda: ui.act("borrow", lambda: ui.game.take_loan(self.amount.value())))
        for i, b in enumerate((self.b_min, self.b_all, self.b_pay, self.b_loan)):
            grid.addWidget(b, i // 2, i % 2)
        ml.addLayout(grid)
        ml.addWidget(label("Payments go to your highest-interest balance (the card) first.", 20, W_NORMAL,
                           T["muted"], wrap=True))
        left.addWidget(mv)

        info, il = self.card("How your bank works")
        self.info = label("", 22, W_NORMAL, T["text2"], wrap=True, rich=True)
        il.addWidget(self.info)
        right.addWidget(info)
        if desktop:
            left.addStretch(1)
            right.addStretch(1)
        else:
            self.lay.addStretch(1)

    def _toggle_autopay(self, on):
        g = self.g
        if g.essentials_on_card != on:
            g.essentials_on_card = on
            g.add_log("Rent & bills will now be charged to your card — pay the statement each quarter!"
                      if on else "Rent & bills will now be paid from cash", "card" if on else "info")
            self.ui.act("autopay" if on else None, lambda: (True, ""))

    def refresh(self):
        g = self.g
        amt = self.amount.value()
        od = g.overdraft_used()
        self.t_cash.set(g.cash, T["red"] if g.cash < 0 else T["green"],
                        f"Overdraft {money(od)} / {money(g.OVERDRAFT_LIMIT)}" if od else
                        f"Overdraft limit {money(g.OVERDRAFT_LIMIT)}", T["red"] if od else None)
        util = g.card / max(1, g.card_limit())
        self.t_card.set(g.card, T["purple"] if g.card <= g.card_limit() else T["red"],
                        f"{util:.0%} used  ·  {money(g.card_limit())} limit",
                        T["red"] if util > g.HIGH_UTILIZATION else (T["amber"] if util > 0.30 else None))
        cap = g.loan_capacity()
        self.t_loan.set(g.loans, T["amber"] if g.loans else T["dim"],
                        f"Can borrow {money(g.loan_room())}" if cap else "Loans need a 450+ score",
                        None if cap else T["red"])

        rem = g.remaining_due()
        if g.min_due <= 0 and g.payment_quality() == "full":
            self.bill.set_kind("tint_green")
            fg = muted = T["tints"]["green"][2]
            _, pts = g.projected_credit_change()
            self.bill_val.setText("Card paid off  ✓")
            self.bill_note.setText(f"You used your card and cleared it this quarter: credit {pts:+d} tonight, no "
                                   "interest.")
            self.bill_chip.setText("ON TIME")
            self.bill_chip.set_style(T["green"], T["solid_green_text"])
        elif g.min_due <= 0:
            self.bill.set_kind("soft")
            fg = muted = T["text"]
            muted = T["muted"]
            self.bill_val.setText("$0 — no bill")
            self.bill_note.setText("No card or loan balance on your last statement. Use your card and pay it back to "
                                   "build credit.")
            self.bill_chip.setText("NO BILL")
            self.bill_chip.set_tint("slate")
        elif rem <= 0:
            self.bill.set_kind("tint_green")
            fg = muted = T["tints"]["green"][2]
            self.bill_val.setText(f"{money(g.min_due)}  ✓ paid")
            q, pts = g.projected_credit_change()
            if q == "full":
                self.bill_note.setText(f"Paid in full: credit {pts:+d} tonight, and no card interest.")
            else:
                self.bill_note.setText(f"{g.QUALITY_LABEL[q].capitalize()}: credit {pts:+d}. Pay the full "
                                       f"{money(g.stmt_card)} statement for {g.full_payment_gain():+d} and no interest.")
            self.bill_chip.setText("ON TIME")
            self.bill_chip.set_style(T["green"], T["solid_green_text"])
        else:
            self.bill.set_kind("tint_red")
            fg = muted = T["tints"]["red"][2]
            self.bill_val.setText(f"{money(rem)} still due")
            self.bill_note.setText(f"Minimum {money(g.min_due)}, paid {money(g.paid_this_qtr)}. Sleeping now = "
                                   f"{'LATE (−20)' if g.paid_this_qtr else 'MISSED (−50)'}. "
                                   f"Pay in full: {g.full_payment_gain():+d}.")
            self.bill_chip.setText("UNPAID")
            self.bill_chip.set_style(T["red"], T["danger_text"])
        set_color(self.bill_val, fg)
        set_color(self.bill_note, muted)
        set_color(self.bill_cap, muted)
        self.autopay.setStyleSheet(f"QCheckBox {{ color:{fg}; }}")
        if self.autopay.isChecked() != g.essentials_on_card:
            self.autopay.blockSignals(True)
            self.autopay.setChecked(g.essentials_on_card)
            self.autopay.blockSignals(False)

        self.b_min.setText(f"Pay minimum\n{money(rem)}" if rem > 0 else "Minimum\ncovered")
        self.b_min.setEnabled(rem > 0 and g.cash > 0)
        self.b_all.setText(f"Pay off card\n{money(min(g.card, max(0, g.cash)))}")
        self.b_all.setEnabled(g.card > 0 and g.cash > 0)
        owed = g.card + g.loans
        self.b_pay.setText(f"Pay debt\n{money(min(amt, owed, max(0, g.cash)))}")
        self.b_pay.setEnabled(owed > 0 and g.cash > 0 and amt > 0)
        self.b_loan.setText(f"Borrow\n{money(amt)} @ {g.loan_rate():.2%}/qtr")
        self.b_loan.setEnabled(amt > 0 and g.loan_block_reason(amt) is None)
        self.b_loan.setToolTip(g.loan_block_reason(amt) or "")

        t = g.tier()
        self.info.setText(
            f"<b>Card:</b> {t[3]:.2%} interest per quarter on any balance you don't pay in full. Pay the whole "
            "statement and it's free (grace period).<br><br>"
            f"<b>Minimum payment:</b> {int(g.CARD_MIN_PCT * 100)}% of the card plus {int(g.LOAN_MIN_PCT * 100)}% of "
            "loans, due before you sleep. Late = −20 credit, missed = −50.<br><br>"
            f"<b>Loans:</b> {t[2]:.2%} per quarter, a {int(g.LOAN_ORIGINATION * 100)}% fee, and a "
            f"{g.LOAN_MIN_SCORE}+ score needed.<br><br>"
            f"<b>Overdraft:</b> cash can go to −{money(g.OVERDRAFT_LIMIT)}, for a {money(g.OVERDRAFT_FEE)} fee plus "
            f"{int(g.OVERDRAFT_RATE * 100)}% interest each quarter. Beyond that, bills go to your card, then to "
            "collections.")
