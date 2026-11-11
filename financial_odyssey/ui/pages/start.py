"""The start screen: resume a save or open a new credit card."""

from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from ...formatting import esc, money
from ..theme import W_BOLD, W_MED, W_NORMAL, W_SEMI, T
from ..widgets import Badge, Card, FitLabel, WrapButton, label


def hero_html(light, bold):
    return (f"<span style='font-weight:300'>{esc(light)} </span>"
            f"<span style='font-weight:700'>{esc(bold)}</span>")


class StartPage(QWidget):
    def __init__(self, ui, desktop):
        super().__init__()
        self.ui = ui
        g, win = ui.game, ui.win
        has_save = win.has_save

        top = QHBoxLayout()
        top.setSpacing(16)
        logo = Badge("FO", 24, 64)
        logo.set_style(T["primary"], T["primary_text"])
        logo.setFixedWidth(64)
        top.addWidget(logo)
        top.addWidget(label("Financial Odyssey", 28, W_SEMI))
        top.addStretch(1)
        settings = WrapButton("Settings", "accent", 25, W_BOLD, height=76, icon="gear")
        settings.setFixedWidth(220)
        settings.clicked.connect(ui.open_settings)
        top.addWidget(settings)
        quit_ = WrapButton("Quit", "red", 25, W_BOLD, height=76, icon="power")
        quit_.setFixedWidth(160)
        quit_.clicked.connect(win.close)
        top.addWidget(quit_)

        hero = label("<span style='font-weight:300'>Work, shop and </span><b>borrow</b>"
                     "<span style='font-weight:300'> your way from </span><b>18 to 65</b>",
                     104 if desktop else 84, W_NORMAL, wrap=True, rich=True)
        sub = label("Your first credit card was just approved. Live your life around town, build your credit, "
                    "keep your happiness up and retire without going broke.", 30, W_NORMAL, T["muted"], wrap=True)
        facts = label("47 years   ·   188 quarters   ·   6 places in town   ·   24 kinds of life events",
                      23, W_SEMI, T["dim"], wrap=True)

        rules = Card("card")
        rl = QVBoxLayout(rules)
        rl.setContentsMargins(40, 34, 40, 36)
        rl.setSpacing(18)
        rl.addWidget(label("How it works", 34, W_BOLD))
        for head, text in [
            ("Live day to day.", "Each quarter you get 12 weeks. Work at the Office, buy groceries, have fun at the "
             "Fun Park or study at the College — then sleep at Home."),
            ("Bills come due.", "Card and loan balances post a minimum payment. Pay it at the Bank before you sleep to "
             "grow your credit."),
            ("Happiness drains.", "Each quarter at 0 is a burnout warning; 4 and you die of depression."),
            ("Credit = cheaper life.", "Higher scores mean lower interest, bigger limits — even cheaper rent."),
            ("$1,000,000 net worth", "lets you retire early. Otherwise you retire at 65."),
        ]:
            rl.addWidget(label(f"<b>{esc(head)}</b> <span style='color:{T['muted']}'>{esc(text)}</span>",
                               25, W_NORMAL, wrap=True, rich=True))
        if not win.settings.get("tutorial_done"):
            rl.addWidget(label("New here? A short guided tutorial starts with your first game.",
                               24, W_SEMI, T["accent"], wrap=True))

        guide = WrapButton("Credit 101 — learn how credit works", "blue", 28, W_BOLD, height=100, icon="book")
        guide.clicked.connect(ui.show_guide)

        buttons = QVBoxLayout()
        buttons.setSpacing(18)
        save_card = None
        if has_save:
            sc = Card("tint_blue")
            sl = QVBoxLayout(sc)
            sl.setContentsMargins(36, 28, 36, 30)
            sl.setSpacing(6)
            fg = T["tints"]["blue"][2]
            sl.addWidget(label("SAVED GAME", 20, W_BOLD, fg))
            sl.addWidget(label(hero_html("Age", f"{g.age_years}  ·  Q{g.quarter()}"), 60, W_NORMAL, fg, rich=True))
            sl.addWidget(FitLabel(f"Net worth {money(g.get_net_worth())}   ·   Credit {g.credit_score}   ·   "
                                  f"Happiness {g.happiness}", 24, W_MED, fg))
            sl.addSpacing(10)
            resume = WrapButton("Resume journey", "primary", 34, W_BOLD, height=110, icon="play")
            resume.clicked.connect(ui.resume)
            sl.addWidget(resume)
            save_card = sc
            new = WrapButton("Start a new credit card", "outline", 27, W_SEMI, height=92)
            new.clicked.connect(ui.confirm_new_game)
            buttons.addWidget(new)
        else:
            begin = WrapButton("Begin your journey", "primary", 40, W_BOLD, height=124, icon="play")
            begin.clicked.connect(ui.new_game)
            buttons.addWidget(begin)
        buttons.addWidget(guide)

        if desktop:
            lay = QVBoxLayout(self)
            lay.setContentsMargins(140, 80, 140, 110)
            lay.setSpacing(0)
            lay.addLayout(top)
            lay.addSpacing(110)
            cols = QHBoxLayout()
            cols.setSpacing(140)
            left = QVBoxLayout()
            left.setSpacing(34)
            left.addWidget(hero)
            left.addWidget(sub)
            left.addWidget(facts)
            left.addSpacing(70)
            left.addLayout(buttons)
            left.addStretch(1)
            cols.addLayout(left, 12)
            right = QVBoxLayout()
            right.setSpacing(36)
            right.addWidget(rules)
            right.addStretch(1)
            if save_card is not None:
                right.addWidget(save_card)
            cols.addLayout(right, 10)
            lay.addLayout(cols, 1)
        else:
            lay = QVBoxLayout(self)
            lay.setContentsMargins(56, 48, 56, 60)
            lay.setSpacing(26)
            lay.addLayout(top)
            lay.addSpacing(16)
            lay.addWidget(hero)
            lay.addWidget(sub)
            lay.addWidget(facts)
            lay.addWidget(rules)
            lay.addStretch(1)
            if save_card is not None:
                lay.addWidget(save_card)
            lay.addLayout(buttons)
