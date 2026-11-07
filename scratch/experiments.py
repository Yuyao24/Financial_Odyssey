"""Extra experiments: luck vs skill, value of individual exploits."""
import random
import statistics
from sim import (LifeGame, Cheese, Responsible, run, score, groceries, spa, invest, pay_debt, choose_safe)


class CheeseNoCourse(Cheese):
    name = "Cheese but never take course"

    def event(self, g):
        a = super().event(g)
        return "pass" if a.startswith("course") else a


class CheeseHealthy(Cheese):
    name = "Cheese but keep HP>=50 (no 0-HP cycling)"

    def main(self, g):
        while g.health < 50 and groceries(g):
            pass
        while g.debt > 0 and pay_debt(g):
            pass
        while invest(g):
            pass


class CheeseSpa(Cheese):
    name = "Cheese but keep HP>=50 using Spa only"

    def main(self, g):
        while g.health < 50 and spa(g):
            pass
        while g.debt > 0 and pay_debt(g):
            pass
        while invest(g):
            pass


def courses_and_score(strategy, n=2000):
    rows = []
    for s in range(n):
        random.seed(s)
        g = LifeGame(seed=s)
        g.state = "main"
        sells = 0
        while g.state != "game_over":
            strategy.main(g)
            g.next_turn()
            if g.state == "event":
                a = strategy.event(g)
                a = choose_safe(g, a)
                if a == "sell_car":
                    sells += 1
                g.handle_choice(a)
        rows.append((g.courses_taken, sells, score(g)))
    return rows


def pearson(xs, ys):
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = (sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys)) ** 0.5
    return num / den if den != 0 else 0.0


if __name__ == "__main__":
    n = 2000
    for s in [Cheese(), CheeseHealthy(), CheeseSpa(), CheeseNoCourse()]:
        sc = [run(s, i)["score"] for i in range(n)]
        print(f"{s.name:<45} median {statistics.median(sc):>13,.0f}  mean {statistics.mean(sc):>13,.0f}")

    rows = courses_and_score(Cheese(), n)
    c = [r[0] for r in rows]
    sc = [r[2] for r in rows]
    print(f"\nCheese: courses taken min {min(c)} median {statistics.median(c)} max {max(c)} (cap is {LifeGame.MAX_COURSES})")
    print(f"Car sales per run median {statistics.median(r[1] for r in rows)}")
    print(f"Pearson r(courses, score) = {pearson(c, sc):.2f}")
    lo = [r[2] for r in rows if r[0] <= 2]
    hi = [r[2] for r in rows if r[0] >= 5]
    if lo:
        print(f"Median score with <=2 courses: {statistics.median(lo):,.0f} (n={len(lo)})")
    if hi:
        print(f"Median score with >=5 courses: {statistics.median(hi):,.0f} (n={len(hi)})")

    # Pure-RNG investment spread: identical $1000 lump sum held 47 years (188 quarters)
    # Market mechanics matching main.py: normal return [-0.05, +0.10], crash chance 1/30 with loss in [0.20, 0.35]
    finals = []
    for s in range(n):
        rng = random.Random(s)
        v = 1000
        for _ in range(188):
            if rng.random() < LifeGame.CRASH_CHANCE:
                growth = -rng.uniform(*LifeGame.CRASH_RANGE)
            else:
                growth = rng.uniform(*LifeGame.INVEST_RANGE)
            v = max(0, v + int(v * growth))
        finals.append(v)
    finals.sort()
    print(f"\n$1,000 held 188 qtrs (with market crashes): p5 ${finals[n//20]:,}  median ${finals[n//2]:,}  p95 ${finals[-n//20]:,}")

    # Course economics in main.py
    print(f"\nCourse 1: ${LifeGame.COURSE_BASE_COST:,} -> +${LifeGame.COURSE_BASE_BONUS:,}/qtr pay, +${int(LifeGame.COURSE_BASE_BONUS * LifeGame.LIFESTYLE_CREEP):,}/qtr expenses.")
    net_gain = LifeGame.COURSE_BASE_BONUS * (1 - LifeGame.LIFESTYLE_CREEP)
    print(f"Net quarterly gain: +${net_gain:,.0f}/qtr. Payback in {LifeGame.COURSE_BASE_COST / net_gain:.1f} quarters.")
