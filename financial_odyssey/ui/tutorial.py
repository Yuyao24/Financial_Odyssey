"""The guided first-run tutorial (spotlight + speech bubbles) and first-time tips."""

import math

from PyQt6.QtCore import QPoint, QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen, QRegion
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from .theme import W_BOLD, W_NORMAL, W_SEMI, T
from .widgets import Badge, Card, WrapButton, clear_layout, label


class CoachOverlay(QWidget):
    """Spotlight overlay: dims everything except one highlighted widget and shows a speech
    bubble next to it. For 'try it' steps the highlighted widget stays clickable (the
    overlay's mask has a hole there); everything else is blocked."""

    def __init__(self, parent, desktop):
        super().__init__(parent)
        self.setGeometry(0, 0, parent.width(), parent.height())
        self.desktop = desktop
        self.hole = None
        self.phase = 0.0
        self.bubble = Card("bubble")
        self.bubble.setParent(self)
        self.blay = QVBoxLayout(self.bubble)
        self.blay.setContentsMargins(40, 32, 40, 34)
        self.blay.setSpacing(14)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.hide()

    def _tick(self):
        self.phase = (self.phase + 0.08) % (2 * math.pi)
        if self.hole is not None:
            self.update(self.hole.adjusted(-30, -30, 30, 30).toRect())

    def show_bubble(self, hole, counter, title, body, hint, buttons, interactive):
        # hide first: Qt doesn't auto-show children added to an already-visible parent
        QWidget.hide(self)
        self.hole = hole.adjusted(-14, -14, 14, 14) if hole is not None else None
        clear_layout(self.blay)
        top = QHBoxLayout()
        tag = Badge(counter, 18, 38)
        tag.set_style(T["accent"], T["accent_text"])
        top.addWidget(tag)
        top.addStretch(1)
        self.blay.addLayout(top)
        self.blay.addWidget(label(title, 38, W_BOLD, wrap=True))
        self.blay.addWidget(label(body, 25, W_NORMAL, T["text2"], wrap=True, rich=True))
        if hint:
            self.blay.addWidget(label(hint, 24, W_BOLD, T["accent"], wrap=True))
        row = QHBoxLayout()
        row.setSpacing(12)
        for text, variant, cb in buttons:
            btn = WrapButton(text, variant, 23, W_SEMI, height=72)
            btn.clicked.connect(cb)
            row.addWidget(btn)
        self.blay.addLayout(row)

        bw = 680 if self.desktop else 860
        self.bubble.setMinimumHeight(0)
        self.bubble.setMaximumHeight(16777215)
        self.bubble.setFixedWidth(bw)
        self.blay.invalidate()                      # drop the previous bubble's cached size
        self.blay.activate()
        bh = self.blay.heightForWidth(bw) if self.blay.hasHeightForWidth() else self.blay.sizeHint().height()
        bh = max(bh, self.blay.sizeHint().height())
        self.bubble.setFixedHeight(bh)
        x, y = self._place(bw, bh)
        self.bubble.move(int(x), int(y))

        if interactive and self.hole is not None:
            self.setMask(QRegion(self.rect()).subtracted(self._hole_region()))
        else:
            self.clearMask()
        self.show()
        self.raise_()
        self.timer.start(40)
        self.update()

    HOLE_RADIUS = 26

    def _hole_path(self):
        path = QPainterPath()
        if self.hole is not None:
            path.addRoundedRect(self.hole, self.HOLE_RADIUS, self.HOLE_RADIUS)
        return path

    def _hole_region(self):
        # same rounded shape as the painted spotlight, so corners stay dimmed
        return QRegion(self._hole_path().toFillPolygon().toPolygon())

    def _place(self, bw, bh):
        W, H, m, gap = self.width(), self.height(), 40, 34
        if self.hole is None:
            return (W - bw) / 2, (H - bh) / 2
        h = self.hole
        if h.bottom() + gap + bh <= H - m:
            y = h.bottom() + gap
        elif h.top() - gap - bh >= m:
            y = h.top() - gap - bh
        else:
            y = None
        if y is not None:
            x = min(max(m, h.center().x() - bw / 2), W - m - bw)
            return x, y
        y = min(max(m, h.center().y() - bh / 2), H - m - bh)
        if h.right() + gap + bw <= W - m:
            return h.right() + gap, y
        if h.left() - gap - bw >= m:
            return h.left() - gap - bw, y
        return (W - bw) / 2, H - m - bh

    def hide(self):
        self.timer.stop()
        super().hide()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRect(QRectF(self.rect()))
        if self.hole is not None:
            path.addPath(self._hole_path())
            path.setFillRule(Qt.FillRule.OddEvenFill)
        p.fillPath(path, QColor(*T["coach"]))
        if self.hole is not None:
            a = int(150 + 100 * math.sin(self.phase))
            c = QColor(T["accent"])
            c.setAlpha(a)
            grow = 6 + 4 * math.sin(self.phase)
            p.setPen(QPen(c, 6))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(self.hole.adjusted(-grow, -grow, grow, grow),
                              self.HOLE_RADIUS + grow, self.HOLE_RADIUS + grow)
        p.end()

    def mousePressEvent(self, e):
        e.accept()


