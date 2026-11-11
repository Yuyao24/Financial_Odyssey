"""Credit menu: the score gauge, what tonight's payment will do, the tier ladder and recent changes."""

import re

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGridLayout, QHBoxLayout

from ...formatting import esc, money
from ..theme import W_BOLD, W_MED, W_NORMAL, W_SEMI, T, set_color
from ..widgets import Badge, CreditGauge, WrapButton, label, score_color
from . import Menu

CREDIT_CHANGE = re.compile(r"Credit [+-]\d")
TIER_TINT = {"Excellent": "green", "Good": "teal", "Fair": "amber", "Poor": "amber", "Very Poor": "red"}


class CreditMenu(Menu):
    def __init__(self, ui, desktop):
        super().__init__(ui, desktop, "Credit", "Your score decides your interest rates, card limit, loans — "
                                                "even your rent.")
        left, right = self.columns(9, 11)
        gc, gl = self.card()
        top = QHBoxLayout()
        top.addWidget(label("Credit score", 30, W_BOLD), 1)
        self.tier_badge = Badge("", 18, 40)
        top.addWidget(self.tier_badge)
        gl.addLayout(top)
        self.gauge = CreditGauge()
        self.gauge.setFixedHeight(380 if desktop else 300)
        gl.addWidget(self.gauge)
        self.rates = label("", 23, W_SEMI, align=Qt.AlignmentFlag.AlignCenter)
        gl.addWidget(self.rates)
        self.notes = label("", 21, W_MED, T["muted"], wrap=True, align=Qt.AlignmentFlag.AlignCenter)
        gl.addWidget(self.notes)
        left.addWidget(gc)

        self.tonight, tl = self.card(None, "soft")
        tl.addWidget(label("IF YOU SLEEP NOW", 18, W_BOLD, T["dim"]))
        self.tonight_val = label("", 34, W_BOLD, wrap=True)
        self.tonight_note = label("", 21, W_NORMAL, T["text2"], wrap=True)
        tl.addWidget(self.tonight_val)
        tl.addWidget(self.tonight_note)
        left.addWidget(self.tonight)

        lc, ll = self.card("Credit tiers")
        self.ladder = QGridLayout()
        self.ladder.setHorizontalSpacing(18)
        self.ladder.setVerticalSpacing(6)
        heads = ["Tier", "Score", "Card rate", "Loan rate", "Card limit", "Rent & bills"]
        for c, h in enumerate(heads):
            self.ladder.addWidget(label(h, 18, W_BOLD, T["dim"]), 0, c)
        self.rows = []
        for r in range(5):
            cells = [label("", 22, W_SEMI) for _ in heads]
            for c, cell in enumerate(cells):
                self.ladder.addWidget(cell, r + 1, c)
            self.rows.append(cells)
        ll.addLayout(self.ladder)
        right.addWidget(lc)

        rc, rl = self.card("Recent credit changes")
        self.recent = label("", 21, W_NORMAL, T["text2"], wrap=True, rich=True)
        rl.addWidget(self.recent)
        guide = WrapButton("Credit 101 — the full guide", "blue", 24, W_BOLD, height=84, icon="book")
        guide.clicked.connect(ui.show_guide)
        rl.addWidget(guide)
        right.addWidget(rc)
        if desktop:
            left.addStretch(1)
            right.addStretch(1)
        else:
            self.lay.addStretch(1)

    def refresh(self):
        g = self.g
        t = g.tier()
        col = score_color(g.credit_score)
        self.gauge.set_score(g.credit_score, t[1], col)
        self.tier_badge.setText(t[1].upper())
        self.tier_badge.set_tint(TIER_TINT[t[1]])
        self.rates.setText(f"Loans {t[2]:.2%}/qtr  ·  Card {t[3]:.2%}/qtr")
        notes = []
        danger = g.low_credit_turns or g.credit_score < g.IRS_SCORE
        if g.history_capped():
            notes.append(f"Capped at 700 for {g.HISTORY_CAP_TURNS - g.turns_played} more quarters (short history)")
        if g.streak:
            notes.append(f"On-time streak: {g.streak}")
        if danger:
            notes.append(f"IRS RISK {g.low_credit_turns}/{g.IRS_TURNS}: pay on time to clear it")
        notes.append(f"Final-score multiplier ×{g.credit_multiplier():.2f}")
        self.notes.setText("  ·  ".join(notes))
        set_color(self.notes, T["red"] if danger else T["muted"])

        q = g.payment_quality()
        if q is None:
            self.tonight.set_kind("soft")
            self.tonight_val.setText("No change")
            self.tonight_note.setText("No bill this quarter. Put something on your card (switch Pay with: Card) and "
                                      "pay it back to start building credit.")
            fg = T["text"]
        elif q in ("late", "missing"):
            self.tonight.set_kind("tint_red")
            pts = -20 if q == "late" else -50
            self.tonight_val.setText(f"{pts:+d}  ({'late' if q == 'late' else 'missed'} payment)")
            self.tonight_note.setText(f"Pay {money(g.remaining_due())} more at the Bank to make it on time. Paying the "
                                      f"full statement would give {g.full_payment_gain():+d}.")
            fg = T["tints"]["red"][2]
        else:
            self.tonight.set_kind("tint_green")
            _, pts = g.projected_credit_change()
            self.tonight_val.setText(f"{pts:+d}  ({g.QUALITY_LABEL[q]})")
            self.tonight_note.setText("Paid in full: the best result, and no card interest." if q == "full" else
                                      f"Paying the full statement would give {g.full_payment_gain():+d} instead.")
            fg = T["tints"]["green"][2]
        set_color(self.tonight_val, fg)
        set_color(self.tonight_note, fg)

        for (score, name, lr, cr, lim, cap), cells in zip(g.TIERS, self.rows):
            mult = g.CREDIT_PRICING[name]
            vals = [name, f"{score}+", f"{cr:.2%}", f"{lr:.2%}", money(g.limit_for((score, name, lr, cr, lim, cap))),
                    f"{(mult - 1) * 100:+.0f}%"]
            current = name == t[1]
            for c, (cell, v) in enumerate(zip(cells, vals)):
                cell.setText(("▶ " if current and c == 0 else "") + v)
                set_color(cell, T["accent"] if current else (T["text"] if c == 0 else T["text2"]))
                cell.setFont(cell.font())

        lines = [(lb, text, tone) for lb, text, tone in reversed(g.log) if CREDIT_CHANGE.search(text)][:6]
        if lines:
            self.recent.setText("<br>".join(
                f"<span style='color:{T['dim']}'>{esc(lb)}</span>&nbsp; "
                f"<span style='color:{T['red'] if tone == 'bad' else T['text2']}'>{esc(text)}</span>"
                for lb, text, tone in lines))
        else:
            self.recent.setText(f"<span style='color:{T['muted']}'>No changes yet. Your score moves when a bill is "
                                "paid (or not) at the end of a quarter.</span>")

