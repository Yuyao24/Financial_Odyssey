"""The end-of-game screen with the final score breakdown."""

from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from ...formatting import esc, money
from ..theme import AL_R, W_BOLD, W_MED, W_NORMAL, W_SEMI, T, set_color
from ..widgets import Badge, Card, FitLabel, WrapButton, label, score_color


class GameOverPage(QWidget):
    def __init__(self, ui, desktop):
        super().__init__()
        self.ui = ui
        self.title = label("", 96 if desktop else 84, W_NORMAL, wrap=True, rich=True)
        self.sub = label("", 30, W_NORMAL, T["muted"], wrap=True)
        self.badge = Badge("", 20, 44)
        top = QHBoxLayout()
        top.addWidget(self.badge)
        top.addStretch(1)

        self.card = Card("card")
        cl = QVBoxLayout(self.card)
        cl.setContentsMargins(44, 34, 44, 34)
        cl.setSpacing(8 if desktop else 6)
        cl.addWidget(label("Your life in numbers", 32, W_BOLD))
        cl.addSpacing(6)
        self.rows = []
        for _ in range(11):
            r = QHBoxLayout()
            a = FitLabel("", 26, W_MED, T["muted"])
            b = FitLabel("", 30, W_BOLD, align=AL_R)
            r.addWidget(a, 3)
            r.addWidget(b, 2)
            cl.addLayout(r)
            self.rows.append((a, b))

        score_card = Card("tint_blue")
        sl = QVBoxLayout(score_card)
        sl.setContentsMargins(40, 28, 40, 30)
        fg = T["tints"]["blue"][2]
        sl.addWidget(FitLabel("FINAL SCORE", 22, W_BOLD, fg))
        self.score = FitLabel("", 96, W_BOLD, fg)
        sl.addWidget(self.score)
        self.ach = label("", 23, W_NORMAL, T["text2"], wrap=True, rich=True)

        guide_btn = WrapButton("View Credit 101 Guide", "blue", 26, W_BOLD, height=88, icon="book")
        guide_btn.clicked.connect(ui.show_guide)

        again = WrapButton("Play again — new credit card", "primary", 36, W_BOLD, height=116, icon="play")
        again.clicked.connect(ui.new_game)
        row = QHBoxLayout()
        row.setSpacing(16)
        menu = WrapButton("Main menu", "outline", 26, W_SEMI, height=88, icon="home")
        menu.clicked.connect(ui.to_menu)
        charts = WrapButton("Life in charts", "purple", 26, W_BOLD, height=88, icon="chart")
        charts.clicked.connect(lambda: ui.open_insights())
        quit_ = WrapButton("Quit", "red", 26, W_BOLD, height=88, icon="power")
        quit_.clicked.connect(ui.win.close)
        row.addWidget(charts)
        row.addWidget(menu)
        row.addWidget(quit_)

        if desktop:
            lay = QHBoxLayout(self)
            lay.setContentsMargins(160, 110, 160, 110)
            lay.setSpacing(140)
            left = QVBoxLayout()
            left.setSpacing(30)
            left.addLayout(top)
            left.addWidget(self.title)
            left.addWidget(self.sub)
            left.addWidget(score_card)
            left.addWidget(self.ach)
            left.addWidget(guide_btn)
            left.addStretch(1)
            left.addWidget(again)
            left.addLayout(row)
            lay.addLayout(left, 1)
            right = QVBoxLayout()
            right.addWidget(self.card)
            right.addStretch(1)
            lay.addLayout(right, 1)
        else:
            lay = QVBoxLayout(self)
            lay.setContentsMargins(56, 70, 56, 60)
            lay.setSpacing(22)
            lay.addLayout(top)
            lay.addWidget(self.title)
            lay.addWidget(self.sub)
            lay.addWidget(score_card)
            lay.addWidget(self.card)
            lay.addWidget(self.ach)
            lay.addWidget(guide_btn)
            lay.addStretch(1)
            lay.addWidget(again)
            lay.addLayout(row)

    def show_game(self, g):
        r = g.end_reason
        good = r in ("RETIREMENT", "EARLY_RETIREMENT")
        if good:
            self.title.setText("<span style='font-weight:300'>You </span><b>retired.</b>")
            self.badge.setText("EARLY RETIREMENT" if r == "EARLY_RETIREMENT" else "AGE 65")
            self.badge.set_tint("green")
            self.sub.setText("You retired early as a millionaire!" if r == "EARLY_RETIREMENT"
                             else "You made it to 65 and retired.")
        elif r == "IRS_SEIZURE":
            self.title.setText("<span style='font-weight:300'>Assets </span><b>seized.</b>")
            self.badge.setText("GAME OVER")
            self.badge.set_tint("red")
            self.sub.setText("You kept missing payments with a credit score under 300, and the IRS took everything.")
        else:
            self.title.setText("<span style='font-weight:300'>Lost to </span><b>depression.</b>")
            self.badge.setText("GAME OVER")
            self.badge.set_tint("red")
            if g.low_credit_turns > 0:
                self.sub.setText("Burnout at zero happiness while facing IRS seizure warnings — the full IRS "
                                 "penalty applies.")
            else:
                self.sub.setText("Four quarters of burnout at zero happiness. Money matters — but so does living.")
        nw = g.get_net_worth()
        raw_score = g.raw_score()
        mult = f"×{g.credit_multiplier():.2f}"
        data = [
            ("Age reached", str(g.age_years), T["text"]),
            ("Net worth", money(nw), T["green"] if nw >= 0 else T["red"]),
            ("Credit score", f"{g.credit_score} ({g.tier()[1]})", score_color(g.credit_score)),
            ("Investments", money(g.investments), T["blue"]),
            ("Debt remaining", money(g.card + g.loans + g.overdraft_used()), T["red"] if g.total_debt() else T["dim"]),
            ("Lifetime interest paid", money(g.stats["interest"]), T["red"]),
            ("Lifetime fees paid", money(g.stats["fees"]), T["red"]),
            ("Payments on time / late / missed", f"{g.stats['on_time']} / {g.stats['late']} / {g.stats['missed']}", T["text"]),
            ("Credit multiplier", mult, T["gold"]),
            ("Score before penalty" if not good else "Net worth × multiplier", f"{raw_score:,} pts",
             T["teal"] if good else T["amber"]),
        ]
        if not good:
            data.append(("Death penalty applied", f"−{money(g.death_penalty_amount())}", T["red"]))
        for i, (a, b) in enumerate(self.rows):
            used = i < len(data)
            a.setVisible(used)
            b.setVisible(used)
            if used:
                k, v, c = data[i]
                a.setText(k)
                b.setText(v)
                set_color(b, c)
        self.score.setText(f"{g.final_score():,}")
        if g.achievements:
            names = "  ·  ".join(esc(g.ACHIEVEMENTS[k][0]) for k in g.achievements)
            self.ach.setText(f"<b>Achievements {len(g.achievements)}/{len(g.ACHIEVEMENTS)}</b><br>{names}")
        else:
            self.ach.setText("No achievements this time.")
