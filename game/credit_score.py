from game.state import Player

def compute_credit_score(player: Player):
    plain_reasons = []
    jargon_reasons = []

    # 1. Payment History (35%)
    recent_12 = player.payment_history[-12:]
    missed_recent = recent_12.count(False)
    if not player.payment_history[-1]:
        plain_reasons.append("Missed a minimum payment this month, which caused a sharp drop.")
        jargon_reasons.append("Delinquent payment recorded this cycle (-35% component).")
    elif missed_recent == 0:
        plain_reasons.append("Paid all accounts on time, keeping a perfect track record.")
        jargon_reasons.append("100% on-time payment history maintained.")
    payment_score = max(0.0, 1.0 - (missed_recent * 0.28))

    # 2. Utilisation (30%)
    util = player.card.utilisation
    if util <= 0.10:
        util_score = 1.0
        plain_reasons.append(f"Used only {util:.0%} of credit limit. Staying under 10% maximises your rating.")
        jargon_reasons.append(f"Optimal revolving utilisation at {util:.0%}.")
    elif util >= 0.90:
        util_score = 0.0
        plain_reasons.append(f"Card is almost maxed out ({util:.0%}), penalising your score.")
        jargon_reasons.append(f"Severe utilisation penalty at {util:.0%}.")
    else:
        util_score = 1.0 - ((util - 0.10) / 0.80)
        if util > 0.30:
            plain_reasons.append(f"Utilisation is {util:.0%}. Reducing below 30% will recover lost points.")
            jargon_reasons.append(f"High utilisation ({util:.0%}); target <30% to improve score.")

    # 3. Account Age (15%)
    age_score = min(1.0, player.first_account_age_months / 72.0)

    # 4. Credit Mix (10%)
    has_installment = any(not l.is_mortgage for l in player.loans)
    has_mortgage = any(l.is_mortgage for l in player.loans)
    mix_score = 0.4 + (0.3 if has_installment else 0.0) + (0.3 if has_mortgage else 0.0)

    # 5. New Credit (10%)
    active_inquiries = [m for m in player.hard_inquiries_months_ago if m <= 12]
    new_credit_score = max(0.0, 1.0 - (len(active_inquiries) * 0.25))
    if 0 in active_inquiries:
        plain_reasons.append("Applying for new credit triggered a temporary hard-search dip.")
        jargon_reasons.append("Hard inquiry registered on credit file.")

    weighted_sum = (
        0.35 * payment_score +
        0.30 * util_score +
        0.15 * age_score +
        0.10 * mix_score +
        0.10 * new_credit_score
    )
    final_score = int(round(300 + 550 * weighted_sum))

    breakdown = {
        "payment_history": round(payment_score, 2),
        "utilisation": round(util_score, 2),
        "account_age": round(age_score, 2),
        "credit_mix": round(mix_score, 2),
        "new_credit": round(new_credit_score, 2),
    }

    return final_score, breakdown, plain_reasons, jargon_reasons