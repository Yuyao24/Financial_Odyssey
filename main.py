#!/usr/bin/env python3
"""
Financial Odyssey: 18 to 65  —  PyQt6 edition

Layouts: "mobile" (fixed 1080x1920, vertical) or "desktop" (fixed 2880x1620, horizontal),
chosen in Settings. The chosen canvas is scaled uniformly into the window and centred, with
black bars filling any leftover space, so every screen shape shows the identical layout.
Pixel-sized fonts, word-wrapping and auto-shrinking labels keep text inside its boxes.

A guided, click-along tutorial runs on the first game, and first-time tips explain each
button the first time it is used (replay both from Settings).
Themes: light / dark (Settings). Progress auto-saves after every move and on close to
  <user app-data folder>/savegame.json   (settings in settings.json next to it)

Controls:  F11 = toggle fullscreen,  Esc = leave fullscreen.
"""
import html
import json
import math
import os
import random
import sys

from PyQt6.QtCore import Qt, QTimer, QRectF, QRect, QPoint, QPointF, QSize, QStandardPaths
from PyQt6.QtGui import (QColor, QFont, QFontMetrics, QPainter, QPen, QBrush, QGuiApplication, QTransform, QShortcut, QKeySequence, QPainterPath, QRegion)
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QFrame, QLabel,
                             QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QStackedWidget, QGraphicsView, QGraphicsScene,
                             QSpinBox, QCheckBox, QScrollArea, QSizePolicy)


def money(v):
    v = int(v)
    return f"-${abs(v):,}" if v < 0 else f"${v:,}"


def esc(text):
    return html.escape(str(text))