TIPS = {
    "invest": ("You invested", "That money is now in the stock market. It grows about 5-6% a year on average, but can "
               "drop — and crash. Withdrawing before age 60 costs a 5% fee."),
    "withdraw": ("You withdrew investments", "Money moved from investments back to cash. Before age 60 you pay a 5% "
                 "early-withdrawal fee, so keep an emergency fund in cash instead."),
    "borrow": ("You took a bank loan", "You got cash now, but it's debt: interest is added every quarter and an 8% "
               "minimum payment is due. Loans are cheaper than a credit card but need a 450+ score."),
    "pay": ("You paid debt", "Payments go to your highest-interest balance first (the card). Anything paid this "
            "quarter counts toward your minimum payment."),
    "pay_min": ("Minimum covered", "No late or missed penalty this quarter. But a minimum payment grows your score "
                "slowly — and not at all if your card is over 90% used. Pay in full for the biggest boost and zero "
                "interest."),
    "pay_card_all": ("Card cleared", "Paying off your whole credit card brings its balance to zero: the biggest credit "
                     "boost and no card interest this quarter (grace period). Loans stay on their own schedule."),
    "buy": ("Happiness refilled", "Leisure costs real money, so budget for it every quarter. Remember: 0 happiness for "
            "the start of burnout — 4 warnings and it's game over."),
    "autopay": ("Essentials on your card", "Rent, food and bills will now be charged to your card each quarter. Pay the "
                "statement before advancing and your credit score climbs."),
    "advance": ("A quarter passed", "You were paid, compulsory essentials were taken and a life event appeared. "
                "Check the Activity log for every detail."),
}


