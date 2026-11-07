"""Headless Monte-Carlo simulator for main.py strategies.

Imports the real LifeGame class (so event/turn logic is exactly the shipped code)
and re-implements the dashboard quick actions exactly as written in main().
"""
import os
import sys
import random
import statistics
from unittest.mock import MagicMock

# Stub pygame entirely: we only need the pure-logic LifeGame class.
_pg = MagicMock()
_pg.display.Info.return_value.current_w = 1080
_pg.display.Info.return_value.current_h = 1920
sys.modules["pygame"] = _pg

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import main as M  # noqa: E402

LifeGame = M.LifeGame
LifeGame.build_event_buttons = lambda self: None  # UI only; avoids MagicMock overhead


# ---- dashboard quick actions from main.py ----
def groceries(g):
    return g.buy_groceries()


def spa(g):
    return g.buy_spa()


def pay_debt(g):
    return g.quick_pay_debt()


def invest(g):
    return g.quick_invest()


def withdraw(g, amount=500):
    return g.quick_withdraw(amount)


def declare_bankruptcy(g):
    return g.declare_bankruptcy()


def score(g):
    return g.final_score()


def valid_actions(g):
    return [act for _, act in g.current_event["options"] if g.option_block_reason(act) is None]


def choose_safe(g, preferred_action):
    """Pick preferred_action if allowed; otherwise fall back to a valid option."""
    if g.option_block_reason(preferred_action) is None:
        return preferred_action
    available = valid_actions(g)
    if available:
        # The last option is typically pass/skip/gamble (always free)
        return available[-1]
    return "pass"


def opt_index(g, action):
    return [a for _, a in g.current_event["options"]].index(action)


# ---------------- strategies ----------------
# Each strategy: event(g) -> action string ; main(g) -> performs quick actions

class Idle:
    """Never touches dashboard, always picks the bottom (3rd) option."""
    name = "Idle (spam bottom option, no upkeep)"

    def event(self, g):
        return g.current_event["options"][-1][1]

    def main(self, g):
        pass


class Hoarder:
    """Keeps health topped with groceries, never invests, pays cash, skips extras."""
    name = "Hoarder (groceries to stay >=50 HP, no investing)"

    def event(self, g):
        t = g.current_event["title"]
        c = g.event_costs
        if t == "Medical Checkup & Care":
            return "skip_med"
        if t == "Stock Market Trend":
            return "pass"
        if t == "Car Maintenance":
            return "fix_car_cash" if g.cash >= c.get("car", 800) else "sell_car"
        if t == "Commuting Without a Car":
            return "buy_car_cash" if g.cash >= c.get("used_car", 3000) else "bus"
        if t == "Luxury Vacation Offer":
            return "vacation_skip"
        if t == "Career Certification":
            return "pass"
        if t == "Debt Consolidation Offer":
            return "pay_debt_now" if g.debt > 0 and g.cash >= c.get("pay", 0) else "pass"
        if t == "Layoff Notice":
            return "layoff_severance"
        return g.current_event["options"][-1][1]

    def main(self, g):
        while g.health < 50 and groceries(g):
            pass
        while g.debt > 0 and pay_debt(g):
            pass


class Responsible:
    """'Intended' play: healthy (>=70 HP), pays cash, takes course w/ cash,
    keeps a cash buffer for emergencies, invests the rest."""
    name = "Responsible (HP>=70, cash buffer, invest surplus)"

    def event(self, g):
        t = g.current_event["title"]
        c = g.event_costs
        if t == "Medical Checkup & Care":
            if g.cash >= c.get("med", 600):
                return "pay_med"
            if g.credit_score >= g.LOAN_MIN_CREDIT and not g.in_collections:
                return "debt_med"
            return "skip_med"
        if t == "Stock Market Trend":
            return "invest_index" if g.cash >= c.get("invest", 1000) + 3000 else "pass"
        if t == "Car Maintenance":
            if g.cash >= c.get("car", 800):
                return "fix_car_cash"
            if g.credit_score >= g.LOAN_MIN_CREDIT and not g.in_collections:
                return "fix_car_loan"
            return "sell_car"
        if t == "Commuting Without a Car":
            if g.cash >= c.get("used_car", 3000):
                return "buy_car_cash"
            if g.credit_score >= g.LOAN_MIN_CREDIT and not g.in_collections:
                return "buy_car_loan"
            return "bus"
        if t == "Luxury Vacation Offer":
            return "vacation_cash" if g.cash >= c.get("vacation", 1500) + 4000 else "vacation_skip"
        if t == "Career Certification":
            if g.courses_taken < g.MAX_COURSES and g.cash >= c.get("course", 1200) + 1500:
                return "course_cash"
            return "pass"
        if t == "Debt Consolidation Offer":
            if g.debt > 0 and g.cash >= c.get("pay", 0):
                return "pay_debt_now"
            if (g.debt > 1500 and g.refi_turns == 0 and g.cash >= c.get("refi_fee", 250)
                    and g.credit_score >= g.REFI_MIN_CREDIT):
                return "refinance"
            return "pass"
        if t == "Layoff Notice":
            return "layoff_severance"
        return g.current_event["options"][-1][1]

    def main(self, g):
        while g.health < 70 and groceries(g):
            pass
        while g.debt > 0 and pay_debt(g):
            pass
        buffer = max(3000, g.living_expense() * 2)
        while g.cash - 500 >= buffer and invest(g):
            pass


