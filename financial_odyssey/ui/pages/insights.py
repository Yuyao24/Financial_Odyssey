""""Your life in charts": summary tiles, chart tabs and the awards grid."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ...formatting import esc, money
from ..charts import LineChart
from ..theme import W_BOLD, W_MED, W_NORMAL, W_SEMI, T
from ..widgets import (
    Card,
    FitLabel,
    IconWidget,
    Tile,
    WrapButton,
    clear_layout,
    label,
    score_color,
    tone_color,
)


class InsightsPage(QWidget):
    """Charts of your whole financial life, key moments and achievements."""

    TABS = [("Net worth", "nw"), ("Credit", "credit"), ("Money", "money"), ("Happiness", "happy"),
            ("Awards", "awards")]

    def __init__(self, ui, desktop):
        super().__init__()
        self.ui = ui
        self.desktop = desktop
        self.tab = "nw"

        top = QHBoxLayout()
        top.setSpacing(20)
        self.back_btn = WrapButton("Back", "outline", 24, W_SEMI, height=72, icon="back")
        self.back_btn.setFixedWidth(200)
        self.back_btn.clicked.connect(ui.close_insights)
        top.addWidget(self.back_btn)
        titles = QVBoxLayout()
        titles.setSpacing(0)
        titles.addWidget(label("<span style='font-weight:300'>Your life </span><b>in charts</b>", 52, W_NORMAL, rich=True))
        self.subtitle = FitLabel("", 22, W_MED, T["muted"])
        titles.addWidget(self.subtitle)
        top.addLayout(titles, 1)

        # summary tiles
        tile_h, tile_px = (150, 42) if desktop else (118, 36)
        self.s_nw, self.s_peak, self.s_credit = Tile("Net worth", tile_h, tile_px), Tile("Peak net worth", tile_h, tile_px), Tile("Credit score", tile_h, tile_px)
        self.s_ontime, self.s_interest, self.s_fees = Tile("On-time payments", tile_h, tile_px), Tile("Interest paid", tile_h, tile_px), Tile("Fees paid", tile_h, tile_px)
        tiles = QWidget()
        grid = QGridLayout(tiles)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(24 if desktop else 14)
        cols = 2 if desktop else 3
        for i, t in enumerate([self.s_nw, self.s_peak, self.s_credit, self.s_ontime, self.s_interest, self.s_fees]):
            grid.addWidget(t, i // cols, i % cols)

        # tabs
        self.tabwrap = Card("segwrap")
        self.tabwrap.setFixedHeight(84)
        tl = QHBoxLayout(self.tabwrap)
        tl.setContentsMargins(8, 8, 8, 8)
        tl.setSpacing(6)
        self.tab_btns = {}
        for text, key in self.TABS:
            b = WrapButton(text, "seg", 22, W_SEMI, height=68)
            b.clicked.connect(lambda _=False, k=key: self.set_tab(k))
            tl.addWidget(b)
            self.tab_btns[key] = b

        # chart card / awards card (stacked)
        self.content = QStackedWidget()
        chart_card = Card("card")
        cl = QVBoxLayout(chart_card)
        cl.setContentsMargins(36, 30, 36, 30)
        cl.setSpacing(10)
        self.chart_title = label("", 34, W_BOLD)
        self.chart_desc = label("", 22, W_NORMAL, T["muted"], wrap=True)
        self.legend = QHBoxLayout()
        self.legend.setSpacing(24)
        cl.addWidget(self.chart_title)
        cl.addWidget(self.chart_desc)
        cl.addLayout(self.legend)
        self.chart = LineChart()
        cl.addWidget(self.chart, 1)
        cl.addWidget(label("Hover over the chart to see each quarter. Dots mark key moments.", 19, W_MED, T["dim"]))
        self.content.addWidget(chart_card)

        awards_card = Card("card")
        al = QVBoxLayout(awards_card)
        al.setContentsMargins(36, 30, 36, 30)
        al.setSpacing(16)
        self.awards_title = label("", 34, W_BOLD)
        al.addWidget(self.awards_title)
        grid_holder = QWidget()
        self.awards_grid = QGridLayout(grid_holder)
        self.awards_grid.setContentsMargins(0, 0, 14, 0)
        self.awards_grid.setSpacing(16)
        self.awards_grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        ascroll = QScrollArea()
        ascroll.setWidgetResizable(True)
        ascroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        ascroll.setWidget(grid_holder)
        al.addWidget(ascroll, 1)
        self.content.addWidget(awards_card)

        # key moments timeline
        mc = Card("card")
        ml = QVBoxLayout(mc)
        ml.setContentsMargins(36, 28, 20, 24)
        ml.setSpacing(10)
        ml.addWidget(label("Key moments", 30, W_BOLD))
        self.moments_lbl = label("", 22, W_NORMAL, wrap=True, rich=True)
        self.moments_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        holder = QWidget()
        hl = QVBoxLayout(holder)
        hl.setContentsMargins(0, 0, 14, 0)
        hl.addWidget(self.moments_lbl)
        hl.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(holder)
        ml.addWidget(scroll)

        if desktop:
            lay = QVBoxLayout(self)
            lay.setContentsMargins(96, 72, 96, 80)
            lay.setSpacing(44)
            lay.addLayout(top)
            cols_l = QHBoxLayout()
            cols_l.setSpacing(44)
            left = QVBoxLayout()
            left.setSpacing(44)
            left.addWidget(tiles)
            left.addWidget(mc, 1)
            lw = QWidget()
            lw.setLayout(left)
            left.setContentsMargins(0, 0, 0, 0)
            lw.setFixedWidth(900)
            cols_l.addWidget(lw)
            right = QVBoxLayout()
            right.setSpacing(28)
            right.addWidget(self.tabwrap)
            right.addWidget(self.content, 1)
            cols_l.addLayout(right, 1)
            lay.addLayout(cols_l, 1)
        else:
            lay = QVBoxLayout(self)
            lay.setContentsMargins(36, 36, 36, 36)
            lay.setSpacing(20)
            lay.addLayout(top)
            lay.addWidget(tiles)
            lay.addWidget(self.tabwrap)
            lay.addWidget(self.content, 1)
            mc.setFixedHeight(360)
            lay.addWidget(mc)

    # ------------------------------------------------------------------------
    def set_tab(self, key):
        self.tab = key
        for k, b in self.tab_btns.items():
            b.set_variant("segon" if k == key else "seg")
        self._render_tab()

    def refresh(self):
        g = self.ui.game
        h = g.history or [{"t": 0, "age": g.age_years, "q": g.quarter(), "credit": g.credit_score,
                           "nw": g.get_net_worth(), "cash": g.cash, "inv": g.investments,
                           "debt": g.total_debt(), "happy": g.happiness, "income": g.quarterly_income(),
                           "ess": g.essentials_total()}]
        self.back_btn.setText("Back" if g.state != "game_over" else "Results")
        self.subtitle.setText(f"{len(h)} quarters recorded  ·  age {h[0]['age']} to {g.age_years}")
        nw = g.get_net_worth()
        year_ago = h[-5]["nw"] if len(h) >= 5 else h[0]["nw"]
        diff = nw - year_ago
        self.s_nw.set(nw, T["green"] if nw >= 0 else T["red"], f"{'+' if diff >= 0 else '−'}{money(abs(diff))} in the last year",
                      T["green"] if diff >= 0 else T["red"])
        peak = max([x["nw"] for x in h] + [nw])
        peak_age = g.age_years if nw >= peak else next(x for x in h if x["nw"] == peak)["age"]
        self.s_peak.set(peak, T["blue"], f"at age {peak_age}")
        best = max([x["credit"] for x in h] + [g.credit_score])
        self.s_credit.set(f"{g.credit_score}", score_color(g.credit_score), f"best {best}  ·  {g.tier()[1]}")
        st = g.stats
        total = st["on_time"] + st["late"] + st["missed"]
        rate = st["on_time"] / total if total else 1.0
        self.s_ontime.set(f"{rate:.0%}", T["green"] if rate >= 0.95 else (T["amber"] if rate >= 0.8 else T["red"]),
                          f"{st['late']} late · {st['missed']} missed · best streak {g.best_streak}")
        self.s_interest.set(st["interest"], T["red"] if st["interest"] else T["dim"], "money lost to interest")
        self.s_fees.set(st["fees"], T["red"] if st["fees"] else T["dim"], "overdraft, late & other fees")

        lines = []
        for t, when, text, tone in reversed(g.moments[-150:]):
            lines.append(f"<span style='color:{T['dim']}'>{esc(when)}</span>&nbsp;&nbsp;"
                         f"<span style='color:{tone_color(tone)}'>{esc(text)}</span>")
        self.moments_lbl.setText("<br>".join(lines) if lines else "Nothing yet — your story starts now.")
        self._hist = h
        self.set_tab(self.tab)

    def _legend(self, items):
        clear_layout(self.legend)
        for name, color in items:
            dot = QLabel()
            dot.setFixedSize(18, 18)
            dot.setStyleSheet(f"background:{color}; border-radius:9px;")
            self.legend.addWidget(dot)
            self.legend.addWidget(label(name, 21, W_SEMI, T["text2"]))
        self.legend.addStretch(1)

    def _render_tab(self):
        g = self.ui.game
        h = self._hist
        labels = [f"Age {x['age']}" + (f" Q{x['q']}" if len(h) < 30 else "") for x in h]
        idx = {x["t"]: i for i, x in enumerate(h)}

        def marks(pred):
            out = []
            for t, when, text, tone in g.moments:
                if t in idx and pred(text):
                    out.append((idx[t], text, tone_color(tone)))
            return out

        if self.tab == "awards":
            self.content.setCurrentIndex(1)
            self._render_awards()
            return
        self.content.setCurrentIndex(0)
        if self.tab == "nw":
            self.chart_title.setText("Net worth")
            self.chart_desc.setText("Cash + investments − debt. Steady saving and investing compounds; crashes, "
                                    "interest and fees pull it down.")
            self._legend([("Net worth", T["accent"])])
            self.chart.set_data(labels, [("Net worth", [x["nw"] for x in h], T["accent"], True)],
                                markers=marks(lambda s: "crash" in s.lower() or "laid off" in s.lower()
                                              or "collections" in s.lower() or "Retired" in s))
        elif self.tab == "credit":
            self.chart_title.setText("Credit score")
            self.chart_desc.setText("Shaded bands are credit tiers. Paying in full climbs fastest; a missed payment "
                                    "costs 50 points.")
            self._legend([("Credit score", T["purple"])])
            bands = [(800, 1000, T["green"], "EXCELLENT"), (700, 800, T["lime"], "GOOD"), (600, 700, T["gold"], "FAIR"),
                     (450, 600, T["amber"], "POOR"), (300, 450, T["red"], "VERY POOR"), (0, 300, T["red"], "IRS DANGER")]
            vals = [x["credit"] for x in h]
            lo = max(0, min(vals) - 60)
            hi = min(1000, max(vals) + 60)
            self.chart.set_data(labels, [("Credit", vals, T["purple"], False)], fmt=lambda v: f"{int(v)}",
                                tick_fmt=lambda v: f"{int(v)}", bands=bands, y_range=(lo, hi),
                                markers=marks(lambda s: s.startswith("Credit ") or "collections" in s.lower()))
        elif self.tab == "money":
            self.chart_title.setText("Cash, investments & debt")
            self.chart_desc.setText("Where your money sits each quarter. Debt includes your card, loans and any overdraft.")
            self._legend([("Cash", T["green"]), ("Investments", T["blue"]), ("Debt", T["red"])])
            self.chart.set_data(labels, [("Investments", [x["inv"] for x in h], T["blue"], True),
                                         ("Cash", [x["cash"] for x in h], T["green"], False),
                                         ("Debt", [x["debt"] for x in h], T["red"], False)])
        else:
            self.chart_title.setText("Happiness")
            self.chart_desc.setText(f"Below {g.HAPPY_RECOVER} you can't recover from burnout; each quarter at 0 is a "
                                    "warning, and 4 is fatal.")
            self._legend([("Happiness", T["pink"])])
            self.chart.set_data(labels, [("Happiness", [x["happy"] for x in h], T["pink"], True)],
                                fmt=lambda v: f"{int(v)}", tick_fmt=lambda v: f"{int(v)}",
                                bands=[(0, g.HAPPY_RECOVER, T["red"], "BURNOUT ZONE")], y_range=(0, 100))

    def _render_awards(self):
        g = self.ui.game
        clear_layout(self.awards_grid)
        got = set(g.achievements)
        self.awards_title.setText(f"Achievements  ·  {len(got)} / {len(g.ACHIEVEMENTS)}")
        cols = 3 if self.desktop else 2
        for i, (key, (name, desc)) in enumerate(g.ACHIEVEMENTS.items()):
            unlocked = key in got
            c = Card("tint_green" if unlocked else "soft")
            if not unlocked:
                c.setStyleSheet(f"QFrame#soft {{ border:2px dashed {T['border_strong']}; }}")
            c.setFixedHeight(150 if self.desktop else 128)
            cl = QHBoxLayout(c)
            cl.setContentsMargins(24, 16, 24, 16)
            cl.setSpacing(18)
            fg = T["tints"]["green"][2] if unlocked else T["dim"]
            cl.addWidget(IconWidget("trophy", 48, lambda col=fg: col))
            tv = QVBoxLayout()
            tv.setSpacing(4)
            tv.addWidget(label(name, 25, W_BOLD, fg))
            tv.addWidget(label(desc if unlocked else f"Locked — {desc}", 19, W_NORMAL,
                               T["tints"]["green"][2] if unlocked else T["muted"], wrap=True))
            cl.addLayout(tv, 1)
            self.awards_grid.addWidget(c, i // cols, i % cols)