# =============================================================================
#                                GAME ENGINE
# =============================================================================
class LifeGame:
    # ---- Economy (all amounts per quarter; 1 turn = 3 months) ---------------
    START_CASH = 800
    START_INCOME = 5200            # take-home pay per quarter at 18
    RENT_BASE = 2300               # compulsory
    FOOD_BASE = 1000               # compulsory groceries
    UTIL_BASE = 550                # compulsory transport & utilities
    NO_CAR_SAVING = 150            # transit is a bit cheaper than running a car
    PET_COST = 120
    LIFESTYLE_CREEP = 0.30         # 30% of every raise is eaten by a pricier lifestyle
    INFLATION_QTR = 0.0075         # ~3% / year
    RAISE_QTR = 0.006              # ~2.4% / year (slower than inflation!)

    HAPPY_COST = 900               # the ONE way to buy happiness on the dashboard
    HAPPY_PTS = 20

    # ---- Banking ------------------------------------------------------------
    OVERDRAFT_LIMIT = 1000
    OVERDRAFT_FEE = 35
    OVERDRAFT_RATE = 0.05
    OVER_LIMIT_FEE = 35
    COLLECTIONS_FEE = 0.15
    LOAN_ORIGINATION = 0.02
    CARD_MIN_PCT = 0.10
    LOAN_MIN_PCT = 0.08
    MIN_PAYMENT_FLOOR = 50
    LOAN_MIN_SCORE = 450

    # (min score, tier name, loan rate/qtr, card rate/qtr, card limit, max total loans)
    TIERS = [
        (800, "Excellent", 0.0125, 0.035, 12000, 60000),
        (700, "Good",      0.0175, 0.045,  8000, 30000),
        (600, "Fair",      0.0250, 0.055,  5000, 15000),
        (450, "Poor",      0.0350, 0.065,  3000,  6000),
        (0,   "Very Poor", 0.0475, 0.075,  1000,     0),
    ]
    HISTORY_CAP_TURNS = 20         # 5 years of history ...
    HISTORY_CAP = 700              # ... before you can pass 700
    IRS_SCORE = 300
    IRS_TURNS = 8
    DEPRESSION_TURNS = 4

    # ---- Investing ----------------------------------------------------------
    INVEST_RANGE = (-0.035, 0.075)
    CRASH_CHANCE = 1 / 48
    CRASH_RANGE = (0.15, 0.35)
    EARLY_WITHDRAW_PENALTY = 0.05
    PENALTY_FREE_AGE = 60

    MAX_COURSES = 5
    COURSE_BASE_COST = 1500
    COURSE_BONUS = 550

    MILLION = 1_000_000
    DEATH_PENALTY = 100_000

    EVENT_DECK = {
        "festival": 3, "market": 2, "car": 2, "vacation": 2, "course": 3,
        "credit_quiz": 3, "layoff": 1, "medical": 2, "phone": 2, "rent_hike": 1,
        "side_hustle": 2, "wedding": 2, "tax_refund": 1, "limit_offer": 1,
        "identity_theft": 1, "pet": 1, "review": 2, "crypto": 1, "inheritance": 1,
        "accident": 1, "scam": 1, "dip": 1, "bonus": 1, "debt_offer": 1,
    }

    ACHIEVEMENTS = {
        "first_swipe":  ("First Swipe", "Used your credit card for the first time"),
        "on_time":      ("Responsible Borrower", "Made your first on-time payment"),
        "streak8":      ("Clockwork", "8 on-time payments in a row"),
        "good_credit":  ("Good Credit", "Reached a 700 credit score"),
        "excellent":    ("Excellent Credit", "Reached an 800 credit score"),
        "investor":     ("Investor", "Made your first investment"),
        "debt_free":    ("Debt Free", "Paid off every dollar of debt"),
        "learner":      ("Lifelong Learner", "Completed all 5 certifications"),
        "storm":        ("Weathered the Storm", "Kept investing through a market crash"),
        "six_figures":  ("Six Figures", "Net worth of $100,000"),
        "millionaire":  ("Millionaire", "Net worth of $1,000,000"),
        "quiz_whiz":    ("Credit Whiz", "Answered 3 credit quizzes correctly"),
        "golden":       ("Golden Years", "Made it to retirement at 65"),
    }

    QUIZ = [
        ("What has the biggest impact on your credit score?",
         ["Paying at least the minimum on time, every time",
          "How much cash you keep in the bank",
          "How often you check your score"],
         "Payment history is king. In this game your score only rises when you pay what is due, "
         "and only falls when you don't. Cash balance and checking your score don't affect it."),
        ("Your statement shows: balance $2,000, minimum due $200. What protects your score?",
         ["Pay at least $200 now — ideally all $2,000 to avoid interest",
          "Pay nothing until next quarter",
          "Pay $50, any amount counts"],
         "Paying the minimum keeps the payment on time. Paying less than the minimum still counts as a "
         "LATE payment (-20), and paying nothing is a MISSED payment (-50). Paying the full statement "
         "also means no card interest thanks to the grace period."),
        ("Which usually charges the highest interest?",
         ["A credit card balance you carry over",
          "A bank loan",
          "They always charge the same"],
         "Credit cards have much higher rates than bank loans. When you pay debt, attack the "
         "highest-rate balance first (this game automatically pays your card first)."),
        ("What happens if you ignore a bill you can't pay?",
         ["It goes to collections: extra fees and a big credit hit",
          "Nothing, it disappears after a while",
          "The bank pays it for you for free"],
         "Unpaid bills are sent to collections: a 15% fee is added, it becomes debt, and it counts as "
         "a missed payment (-50). Even a small payment plan is better than ignoring a bill."),
        ("Why can't an 18-year-old jump straight to an 800 score?",
         ["Lenders want a long history — scores are capped near 700 for ~5 years",
          "Young people are banned from good credit",
          "Scores only start counting at age 30"],
         "Length of credit history matters. In this game your score can't pass 700 until you've had "
         "5 years (20 quarters) of history — so start building good habits early."),
        ("Does swiping your credit card lower your score in this game?",
         ["No — only unpaid minimum payments lower it",
          "Yes, every purchase costs points",
          "Only purchases over $100"],
         "Using your card is not the problem — not paying it back is. Charging things and paying the "
         "statement on time is exactly how you build credit."),
        ("What does a higher credit score get you?",
         ["Lower interest, higher card limits and bigger loans",
          "A higher salary",
          "Free groceries"],
         "Better credit tiers lower your loan and card interest rates, raise your card limit and let you "
         "borrow more. Over a lifetime that's thousands of dollars saved."),
        ("What is an overdraft?",
         ["Spending more than your bank balance — the bank covers it, for fees and interest",
          "A free bonus from the bank",
          "A type of investment"],
         "Overdraft lets your cash go negative (up to $1,000 here), but costs a $35 fee plus 5% interest "
         "each quarter. Go past the limit and the rest goes to your card or to collections."),
        ("If you only ever pay the minimum on your card...",
         ["Your score stays safe, but interest keeps piling up on the rest",
          "The debt is forgiven after a year",
          "You never pay any interest"],
         "Minimum payments protect your score, but the remaining balance keeps growing with interest. "
         "Pay in full whenever you can."),
        ("$1,000 on a card at 5% interest per quarter, unpaid for a year, becomes about...",
         ["$1,216", "$1,050", "$1,000"],
         "Interest compounds: 1,000 x 1.05 x 1.05 x 1.05 x 1.05 = about $1,216. Debt grows on top of itself."),
    ]

    def __init__(self, seed=None):
        self.reset(seed)

    # ---------------------------------------------------------------- setup --
    def reset(self, seed=None):
        self.seed = seed if seed is not None else random.randrange(1_000_000)
        self.rng = random.Random(self.seed)

        self.age_years, self.age_months, self.turns_played = 18, 0, 0
        self.cash = self.START_CASH
        self.investments = 0
        self.card = 0
        self.loans = 0
        self.credit_score = 550
        self.streak = 0
        self.best_streak = 0
        self.happiness = 100
        self.low_credit_turns = 0
        self.zero_happiness_turns = 0

        self.min_due = 0
        self.paid_this_qtr = 0
        self.paid_card_this_qtr = 0
        self.stmt_card = 0
        self.essentials_on_card = False

        self.base_income = self.START_INCOME
        self.price_index = 1.0
        self.wage_index = 1.0
        self.has_car = True
        self.has_pet = False
        self.has_roommate = False
        self.inheritance_done = False
        self.rent_adj = 0
        self.limit_bonus = 0
        self.courses_taken = 0
        self.layoff_turns = 0
        self.layoff_mult = 1.0

        self.event_deck = []
        self.last_event_key = None
        self.current_event = None
        self.state = "start"            # start, main, event, game_over
        self.end_reason = ""
        self.log = []
        self.popups = []                # dicts for the UI to show
        self.toasts = []                # (text, tone)
        self.achievements = []
        self.quiz_correct = 0
        self.quiz_pool = []
        self.credit_reasons = []
        self.millionaire_notified = False
        self.tutorial_step = -1          # >= 0 while the guided tutorial is running
        self.scripted_events = []        # tutorial quarters use these instead of random events
        self.had_debt = False
        self.stats = {"interest": 0, "fees": 0, "on_time": 0, "late": 0, "missed": 0}

    # ------------------------------------------------------------ save/load --
    SAVE_VERSION = 1
    _TRANSIENT = ("rng", "popups", "toasts")

    def to_dict(self):
        d = {k: v for k, v in self.__dict__.items() if k not in self._TRANSIENT}
        d["rng_state"] = self.rng.getstate()
        d["save_version"] = self.SAVE_VERSION
        return d

    @classmethod
    def from_dict(cls, d):
        g = cls(seed=d.get("seed"))
        for k, v in d.items():
            if k in g.__dict__ and k not in cls._TRANSIENT:
                setattr(g, k, v)
        st = d.get("rng_state")
        if st:
            g.rng.setstate((st[0], tuple(st[1]), st[2]))
        g.log = [tuple(x) for x in g.log]
        return g

    def start(self):
        self.state = "main"
        self.add_log("Credit card approved! Your credit journey begins at a score of 550.", "good")

    # -------------------------------------------------------------- helpers --
    def price(self, amount):
        return int(round(amount * self.price_index))

    def wage(self, amount):
        return int(round(amount * self.wage_index))

    def quarter(self):
        return self.age_months // 3 + 1

    def add_log(self, text, tone="info"):
        self.log.append((f"{self.age_years} Q{self.quarter()}", text, tone))
        if len(self.log) > 80:
            self.log.pop(0)

    def unlock(self, key):
        if key not in self.achievements:
            self.achievements.append(key)
            name, desc = self.ACHIEVEMENTS[key]
            self.toasts.append((f"Achievement unlocked: {name} — {desc}", "gold"))

    @staticmethod
    def tier_for(score):
        for t in LifeGame.TIERS:
            if score >= t[0]:
                return t
        return LifeGame.TIERS[-1]

    def tier(self):
        return self.tier_for(self.credit_score)

    def loan_rate(self):
        return self.tier()[2]

    def card_rate(self):
        return self.tier()[3]

    def card_limit(self):
        return self.tier()[4] + self.limit_bonus

    def card_available(self):
        return max(0, self.card_limit() - self.card)

    def loan_capacity(self):
        return self.tier()[5]

    def loan_room(self):
        return max(0, self.loan_capacity() - self.loans)

    def overdraft_used(self):
        return max(0, -self.cash)

    def total_debt(self):
        return self.card + self.loans + self.overdraft_used()

    def get_net_worth(self):
        return self.cash + self.investments - self.card - self.loans

    def history_capped(self):
        return self.turns_played < self.HISTORY_CAP_TURNS

    def potential_income(self):
        return int(self.base_income * self.wage_index)

    def quarterly_income(self):
        mult = self.layoff_mult * (1.0 if self.has_car else 0.90)
        return int(self.potential_income() * mult)

    def essentials_breakdown(self):
        items = [
            ("Rent", self.price(self.RENT_BASE + self.rent_adj)),
            ("Groceries", self.price(self.FOOD_BASE)),
            ("Transport & bills", self.price(self.UTIL_BASE - (0 if self.has_car else self.NO_CAR_SAVING))),
        ]
        if self.has_pet:
            items.append(("Pet care", self.price(self.PET_COST)))
        creep = int(self.LIFESTYLE_CREEP * max(0, self.potential_income() - self.wage(self.START_INCOME)))
        if creep > 0:
            items.append(("Lifestyle", creep))
        return items

    def essentials_total(self):
        return sum(v for _, v in self.essentials_breakdown())

    def happiness_cost(self):
        return self.price(self.HAPPY_COST)

    def happiness_decay(self):
        return 12 + (8 * (self.age_years - 18)) // 47 - (3 if self.has_pet else 0)

    def withdraw_fee_rate(self):
        return 0.0 if self.age_years >= self.PENALTY_FREE_AGE else self.EARLY_WITHDRAW_PENALTY

    def remaining_due(self):
        return max(0, min(self.min_due - self.paid_this_qtr, self.card + self.loans))

    def can_retire_early(self):
        return self.state == "main" and self.get_net_worth() >= self.MILLION

    def final_score(self):
        nw = self.get_net_worth()
        if self.end_reason in ("RETIREMENT", "EARLY_RETIREMENT"):
            multiplier = 0.5 + (self.credit_score / 2000)
            return int(nw * multiplier) if nw >= 0 else int(nw)
        return int(min(nw, nw * 0.25) - self.DEATH_PENALTY)

    # --------------------------------------------------------- credit score --
    def _credit(self, status, reason):
        before = self.credit_score
        if status == "missing":
            delta = -50
            self.streak = 0
            self.stats["missed"] += 1
        elif status == "late":
            delta = -20
            self.streak = 0
            self.stats["late"] += 1
        else:  # on_time
            self.streak += 1
            self.best_streak = max(self.best_streak, self.streak)
            self.stats["on_time"] += 1
            if before >= 800:
                delta = self.rng.choice([0, 1])            # very high score: +0 / +1
            elif before >= 700:
                delta = 2                                  # established: +2
            else:
                delta = 5 + (2 if self.streak >= 4 else 0)  # building: +5, +2 streak bonus
        new = max(0, min(1000, before + delta))
        capped = False
        if self.history_capped() and new > self.HISTORY_CAP:
            new = max(before, self.HISTORY_CAP)
            capped = True
        self.credit_score = new
        actual = new - before
        self.credit_reasons.append((actual, reason, status))

        if actual < 0:
            self.add_log(f"{reason}. Credit {actual:+d} → {new}", "bad")
        elif capped and actual < delta:
            self.add_log(f"{reason}. Credit {actual:+d} (capped at 700 until 5 years of history)", "good")
        else:
            self.add_log(f"{reason}. Credit {actual:+d} → {new}", "good")

        if status == "on_time":
            self.unlock("on_time")
            if self.streak >= 8:
                self.unlock("streak8")
        if self.credit_score >= 700:
            self.unlock("good_credit")
        if self.credit_score >= 800:
            self.unlock("excellent")
        t_before, t_after = self.tier_for(before), self.tier()
        if t_after[0] > t_before[0]:
            self.toasts.append((f"Credit tier up: {t_after[1]}! Card limit {money(self.card_limit())}, "
                                f"loan rate {t_after[2]:.2%}/qtr", "good"))

    def _credit_drop_popup(self, before):
        after = self.credit_score
        if after >= before:
            return
        drops = [r for r in self.credit_reasons if r[0] < 0]
        tb, ta = self.tier_for(before), self.tier()
        best = self.TIERS[0]
        items = "".join(f"<li>{esc(r)} <b style='color:#F87171'>({d:+d})</b></li>" for d, r, _ in drops)
        tier_html = ""
        if ta[0] < tb[0]:
            tier_html = (f"<p style='color:#FBBF24'><b>Tier dropped: {tb[1]} → {ta[1]}.</b> "
                         f"Loan rate {tb[2]:.2%} → {ta[2]:.2%}/qtr, card rate {tb[3]:.2%} → {ta[3]:.2%}/qtr, "
                         f"card limit {money(tb[4] + self.limit_bonus)} → {money(ta[4] + self.limit_bonus)}.</p>")
        extra = int(10000 * (ta[2] - best[2]))
        irs = ""
        if self.credit_score < self.IRS_SCORE:
            irs = (f" <b style='color:#F87171'>You are below 300 right now — still under 300 at the end of "
                   f"next quarter means strike {self.low_credit_turns + 1}/{self.IRS_TURNS}.</b>")
        body = (
            f"<p>Your score fell from <b>{before}</b> to <b style='color:#F87171'>{after}</b> "
            f"({after - before:+d}).</p>"
            f"<p><b>What happened</b></p><ul>{items}</ul>{tier_html}"
            "<p><b style='color:#F87171'>Why a low score hurts</b></p><ul>"
            f"<li><b>Expensive debt:</b> loans cost you {ta[2]:.2%}/qtr vs {best[2]:.2%} at 800+. "
            f"On a $10,000 loan that is {money(extra)} more <i>every quarter</i>.</li>"
            f"<li><b>Smaller card limit</b> ({money(self.card_limit())}) — less room for emergencies, "
            "so surprise bills spill into overdraft or collections.</li>"
            "<li><b>Loans denied</b> below a 450 score.</li>"
            f"<li><b>IRS seizure</b> if your score stays under 300 for 8 quarters — game over.{irs}</li>"
            "<li><b>Lower final score</b> — your retirement multiplier is 0.5 + score/2000.</li></ul>"
            "<p><b style='color:#4ADE80'>How to rebuild it</b></p><ul>"
            "<li>Pay at least the <b>minimum due</b> shown on the dashboard every quarter <i>before</i> "
            "pressing Advance: +5 per on-time payment, +2 bonus once you're on a 4-quarter streak.</li>"
            "<li>Paying something but less than the minimum is still <b>late (-20)</b>; paying nothing is "
            "<b>missed (-50)</b>.</li>"
            "<li>Keep an emergency cash cushion so surprise bills never go to collections (-50).</li>"
            "<li>Using your card is fine — <b>only unpaid debt lowers your score</b>. Charging and paying on "
            "time is how you climb.</li></ul>"
        )
        self.popups.append({"title": "Your credit score dropped", "body": body,
                            "kind": "warning", "guide": True})

    # --------------------------------------------------------- money moves --
    def _note_debt(self):
        if self.total_debt() > 0:
            self.had_debt = True

    def buy_happiness(self):
        cost = self.happiness_cost()
        if self.happiness >= 100:
            return False, "Happiness is already full"
        if self.cash < cost:
            return False, f"Need {money(cost)} cash"
        self.cash -= cost
        self.happiness = min(100, self.happiness + self.HAPPY_PTS)
        self.add_log(f"Spent {money(cost)} on leisure & hobbies. Happiness +{self.HAPPY_PTS}", "good")
        return True, ""

    def invest(self, amount):
        if amount <= 0:
            return False, "Choose an amount above $0"
        if self.cash < amount:
            return False, f"Not enough cash (you have {money(self.cash)})"
        self.cash -= amount
        self.investments += amount
        self.add_log(f"Invested {money(amount)} in the stock market", "invest")
        self.unlock("investor")
        return True, ""

    def withdraw(self, amount):
        if self.investments <= 0:
            return False, "You have no investments"
        amt = min(amount, self.investments)
        if amt <= 0:
            return False, "Choose an amount above $0"
        fee = int(amt * self.withdraw_fee_rate())
        self.investments -= amt
        self.cash += amt - fee
        self.stats["fees"] += fee
        msg = f"Withdrew {money(amt - fee)} from investments" + (f" (early-withdrawal fee {money(fee)})" if fee else "")
        self.add_log(msg, "warn" if fee else "invest")
        return True, ""

    def loan_block_reason(self, amount):
        if self.loan_capacity() <= 0:
            return f"Loans need a {self.LOAN_MIN_SCORE}+ credit score"
        if amount > self.loan_room():
            return f"Loan limit reached ({money(self.loan_room())} left)"
        return None

    def take_loan(self, amount):
        if amount <= 0:
            return False, "Choose an amount above $0"
        reason = self.loan_block_reason(amount)
        if reason:
            self.add_log(f"Loan of {money(amount)} denied: {reason}", "bad")
            return False, reason
        fee = math.ceil(amount * self.LOAN_ORIGINATION)
        self.loans += amount + fee
        self.cash += amount
        self.stats["fees"] += fee
        self._note_debt()
        self.add_log(f"Bank loan of {money(amount)} at {self.loan_rate():.2%}/qtr (+{money(fee)} fee)", "warn")
        return True, ""

    def _apply_payment(self, pay):
        to_card = min(pay, self.card)
        self.card -= to_card
        to_loans = pay - to_card
        self.loans -= to_loans
        self.cash -= pay
        self.paid_this_qtr += pay
        self.paid_card_this_qtr += to_card
        if self.card + self.loans == 0 and self.had_debt and self.cash >= 0:
            self.unlock("debt_free")
        return to_card, to_loans

    def pay_debt(self, amount):
        owed = self.card + self.loans
        if owed <= 0:
            return False, "You have no card or loan debt"
        if self.cash <= 0:
            return False, "No cash available to pay with"
        pay = min(amount, self.cash, owed)
        if pay <= 0:
            return False, "Choose an amount above $0"
        to_card, to_loans = self._apply_payment(pay)
        parts = []
        if to_card:
            parts.append(f"card {money(to_card)}")
        if to_loans:
            parts.append(f"loans {money(to_loans)}")
        self.add_log(f"Paid {money(pay)} toward debt ({', '.join(parts)})", "good")
        return True, ""

    def pay_minimum(self):
        r = self.remaining_due()
        if r <= 0:
            return False, "This quarter's minimum is already covered"
        return self.pay_debt(r)

    def pay_all(self):
        return self.pay_debt(self.card + self.loans)

    def retire_early(self):
        if not self.can_retire_early():
            return False, "Net worth must be at least $1,000,000"
        self.state = "game_over"
        self.end_reason = "EARLY_RETIREMENT"
        return True, ""

    # ----------------------------------------------------------- quarter ---
    def _evaluate_payments(self):
        if self.min_due <= 0:
            return
        paid, due = self.paid_this_qtr, self.min_due
        if paid >= due or (self.card + self.loans == 0 and paid > 0):
            self._credit("on_time", f"On-time payment ({money(paid)} paid, {money(due)} minimum)")
        elif paid > 0:
            self._credit("late", f"Late payment: paid only {money(paid)} of the {money(due)} minimum")
        else:
            self._credit("missing", f"Missed payment: $0 paid of the {money(due)} minimum")

    def _charge_interest(self):
        if self.card > 0 and self.stmt_card > 0 and self.paid_card_this_qtr < self.stmt_card:
            i = math.ceil(self.card * self.card_rate())
            self.card += i
            self.stats["interest"] += i
            self.add_log(f"Card interest +{money(i)} ({self.card_rate():.2%}/qtr) — pay the full statement to avoid it", "bad")
        elif self.stmt_card > 0:
            self.add_log("Statement paid in full — no card interest this quarter (grace period)", "good")
        if self.loans > 0:
            i = math.ceil(self.loans * self.loan_rate())
            self.loans += i
            self.stats["interest"] += i
            self.add_log(f"Loan interest +{money(i)} ({self.loan_rate():.2%}/qtr)", "bad")
        if self.cash < 0:
            i = math.ceil(-self.cash * self.OVERDRAFT_RATE) + self.OVERDRAFT_FEE
            self.cash -= i
            self.stats["fees"] += i
            self.add_log(f"Overdraft fee & interest -{money(i)}", "bad")
        if self.card > self.card_limit():
            self.card += self.OVER_LIMIT_FEE
            self.stats["fees"] += self.OVER_LIMIT_FEE
            self.add_log(f"Card is over its {money(self.card_limit())} limit: {money(self.OVER_LIMIT_FEE)} fee", "bad")

    def _collections(self, amount, label):
        fee = math.ceil(amount * self.COLLECTIONS_FEE)
        self.loans += amount + fee
        self.stats["fees"] += fee
        self._note_debt()
        self._credit("missing", f"{label}: {money(amount)} unpaid and sent to collections (+{money(fee)} fee)")

    def _forced_payment(self, amount, label):
        """Compulsory costs: (card if autopay) -> cash -> overdraft -> card -> collections."""
        remaining = amount
        used_card = 0
        if self.essentials_on_card:
            use = min(remaining, self.card_available())
            self.card += use
            used_card += use
            remaining -= use
        use = min(remaining, max(0, self.cash))
        self.cash -= use
        remaining -= use
        if remaining > 0:
            room = self.OVERDRAFT_LIMIT - self.overdraft_used()
            use = min(remaining, max(0, room))
            if use:
                self.cash -= use
                remaining -= use
                self.add_log(f"Not enough cash for {label.lower()} — {money(use)} went into overdraft", "bad")
        if remaining > 0:
            use = min(remaining, self.card_available())
            if use:
                self.card += use
                used_card += use
                remaining -= use
                self.add_log(f"Overdraft maxed — {money(use)} charged to your card", "warn")
        if used_card:
            self.unlock("first_swipe")
        if remaining > 0:
            self._collections(remaining, label)
        self._note_debt()
        return used_card

    def _post_statement(self):
        card_due = 0
        if self.card > 0:
            card_due = min(self.card, max(self.price(self.MIN_PAYMENT_FLOOR), math.ceil(self.card * self.CARD_MIN_PCT)))
        loan_due = 0
        if self.loans > 0:
            loan_due = min(self.loans, max(self.price(self.MIN_PAYMENT_FLOOR), math.ceil(self.loans * self.LOAN_MIN_PCT)))
        self.min_due = card_due + loan_due
        self.stmt_card = self.card
        self.paid_this_qtr = 0
        self.paid_card_this_qtr = 0
        if self.min_due:
            self.add_log(f"New statement: minimum payment {money(self.min_due)} due before next quarter", "warn")

    def next_turn(self):
        if self.state != "main":
            return
        start_score = self.credit_score
        self.credit_reasons = []

        self._evaluate_payments()
        self._charge_interest()

        self.turns_played += 1
        self.age_months += 3
        if self.age_months >= 12:
            self.age_years += 1
            self.age_months = 0

        if self.age_years >= 65:
            self.state = "game_over"
            self.end_reason = "RETIREMENT"
            self.unlock("golden")
            return

        self.price_index *= 1 + self.INFLATION_QTR
        self.wage_index *= 1 + self.RAISE_QTR

        earned = self.quarterly_income()
        self.cash += earned
        note = ""
        if self.layoff_turns > 0:
            self.layoff_turns -= 1
            note = f" ({int(self.layoff_mult * 100)}% pay)"
            if self.layoff_turns == 0:
                self.layoff_mult = 1.0
        self.add_log(f"Paycheck +{money(earned)}{note}", "good")
        if note and self.layoff_turns == 0:
            self.add_log("Back on full salary next quarter!", "good")

        ess = self.essentials_total()
        on_card = self._forced_payment(ess, "Essentials")
        self.add_log(f"Compulsory rent, groceries & bills -{money(ess)}" +
                     (f" ({money(on_card)} on card)" if on_card else ""), "info")

        decay = self.happiness_decay()
        self.happiness = max(0, self.happiness - decay)

        if self.investments > 0:
            if self.rng.random() < self.CRASH_CHANCE:
                change = -int(self.investments * self.rng.uniform(*self.CRASH_RANGE))
                self.investments = max(0, self.investments + change)
                self.add_log(f"MARKET CRASH! Investments fell {money(-change)}", "bad")
                self.unlock("storm")
            else:
                change = int(self.investments * self.rng.uniform(*self.INVEST_RANGE))
                self.investments = max(0, self.investments + change)
                self.add_log(f"Investments {'grew' if change >= 0 else 'fell'} {money(abs(change))}",
                             "invest" if change >= 0 else "bad")

        self._post_statement()
        self._milestones()

        if self.happiness <= 0:
            self.zero_happiness_turns += 1
            if self.zero_happiness_turns >= self.DEPRESSION_TURNS:
                self.state = "game_over"
                self.end_reason = "DEPRESSION"
                return
            self.add_log(f"Happiness is 0! Depression warning {self.zero_happiness_turns}/{self.DEPRESSION_TURNS}", "bad")
        else:
            self.zero_happiness_turns = 0

        if self.credit_score < self.IRS_SCORE:
            self.low_credit_turns += 1
            if self.low_credit_turns >= self.IRS_TURNS:
                self.state = "game_over"
                self.end_reason = "IRS_SEIZURE"
                return
            self.add_log(f"Credit under 300! IRS strike {self.low_credit_turns}/{self.IRS_TURNS}", "bad")
        else:
            self.low_credit_turns = 0

        self._credit_drop_popup(start_score)
        self._trigger_event()

    def _milestones(self):
        nw = self.get_net_worth()
        if nw >= 100_000:
            self.unlock("six_figures")
        if nw >= self.MILLION:
            self.unlock("millionaire")
            if not self.millionaire_notified:
                self.millionaire_notified = True
                self.popups.append({
                    "title": "You're a millionaire!", "kind": "success",
                    "body": "<p>Your net worth has passed <b>$1,000,000</b>.</p>"
                            "<p>You can now <b>retire early</b> from the dashboard at any time while your net "
                            "worth stays above $1M — or keep playing to grow your final score.</p>"})

    # -------------------------------------------------------------- events --
    def _draw_event_key(self):
        while self.scripted_events:
            key = self.scripted_events.pop(0)
            if self._event_applies(key):
                return key
        if self.age_months == 9 and self.rng.random() < 0.5 and self.last_event_key != "holiday":
            return "holiday"
        for _ in range(sum(self.EVENT_DECK.values()) * 2):
            if not self.event_deck:
                self.event_deck = [k for k, n in self.EVENT_DECK.items() for _ in range(n)]
                self.rng.shuffle(self.event_deck)
            key = self.event_deck.pop()
            if key == self.last_event_key or not self._event_applies(key):
                continue
            return key
        return "festival"

    def _event_applies(self, key):
        if key == "course":
            return self.courses_taken < self.MAX_COURSES
        if key in ("accident",):
            return self.has_car
        if key == "pet":
            return not self.has_pet
        if key == "limit_offer":
            return self.credit_score >= 600 and self.limit_bonus < 6000
        if key == "dip":
            return self.investments >= 500
        if key == "debt_offer":
            return self.card + self.loans > 0
        if key == "layoff":
            return self.layoff_turns == 0
        if key == "inheritance":
            return not self.inheritance_done
        return True

    def _trigger_event(self):
        key = self._draw_event_key()
        self.last_event_key = key
        ev = getattr(self, f"_ev_{key}")()
        ev["key"] = key
        self.current_event = ev
        self.state = "event"

    @staticmethod
    def O(label, pay=None, amount=0, tone="skip", log="", need=0, **fx):
        return {"label": label, "pay": pay, "amount": int(amount), "tone": tone,
                "log": log, "need": int(need), "fx": fx}

    def _collect_option(self, amt, what):
        return self.O(f"Ignore the bill — it goes to collections (+15% fee, -50 credit)",
                      "collections", amt, "bad", log=what)

    def _loan_label(self, amt):
        return f"Payment plan: {money(amt)} bank loan at {self.loan_rate():.2%}/qtr"

    def _ev_festival(self):
        c = self.price(450)
        return {"title": "Weekend Music Festival",
                "desc": "Your friends are heading to a 3-day music festival to recharge. Missing it will sting.",
                "options": [
                    self.O(f"Pay {money(c)} cash  (+18 happiness)", "cash", c, "cash", "Went to the festival", happiness=18),
                    self.O(f"Charge {money(c)} to credit card  (+18 happiness)", "card", c, "card", "Charged the festival", happiness=18),
                    self.O("Stay home  (-12 happiness)", None, 0, "skip", "Skipped the festival", happiness=-12)]}

    def _ev_market(self):
        a, b = self.price(1000), self.price(2000)
        return {"title": "Index Fund Opportunity",
                "desc": "A low-fee index fund is open to new investors. Investing early lets compounding work for decades — "
                        "but markets can fall, and borrowed money charges interest even when they do.",
                "options": [
                    self.O(f"Invest {money(a)} cash", "cash", a, "cash", f"Invested {money(a)} in an index fund", invest=a),
                    self.O(f"Borrow {money(b)} to invest (loan at {self.loan_rate():.2%}/qtr)", "loan", b, "loan",
                           f"Borrowed {money(b)} to invest", invest=b),
                    self.O("Pass", None, 0, "skip", "Passed on the index fund")]}

    def _ev_car(self):
        if self.has_car:
            c, s = self.price(700), self.price(1500)
            return {"title": "Car Trouble",
                    "desc": "Your car's transmission is slipping. Without a car your commute gets harder and your pay drops 10%.",
                    "options": [
                        self.O(f"Repair it: {money(c)} cash", "cash", c, "cash", "Repaired the car"),
                        self.O(f"Repair it: charge {money(c)} to card", "card", c, "card", "Charged the car repair"),
                        self.O(f"Sell the car (+{money(s)}, -10% pay, cheaper transport)", None, 0, "bad",
                               f"Sold the car for {money(s)}", cash=s, has_car=False)]}
        c = self.price(3000)
        return {"title": "Commute Struggles",
                "desc": "Bus delays are wrecking your schedule. A used car would restore your full pay.",
                "options": [
                    self.O(f"Buy a used car: {money(c)} cash", "cash", c, "cash", "Bought a used car", has_car=True),
                    self.O(f"Finance it: {money(c)} loan at {self.loan_rate():.2%}/qtr", "loan", c, "loan", "Financed a used car", has_car=True),
                    self.O("Keep taking the bus  (-10 happiness)", None, 0, "skip", "Stuck with the bus", happiness=-10)]}

    def _ev_vacation(self):
        c, w = self.price(1300), self.wage(600)
        return {"title": "Beach Vacation",
                "desc": "A week at the beach would do wonders for your mood — or you could pick up overtime instead.",
                "options": [
                    self.O(f"Book it: {money(c)} cash  (+30 happiness)", "cash", c, "cash", "Took a beach vacation", happiness=30),
                    self.O(f"Charge {money(c)} to card  (+30 happiness)", "card", c, "card", "Charged a beach vacation", happiness=30),
                    self.O(f"Work overtime instead  (+{money(w)}, -12 happiness)", None, 0, "good",
                           f"Worked overtime (+{money(w)})", cash=w, happiness=-12)]}

    def _ev_course(self):
        c = self.price(self.COURSE_BASE_COST * (1.35 ** self.courses_taken))
        b = self.wage(self.COURSE_BONUS)
        q = math.ceil(c / max(1, b * (1 - self.LIFESTYLE_CREEP)))
        return {"title": "Career Certification",
                "desc": f"Certification {self.courses_taken + 1} of {self.MAX_COURSES}: permanently raises your pay by "
                        f"{money(b)}/qtr. After lifestyle creep it pays for itself in about {q} quarters.",
                "options": [
                    self.O(f"Pay {money(c)} cash", "cash", c, "cash", "Completed a certification", course=True),
                    self.O(f"Charge {money(c)} to card", "card", c, "card", "Completed a certification (on card)", course=True),
                    self.O(f"Student loan: {money(c)} at {self.loan_rate():.2%}/qtr", "loan", c, "loan",
                           "Completed a certification (student loan)", course=True),
                    self.O("Skip it", None, 0, "skip", "Skipped the certification")]}

    def _ev_credit_quiz(self):
        if not self.quiz_pool:
            self.quiz_pool = list(range(len(self.QUIZ)))
            self.rng.shuffle(self.quiz_pool)
        q, answers, explain = self.QUIZ[self.quiz_pool.pop()]
        order = list(range(3))
        self.rng.shuffle(order)
        opts = [self.O(answers[i], None, 0, "info", "", quiz=(i == 0)) for i in order]
        return {"title": "Credit Workshop Quiz",
                "desc": f"A free community credit workshop ends with a quick question. Answer correctly to win a "
                        f"{money(int(round(self.price(150), -1)))} gift card.\n\n{q}",
                "explain": explain, "options": opts}

    def _ev_layoff(self):
        s = self.wage(1500)
        return {"title": "Company Layoffs",
                "desc": "Your company is downsizing and your role is cut. This is exactly why an emergency fund "
                        "(3-6 months of essentials) matters.",
                "options": [
                    self.O(f"Take severance: +{money(s)} now, 50% pay for 2 quarters", None, 0, "loan",
                           f"Laid off with {money(s)} severance", cash=s, layoff=(2, 0.5)),
                    self.O("Take a temp contract: 75% pay for 2 quarters", None, 0, "skip",
                           "Took a temp contract", layoff=(2, 0.75))]}

    def _ev_medical(self):
        c = self.price(1400)
        return {"title": "Medical Emergency",
                "desc": f"A trip to the ER leaves you with a {money(c)} bill. This one isn't optional.",
                "options": [
                    self.O(f"Pay {money(c)} cash", "cash", c, "cash", "Paid the hospital bill"),
                    self.O(f"Charge {money(c)} to card", "card", c, "card", "Charged the hospital bill"),
                    self.O(self._loan_label(c), "loan", c, "loan", "Hospital payment plan"),
                    self._collect_option(c, "Hospital bill")]}

    def _ev_phone(self):
        new, used = self.price(900), self.price(300)
        return {"title": "Phone Smashed",
                "desc": "Your phone slipped and the screen is shattered beyond repair.",
                "options": [
                    self.O(f"New flagship phone: charge {money(new)} to card  (+5 happiness)", "card", new, "card",
                           "Bought a new phone on card", happiness=5),
                    self.O(f"Refurbished phone: {money(used)} cash", "cash", used, "cash", "Bought a refurbished phone"),
                    self.O("Go without a phone  (-12 happiness)", None, 0, "skip", "Went without a phone", happiness=-12)]}

    def _ev_rent_hike(self):
        hike, move = 250, self.price(900)
        opts = [self.O(f"Accept the increase (+{money(self.price(hike))}/qtr rent forever)", None, 0, "bad",
                       "Accepted a rent increase", rent=hike)]
        if not self.has_roommate:
            opts.append(self.O(f"Get a roommate (rent -{money(self.price(300))}/qtr, -15 happiness)", None, 0, "good",
                               "Got a roommate", rent=-300, roommate=True, happiness=-15))
        opts += [self.O(f"Move somewhere cheaper: {money(move)} cash moving costs (-8 happiness)", "cash", move, "cash",
                        "Moved to avoid the rent hike", happiness=-8),
                 self.O(f"Move: charge {money(move)} moving costs to card (-8 happiness)", "card", move, "card",
                        "Moved (moving costs on card)", happiness=-8)]
        return {"title": "Rent Increase",
                "desc": f"Your landlord is raising rent by {money(self.price(hike))} per quarter, permanently.",
                "options": opts}

    def _ev_side_hustle(self):
        w = self.wage(700)
        return {"title": "Weekend Side Hustle",
                "desc": "A friend needs help with weekend deliveries for the next few months.",
                "options": [
                    self.O(f"Take the gig  (+{money(w)}, -12 happiness)", None, 0, "good", f"Side hustle +{money(w)}",
                           cash=w, happiness=-12),
                    self.O("Decline — protect your weekends", None, 0, "skip", "Declined the side hustle")]}

    def _ev_wedding(self):
        c = self.price(700)
        return {"title": "Friend's Wedding",
                "desc": "Your close friend is getting married out of town. Travel, hotel and a gift add up.",
                "options": [
                    self.O(f"Go: {money(c)} cash  (+10 happiness)", "cash", c, "cash", "Went to the wedding", happiness=10),
                    self.O(f"Go: charge {money(c)} to card  (+10 happiness)", "card", c, "card", "Charged the wedding trip", happiness=10),
                    self.O("Send regrets  (-15 happiness)", None, 0, "skip", "Missed the wedding", happiness=-15)]}

    def _ev_tax_refund(self):
        r = self.wage(900)
        opts = [self.O(f"Save it (+{money(r)} cash)", None, 0, "cash", f"Saved a {money(r)} tax refund", cash=r),
                self.O(f"Invest it (+{money(r)} investments)", None, 0, "info", f"Invested a {money(r)} tax refund", invest=r)]
        if self.card + self.loans > 0:
            opts.append(self.O(f"Put it toward debt ({money(r)})", None, 0, "good", "Paid debt with the tax refund", cash=r, pay_debt=r))
        opts.append(self.O("Treat yourself (+20 happiness)", None, 0, "card", "Splurged the tax refund", happiness=20))
        return {"title": "Tax Refund", "desc": f"You overpaid taxes last year and got {money(r)} back.", "options": opts}

    def _ev_limit_offer(self):
        return {"title": "Credit Limit Increase",
                "desc": "Thanks to your good payment record, the bank offers to raise your card limit by $2,000.",
                "info": "A higher limit gives you more room for emergencies so surprise bills don't hit overdraft or "
                        "collections. In this game, using your card never hurts your score — only unpaid minimums do. "
                        "The risk is temptation: more credit makes overspending easier.",
                "options": [
                    self.O("Accept (+$2,000 card limit)", None, 0, "card", "Card limit raised by $2,000", limit_bonus=2000),
                    self.O("Decline", None, 0, "skip", "Declined a limit increase")]}

    def _ev_identity_theft(self):
        f = self.price(800)
        return {"title": "Suspicious Charges!",
                "desc": f"{money(f)} of purchases you never made just showed up on your credit card.",
                "info": "Always read your statements. Reporting fraud quickly gets charges reversed — ignoring it means "
                        "you're stuck paying them (plus interest).",
                "options": [
                    self.O("Report it to your bank right away (charges reversed, -5 happiness hassle)", None, 0, "good",
                           "Reported fraud — charges reversed", happiness=-5),
                    self.O(f"Ignore it (the {money(f)} stays on your card)", None, 0, "bad",
                           f"Ignored fraud — {money(f)} stays on the card", card_charge=f)]}

    def _ev_pet(self):
        c = self.price(600)
        return {"title": "Adopt a Dog?",
                "desc": f"A shelter puppy picked you. Adoption costs {money(c)}, food & vet add "
                        f"{money(self.price(self.PET_COST))}/qtr forever — but your happiness decays 3 less per quarter.",
                "options": [
                    self.O(f"Adopt: {money(c)} cash  (+25 happiness)", "cash", c, "cash", "Adopted a dog!", happiness=25, pet=True),
                    self.O(f"Adopt: charge {money(c)} to card  (+25 happiness)", "card", c, "card", "Adopted a dog (on card)", happiness=25, pet=True),
                    self.O("Not right now", None, 0, "skip", "Didn't adopt")]}

    def _ev_review(self):
        r = self.wage(450)
        chance = min(0.85, 0.45 + 0.08 * self.courses_taken)
        return {"title": "Performance Review",
                "desc": f"Annual review time. Your certifications give you a {int(chance * 100)}% chance if you ask for a raise.",
                "options": [
                    self.O(f"Ask for a raise (+{money(r)}/qtr if it works, -5 happiness if not)", None, 0, "good", "",
                           gamble=(chance, {"income": 450, "log": f"Raise approved! +{money(r)}/qtr"},
                                   {"happiness": -5, "log": "Raise request denied"})),
                    self.O(f"Volunteer for a big project (+{money(self.wage(300))}/qtr, -15 happiness)", None, 0, "loan",
                           "Took on extra responsibility", income=300, happiness=-15),
                    self.O("Keep your head down", None, 0, "skip", "Quiet review")]}

    def _ev_crypto(self):
        c = self.price(1000)
        return {"title": "Crypto Hype",
                "desc": "A coworker swears a new coin will 'definitely 10x'. He wants you in today.",
                "info": "High-risk speculation is not investing. Never put in money you can't afford to lose — and "
                        "never borrow to gamble.",
                "options": [
                    self.O(f"Buy {money(c)} of the coin (cash)", "cash", c, "bad", "",
                           gamble=(0.30, {"cash": c * 3, "log": f"The coin mooned! Sold for {money(c * 3)}"},
                                   {"cash": c // 10, "log": f"The coin crashed 90%. Recovered {money(c // 10)}"})),
                    self.O("Pass — stick to what you understand", None, 0, "skip", "Passed on crypto")]}

    def _ev_inheritance(self):
        self.inheritance_done = True
        g = self.wage(3000)
        opts = [self.O(f"Keep it as an emergency fund (+{money(g)} cash)", None, 0, "cash", f"Inherited {money(g)}", cash=g),
                self.O(f"Invest it (+{money(g)} investments)", None, 0, "info", f"Invested a {money(g)} inheritance", invest=g)]
        if self.card + self.loans > 0:
            opts.append(self.O("Pay down debt with it", None, 0, "good", "Paid debt with an inheritance", cash=g, pay_debt=g))
        return {"title": "Small Inheritance",
                "desc": f"A great-aunt you barely knew left you {money(g)}.", "options": opts}

    def _ev_accident(self):
        c = self.price(1800)
        return {"title": "Fender Bender",
                "desc": f"Someone backed into you. Your insurance deductible is {money(c)}.",
                "options": [
                    self.O(f"Pay {money(c)} cash", "cash", c, "cash", "Paid the deductible"),
                    self.O(f"Charge {money(c)} to card", "card", c, "card", "Charged the deductible"),
                    self.O(self._loan_label(c), "loan", c, "loan", "Deductible payment plan"),
                    self._collect_option(c, "Insurance deductible")]}

    def _ev_scam(self):
        c = self.price(500)
        return {"title": "Urgent Call from the 'IRS'",
                "desc": f"A caller says you owe back taxes and will be arrested unless you pay {money(c)} in gift cards today.",
                "options": [
                    self.O("Hang up and report the number", None, 0, "good", "Spotted a scam call", happiness=5,
                           popup={"title": "Scam avoided!", "kind": "success",
                                  "body": "<p>Real tax agencies never call demanding gift cards, wire transfers or crypto. "
                                          "Hang up, and contact the agency directly using its official number.</p>"}),
                    self.O(f"Pay {money(c)} in gift cards", "cash", c, "bad", f"Lost {money(c)} to a phone scam", happiness=-10,
                           popup={"title": "That was a scam", "kind": "warning",
                                  "body": "<p>The money is gone — gift cards are untraceable. Real tax agencies never demand "
                                          "gift cards or threaten arrest over the phone.</p>"})]}

    def _ev_dip(self):
        before = self.investments
        self.investments = int(self.investments * 0.88)
        self.add_log(f"Markets slid 12% — investments fell {money(before - self.investments)}", "bad")
        b = self.price(1000)
        fee = int(self.investments * self.withdraw_fee_rate())
        return {"title": "Market Slump",
                "desc": f"Markets fell 12% this quarter and your portfolio dropped to {money(self.investments)}. "
                        "Headlines are screaming 'recession'.",
                "info": "Historically, markets have recovered from every slump — but selling in a panic locks in your losses.",
                "options": [
                    self.O("Hold steady", None, 0, "skip", "Held investments through the slump"),
                    self.O(f"Buy the dip: invest {money(b)} cash", "cash", b, "cash", f"Bought the dip ({money(b)})", invest=b),
                    self.O(f"Panic-sell everything (fee {money(fee)})", None, 0, "bad", "Panic-sold investments", sell_all=True)]}

    def _ev_bonus(self):
        b = self.wage(1000)
        return {"title": "Year-End Bonus",
                "desc": f"Great work this year! Your manager hands you a {money(b)} bonus.",
                "options": [
                    self.O(f"Save it (+{money(b)} cash)", None, 0, "cash", f"Saved a {money(b)} bonus", cash=b),
                    self.O(f"Invest it (+{money(b)} investments)", None, 0, "info", f"Invested a {money(b)} bonus", invest=b),
                    self.O("Celebrate (+20 happiness)", None, 0, "card", "Celebrated the bonus", happiness=20)]}

    def _ev_holiday(self):
        c = self.price(550)
        return {"title": "Holiday Season",
                "desc": "Gifts, travel home and holiday dinners. Everyone else seems to be spending.",
                "options": [
                    self.O(f"Celebrate: {money(c)} cash  (+12 happiness)", "cash", c, "cash", "Holiday celebrations", happiness=12),
                    self.O(f"Celebrate: charge {money(c)} to card  (+12 happiness)", "card", c, "card", "Holidays on the card", happiness=12),
                    self.O("Skip gifts this year  (-15 happiness)", None, 0, "skip", "Skipped the holidays", happiness=-15)]}

    def _ev_debt_offer(self):
        owed = self.card + self.loans
        pay = min(owed, self.price(1000))
        waive = min(owed - pay, self.price(100))
        return {"title": "Pay-Down Challenge",
                "desc": f"Your bank will waive {money(waive)} of fees if you pay {money(pay)} toward your debt right now. "
                        "This counts toward your minimum payment.",
                "options": [
                    self.O(f"Pay {money(pay)} now" + (f" ({money(waive)} waived)" if waive else ""), None, 0, "good",
                           "Took the pay-down challenge", need=pay, pay_debt=pay, waive=waive),
                    self.O("Not now", None, 0, "skip", "Skipped the pay-down challenge")]}

    # ------------------------------------------------------ option choices --
    def option_block_reason(self, o):
        p, a = o["pay"], o["amount"]
        if p == "cash" and self.cash < a:
            return f"need {money(a)} cash"
        if p == "card" and self.card_available() < a:
            return f"only {money(self.card_available())} card credit left"
        if p == "loan":
            r = self.loan_block_reason(a)
            if r:
                return r[0].lower() + r[1:]
        if o["need"] and self.cash < o["need"]:
            return f"need {money(o['need'])} cash"
        return None

    def _apply_fx(self, fx):
        for k, v in fx.items():
            if k == "happiness":
                self.happiness = max(0, min(100, self.happiness + v))
            elif k == "cash":
                self.cash += v
            elif k == "invest":
                self.investments += v
                self.unlock("investor")
            elif k == "income":
                self.base_income += v
            elif k == "rent":
                self.rent_adj = max(-600, self.rent_adj + v)
            elif k == "roommate":
                self.has_roommate = True
            elif k == "has_car":
                self.has_car = v
            elif k == "pet":
                self.has_pet = True
            elif k == "layoff":
                self.layoff_turns, self.layoff_mult = v
            elif k == "course":
                self.courses_taken += 1
                self.base_income += self.COURSE_BONUS
                if self.courses_taken >= self.MAX_COURSES:
                    self.unlock("learner")
            elif k == "limit_bonus":
                self.limit_bonus += v
            elif k == "card_charge":
                self.card += v
                self._note_debt()
            elif k == "pay_debt":
                pay = min(v, self.card + self.loans, max(0, self.cash))
                if pay > 0:
                    self._apply_payment(pay)
                    self.add_log(f"Paid {money(pay)} toward debt", "good")
            elif k == "waive":
                w = min(v, self.loans)
                self.loans -= w
                self.card -= min(v - w, self.card)
            elif k == "sell_all":
                amt = self.investments
                fee = int(amt * self.withdraw_fee_rate())
                self.investments = 0
                self.cash += amt - fee
                self.stats["fees"] += fee
            elif k == "gamble":
                chance, win, lose = v
                won = self.rng.random() < chance
                res = dict(win if won else lose)
                log = res.pop("log", "")
                self._apply_fx(res)
                if log:
                    self.add_log(log, "good" if won else "warn")
            elif k == "popup":
                self.popups.append(v)

    def choose_option(self, idx):
        if self.state != "event":
            return False, ""
        ev = self.current_event
        o = ev["options"][idx]
        reason = self.option_block_reason(o)
        if reason:
            return False, reason
        start_score = self.credit_score
        self.credit_reasons = []
        p, a = o["pay"], o["amount"]
        if p == "cash":
            self.cash -= a
        elif p == "card":
            self.card += a
            self._note_debt()
            self.unlock("first_swipe")
        elif p == "loan":
            fee = math.ceil(a * self.LOAN_ORIGINATION)
            self.loans += a + fee
            self.stats["fees"] += fee
            self._note_debt()
        elif p == "collections":
            self._collections(a, o["log"] or "Bill")

        fx = dict(o["fx"])
        quiz = fx.pop("quiz", None)
        self._apply_fx(fx)

        if o["log"] and p != "collections":
            tone = {"cash": "info", "card": "card", "loan": "warn", "bad": "bad", "good": "good", "info": "invest"}.get(o["tone"], "info")
            self.add_log(o["log"] + (f" (-{money(a)})" if p == "cash" and a else
                                     f" ({money(a)} on card)" if p == "card" else
                                     f" ({money(a)} loan)" if p == "loan" else ""), tone)

        if quiz is not None:
            if quiz:
                prize = int(round(self.price(150), -1))
                self.cash += prize
                self.happiness = min(100, self.happiness + 5)
                self.quiz_correct += 1
                if self.quiz_correct >= 3:
                    self.unlock("quiz_whiz")
                self.add_log(f"Aced the credit quiz! +{money(prize)} gift card", "good")
                title, kind = "Correct!", "success"
            else:
                self.add_log("Missed the credit quiz question", "warn")
                title, kind = "Not quite", "info"
            correct = next(x["label"] for x in ev["options"] if x["fx"].get("quiz"))
            self.popups.append({"title": title, "kind": kind,
                                "body": f"<p><b>Answer:</b> {esc(correct)}</p><p>{esc(ev['explain'])}</p>"})

        self._milestones()
        self._credit_drop_popup(start_score)
        self.current_event = None
        self.state = "main"
        return True, ""

    # ---------------------------------------------------------- the guide --
    def credit_guide_html(self):
        rows = "".join(
            f"<tr><td><b>{n}</b></td><td>{s}+</td><td>{lr:.2%}</td><td>{cr:.2%}</td>"
            f"<td>{money(lim)}</td><td>{money(cap) if cap else 'Denied'}</td></tr>"
            for s, n, lr, cr, lim, cap in self.TIERS)
        return (
            "<p>Your <b>credit score</b> (0 - 1000) is how much lenders trust you. You start at <b>550</b> "
            "with a brand-new credit card.</p>"
            "<p><b style='color:#FACC15'>How the score moves</b> — it only changes when a bill is due:</p><ul>"
            "<li>Each quarter your card and loans post a <b>statement</b> with a <b>minimum payment due</b> "
            "(10% of the card balance, 8% of loans). It's shown on the dashboard.</li>"
            "<li><b style='color:#4ADE80'>On time</b> (paid at least the minimum before advancing): "
            "+5 while building (under 700), +2 bonus on a 4+ quarter streak; +2 from 700-799; +0 or +1 at 800+.</li>"
            "<li><b style='color:#FBBF24'>Late</b> (paid something, but less than the minimum): -20.</li>"
            "<li><b style='color:#F87171'>Missed</b> (paid nothing) or a bill sent to collections: -50.</li>"
            "<li>Swiping your card or carrying a balance does <b>not</b> lower your score — only unpaid "
            "minimums do. No debt means no statement, and your score simply holds.</li>"
            "<li><b>History cap:</b> you can't pass 700 until you have 5 years (20 quarters) of history.</li></ul>"
            "<p><b style='color:#FACC15'>What your tier gets you</b> (rates are per quarter):</p>"
            "<table cellspacing='0' cellpadding='6' width='100%'>"
            "<tr style='color:#8A97B1'><td>Tier</td><td>Score</td><td>Loan</td><td>Card</td><td>Card limit</td><td>Max loans</td></tr>"
            f"{rows}</table>"
            "<p><b style='color:#FACC15'>Limits, interest & fees</b></p><ul>"
            "<li><b>Card limit:</b> purchases that would go over your limit are declined.</li>"
            "<li><b>Grace period:</b> pay the full statement balance and you pay no card interest that quarter.</li>"
            f"<li><b>Overdraft:</b> if essentials exceed your cash, your bank balance can go down to "
            f"-{money(self.OVERDRAFT_LIMIT)} ({money(self.OVERDRAFT_FEE)} fee + 5% interest per quarter). "
            "Beyond that it goes on your card, and beyond your card limit it goes to <b>collections</b> "
            "(+15% fee and -50 credit).</li>"
            "<li><b>Bank loans</b> are cheaper than cards but need a 450+ score; a 2% fee is added up front.</li>"
            "<li>Payments always go to the highest-interest balance (your card) first.</li></ul>"
            "<p><b style='color:#F87171'>Danger zone</b></p><ul>"
            "<li>Below 450: no loans. Below 300 for 8 straight quarters: the IRS seizes your assets (game over).</li>"
            "<li>At retirement your net worth is multiplied by 0.5 + score/2000 — a 900 score is worth 30% more "
            "than a 300 score.</li></ul>"
            "<p><b style='color:#4ADE80'>Pro tip:</b> turn on <i>Charge essentials to card</i>, then pay the "
            "statement in full each quarter. You'll build credit every quarter and never pay card interest.</p>"
        )


# =============================================================================
#                                  UI LAYER
# =============================================================================
# Mobile: 1080x1920 portrait canvas.
# Desktop: 2880x1620 landscape canvas (1.5x a 1080p screen). Elements use the same pixel
# sizes as mobile, so on a desktop monitor they appear ~1/3 smaller with much more
# whitespace (desktop type scale: ~14-16px body, ~28-32px figures; 8pt spacing grid with
# 16-24px card padding, ~24px card gaps and ~64px page margins at 1x).
CANVAS = {"mobile": (1080, 1920), "desktop": (2880, 1620)}

_TINTS_LIGHT = {  # name: (background, hover background, text)
    "blue":   ("#E0E7FF", "#C7D2FE", "#312E81"),
    "purple": ("#EDE9FE", "#DDD6FE", "#4C1D95"),
    "amber":  ("#FEF3C7", "#FDE68A", "#78350F"),
    "teal":   ("#CCFBF1", "#99F6E4", "#134E4A"),
    "green":  ("#DCFCE7", "#BBF7D0", "#14532D"),
    "red":    ("#FEE2E2", "#FECACA", "#7F1D1D"),
    "pink":   ("#FCE7F3", "#FBCFE8", "#831843"),
    "slate":  ("#F1F2F5", "#E4E6EB", "#1F2937"),
}
_TINTS_DARK = {
    "blue":   ("#23274A", "#2E3363", "#C7D2FE"),
    "purple": ("#2A2347", "#362D5C", "#DDD6FE"),
    "amber":  ("#33270F", "#443416", "#FDE68A"),
    "teal":   ("#0F2E2B", "#153F3A", "#99F6E4"),
    "green":  ("#11301D", "#174027", "#BBF7D0"),
    "red":    ("#3A1717", "#4B1E1E", "#FECACA"),
    "pink":   ("#3A1A2A", "#4B2237", "#FBCFE8"),
    "slate":  ("#20242D", "#2B303B", "#E5E7EB"),
}
THEMES = {
    "light": dict(
        bg_top="#F4F5F7", bg_bot="#E6E9EE", card="#FFFFFF", border="#E7E9ED", border_strong="#CDD2DA",
        surface="#F4F5F8", text="#0F1115", text2="#374151", muted="#6B7280", dim="#A3A9B5", track="#ECEEF2",
        primary="#111317", primary_hover="#2B2E35", primary_text="#FFFFFF",
        accent="#4F46E5", accent_hover="#4338CA", accent_text="#FFFFFF",
        danger="#DC2626", danger_hover="#B91C1C", danger_text="#FFFFFF",
        modal="#FFFFFF", modal_border="#E7E9ED", overlay=(17, 19, 24, 110), coach=(10, 12, 18, 150),
        disabled_bg="#F1F2F4", disabled_text="#B4BAC4",
        green="#16A34A", red="#DC2626", amber="#D97706", gold="#B7791F", blue="#4F46E5",
        purple="#7C3AED", teal="#0D9488", lime="#65A30D", pink="#DB2777",
        seg_fill="#A5B4FC", tints=_TINTS_LIGHT, solid_green_text="#FFFFFF"),
    "dark": dict(
        bg_top="#0F1116", bg_bot="#07080B", card="#16191F", border="#242832", border_strong="#3D4350",
        surface="#1D2129", text="#F4F5F7", text2="#D1D5DB", muted="#9CA3AF", dim="#5F6673", track="#232833",
        primary="#F4F5F7", primary_hover="#FFFFFF", primary_text="#0F1115",
        accent="#818CF8", accent_hover="#A5B4FC", accent_text="#0B0D2A",
        danger="#F87171", danger_hover="#FCA5A5", danger_text="#1A0505",
        modal="#16191F", modal_border="#2B303B", overlay=(0, 0, 0, 170), coach=(0, 0, 0, 185),
        disabled_bg="#1A1D23", disabled_text="#4B5160",
        green="#4ADE80", red="#F87171", amber="#FBBF24", gold="#FACC15", blue="#818CF8",
        purple="#A78BFA", teal="#2DD4BF", lime="#A3E635", pink="#F472B6",
        seg_fill="#818CF8", tints=_TINTS_DARK, solid_green_text="#06210F"),
}
T = dict(THEMES["light"])          # the active theme; mutated in place on switch


def use_theme(name):
    T.clear()
    T.update(THEMES.get(name, THEMES["light"]))


def rgba(hex_color, alpha):
    c = QColor(hex_color)
    return f"rgba({c.red()},{c.green()},{c.blue()},{alpha})"


FAMILIES = ["Segoe UI", "SF Pro Display", "Inter", "Helvetica Neue", "Roboto",
            "Noto Sans", "Arial", "DejaVu Sans"]
W_LIGHT, W_NORMAL, W_MED, W_SEMI, W_BOLD = (QFont.Weight.Light, QFont.Weight.Normal, QFont.Weight.Medium,
                                            QFont.Weight.DemiBold, QFont.Weight.Bold)
AL_C = Qt.AlignmentFlag.AlignCenter
AL_L = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
AL_R = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter


def make_font(px, weight=W_NORMAL):
    f = QFont()
    f.setFamilies(FAMILIES)
    f.setPixelSize(int(px))            # pixel sizes => identical layout at any DPI
    f.setWeight(weight)
    f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    return f


def set_color(lb, color):
    lb.setStyleSheet(f"color:{color}; background:transparent;")


class WrapLabel(QLabel):
    """QLabel that never demands a wide minimum width when word-wrapping."""

    def minimumSizeHint(self):
        s = super().minimumSizeHint()
        return QSize(min(s.width(), 40), s.height()) if self.wordWrap() else s


def label(text="", px=24, weight=W_NORMAL, color=None, wrap=False, align=None, rich=False):
    lb = WrapLabel(text)
    lb.setFont(make_font(px, weight))
    set_color(lb, color or T["text"])
    lb.setWordWrap(wrap)
    lb.setTextFormat(Qt.TextFormat.RichText if rich else Qt.TextFormat.PlainText)
    if align is not None:
        lb.setAlignment(align)
    if wrap:
        lb.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
    return lb


def tone_color(tone):
    return {"info": T["text2"], "good": T["green"], "bad": T["red"], "warn": T["amber"],
            "card": T["purple"], "invest": T["blue"], "gold": T["gold"]}.get(tone, T["text"])


def score_color(score):
    if score >= 800:
        return T["green"]
    if score >= 700:
        return T["lime"]
    if score >= 600:
        return T["gold"]
    if score >= 450:
        return T["amber"]
    return T["red"]


def variant_fg(v):
    if v in T["tints"]:
        return T["tints"][v][2]
    return {"primary": T["primary_text"], "accent": T["accent_text"], "danger": T["danger_text"],
            "solid_green": T["solid_green_text"], "seg": T["muted"], "segon": T["primary_text"]}.get(v, T["text"])


def restyle(w):
    w.style().unpolish(w)
    w.style().polish(w)
    w.update()


# ------------------------------------------------------------------- icons --
def draw_icon(p, kind, rect, color):
    s = min(rect.width(), rect.height())
    c = rect.center()
    cx, cy = c.x(), c.y()
    pen = QPen(QColor(color), max(2.0, s * 0.09), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
               Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    if kind == "menu":
        for dy in (-0.18, 0.18):
            p.drawLine(QPointF(cx - s * 0.4, cy + s * dy), QPointF(cx + s * 0.4, cy + s * dy))
    elif kind == "close":
        d = s * 0.32
        p.drawLine(QPointF(cx - d, cy - d), QPointF(cx + d, cy + d))
        p.drawLine(QPointF(cx - d, cy + d), QPointF(cx + d, cy - d))
    elif kind == "gear":
        p.drawEllipse(QPointF(cx, cy), s * 0.15, s * 0.15)
        p.drawEllipse(QPointF(cx, cy), s * 0.32, s * 0.32)
        for i in range(8):
            a = math.radians(i * 45)
            p.drawLine(QPointF(cx + math.cos(a) * s * 0.36, cy + math.sin(a) * s * 0.36),
                       QPointF(cx + math.cos(a) * s * 0.48, cy + math.sin(a) * s * 0.48))
    elif kind == "book":
        w, h = s * 0.42, s * 0.40
        p.drawRoundedRect(QRectF(cx - w, cy - h, w * 2, h * 2), s * 0.06, s * 0.06)
        p.drawLine(QPointF(cx, cy - h), QPointF(cx, cy + h))
    elif kind == "power":
        r = s * 0.36
        p.drawArc(QRectF(cx - r, cy - r + s * 0.05, 2 * r, 2 * r), 125 * 16, 290 * 16)
        p.drawLine(QPointF(cx, cy - s * 0.42), QPointF(cx, cy - s * 0.02))
    elif kind == "sun":
        p.drawEllipse(QPointF(cx, cy), s * 0.18, s * 0.18)
        for i in range(8):
            a = math.radians(i * 45)
            p.drawLine(QPointF(cx + math.cos(a) * s * 0.30, cy + math.sin(a) * s * 0.30),
                       QPointF(cx + math.cos(a) * s * 0.44, cy + math.sin(a) * s * 0.44))
    elif kind == "moon":
        path = QPainterPath()
        path.addEllipse(QPointF(cx, cy), s * 0.38, s * 0.38)
        cut = QPainterPath()
        cut.addEllipse(QPointF(cx + s * 0.2, cy - s * 0.16), s * 0.32, s * 0.32)
        p.drawPath(path.subtracted(cut))
    elif kind == "home":
        p.drawPolyline([QPointF(cx - s * 0.4, cy - s * 0.02), QPointF(cx, cy - s * 0.4), QPointF(cx + s * 0.4, cy - s * 0.02)])
        p.drawPolyline([QPointF(cx - s * 0.28, cy - s * 0.12), QPointF(cx - s * 0.28, cy + s * 0.38),
                        QPointF(cx + s * 0.28, cy + s * 0.38), QPointF(cx + s * 0.28, cy - s * 0.12)])
    elif kind == "play":
        p.drawPolygon([QPointF(cx - s * 0.22, cy - s * 0.34), QPointF(cx + s * 0.34, cy), QPointF(cx - s * 0.22, cy + s * 0.34)])
    elif kind == "replay":
        r = s * 0.34
        p.drawArc(QRectF(cx - r, cy - r, 2 * r, 2 * r), 60 * 16, 290 * 16)
        p.drawPolyline([QPointF(cx + s * 0.06, cy - s * 0.46), QPointF(cx + s * 0.2, cy - s * 0.3), QPointF(cx + s * 0.02, cy - s * 0.2)])


class IconWidget(QWidget):
    def __init__(self, kind, size, color_fn):
        super().__init__()
        self.kind, self.color_fn = kind, color_fn
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        draw_icon(p, self.kind, QRectF(2, 2, self.width() - 4, self.height() - 4), self.color_fn())
        p.end()


class FitLabel(QLabel):
    """Single-line label that shrinks its font until the text fits its width."""

    def __init__(self, text="", px=32, weight=W_BOLD, color=None, min_px=12, align=AL_L):
        super().__init__()
        self._px, self._min, self._weight = px, min_px, weight
        self.setFont(make_font(px, weight))
        self.setAlignment(align)
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(int(px * 1.32))
        set_color(self, color or T["text"])
        self.setText(text)

    def setFixedWidth(self, w):
        # an 'Ignored' policy breaks box layouts when combined with a fixed width
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        super().setFixedWidth(w)

    def setText(self, text):
        super().setText(text)
        self._fit()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._fit()

    def _fit(self):
        avail = self.width() - 4 - self.contentsMargins().left() - self.contentsMargins().right()
        if avail <= 0:
            return
        px = self._px
        f = make_font(px, self._weight)
        while px > self._min and QFontMetrics(f).horizontalAdvance(self.text()) > avail:
            px -= 1
            f.setPixelSize(px)
        if self.font().pixelSize() != px:
            self.setFont(f)


class Badge(FitLabel):
    """Flat, square-ish status tag. Deliberately NOT button-shaped (no pill, no edge)."""

    def __init__(self, text="", px=19, height=40):
        super().__init__(text, px, W_BOLD, align=AL_C)
        self.setFixedHeight(height)
        self._h = height
        self.setContentsMargins(14, 0, 14, 0)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        bg, _, fg = T["tints"]["slate"]
        self.set_style(bg, fg)

    def set_style(self, bg, fg):
        self.setStyleSheet(f"color:{fg}; background:{bg}; border-radius:10px;")

    def set_tint(self, tint):
        bg, _, fg = T["tints"][tint]
        self.set_style(bg, fg)

    def sizeHint(self):
        fm = QFontMetrics(make_font(self._px, self._weight))
        return QSize(fm.horizontalAdvance(self.text()) + 40, self._h)

    def minimumSizeHint(self):
        return QSize(min(self.sizeHint().width(), 80), self._h)


class WrapButton(QPushButton):
    """Clearly clickable button: raised edge, hover state, hand cursor. Text wraps/shrinks
    to always fit; optional painted icon."""

    def __init__(self, text="", variant="soft", px=24, weight=W_SEMI, height=None, pad=20, icon=None):
        super().__init__()
        self.setProperty("variant", variant)
        self._px, self._weight, self._pad = px, weight, pad
        self.icon_w = None
        if icon:
            lay = QHBoxLayout(self)
            lay.setContentsMargins(pad, 6, pad, 10)
            lay.setSpacing(int(px * 0.55))
            lay.addStretch(1)
            self.icon_w = IconWidget(icon, int(px * 1.15), self._icon_color)
            lay.addWidget(self.icon_w)
        else:
            lay = QVBoxLayout(self)
            lay.setContentsMargins(pad, 6, pad, 10)
        self.lbl = WrapLabel()
        self.lbl.setWordWrap(icon is None)
        self.lbl.setAlignment(AL_C)
        self.lbl.setTextFormat(Qt.TextFormat.PlainText)
        self.lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.lbl.setFont(make_font(px, weight))
        lay.addWidget(self.lbl)
        if icon:
            lay.addStretch(1)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if height:
            self.setFixedHeight(height)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._text = ""
        self.setText(text)

    def _icon_color(self):
        return variant_fg(self.property("variant")) if self.isEnabled() else T["disabled_text"]

    def setText(self, text):
        self._text = text
        self.lbl.setText(text)
        self._fit()

    def text(self):
        return self._text

    def set_variant(self, v):
        if self.property("variant") != v:
            self.setProperty("variant", v)
            restyle(self)
            restyle(self.lbl)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._fit()

    def _fit(self):
        icon_space = (self.icon_w.width() + int(self._px * 0.55)) if self.icon_w else 0
        w, h = self.width() - 2 * self._pad - icon_space - 4, self.height() - 18
        if w <= 0 or h <= 0:
            return
        px = self._px
        f = make_font(px, self._weight)
        flags = (int(Qt.TextFlag.TextWordWrap) if not self.icon_w else 0) | int(AL_C)
        while px > 12:
            fm = QFontMetrics(f)
            r = fm.boundingRect(QRect(0, 0, w, 10000), flags, self._text)
            longest = max((fm.horizontalAdvance(word) for word in self._text.split()), default=0)
            if r.height() <= h and longest <= w and r.width() <= w:
                break
            px -= 1
            f.setPixelSize(px)
        if self.lbl.font().pixelSize() != px:
            self.lbl.setFont(f)


class Card(QFrame):
    def __init__(self, name="card"):
        super().__init__()
        self.setObjectName(name)

    def set_kind(self, name):
        if self.objectName() != name:
            self.setObjectName(name)
            restyle(self)


class IconButton(QPushButton):
    """Round icon-only button (used for 'close')."""

    def __init__(self, kind, size=76):
        super().__init__()
        self.kind = kind
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("background:transparent; border:none;")

    def enterEvent(self, e):
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.update()
        super().leaveEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        s = self.width()
        hover = self.underMouse()
        p.setPen(QPen(QColor(T["text"] if hover else T["border_strong"]), 2.5))
        p.setBrush(QColor(T["surface"] if hover else T["card"]))
        p.drawEllipse(QRectF(2, 2, s - 4, s - 4))
        draw_icon(p, self.kind, QRectF(s * 0.32, s * 0.32, s * 0.36, s * 0.36), T["text"])
        p.end()


class SegmentBar(QWidget):
    """Row of rounded segments, filled / dashed-empty (like the usage meters in the examples)."""

    def __init__(self, segments=10, height=58):
        super().__init__()
        self.n, self.frac, self.color = segments, 0.0, T["seg_fill"]
        self.setFixedHeight(height)

    def set_value(self, frac, color):
        self.frac, self.color = max(0.0, min(1.0, frac)), color
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        gap = 8
        w = (self.width() - gap * (self.n - 1)) / self.n
        h = self.height()
        filled = math.ceil(self.frac * self.n - 1e-9) if self.frac > 0 else 0
        for i in range(self.n):
            r = QRectF(i * (w + gap) + 1, 1, w - 2, h - 2)
            rad = min(w, h) * 0.42
            if i < filled:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(self.color))
            else:
                p.setPen(QPen(QColor(T["border_strong"]), 2, Qt.PenStyle.DashLine))
                p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(r, rad, rad)
        p.end()


class CreditGauge(QWidget):
    def __init__(self):
        super().__init__()
        self.score, self.tier, self.color = 550, "Poor", T["amber"]
        self.setMinimumHeight(180)

    def set_score(self, score, tier, color):
        self.score, self.tier, self.color = score, tier, color
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        pen_w = max(18, int(min(w, h) * 0.10))
        r = min((w - pen_w * 2) / 2, (h - pen_w) / 1.52)
        cx = w / 2
        cy = (h - (1.5 * r + pen_w)) / 2 + pen_w / 2 + r
        rect = QRectF(cx - r, cy - r, 2 * r, 2 * r)
        p.setPen(QPen(QColor(T["track"]), pen_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(rect, 210 * 16, -240 * 16)
        p.setPen(QPen(QColor(T["border_strong"]), 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        for s in (300, 450, 600, 700, 800):
            ang = math.radians(210 - 240 * s / 1000)
            r1, r2 = r - pen_w / 2 - 8, r - pen_w / 2 - 18
            p.drawLine(QPointF(cx + r1 * math.cos(ang), cy - r1 * math.sin(ang)),
                       QPointF(cx + r2 * math.cos(ang), cy - r2 * math.sin(ang)))
        span = -240 * max(0.0, min(1.0, self.score / 1000))
        if span < 0:
            p.setPen(QPen(QColor(self.color), pen_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(rect, 210 * 16, int(span * 16))
        p.setPen(QColor(T["text"]))
        p.setFont(make_font(int(r * 0.56), W_BOLD))
        p.drawText(QRectF(cx - r, cy - r * 0.58, 2 * r, r * 0.66), AL_C, str(self.score))
        p.setPen(QColor(self.color))
        p.setFont(make_font(int(r * 0.19), W_BOLD))
        p.drawText(QRectF(cx - r, cy + r * 0.10, 2 * r, r * 0.30), AL_C, self.tier.upper())
        p.end()


def build_stylesheet():
    t = T
    qss = [f"""
    QWidget#root {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {t['bg_top']}, stop:1 {t['bg_bot']}); }}
    QFrame#card {{ background-color:{t['card']}; border:1px solid {t['border']}; border-radius:32px; }}
    QFrame#tile, QFrame#soft, QFrame#infobox {{ background-color:{t['surface']}; border:none; border-radius:24px; }}
    QFrame#modal {{ background-color:{t['modal']}; border:1px solid {t['modal_border']}; border-radius:40px; }}
    QFrame#bubble {{ background-color:{t['modal']}; border:3px solid {t['accent']}; border-radius:32px; }}
    QFrame#segwrap {{ background-color:{t['surface']}; border:none; border-radius:30px; }}
    QFrame#toast {{ background-color:{t['primary']}; border:none; border-radius:28px; }}
    QFrame#divider {{ background-color:{t['border']}; border:none; }}

    /* clickable buttons: solid fill or even outline, a hover state and a hand cursor */
    QPushButton {{ border-radius:22px; border:none; }}
    QPushButton QLabel {{ background:transparent; }}

    QPushButton[variant="primary"] {{ background:{t['primary']}; }}
    QPushButton[variant="primary"]:hover {{ background:{t['primary_hover']}; }}
    QPushButton[variant="primary"] QLabel {{ color:{t['primary_text']}; }}
    QPushButton[variant="accent"] {{ background:{t['accent']}; }}
    QPushButton[variant="accent"]:hover {{ background:{t['accent_hover']}; }}
    QPushButton[variant="accent"] QLabel {{ color:{t['accent_text']}; }}
    QPushButton[variant="danger"] {{ background:{t['danger']}; }}
    QPushButton[variant="danger"]:hover {{ background:{t['danger_hover']}; }}
    QPushButton[variant="danger"] QLabel {{ color:{t['danger_text']}; }}
    QPushButton[variant="solid_green"] {{ background:{t['green']}; }}
    QPushButton[variant="solid_green"]:hover {{ border:3px solid {t['text']}; }}
    QPushButton[variant="solid_green"] QLabel {{ color:{t['solid_green_text']}; }}

    QPushButton[variant="outline"], QPushButton[variant="soft"], QPushButton[variant="chip"] {{
        border:2px solid {t['border_strong']}; }}
    QPushButton[variant="outline"] {{ background:{t['card']}; }}
    QPushButton[variant="soft"], QPushButton[variant="chip"] {{ background:{t['surface']}; }}
    QPushButton[variant="outline"]:hover, QPushButton[variant="soft"]:hover, QPushButton[variant="chip"]:hover {{
        border-color:{t['text']}; }}
    QPushButton[variant="outline"] QLabel, QPushButton[variant="soft"] QLabel, QPushButton[variant="chip"] QLabel {{
        color:{t['text']}; }}

    QPushButton[variant="seg"] {{ background:transparent; border-radius:24px; }}
    QPushButton[variant="seg"]:hover {{ background:{t['card']}; }}
    QPushButton[variant="seg"] QLabel {{ color:{t['muted']}; }}
    QPushButton[variant="segon"] {{ background:{t['primary']}; border-radius:24px; }}
    QPushButton[variant="segon"] QLabel {{ color:{t['primary_text']}; }}

    QSpinBox {{ background-color:{t['card']}; color:{t['text']}; border:2px solid {t['border_strong']};
               border-radius:22px; padding:0px 6px; selection-background-color:{t['accent']}; }}
    QSpinBox:focus {{ border-color:{t['accent']}; }}
    QSpinBox::up-button, QSpinBox::down-button {{ width:0px; border:none; }}
    QSpinBox::up-arrow, QSpinBox::down-arrow {{ width:0px; height:0px; }}
    QCheckBox {{ color:{t['text2']}; spacing:14px; background:transparent; }}
    QCheckBox::indicator {{ width:32px; height:32px; border-radius:10px; border:3px solid {t['border_strong']};
                            background:{t['card']}; }}
    QCheckBox::indicator:hover {{ border-color:{t['accent']}; }}
    QCheckBox::indicator:checked {{ background:{t['accent']}; border-color:{t['accent']}; }}
    QScrollArea {{ background:transparent; border:none; }}
    QScrollArea > QWidget > QWidget {{ background:transparent; }}
    QScrollBar:vertical {{ width:12px; background:transparent; margin:4px; }}
    QScrollBar::handle:vertical {{ background:{t['border_strong']}; border-radius:4px; min-height:50px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background:transparent; }}
    QToolTip {{ background:{t['card']}; color:{t['text']}; border:1px solid {t['border']}; padding:6px; }}
    """]
    for name, (bg, hov, fg) in t["tints"].items():
        qss.append(f"""
        QFrame#tint_{name} {{ background-color:{bg}; border:none; border-radius:28px; }}
        QPushButton[variant="{name}"] {{ background:{bg}; border:2px solid {rgba(fg, 0.30)};
                                          }}
        QPushButton[variant="{name}"]:hover {{ background:{hov}; border-color:{rgba(fg, 0.6)}; }}
        QPushButton[variant="{name}"] QLabel {{ color:{fg}; }}
        """)
    # disabled = flat + dashed outline, so it reads as "not clickable right now"
    for name in list(t["tints"]) + ["primary", "accent", "danger", "outline", "soft", "chip", "solid_green"]:
        qss.append(f'QPushButton[variant="{name}"]:disabled {{ background:{t["disabled_bg"]}; '
                   f'border:2px dashed {t["border_strong"]}; }}'
                   f'QPushButton[variant="{name}"] QLabel:disabled {{ color:{t["disabled_text"]}; }}')
    return "\n".join(qss)


# ------------------------------------------------------------------ overlays --
class Overlay(QWidget):
    """Full-canvas dimmed layer with a centred modal card."""

    def __init__(self, parent, width):
        super().__init__(parent)
        self.setGeometry(0, 0, parent.width(), parent.height())
        outer = QVBoxLayout(self)
        outer.setContentsMargins(40, 40, 40, 40)
        outer.addStretch(1)
        row = QHBoxLayout()
        row.addStretch(1)
        self.modal = Card("modal")
        self.modal.setFixedWidth(width)
        row.addWidget(self.modal)
        row.addStretch(1)
        outer.addLayout(row)
        outer.addStretch(1)
        self.body = QVBoxLayout(self.modal)
        self.body.setContentsMargins(48, 42, 48, 42)
        self.body.setSpacing(20)
        self.hide()

    def paintEvent(self, e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(*T["overlay"]))
        p.end()

    def mousePressEvent(self, e):
        e.accept()                                  # block clicks to the page below

    def clear(self):
        self.hide()            # new children of a visible widget would otherwise stay hidden
        clear_layout(self.body)


def clear_layout(layout):
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w is not None:
            w.hide()
            w.setParent(None)               # detach now so nothing old is painted
            w.deleteLater()
        elif item.layout():
            clear_layout(item.layout())


TONE_VARIANT = {"cash": "green", "card": "purple", "loan": "amber", "bad": "red",
                "good": "teal", "info": "blue", "skip": "slate"}


class EventOverlay(Overlay):
    def __init__(self, parent, on_choose, desktop):
        super().__init__(parent, 1300 if desktop else 970)
        self.desktop = desktop
        self.on_choose = on_choose
        self.key = None

    def show_event(self, g):
        ev = g.current_event
        if self.isVisible() and self.key is ev:
            return
        self.key = ev
        self.clear()
        b = self.body
        top = QHBoxLayout()
        tag = Badge(f"QUARTERLY EVENT  ·  AGE {g.age_years}  ·  Q{g.quarter()}", 19, 40)
        tag.set_tint("blue")
        top.addWidget(tag, 0)
        top.addStretch(1)
        b.addLayout(top)
        b.addWidget(label(ev["title"], 54, W_BOLD, wrap=True))
        b.addWidget(label(ev["desc"], 28, W_NORMAL, T["text2"], wrap=True))
        if ev.get("info"):
            box = Card("infobox")
            bl = QVBoxLayout(box)
            bl.setContentsMargins(28, 20, 28, 22)
            bl.setSpacing(6)
            bl.addWidget(label("Why it matters", 22, W_BOLD))
            bl.addWidget(label(ev["info"], 23, W_NORMAL, T["text2"], wrap=True))
            b.addWidget(box)
        # plain text status line (information, not buttons)
        b.addWidget(label(f"Cash {money(g.cash)}     Card credit left {money(g.card_available())}     "
                          f"Happiness {g.happiness}     Credit {g.credit_score}", 21, W_SEMI, T["muted"], wrap=True))
        b.addWidget(label("Choose one:", 22, W_BOLD, T["text"]))

        grid = QGridLayout()
        grid.setSpacing(16)
        opts = ev["options"]
        cols = 2 if self.desktop and len(opts) >= 3 else 1
        for i, o in enumerate(opts):
            reason = g.option_block_reason(o)
            text = o["label"] + (f"\n(unavailable: {reason})" if reason else "")
            btn = WrapButton(text, TONE_VARIANT.get(o["tone"], "slate"), 26, W_SEMI, height=110)
            btn.setEnabled(reason is None)
            btn.clicked.connect(lambda _=False, idx=i: self.on_choose(idx))
            span = 2 if cols == 2 and i == len(opts) - 1 and len(opts) % 2 else 1
            grid.addWidget(btn, i // cols, i % cols, 1, span)
        b.addLayout(grid)
        self.show()
        self.raise_()


class PopupOverlay(Overlay):
    KIND_TINT = {"warning": "red", "success": "green", "info": "blue", "gold": "amber"}

    def __init__(self, parent, on_close, desktop):
        super().__init__(parent, 1300 if desktop else 980)
        self.width_ = 1300 if desktop else 980
        self.max_h = 1000 if desktop else 1160
        self.on_close = on_close

    def show_popup(self, title, body_html, kind="info", buttons=None):
        self.clear()
        b = self.body
        top = QHBoxLayout()
        badge = Badge({"warning": "HEADS UP", "success": "NICE WORK", "gold": "GUIDE"}.get(kind, "INFO"), 19, 40)
        badge.set_tint(self.KIND_TINT.get(kind, "blue"))
        top.addWidget(badge)
        top.addStretch(1)
        b.addLayout(top)
        b.addWidget(label(title, 50, W_BOLD, wrap=True))

        body = label(body_html, 25, W_NORMAL, T["text2"], wrap=True, rich=True)
        body.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        holder = QWidget()
        hl = QVBoxLayout(holder)
        hl.setContentsMargins(0, 0, 18, 0)
        hl.addWidget(body)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(holder)
        need = body.heightForWidth(self.width_ - 96 - 30) + 64
        scroll.setFixedHeight(max(110, min(self.max_h, need)))
        b.addWidget(scroll)

        row = QHBoxLayout()
        row.setSpacing(14)
        for text, variant, cb in (buttons or [("Got it", "primary", None)]):
            btn = WrapButton(text, variant, 27, W_SEMI, height=92)
            btn.setEnabled(cb is not False)
            btn.clicked.connect(lambda _=False, c=cb: self._clicked(c))
            row.addWidget(btn)
        b.addLayout(row)
        self.show()
        self.raise_()

    def _clicked(self, cb):
        self.hide()
        if callable(cb):
            cb()
        self.on_close()


class SettingsOverlay(Overlay):
    def __init__(self, parent, ui, desktop):
        super().__init__(parent, 1100 if desktop else 960)
        self.ui = ui

    def _segmented(self, options, current, on_pick):
        wrap = Card("segwrap")
        wrap.setFixedHeight(84)
        lay = QHBoxLayout(wrap)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(8)
        for text, value, icon in options:
            btn = WrapButton(text, "segon" if value == current else "seg", 25, W_SEMI, height=68, icon=icon)
            btn.clicked.connect(lambda _=False, v=value: on_pick(v))
            lay.addWidget(btn)
        return wrap

    def open(self):
        self.clear()
        ui, win = self.ui, self.ui.win
        b = self.body
        b.setSpacing(16)
        top = QHBoxLayout()
        top.addWidget(label("Settings", 58, W_BOLD))
        top.addStretch(1)
        close = IconButton("close", 76)
        close.clicked.connect(self.close_)
        top.addWidget(close)
        b.addLayout(top)

        def section(title, hint=None):
            b.addSpacing(8)
            b.addWidget(label(title, 26, W_BOLD))
            if hint:
                b.addWidget(label(hint, 21, W_NORMAL, T["muted"], wrap=True))

        section("Appearance")
        b.addWidget(self._segmented([("Light", "light", "sun"), ("Dark", "dark", "moon")],
                                    win.settings["theme"], win.set_theme))
        section("Layout", "Mobile is a vertical 9:16 screen, desktop a horizontal 16:9 screen. Either one scales "
                          "to fit any window or monitor, with bars filling any leftover space.")
        b.addWidget(self._segmented([("Mobile  ·  vertical", "mobile", None), ("Desktop  ·  horizontal", "desktop", None)],
                                    win.settings["layout"], win.set_layout))
        section("Display")
        fs = WrapButton("Exit fullscreen  (F11)" if win.isFullScreen() else "Enter fullscreen  (F11)",
                        "soft", 25, W_SEMI, height=80)
        fs.clicked.connect(lambda: (win.toggle_fullscreen(), self.open()))
        b.addWidget(fs)

        section("Help")
        row = QHBoxLayout()
        row.setSpacing(14)
        guide = WrapButton("Credit 101 guide", "blue", 25, W_SEMI, height=80, icon="book")
        guide.clicked.connect(lambda: (self.hide(), ui.show_guide()))
        row.addWidget(guide)
        tut = WrapButton("Replay tutorial", "soft", 25, W_SEMI, height=80, icon="replay")
        tut.clicked.connect(lambda: (self.hide(), ui.replay_tutorial()))
        row.addWidget(tut)
        b.addLayout(row)

        section("Game", "Progress saves automatically after every move, and when you close the window.")
        row = QHBoxLayout()
        row.setSpacing(14)
        if win.page == "game" and ui.game.state in ("main", "event"):
            menu = WrapButton("Save & main menu", "outline", 25, W_SEMI, height=88, icon="home")
            menu.clicked.connect(lambda: (self.hide(), ui.to_menu()))
            row.addWidget(menu)
            quit_ = WrapButton("Save & quit", "danger", 27, W_BOLD, height=88, icon="power")
        else:
            quit_ = WrapButton("Quit game", "danger", 27, W_BOLD, height=88, icon="power")
        quit_.clicked.connect(win.close)
        row.addWidget(quit_)
        b.addLayout(row)
        self.show()
        self.raise_()

    def close_(self):
        self.hide()
        self.ui.after_overlay()


class Toast(QFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("toast")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(30, 18, 30, 18)
        lay.setSpacing(16)
        self.dot = QLabel()
        self.dot.setFixedSize(16, 16)
        lay.addWidget(self.dot)
        self.lbl = label("", 24, W_SEMI, T["primary_text"], wrap=True)
        lay.addWidget(self.lbl, 1)
        self.queue = []
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._next)
        self.hide()

    def push(self, text, tone="gold"):
        self.queue.append((text, tone))
        if not self.isVisible():
            self._next()

    def _next(self):
        if not self.queue:
            self.hide()
            return
        text, tone = self.queue.pop(0)
        dot = {"bad": "#F87171", "good": "#4ADE80", "gold": "#FACC15"}.get(tone, "#818CF8")
        self.dot.setStyleSheet(f"background:{dot}; border-radius:8px;")
        self.lbl.setText(text)
        pw = self.parentWidget().width()
        w = min(900, pw - 80)
        h = self.lbl.heightForWidth(w - 92) + 40
        self.setGeometry((pw - w) // 2, 28, w, max(80, h))
        self.show()
        self.raise_()
        self.timer.start(2800)

    def mousePressEvent(self, e):
        self.timer.stop()
        self._next()


# --------------------------------------------------------------- tutorial ---
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
    "pay_min": ("Minimum covered", "This quarter will count as an ON-TIME payment when you advance (+credit). Paying the "
                "full statement also avoids card interest."),
    "pay_all": ("Debt cleared", "Paying the whole statement means no card interest this quarter (grace period) — the "
                "smartest way to use a credit card."),
    "buy": ("Happiness refilled", "Leisure costs real money, so budget for it every quarter. Remember: 0 happiness for "
            "a full year is game over."),
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
                 body="Work and life stress drain happiness every quarter. If it sits at <b>0 for a full year</b>, "
                      "you die of depression. The pink button refills it."),
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
            dict(title="Pay your bill", target=lambda: d().b_min, wait=("pay_min", "pay_all", "pay"),
                 skip=lambda: g().remaining_due() <= 0 or g().cash <= 0,
                 body="<b>Pay minimum</b> protects your score. <b>Pay off all</b> clears the card and avoids "
                      "interest entirely.", hint="Try it: press Pay minimum (or Pay off all)."),
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
                      "tutorial. <b>Credit 101</b> opens the full guide. <b>Save & quit</b> any time — your "
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
                  "pay_min": d.b_min, "pay_all": d.b_all, "buy": d.buy_btn, "autopay": d.bills,
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


# --------------------------------------------------------------------- pages --
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

        hero = label("<span style='font-weight:300'>Earn, spend and </span><b>borrow</b>"
                     "<span style='font-weight:300'> your way from </span><b>18 to 65</b>",
                     104 if desktop else 84, W_NORMAL, wrap=True, rich=True)
        sub = label("Your first credit card was just approved. Build your credit, keep your happiness up "
                    "and retire without going broke.", 30, W_NORMAL, T["muted"], wrap=True)
        facts = label("47 years   ·   188 quarters   ·   25 kinds of life events   ·   13 achievements",
                      23, W_SEMI, T["dim"], wrap=True)

        rules = Card("card")
        rl = QVBoxLayout(rules)
        rl.setContentsMargins(40, 34, 40, 36)
        rl.setSpacing(18)
        rl.addWidget(label("How it works", 34, W_BOLD))
        for head, text in [
            ("Bills come due.", "Card and loan balances post a minimum payment. Pay it before advancing to grow your credit."),
            ("Happiness drains.", "Buy leisure to refill it. At 0 for a full year you die of depression."),
            ("Credit = cheaper money.", "Higher scores unlock lower interest, bigger limits and loans (capped at 700 for 5 years)."),
            ("Costs rise faster than pay.", "Rent, groceries and bills are compulsory, so certifications and investing matter."),
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


class Tile(Card):
    def __init__(self, caption, height=118, value_px=40):
        super().__init__("tile")
        self.setFixedHeight(height)
        lay = QVBoxLayout(self)
        pad = 24 if height < 140 else 32
        lay.setContentsMargins(pad, 10 if height < 140 else 22, pad, 10 if height < 140 else 22)
        lay.setSpacing(2)
        self.cap = FitLabel(caption, 20, W_MED, T["muted"])
        self.val = FitLabel("", value_px, W_BOLD)
        self.sub = FitLabel("", 18, W_MED, T["muted"])
        lay.addWidget(self.cap)
        lay.addWidget(self.val)
        lay.addWidget(self.sub)

    def set(self, value, color, sub, sub_color=None):
        self.val.setText(value)
        set_color(self.val, color)
        self.sub.setText(sub)
        set_color(self.sub, sub_color or T["muted"])


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
        s.setFixedWidth(220)
        gd.setFixedWidth(230)
        q.setFixedWidth(240)
        tl.addWidget(s)
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
        self.b_all.clicked.connect(lambda: ui.act("pay_all", ui.game.pay_all))
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
            notes.append(f"IRS SEIZURE RISK {g.low_credit_turns}/{g.IRS_TURNS}")
        self.credit_note.setText("  ·  ".join(notes) if notes else "Pay your minimum each quarter to climb")
        set_color(self.credit_note, T["red"] if danger else T["muted"])

        hcol = T["seg_fill"] if g.happiness > 50 else (T["amber"] if g.happiness > 25 else T["red"])
        self.happy_val.setText(f"<span style='color:{T['text'] if g.happiness > 25 else T['red']}'>{g.happiness}</span>"
                               f"<span style='font-size:26px; font-weight:500; color:{T['muted']}'>  / 100</span>")
        self.happy_bar.set_value(g.happiness / 100, hcol)
        self.decay_badge.setText(f"−{g.happiness_decay()} / QTR")
        if g.zero_happiness_turns:
            self.happy_note.setText(f"DEPRESSION WARNING {g.zero_happiness_turns}/{g.DEPRESSION_TURNS} — "
                                    "buy leisure now or you won't survive the year!")
            set_color(self.happy_note, T["red"])
        else:
            self.happy_note.setText("Work & life stress drain it every quarter. Zero for a full year is fatal.")
            set_color(self.happy_note, T["muted"])
        cost = g.happiness_cost()
        self.buy_btn.setText(f"Buy leisure & hobbies\n−{money(cost)}  ·  +{g.HAPPY_PTS} happiness")
        self.buy_btn.setEnabled(g.cash >= cost and g.happiness < 100)

        od = g.overdraft_used()
        self.t_cash.set(money(g.cash), T["red"] if g.cash < 0 else T["green"],
                        f"Overdraft {money(od)} / {money(g.OVERDRAFT_LIMIT)}" if od else
                        f"Overdraft limit {money(g.OVERDRAFT_LIMIT)}", T["red"] if od else None)
        self.t_inv.set(money(g.investments), T["blue"],
                       "No withdrawal fee (60+)" if g.withdraw_fee_rate() == 0 else "5% fee to withdraw before 60")
        util = g.card / max(1, g.card_limit())
        self.t_card.set(money(g.card), T["purple"] if g.card <= g.card_limit() else T["red"],
                        f"{money(g.card_available())} free of {money(g.card_limit())}",
                        T["red"] if util > 0.9 else None)
        cap = g.loan_capacity()
        self.t_loan.set(money(g.loans), T["amber"] if g.loans else T["dim"],
                        f"Can borrow {money(g.loan_room())}" if cap else "Loans need a 450+ score",
                        None if cap else T["red"])
        inc_sub = f"Certifications {g.courses_taken}/{g.MAX_COURSES}"
        if g.layoff_turns:
            inc_sub = f"{int(g.layoff_mult * 100)}% pay for {g.layoff_turns} more qtr"
        elif not g.has_car:
            inc_sub += "  ·  no car −10%"
        self.t_inc.set(money(g.quarterly_income()), T["gold"], inc_sub, T["amber"] if g.layoff_turns else None)
        items = g.essentials_breakdown()
        self.t_ess.set(money(g.essentials_total()), T["pink"], "Rent, food & bills — compulsory")
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
            extra = ("Statement fully paid — no card interest." if g.paid_card_this_qtr >= g.stmt_card
                     else f"Pay the full {money(g.stmt_card)} statement to skip card interest.")
            self.due_note.setText(f"Paid {money(g.paid_this_qtr)} this quarter. {extra}")
            self.due_chip.setText("ON TIME")
            self.due_chip.set_style(T["green"], T["solid_green_text"])
        else:
            self.bills.set_kind("tint_red")
            fg = muted = T["tints"]["red"][2]
            self.due_val.setText(f"{money(rem)} still due")
            self.due_note.setText(f"Minimum {money(g.min_due)}, paid {money(g.paid_this_qtr)}. Advancing now = "
                                  f"{'LATE (−20)' if g.paid_this_qtr else 'MISSED (−50)'}.")
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
        self.b_all.setText(f"Pay off all\n{money(owed)}")
        self.b_all.setEnabled(owed > 0 and g.cash > 0)

        lines = []
        for when, text, tone in reversed(g.log[-60:]):
            lines.append(f"<span style='color:{T['dim']}'>{esc(when)}</span>&nbsp;&nbsp;"
                         f"<span style='color:{tone_color(tone)}'>{esc(text)}</span>")
        self.log_lbl.setText("<br>".join(lines))

        self.retire_btn.setVisible(g.get_net_worth() >= g.MILLION)
        self.next_btn.setEnabled(g.state == "main")


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
        for _ in range(9):
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

        again = WrapButton("Play again — new credit card", "primary", 36, W_BOLD, height=116, icon="play")
        again.clicked.connect(ui.new_game)
        row = QHBoxLayout()
        row.setSpacing(16)
        menu = WrapButton("Main menu", "outline", 26, W_SEMI, height=88, icon="home")
        menu.clicked.connect(ui.to_menu)
        quit_ = WrapButton("Quit", "red", 26, W_BOLD, height=88, icon="power")
        quit_.clicked.connect(ui.win.close)
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
            self.sub.setText("Your credit score stayed under 300 for two years and the IRS took everything.")
        else:
            self.title.setText("<span style='font-weight:300'>Lost to </span><b>depression.</b>")
            self.badge.setText("GAME OVER")
            self.badge.set_tint("red")
            self.sub.setText("Your happiness stayed at 0 for a full year. Money matters — but so does living.")
        nw = g.get_net_worth()
        mult = f"×{0.5 + g.credit_score / 2000:.2f} credit multiplier" if good else f"−{money(g.DEATH_PENALTY)} penalty"
        data = [
            ("Age reached", str(g.age_years), T["text"]),
            ("Net worth", money(nw), T["green"] if nw >= 0 else T["red"]),
            ("Credit score", f"{g.credit_score} ({g.tier()[1]})", score_color(g.credit_score)),
            ("Investments", money(g.investments), T["blue"]),
            ("Debt remaining", money(g.card + g.loans + g.overdraft_used()), T["red"] if g.total_debt() else T["dim"]),
            ("Lifetime interest paid", money(g.stats["interest"]), T["red"]),
            ("Lifetime fees paid", money(g.stats["fees"]), T["red"]),
            ("Payments on time / late / missed", f"{g.stats['on_time']} / {g.stats['late']} / {g.stats['missed']}", T["text"]),
            ("Score modifier", mult, T["gold"]),
        ]
        for (a, b), (k, v, c) in zip(self.rows, data):
            a.setText(k)
            b.setText(v)
            set_color(b, c)
        self.score.setText(f"{g.final_score():,}")
        if g.achievements:
            names = "  ·  ".join(esc(g.ACHIEVEMENTS[k][0]) for k in g.achievements)
            self.ach.setText(f"<b>Achievements {len(g.achievements)}/{len(g.ACHIEVEMENTS)}</b><br>{names}")
        else:
            self.ach.setText("No achievements this time.")


# ---------------------------------------------------------------- controller --
class GameUI(QWidget):
    def __init__(self, win, mode):
        super().__init__()
        self.win = win
        self.mode = mode
        desktop = mode == "desktop"
        cw, ch = CANVAS[mode]
        self.setObjectName("root")
        self.setFixedSize(cw, ch)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(build_stylesheet())
        self.setFont(make_font(24))
        self.popup_queue = []

        self.stack = QStackedWidget(self)
        self.stack.setGeometry(0, 0, cw, ch)
        self.start_page = StartPage(self, desktop)
        self.dash = Dashboard(self, desktop)
        self.over_page = GameOverPage(self, desktop)
        for w in (self.start_page, self.dash, self.over_page):
            self.stack.addWidget(w)

        self.event_overlay = EventOverlay(self, self.choose, desktop)
        self.tut = Tutorial(self, desktop)
        self.popup = PopupOverlay(self, self.after_overlay, desktop)
        self.settings = SettingsOverlay(self, self, desktop)
        self.toast = Toast(self)

        if win.page == "menu":
            self.stack.setCurrentWidget(self.start_page)
        else:
            self.after(save=False)

    @property
    def game(self):
        return self.win.game

    # ----------------------------------------------------------- navigation --
    def new_game(self):
        self.win.delete_save()
        self.win.game = LifeGame()
        self.win.game.start()
        self.win.page = "game"
        self.popup_queue.clear()
        self.event_overlay.hide()
        if not self.win.settings.get("tutorial_done"):
            self.tut.start()
        self.after()

    def confirm_new_game(self):
        g = self.game
        body = (f"<p>Starting a new credit card <b>permanently deletes</b> your saved game:</p>"
                f"<p><b>Age {g.age_years} Q{g.quarter()}</b> · net worth {money(g.get_net_worth())} · "
                f"credit {g.credit_score}</p><p>This can't be undone.</p>")
        self.popup_queue.insert(0, {"title": "Delete your saved game?", "body": body, "kind": "warning",
                                    "buttons": [("Delete & start new", "danger", self.win.restart_new_game),
                                                ("Keep my save", "soft", None)]})
        self._pump()

    def resume(self):
        self.win.page = "game"
        self.after(save=False)

    def to_menu(self):
        self.win.save_game()
        self.win.page = "menu"
        self.win.has_save = self.win.save_exists()
        self.win.rebuild_later()

    def open_settings(self):
        self.tut.coach.hide()
        self.settings.open()

    def replay_tutorial(self):
        self.win.settings["tutorial_done"] = False
        self.win.settings["tips_seen"] = []
        self.win.save_settings()
        if self.win.page == "game" and self.game.state == "main":
            self.tut.start()
            self.after()
        else:
            self.toast.push("The tutorial will play when you start or resume a game.", "good")
            self.after_overlay()

    def after_overlay(self):
        if self.win.page == "game" and self.game.state in ("main", "event"):
            self.dash.refresh()
        self._pump()
        self.tut.refresh()

    # -------------------------------------------------------------- actions --
    def act(self, key, fn):
        res = fn()
        ok = not (isinstance(res, tuple) and not res[0])
        if not ok and res[1]:
            self.toast.push(res[1], "bad")
        if ok:
            self.tut.notify(key)
        self.after()

    def do(self, fn):
        self.act(None, fn)

    def choose(self, idx):
        self.act("choose", lambda: self.game.choose_option(idx))

    def advance(self):
        g = self.game
        rem = g.remaining_due()
        if g.state == "main" and rem > 0:
            hit = "LATE payment (−20 credit)" if g.paid_this_qtr else "MISSED payment (−50 credit)"
            can_pay = g.cash >= rem
            body = (f"<p>Your minimum payment of <b>{money(g.min_due)}</b> isn't covered yet — "
                    f"<b>{money(rem)}</b> is still due.</p>"
                    f"<p>If you advance now it counts as a <b style='color:{T['red']}'>{hit}</b>.</p>"
                    + ("" if can_pay else f"<p style='color:{T['red']}'>You don't have enough cash to cover it. "
                       "Consider withdrawing investments or taking a cheaper bank loan to pay the card.</p>"))
            self.popup_queue.insert(0, {"title": "Payment not covered", "body": body, "kind": "warning",
                                        "buttons": [(f"Pay {money(rem)} now", "green", self._pay_and_advance if can_pay else False),
                                                    ("Advance anyway", "red", self._advance_now),
                                                    ("Cancel", "soft", None)]})
            self.tut.coach.hide()
            self._pump()
            return
        self._advance_now()

    def _pay_and_advance(self):
        self.game.pay_minimum()
        self._advance_now()

    def _advance_now(self):
        self.game.next_turn()
        self.tut.notify("advance")
        self.after()

    def confirm_retire(self):
        g = self.game
        mult = 0.5 + g.credit_score / 2000
        body = (f"<p>Retire now with a net worth of <b>{money(g.get_net_worth())}</b>?</p>"
                f"<p>Your final score will be net worth × {mult:.2f} (credit multiplier) = "
                f"<b>{int(g.get_net_worth() * mult):,}</b>.</p>")
        self.popup_queue.insert(0, {"title": "Retire early?", "body": body, "kind": "gold",
                                    "buttons": [("Retire now", "solid_green", lambda: self.do(g.retire_early)),
                                                ("Keep working", "soft", None)]})
        self._pump()

    def show_guide(self):
        self.tut.coach.hide()
        self.popup_queue.insert(0, {"title": "Credit 101", "body": self.game.credit_guide_html(), "kind": "gold"})
        self._pump()

    # ------------------------------------------------------------------------
    def after(self, save=True):
        g = self.game
        for text, tone in g.toasts:
            self.toast.push(text, tone)
        g.toasts.clear()
        for p in g.popups:
            item = dict(p)
            if p.get("guide"):
                item["buttons"] = [("Open full credit guide", "blue", self.show_guide), ("Got it", "primary", None)]
            self.popup_queue.append(item)
        g.popups.clear()

        if g.state == "game_over":
            self.event_overlay.hide()
            self.tut.coach.hide()
            self.popup_queue = [q for q in self.popup_queue if q["title"] == "Credit 101"]
            self.over_page.show_game(g)
            self.stack.setCurrentWidget(self.over_page)
            self.win.delete_save()
        elif g.state in ("main", "event"):
            self.stack.setCurrentWidget(self.dash)
            self.dash.refresh()
            if g.state == "event":
                self.event_overlay.show_event(g)
            else:
                self.event_overlay.hide()
            if save:
                self.win.save_game()
        self._pump()
        self.tut.refresh()

    def _pump(self):
        if self.popup.isVisible() or not self.popup_queue:
            if self.popup.isVisible():
                self.popup.raise_()
            return
        item = self.popup_queue.pop(0)
        self.tut.coach.hide()
        self.popup.show_popup(item["title"], item["body"], item.get("kind", "info"), item.get("buttons"))
        self.toast.raise_()


class ScaledView(QGraphicsView):
    """Uniformly scales the fixed canvas into any window, centred; leftover space shows as bars."""

    def __init__(self, root, cw, ch):
        super().__init__()
        self.cw, self.ch = cw, ch
        self.scene_ = QGraphicsScene(self)
        self.proxy = self.scene_.addWidget(root)
        self.setScene(self.scene_)
        self.setSceneRect(0, 0, cw, ch)
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing |
                            QPainter.RenderHint.SmoothPixmapTransform)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setBackgroundBrush(QBrush(QColor(0, 0, 0)))
        self.setAlignment(AL_C)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        s = min(self.viewport().width() / self.cw, self.viewport().height() / self.ch)
        self.setTransform(QTransform.fromScale(s, s))
        self.centerOn(self.cw / 2, self.ch / 2)

    def wheelEvent(self, e):
        if self.itemAt(e.position().toPoint()) is not None:
            super().wheelEvent(e)


# ------------------------------------------------------------------ storage --
def data_dir():
    d = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    if not d:
        d = os.path.join(os.path.expanduser("~"), ".financial_odyssey")
    os.makedirs(d, exist_ok=True)
    return d


def read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def write_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.replace(tmp, path)                 # atomic: a crash never leaves a half-written save


class MainWindow(QMainWindow):
    def __init__(self, storage_dir=None):
        super().__init__()
        self.setWindowTitle("Financial Odyssey: 18 to 65")
        self.setStyleSheet("QMainWindow { background:#000; }")
        self.dir = storage_dir or data_dir()
        os.makedirs(self.dir, exist_ok=True)
        self.save_path = os.path.join(self.dir, "savegame.json")
        self.settings_path = os.path.join(self.dir, "settings.json")

        self.settings = {"theme": "light", "layout": "mobile", "tutorial_done": False, "tips_seen": []}
        saved = read_json(self.settings_path) or {}
        if saved.get("theme") in THEMES:
            self.settings["theme"] = saved["theme"]
        if saved.get("layout") in CANVAS:
            self.settings["layout"] = saved["layout"]
        if isinstance(saved.get("tutorial_done"), bool):
            self.settings["tutorial_done"] = saved["tutorial_done"]
        if isinstance(saved.get("tips_seen"), list):
            self.settings["tips_seen"] = [str(x) for x in saved["tips_seen"]]
        self.game = self.load_game() or LifeGame()
        self.has_save = self.game.state in ("main", "event")
        self.page = "menu"
        self.ui = None

        self.setMinimumSize(320, 320)
        self.rebuild()
        self.fit_window()
        QShortcut(QKeySequence("F11"), self, self.toggle_fullscreen)
        QShortcut(QKeySequence("Esc"), self, lambda: self.showNormal() if self.isFullScreen() else None)

    # -------------------------------------------------------------- saving --
    def load_game(self):
        d = read_json(self.save_path)
        if not d:
            return None
        try:
            g = LifeGame.from_dict(d)
            return g if g.state in ("main", "event") else None
        except Exception:
            return None

    def save_exists(self):
        return os.path.exists(self.save_path)

    def save_game(self):
        if self.page == "game" and self.game.state in ("main", "event"):
            try:
                write_json(self.save_path, self.game.to_dict())
            except OSError:
                pass

    def delete_save(self):
        try:
            os.remove(self.save_path)
        except OSError:
            pass

    def save_settings(self):
        try:
            write_json(self.settings_path, self.settings)
        except OSError:
            pass

    def restart_new_game(self):
        self.ui.new_game()

    def closeEvent(self, e):
        self.save_game()
        self.save_settings()
        super().closeEvent(e)

    # ------------------------------------------------------- theme & layout --
    def rebuild(self, reopen_settings=False):
        use_theme(self.settings["theme"])
        mode = self.settings["layout"] if self.settings["layout"] in CANVAS else "mobile"
        carry = [q for q in (self.ui.popup_queue if self.ui else []) if not q.get("buttons")]
        self.ui = GameUI(self, mode)
        self.ui.popup_queue[:0] = carry
        cw, ch = CANVAS[mode]
        self.setCentralWidget(ScaledView(self.ui, cw, ch))
        if reopen_settings:
            self.ui.open_settings()
        else:
            self.ui._pump()
            self.ui.tut.refresh()

    def rebuild_later(self, reopen_settings=False):
        # defer so we never delete the widget whose click handler is still running
        QTimer.singleShot(0, lambda: self.rebuild(reopen_settings))

    def set_theme(self, name, reopen=True):
        if name in THEMES and name != self.settings["theme"]:
            self.settings["theme"] = name
            self.save_settings()
            self.rebuild_later(reopen_settings=reopen)

    def set_layout(self, mode):
        if mode in CANVAS and mode != self.settings["layout"]:
            self.settings["layout"] = mode
            self.save_settings()
            self.rebuild_later(reopen_settings=True)
            QTimer.singleShot(0, self.fit_window)

    def fit_window(self):
        """Size the window to the layout's aspect ratio (still letterboxes if resized freely)."""
        if self.isFullScreen() or self.isMaximized():
            return
        cw, ch = CANVAS.get(self.settings["layout"], CANVAS["mobile"])
        scr = (self.screen() or QGuiApplication.primaryScreen()).availableGeometry()
        h = int(scr.height() * 0.90)
        w = int(h * cw / ch)
        if w > scr.width() * 0.92:
            w = int(scr.width() * 0.92)
            h = int(w * ch / cw)
        self.resize(w, h)
        self.move(scr.x() + (scr.width() - w) // 2, scr.y() + (scr.height() - h) // 2)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.fit_window()
        else:
            self.showFullScreen()


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setOrganizationName("FinancialOdyssey")
    app.setApplicationName("Financial Odyssey")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
