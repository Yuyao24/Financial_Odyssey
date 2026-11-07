import random
from game.state import Player
from game.turn import advance_month
from game.events import pick_event, apply_event_choice

def run_cli_game():
    player = Player()
    rng = random.Random()
    print("=== CREDIT WHERE IT'S DUE: CLI PROTOTYPE ===")

    while player.month <= 60 and player.months_insolvent < 3:
        print(f"\n--- MONTH {player.month}/60 ---")
        print(f"Cash: £{player.cash:.2f} | Card Balance: £{player.card.balance:.2f} / £{player.card.limit:.2f}")
        print(f"Credit Score: {player.credit_score} | Net Worth: £{player.net_worth:.2f}")

        # Event
        event = pick_event(player, rng)
        desc = event["plain_description"] if player.plain_language_mode else event["description"]
        print(f"\nEvent: {event['title']}\n{desc}")
        for i, ch in enumerate(event["choices"]):
            txt = ch["plain_text"] if player.plain_language_mode else ch["text"]
            print(f"  [{i+1}] {txt}")

        choice_idx = 0
        try:
            choice_in = input("Select choice [1-2] (default 1): ").strip()
            if choice_in in ("1", "2"):
                choice_idx = int(choice_in) - 1
        except EOFError:
            pass
        apply_event_choice(player, event["choices"][choice_idx])

        # Card payment action
        if player.card.balance > 0:
            print(f"\nCredit Card Statement: Balance £{player.card.balance:.2f}, Min Due £{player.card.min_payment_due:.2f}")
            print("Actions: [1] Pay in Full, [2] Pay Minimum, [3] Skip/Custom (£0)")
            pay_opt = input("Payment choice (default 1): ").strip() or "1"
            if pay_opt == "1":
                pay_amt = min(player.cash, player.card.balance)
                player.cash -= pay_amt
                player.card.paid_this_month = pay_amt
                player.card.balance -= pay_amt
            elif pay_opt == "2":
                pay_amt = min(player.cash, player.card.min_payment_due)
                player.cash -= pay_amt
                player.card.paid_this_month = pay_amt
                player.card.balance -= pay_amt

        # Month Turn
        statement = advance_month(player, rng)
        print(f"\n--- End of Month {statement.month} Statement ---")
        print(f"Bills Paid: £{statement.bills_paid:.2f} | Interest Charged: £{statement.interest_charged:.2f}")
        print(f"Score: {statement.old_score} -> {statement.new_score} ({statement.new_score - statement.old_score:+d})")
        reasons = statement.reasons if player.plain_language_mode else statement.jargon_reasons
        for r in reasons:
            print(f"  * {r}")

    # Results
    mult = 1.2 if player.credit_score >= 750 else (0.8 if player.credit_score < 600 else 1.0)
    final_score = player.net_worth * mult
    print("\n===============================")
    print(f"Game Over! Final Rating Score: {final_score:.1f}")
    print(f"Final Net Worth: £{player.net_worth:.2f} | Final Credit Score: {player.credit_score}")

if __name__ == "__main__":
    run_cli_game()