"""Extra experiments: luck vs skill, value of individual exploits."""
import random, statistics
from sim import (LifeGame, Cheese, Responsible, run, score, groceries, invest, pay_debt)


class CheeseNoCourse(Cheese):
    name = "Cheese but never take course"
    def event(self, g):
        a = super().event(g)
        return "pass" if a.startswith("course") else a


class CheeseHealthy(Cheese):
    name = "Cheese but keep HP>=50 (no 0-HP cycling)"
    def main(self, g):
        while g.health < 50 and groceries(g): pass
        while g.debt > 0 and pay_debt(g): pass
        while invest(g): pass


class CheeseSpa(Cheese):
    name = "Cheese but keep HP>=50 using Spa only"
    def main(self, g):
        from sim import spa
        while g.health < 50 and spa(g): pass
        while g.debt > 0 and pay_debt(g): pass
        while invest(g): pass


def courses_and_score(strategy, n=2000):
    rows = []
    for s in range(n):
        random.seed(s)
        g = LifeGame(); g.state = "main"; courses = 0; sells = 0
        while g.state != "game_over":
            strategy.main(g); g.next_turn()
            if g.state == "event":
                a = strategy.event(g)
                courses += a.startswith("course"); sells += a == "sell_car"
                g.handle_choice(a)
        rows.append((courses, sells, score(g)))
    return rows


def pearson(xs, ys):
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = (sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys)) ** 0.5
    return num / den


if __name__ == "__main__":
    n = 2000
    for s in [Cheese(), CheeseHealthy(), CheeseSpa(), CheeseNoCourse()]:
        sc = [run(s, i)["score"] for i in range(n)]
        print(f"{s.name:<45} median {statistics.median(sc):>13,.0f}  mean {statistics.mean(sc):>13,.0f}")

    rows = courses_and_score(Cheese(), n)
    c = [r[0] for r in rows]; sc = [r[2] for r in rows]
    print(f"\nCheese: courses taken min {min(c)} median {statistics.median(c)} max {max(c)}")
    print(f"Car sales per run median {statistics.median(r[1] for r in rows)} -> ~${statistics.median(r[1] for r in rows)*1200:,.0f} free cash")
    print(f"Pearson r(courses, score) = {pearson(c, sc):.2f}")
    lo = [r[2] for r in rows if r[0] <= 25]; hi = [r[2] for r in rows if r[0] >= 37]
    print(f"Median score with <=25 courses: {statistics.median(lo):,.0f} (n={len(lo)});"
          f"  >=37 courses: {statistics.median(hi):,.0f} (n={len(hi)})")

    # Pure-RNG investment spread: identical $1000 lump sum held 47 years
    finals = []
    for s in range(n):
        random.seed(s); v = 1000
        for _ in range(187):
            v = max(0, v + int(v * random.uniform(-0.04, 0.08)))
        finals.append(v)
    finals.sort()
    print(f"\n$1,000 held 187 qtrs: p5 {finals[n//20]:,}  median {finals[n//2]:,}  p95 {finals[-n//20]:,}")

    # Course ROI
    print("\nCourse: $1,200 -> +$500/qtr. Payback in 2.4 qtrs; with ~8.2% APR investing,"
          " one course taken at 18 is worth ~"
          f"${500 * ((1.02 ** 187 - 1) / 0.02):,.0f} by 65 (deterministic mean growth).")
