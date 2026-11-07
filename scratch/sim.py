"""Headless Monte-Carlo simulator for main.py strategies.

Imports the real LifeGame class (so event/turn logic is exactly the shipped code)
and re-implements the dashboard quick actions exactly as written in main().
"""
import os, sys, random, statistics
from unittest.mock import MagicMock
# Stub pygame entirely: we only need the pure-logic LifeGame class.
_pg = MagicMock()
_pg.display.Info.return_value.current_w = 1080
_pg.display.Info.return_value.current_h = 1920
sys.modules["pygame"] = _pg
sys.path.insert(0, "/Users/afeefurr/Documents/GitHub/WHACK_Project")
import main as M  # noqa: E402

LifeGame = M.LifeGame
LifeGame.build_event_buttons = lambda self: None  # UI only; avoids MagicMock overhead


# ---- exact copies of dashboard quick actions from main() ----
def groceries(g):
    if g.cash >= 300:
        g.cash -= 300; g.health = min(100, g.health + 20); return True
    return False

def spa(g):
    if g.cash >= 800:
        g.cash -= 800; g.health = min(100, g.health + 50); return True
    return False

def pay_debt(g):
    if g.cash >= 500 and g.debt > 0:
        pay = min(500, g.debt); g.cash -= pay; g.debt -= pay; g.update_credit(20); return True
    return False

def invest(g):
    if g.cash >= 500:
        g.cash -= 500; g.investments += 500; g.update_credit(10); return True
    return False


def score(g):
    return int(g.get_net_worth() + g.credit_score * 50)


def opt_index(g, action):
    return [a for _, a in g.current_event["options"]].index(action)


# ---------------- strategies ----------------
# Each strategy: event(g) -> action string ; main(g) -> performs quick actions

class Idle:
    """Never touches dashboard, always picks the 3rd (bottom) option."""
    name = "Idle (spam bottom option, no upkeep)"
    def event(self, g): return g.current_event["options"][2][1]
    def main(self, g): pass

class Hoarder:
    """Keeps health topped with groceries, never invests, pays cash, skips extras."""
    name = "Hoarder (groceries to stay >=50 HP, no investing)"
    def event(self, g):
        t = g.current_event["title"]
        return {"Medical Checkup & Care": "skip_med", "Stock Market Trend": "pass",
                "Car Maintenance": "fix_car_cash", "Luxury Vacation Offer": "vacation_skip",
                "Career Certification": "pass", "Debt Consolidation Offer": "pay_debt_1000"}[t]
    def main(self, g):
        while g.health < 50 and groceries(g): pass
        while g.debt > 0 and pay_debt(g): pass

class Responsible:
    """'Intended' play: healthy (>=70 HP), pays cash, takes course w/ cash,
    keeps a $3k emergency fund, invests the rest."""
    name = "Responsible (HP>=70, cash buffer $3k, invest surplus)"
    def event(self, g):
        t = g.current_event["title"]
        if t == "Medical Checkup & Care": return "pay_med" if g.cash >= 600 else "skip_med"
        if t == "Stock Market Trend": return "invest_index" if g.cash >= 1000 else "pass"
        if t == "Car Maintenance": return "fix_car_cash"
        if t == "Luxury Vacation Offer": return "vacation_cash" if g.cash >= 4000 else "vacation_skip"
        if t == "Career Certification": return "course_cash" if g.cash >= 1200 else "pass"
        return "pay_debt_1000" if g.debt > 0 else "pass"
    def main(self, g):
        while g.health < 70 and groceries(g): pass
        while g.debt > 0 and pay_debt(g): pass
        while g.cash - 500 >= 3000 and invest(g): pass

class Cheese:
    """Min-max: health floor exploit, sell car, always course (loan), all-in invest."""
    name = "Min-max cheese (0-HP cycling, sell car, course loans, all-in)"
    def event(self, g):
        t = g.current_event["title"]
        if t == "Medical Checkup & Care": return "skip_med"
        if t == "Stock Market Trend": return "invest_index" if g.cash >= 1000 else "pass"
        if t == "Car Maintenance": return "sell_car"
        if t == "Luxury Vacation Offer": return "vacation_skip"
        if t == "Career Certification": return "course_cash" if g.cash >= 1200 else "course_loan"
        return "pay_debt_1000" if g.debt > 0 else "pass"
    def main(self, g):
        # health only needs to be >0 once every 4 checks; next check subtracts 15
        if g.zero_health_turns >= 3 and g.health < 16:
            while g.health < 16 and groceries(g): pass
        while g.debt > 0 and pay_debt(g): pass
        while invest(g): pass

class CheeseNoSell(Cheese):
    name = "Min-max cheese WITHOUT selling car"
    def event(self, g):
        a = super().event(g)
        return "fix_car_cash" if a == "sell_car" and g.cash >= 800 else ("fix_car_loan" if a == "sell_car" else a)


def run(strategy, seed):
    random.seed(seed)
    g = LifeGame()
    g.state = "main"
    turns = 0
    credit_max_turn = None
    while g.state != "game_over":
        strategy.main(g)
        if credit_max_turn is None and g.credit_score >= 1000:
            credit_max_turn = turns
        g.next_turn(); turns += 1
        if g.state == "event":
            g.handle_choice(strategy.event(g))
    return dict(score=score(g), reason=g.death_reason, age=g.age_years, nw=g.get_net_worth(),
                credit=g.credit_score, income=g.base_income, turns=turns,
                credit_max_turn=credit_max_turn)


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
