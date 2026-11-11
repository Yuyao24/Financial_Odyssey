"""Fast checks of the game rules. Pure engine, so no display or PyQt6 window is needed.

Run with:  python -m unittest discover tests
"""
import json
import unittest

from financial_odyssey.engine import LifeGame


def play(game, quarters, pay=True):
    """Advance `quarters` turns, always taking the first affordable event option."""
    for _ in range(quarters):
        while game.state == "event" and game.current_event:
            n = len(game.current_event["options"])
            if not any(game.choose_option(i)[0] for i in range(n)):
                break
        if game.state != "main":
            return
        if pay:
            game.pay_all()
        if game.happiness < 50:
            game.buy_happiness()
        game.next_turn()


class TestNewGame(unittest.TestCase):
    def test_starting_values(self):
        g = LifeGame(seed=1)
        g.start()
        self.assertEqual(g.state, "main")
        self.assertEqual((g.age_years, g.credit_score, g.cash), (18, 550, g.START_CASH))
        self.assertEqual(g.tier()[1], "Poor")

    def test_quarter_advances_age_and_shows_event(self):
        g = LifeGame(seed=1)
        g.start()
        g.next_turn()
        self.assertEqual((g.age_years, g.age_months, g.turns_played), (18, 3, 1))
        self.assertEqual(g.state, "event")


class TestCredit(unittest.TestCase):
    def test_missed_payment_costs_50(self):
        g = LifeGame(seed=2)
        g.start()
        g.min_due = 100
        g.card = 1000
        before = g.credit_score
        g.next_turn()
        self.assertEqual(g.credit_score, before - 50)

    def test_paying_in_full_raises_score(self):
        g = LifeGame(seed=3)
        g.start()
        g.card = g.stmt_card = 500
        g.min_due = 50
        g.cash = 2000
        before = g.credit_score
        self.assertTrue(g.pay_card_all()[0])
        g.next_turn()
        self.assertGreater(g.credit_score, before)

    def test_score_capped_at_700_for_first_five_years(self):
        g = LifeGame(seed=4)
        g.start()
        g.credit_score = 699
        g.card = g.stmt_card = 500
        g.min_due = 50
        g.cash = 2000
        g.pay_card_all()
        g.next_turn()
        self.assertLessEqual(g.credit_score, g.HISTORY_CAP)

    def test_loans_need_450(self):
        g = LifeGame(seed=5)
        g.start()
        g.credit_score = 400
        self.assertFalse(g.take_loan(1000)[0])


class TestMoney(unittest.TestCase):
    def test_invest_and_withdraw_fee(self):
        g = LifeGame(seed=6)
        g.start()
        g.cash = 5000
        self.assertTrue(g.invest(1000)[0])
        self.assertEqual((g.cash, g.investments), (4000, 1000))
        g.withdraw(1000)
        self.assertEqual(g.cash, 4000 + 1000 - int(1000 * g.EARLY_WITHDRAW_PENALTY))

    def test_cannot_invest_more_than_cash(self):
        g = LifeGame(seed=7)
        g.start()
        self.assertFalse(g.invest(g.cash + 1)[0])

    def test_pay_off_card_leaves_loans(self):
        g = LifeGame(seed=8)
        g.start()
        g.cash, g.card, g.loans = 5000, 300, 1000
        g.pay_card_all()
        self.assertEqual((g.card, g.loans), (0, 1000))


class TestSaveLoad(unittest.TestCase):
    def test_round_trip_through_json_continues_identically(self):
        a = LifeGame(seed=9)
        a.start()
        play(a, 10)
        b = LifeGame.from_dict(json.loads(json.dumps(a.to_dict())))
        play(a, 10)
        play(b, 10)
        self.assertEqual(json.dumps(a.to_dict(), sort_keys=True), json.dumps(b.to_dict(), sort_keys=True))


class TestWholeGames(unittest.TestCase):
    def test_same_seed_same_game(self):
        a, b = LifeGame(seed=10), LifeGame(seed=10)
        for g in (a, b):
            g.start()
            play(g, 40)
        self.assertEqual(a.get_net_worth(), b.get_net_worth())

    def test_ignoring_happiness_and_bills_ends_the_game(self):
        g = LifeGame(seed=11)
        g.start()
        for _ in range(200):
            while g.state == "event" and g.current_event:
                n = len(g.current_event["options"])
                if not any(g.choose_option(i)[0] for i in reversed(range(n))):
                    break
            if g.state != "main":
                break
            g.next_turn()
        self.assertEqual(g.state, "game_over")
        self.assertIn(g.end_reason, ("DEPRESSION", "IRS_SEIZURE"))
        self.assertLess(g.final_score(), 0)


if __name__ == "__main__":
    unittest.main()