class Tutorial:
    """Guided first-run tutorial (spotlight + speech bubbles, waiting for real clicks),
    plus one-time tips the first time any action button is used."""

    def __init__(self, ui, desktop):
        self.ui = ui
        self.coach = CoachOverlay(ui, desktop)
        self.pending_tip = None
        self.steps = self._steps()

    # ---------------------------------------------------------------- steps --
    def _steps(self):
        d = lambda: self.ui.dash                          # noqa: E731
        g = lambda: self.ui.game                          # noqa: E731
        return [
            dict(title="Welcome to your financial life!", target=None,
                 body="This is your dashboard. The next few quarters are a <b>guided tutorial</b> — "
                      "nothing bad can happen yet.<br><br><b>How to tell what's clickable:</b> buttons have a "
                      "raised edge and change when you hover. Flat cards and grey tags only show information. "
                      "Faded buttons with a dashed outline are unavailable right now."),
            dict(title="Time & net worth", target=lambda: d().header_info,
                 body="Each turn is <b>3 months</b> (a quarter). You retire at 65 — or early once your "
                      "<b>net worth</b> (cash + investments − debt) reaches $1,000,000."),
            dict(title="Your credit score", target=lambda: d().credit_box,
                 body="You start at <b>550</b>. It only rises when you pay bills on time, and drops when you "
                      "don't. Higher scores mean cheaper loans and bigger card limits."),
            dict(title="Happiness", target=lambda: d().happy_box,
                 body="Work and life stress drain happiness every quarter. Each quarter at <b>0</b> is a burnout "
                      "warning — 4 and you die of depression. Warnings only fade once you're back above "
                      "<b>25</b>. The pink button refills it."),
            dict(title="Your money", target=lambda: d().tiles_box,
                 body="Cash, investments, credit card and loan balances, your pay, and your <b>compulsory</b> "
                      "rent, food & bills. These tiles are information only."),
            dict(title="Build credit from day one", target=lambda: d().bills, wait=("autopay",),
                 body="Credit is built by borrowing and paying it back. Tick <b>Charge essentials to card</b>: "
                      "your bills go on the card, and you pay the statement back each quarter.",
                 hint="Try it: tick the highlighted checkbox."),
            dict(title="Advance time", target=lambda: d().next_btn, wait=("advance",),
                 body="Each press = one quarter: you get paid, essentials are charged and a life event happens.",
                 hint="Try it: press Advance 3 months."),
            dict(title="Life events", target=lambda: self.ui.event_overlay.modal, wait=("choose",), state="event",
                 body="Every quarter brings an event. <b style='color:#16A34A'>Green</b> = pay cash, "
                      "<b style='color:#7C3AED'>purple</b> = credit card, <b style='color:#D97706'>amber</b> = loan, "
                      "<b style='color:#DC2626'>red</b> = risky, grey = skip. Faded options aren't affordable.",
                 hint="Try it: pick any option."),
            dict(title="Your first statement", target=lambda: d().bills, skip=lambda: g().min_due <= 0,
                 body="You used your card, so a <b>minimum payment</b> is now due. Pay at least this much "
                      "<b>before</b> advancing: on time = credit up, late = −20, missed = −50."),
            dict(title="Pay your bill", target=lambda: d().b_all, wait=("pay_card_all", "pay_min", "pay"),
                 skip=lambda: g().remaining_due() <= 0 or g().cash <= 0,
                 body="<b>Pay off card</b> clears the card: the biggest credit boost <i>and</i> zero interest. "
                      "<b>Pay minimum</b> only avoids a penalty — your score barely moves (not at all if the card "
                      "is over 90% used) and the rest keeps collecting interest.",
                 hint="Try it: press Pay off card."),
            dict(title="Activity log", target=lambda: d().log_box,
                 body="Every paycheck, bill, interest charge and decision is recorded here, newest first."),
            dict(title="Choose an amount", target=lambda: d().amount_box, on_show=lambda: d().amount.setValue(500),
                 body="Type an amount or tap a preset. <b>Invest</b>, <b>Withdraw</b>, <b>Borrow</b> and "
                      "<b>Pay debt</b> all use this amount."),
            dict(title="Invest for the future", target=lambda: d().b_invest, wait=("invest",),
                 skip=lambda: g().cash < 500,
                 body="Investing grows your money over decades (about 5-6% a year on average) — but markets "
                      "can crash. Withdrawing before age 60 costs 5%.", hint="Try it: press Invest $500."),
            dict(title="Stay happy", target=lambda: d().buy_btn, wait=("buy",),
                 skip=lambda: not d().buy_btn.isEnabled(),
                 body="Happiness costs real money — budget for it every quarter.",
                 hint="Try it: press Buy leisure & hobbies."),
            dict(title="One more quarter", target=lambda: d().next_btn, wait=("advance",),
                 body="Advance again. If a bill were still unpaid, you'd get a warning first.",
                 hint="Try it: press Advance 3 months."),
            dict(title="Credit workshop", target=lambda: self.ui.event_overlay.modal, wait=("choose",), state="event",
                 body="Some events are quizzes that teach real credit rules. Answer correctly to win a gift card.",
                 hint="Pick the answer you think is right."),
            dict(title="Watch your score", target=lambda: d().credit_box,
                 body="Paying on time is what moves this. During your first 5 years it can't pass 700 — "
                      "lenders want a long history."),
            dict(title="Settings, help & quitting", target=lambda: d().toolbar_box,
                 body="<b>Settings</b>: light/dark theme, mobile/desktop layout, fullscreen and replaying this "
                      "tutorial. <b>Stats</b> shows charts of your credit score, net worth and more over time. <b>Credit 101</b> opens the full guide. <b>Save & quit</b> any time — your "
                      "game also saves automatically after every move."),
            dict(title="You're ready!", target=None,
                 body="From now on events are real. Pay your bills, keep happiness up, invest what you can — "
                      "and good luck!", last=True),
        ]

    # --------------------------------------------------------------- state ---
    @property
    def active(self):
        ui = self.ui
        return ui.win.page == "game" and ui.game.tutorial_step >= 0 and ui.game.state in ("main", "event")

    def start(self):
        g = self.ui.game
        g.tutorial_step = 0
        g.scripted_events = ["festival", "credit_quiz"]
        self.refresh()

    def finish(self):
        self.ui.game.tutorial_step = -1
        win = self.ui.win
        win.settings["tutorial_done"] = True
        win.settings["tips_seen"] = sorted(set(win.settings.get("tips_seen", [])) |
                                           {"invest", "pay_min", "buy", "autopay", "advance"})
        win.save_settings()
        win.save_game()
        self.coach.hide()
        self.ui.dash.refresh()

    def next(self):
        g = self.ui.game
        g.tutorial_step += 1
        if g.tutorial_step >= len(self.steps):
            self.finish()
            return
        self.ui.win.save_game()
        self.refresh()

    def notify(self, key):
        """Called after any player action (key = invest/advance/choose/...)."""
        if self.active:
            st = self.steps[self.ui.game.tutorial_step]
            if key in st.get("wait", ()):
                self.next()
            return
        seen = self.ui.win.settings.setdefault("tips_seen", [])
        if key in TIPS and key not in seen:
            self.pending_tip = key

    # -------------------------------------------------------------- render ---
    def refresh(self):
        QTimer.singleShot(0, self._render)          # after layouts settle

    def _blocked(self):
        ui = self.ui
        return (ui.popup.isVisible() or ui.settings.isVisible() or ui.stack.currentWidget() is not ui.dash
                or ui.win.page != "game")

    def _rect_of(self, w):
        if w is None or not w.isVisible():
            return None
        tl = w.mapTo(self.ui, QPoint(0, 0))
        return QRectF(tl.x(), tl.y(), w.width(), w.height())

    def _render(self):
        try:
            self.coach.isVisible()
        except RuntimeError:                         # UI was rebuilt; this controller is stale
            return
        if self._blocked():
            self.coach.hide()
            return
        g = self.ui.game
        if not self.active:
            if self.pending_tip:
                self._show_tip(self.pending_tip)
            else:
                self.coach.hide()
            return
        while True:
            st = self.steps[g.tutorial_step]
            if st.get("state", "main") != g.state:
                self.coach.hide()
                return
            if st.get("skip") and st["skip"]():
                g.tutorial_step += 1
                if g.tutorial_step >= len(self.steps):
                    self.finish()
                    return
                continue
            break
        if st.get("on_show"):
            st["on_show"]()
        target = st["target"]() if st.get("target") else None
        rect = self._rect_of(target)
        counter = f"TUTORIAL  ·  {g.tutorial_step + 1} / {len(self.steps)}"
        waiting = bool(st.get("wait"))
        if st.get("last"):
            buttons = [("Start playing", "accent", self.next)]
        elif waiting:
            buttons = [("Skip tutorial", "outline", self.finish), ("Skip this step", "soft", self.next)]
        else:
            buttons = [("Skip tutorial", "outline", self.finish), ("Next  →", "accent", self.next)]
        self.coach.show_bubble(rect, counter, st["title"], st["body"], st.get("hint"), buttons, waiting)

    def _show_tip(self, key):
        title, body = TIPS[key]
        d = self.ui.dash
        target = {"invest": d.b_invest, "withdraw": d.b_withdraw, "borrow": d.b_loan, "pay": d.b_pay,
                  "pay_min": d.b_min, "pay_card_all": d.b_all, "buy": d.buy_btn, "autopay": d.bills,
                  "advance": d.log_box}.get(key)

        def done():
            seen = self.ui.win.settings.setdefault("tips_seen", [])
            if key not in seen:
                seen.append(key)
            self.ui.win.save_settings()
            self.pending_tip = None
            self.coach.hide()

        self.coach.show_bubble(self._rect_of(target), "FIRST-TIME TIP", title, body, None,
                               [("Got it", "accent", done)], False)
