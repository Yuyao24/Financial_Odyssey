"""Every tuning number for the economy, banking, credit and investing.

Change these to rebalance the game (e.g. START_CASH for testing)."""

from . import content


class GameConfig:
    """Balance constants. All amounts are per quarter (1 turn = 3 months)."""

    # ---- Economy (all amounts per quarter; 1 turn = 3 months) ---------------
    START_CASH = 800
    START_INCOME = 5200            # take-home pay per quarter at 18
    RENT_BASE = 2300               # compulsory
    FOOD_BASE = 1000               # compulsory groceries
    UTIL_BASE = 550                # compulsory transport & utilities
    NO_CAR_SAVING = 150            # transit is a bit cheaper than running a car
    PET_COST = 120
    LIFESTYLE_CREEP = 0.45         # 45% of every raise is eaten by a pricier lifestyle
    INFLATION_QTR = 0.0075         # ~3% / year
    RAISE_QTR = 0.0055             # ~2.2% / year (slower than inflation!)

    HAPPY_COST = 900               # the ONE way to buy happiness on the dashboard
    HAPPY_PTS = 20

    # ---- Banking ------------------------------------------------------------
    OVERDRAFT_LIMIT = 1000
    OVERDRAFT_FEE = 35
    OVERDRAFT_RATE = 0.05
    OVER_LIMIT_FEE = 35
    COLLECTIONS_FEE = 0.15
    LOAN_ORIGINATION = 0.02
    CARD_MIN_PCT = 0.04            # small minimums: carried balances linger (and cost interest)
    LOAN_MIN_PCT = 0.08
    MIN_PAYMENT_FLOOR = 50
    LOAN_MIN_SCORE = 450

    # (min score, tier name, loan rate/qtr, card rate/qtr, card limit, max total loans)
    TIERS = [
        (800, "Excellent", 0.0125, 0.035, 12000, 60000),
        (700, "Good",      0.0175, 0.045,  8000, 30000),
        (600, "Fair",      0.0250, 0.055,  5000, 15000),
        (450, "Poor",      0.0350, 0.065,  3000,  6000),
        (0,   "Very Poor", 0.0475, 0.075,  1000,     0),
    ]
    # Landlords, utilities and insurers price by credit: multiplier on rent + transport & bills
    CREDIT_PRICING = {"Excellent": 0.92, "Good": 0.96, "Fair": 1.00, "Poor": 1.08, "Very Poor": 1.16}
    CREDIT_BANDS = (800, 700, 600, 450, 300)   # crossing below one of these triggers the warning popup
    HISTORY_CAP_TURNS = 20         # 5 years of history ...
    HISTORY_CAP = 700              # ... before you can pass 700
    REBUILD_SCORE = 450            # below this, on-time payments rebuild faster
    # On-time payment gains by band: (paid in full, paid extra, minimum only, minimum with card >90% used)
    PAY_GAINS = {"rebuild": (12, 10, 5, 0), "building": (7, 5, 2, 0),
                 "established": (3, 2, 1, 0), "very_high": (1, 0, 0, 0)}
    STREAK_BONUS = 2               # building band, 4+ on-time quarters in a row, paid in full or extra
    HIGH_UTILIZATION = 0.90
    QUALITY_LABEL = {"full": "paid in full", "more": "paid extra", "minimum": "minimum only",
                     "maxed": "minimum, card over 90% used"}
    IRS_SCORE = 300
    IRS_TURNS = 8                  # strikes = quarters under 300 while STILL missing/late on payments
    DEPRESSION_TURNS = 4
    HAPPY_RECOVER = 25             # depression strikes only fade once happiness is back to 25+

    # ---- Investing ----------------------------------------------------------
    INVEST_RANGE = (-0.02, 0.045)  # calmer quarters: skill, not market luck, should decide the score
    CRASH_CHANCE = 1 / 80
    CRASH_RANGE = (0.10, 0.22)
    EARLY_WITHDRAW_PENALTY = 0.05
    PENALTY_FREE_AGE = 60

    MAX_COURSES = 5
    COURSE_BASE_COST = 1500
    COURSE_BONUS = 550

    MILLION = 1_000_000
    IRS_DEATH_PENALTY = 100_000
    DEPRESSION_DEATH_PENALTY = 25_000

    EVENT_DECK = {
        "festival": 3, "market": 2, "car": 2, "vacation": 2, "course": 3,
        "credit_quiz": 3, "layoff": 1, "medical": 2, "phone": 2, "rent_hike": 1,
        "side_hustle": 2, "wedding": 2, "tax_refund": 1, "limit_offer": 1,
        "identity_theft": 1, "pet": 1, "review": 2, "crypto": 1, "inheritance": 1,
        "accident": 1, "scam": 1, "dip": 1, "bonus": 1, "debt_offer": 1,
    }

    # ---- Content (see content.py) ---------------------------------------------
    ACHIEVEMENTS = content.ACHIEVEMENTS
    QUIZ = content.QUIZ
