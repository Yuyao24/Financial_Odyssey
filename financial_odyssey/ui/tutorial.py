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
    "work": ("You worked", "Your paycheck arrived straight away. Work uses weeks of your quarter: whatever is left "
             "can go to study, fun or rest."),
    "groceries": ("Kitchen stocked", "That's food for the whole quarter. Fresh food costs more but makes you happier; "
                  "skipping the store means expensive takeout."),
    "fun": ("Feeling better", "Happiness drops every quarter. Fun costs weeks and usually money, so plan for it. "
            "At 0 happiness you start burning out: 4 warnings and it's game over."),
    "study": ("Certification earned", "Your pay is now higher every quarter, for good. Courses get pricier each "
              "time, but they pay back over decades."),
    "pay_card": ("Paying by card", "Shopping, fun and courses now go on your credit card. Pay the statement at the "
                 "Bank each quarter and your credit score climbs. Leave it unpaid and it costs interest and credit."),
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
    "autopay": ("Rent on your card", "Rent & bills will now be charged to your card each night. Pay the statement "
                "before you sleep and your credit score climbs."),
    "advance": ("A new quarter", "Overnight you paid rent & bills, interest was added and your bill was judged. "
                "The Activity menu shows everything that happened."),
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
        p = lambda: self.ui.play                          # noqa: E731
        g = lambda: self.ui.game                          # noqa: E731

        def building(key):
            return lambda: self._building_rect(key)

        def place(key, attr):
            return lambda: getattr(p().town.panel.places[key], attr)

        return [
            dict(title="Welcome to your new life!", target=None,
                 body="You're 18, with $800 and your first credit card. The next few quarters are a <b>guided "
                      "tutorial</b> — nothing bad can happen yet.<br><br>The <b>town</b> is where you live day to day. "
                      "The <b>menus</b> show your bank, credit and investments.<br><br>Buttons have an outline and "
                      "change when you hover. Faded buttons with a dashed outline are unavailable right now."),
            dict(title="Your status bar", target=lambda: p().hud,
                 body="Age, money, credit and happiness at a glance. Each turn is one <b>quarter</b> (3 months), and "
                      "you retire at 65 — or early once your net worth reaches $1,000,000."),
            dict(title="Free time", target=lambda: p().hud.time_box,
                 body="Every quarter you get <b>12 weeks</b>. Work, study and fun all use weeks. Weeks you don't use "
                      "become rest when you sleep."),
            dict(title="Go to work", target=building("office"), wait=("loc_office",),
                 body="You only have $800 and groceries cost more than that. Time to earn some money!",
                 hint="Try it: click the Office."),
            dict(title="Pick your hours", target=place("office", "plans_box"), wait=("work",),
                 body="<b>Full-time</b> pays your full salary and leaves 4 free weeks. Part-time leaves more time but "
                      "pays half. Overtime pays more but costs happiness.",
                 hint="Try it: work full-time."),
            dict(title="Build credit as you shop", target=lambda: p().hud.pay, wait=("pay_card",),
                 skip=lambda: g().pay_method == "card",
                 body="Credit is built by <b>borrowing and paying it back</b>. Switch to <b>Card</b>: your purchases "
                      "go on the card, and you pay it off at the Bank.",
                 hint="Try it: choose Card."),
            dict(title="Buy groceries", target=building("grocery"), wait=("loc_grocery",),
                 body="You need food for the quarter.", hint="Try it: click the Grocery store."),
            dict(title="Fill the fridge", target=place("grocery", "plans_box"), wait=("groceries",),
                 body="Budget saves money but you'll feel it. Fresh food costs more and lifts your mood. If you skip "
                      "shopping you'll pay extra for takeout.", hint="Try it: buy any basket."),
            dict(title="Have some fun", target=building("fun"), wait=("loc_fun",),
                 body="Happiness drops every quarter. At 0 you start burning out, and 4 quarters of burnout is fatal. "
                      "The Fun Park is where you recharge.",
                 hint="Try it: click the Fun Park."),
            dict(title="Recharge", target=place("fun", "grid_box"), wait=("fun",),
                 skip=lambda: all(g().fun_block_reason(k) for k in g().FUN_ACTIVITIES),
                 body="A walk in the park is free. Bigger outings cost money but give more happiness.",
                 hint="Try it: pick an activity."),
            dict(title="Head home", target=building("home"), wait=("loc_home",),
                 body=lambda: "When you're done for the quarter, go home and sleep." + (
                     " (You're at full happiness right now, so fun can wait until it drops.)"
                     if not g().fun_done else ""), hint="Try it: click Home."),
            dict(title="Sleep", target=place("home", "sleep_btn"), wait=("advance",),
                 body="Overnight, <b>rent & bills</b> are paid, interest is added and your card bill is judged. The "
                      "checklist shows anything you forgot.", hint="Try it: press Sleep."),
            dict(title="Life events", target=lambda: self.ui.event_overlay.modal, wait=("choose",), state="event",
                 body="Each quarter brings an event. <b style='color:#16A34A'>Green</b> = pay cash, "
                      "<b style='color:#7C3AED'>purple</b> = credit card, <b style='color:#D97706'>amber</b> = loan, "
                      "<b style='color:#DC2626'>red</b> = risky, grey = skip. Faded options aren't affordable.",
                 hint="Try it: pick any option."),
            dict(title="Your first bill", target=lambda: p().nav["bank"], wait=("nav_bank",),
                 skip=lambda: g().min_due <= 0,
                 body="You used your card, so a <b>minimum payment</b> is now due (see the red dot). The menus are "
                      "where you manage your money.", hint="Try it: open the Bank menu."),
            dict(title="Pay your bill", target=lambda: p().menus["bank"].b_all, wait=("pay_card_all", "pay_min", "pay"),
                 skip=lambda: g().remaining_due() <= 0 or g().cash <= 0 or p().menu != "bank",
                 body="<b>Pay off card</b> clears it: the biggest credit boost <i>and</i> zero interest. Paying only "
                      "the minimum avoids a penalty, but your score barely moves and the rest collects interest.",
                 hint="Try it: press Pay off card."),
            dict(title="More menus", target=lambda: p().nav_box,
                 body="<b>Credit</b> shows your score and what tonight's payment will do. <b>Invest</b> grows spare "
                      "cash. <b>Activity</b> lists everything that happened. <b>Insights</b> charts your whole life."),
            dict(title="Back to town", target=lambda: p().nav["town"], wait=("nav_town",),
                 skip=lambda: p().menu == "town",
                 body="Each quarter: work, shop, have fun, pay your bill, then sleep.", hint="Try it: open Town."),
            dict(title="Badges guide you", target=lambda: p().town.view,
                 body="Red <b>!</b> marks things still to do, a gold <b>$</b> means a bill is due, a green tick means "
                      "done, and the blue <b>z</b> on Home means you're ready to sleep."),
            dict(title="You're ready!", target=None,
                 body="From now on events are real. Pay your bills, keep happiness up, invest what you can — and "
                      "good luck! You can replay this tutorial from Settings.", last=True),
        ]

    def _building_rect(self, key):
        view = self.ui.play.town.view
        if not view.isVisible():
            return None
        r = view.building_rect(key).adjusted(-14, -22, 14, 14)
        tl = view.mapTo(self.ui, QPoint(0, 0))
        return r.translated(tl.x(), tl.y())

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
                                           {"work", "groceries", "fun", "pay_card", "pay_card_all",
                                            "pay_min", "advance"})
        win.save_settings()
        win.save_game()
        self.coach.hide()
        self.ui.play.refresh()

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
        return (ui.popup.isVisible() or ui.settings.isVisible() or ui.stack.currentWidget() is not ui.play
                or ui.win.page != "game")

    def _rect_of(self, w):
        if isinstance(w, QRectF):
            return w
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
        body = st["body"]() if callable(st["body"]) else st["body"]
        self.coach.show_bubble(rect, counter, st["title"], body, st.get("hint"), buttons, waiting)

    def _show_tip(self, key):
        title, body = TIPS[key]
        p = self.ui.play
        bank, inv, places = p.menus["bank"], p.menus["invest"], p.town.panel.places
        target = {"invest": inv.b_invest, "withdraw": inv.b_withdraw, "borrow": bank.b_loan, "pay": bank.b_pay,
                  "pay_min": bank.b_min if p.menu == "bank" else places["bank"].min_btn,
                  "pay_card_all": bank.b_all if p.menu == "bank" else places["bank"].card_btn,
                  "autopay": bank.bill if p.menu == "bank" else places["home"].autopay,
                  "work": places["office"].plans_box, "groceries": places["grocery"].plans_box,
                  "fun": places["fun"].grid_box, "study": places["college"].pay_btn, "pay_card": p.hud.pay,
                  "advance": p.hud}.get(key)

        def done():
            seen = self.ui.win.settings.setdefault("tips_seen", [])
            if key not in seen:
                seen.append(key)
            self.ui.win.save_settings()
            self.pending_tip = None
            self.coach.hide()

        self.coach.show_bubble(self._rect_of(target), "FIRST-TIME TIP", title, body, None,
                               [("Got it", "accent", done)], False)
