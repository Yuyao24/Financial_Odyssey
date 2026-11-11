"""Quarterly banking: judging payments, interest, overdraft, collections and statements."""

import math

from ..formatting import money
from .credit import CreditSystem


class Banking(CreditSystem):
    """What the bank does to your accounts at the end of each quarter."""

    # ----------------------------------------------------------- quarter ---
    def _evaluate_payments(self):
        if self.min_due <= 0:
            return
        paid, due = self.paid_this_qtr, self.min_due
        q = self.payment_quality()
        if q in ("full", "more", "minimum", "maxed"):
            self._credit("on_time", f"On-time payment, {self.QUALITY_LABEL[q]} ({money(paid)} paid, "
                                    f"{money(due)} minimum, card {self.utilization():.0%} used)", quality=q)
        elif paid > 0:
            self._credit("late", f"Late payment: paid only {money(paid)} of the {money(due)} minimum")
        else:
            self._credit("missing", f"Missed payment: $0 paid of the {money(due)} minimum")

    def _charge_interest(self):
        if self.card > 0 and self.stmt_card > 0 and self.paid_card_this_qtr < self.stmt_card:
            i = math.ceil(self.card * self.card_rate())
            self.card += i
            self.stats["interest"] += i
            self.add_log(f"Card interest +{money(i)} ({self.card_rate():.2%}/qtr) — pay the full statement to avoid it", "bad")
        elif self.stmt_card > 0:
            self.add_log("Statement paid in full — no card interest this quarter (grace period)", "good")
        if self.loans > 0:
            i = math.ceil(self.loans * self.loan_rate())
            self.loans += i
            self.stats["interest"] += i
            self.add_log(f"Loan interest +{money(i)} ({self.loan_rate():.2%}/qtr)", "bad")
        if self.cash < 0:
            i = math.ceil(-self.cash * self.OVERDRAFT_RATE) + self.OVERDRAFT_FEE
            self.cash -= i
            self.stats["fees"] += i
            self.add_log(f"Overdraft fee & interest -{money(i)}", "bad")
        if self.card > self.card_limit():
            self.card += self.OVER_LIMIT_FEE
            self.stats["fees"] += self.OVER_LIMIT_FEE
            self.add_log(f"Card is over its {money(self.card_limit())} limit: {money(self.OVER_LIMIT_FEE)} fee", "bad")

    def _collections(self, amount, label):
        fee = math.ceil(amount * self.COLLECTIONS_FEE)
        self.loans += amount + fee
        self.stats["fees"] += fee
        self._note_debt()
        self._credit("missing", f"{label}: {money(amount)} unpaid and sent to collections (+{money(fee)} fee)")
        self.moment(f"{label} sent to collections", "bad")

    def _forced_payment(self, amount, label):
        """Compulsory costs: (card if autopay) -> cash -> overdraft -> card -> collections."""
        remaining = amount
        used_card = 0
        if self.essentials_on_card:
            use = min(remaining, self.card_available())
            self.card += use
            used_card += use
            remaining -= use
        use = min(remaining, max(0, self.cash))
        self.cash -= use
        remaining -= use
        if remaining > 0:
            room = self.OVERDRAFT_LIMIT - self.overdraft_used()
            use = min(remaining, max(0, room))
            if use:
                self.cash -= use
                remaining -= use
                self.add_log(f"Not enough cash for {label.lower()} — {money(use)} went into overdraft", "bad")
        if remaining > 0:
            use = min(remaining, self.card_available())
            if use:
                self.card += use
                used_card += use
                remaining -= use
                self.add_log(f"Overdraft maxed — {money(use)} charged to your card", "warn")
        if used_card:
            self.unlock("first_swipe")
        if remaining > 0:
            self._collections(remaining, label)
        self._note_debt()
        return used_card

    def _post_statement(self):
        card_due = 0
        if self.card > 0:
            card_due = min(self.card, max(self.price(self.MIN_PAYMENT_FLOOR), math.ceil(self.card * self.CARD_MIN_PCT)))
        loan_due = 0
        if self.loans > 0:
            loan_due = min(self.loans, max(self.price(self.MIN_PAYMENT_FLOOR), math.ceil(self.loans * self.LOAN_MIN_PCT)))
        self.min_due = card_due + loan_due
        self.stmt_card = self.card
        self.paid_this_qtr = 0
        self.paid_card_this_qtr = 0
        if self.min_due:
            self.add_log(f"New statement: minimum payment {money(self.min_due)} due before next quarter", "warn")
