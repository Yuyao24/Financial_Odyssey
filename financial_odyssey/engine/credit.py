"""Credit score changes and the credit-drop warning popups."""

from ..formatting import esc, money
from .state import GameState


class CreditSystem(GameState):
    """Applies payment results to the credit score."""

    # --------------------------------------------------------- credit score --
    def _credit(self, status, reason, quality="full"):
        before = self.credit_score
        if status == "missing":
            delta = -50
            self.streak = 0
            self.stats["missed"] += 1
            self.delinquent = True
        elif status == "late":
            delta = -20
            self.streak = 0
            self.stats["late"] += 1
            self.delinquent = True
        else:  # on_time
            self.streak += 1
            self.best_streak = max(self.best_streak, self.streak)
            self.stats["on_time"] += 1
            delta = self.credit_gain_for(quality, before, self.streak)
            if before >= 800 and delta:
                delta = self.rng.choice([0, 1])            # very high score: +0 or +1 per payment
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
            self.moment(f"Credit rose to {t_after[1]} ({new})", "good")
        elif t_after[0] < t_before[0]:
            self.moment(f"Credit fell to {t_after[1]} ({new})", "bad")

    @classmethod
    def band_of(cls, score):
        return sum(score >= b for b in cls.CREDIT_BANDS)

    def _credit_drop_popup(self, before):
        after = self.credit_score
        if after >= before:
            return
        if self.band_of(after) >= self.band_of(before):
            # still in the same band: a quick heads-up instead of the full explainer
            self.toasts.append((f"Credit score {after - before:+d} → {after}. Pay the minimum every quarter "
                                f"to rebuild it.", "bad"))
            return
        drops = [r for r in self.credit_reasons if r[0] < 0]
        tb, ta = self.tier_for(before), self.tier()
        best = self.TIERS[0]
        items = "".join(f"<li>{esc(r)} <b style='color:#F87171'>({d:+d})</b></li>" for d, r, _ in drops)
        tier_html = ""
        if ta[0] < tb[0]:
            tier_html = (f"<p style='color:#FBBF24'><b>Tier dropped: {tb[1]} → {ta[1]}.</b> "
                         f"Loan rate {tb[2]:.2%} → {ta[2]:.2%}/qtr, card rate {tb[3]:.2%} → {ta[3]:.2%}/qtr, "
                         f"card limit {money(self.limit_for(tb))} → {money(self.limit_for(ta))}, rent & bills "
                         f"{(self.CREDIT_PRICING[tb[1]] - 1) * 100:+.0f}% → {(self.CREDIT_PRICING[ta[1]] - 1) * 100:+.0f}%.</p>")
        extra = int(10000 * (ta[2] - best[2]))
        irs = ""
        if self.credit_score < self.IRS_SCORE:
            irs = (f" <b style='color:#F87171'>You are below 300 now. Every quarter you're under 300 AND miss a "
                   f"payment is a strike ({self.low_credit_turns}/{self.IRS_TURNS} so far). Pay on time and "
                   f"strikes stop — you can always recover.</b>")
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
            f"<li><b>Pricier life:</b> landlords and insurers charge you "
            f"{(self.CREDIT_PRICING[ta[1]] - 1) * 100:+.0f}% on rent & bills at this tier "
            f"({(self.CREDIT_PRICING['Excellent'] - 1) * 100:+.0f}% at Excellent).</li>"
            f"<li><b>IRS seizure</b> after 8 quarters under 300 while still missing payments — game over.{irs}</li>"
            "<li><b>Lower final score multiplier</b> (0.50 for Very Poor up to 2.00 for Excellent 900+).</li></ul>"
            "<p><b style='color:#4ADE80'>How to rebuild it</b></p><ul>"
            "<li>Pay at least the <b>minimum due</b> shown on the dashboard every quarter <i>before</i> "
            "pressing Advance — and pay the <b>full statement</b> whenever you can: it's worth far more than "
            "the minimum, and a card kept over 90% full earns nothing.</li>"
            "<li>Paying something but less than the minimum is still <b>late (-20)</b>; paying nothing is "
            "<b>missed (-50)</b>.</li>"
            "<li>Keep an emergency cash cushion so surprise bills never go to collections (-50).</li>"
            "<li>Using your card is fine — <b>only unpaid debt lowers your score</b>. Charging and paying on "
            "time is how you climb.</li></ul>"
        )
        self.popups.append({"title": f"Your credit fell to {ta[1]}" if ta[0] < tb[0] else
                            "Your credit is in the danger zone", "body": body, "kind": "warning", "guide": True})
