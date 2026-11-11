"""Player money moves: invest, withdraw, borrow, pay debt, retire early."""

import math

from ..formatting import money
from .banking import Banking


class MoneyMoves(Banking):
    """Every banking action the player can take from the Bank and Invest menus."""

    # --------------------------------------------------------- money moves --
    def invest(self, amount):
        if amount <= 0:
            return False, "Choose an amount above $0"
        if self.cash < amount:
            return False, f"Not enough cash (you have {money(self.cash)})"
        self.cash -= amount
        self.investments += amount
        self.add_log(f"Invested {money(amount)} in the stock market", "invest")
        self.unlock("investor")
        return True, ""

    def withdraw(self, amount):
        if self.investments <= 0:
            return False, "You have no investments"
        amt = min(amount, self.investments)
        if amt <= 0:
            return False, "Choose an amount above $0"
        fee = int(amt * self.withdraw_fee_rate())
        self.investments -= amt
        self.cash += amt - fee
        self.stats["fees"] += fee
        msg = f"Withdrew {money(amt - fee)} from investments" + (f" (early-withdrawal fee {money(fee)})" if fee else "")
        self.add_log(msg, "warn" if fee else "invest")
        return True, ""

    def loan_block_reason(self, amount):
        if self.loan_capacity() <= 0:
            return f"Loans need a {self.LOAN_MIN_SCORE}+ credit score"
        if amount > self.loan_room():
            return f"Loan limit reached ({money(self.loan_room())} left)"
        return None

    def take_loan(self, amount):
        if amount <= 0:
            return False, "Choose an amount above $0"
        reason = self.loan_block_reason(amount)
        if reason:
            self.add_log(f"Loan of {money(amount)} denied: {reason}", "bad")
            return False, reason
        fee = math.ceil(amount * self.LOAN_ORIGINATION)
        self.loans += amount + fee
        self.cash += amount
        self.stats["fees"] += fee
        self._note_debt()
        self.add_log(f"Bank loan of {money(amount)} at {self.loan_rate():.2%}/qtr (+{money(fee)} fee)", "warn")
        return True, ""

    def _apply_payment(self, pay):
        to_card = min(pay, self.card)
        self.card -= to_card
        to_loans = pay - to_card
        self.loans -= to_loans
        self.cash -= pay
        self.paid_this_qtr += pay
        self.paid_card_this_qtr += to_card
        if self.card + self.loans == 0 and self.had_debt and self.cash >= 0:
            self.unlock("debt_free")
        return to_card, to_loans

    def pay_debt(self, amount):
        owed = self.card + self.loans
        if owed <= 0:
            return False, "You have no card or loan debt"
        if self.cash <= 0:
            return False, "No cash available to pay with"
        pay = min(amount, self.cash, owed)
        if pay <= 0:
            return False, "Choose an amount above $0"
        to_card, to_loans = self._apply_payment(pay)
        parts = []
        if to_card:
            parts.append(f"card {money(to_card)}")
        if to_loans:
            parts.append(f"loans {money(to_loans)}")
        self.add_log(f"Paid {money(pay)} toward debt ({', '.join(parts)})", "good")
        return True, ""

    def pay_minimum(self):
        r = self.remaining_due()
        if r <= 0:
            return False, "This quarter's minimum is already covered"
        return self.pay_debt(r)

    def pay_all(self):
        return self.pay_debt(self.card + self.loans)

    def pay_card_all(self):
        """Pay off the credit card balance only (loans are left on their own schedule)."""
        if self.card <= 0:
            return False, "You have no credit card debt"
        if self.cash <= 0:
            return False, "No cash available to pay with"
        pay = min(self.card, self.cash)
        self.card -= pay
        self.cash -= pay
        self.paid_this_qtr += pay
        self.paid_card_this_qtr += pay
        if self.card + self.loans == 0 and self.had_debt and self.cash >= 0:
            self.unlock("debt_free")
        self.add_log(f"Paid off {money(pay)} of credit card debt", "good")
        return True, ""

    def retire_early(self):
        if not self.can_retire_early():
            return False, "Net worth must be at least $1,000,000"
        self.state = "game_over"
        self.end_reason = "EARLY_RETIREMENT"
        return True, ""
