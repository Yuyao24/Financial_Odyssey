"""Static game content: achievements and the credit quiz questions."""


ACHIEVEMENTS = {
    "first_swipe":  ("First Swipe", "Used your credit card for the first time"),
    "on_time":      ("Responsible Borrower", "Made your first on-time payment"),
    "streak8":      ("Clockwork", "8 on-time payments in a row"),
    "good_credit":  ("Good Credit", "Reached a 700 credit score"),
    "excellent":    ("Excellent Credit", "Reached an 800 credit score"),
    "investor":     ("Investor", "Made your first investment"),
    "debt_free":    ("Debt Free", "Paid off every dollar of debt"),
    "learner":      ("Lifelong Learner", "Completed all 5 certifications"),
    "storm":        ("Weathered the Storm", "Kept investing through a market crash"),
    "six_figures":  ("Six Figures", "Net worth of $100,000"),
    "millionaire":  ("Millionaire", "Net worth of $1,000,000"),
    "quiz_whiz":    ("Credit Whiz", "Answered 3 credit quizzes correctly"),
    "golden":       ("Golden Years", "Made it to retirement at 65"),
}


QUIZ = [
    ("What has the biggest impact on your credit score?",
     ["Paying at least the minimum on time, every time",
      "How much cash you keep in the bank",
      "How often you check your score"],
     "Payment history is king. In this game your score only rises when you pay what is due, "
     "and only falls when you don't. Cash balance and checking your score don't affect it."),
    ("Your statement shows: balance $2,000, minimum due $80. What protects your score?",
     ["Pay at least $80 now — ideally all $2,000 to avoid interest",
      "Pay nothing until next quarter",
      "Pay $50, any amount counts"],
     "Paying the minimum keeps the payment on time. Paying less than the minimum still counts as a "
     "LATE payment (-20), and paying nothing is a MISSED payment (-50). Paying the full statement "
     "also means no card interest thanks to the grace period."),
    ("Which usually charges the highest interest?",
     ["A credit card balance you carry over",
      "A bank loan",
      "They always charge the same"],
     "Credit cards have much higher rates than bank loans. When you pay debt, attack the "
     "highest-rate balance first (this game automatically pays your card first)."),
    ("What happens if you ignore a bill you can't pay?",
     ["It goes to collections: extra fees and a big credit hit",
      "Nothing, it disappears after a while",
      "The bank pays it for you for free"],
     "Unpaid bills are sent to collections: a 15% fee is added, it becomes debt, and it counts as "
     "a missed payment (-50). Even a small payment plan is better than ignoring a bill."),
    ("Why can't an 18-year-old jump straight to an 800 score?",
     ["Lenders want a long history — scores are capped near 700 for ~5 years",
      "Young people are banned from good credit",
      "Scores only start counting at age 30"],
     "Length of credit history matters. In this game your score can't pass 700 until you've had "
     "5 years (20 quarters) of history — so start building good habits early."),
    ("Does swiping your credit card lower your score in this game?",
     ["No — only unpaid minimum payments lower it",
      "Yes, every purchase costs points",
      "Only purchases over $100"],
     "Using your card is not the problem — not paying it back is. Charging things and paying the "
     "statement on time is exactly how you build credit."),
    ("What does a higher credit score get you?",
     ["Lower interest, higher card limits and bigger loans",
      "A higher salary",
      "Free groceries"],
     "Better credit tiers lower your loan and card interest rates, raise your card limit and let you "
     "borrow more. Over a lifetime that's thousands of dollars saved."),
    ("What is an overdraft?",
     ["Spending more than your bank balance — the bank covers it, for fees and interest",
      "A free bonus from the bank",
      "A type of investment"],
     "Overdraft lets your cash go negative (up to $1,000 here), but costs a $35 fee plus 5% interest "
     "each quarter. Go past the limit and the rest goes to your card or to collections."),
    ("If you only ever pay the minimum on your card...",
     ["You avoid penalties, but your score barely grows and interest piles up",
      "The debt is forgiven after a year",
      "You never pay any interest"],
     "Minimum payments avoid a late or missed penalty, but lenders see a card that stays nearly full: "
     "your score grows slowly (not at all above 90% used) while the balance collects interest. "
     "Pay in full whenever you can."),
    ("$1,000 on a card at 5% interest per quarter, unpaid for a year, becomes about...",
     ["$1,216", "$1,050", "$1,000"],
     "Interest compounds: 1,000 x 1.05 x 1.05 x 1.05 x 1.05 = about $1,216. Debt grows on top of itself."),
]