class Cheese:
    """Min-max: health floor exploit, sell car, always course (cash/loan), all-in invest."""
    name = "Min-max cheese (0-HP cycling, sell car, course loans, all-in)"

    def event(self, g):
        t = g.current_event["title"]
        c = g.event_costs
        if t == "Medical Checkup & Care":
            return "skip_med"
        if t == "Stock Market Trend":
            return "invest_index" if g.cash >= c.get("invest", 1000) else "pass"
        if t == "Car Maintenance":
            return "sell_car"
        if t == "Commuting Without a Car":
            return "bus"
        if t == "Luxury Vacation Offer":
            return "vacation_skip"
        if t == "Career Certification":
            if g.courses_taken >= g.MAX_COURSES:
                return "pass"
            if g.cash >= c.get("course", 1200):
                return "course_cash"
            if g.credit_score >= g.COURSE_LOAN_MIN_CREDIT and not g.in_collections:
                return "course_loan"
            return "pass"
        if t == "Debt Consolidation Offer":
            return "pay_debt_now" if g.debt > 0 and g.cash >= c.get("pay", 0) else "pass"
        if t == "Layoff Notice":
            return "layoff_severance"
        return g.current_event["options"][-1][1]

    def main(self, g):
        # 0-HP cycling: zero_health_turns kills at 4 strikes.
        # Recover before the fatal 4th strike:
        if g.zero_health_turns >= 3 and g.health <= 0:
            while g.health < 20 and groceries(g):
                pass
        while g.debt > 0 and pay_debt(g):
            pass
        while invest(g):
            pass


class CheeseNoSell(Cheese):
    name = "Min-max cheese WITHOUT selling car"

    def event(self, g):
        t = g.current_event["title"]
        c = g.event_costs
        if t == "Car Maintenance":
            if g.cash >= c.get("car", 800):
                return "fix_car_cash"
            if g.credit_score >= g.LOAN_MIN_CREDIT and not g.in_collections:
                return "fix_car_loan"
            return "sell_car"
        if t == "Commuting Without a Car":
            if g.cash >= c.get("used_car", 3000):
                return "buy_car_cash"
            if g.credit_score >= g.LOAN_MIN_CREDIT and not g.in_collections:
                return "buy_car_loan"
            return "bus"
        return super().event(g)


def run(strategy, seed):
    random.seed(seed)
    g = LifeGame(seed=seed)
    g.state = "main"
    turns = 0
    credit_max_turn = None
    while g.state != "game_over":
        strategy.main(g)
        if credit_max_turn is None and g.credit_score >= 1000:
            credit_max_turn = turns
        g.next_turn()
        turns += 1
        if g.state == "event":
            act = strategy.event(g)
            act = choose_safe(g, act)
            g.handle_choice(act)
    return dict(
        score=score(g),
        reason=g.death_reason,
        age=g.age_years,
        nw=g.get_net_worth(),
        credit=g.credit_score,
        income=g.quarterly_income(),
        base_income=g.base_income,
        cash=g.cash,
        debt=g.debt,
        investments=g.investments,
        courses=g.courses_taken,
        turns=turns,
        credit_max_turn=credit_max_turn,
    )


def summarize(strategy, n=2000):
    rs = [run(strategy, s) for s in range(n)]
    sc = [r["score"] for r in rs]
    deaths = sum(r["reason"] != "RETIREMENT" for r in rs)
    cm = [r["credit_max_turn"] for r in rs if r["credit_max_turn"] is not None]
    print(f"\n== {strategy.name} ==")
    print(f"  death rate: {deaths/n:.1%}   median age at end: {statistics.median(r['age'] for r in rs)}")
    print(f"  score  mean {statistics.mean(sc):>14,.0f}  median {statistics.median(sc):>14,.0f}"
          f"  min {min(sc):>14,}  max {max(sc):>14,}")
    print(f"  final income/qtr median {statistics.median(r['income'] for r in rs):,.0f}"
          f"   final credit median {statistics.median(r['credit'] for r in rs)}")
    if cm:
        print(f"  credit hits 1000 by turn (median) {statistics.median(cm)}  "
              f"(~age {18 + statistics.median(cm)/4:.1f}) in {len(cm)/n:.0%} of runs")


if __name__ == "__main__":
    for s in [Idle(), Hoarder(), Responsible(), CheeseNoSell(), Cheese()]:
        summarize(s)
