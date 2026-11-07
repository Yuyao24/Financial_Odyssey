"""Difficulty probes: can a player actually lose?"""
import random
import statistics
from collections import Counter
from sim import LifeGame, run, groceries, invest, pay_debt, valid_actions, choose_safe


class Debtor:
    name = "Debtor (always picks loan option, never repays, groceries HP>=50)"
    LOANS = {
        "Medical Checkup & Care": "debt_med",
        "Stock Market Trend": "loan_invest",
        "Car Maintenance": "fix_car_loan",
        "Commuting Without a Car": "buy_car_loan",
        "Luxury Vacation Offer": "vacation_loan",
        "Career Certification": "course_loan",
        "Debt Consolidation Offer": "pass",
        "Layoff Notice": "layoff_gamble",
    }

    def event(self, g):
        pref = self.LOANS.get(g.current_event["title"], "pass")
        return choose_safe(g, pref)

    def main(self, g):
        while g.health < 50 and groceries(g):
            pass


class RandomClicker:
    name = "Random clicker (random valid event option, groceries if HP<30, invests half)"

    def event(self, g):
        opts = valid_actions(g)
        return random.choice(opts) if opts else g.current_event["options"][-1][1]

    def main(self, g):
        if g.health < 30:
            groceries(g)
        if random.random() < 0.5:
            while g.cash > 2000 and invest(g):
                pass


class Forgetful:
    name = "Forgetful (never buys health, otherwise invests all)"

    def event(self, g):
        return g.current_event["options"][-1][1]

    def main(self, g):
        while invest(g):
            pass


if __name__ == "__main__":
    for s in [Debtor(), RandomClicker(), Forgetful()]:
        rs = [run(s, i) for i in range(2000)]
        reasons = Counter(r["reason"] for r in rs)
        print(f"\n{s.name}\n  outcomes {dict(reasons)}  median end age {statistics.median(r['age'] for r in rs)}"
              f"  median score {statistics.median(r['score'] for r in rs):,.0f}")
        dead_irs = [r for r in rs if r["reason"] == "IRS_SEIZURE"]
        if dead_irs:
            print(f"  IRS deaths median age {statistics.median(r['age'] for r in dead_irs)}")
        dead_health = [r for r in rs if r["reason"] == "HEALTH_FAILURE"]
        if dead_health:
            print(f"  Health deaths median age {statistics.median(r['age'] for r in dead_health)}")
