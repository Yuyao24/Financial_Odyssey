"""The full game: what happens when you sleep (the quarterly turn) and the Credit 101 guide."""

from ..formatting import money
from .daily import DailyLife


class LifeGame(DailyLife):
    """A complete game from age 18 to 65.

    Built up in layers (each file adds one): GameConfig -> GameState -> CreditSystem -> Banking
    -> MoneyMoves -> LifeEvents -> DailyLife -> LifeGame."""

    def next_turn(self):
        if self.state != "main":
            return
        start_score = self.credit_score
        log_mark = self.log_count
        self.credit_reasons = []
        self._sleep(start_score)
        self.night_report = self.log[-(self.log_count - log_mark):] if self.log_count > log_mark else []
        if self.state == "main":
            self._trigger_event()

    def _sleep(self, start_score):
        self._evaluate_payments()
        self._charge_interest()
        self._end_quarter_life()

        self.turns_played += 1
        self.age_months += 3
        if self.age_months >= 12:
            self.age_years += 1
            self.age_months = 0

        if self.age_years >= 65:
            self.state = "game_over"
            self.end_reason = "RETIREMENT"
            self.unlock("golden")
            self.moment("Retired at 65", "good")
            self.snapshot()
            return

        self.price_index *= 1 + self.INFLATION_QTR
        self.wage_index *= 1 + self.RAISE_QTR

        if self.layoff_turns > 0:
            self.layoff_turns -= 1
            if self.layoff_turns == 0:
                self.layoff_mult = 1.0
                self.add_log("Back on full salary from this quarter!", "good")

        ess = self.essentials_total()
        on_card = self._forced_payment(ess, "Rent & bills")
        self.add_log(f"Compulsory rent & bills -{money(ess)}" +
                     (f" ({money(on_card)} on card)" if on_card else ""), "info")

        decay = self.happiness_decay()
        self.happiness = max(0, self.happiness - decay)

        if self.investments > 0:
            if self.rng.random() < self.CRASH_CHANCE:
                change = -int(self.investments * self.rng.uniform(*self.CRASH_RANGE))
                self.investments = max(0, self.investments + change)
                self.add_log(f"MARKET CRASH! Investments fell {money(-change)}", "bad")
                self.moment(f"Market crash: investments −{money(-change)}", "bad")
                self.unlock("storm")
            else:
                change = int(self.investments * self.rng.uniform(*self.INVEST_RANGE))
                self.investments = max(0, self.investments + change)
                self.add_log(f"Investments {'grew' if change >= 0 else 'fell'} {money(abs(change))}",
                             "invest" if change >= 0 else "bad")

        self._post_statement()
        self._reset_quarter_life()
        self._milestones()
        self.snapshot()

        if self.happiness <= 0:
            self.zero_happiness_turns += 1
            if self.zero_happiness_turns >= self.DEPRESSION_TURNS:
                self.state = "game_over"
                self.end_reason = "DEPRESSION"
                return
            self.add_log(f"Happiness is 0! Depression warning {self.zero_happiness_turns}/{self.DEPRESSION_TURNS}", "bad")
        elif self.happiness >= self.HAPPY_RECOVER:
            if self.zero_happiness_turns:
                self.zero_happiness_turns -= 1          # recovery is gradual, one quarter at a time
                self.add_log(f"Recovering from burnout ({self.zero_happiness_turns}/{self.DEPRESSION_TURNS} warnings left)", "good")
        elif self.zero_happiness_turns:
            self.add_log(f"Still burnt out — happiness must reach {self.HAPPY_RECOVER} to recover "
                         f"({self.zero_happiness_turns}/{self.DEPRESSION_TURNS})", "warn")

        if self.credit_score < self.IRS_SCORE:
            if self.delinquent:
                self.low_credit_turns += 1
                if self.low_credit_turns >= self.IRS_TURNS:
                    self.state = "game_over"
                    self.end_reason = "IRS_SEIZURE"
                    return
                self.add_log(f"Under 300 and still missing payments: IRS strike {self.low_credit_turns}/{self.IRS_TURNS}", "bad")
            elif self.low_credit_turns:
                self.low_credit_turns -= 1
                self.add_log(f"Paying on time — IRS strikes falling ({self.low_credit_turns}/{self.IRS_TURNS})", "good")
        else:
            self.low_credit_turns = 0
        self.delinquent = False

        self._credit_drop_popup(start_score)

    # ---------------------------------------------------------- the guide --
    def credit_guide_html(self):
        rows = "".join(
            f"<tr><td><b>{n}</b></td><td>{s}+</td><td>{lr:.2%}</td><td>{cr:.2%}</td>"
            f"<td>{money(self.limit_for((s, n, lr, cr, lim, cap)))}</td><td>{money(cap) if cap else 'Denied'}</td>"
            f"<td>{(self.CREDIT_PRICING[n] - 1) * 100:+.0f}%</td></tr>"
            for s, n, lr, cr, lim, cap in self.TIERS)
        return (
            "<p>Your <b>credit score</b> (0 - 1000) is how much lenders trust you. You start at <b>550</b> "
            "with a brand-new credit card.</p>"
            "<p><b style='color:#FACC15'>How the score moves</b> — it only changes when a bill is due:</p><ul>"
            "<li>Each quarter your card and loans post a <b>statement</b> with a <b>minimum payment due</b> "
            "(4% of the card balance, 8% of loans). It's shown in the Bank menu. A small minimum keeps "
            "your score safe — but whatever you don't pay keeps collecting interest.</li>"
            "<li><b style='color:#4ADE80'>On time</b> (paid at least the minimum before advancing) — how much "
            "it helps depends on <b>how much of your card you're still using</b> (utilisation):</li></ul>"
            "<table cellspacing='0' cellpadding='5' width='100%'>"
            "<tr style='color:#8A97B1'><td>Payment</td><td>Under 450</td><td>450-699</td><td>700-799</td><td>800+</td></tr>"
            "<tr><td><b>Paid in full</b> (utilisation low)</td><td>+12</td><td>+7*</td><td>+3</td><td>+0/+1</td></tr>"
            "<tr><td><b>Paid extra</b> (2× minimum or more)</td><td>+10</td><td>+5*</td><td>+2</td><td>+0</td></tr>"
            "<tr><td><b>Minimum</b>, card 90% used or less</td><td>+5</td><td>+2</td><td>+1</td><td>+0</td></tr>"
            "<tr><td><b>Minimum</b>, card over 90% used</td><td>+0</td><td>+0</td><td>+0</td><td>+0</td></tr>"
            "</table><p style='color:#8A97B1'>* +2 bonus once you're on a 4+ quarter on-time streak.</p><ul>"
            "<li><b style='color:#FBBF24'>Late</b> (paid something, but less than the minimum): -20.</li>"
            "<li><b style='color:#F87171'>Missed</b> (paid nothing) or a bill sent to collections: -50.</li>"
            "<li>Swiping your card or carrying a balance does <b>not</b> lower your score — only unpaid "
            "minimums do. No debt means no statement, and your score simply holds.</li>"
            "<li><b>History cap:</b> you can't pass 700 until you have 5 years (20 quarters) of history.</li></ul>"
            "<p><b style='color:#FACC15'>What your tier gets you</b> (rates are per quarter):</p>"
            "<table cellspacing='0' cellpadding='6' width='100%'>"
            "<tr style='color:#8A97B1'><td>Tier</td><td>Score</td><td>Loan</td><td>Card</td><td>Card limit</td>"
            "<td>Max loans</td><td>Rent & bills</td></tr>"
            f"{rows}</table>"
            "<p><b style='color:#FACC15'>Limits, interest & fees</b></p><ul>"
            "<li><b>Card limit:</b> purchases that would go over your limit are declined. Limits grow as your "
            "pay rises — so does the damage a carried balance can do.</li>"
            "<li><b>Credit-based pricing:</b> landlords, utilities and insurers check your score. Rent and bills "
            "cost 8% less at Excellent and up to 16% more at Very Poor — even if you never borrow a cent.</li>"
            "<li><b>Grace period:</b> pay the full statement balance and you pay no card interest that quarter.</li>"
            f"<li><b>Overdraft:</b> if rent & bills exceed your cash, your bank balance can go down to "
            f"-{money(self.OVERDRAFT_LIMIT)} ({money(self.OVERDRAFT_FEE)} fee + 5% interest per quarter). "
            "Beyond that it goes on your card, and beyond your card limit it goes to <b>collections</b> "
            "(+15% fee and -50 credit).</li>"
            "<li><b>Bank loans</b> are cheaper than cards but need a 450+ score; a 2% fee is added up front.</li>"
            "<li>Payments always go to the highest-interest balance (your card) first.</li></ul>"
            "<p><b style='color:#F87171'>Danger zone</b></p><ul>"
            "<li>Below 450: no loans. Under 300 AND still missing payments for 8 quarters: the IRS seizes your "
            "assets (game over). Pay on time and the strikes count back down — recovery is always possible.</li>"
            "<li>At retirement your net worth is multiplied by your credit multiplier (0.50 for Very Poor, "
            "1.00 for Fair, up to 2.00 for 900+).</li></ul>"
            "<p><b style='color:#4ADE80'>Pro tip:</b> set <i>Pay with: Card</i> in town (or charge rent & bills to the card at home), then pay the "
            "statement in full each quarter. You'll build credit every quarter and never pay card interest.</p>"
        )
