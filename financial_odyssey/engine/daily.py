"""Daily life in the town: work shifts, groceries, fun, studying and how purchases are paid.

Each quarter has WEEKS_PER_QTR weeks of free time. Working, studying and most fun cost weeks;
unused weeks become rest (a little happiness) when you sleep. Groceries cost no time, but if
you never visit the store you live on takeout, which costs more and feels worse.
"""

import math

from ..formatting import money
from .events import LifeEvents


class DailyLife(LifeEvents):
    """Town actions. Every action returns (ok, reason) like the bank actions do."""

    # ---------------------------------------------------------------- time --
    def weeks_left(self):
        return max(0, self.WEEKS_PER_QTR - self.weeks_used)

    def set_pay_method(self, method):
        if method in ("cash", "card") and method != self.pay_method:
            self.pay_method = method
            self.add_log("Town purchases will now go on your credit card" if method == "card"
                         else "Town purchases will now be paid in cash", "card" if method == "card" else "info")
        return True, ""

    def _spend_block_reason(self, amount):
        if amount <= 0:
            return None
        if self.pay_method == "card":
            if self.card_available() < amount:
                return f"Only {money(self.card_available())} of card credit left. Pay with cash instead"
            return None
        if self.cash < amount:
            return f"Not enough cash ({money(self.cash)}). Work first, or pay with your card"
        return None

    def _spend(self, amount):
        """Pay for a town purchase with the chosen method. Returns a short note for the log."""
        if amount <= 0:
            return ""
        if self.pay_method == "card":
            self.card += amount
            self._note_debt()
            self.unlock("first_swipe")
            return f" ({money(amount)} on card)"
        self.cash -= amount
        return f" (-{money(amount)})"

    # ---------------------------------------------------------------- work --
    def work_pay(self, plan):
        return int(self.quarterly_income() * self.WORK_PLANS[plan][2])

    def work_block_reason(self, plan):
        if self.work_plan:
            return "You've already worked this quarter"
        weeks = self.WORK_PLANS[plan][1]
        if self.weeks_left() < weeks:
            return f"Needs {weeks} free weeks (you have {self.weeks_left()})"
        return None

    def work(self, plan):
        reason = self.work_block_reason(plan)
        if reason:
            return False, reason
        name, weeks, _, happy = self.WORK_PLANS[plan]
        pay = self.work_pay(plan)
        self.work_plan = plan
        self.weeks_used += weeks
        self.cash += pay
        if happy:
            self.happiness = max(0, min(100, self.happiness + happy))
        note = f" at {int(self.layoff_mult * 100)}% pay" if self.layoff_turns else ""
        self.add_log(f"Worked {name.lower()} ({weeks} weeks){note}: paycheck +{money(pay)}"
                     + (f", happiness {happy:+d}" if happy else ""), "good")
        return True, ""

    # ----------------------------------------------------------- groceries --
    def grocery_cost(self, plan):
        return self.price(self.FOOD_BASE * self.GROCERY_PLANS[plan][1])

    def takeout_cost(self):
        return self.price(self.FOOD_BASE * self.TAKEOUT_MULT)

    def grocery_block_reason(self, plan):
        if self.groceries:
            return "Your kitchen is already stocked for this quarter"
        return self._spend_block_reason(self.grocery_cost(plan))

    def buy_groceries(self, plan):
        reason = self.grocery_block_reason(plan)
        if reason:
            return False, reason
        name, _, happy = self.GROCERY_PLANS[plan]
        note = self._spend(self.grocery_cost(plan))
        self.groceries = plan
        if happy:
            self.happiness = max(0, min(100, self.happiness + happy))
        self.add_log(f"Bought groceries: {name.lower()}{note}" + (f", happiness {happy:+d}" if happy else ""),
                     "card" if self.pay_method == "card" else "info")
        return True, ""

    # ------------------------------------------------------------------ fun --
    def fun_cost(self, key):
        return self.price(self.FUN_ACTIVITIES[key][2])

    def fun_block_reason(self, key):
        if key in self.fun_done:
            return "You've already done that this quarter"
        weeks = self.FUN_ACTIVITIES[key][1]
        if self.weeks_left() < weeks:
            return f"Needs {weeks} free week{'s' if weeks > 1 else ''}"
        if self.happiness >= 100:
            return "Happiness is already full"
        return self._spend_block_reason(self.fun_cost(key))

    def do_fun(self, key):
        reason = self.fun_block_reason(key)
        if reason:
            return False, reason
        name, weeks, _, happy = self.FUN_ACTIVITIES[key]
        note = self._spend(self.fun_cost(key))
        self.fun_done.append(key)
        self.weeks_used += weeks
        self.happiness = min(100, self.happiness + happy)
        self.add_log(f"{name}{note}. Happiness +{happy}", "good")
        return True, ""

    # -------------------------------------------------------------- college --
    def course_cost(self):
        return self.price(self.COURSE_BASE_COST * (1.35 ** self.courses_taken))

    def study_block_reason(self, method="pay"):
        if self.courses_taken >= self.MAX_COURSES:
            return "You've earned every certification"
        if self.studied:
            return "One certification per quarter"
        if self.weeks_left() < self.STUDY_WEEKS:
            return f"Needs {self.STUDY_WEEKS} free weeks (you have {self.weeks_left()})"
        if method == "loan":
            return self.loan_block_reason(self.course_cost())
        return self._spend_block_reason(self.course_cost())

    def study(self, method="pay"):
        """method: "pay" (with the chosen cash/card method) or "loan" (a student loan)."""
        reason = self.study_block_reason(method)
        if reason:
            return False, reason
        cost = self.course_cost()
        if method == "loan":
            fee = math.ceil(cost * self.LOAN_ORIGINATION)
            self.loans += cost + fee
            self.stats["fees"] += fee
            self._note_debt()
            note = f" ({money(cost)} student loan)"
        else:
            note = self._spend(cost)
        self.studied = True
        self.weeks_used += self.STUDY_WEEKS
        self._apply_fx({"course": True})
        self.add_log(f"Earned certification {self.courses_taken}/{self.MAX_COURSES}{note}: "
                     f"pay +{money(self.wage(self.COURSE_BONUS))}/qtr", "good")
        return True, ""

    # ------------------------------------------------------------- bedtime --
    def bedtime_checklist(self):
        """What is still undone before sleeping: [(text, ok)]."""
        return [
            ("Worked this quarter" if self.work_plan else "Not worked yet: no paycheck this quarter",
             bool(self.work_plan)),
            ("Groceries bought" if self.groceries else
             f"No groceries: takeout will cost {money(self.takeout_cost())} and {self.TAKEOUT_HAPPY} happiness",
             bool(self.groceries)),
            ("Minimum payment covered" if self.remaining_due() <= 0 else
             f"{money(self.remaining_due())} minimum payment still due", self.remaining_due() <= 0),
        ]

    def _end_quarter_life(self):
        """Called when you sleep: takeout if the kitchen is empty, rest from unused weeks."""
        if not self.work_plan:
            self.add_log("You didn't work this quarter, so there was no paycheck", "bad")
        if not self.groceries:
            cost = self.takeout_cost()
            on_card = self._forced_payment(cost, "Takeout food")
            self.happiness = max(0, self.happiness + self.TAKEOUT_HAPPY)
            self.add_log(f"No groceries: lived on takeout -{money(cost)}" +
                         (f" ({money(on_card)} on card)" if on_card else "") +
                         f", happiness {self.TAKEOUT_HAPPY}", "bad")
        rest = self.weeks_left() * self.REST_HAPPY
        if rest:
            self.happiness = min(100, self.happiness + rest)
            self.add_log(f"Rested {self.weeks_left()} free week{'s' if self.weeks_left() > 1 else ''}: happiness +{rest}",
                         "good")

    def _reset_quarter_life(self):
        self.weeks_used = 0
        self.work_plan = None
        self.groceries = None
        self.fun_done = []
        self.studied = False
