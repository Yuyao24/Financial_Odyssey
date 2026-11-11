"""The main dashboard where each quarter is played."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QHBoxLayout,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...formatting import esc, money
from ..theme import AL_C, AL_R, W_BOLD, W_MED, W_NORMAL, W_SEMI, T, make_font, set_color
from ..widgets import (
    Badge,
    Card,
    CreditGauge,
    FitLabel,
    SegmentBar,
    Tile,
    WrapButton,
    label,
    score_color,
    tone_color,
)


class Dashboard(QWidget):
    def __init__(self, ui, desktop):
        super().__init__()
        self.ui = ui
        self.desktop = desktop
        if desktop:
            self._build_desktop()
        else:
            self._build_mobile()

    # ------------------------------------------------------------- toolbar --
    def _toolbar(self, vertical):
        box = QVBoxLayout() if vertical else QHBoxLayout()
        box.setSpacing(16 if vertical else 12)
        h = 78 if vertical else 60
        px = 24 if vertical else 21
        self.settings_btn = WrapButton("Settings", "accent", px, W_BOLD, height=h, icon="gear")
        self.settings_btn.clicked.connect(self.ui.open_settings)
        self.guide_btn = WrapButton("Credit 101", "blue", px, W_BOLD, height=h, icon="book")
        self.guide_btn.clicked.connect(self.ui.show_guide)
        self.quit_btn = WrapButton("Save & quit", "red", px, W_BOLD, height=h, icon="power")
        self.quit_btn.clicked.connect(self.ui.win.close)
        self.stats_btn = WrapButton("Insights" if vertical else "Stats", "purple", px, W_BOLD, height=h, icon="chart")
        self.stats_btn.clicked.connect(lambda: self.ui.open_insights())
        return box, [self.settings_btn, self.guide_btn, self.quit_btn]

    def _build_mobile(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(36, 26, 36, 28)
        lay.setSpacing(14)

        hdr = Card("card")
        hdr.setFixedHeight(232)
        hv = QVBoxLayout(hdr)
        hv.setContentsMargins(26, 20, 26, 18)
        hv.setSpacing(12)
        tb, (s, gd, q) = self._toolbar(False)
        self.toolbar_box = QWidget()
        tl = QHBoxLayout(self.toolbar_box)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(12)
        s.setFixedWidth(196)
        gd.setFixedWidth(182)
        gd.setText("Guide")
        self.stats_btn.setFixedWidth(170)
        q.setFixedWidth(230)
        tl.addWidget(s)
        tl.addWidget(self.stats_btn)
        tl.addWidget(gd)
        tl.addStretch(1)
        tl.addWidget(q)
        hv.addWidget(self.toolbar_box)
        hv.addWidget(self._age_networth(52))
        lay.addWidget(hdr)

        row = QHBoxLayout()
        row.setSpacing(14)
        row.addWidget(self._credit_card(fixed=388), 1)
        row.addWidget(self._happy_card(fixed=388), 1)
        lay.addLayout(row)
        lay.addWidget(self._tiles(118, 40, 14))
        lay.addWidget(self._bills(150))
        lay.addWidget(self._actions(84))
        lay.addWidget(self._log(), 1)

        bottom = QHBoxLayout()
        bottom.setSpacing(14)
        self.retire_btn = WrapButton("Retire early", "solid_green", 30, W_BOLD, height=112)
        self.retire_btn.setFixedWidth(320)
        self.retire_btn.clicked.connect(self.ui.confirm_retire)
        bottom.addWidget(self.retire_btn)
        self.next_btn = WrapButton("Advance 3 months  →", "primary", 40, W_BOLD, height=112)
        self.next_btn.clicked.connect(self.ui.advance)
        bottom.addWidget(self.next_btn)
        lay.addLayout(bottom)

    def _build_desktop(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- sidebar ------------------------------------------------------
        side = QWidget()
        side.setFixedWidth(440)
        sv = QVBoxLayout(side)
        sv.setContentsMargins(64, 72, 48, 72)
        sv.setSpacing(18)
        brand = QHBoxLayout()
        brand.setSpacing(16)
        logo = Badge("FO", 24, 64)
        logo.set_style(T["primary"], T["primary_text"])
        logo.setFixedWidth(64)
        brand.addWidget(logo)
        brand.addWidget(label("Financial\nOdyssey", 26, W_BOLD))
        brand.addStretch(1)
        sv.addLayout(brand)
        sv.addSpacing(56)
        sv.addWidget(label("MENU", 18, W_BOLD, T["dim"]))
        tb, (s, gd, q) = self._toolbar(True)
        self.toolbar_box = QWidget()
        tl = QVBoxLayout(self.toolbar_box)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(16)
        tl.addWidget(s)
        tl.addWidget(self.stats_btn)
        tl.addWidget(gd)
        theme_dark = self.ui.win.settings["theme"] == "dark"
        self.theme_btn = WrapButton("Light mode" if theme_dark else "Dark mode", "soft", 24, W_SEMI,
                                    height=78, icon="sun" if theme_dark else "moon")
        self.theme_btn.clicked.connect(lambda: self.ui.win.set_theme("light" if theme_dark else "dark", reopen=False))
        tl.addWidget(self.theme_btn)
        sv.addWidget(self.toolbar_box)
        sv.addStretch(1)
        sv.addWidget(label("Progress saves automatically after every move.", 19, W_MED, T["muted"], wrap=True))
        menu = WrapButton("Main menu", "outline", 24, W_SEMI, height=78, icon="home")
        menu.clicked.connect(self.ui.to_menu)
        sv.addWidget(menu)
        sv.addWidget(q)
        root.addWidget(side)
        div = Card("divider")
        div.setFixedWidth(2)
        root.addWidget(div)

        # ---- main ------------------------------------------------------------
        main = QVBoxLayout()
        main.setContentsMargins(72, 64, 96, 72)
        main.setSpacing(44)
        top = QHBoxLayout()
        top.setSpacing(32)
        top.addWidget(self._age_networth(64, desktop=True), 1)
        self.retire_btn = WrapButton("Retire early", "solid_green", 28, W_BOLD, height=96)
        self.retire_btn.setFixedWidth(280)
        self.retire_btn.clicked.connect(self.ui.confirm_retire)
        top.addWidget(self.retire_btn)
        self.next_btn = WrapButton("Advance 3 months  →", "primary", 32, W_BOLD, height=96)
        self.next_btn.setFixedWidth(480)
        self.next_btn.clicked.connect(self.ui.advance)
        top.addWidget(self.next_btn)
        main.addLayout(top)

        cols = QHBoxLayout()
        cols.setSpacing(44)
        a = QVBoxLayout()
        a.setSpacing(44)
        ov = Card("card")
        ol = QVBoxLayout(ov)
        ol.setContentsMargins(40, 34, 40, 40)
        ol.setSpacing(24)
        ol.addWidget(label("Overview", 30, W_BOLD))
        ol.addWidget(self._tiles(150, 44, 24))
        a.addWidget(ov)
        a.addWidget(self._bills(196))
        a.addWidget(self._actions(88))
        a.addStretch(1)
        cols.addLayout(a, 11)
        b = QVBoxLayout()
        b.setSpacing(44)
        b.addWidget(self._credit_card(), 1)
        b.addWidget(self._happy_card(fixed=430))
        cols.addLayout(b, 6)
        cols.addWidget(self._log(), 5)
        main.addLayout(cols, 1)
        root.addLayout(main, 1)

    # ------------------------------------------------------------- sections --
    def _age_networth(self, px, desktop=False):
        w = QWidget()
        self.header_info = w
        hl = QHBoxLayout(w)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(20)
        left = QVBoxLayout()
        left.setSpacing(2)
        self.age_lbl = label("", px, W_NORMAL, rich=True)
        self.age_lbl.setFixedHeight(int(px * 1.3))
        self.sub_lbl = FitLabel("", 22, W_MED, T["muted"])
        left.addWidget(self.age_lbl)
        left.addWidget(self.sub_lbl)
        hl.addLayout(left, 1)
        right = QVBoxLayout()
        right.setSpacing(0)
        self.nw_cap = FitLabel("Net worth", 22, W_MED, T["muted"], align=AL_R)
        self.nw_lbl = FitLabel("", px, W_BOLD, align=AL_R)
        right.addWidget(self.nw_cap)
        right.addWidget(self.nw_lbl)
        rw = QWidget()
        rw.setLayout(right)
        right.setContentsMargins(0, 0, 0, 0)
        rw.setFixedWidth(460 if desktop else 380)
        hl.addWidget(rw)
        return w

    def _credit_card(self, fixed=None):
        cc = Card("card")
        self.credit_box = cc
        if fixed:
            cc.setFixedHeight(fixed)
        cl = QVBoxLayout(cc)
        pad = 40 if self.desktop else 28
        cl.setContentsMargins(pad, pad - 6, pad, pad - 8)
        cl.setSpacing(8)
        top = QHBoxLayout()
        top.addWidget(label("Credit score", 30, W_BOLD))
        top.addStretch(1)
        self.tier_badge = Badge("", 18, 38)
        top.addWidget(self.tier_badge)
        cl.addLayout(top)
        self.gauge = CreditGauge()
        if self.desktop:
            cl.addSpacing(10)
            cl.addWidget(self.gauge, 1)
        else:
            self.gauge.setFixedHeight(200)
            cl.addWidget(self.gauge)
        self.rates_lbl = FitLabel("", 21, W_SEMI, T["text2"], align=AL_C)
        cl.addWidget(self.rates_lbl)
        self.credit_note = label("", 19, W_MED, T["muted"], wrap=True, align=AL_C)
        cl.addWidget(self.credit_note)
        if not self.desktop:
            cl.addStretch(1)
        return cc

    def _happy_card(self, fixed):
        hc = Card("card")
        self.happy_box = hc
        hc.setFixedHeight(fixed)
        hl = QVBoxLayout(hc)
        pad = 40 if self.desktop else 28
        hl.setContentsMargins(pad, pad - 6, pad, pad - 6)
        hl.setSpacing(8 if not self.desktop else 14)
        top = QHBoxLayout()
        top.addWidget(label("Happiness", 30, W_BOLD))
        top.addStretch(1)
        self.decay_badge = Badge("", 18, 38)
        top.addWidget(self.decay_badge)
        hl.addLayout(top)
        self.happy_val = label("", 64, W_BOLD, rich=True)
        self.happy_val.setFixedHeight(80)
        hl.addWidget(self.happy_val)
        self.happy_bar = SegmentBar(10, 40)
        hl.addWidget(self.happy_bar)
        self.happy_note = label("", 19, W_MED, T["muted"], wrap=True)
        hl.addWidget(self.happy_note)
        hl.addStretch(1)
        self.buy_btn = WrapButton("", "pink", 23, W_BOLD, height=84)
        self.buy_btn.clicked.connect(lambda: self.ui.act("buy", self.ui.game.buy_happiness))
        hl.addWidget(self.buy_btn)
        return hc

    def _tiles(self, h, px, gap):
        w = QWidget()
        self.tiles_box = w
        grid = QGridLayout(w)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(gap)
        self.t_cash, self.t_inv, self.t_card = Tile("Cash", h, px), Tile("Investments", h, px), Tile("Credit card", h, px)
        self.t_loan, self.t_inc, self.t_ess = (Tile("Bank loans", h, px), Tile("Pay / quarter", h, px),
                                               Tile("Essentials / quarter", h, px))
        for i, t in enumerate([self.t_cash, self.t_inv, self.t_card, self.t_loan, self.t_inc, self.t_ess]):
            grid.addWidget(t, i // 3, i % 3)
        return w

    def _bills(self, h):
        self.bills = Card("soft")
        bc = self.bills
        bc.setFixedHeight(h)
        bl = QHBoxLayout(bc)
        pad = 40 if self.desktop else 28
        bl.setContentsMargins(pad, 16 if not self.desktop else 30, pad, 16 if not self.desktop else 30)
        bl.setSpacing(24)
        left = QVBoxLayout()
        left.setSpacing(2)
        self.due_cap = FitLabel("Minimum payment due this quarter", 21, W_SEMI, T["muted"])
        left.addWidget(self.due_cap)
        self.due_val = FitLabel("", 40, W_BOLD)
        left.addWidget(self.due_val)
        self.due_note = label("", 19, W_MED, T["muted"], wrap=True)
        left.addWidget(self.due_note)
        left.addStretch(1)
        bl.addLayout(left, 5)
        right = QVBoxLayout()
        right.setSpacing(14)
        tr = QHBoxLayout()
        tr.addStretch(1)
        self.due_chip = Badge("", 19, 40)
        tr.addWidget(self.due_chip)
        right.addLayout(tr)
        self.autopay = QCheckBox("Charge essentials to card (builds credit)")
        self.autopay.setFont(make_font(20, W_SEMI))
        self.autopay.setCursor(Qt.CursorShape.PointingHandCursor)
        self.autopay.toggled.connect(self._toggle_autopay)
        right.addWidget(self.autopay)
        right.addStretch(1)
        bl.addLayout(right, 3)
        return bc

    def _actions(self, h):
        ac = Card("card")
        al = QVBoxLayout(ac)
        pad = 40 if self.desktop else 28
        al.setContentsMargins(pad, pad - 8, pad, pad - 6)
        al.setSpacing(14 if not self.desktop else 20)
        top = QHBoxLayout()
        top.addWidget(label("Money moves", 30, W_BOLD))
        top.addStretch(1)
        top.addWidget(label("Payments go to your card first", 19, W_MED, T["muted"]))
        al.addLayout(top)
        self.amount_box = QWidget()
        arow = QHBoxLayout(self.amount_box)
        arow.setContentsMargins(0, 0, 0, 0)
        arow.setSpacing(10)
        arow.addWidget(label("Amount", 22, W_SEMI, T["muted"]))
        minus = WrapButton("−", "chip", 32, W_BOLD, height=62, pad=4)
        minus.setFixedWidth(66)
        minus.clicked.connect(lambda: self.amount.stepBy(-1))
        arow.addWidget(minus)
        self.amount = QSpinBox()
        self.amount.setRange(0, 10_000_000)
        self.amount.setSingleStep(100)
        self.amount.setValue(500)
        self.amount.setPrefix("$ ")
        self.amount.setGroupSeparatorShown(True)
        # NOTE: don't use NoButtons here - with a stylesheet Qt 6.12 collapses the text field;
        # the arrow buttons are hidden via the stylesheet instead.
        self.amount.setAlignment(AL_C)
        self.amount.setFont(make_font(28, W_BOLD))
        self.amount.setFixedSize(190, 62)
        self.amount.valueChanged.connect(lambda _: self.refresh())
        arow.addWidget(self.amount)
        plus = WrapButton("+", "chip", 32, W_BOLD, height=62, pad=4)
        plus.setFixedWidth(66)
        plus.clicked.connect(lambda: self.amount.stepBy(1))
        arow.addWidget(plus)
        for txt, val in (("$100", 100), ("$500", 500), ("$1k", 1000), ("$5k", 5000), ("All", None)):
            chip = WrapButton(txt, "chip", 21, W_SEMI, height=62, pad=4)
            chip.clicked.connect(lambda _=False, v=val: self._set_amount(v))
            arow.addWidget(chip)
        al.addWidget(self.amount_box)

        grid = QGridLayout()
        grid.setSpacing(12 if not self.desktop else 18)
        self.b_invest = WrapButton("", "blue", 22, W_BOLD, height=h)
        self.b_withdraw = WrapButton("", "purple", 22, W_BOLD, height=h)
        self.b_loan = WrapButton("", "amber", 22, W_BOLD, height=h)
        self.b_min = WrapButton("", "green", 22, W_BOLD, height=h)
        self.b_pay = WrapButton("", "teal", 22, W_BOLD, height=h)
        self.b_all = WrapButton("", "teal", 22, W_BOLD, height=h)
        ui = self.ui
        self.b_invest.clicked.connect(lambda: ui.act("invest", lambda: ui.game.invest(self.amount.value())))
        self.b_withdraw.clicked.connect(lambda: ui.act("withdraw", lambda: ui.game.withdraw(self.amount.value())))
        self.b_loan.clicked.connect(lambda: ui.act("borrow", lambda: ui.game.take_loan(self.amount.value())))
        self.b_pay.clicked.connect(lambda: ui.act("pay", lambda: ui.game.pay_debt(self.amount.value())))
        self.b_min.clicked.connect(lambda: ui.act("pay_min", ui.game.pay_minimum))
        self.b_all.clicked.connect(lambda: ui.act("pay_card_all", ui.game.pay_card_all))
        for i, b in enumerate([self.b_invest, self.b_withdraw, self.b_loan, self.b_min, self.b_pay, self.b_all]):
            grid.addWidget(b, i // 3, i % 3)
        al.addLayout(grid)
        return ac

    def _log(self):
        lc = Card("card")
        self.log_box = lc
        ll = QVBoxLayout(lc)
        pad = 40 if self.desktop else 28
        ll.setContentsMargins(pad, pad - 8, 18, pad - 10)
        ll.setSpacing(12)
        ll.addWidget(label("Activity", 30, W_BOLD))
        self.log_lbl = label("", 21, W_NORMAL, wrap=True, rich=True)
        self.log_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        holder = QWidget()
        hl = QVBoxLayout(holder)
        hl.setContentsMargins(0, 0, 12, 0)
        hl.addWidget(self.log_lbl)
        hl.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(holder)
        ll.addWidget(scroll)
        return lc

    # ---------------------------------------------------------------------------
    def _set_amount(self, v):
        g = self.ui.game
        self.amount.setValue(max(0, g.cash) if v is None else v)

    def _toggle_autopay(self, on):
        g = self.ui.game
        if g.essentials_on_card != on:
            g.essentials_on_card = on
            g.add_log("Essentials will now be charged to your card — pay the statement each quarter!"
                      if on else "Essentials will now be paid from cash", "card" if on else "info")
            self.ui.win.save_game()
            self.refresh()
            if on:
                self.ui.tut.notify("autopay")
                self.ui.tut.refresh()

    def refresh(self):
        g = self.ui.game
        amt = self.amount.value()

        self.age_lbl.setText(f"<span style='font-weight:300'>Age </span><span style='font-weight:700'>{g.age_years}</span>"
                             f"<span style='font-weight:300; color:{T['muted']}'>  ·  Q{g.quarter()}</span>")
        self.sub_lbl.setText(f"{65 - g.age_years} years to retirement  ·  Turn {g.turns_played}")
        nw = g.get_net_worth()
        self.nw_lbl.setText(money(nw))
        set_color(self.nw_lbl, T["text"] if nw >= 0 else T["red"])

        t = g.tier()
        col = score_color(g.credit_score)
        self.gauge.set_score(g.credit_score, t[1], col)
        self.tier_badge.setText(t[1].upper())
        self.tier_badge.set_tint({"Excellent": "green", "Good": "teal", "Fair": "amber",
                                  "Poor": "amber", "Very Poor": "red"}[t[1]])
        self.rates_lbl.setText(f"Loans {t[2]:.2%}/qtr  ·  Card {t[3]:.2%}/qtr")
        notes = []
        danger = g.low_credit_turns or g.credit_score < g.IRS_SCORE
        if g.history_capped():
            notes.append(f"History cap: max 700 for {g.HISTORY_CAP_TURNS - g.turns_played} more quarters")
        if g.streak:
            notes.append(f"On-time streak {g.streak}")
        if danger:
            notes.append(f"IRS RISK {g.low_credit_turns}/{g.IRS_TURNS}: pay on time to clear it")
        self.credit_note.setText("  ·  ".join(notes) if notes else "Pay your minimum each quarter to climb")
        set_color(self.credit_note, T["red"] if danger else T["muted"])

        hcol = T["seg_fill"] if g.happiness > 50 else (T["amber"] if g.happiness > 25 else T["red"])
        self.happy_val.setText(f"<span style='color:{T['text'] if g.happiness > 25 else T['red']}'>{g.happiness}</span>"
                               f"<span style='font-size:26px; font-weight:500; color:{T['muted']}'>  / 100</span>")
        self.happy_bar.set_value(g.happiness / 100, hcol)
        self.decay_badge.setText(f"−{g.happiness_decay()} / QTR")
        if g.zero_happiness_turns:
            self.happy_note.setText(f"BURNOUT WARNING {g.zero_happiness_turns}/{g.DEPRESSION_TURNS} — get happiness "
                                    f"above {g.HAPPY_RECOVER} to recover, 4 warnings is fatal.")
            set_color(self.happy_note, T["red"])
        else:
            self.happy_note.setText("Work & life stress drain it every quarter. 4 quarters at zero is fatal.")
            set_color(self.happy_note, T["muted"])
        cost = g.happiness_cost()
        self.buy_btn.setText(f"Buy leisure & hobbies\n−{money(cost)}  ·  +{g.HAPPY_PTS} happiness")
        self.buy_btn.setEnabled(g.cash >= cost and g.happiness < 100)

        od = g.overdraft_used()
        self.t_cash.set(g.cash, T["red"] if g.cash < 0 else T["green"],
                        f"Overdraft {money(od)} / {money(g.OVERDRAFT_LIMIT)}" if od else
                        f"Overdraft limit {money(g.OVERDRAFT_LIMIT)}", T["red"] if od else None)
        self.t_inv.set(g.investments, T["blue"],
                       "No withdrawal fee (60+)" if g.withdraw_fee_rate() == 0 else "5% fee to withdraw before 60")
        util = g.card / max(1, g.card_limit())
        self.t_card.set(g.card, T["purple"] if g.card <= g.card_limit() else T["red"],
                        f"{util:.0%} used  ·  {money(g.card_limit())} limit",
                        T["red"] if util > g.HIGH_UTILIZATION else (T["amber"] if util > 0.30 else None))
        cap = g.loan_capacity()
        self.t_loan.set(g.loans, T["amber"] if g.loans else T["dim"],
                        f"Can borrow {money(g.loan_room())}" if cap else "Loans need a 450+ score",
                        None if cap else T["red"])
        inc_sub = f"Certifications {g.courses_taken}/{g.MAX_COURSES}"
        if g.layoff_turns:
            inc_sub = f"{int(g.layoff_mult * 100)}% pay for {g.layoff_turns} more qtr"
        elif not g.has_car:
            inc_sub += "  ·  no car −10%"
        self.t_inc.set(g.quarterly_income(), T["gold"], inc_sub, T["amber"] if g.layoff_turns else None)
        items = g.essentials_breakdown()
        adj = dict(items).get("Credit premium", 0) or dict(items).get("Credit discount", 0)
        self.t_ess.set(g.essentials_total(), T["pink"],
                       (f"Incl. credit {'premium +' if adj > 0 else 'discount −'}{money(abs(adj))}" if adj
                        else "Rent, food & bills — compulsory"),
                       T["red"] if adj > 0 else (T["green"] if adj < 0 else None))
        self.t_ess.setToolTip("\n".join(f"{n}: {money(v)}" for n, v in items))

        rem = g.remaining_due()
        if g.min_due <= 0:
            self.bills.set_kind("soft")
            fg = T["text"]
            muted = T["muted"]
            self.due_val.setText("$0 — no bill")
            self.due_note.setText("No card or loan balance on your last statement. Use your card and pay it back "
                                  "to build credit.")
            self.due_chip.setText("NO BILL")
            self.due_chip.set_tint("slate")
        elif rem <= 0:
            self.bills.set_kind("tint_green")
            fg = muted = T["tints"]["green"][2]
            self.due_val.setText(f"{money(g.min_due)}  ✓ paid")
            q, pts = g.projected_credit_change()
            if q == "full":
                extra = f"Paid in full: credit {pts:+d}, no card interest."
            else:
                extra = (f"{g.QUALITY_LABEL[q].capitalize()}: credit {pts:+d}. Pay the full {money(g.stmt_card)} "
                         f"statement for {g.full_payment_gain():+d} and no interest.")
            self.due_note.setText(extra)
            self.due_chip.setText("ON TIME")
            self.due_chip.set_style(T["green"], T["solid_green_text"])
        else:
            self.bills.set_kind("tint_red")
            fg = muted = T["tints"]["red"][2]
            self.due_val.setText(f"{money(rem)} still due")
            self.due_note.setText(f"Minimum {money(g.min_due)}, paid {money(g.paid_this_qtr)}. Advancing now = "
                                  f"{'LATE (−20)' if g.paid_this_qtr else 'MISSED (−50)'}. "
                                  f"Pay in full: {g.full_payment_gain():+d}.")
            self.due_chip.setText("UNPAID")
            self.due_chip.set_style(T["red"], T["danger_text"])
        set_color(self.due_val, fg)
        set_color(self.due_note, muted)
        set_color(self.due_cap, muted)
        self.autopay.setStyleSheet(f"QCheckBox {{ color:{fg}; }}")
        if self.autopay.isChecked() != g.essentials_on_card:
            self.autopay.blockSignals(True)
            self.autopay.setChecked(g.essentials_on_card)
            self.autopay.blockSignals(False)

        fee = int(min(amt, g.investments) * g.withdraw_fee_rate())
        self.b_invest.setText(f"Invest\n{money(amt)}")
        self.b_invest.setEnabled(0 < amt <= g.cash)
        self.b_withdraw.setText(f"Withdraw\n{money(min(amt, g.investments))}" + (f" (−{money(fee)} fee)" if fee else ""))
        self.b_withdraw.setEnabled(g.investments > 0 and amt > 0)
        self.b_loan.setText(f"Borrow\n{money(amt)} @ {g.loan_rate():.2%}")
        lr = g.loan_block_reason(amt)
        self.b_loan.setEnabled(amt > 0 and lr is None)
        self.b_loan.setToolTip(lr or "2% origination fee is added to the loan")
        owed = g.card + g.loans
        self.b_pay.setText(f"Pay debt\n{money(min(amt, owed))}")
        self.b_pay.setEnabled(owed > 0 and g.cash > 0 and amt > 0)
        self.b_min.setText(f"Pay minimum\n{money(rem)}" if rem else "Minimum\ncovered")
        self.b_min.setEnabled(rem > 0 and g.cash > 0)
        self.b_all.setText(f"Pay off card\n{money(g.card)}")
        self.b_all.setEnabled(g.card > 0 and g.cash > 0)

        lines = []
        for when, text, tone in reversed(g.log[-60:]):
            lines.append(f"<span style='color:{T['dim']}'>{esc(when)}</span>&nbsp;&nbsp;"
                         f"<span style='color:{tone_color(tone)}'>{esc(text)}</span>")
        self.log_lbl.setText("<br>".join(lines))

        self.retire_btn.setVisible(g.get_net_worth() >= g.MILLION)
        self.next_btn.setEnabled(g.state == "main")
