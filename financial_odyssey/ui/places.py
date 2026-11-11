"""The panel shown next to the town for the building you're visiting.

All six panels are built once and kept in a stack; refresh() only updates their text and which
buttons are enabled, so nothing is created or destroyed while you play.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QHBoxLayout,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..formatting import esc, money
from .theme import W_BOLD, W_MED, W_NORMAL, T, make_font
from .widgets import Badge, Card, IconWidget, WrapButton, label

PLACE_ICONS = {"home": "home", "office": "briefcase", "grocery": "cart", "bank": "bank", "fun": "ferris",
               "college": "cap"}
PLACE_TINTS = {"home": "slate", "office": "blue", "grocery": "green", "bank": "teal", "fun": "pink",
               "college": "purple"}
PLACE_INFO = {
    "home": ("Home", "Sleep to end the quarter. Rent & bills are charged overnight."),
    "office": ("Office", "Pick how much to work this quarter. You're paid straight away."),
    "grocery": ("Grocery store", "Stock the kitchen for the quarter. Skip it and you'll live on takeout."),
    "bank": ("Bank", "Pay your card, check your statement or take a loan."),
    "fun": ("Fun Park", "Spend free weeks recharging. Each activity once per quarter."),
    "college": ("College", "Earn certifications that permanently raise your pay."),
}


def check_line(ok, text):
    mark, col = ("✓", T["green"]) if ok else ("✗", T["red"])
    return f"<span style='color:{col}; font-weight:700'>{mark}</span>&nbsp; {esc(text)}"


class Place(QWidget):
    """Common header (icon, title, subtitle, status tag) plus a body layout for the actions."""

    def __init__(self, ui, key, desktop):
        super().__init__()
        self.ui, self.key, self.desktop = ui, key, desktop
        self.btn_h = 100 if desktop else 86
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)
        head = QHBoxLayout()
        head.setSpacing(18)
        tint = PLACE_TINTS[key]
        icon_box = Card(f"tint_{tint}")
        icon_box.setFixedSize(84, 84)
        il = QVBoxLayout(icon_box)
        il.setContentsMargins(16, 16, 16, 16)
        il.addWidget(IconWidget(PLACE_ICONS[key], 52, lambda t=tint: T["tints"][t][2]))
        head.addWidget(icon_box)
        tv = QVBoxLayout()
        tv.setSpacing(2)
        title, sub = PLACE_INFO[key]
        tv.addWidget(label(title, 38, W_BOLD))
        tv.addWidget(label(sub, 21, W_NORMAL, T["muted"], wrap=True))
        head.addLayout(tv, 1)
        self.status = Badge("", 18, 40)
        head.addWidget(self.status, 0, Qt.AlignmentFlag.AlignTop)
        lay.addLayout(head)
        self.body = QVBoxLayout()
        self.body.setSpacing(14)
        lay.addLayout(self.body)
        lay.addStretch(1)

    def set_status(self, text, kind):
        self.status.setText(text)
        if kind == "done":
            self.status.set_style(T["green"], T["solid_green_text"])
        elif kind == "todo":
            self.status.set_style(T["red"], T["danger_text"])
        else:
            self.status.set_tint(kind)
        self.status.setVisible(bool(text))

    def button(self, variant, fn, key=None):
        b = WrapButton("", variant, 23, W_BOLD, height=self.btn_h)
        b.clicked.connect(lambda: self.ui.act(key, fn))
        return b

    def group(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(14)
        self.body.addWidget(w)
        return w, v

    def info(self, px=24, color=None):
        lb = label("", px, W_MED, color or T["text2"], wrap=True, rich=True)
        self.body.addWidget(lb)
        return lb

    @property
    def g(self):
        return self.ui.game


class HomePlace(Place):
    def __init__(self, ui, desktop):
        super().__init__(ui, "home", desktop)
        self.rent = self.info(26, T["text"])
        self.checklist = self.info(23)
        self.autopay = QCheckBox("Charge rent && bills to my credit card")
        self.autopay.setFont(make_font(22, W_MED))
        self.autopay.toggled.connect(self._toggle_autopay)
        self.body.addWidget(self.autopay)
        self.night = None
        if desktop:
            self.night_cap = label("LAST NIGHT", 18, W_BOLD, T["dim"])
            self.body.addWidget(self.night_cap)
            self.night = self.info(20, T["text2"])
        self.sleep_btn = WrapButton("Sleep  ·  next quarter", "primary", 30, W_BOLD, height=110, icon="bed")
        self.sleep_btn.clicked.connect(ui.advance)
        self.body.addWidget(self.sleep_btn)
        self.retire_btn = WrapButton("Retire early", "solid_green", 26, W_BOLD, height=90)
        self.retire_btn.clicked.connect(ui.confirm_retire)
        self.body.addWidget(self.retire_btn)

    def _toggle_autopay(self, on):
        g = self.g
        if g.essentials_on_card != on:
            g.essentials_on_card = on
            g.add_log("Rent & bills will now be charged to your card — pay the statement each quarter!"
                      if on else "Rent & bills will now be paid from cash", "card" if on else "info")
            self.ui.act("autopay" if on else None, lambda: (True, ""))

    def refresh(self):
        g = self.g
        ess = g.essentials_total()
        after = g.cash - (0 if g.essentials_on_card else ess)
        line = f"Rent & bills tonight: <b>{money(ess)}</b>"
        if g.essentials_on_card:
            line += f"<br><span style='color:{T['purple']}; font-size:21px'>Goes on your card</span>"
        elif after < 0:
            line += (f"<br><span style='color:{T['red']}; font-size:21px'>You're {money(-after)} short: "
                     "it'll go into overdraft, onto your card, or to collections</span>")
        else:
            line += f"<br><span style='color:{T['muted']}; font-size:21px'>Cash left after rent: {money(after)}</span>"
        self.rent.setText(line)
        self.rent.setToolTip("\n".join(f"{n}: {money(v)}" for n, v in g.essentials_breakdown()))
        items = g.bedtime_checklist()
        rest = g.weeks_left() * g.REST_HAPPY
        lines = [check_line(ok, t) for t, ok in items]
        if rest:
            lines.append(f"<span style='color:{T['blue']}; font-weight:700'>☾</span>&nbsp; {g.weeks_left()} free "
                         f"week{'s' if g.weeks_left() != 1 else ''} left: rest gives +{rest} happiness")
        self.checklist.setText("<br>".join(lines))
        if self.autopay.isChecked() != g.essentials_on_card:
            self.autopay.blockSignals(True)
            self.autopay.setChecked(g.essentials_on_card)
            self.autopay.blockSignals(False)
        if self.night is not None:
            rep = g.night_report[-6:]
            self.night_cap.setVisible(bool(rep))
            self.night.setVisible(bool(rep))
            self.night.setText("<br>".join(f"<span style='color:{tone_col(t)}'>{esc(x)}</span>" for _, x, t in rep))
        todo = sum(not ok for _, ok in items)
        self.set_status("READY" if not todo else f"{todo} TO DO", "done" if not todo else "amber")
        self.retire_btn.setVisible(g.can_retire_early())


def tone_col(tone):
    return {"good": T["green"], "bad": T["red"], "warn": T["amber"], "invest": T["blue"],
            "card": T["purple"], "gold": T["gold"]}.get(tone, T["text2"])


class OfficePlace(Place):
    def __init__(self, ui, desktop):
        super().__init__(ui, "office", desktop)
        self.pay = self.info(25, T["text"])
        self.plans = {}
        self.plans_box, box = self.group()
        for key in ("part", "full", "over"):
            b = self.button("blue" if key != "over" else "amber", lambda k=key: self.g.work(k), "work")
            self.plans[key] = b
            box.addWidget(b)
        self.note = self.info(21, T["muted"])

    def refresh(self):
        g = self.g
        line = f"Full-time pay: <b>{money(g.quarterly_income())}</b> per quarter"
        if g.layoff_turns:
            line += f"<br><span style='color:{T['amber']}'>Reduced hours: {int(g.layoff_mult * 100)}% pay for " \
                    f"{g.layoff_turns} more quarter{'s' if g.layoff_turns > 1 else ''}</span>"
        elif not g.has_car:
            line += f"<br><span style='color:{T['muted']}; font-size:21px'>No car: commute costs you 10% of pay</span>"
        self.pay.setText(line)
        for key, b in self.plans.items():
            name, weeks, frac, happy = g.WORK_PLANS[key]
            extra = f"  ·  {happy:+d} happiness" if happy else ""
            if g.work_plan == key:
                b.setText(f"✓ Worked {name.lower()} this quarter\n+{money(g.work_pay(key))}")
            else:
                b.setText(f"{name}  ·  {weeks} weeks\n+{money(g.work_pay(key))}{extra}")
            b.setEnabled(g.work_block_reason(key) is None)
        if g.work_plan:
            self.note.setText("Come back next quarter. Your free weeks can go to study, fun or rest.")
            self.set_status("DONE", "done")
        else:
            self.note.setText(f"You have {g.weeks_left()} free weeks. Full-time leaves 4 for fun, study or rest.")
            self.set_status("TO DO", "todo")


class GroceryPlace(Place):
    def __init__(self, ui, desktop):
        super().__init__(ui, "grocery", desktop)
        self.method = self.info(24, T["text"])
        self.plans = {}
        self.plans_box, box = self.group()
        for key in ("budget", "regular", "fresh"):
            b = self.button("green", lambda k=key: self.g.buy_groceries(k), "groceries")
            self.plans[key] = b
            box.addWidget(b)
        self.note = self.info(21, T["muted"])

    def refresh(self):
        g = self.g
        self.method.setText(pay_line(g))
        for key, b in self.plans.items():
            name, _, happy = g.GROCERY_PLANS[key]
            extra = f"  ·  {happy:+d} happiness" if happy else ""
            if g.groceries == key:
                b.setText(f"✓ {name}\nKitchen stocked for this quarter")
            else:
                b.setText(f"{name}\n{money(g.grocery_cost(key))}{extra}")
            b.setEnabled(g.grocery_block_reason(key) is None)
        if g.groceries:
            self.note.setText("All stocked up. See you next quarter!")
            self.set_status("DONE", "done")
        else:
            self.note.setText(f"Skip shopping and you'll eat takeout: {money(g.takeout_cost())} and "
                              f"{g.TAKEOUT_HAPPY} happiness.")
            self.set_status("TO DO", "todo")


def pay_line(g):
    if g.pay_method == "card":
        return (f"Paying with: <b style='color:{T['purple']}'>Credit card</b> "
                f"<span style='color:{T['muted']}'>({money(g.card_available())} available)</span>")
    return (f"Paying with: <b style='color:{T['green']}'>Cash</b> "
            f"<span style='color:{T['muted']}'>({money(g.cash)} in the bank)</span>")


class FunPlace(Place):
    def __init__(self, ui, desktop):
        super().__init__(ui, "fun", desktop)
        self.method = self.info(24, T["text"])
        self.grid_box = QWidget()
        grid = QGridLayout(self.grid_box)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(14)
        self.acts = {}
        for i, key in enumerate(("park", "movies", "concert", "trip")):
            b = self.button("pink", lambda k=key: self.g.do_fun(k), "fun")
            self.acts[key] = b
            grid.addWidget(b, i // 2, i % 2)
        self.body.addWidget(self.grid_box)
        self.note = self.info(21, T["muted"])

    def refresh(self):
        g = self.g
        self.method.setText(pay_line(g))
        for key, b in self.acts.items():
            name, weeks, _, happy = g.FUN_ACTIVITIES[key]
            cost = g.fun_cost(key)
            if key in g.fun_done:
                b.setText(f"✓ {name}\ndone this quarter")
            else:
                b.setText(f"{name}\n{money(cost) if cost else 'Free'} · {weeks}wk · +{happy}")
            b.setEnabled(g.fun_block_reason(key) is None)
        if g.happiness >= 100:
            self.note.setText("You're as happy as can be. Save your free weeks: each unused week is rest.")
        else:
            self.note.setText(f"Happiness {g.happiness}/100, dropping {g.happiness_decay()} each quarter. "
                              f"{g.weeks_left()} free week{'s' if g.weeks_left() != 1 else ''} left.")
        if g.happiness < 35:
            self.set_status("LOW HAPPINESS", "todo")
        else:
            self.set_status("", "slate")


class CollegePlace(Place):
    def __init__(self, ui, desktop):
        super().__init__(ui, "college", desktop)
        self.text = self.info(24, T["text"])
        self.pay_btn = self.button("purple", lambda: self.g.study("pay"), "study")
        self.loan_btn = self.button("amber", lambda: self.g.study("loan"), "study")
        self.body.addWidget(self.pay_btn)
        self.body.addWidget(self.loan_btn)
        self.note = self.info(21, T["muted"])

    def refresh(self):
        g = self.g
        n = g.courses_taken
        if n >= g.MAX_COURSES:
            self.text.setText(f"You've earned all <b>{g.MAX_COURSES}</b> certifications. Well done!")
            self.pay_btn.setVisible(False)
            self.loan_btn.setVisible(False)
            self.note.setText("")
            self.set_status("COMPLETE", "done")
            return
        cost = g.course_cost()
        self.text.setText(f"Certification <b>{n + 1} of {g.MAX_COURSES}</b>: {money(cost)} and "
                          f"{g.STUDY_WEEKS} weeks.<br>Raises your pay by <b>{money(g.wage(g.COURSE_BONUS))}</b> "
                          "every quarter, for good.<br>" + pay_line(g))
        self.pay_btn.setVisible(True)
        self.loan_btn.setVisible(True)
        self.pay_btn.setText(f"Enroll  ·  pay {money(cost)} by {'card' if g.pay_method == 'card' else 'cash'}")
        self.pay_btn.setEnabled(g.study_block_reason("pay") is None)
        self.loan_btn.setText(f"Enroll with a student loan\n{money(cost)} at {g.loan_rate():.2%}/qtr")
        self.loan_btn.setEnabled(g.study_block_reason("loan") is None)
        reason = g.study_block_reason("pay")
        self.note.setText(reason or "Courses get pricier each time, but pay back over decades.")
        self.set_status("STUDIED" if g.studied else "", "done" if g.studied else "slate")


class BankPlace(Place):
    def __init__(self, ui, desktop):
        super().__init__(ui, "bank", desktop)
        self.text = self.info(24, T["text"])
        row = QHBoxLayout()
        row.setSpacing(14)
        self.min_btn = self.button("green", lambda: self.g.pay_minimum(), "pay_min")
        self.card_btn = self.button("teal", lambda: self.g.pay_card_all(), "pay_card_all")
        row.addWidget(self.min_btn)
        row.addWidget(self.card_btn)
        self.body.addLayout(row)
        self.open_btn = WrapButton("Open the Bank menu  →", "outline", 25, W_BOLD, height=self.btn_h, icon="bank")
        self.open_btn.clicked.connect(lambda: ui.play.show_menu("bank"))
        self.body.addWidget(self.open_btn)

    def refresh(self):
        g = self.g
        rem = g.remaining_due()
        lines = [f"Cash <b>{money(g.cash)}</b>  ·  Card <b>{money(g.card)}</b> of {money(g.card_limit())}"
                 + (f"  ·  Loans <b>{money(g.loans)}</b>" if g.loans else "")]
        if g.min_due <= 0 and g.payment_quality() == "full":
            _, pts = g.projected_credit_change()
            lines.append(f"<span style='color:{T['green']}'>Card used and paid off: credit {pts:+d} tonight</span>")
            self.set_status("PAID", "done")
        elif g.min_due <= 0:
            lines.append(f"<span style='color:{T['muted']}'>No bill this quarter. Use your card and pay it back to "
                         "build credit.</span>")
            self.set_status("NO BILL", "slate")
        elif rem > 0:
            lines.append(f"<span style='color:{T['red']}'><b>{money(rem)}</b> minimum still due before you sleep</span>")
            self.set_status("BILL DUE", "todo")
        else:
            q, pts = g.projected_credit_change()
            lines.append(f"<span style='color:{T['green']}'>Minimum covered ({g.QUALITY_LABEL[q]}): credit {pts:+d} "
                         "tonight</span>")
            self.set_status("PAID", "done")
        self.text.setText("<br>".join(lines))
        self.min_btn.setText(f"Pay minimum\n{money(rem)}" if rem > 0 else "Minimum\ncovered")
        self.min_btn.setEnabled(rem > 0 and g.cash > 0)
        self.card_btn.setText(f"Pay off card\n{money(min(g.card, max(0, g.cash)))}")
        self.card_btn.setEnabled(g.card > 0 and g.cash > 0)


class PlacePanel(Card):
    """Card holding one panel per building; show(key) switches between them."""

    def __init__(self, ui, desktop):
        super().__init__("card")
        lay = QVBoxLayout(self)
        pad = 40 if desktop else 30
        lay.setContentsMargins(pad, pad - 4, pad, pad - 4)
        self.stack = QStackedWidget()
        self.places = {
            "home": HomePlace(ui, desktop), "office": OfficePlace(ui, desktop), "grocery": GroceryPlace(ui, desktop),
            "bank": BankPlace(ui, desktop), "fun": FunPlace(ui, desktop), "college": CollegePlace(ui, desktop),
        }
        for w in self.places.values():
            self.stack.addWidget(w)
        lay.addWidget(self.stack)

    def show_place(self, key):
        self.stack.setCurrentWidget(self.places[key])

    def refresh(self):
        for w in self.places.values():
            w.refresh()


def place_badges(g):
    """Badge for each building in the town scene."""
    b = {"office": "done" if g.work_plan else "todo",
         "grocery": "done" if g.groceries else "todo"}
    if g.remaining_due() > 0:
        b["bank"] = "due"
    if g.happiness < 35 and g.weeks_left() > 0:
        b["fun"] = "todo"
    if g.work_plan and g.groceries and g.remaining_due() <= 0:
        b["home"] = "sleep"
    return b

