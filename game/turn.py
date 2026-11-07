import random
from game.state import Player, MonthlyStatement
from game.finance import process_end_of_month_finances
from game.credit_score import compute_credit_score

def advance_month(player: Player, rng: random.Random) -> MonthlyStatement:
    # 1. Income
    player.cash += player.income
    income_received = player.income

    # 2. Financial settlement
    bills, interest, fees, on_time = process_end_of_month_finances(player, rng)

    # 3. Update histories & ages
    player.first_account_age_months += 1
    player.payment_history.append(on_time)
    player.hard_inquiries_months_ago = [m + 1 for m in player.hard_inquiries_months_ago]

    # 4. Recompute score
    old_score = player.credit_score
    new_score, breakdown, plain_reasons, jargon_reasons = compute_credit_score(player)
    player.credit_score = new_score

    player.score_history.append(new_score)
    player.net_worth_history.append(player.net_worth)

    # 5. Check solvency
    if player.net_worth < 0:
        player.months_insolvent += 1
    else:
        player.months_insolvent = 0

    player.month += 1

    return MonthlyStatement(
        month=player.month - 1,
        income_received=income_received,
        bills_paid=bills,
        interest_charged=interest,
        late_fees=fees,
        old_score=old_score,
        new_score=new_score,
        score_breakdown=breakdown,
        reasons=plain_reasons,
        jargon_reasons=jargon_reasons,
    )