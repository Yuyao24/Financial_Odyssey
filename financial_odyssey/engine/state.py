"""Game state: setup, save/load, per-quarter history, milestones and read-only helpers
(tiers, limits, income, essentials, net worth and scoring)."""

import random

from .config import GameConfig


class GameState(GameConfig):
    """Holds every value that describes a game in progress."""

    def __init__(self, seed=None):
        self.reset(seed)

    # ---------------------------------------------------------------- setup --
    def reset(self, seed=None):
        self.seed = seed if seed is not None else random.randrange(1_000_000)
        self.rng = random.Random(self.seed)

        self.age_years, self.age_months, self.turns_played = 18, 0, 0
        self.cash = self.START_CASH
        self.investments = 0
        self.card: int = 0
        self.loans: int = 0
        self.credit_score = 550
        self.streak = 0
        self.best_streak = 0
        self.happiness = 100
        self.low_credit_turns = 0
        self.zero_happiness_turns = 0
        self.delinquent = False          # a payment was late/missed since the last IRS check

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
        self.current_event: dict | None = None
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
        self.history = []                # per-quarter snapshots for the Insights charts
        self.moments = []                # (turn, "age Qn", text, tone) timeline entries
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
        self.moment("Got your first credit card", "good")
        self.snapshot()

    # -------------------------------------------------------------- history --
    def snapshot(self):
        """One data point per quarter for the Insights charts."""
        self.history.append({
            "t": self.turns_played, "age": self.age_years, "q": self.quarter(),
            "credit": self.credit_score, "nw": self.get_net_worth(), "cash": self.cash,
            "inv": self.investments, "debt": self.card + self.loans + self.overdraft_used(),
            "happy": self.happiness, "income": self.quarterly_income(), "ess": self.essentials_total(),
        })

    def moment(self, text, tone="info"):
        """A notable life event, shown on the Insights timeline and as chart markers."""
        self.moments.append((self.turns_played, f"{self.age_years} Q{self.quarter()}", text, tone))
        if len(self.moments) > 300:
            self.moments.pop(0)

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
            self.moment(f"Achievement: {name}", "gold")

    @staticmethod
    def tier_for(score):
        for t in GameConfig.TIERS:
            if score >= t[0]:
                return t
        return GameConfig.TIERS[-1]

    def tier(self):
        return self.tier_for(self.credit_score)

    def loan_rate(self):
        return self.tier()[2]

    def card_rate(self):
        return self.tier()[3]

    def limit_for(self, tier):
        # card limits grow with your pay, so a carried balance can get genuinely large
        return int((tier[4] + self.limit_bonus) * self.wage_index)

    def card_limit(self):
        return self.limit_for(self.tier())

    def credit_price_factor(self):
        return self.CREDIT_PRICING[self.tier()[1]]

    def card_available(self):
        return max(0, self.card_limit() - self.card)

    def utilization(self):
        return self.card / max(1, self.card_limit())

    def payment_quality(self):
        """How this quarter's payment will be judged if you advance now (None = no bill)."""
        if self.min_due <= 0:
            return None
        paid, due = self.paid_this_qtr, self.min_due
        if paid < due and not (self.card + self.loans == 0 and paid > 0):
            return "late" if paid > 0 else "missing"
        if self.paid_card_this_qtr >= self.stmt_card:
            return "full"                       # statement cleared: lowest possible utilisation
        if self.utilization() > self.HIGH_UTILIZATION:
            return "maxed"
        if paid >= due * 2:
            return "more"
        return "minimum"

    def credit_gain_for(self, quality, score=None, streak=None):
        """Points an on-time payment of this quality earns (before the 5-year history cap)."""
        score = self.credit_score if score is None else score
        streak = self.streak + 1 if streak is None else streak
        if score >= 800:
            band = "very_high"
        elif score >= 700:
            band = "established"
        elif score < self.REBUILD_SCORE:
            band = "rebuild"
        else:
            band = "building"
        gain = self.PAY_GAINS[band][("full", "more", "minimum", "maxed").index(quality)]
        if band == "building" and quality in ("full", "more") and streak >= 4:
            gain += self.STREAK_BONUS
        return gain

    def projected_credit_change(self):
        """(quality, points) if you advanced right now; history cap applied."""
        q = self.payment_quality()
        if q is None:
            return None, 0
        if q == "late":
            return q, -20
        if q == "missing":
            return q, -50
        gain = self.credit_gain_for(q)
        if self.history_capped():
            gain = min(gain, max(0, self.HISTORY_CAP - self.credit_score))
        return q, gain

    def full_payment_gain(self):
        gain = self.credit_gain_for("full")
        if self.history_capped():
            gain = min(gain, max(0, self.HISTORY_CAP - self.credit_score))
        return gain

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
        rent = self.price(self.RENT_BASE + self.rent_adj)
        bills = self.price(self.UTIL_BASE - (0 if self.has_car else self.NO_CAR_SAVING))
        items = [("Rent", rent), ("Groceries", self.price(self.FOOD_BASE)), ("Transport & bills", bills)]
        adj = int(round((rent + bills) * (self.credit_price_factor() - 1)))
        if adj:
            items.append(("Credit discount" if adj < 0 else "Credit premium", adj))
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

    def credit_multiplier(self):
        """Final-score multiplier from credit: 0.50 (Very Poor) up to 2.00 (900+).
        Under 450: 0.50 · 450-599: 0.50 -> 1.00 · 600-699: exactly 1.00 · 700-899: 1.00 -> 2.00 · 900+: 2.00
        """
        score = self.credit_score
        if score >= 900:
            return 2.00
        if score >= 700:
            return 1.00 + (score - 700) / 200.0
        if score >= 600:
            return 1.00
        if score >= 450:
            return 0.50 + 0.50 * (score - 450) / 150.0
        return 0.50

    def raw_score(self):
        """Net worth x credit multiplier (a negative net worth is not multiplied)."""
        nw = self.get_net_worth()
        return int(nw * self.credit_multiplier()) if nw >= 0 else int(nw)

    def death_penalty_amount(self):
        """IRS seizure costs the full IRS penalty; so does burning out while you still have IRS strikes."""
        if self.end_reason == "IRS_SEIZURE":
            return self.IRS_DEATH_PENALTY
        if self.end_reason == "DEPRESSION":
            return self.IRS_DEATH_PENALTY if self.low_credit_turns > 0 else self.DEPRESSION_DEATH_PENALTY
        return 0

    def final_score(self):
        raw = self.raw_score()
        if self.end_reason in ("RETIREMENT", "EARLY_RETIREMENT"):
            return raw
        return int(min(raw, raw * 0.25) - self.death_penalty_amount())

    # ----------------------------------------------------------- shared --
    def _note_debt(self):
        if self.total_debt() > 0:
            self.had_debt = True

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
