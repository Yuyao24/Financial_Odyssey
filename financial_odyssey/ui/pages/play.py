"""The main game page: status bar, the town (or a menu), and the menu bar.

Mobile: status bar on top, content in the middle, a bottom menu bar.
Desktop: a menu sidebar on the left, status bar and content on the right.
"""

from PyQt6.QtWidgets import QHBoxLayout, QStackedWidget, QVBoxLayout, QWidget

from ..hud import Hud
from ..menus.activity import ActivityMenu
from ..menus.bank import BankMenu
from ..menus.credit import CreditMenu
from ..menus.invest import InvestMenu
from ..places import PlacePanel, place_badges
from ..theme import W_BOLD, W_MED, W_SEMI, T
from ..town import TownView
from ..widgets import Badge, Card, NavButton, WrapButton, label

NAV = [("town", "Town", "town"), ("bank", "Bank", "bank"), ("credit", "Credit", "gauge"),
       ("invest", "Invest", "growth"), ("activity", "Activity", "list"), ("insights", "Insights", "chart")]


class TownScreen(QWidget):
    def __init__(self, ui, desktop):
        super().__init__()
        self.ui = ui
        self.view = TownView(on_pick=lambda k: ui.play.visit(k))
        self.panel = PlacePanel(ui, desktop)
        if desktop:
            lay = QHBoxLayout(self)
            lay.setSpacing(36)
            lay.addWidget(self.view, 1)
            self.panel.setFixedWidth(880)
            lay.addWidget(self.panel)
        else:
            lay = QVBoxLayout(self)
            lay.setSpacing(16)
            self.view.setFixedHeight(690)
            lay.addWidget(self.view)
            lay.addWidget(self.panel, 1)
        lay.setContentsMargins(0, 0, 0, 0)


class PlayPage(QWidget):
    def __init__(self, ui, desktop):
        super().__init__()
        self.ui = ui
        self.desktop = desktop
        self.place = "home"
        self.menu = "town"
        self.hud = Hud(ui, desktop)
        self.town = TownScreen(ui, desktop)
        self.menus = {"town": self.town, "bank": BankMenu(ui, desktop), "credit": CreditMenu(ui, desktop),
                      "invest": InvestMenu(ui, desktop), "activity": ActivityMenu(ui, desktop)}
        self.stack = QStackedWidget()
        for w in self.menus.values():
            self.stack.addWidget(w)
        self.nav = {}
        for key, text, icon in NAV:
            b = NavButton(icon, text, not desktop, 124 if not desktop else 84)
            b.clicked.connect(lambda _=False, k=key: self.show_menu(k))
            self.nav[key] = b
        if desktop:
            self._build_desktop()
        else:
            self._build_mobile()
        self.town.panel.show_place(self.place)

    # -------------------------------------------------------------- layout --
    def _build_mobile(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 20)
        lay.setSpacing(18)
        lay.addWidget(self.hud)
        lay.addWidget(self.stack, 1)
        bar = QHBoxLayout()
        bar.setSpacing(10)
        for b in self.nav.values():
            bar.addWidget(b, 1)
        self.nav_box = QWidget()
        self.nav_box.setLayout(bar)
        bar.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.nav_box)

    def _build_desktop(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        side = QWidget()
        side.setFixedWidth(380)
        sv = QVBoxLayout(side)
        sv.setContentsMargins(44, 56, 36, 56)
        sv.setSpacing(14)
        brand = QHBoxLayout()
        brand.setSpacing(16)
        logo = Badge("FO", 24, 64)
        logo.set_style(T["primary"], T["primary_text"])
        logo.setFixedWidth(64)
        brand.addWidget(logo)
        brand.addWidget(label("Financial\nOdyssey", 26, W_BOLD))
        brand.addStretch(1)
        sv.addLayout(brand)
        sv.addSpacing(40)
        sv.addWidget(label("MENUS", 18, W_BOLD, T["dim"]))
        nav = QVBoxLayout()
        nav.setSpacing(12)
        for b in self.nav.values():
            nav.addWidget(b)
        self.nav_box = QWidget()
        self.nav_box.setLayout(nav)
        nav.setContentsMargins(0, 0, 0, 0)
        sv.addWidget(self.nav_box)
        sv.addStretch(1)
        self.tools_box = QWidget()
        tl = QVBoxLayout(self.tools_box)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(12)
        ui = self.ui
        theme_dark = ui.win.settings["theme"] == "dark"
        for text, variant, icon, fn in (
                ("Settings", "accent", "gear", ui.open_settings),
                ("Credit 101", "blue", "book", ui.show_guide),
                ("Light mode" if theme_dark else "Dark mode", "soft", "sun" if theme_dark else "moon",
                 lambda: ui.win.set_theme("light" if theme_dark else "dark", reopen=False)),
                ("Main menu", "outline", "home", ui.to_menu),
                ("Save & quit", "red", "power", ui.win.close)):
            b = WrapButton(text, variant, 23, W_SEMI, height=72, icon=icon)
            b.clicked.connect(fn)
            tl.addWidget(b)
        sv.addWidget(label("Progress saves automatically after every move.", 18, W_MED, T["muted"], wrap=True))
        sv.addWidget(self.tools_box)
        root.addWidget(side)
        div = Card("divider")
        div.setFixedWidth(2)
        root.addWidget(div)
        main = QVBoxLayout()
        main.setContentsMargins(56, 44, 64, 48)
        main.setSpacing(32)
        main.addWidget(self.hud)
        main.addWidget(self.stack, 1)
        root.addLayout(main, 1)

    # ---------------------------------------------------------- navigation --
    def show_menu(self, key):
        if key == "insights":
            self.ui.open_insights()
            self.ui.tut.notify("nav_insights")
            return
        self.menu = key
        self.stack.setCurrentWidget(self.menus[key])
        self.refresh()
        self.ui.tut.notify(f"nav_{key}")
        self.ui.tut.refresh()

    def visit(self, key):
        """Walk to a building and open its panel."""
        self.place = key
        self.town.panel.show_place(key)
        self.town.view.walk_to(key)
        self.refresh()
        self.ui.tut.notify(f"loc_{key}")
        self.ui.tut.refresh()

    def wake_up(self):
        """After sleeping: back home, looking at the town."""
        self.place = "home"
        self.menu = "town"
        self.stack.setCurrentWidget(self.town)
        self.town.panel.show_place("home")
        self.town.view.place_at("home")

    def refresh(self):
        ui, g = self.ui, self.ui.game
        self.hud.refresh()
        self.town.view.set_state(g.quarter(), ui.win.settings["theme"] == "dark", g.age_years, self.place,
                                 place_badges(g), bool(ui.win.settings.get("animations", True)))
        self.town.panel.refresh()
        current = self.menus[self.menu]
        if current is not self.town:
            current.refresh()
        for key, b in self.nav.items():
            b.set_state(key == self.menu, key == "bank" and g.remaining_due() > 0)
