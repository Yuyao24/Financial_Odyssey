import random
from typing import Optional
from game.state import Player, Loan

SAVINGS_APY = 0.03
LATE_FEE = 12.0

def calculate_amortised_payment(principal: float, apr: float, term_months: int) -> float:
    """Standard amortisation formula: M = P * r(1+r)^n / ((1+r)^n - 1)"""
    if apr == 0:
        return principal / term_months
    r = apr / 12.0
    factor = (1 + r) ** term_months
    return principal * (r * factor) / (factor - 1)

def get_offered_apr(credit_score: int) -> Optional[float]:
    """Maps score tiers to borrowing cost."""
    if credit_score >= 750:
        return 0.06
    elif credit_score >= 650:
        return 0.12
    elif credit_score >= 550:
        return 0.22
    return None  # Declined

def process_end_of_month_finances(player: Player, rng: random.Random) -> tuple[float, float, float, bool]:
    """
    Runs automatic bills, loan payments, savings/investment returns, and card interest.
    Returns: (bills_paid, interest_charged, late_fees, made_all_payments_on_time)
    """
    bills_paid = 0.0
    interest_charged = 0.0
    late_fees = 0.0
    on_time = True

    # 1. Mandatory living costs (rent/groceries)
    player.cash -= player.living_costs
    bills_paid += player.living_costs

    # 2. Installment loans & mortgage auto-debit
    active_loans = []
    for loan in player.loans:
        if player.cash >= loan.monthly_payment:
            player.cash -= loan.monthly_payment
            bills_paid += loan.monthly_payment
            monthly_interest = loan.principal * (loan.apr / 12.0)
            principal_paid = loan.monthly_payment - monthly_interest
            loan.principal = max(0.0, loan.principal - principal_paid)
            loan.term_months_left -= 1
            interest_charged += monthly_interest
        else:
            # Missed loan payment
            on_time = False
            late_fees += LATE_FEE
            loan.principal += LATE_FEE
        
        if loan.is_mortgage:
            loan.property_value *= 1.0025  # ~3% annual appreciation
            
        if loan.term_months_left > 0 and loan.principal > 0.01:
            active_loans.append(loan)
    player.loans = active_loans

    # 3. Credit card settlement check
    if player.card.paid_this_month < player.card.min_payment_due - 0.01:
        on_time = False
        late_fees += LATE_FEE
        player.card.balance += LATE_FEE

    # Charge card interest if statement balance wasn't cleared in full
    if player.card.paid_this_month < player.card.statement_balance - 0.01:
        card_interest = player.card.balance * (player.card.apr / 12.0)
        player.card.balance += card_interest
        interest_charged += card_interest

    # Roll card statement for next month
    player.card.statement_balance = player.card.balance
    est_next_interest = player.card.balance * (player.card.apr / 12.0)
    if player.card.balance > 0:
        player.card.min_payment_due = min(
            player.card.balance,
            max(25.0, 0.02 * player.card.balance + est_next_interest)
        )
    else:
        player.card.min_payment_due = 0.0
    player.card.paid_this_month = 0.0

    # 4. Savings & Investment compounding
    player.savings *= (1.0 + SAVINGS_APY / 12.0)
    if player.investments > 0:
        monthly_return = rng.gauss(0.006, 0.04)
        player.investments = max(0.0, player.investments * (1.0 + monthly_return))

    # 5. Overdraft protection check (if cash went negative from rent)
    if player.cash < 0:
        shortfall = abs(player.cash)
        player.cash = 0.0
        player.card.balance += shortfall  # Forced onto card

    return bills_paid, interest_charged, late_fees, on_time