#!/usr/bin/env python3
"""
Financial Odyssey: 18 to 65  —  PyQt6 edition

Layout strategy (consistent on every screen / aspect ratio):
  The whole UI is built once on a fixed 1080 x 1920 (9:16) virtual canvas with
  pixel-sized fonts. That canvas lives inside a QGraphicsView and is scaled
  uniformly (vector scaling, so text stays sharp) and centred, with black bars
  filling any leftover space. Every device therefore sees the exact same layout,
  and text that fits once fits everywhere. On top of that, all long text uses
  word-wrapping and single-line values auto-shrink to fit their boxes.

Controls:  F11 = toggle fullscreen,  Esc = leave fullscreen.
"""
import html
import math
import random
import sys

from PyQt6.QtCore import Qt, QTimer, QRectF, QRect
from PyQt6.QtGui import (QColor, QFont, QFontMetrics, QPainter, QPen, QBrush,
                         QGuiApplication, QTransform, QShortcut, QKeySequence)
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
        self.had_debt = False
        self.stats = {"interest": 0, "fees": 0, "on_time": 0, "late": 0, "missed": 0}

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
VW, VH = 1080, 1920                      # fixed virtual canvas (9:16)

C_BG = "#0A1120"
C_CARD = "#121A2C"
C_BORDER = "#22304D"
C_TEXT = "#EEF2FA"
C_MUTED = "#8A97B1"
C_DIM = "#56627C"
C_GREEN = "#22C55E"
C_RED = "#EF4444"
C_RED_L = "#F87171"
C_AMBER = "#F59E0B"
C_GOLD = "#FACC15"
C_BLUE = "#3B82F6"
C_PURPLE = "#8B5CF6"
C_TEAL = "#14B8A6"

TONE_COLORS = {"info": "#C9D3E6", "good": "#4ADE80", "bad": C_RED_L, "warn": "#FBBF24",
               "card": "#A78BFA", "invest": "#60A5FA", "gold": C_GOLD}

FAMILIES = ["Segoe UI", "SF Pro Display", "Inter", "Helvetica Neue", "Roboto",
            "Noto Sans", "Arial", "DejaVu Sans"]

W_NORMAL, W_MED, W_SEMI, W_BOLD = (QFont.Weight.Normal, QFont.Weight.Medium,
                                    QFont.Weight.DemiBold, QFont.Weight.Bold)


def make_font(px, weight=W_NORMAL):
    f = QFont()
    f.setFamilies(FAMILIES)
    f.setPixelSize(int(px))           # pixel sizes => identical layout at any DPI
    f.setWeight(weight)
    f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)  # scales cleanly
    return f


def label(text="", px=24, weight=W_NORMAL, color=C_TEXT, wrap=False,
          align=None, rich=False):
    lb = QLabel(text)
    lb.setFont(make_font(px, weight))
    lb.setStyleSheet(f"color:{color}; background:transparent;")
    lb.setWordWrap(wrap)
    lb.setTextFormat(Qt.TextFormat.RichText if rich else Qt.TextFormat.PlainText)
    if align is not None:
        lb.setAlignment(align)
    if wrap:
        lb.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
    return lb


def set_color(lb, color):
    lb.setStyleSheet(f"color:{color}; background:transparent;")


class FitLabel(QLabel):
    """Single-line label that shrinks its font until the text fits its width."""

    def __init__(self, text="", px=32, weight=W_BOLD, color=C_TEXT, min_px=12,
                 align=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter):
        super().__init__()
        self._px, self._min, self._weight = px, min_px, weight
        self.setFont(make_font(px, weight))
        self.setAlignment(align)
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(int(px * 1.35))
        set_color(self, color)
        self.setText(text)

    def setText(self, text):
        super().setText(text)
        self._fit()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._fit()

    def _fit(self):
        avail = self.width() - 4
        if avail <= 0:
            return
        px = self._px
        f = make_font(px, self._weight)
        while px > self._min and QFontMetrics(f).horizontalAdvance(self.text()) > avail:
            px -= 1
            f.setPixelSize(px)
        if self.font().pixelSize() != px:
            self.setFont(f)


class WrapButton(QPushButton):
    """Push button whose text word-wraps and auto-shrinks to always fit inside."""

    def __init__(self, text="", variant="slate", px=24, weight=W_SEMI, height=None):
        super().__init__()
        self.setProperty("variant", variant)
        self._px, self._weight = px, weight
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 8, 18, 8)
        self.lbl = QLabel()
        self.lbl.setWordWrap(True)
        self.lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl.setTextFormat(Qt.TextFormat.PlainText)
        self.lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.lbl.setFont(make_font(px, weight))
        lay.addWidget(self.lbl)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if height:
            self.setFixedHeight(height)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._text = ""
        self.setText(text)

    def setText(self, text):
        self._text = text
        self.lbl.setText(text)
        self._fit()

    def text(self):
        return self._text

    def set_variant(self, v):
        if self.property("variant") != v:
            self.setProperty("variant", v)
            self.style().unpolish(self)
            self.style().polish(self)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._fit()

    def _fit(self):
        w, h = self.width() - 36, self.height() - 16
        if w <= 0 or h <= 0:
            return
        px = self._px
        f = make_font(px, self._weight)
        flags = int(Qt.TextFlag.TextWordWrap) | int(Qt.AlignmentFlag.AlignCenter)
        while px > 12:
            fm = QFontMetrics(f)
            r = fm.boundingRect(QRect(0, 0, w, 10000), flags, self._text)
            longest = max((fm.horizontalAdvance(word) for word in self._text.split()), default=0)
            if r.height() <= h and longest <= w:
                break
            px -= 1
            f.setPixelSize(px)
        if self.lbl.font().pixelSize() != px:
            self.lbl.setFont(f)


class Card(QFrame):
    def __init__(self, name="card"):
        super().__init__()
        self.setObjectName(name)


class CreditGauge(QWidget):
    def __init__(self):
        super().__init__()
        self.score, self.tier, self.color = 550, "Poor", C_AMBER
        self.setMinimumHeight(200)

    def set_score(self, score, tier, color):
        self.score, self.tier, self.color = score, tier, color
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        pen_w = 24
        r = min((w - pen_w * 2) / 2, (h - pen_w) / 1.52)
        cx, cy = w / 2, pen_w / 2 + r + 6
        rect = QRectF(cx - r, cy - r, 2 * r, 2 * r)

        pen = QPen(QColor("#1C263B"), pen_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawArc(rect, 210 * 16, -240 * 16)

        # tier markers
        p.setPen(QPen(QColor("#33415F"), 3))
        for s in (300, 450, 600, 700, 800):
            ang = math.radians(210 - 240 * s / 1000)
            r1, r2 = r - pen_w / 2 - 6, r - pen_w / 2 - 16
            p.drawLine(int(cx + r1 * math.cos(ang)), int(cy - r1 * math.sin(ang)),
                       int(cx + r2 * math.cos(ang)), int(cy - r2 * math.sin(ang)))

        span = -240 * max(0.0, min(1.0, self.score / 1000))
        if span < 0:
            p.setPen(QPen(QColor(self.color), pen_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(rect, 210 * 16, int(span * 16))

        p.setPen(QColor(C_TEXT))
        p.setFont(make_font(int(r * 0.52), W_BOLD))
        p.drawText(QRectF(cx - r, cy - r * 0.55, 2 * r, r * 0.62), Qt.AlignmentFlag.AlignCenter, str(self.score))
        p.setPen(QColor(self.color))
        p.setFont(make_font(int(r * 0.19), W_BOLD))
        p.drawText(QRectF(cx - r, cy + r * 0.10, 2 * r, r * 0.30), Qt.AlignmentFlag.AlignCenter, self.tier.upper())
        p.end()


class MeterBar(QWidget):
    def __init__(self, height=26):
        super().__init__()
        self.value, self.color = 0.0, C_GREEN
        self.setFixedHeight(height)

    def set_value(self, frac, color):
        self.value, self.color = max(0.0, min(1.0, frac)), color
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(0, 0, self.width(), self.height())
        rad = self.height() / 2
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#1C263B"))
        p.drawRoundedRect(r, rad, rad)
        if self.value > 0:
            fw = max(self.height(), self.width() * self.value)
            p.setBrush(QColor(self.color))
            p.drawRoundedRect(QRectF(0, 0, fw, self.height()), rad, rad)
        p.end()


def score_color(score):
    if score >= 800:
        return C_GREEN
    if score >= 700:
        return "#84CC16"
    if score >= 600:
        return C_GOLD
    if score >= 450:
        return C_AMBER
    return C_RED


def build_stylesheet():
    variants = {
        # name: (top, bottom, hover_top, hover_bottom, text)
        "green":  ("#22C55E", "#15803D", "#34D399", "#16A34A", "#FFFFFF"),
        "blue":   ("#3B82F6", "#1D4ED8", "#60A5FA", "#2563EB", "#FFFFFF"),
        "purple": ("#8B5CF6", "#6D28D9", "#A78BFA", "#7C3AED", "#FFFFFF"),
        "amber":  ("#F59E0B", "#B45309", "#FBBF24", "#D97706", "#1A1100"),
        "red":    ("#EF4444", "#B91C1C", "#F87171", "#DC2626", "#FFFFFF"),
        "gold":   ("#FDE047", "#EAB308", "#FEF08A", "#FACC15", "#1A1300"),
        "teal":   ("#14B8A6", "#0F766E", "#2DD4BF", "#0D9488", "#FFFFFF"),
        "slate":  ("#273349", "#1E293D", "#334262", "#26334D", "#E5EBF5"),
    }
    qss = [f"""
    QWidget#root {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0C1528, stop:1 #060A14); }}
    QFrame#card {{ background-color:{C_CARD}; border:1px solid {C_BORDER}; border-radius:26px; }}
    QFrame#tile {{ background-color:#0F1626; border:1px solid {C_BORDER}; border-radius:20px; }}
    QFrame#infobox {{ background-color:#0C1322; border:1px solid #2E3E62; border-radius:18px; }}
    QFrame#modal {{ background-color:#131C30; border:2px solid #34466E; border-radius:30px; }}
    QFrame#toast {{ background-color:#1B2540; border:2px solid {C_GOLD}; border-radius:22px; }}
    QPushButton {{ border:none; border-radius:18px; }}
    QPushButton QLabel {{ background:transparent; }}
    QPushButton QLabel:disabled {{ color:#4E5A73; }}
    QSpinBox {{ background-color:#0C1322; color:{C_TEXT}; border:2px solid #2E3E62; border-radius:16px;
               padding:0px 6px; selection-background-color:{C_PURPLE}; }}
    QSpinBox::up-button, QSpinBox::down-button {{ width:0px; border:none; }}
    QSpinBox::up-arrow, QSpinBox::down-arrow {{ width:0px; height:0px; }}
    QSpinBox:focus {{ border-color:{C_PURPLE}; }}
    QCheckBox {{ color:#C9D3E6; spacing:14px; background:transparent; }}
    QCheckBox::indicator {{ width:30px; height:30px; border-radius:9px; border:2px solid #3A4A6E; background:#0C1322; }}
    QCheckBox::indicator:checked {{ background:{C_PURPLE}; border-color:#A78BFA; }}
    QScrollArea {{ background:transparent; border:none; }}
    QScrollArea > QWidget > QWidget {{ background:transparent; }}
    QScrollBar:vertical {{ width:12px; background:transparent; margin:4px; }}
    QScrollBar::handle:vertical {{ background:#2E3E62; border-radius:4px; min-height:50px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background:transparent; }}
    QToolTip {{ background:#1B2540; color:{C_TEXT}; border:1px solid #34466E; padding:6px; }}
    """]
    for name, (t, b, ht, hb, txt) in variants.items():
        qss.append(f"""
        QPushButton[variant="{name}"] {{ background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 {t}, stop:1 {b}); }}
        QPushButton[variant="{name}"]:hover {{ background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 {ht}, stop:1 {hb});
                                               border:2px solid rgba(255,255,255,0.55); }}
        QPushButton[variant="{name}"]:pressed {{ background:{b}; }}
        QPushButton[variant="{name}"]:disabled {{ background:#151D2F; border:1px solid #1F2A42; }}
        QPushButton[variant="{name}"] QLabel {{ color:{txt}; }}
        QPushButton[variant="{name}"] QLabel:disabled {{ color:#4E5A73; }}
        """)
    qss.append(f"""
    QPushButton[variant="chip"] {{ background:#172036; border:2px solid #2C3A58; border-radius:14px; }}
    QPushButton[variant="chip"]:hover {{ border-color:{C_PURPLE}; }}
    QPushButton[variant="chip"] QLabel {{ color:#C9D3E6; }}
    QPushButton[variant="ghost"] {{ background:transparent; border:2px solid #34466E; border-radius:14px; }}
    QPushButton[variant="ghost"]:hover {{ border-color:{C_GOLD}; }}
    QPushButton[variant="ghost"] QLabel {{ color:{C_GOLD}; }}
    """)
    return "\n".join(qss)


# ------------------------------------------------------------------ overlays --
class Overlay(QWidget):
    """Full-canvas dimmed layer with a centred modal card."""

    def __init__(self, parent, width=960):
        super().__init__(parent)
        self.setGeometry(0, 0, VW, VH)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(40, 60, 40, 60)
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
        self.body.setContentsMargins(44, 40, 44, 40)
        self.body.setSpacing(20)
        self.hide()

    def paintEvent(self, e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(3, 6, 14, 215))
        p.end()

    def mousePressEvent(self, e):
        e.accept()                                  # block clicks to the page below

    def clear(self):
        def wipe(layout):
            while layout.count():
                item = layout.takeAt(0)
                w = item.widget()
                if w is not None:
                    w.hide()
                    w.setParent(None)        # detach now so nothing old is painted
                    w.deleteLater()
                elif item.layout():
                    wipe(item.layout())
        wipe(self.body)


class EventOverlay(Overlay):
    def __init__(self, parent, on_choose):
        super().__init__(parent)
        self.on_choose = on_choose
        self.key = None

    def show_event(self, g):
        ev = g.current_event
        if self.isVisible() and self.key is ev:
            return
        self.key = ev
        self.clear()
        b = self.body
        b.addWidget(label(f"QUARTERLY EVENT  ·  AGE {g.age_years}  ·  Q{g.quarter()}", 22, W_BOLD, C_GOLD,
                          align=Qt.AlignmentFlag.AlignCenter))
        b.addWidget(label(ev["title"], 50, W_BOLD, C_TEXT, wrap=True, align=Qt.AlignmentFlag.AlignCenter))
        b.addWidget(label(ev["desc"], 28, W_NORMAL, "#B7C2D8", wrap=True, align=Qt.AlignmentFlag.AlignCenter))
        if ev.get("info"):
            box = Card("infobox")
            bl = QVBoxLayout(box)
            bl.setContentsMargins(26, 20, 26, 20)
            bl.addWidget(label("WHY IT MATTERS", 19, W_BOLD, C_GOLD))
            bl.addWidget(label(ev["info"], 23, W_NORMAL, "#C9D3E6", wrap=True))
            b.addWidget(box)

        status = (f"Cash {money(g.cash)}   ·   Card credit left {money(g.card_available())}   ·   "
                  f"Happiness {g.happiness}   ·   Credit {g.credit_score}")
        b.addWidget(label(status, 21, W_SEMI, C_MUTED, wrap=True, align=Qt.AlignmentFlag.AlignCenter))
        b.addSpacing(6)

        tone_variant = {"cash": "green", "card": "purple", "loan": "amber", "bad": "red",
                        "good": "teal", "info": "blue", "skip": "slate"}
        for i, o in enumerate(ev["options"]):
            reason = g.option_block_reason(o)
            text = o["label"] + (f"\n(unavailable: {reason})" if reason else "")
            btn = WrapButton(text, tone_variant.get(o["tone"], "slate"), 26, W_SEMI, height=104)
            btn.setEnabled(reason is None)
            btn.clicked.connect(lambda _=False, idx=i: self.on_choose(idx))
            b.addWidget(btn)
        self.show()
        self.raise_()


class PopupOverlay(Overlay):
    KIND_COLORS = {"warning": C_RED, "success": C_GREEN, "info": C_BLUE, "gold": C_GOLD}

    def __init__(self, parent, on_close):
        super().__init__(parent, width=980)
        self.on_close = on_close

    def show_popup(self, title, body_html, kind="info", buttons=None):
        self.clear()
        b = self.body
        stripe = QFrame()
        stripe.setFixedHeight(8)
        stripe.setStyleSheet(f"background:{self.KIND_COLORS.get(kind, C_BLUE)}; border-radius:4px;")
        b.addWidget(stripe)
        b.addWidget(label(title, 46, W_BOLD, C_TEXT, wrap=True, align=Qt.AlignmentFlag.AlignCenter))

        body = label(body_html, 25, W_NORMAL, "#D3DBEA", wrap=True, rich=True)
        body.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        holder = QWidget()
        hl = QVBoxLayout(holder)
        hl.setContentsMargins(0, 0, 18, 0)
        hl.addWidget(body)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(holder)
        need = body.heightForWidth(980 - 88 - 30) + 36
        scroll.setFixedHeight(max(120, min(1180, need)))
        b.addWidget(scroll)

        row = QHBoxLayout()
        row.setSpacing(16)
        for text, variant, cb in (buttons or [("Got it", "gold", None)]):
            btn = WrapButton(text, variant, 28, W_BOLD, height=96)
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


class Toast(QFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("toast")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(28, 18, 28, 18)
        self.lbl = label("", 25, W_SEMI, C_TEXT, wrap=True, align=Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.lbl)
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
        color = TONE_COLORS.get(tone, C_GOLD)
        self.setStyleSheet(f"QFrame#toast {{ background-color:#1B2540; border:2px solid {color}; border-radius:22px; }}")
        self.lbl.setText(text)
        w = 900
        h = self.lbl.heightForWidth(w - 56) + 40
        self.setGeometry((VW - w) // 2, 26, w, max(80, h))
        self.show()
        self.raise_()
        self.timer.start(2800)

    def mousePressEvent(self, e):
        self.timer.stop()
        self._next()


# --------------------------------------------------------------------- pages --
class StartPage(QWidget):
    def __init__(self, on_start, on_guide):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(56, 90, 56, 80)
        lay.setSpacing(26)
        lay.addWidget(label("FINANCIAL ODYSSEY", 74, W_BOLD, C_GOLD, align=Qt.AlignmentFlag.AlignCenter, wrap=True))
        lay.addWidget(label("Ages 18 to 65  ·  one quarter at a time", 32, W_MED, C_MUTED,
                            align=Qt.AlignmentFlag.AlignCenter, wrap=True))
        card = Card()
        cl = QVBoxLayout(card)
        cl.setContentsMargins(44, 40, 44, 40)
        cl.setSpacing(24)
        cl.addWidget(label("Happy 18th birthday!", 44, W_BOLD, C_TEXT, wrap=True))
        cl.addWidget(label("Your first credit card was just approved. Earn, spend, borrow and invest your way "
                           "to retirement — without going broke, burning out or wrecking your credit.",
                           30, W_NORMAL, "#B7C2D8", wrap=True))
        rules = [
            ("1 turn = 3 months.", "Each quarter you're paid, compulsory rent, groceries & bills are taken, and a life event happens."),
            ("Happiness drains every quarter.", "Buy leisure to refill it. At 0 for a full year you die of depression."),
            ("Bills come due.", "Card and loan balances post a minimum payment. Pay it before advancing to grow your credit."),
            ("Credit = cheaper money.", "Higher scores unlock lower interest, bigger limits and loans. Capped at 700 for your first 5 years."),
            ("Costs rise faster than pay.", "Inflation outpaces raises, so certifications and investing matter."),
            ("Hit $1,000,000 net worth", "and you may retire early. Otherwise you retire at 65."),
        ]
        for head, text in rules:
            cl.addWidget(label(f"<b style='color:{C_GOLD}'>{esc(head)}</b> {esc(text)}", 28, W_NORMAL, "#D3DBEA",
                               wrap=True, rich=True))
        lay.addWidget(card)
        lay.addStretch(1)
        guide = WrapButton("Credit 101 — how credit scores work", "ghost", 30, W_BOLD, height=96)
        guide.clicked.connect(on_guide)
        lay.addWidget(guide)
        start = WrapButton("BEGIN YOUR JOURNEY", "gold", 46, W_BOLD, height=140)
        start.clicked.connect(on_start)
        lay.addWidget(start)


class Tile(Card):
    def __init__(self, caption):
        super().__init__("tile")
        self.setFixedHeight(132)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 14, 22, 14)
        lay.setSpacing(2)
        self.cap = FitLabel(caption, 19, W_BOLD, C_MUTED)
        self.val = FitLabel("", 40, W_BOLD, C_TEXT)
        self.sub = FitLabel("", 19, W_MED, C_MUTED)
        lay.addWidget(self.cap)
        lay.addWidget(self.val)
        lay.addWidget(self.sub)

    def set(self, value, color, sub, sub_color=C_MUTED):
        self.val.setText(value)
        set_color(self.val, color)
        self.sub.setText(sub)
        set_color(self.sub, sub_color)


class Dashboard(QWidget):
    def __init__(self, ui):
        super().__init__()
        self.ui = ui
        lay = QVBoxLayout(self)
        lay.setContentsMargins(36, 30, 36, 30)
        lay.setSpacing(16)

        # --- header -----------------------------------------------------------
        hdr = Card()
        hdr.setFixedHeight(150)
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(34, 18, 34, 18)
        left = QVBoxLayout()
        left.setSpacing(0)
        self.age_lbl = FitLabel("", 56, W_BOLD, C_GOLD)
        self.sub_lbl = FitLabel("", 22, W_MED, C_MUTED)
        left.addWidget(self.age_lbl)
        left.addWidget(self.sub_lbl)
        right = QVBoxLayout()
        right.setSpacing(0)
        ar = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        self.nw_cap = FitLabel("NET WORTH", 22, W_BOLD, C_MUTED, align=ar)
        self.nw_lbl = FitLabel("", 54, W_BOLD, C_GREEN, align=ar)
        right.addWidget(self.nw_cap)
        right.addWidget(self.nw_lbl)
        hl.addLayout(left, 1)
        hl.addLayout(right, 1)
        lay.addWidget(hdr)

        # --- credit + happiness -------------------------------------------------
        row = QHBoxLayout()
        row.setSpacing(16)
        cc = Card()
        cc.setFixedHeight(372)
        cl = QVBoxLayout(cc)
        cl.setContentsMargins(26, 18, 26, 18)
        cl.setSpacing(6)
        top = QHBoxLayout()
        top.addWidget(label("CREDIT SCORE", 22, W_BOLD, C_MUTED))
        top.addStretch(1)
        gbtn = WrapButton("Guide", "ghost", 20, W_BOLD, height=44)
        gbtn.setFixedWidth(110)
        gbtn.clicked.connect(ui.show_guide)
        top.addWidget(gbtn)
        cl.addLayout(top)
        self.gauge = CreditGauge()
        self.gauge.setFixedHeight(196)
        cl.addWidget(self.gauge)
        self.rates_lbl = FitLabel("", 21, W_SEMI, "#C9D3E6", align=Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(self.rates_lbl)
        self.credit_note = label("", 19, W_MED, C_MUTED, wrap=True, align=Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(self.credit_note)
        cl.addStretch(1)
        row.addWidget(cc, 1)

        hc = Card()
        hc.setFixedHeight(372)
        hcl = QVBoxLayout(hc)
        hcl.setContentsMargins(26, 18, 26, 20)
        hcl.setSpacing(8)
        hcl.addWidget(label("HAPPINESS", 22, W_BOLD, C_MUTED))
        self.happy_val = FitLabel("", 66, W_BOLD, C_GREEN)
        hcl.addWidget(self.happy_val)
        self.happy_bar = MeterBar(26)
        hcl.addWidget(self.happy_bar)
        self.happy_note = label("", 20, W_MED, C_MUTED, wrap=True)
        hcl.addWidget(self.happy_note)
        hcl.addStretch(1)
        self.buy_btn = WrapButton("", "green", 24, W_BOLD, height=92)
        self.buy_btn.clicked.connect(lambda: ui.do(ui.game.buy_happiness))
        hcl.addWidget(self.buy_btn)
        row.addWidget(hc, 1)
        lay.addLayout(row)

        # --- money tiles --------------------------------------------------------
        grid = QGridLayout()
        grid.setSpacing(14)
        self.t_cash, self.t_inv, self.t_card = Tile("CASH"), Tile("INVESTMENTS"), Tile("CREDIT CARD")
        self.t_loan, self.t_inc, self.t_ess = Tile("BANK LOANS"), Tile("PAY / QUARTER"), Tile("ESSENTIALS / QTR")
        for i, t in enumerate([self.t_cash, self.t_inv, self.t_card, self.t_loan, self.t_inc, self.t_ess]):
            grid.addWidget(t, i // 3, i % 3)
        lay.addLayout(grid)

        # --- bills ----------------------------------------------------------------
        bc = Card()
        bc.setFixedHeight(168)
        bl = QHBoxLayout(bc)
        bl.setContentsMargins(28, 16, 28, 16)
        bl.setSpacing(20)
        bleft = QVBoxLayout()
        bleft.setSpacing(2)
        bleft.addWidget(FitLabel("MINIMUM PAYMENT DUE THIS QUARTER", 20, W_BOLD, C_MUTED))
        self.due_val = FitLabel("", 42, W_BOLD, C_TEXT)
        bleft.addWidget(self.due_val)
        self.due_note = label("", 19, W_MED, C_MUTED, wrap=True)
        bleft.addWidget(self.due_note)
        bl.addLayout(bleft, 3)
        bright = QVBoxLayout()
        bright.setSpacing(10)
        self.due_chip = FitLabel("", 22, W_BOLD, C_TEXT, align=Qt.AlignmentFlag.AlignCenter)
        self.due_chip.setFixedHeight(46)
        bright.addWidget(self.due_chip)
        self.autopay = QCheckBox("Charge essentials to card (builds credit)")
        self.autopay.setFont(make_font(19, W_MED))
        self.autopay.toggled.connect(self._toggle_autopay)
        bright.addWidget(self.autopay)
        bl.addLayout(bright, 2)
        lay.addWidget(bc)

        # --- actions --------------------------------------------------------------
        ac = Card()
        al = QVBoxLayout(ac)
        al.setContentsMargins(26, 18, 26, 20)
        al.setSpacing(14)
        arow = QHBoxLayout()
        arow.setSpacing(10)
        arow.addWidget(label("AMOUNT", 22, W_BOLD, C_MUTED))
        minus = WrapButton("−", "chip", 32, W_BOLD, height=62)
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
        self.amount.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.amount.setFont(make_font(30, W_BOLD))
        self.amount.setFixedSize(230, 62)
        self.amount.valueChanged.connect(lambda _: self.refresh())
        arow.addWidget(self.amount)
        plus = WrapButton("+", "chip", 32, W_BOLD, height=62)
        plus.setFixedWidth(66)
        plus.clicked.connect(lambda: self.amount.stepBy(1))
        arow.addWidget(plus)
        for txt, val in (("$100", 100), ("$500", 500), ("$1k", 1000), ("$5k", 5000), ("All", None)):
            chip = WrapButton(txt, "chip", 22, W_BOLD, height=62)
            chip.clicked.connect(lambda _=False, v=val: self._set_amount(v))
            arow.addWidget(chip)
        al.addLayout(arow)

        agrid = QGridLayout()
        agrid.setSpacing(12)
        self.b_invest = WrapButton("", "blue", 23, W_BOLD, height=88)
        self.b_withdraw = WrapButton("", "purple", 23, W_BOLD, height=88)
        self.b_loan = WrapButton("", "amber", 23, W_BOLD, height=88)
        self.b_pay = WrapButton("", "teal", 23, W_BOLD, height=88)
        self.b_min = WrapButton("", "green", 23, W_BOLD, height=88)
        self.b_all = WrapButton("", "teal", 23, W_BOLD, height=88)
        self.b_invest.clicked.connect(lambda: ui.do(lambda: ui.game.invest(self.amount.value())))
        self.b_withdraw.clicked.connect(lambda: ui.do(lambda: ui.game.withdraw(self.amount.value())))
        self.b_loan.clicked.connect(lambda: ui.do(lambda: ui.game.take_loan(self.amount.value())))
        self.b_pay.clicked.connect(lambda: ui.do(lambda: ui.game.pay_debt(self.amount.value())))
        self.b_min.clicked.connect(lambda: ui.do(ui.game.pay_minimum))
        self.b_all.clicked.connect(lambda: ui.do(ui.game.pay_all))
        for i, b in enumerate([self.b_invest, self.b_withdraw, self.b_loan, self.b_min, self.b_pay, self.b_all]):
            agrid.addWidget(b, i // 3, i % 3)
        al.addLayout(agrid)
        lay.addWidget(ac)

        # --- log ------------------------------------------------------------------
        lc = Card()
        ll = QVBoxLayout(lc)
        ll.setContentsMargins(28, 16, 18, 16)
        ll.setSpacing(8)
        ll.addWidget(label("ACTIVITY LOG", 22, W_BOLD, C_MUTED))
        self.log_lbl = label("", 21, W_NORMAL, C_TEXT, wrap=True, rich=True)
        self.log_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        holder = QWidget()
        hl2 = QVBoxLayout(holder)
        hl2.setContentsMargins(0, 0, 12, 0)
        hl2.addWidget(self.log_lbl)
        hl2.addStretch(1)
        self.log_scroll = QScrollArea()
        self.log_scroll.setWidgetResizable(True)
        self.log_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.log_scroll.setWidget(holder)
        ll.addWidget(self.log_scroll)
        lay.addWidget(lc, 1)

        # --- bottom -----------------------------------------------------------------
        brow = QHBoxLayout()
        brow.setSpacing(16)
        self.retire_btn = WrapButton("RETIRE EARLY", "teal", 30, W_BOLD, height=116)
        self.retire_btn.clicked.connect(ui.confirm_retire)
        self.retire_btn.setFixedWidth(330)
        brow.addWidget(self.retire_btn)
        self.next_btn = WrapButton("ADVANCE 3 MONTHS  »", "gold", 44, W_BOLD, height=116)
        self.next_btn.clicked.connect(ui.advance)
        brow.addWidget(self.next_btn)
        lay.addLayout(brow)

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
            self.refresh()

    def refresh(self):
        g = self.ui.game
        amt = self.amount.value()

        years_left = 65 - g.age_years
        self.age_lbl.setText(f"AGE {g.age_years}  ·  Q{g.quarter()}")
        self.sub_lbl.setText(f"{years_left} years to retirement  ·  Turn {g.turns_played}")
        nw = g.get_net_worth()
        self.nw_lbl.setText(money(nw))
        set_color(self.nw_lbl, C_GREEN if nw >= 0 else C_RED_L)

        t = g.tier()
        col = score_color(g.credit_score)
        self.gauge.set_score(g.credit_score, t[1], col)
        self.rates_lbl.setText(f"Loans {t[2]:.2%}/qtr  ·  Card {t[3]:.2%}/qtr")
        notes = []
        if g.history_capped():
            notes.append(f"History cap: max 700 for {g.HISTORY_CAP_TURNS - g.turns_played} more quarters")
        if g.streak:
            notes.append(f"On-time streak: {g.streak}")
        if g.low_credit_turns or g.credit_score < g.IRS_SCORE:
            notes.append(f"IRS SEIZURE RISK: {g.low_credit_turns}/{g.IRS_TURNS} strikes")
        self.credit_note.setText("  ·  ".join(notes) if notes else "Pay your minimum each quarter to climb")
        set_color(self.credit_note, C_RED_L if g.low_credit_turns or g.credit_score < g.IRS_SCORE else C_MUTED)

        hcol = C_GREEN if g.happiness > 50 else (C_GOLD if g.happiness > 25 else C_RED)
        self.happy_val.setText(f"{g.happiness} / 100")
        set_color(self.happy_val, hcol)
        self.happy_bar.set_value(g.happiness / 100, hcol)
        if g.zero_happiness_turns:
            self.happy_note.setText(f"DEPRESSION WARNING {g.zero_happiness_turns}/{g.DEPRESSION_TURNS} — "
                                    "buy leisure now or you won't survive the year!")
            set_color(self.happy_note, C_RED_L)
        else:
            self.happy_note.setText(f"Life & work stress drain about {g.happiness_decay()} every quarter. "
                                    f"Zero for a year is fatal.")
            set_color(self.happy_note, C_MUTED)
        cost = g.happiness_cost()
        self.buy_btn.setText(f"Buy leisure & hobbies\n-{money(cost)}  ·  +{g.HAPPY_PTS} happiness")
        self.buy_btn.setEnabled(g.cash >= cost and g.happiness < 100)

        od = g.overdraft_used()
        self.t_cash.set(money(g.cash), C_RED_L if g.cash < 0 else C_GREEN,
                        f"OVERDRAFT {money(od)} / {money(g.OVERDRAFT_LIMIT)}" if od else
                        f"Overdraft limit {money(g.OVERDRAFT_LIMIT)}", C_RED_L if od else C_MUTED)
        fee_txt = "No withdrawal fee (60+)" if g.withdraw_fee_rate() == 0 else "5% fee to withdraw before 60"
        self.t_inv.set(money(g.investments), "#60A5FA", fee_txt)
        util = g.card / max(1, g.card_limit())
        self.t_card.set(money(g.card), "#A78BFA" if g.card <= g.card_limit() else C_RED_L,
                        f"{money(g.card_available())} free of {money(g.card_limit())}",
                        C_RED_L if util > 0.9 else C_MUTED)
        cap = g.loan_capacity()
        self.t_loan.set(money(g.loans), C_AMBER if g.loans else C_DIM,
                        f"Can borrow {money(g.loan_room())}" if cap else "Loans need a 450+ score",
                        C_MUTED if cap else C_RED_L)
        inc_sub = f"Certifications {g.courses_taken}/{g.MAX_COURSES}"
        if g.layoff_turns:
            inc_sub = f"{int(g.layoff_mult * 100)}% pay for {g.layoff_turns} more qtr"
        elif not g.has_car:
            inc_sub += "  ·  no car -10%"
        self.t_inc.set(money(g.quarterly_income()), C_GOLD, inc_sub, C_AMBER if g.layoff_turns else C_MUTED)
        items = g.essentials_breakdown()
        self.t_ess.set(money(g.essentials_total()), "#FCA5A5", "Rent, food & bills — compulsory")
        self.t_ess.setToolTip("\n".join(f"{n}: {money(v)}" for n, v in items))

        # bills
        rem = g.remaining_due()
        if g.min_due <= 0:
            self.due_val.setText("$0 — no bill")
            set_color(self.due_val, C_MUTED)
            self.due_note.setText("No card or loan balance on your last statement. Use your card and pay it "
                                  "back to build credit.")
            self.due_chip.setText("NO BILL")
            self.due_chip.setStyleSheet(f"color:{C_MUTED}; background:#1A2337; border-radius:14px;")
        elif rem <= 0:
            self.due_val.setText(f"{money(g.min_due)}  ✓ paid")
            set_color(self.due_val, C_GREEN)
            extra = ("Statement fully paid — no card interest." if g.paid_card_this_qtr >= g.stmt_card
                     else f"Pay the full {money(g.stmt_card)} statement to skip card interest.")
            self.due_note.setText(f"Paid {money(g.paid_this_qtr)} this quarter. {extra}")
            self.due_chip.setText("ON TIME")
            self.due_chip.setStyleSheet(f"color:#04130A; background:{C_GREEN}; border-radius:14px;")
        else:
            self.due_val.setText(f"{money(rem)} still due")
            set_color(self.due_val, C_GOLD)
            self.due_note.setText(f"Minimum {money(g.min_due)}, paid {money(g.paid_this_qtr)}. Advance now = "
                                  f"{'LATE (-20)' if g.paid_this_qtr else 'MISSED (-50)'}.")
            self.due_chip.setText("UNPAID")
            self.due_chip.setStyleSheet(f"color:#1A0505; background:{C_RED_L}; border-radius:14px;")
        if self.autopay.isChecked() != g.essentials_on_card:
            self.autopay.blockSignals(True)
            self.autopay.setChecked(g.essentials_on_card)
            self.autopay.blockSignals(False)

        # action buttons
        fee = int(min(amt, g.investments) * g.withdraw_fee_rate())
        self.b_invest.setText(f"Invest\n{money(amt)}")
        self.b_invest.setEnabled(0 < amt <= g.cash)
        self.b_withdraw.setText(f"Withdraw\n{money(min(amt, g.investments))}" + (f" (-{money(fee)} fee)" if fee else ""))
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

        # log (newest first)
        lines = []
        for when, text, tone in reversed(g.log[-60:]):
            lines.append(f"<span style='color:{C_DIM}'>{esc(when)}</span>&nbsp;&nbsp;"
                         f"<span style='color:{TONE_COLORS.get(tone, C_TEXT)}'>{esc(text)}</span>")
        self.log_lbl.setText("<br>".join(lines))

        self.retire_btn.setVisible(g.get_net_worth() >= g.MILLION)
        self.next_btn.setEnabled(g.state == "main")


class GameOverPage(QWidget):
    def __init__(self, on_restart):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(56, 90, 56, 80)
        lay.setSpacing(24)
        self.title = label("", 70, W_BOLD, C_GOLD, wrap=True, align=Qt.AlignmentFlag.AlignCenter)
        self.sub = label("", 30, W_MED, "#C9D3E6", wrap=True, align=Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.title)
        lay.addWidget(self.sub)
        self.card = Card()
        cl = QVBoxLayout(self.card)
        cl.setContentsMargins(44, 34, 44, 34)
        cl.setSpacing(4)
        self.rows = []
        for _ in range(9):
            r = QHBoxLayout()
            a = FitLabel("", 30, W_SEMI, C_MUTED)
            b = FitLabel("", 34, W_BOLD, C_TEXT, align=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            r.addWidget(a, 3)
            r.addWidget(b, 2)
            cl.addLayout(r)
            self.rows.append((a, b))
        cl.addSpacing(16)
        self.score_cap = FitLabel("FINAL SCORE", 30, W_BOLD, C_GOLD, align=Qt.AlignmentFlag.AlignCenter)
        self.score = FitLabel("", 80, W_BOLD, C_GOLD, align=Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(self.score_cap)
        cl.addWidget(self.score)
        lay.addWidget(self.card)
        self.ach = label("", 24, W_NORMAL, "#C9D3E6", wrap=True, rich=True, align=Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.ach)
        lay.addStretch(1)
        btn = WrapButton("PLAY AGAIN", "green", 50, W_BOLD, height=140)
        btn.clicked.connect(on_restart)
        lay.addWidget(btn)

    def show_game(self, g):
        r = g.end_reason
        if r in ("RETIREMENT", "EARLY_RETIREMENT"):
            self.title.setText("CONGRATULATIONS!")
            set_color(self.title, C_GOLD)
            self.sub.setText("You retired early as a millionaire!" if r == "EARLY_RETIREMENT"
                             else "You made it to 65 and retired.")
        elif r == "IRS_SEIZURE":
            self.title.setText("ASSETS SEIZED")
            set_color(self.title, C_RED_L)
            self.sub.setText("Your credit score stayed under 300 for two years and the IRS took everything.")
        else:
            self.title.setText("LOST TO DEPRESSION")
            set_color(self.title, C_RED_L)
            self.sub.setText("Your happiness stayed at 0 for a full year. Money matters — but so does living.")
        nw = g.get_net_worth()
        mult = f"x{0.5 + g.credit_score / 2000:.2f} credit multiplier" if r in ("RETIREMENT", "EARLY_RETIREMENT") \
            else f"-{money(g.DEATH_PENALTY)} penalty"
        data = [
            ("Age reached", str(g.age_years), C_TEXT),
            ("Net worth", money(nw), C_GREEN if nw >= 0 else C_RED_L),
            ("Credit score", f"{g.credit_score} ({g.tier()[1]})", score_color(g.credit_score)),
            ("Investments", money(g.investments), "#60A5FA"),
            ("Debt remaining", money(g.card + g.loans + g.overdraft_used()), C_RED_L if g.total_debt() else C_DIM),
            ("Lifetime interest paid", money(g.stats["interest"]), C_RED_L),
            ("Lifetime fees paid", money(g.stats["fees"]), C_RED_L),
            ("Payments on time / late / missed", f"{g.stats['on_time']} / {g.stats['late']} / {g.stats['missed']}", C_TEXT),
            ("Score modifier", mult, C_GOLD),
        ]
        for (a, b), (k, v, c) in zip(self.rows, data):
            a.setText(k)
            b.setText(v)
            set_color(b, c)
        self.score.setText(f"{g.final_score():,}")
        if g.achievements:
            names = "  ·  ".join(esc(g.ACHIEVEMENTS[k][0]) for k in g.achievements)
            self.ach.setText(f"<b style='color:{C_GOLD}'>Achievements ({len(g.achievements)}/{len(g.ACHIEVEMENTS)})</b><br>{names}")
        else:
            self.ach.setText("No achievements this time.")


# ---------------------------------------------------------------- controller --
class GameUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("root")
        self.setFixedSize(VW, VH)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(build_stylesheet())
        self.setFont(make_font(24))
        self.game = LifeGame()
        self.popup_queue = []

        self.stack = QStackedWidget(self)
        self.stack.setGeometry(0, 0, VW, VH)
        self.start_page = StartPage(self.start_game, self.show_guide)
        self.dash = Dashboard(self)
        self.over_page = GameOverPage(self.restart)
        for w in (self.start_page, self.dash, self.over_page):
            self.stack.addWidget(w)

        self.event_overlay = EventOverlay(self, self.choose)
        self.popup = PopupOverlay(self, self._pump)
        self.toast = Toast(self)

    # ------------------------------------------------------------------------
    def start_game(self):
        self.game.start()
        self.stack.setCurrentWidget(self.dash)
        self.after()

    def restart(self):
        self.game.reset()
        self.event_overlay.hide()
        self.popup_queue.clear()
        self.dash.amount.setValue(500)
        self.start_game()

    def do(self, fn):
        res = fn()
        if isinstance(res, tuple) and not res[0] and res[1]:
            self.toast.push(res[1], "bad")
        self.after()

    def choose(self, idx):
        self.do(lambda: self.game.choose_option(idx))

    def advance(self):
        g = self.game
        rem = g.remaining_due()
        if g.state == "main" and rem > 0:
            hit = "LATE payment (-20 credit)" if g.paid_this_qtr else "MISSED payment (-50 credit)"
            can_pay = g.cash >= rem
            body = (f"<p>Your minimum payment of <b>{money(g.min_due)}</b> isn't covered yet — "
                    f"<b style='color:{C_GOLD}'>{money(rem)}</b> is still due.</p>"
                    f"<p>If you advance now it counts as a <b style='color:{C_RED_L}'>{hit}</b>.</p>"
                    + ("" if can_pay else f"<p style='color:{C_RED_L}'>You don't have enough cash to cover it. "
                       "Consider withdrawing investments or taking a cheaper bank loan to pay the card.</p>"))
            self.popup_queue.insert(0, ("Payment not covered", body, "warning", [
                (f"Pay {money(rem)} now", "green", self._pay_and_advance if can_pay else False),
                ("Advance anyway", "red", self._advance_now),
                ("Cancel", "slate", None)]))
            self._pump()
            return
        self._advance_now()

    def _pay_and_advance(self):
        self.game.pay_minimum()
        self._advance_now()

    def _advance_now(self):
        self.game.next_turn()
        self.after()

    def confirm_retire(self):
        g = self.game
        mult = 0.5 + g.credit_score / 2000
        body = (f"<p>Retire now with a net worth of <b>{money(g.get_net_worth())}</b>?</p>"
                f"<p>Your final score will be net worth x {mult:.2f} (credit multiplier) = "
                f"<b style='color:{C_GOLD}'>{int(g.get_net_worth() * mult):,}</b>.</p>")
        self.popup_queue.insert(0, ("Retire early?", body, "gold", [
            ("Retire now", "teal", lambda: self.do(g.retire_early)),
            ("Keep working", "slate", None)]))
        self._pump()

    def show_guide(self):
        self.popup_queue.insert(0, ("Credit 101", self.game.credit_guide_html(), "gold", None))
        self._pump()

    # ------------------------------------------------------------------------
    def after(self):
        g = self.game
        for text, tone in g.toasts:
            self.toast.push(text, tone)
        g.toasts.clear()
        for p in g.popups:
            btns = None
            if p.get("guide"):
                btns = [("Open full credit guide", "ghost", self.show_guide), ("Got it", "gold", None)]
            self.popup_queue.append((p["title"], p["body"], p.get("kind", "info"), btns))
        g.popups.clear()

        if g.state == "game_over":
            self.event_overlay.hide()
            self.popup_queue = [q for q in self.popup_queue if q[0] == "Credit 101"]
            self.over_page.show_game(g)
            self.stack.setCurrentWidget(self.over_page)
        elif g.state in ("main", "event"):
            self.dash.refresh()
            if g.state == "event":
                self.event_overlay.show_event(g)
            else:
                self.event_overlay.hide()
        self._pump()

    def _pump(self):
        if self.popup.isVisible() or not self.popup_queue:
            if self.popup.isVisible():
                self.popup.raise_()
            return
        title, body, kind, btns = self.popup_queue.pop(0)
        self.popup.show_popup(title, body, kind, btns)
        self.toast.raise_()


class ScaledView(QGraphicsView):
    """Uniformly scales the fixed 1080x1920 canvas into any window, centred, letterboxed."""

    def __init__(self, root):
        super().__init__()
        self.scene_ = QGraphicsScene(self)
        self.proxy = self.scene_.addWidget(root)
        self.setScene(self.scene_)
        self.setSceneRect(0, 0, VW, VH)
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing |
                            QPainter.RenderHint.SmoothPixmapTransform)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setBackgroundBrush(QBrush(QColor(0, 0, 0)))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        s = min(self.viewport().width() / VW, self.viewport().height() / VH)
        self.setTransform(QTransform.fromScale(s, s))
        self.centerOn(VW / 2, VH / 2)

    def wheelEvent(self, e):
        # route wheel to embedded widgets only; never scroll the view itself
        item = self.itemAt(e.position().toPoint())
        if item is not None:
            super().wheelEvent(e)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Financial Odyssey: 18 to 65")
        self.ui = GameUI()
        self.ui.popup.on_close = self._popup_closed
        self.view = ScaledView(self.ui)
        self.setCentralWidget(self.view)
        self.setStyleSheet("QMainWindow { background:#000; }")

        # Initial size: 9:16 window filling ~92% of the screen height (or width if the
        # screen is narrow). Same proportions on every monitor / phone / tablet.
        scr = QGuiApplication.primaryScreen().availableGeometry()
        h = int(scr.height() * 0.92)
        w = int(h * VW / VH)
        if w > scr.width() * 0.96:
            w = int(scr.width() * 0.96)
            h = int(w * VH / VW)
        self.resize(w, h)
        self.move(scr.x() + (scr.width() - w) // 2, scr.y() + (scr.height() - h) // 2)
        self.setMinimumSize(270, 480)

        QShortcut(QKeySequence("F11"), self, self.toggle_fullscreen)
        QShortcut(QKeySequence("Esc"), self, lambda: self.showNormal() if self.isFullScreen() else None)

    def _popup_closed(self):
        self.ui.dash.refresh() if self.ui.game.state in ("main", "event") else None
        self.ui._pump()

    def toggle_fullscreen(self):
        self.showNormal() if self.isFullScreen() else self.showFullScreen()


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName("Financial Odyssey")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
