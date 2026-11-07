import math
import pygame
import random
import sys

# Initialize Pygame
pygame.init()

# 1080x1920 portrait virtual screen resolution with black bars
VIRTUAL_WIDTH = 1080
VIRTUAL_HEIGHT = 1920

# Display Setup
screen_info = pygame.display.Info()
DISPLAY_WIDTH = screen_info.current_w
DISPLAY_HEIGHT = screen_info.current_h

# Calculate scaling to fit 1080x1920 inside the display with black bars
TARGET_ASPECT = VIRTUAL_WIDTH / VIRTUAL_HEIGHT
SCREEN_ASPECT = DISPLAY_WIDTH / DISPLAY_HEIGHT

if SCREEN_ASPECT > TARGET_ASPECT:
    # Screen is wider than target aspect ratio (pillarboxing)
    WINDOW_HEIGHT = DISPLAY_HEIGHT
    WINDOW_WIDTH = int(DISPLAY_HEIGHT * TARGET_ASPECT)
else:
    # Screen is taller than target aspect ratio (letterboxing)
    WINDOW_WIDTH = DISPLAY_WIDTH
    WINDOW_HEIGHT = int(DISPLAY_WIDTH / TARGET_ASPECT)

window = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Financial Odyssey: 18 to 65")

virtual_surface = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))

# Colors
BLACK = (10, 15, 25)
WHITE = (245, 245, 250)
GREEN = (46, 204, 113)
DARK_GREEN = (39, 174, 96)
RED = (231, 76, 60)
DARK_RED = (192, 57, 43)
BLUE = (54, 162, 235)
DARK_BLUE = (41, 128, 185)
YELLOW = (241, 196, 15)
DARK_YELLOW = (212, 143, 0)
ORANGE = (230, 126, 34)
PURPLE = (155, 89, 182)
GRAY = (149, 165, 166)
DARK_GRAY = (52, 73, 94)
CARD_BG = (34, 45, 62)
BG_COLOR = (18, 26, 38)
ACCENT = (255, 215, 0)

# Fonts
try:
    FONT_TITLE = pygame.font.SysFont("arial", 64, bold=True)
    FONT_HEADER = pygame.font.SysFont("arial", 46, bold=True)
    FONT_MEDIUM = pygame.font.SysFont("arial", 36, bold=True)
    FONT_REGULAR = pygame.font.SysFont("arial", 28)
    FONT_SMALL = pygame.font.SysFont("arial", 22)
except:
    FONT_TITLE = pygame.font.Font(None, 64)
    FONT_HEADER = pygame.font.Font(None, 46)
    FONT_MEDIUM = pygame.font.Font(None, 36)
    FONT_REGULAR = pygame.font.Font(None, 28)
    FONT_SMALL = pygame.font.Font(None, 22)

# Ignore clicks for a short time after the screen changes, so a fast double click
# can't advance a quarter AND pick an event option in one go.
CLICK_COOLDOWN_MS = 200


class Button:
    def __init__(self, x, y, w, h, text, color=BLUE, hover_color=DARK_BLUE, font=None, text_color=WHITE):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.font = font or FONT_REGULAR
        self.text_color = text_color
        self.hovered = False
        self.enabled = True

    def draw(self, surface):
        draw_color = DARK_GRAY if not self.enabled else (self.hover_color if self.hovered else self.color)

        # Shadow
        shadow_rect = self.rect.copy()
        shadow_rect.x += 4
        shadow_rect.y += 4
        pygame.draw.rect(surface, (0, 0, 0, 150), shadow_rect, border_radius=16)
        pygame.draw.rect(surface, draw_color, self.rect, border_radius=16)
        pygame.draw.rect(surface, WHITE if self.hovered and self.enabled else draw_color, self.rect, 3,
                         border_radius=16)

        # Multi-line or single line text draw
        words = self.text.split()
        lines = []
        curr_line = ""
        for w in words:
            test = curr_line + (" " if curr_line else "") + w
            if self.font.size(test)[0] < self.rect.width - 30:
                curr_line = test
            else:
                lines.append(curr_line)
                curr_line = w
        if curr_line:
            lines.append(curr_line)

        line_height = self.font.get_linesize()
        start_y = self.rect.centery - (len(lines) * line_height) // 2
        for i, line in enumerate(lines):
            ts = self.font.render(line, True, self.text_color if self.enabled else GRAY)
            tr = ts.get_rect(center=(self.rect.centerx, start_y + i * line_height + line_height // 2))
            surface.blit(ts, tr)

    def check_hover(self, pos):
        self.hovered = self.rect.collidepoint(pos) and self.enabled
        return self.hovered

    def is_clicked(self, pos, click):
        return self.enabled and self.rect.collidepoint(pos) and click


class LifeGame:
    # ------------------------------------------------------------------
    # Balance constants (tweak here)
    # ------------------------------------------------------------------
    START_INCOME = 4500            # Quarterly salary at 18
    START_EXPENSE = 2000           # Quarterly living costs at 18
    INFLATION_QTR = 0.005          # Prices rise ~2%/yr
    RAISE_QTR = 0.0025             # Cost-of-living pay rises ~1%/yr (slower than prices)

    INVEST_RANGE = (-0.05, 0.10)   # Normal quarter: -5% to +10%
    CRASH_CHANCE = 1 / 30          # ~6 market crashes in a lifetime
    CRASH_RANGE = (0.20, 0.35)     # A crash wipes out 20-35% of the portfolio
    EARLY_WITHDRAW_PENALTY = 0.10  # 10% penalty for withdrawing before PENALTY_FREE_AGE
    PENALTY_FREE_AGE = 60

    MAX_COURSES = 6
    COURSE_BASE_COST = 1200        # Each extra course costs 1.5x the previous one
    COURSE_BASE_BONUS = 500        # Each extra course adds $50 less income than the previous one
    LIFESTYLE_CREEP = 0.2          # Share of every raise that gets eaten by a fancier lifestyle

    NO_CAR_INCOME_MULT = 0.95      # Without a car you lose some shifts / job options

    LOAN_MIN_CREDIT = 400          # Any loan needs at least this credit score
    COURSE_LOAN_MIN_CREDIT = 600
    INVEST_LOAN_MIN_CREDIT = 700
    REFI_MIN_CREDIT = 450
    REFI_RATE = 0.02
    REFI_TURNS = 4

    COLLECTIONS_RATIO = 3          # Debt above 3x quarterly pay goes to collections
    GARNISH_RATE = 0.25            # Collections garnish 25% of wages

    DEATH_PENALTY = 100_000        # Dying early is always worse than surviving

    # Weighted, shuffled deck so events come up at a steady, predictable rate.
    EVENT_DECK = (["medical"] * 3 + ["market"] * 2 + ["car"] * 2 + ["vacation"] * 2 +
                  ["course"] * 2 + ["debt"] * 2 + ["layoff"])

    def __init__(self, seed=None):
        self.reset(seed)

    def reset(self, seed=None):
        # Every run has its own seed so a run can be replayed / compared fairly.
        self.seed = seed if seed is not None else random.randrange(1_000_000)
        self.rng = random.Random(self.seed)

        self.age_years = 18
        self.age_months = 0
        self.cash = 1500
        self.credit_score = 650  # Cap: 1000, Death threshold < 299 for ~8 turns (2 years)
        self.debt = 0
        self.investments = 0
        self.health = 100  # Cap 100, Death threshold <= 0 for ~4 turns (1 year)

        # Strike counters: +1 for every bad quarter, -1 for every good one
        # (a single good quarter no longer wipes the slate clean).
        self.low_credit_turns = 0
        self.zero_health_turns = 0

        self.state = "card_prompt"  # card_prompt, main, event, game_over
        self.death_reason = ""
        self.log = []
        self.current_event = None
        self.event_costs = {}
        self.event_buttons = []
        self.message = ""

        # Quarter stats (in "age 18 dollars"; scaled by wage_index / price_index)
        self.base_income = self.START_INCOME
        self.base_living_expense = self.START_EXPENSE
        self.price_index = 1.0
        self.wage_index = 1.0

        # Life state
        self.has_car = True
        self.courses_taken = 0
        self.layoff_turns = 0
        self.layoff_mult = 1.0
        self.refi_turns = 0
        self.in_collections = False
        self.bankruptcies = 0
        self.event_deck = []

    # ------------------------------------------------------------------
    # Derived values
    # ------------------------------------------------------------------
    def get_net_worth(self):
        return self.cash + self.investments - self.debt

    def price(self, amount):
        """Today's price of something that cost `amount` at age 18."""
        return int(round(amount * self.price_index))

    def wage(self, amount):
        """Today's pay for something that paid `amount` at age 18."""
        return int(round(amount * self.wage_index))

    def health_multiplier(self):
        # Sick people earn less: 60% pay at 0 HP, 100% pay at 100 HP.
        return 0.6 + 0.4 * self.health / 100

    def potential_income(self):
        """Full-time, fully healthy quarterly pay."""
        return int(self.base_income * self.wage_index)

    def quarterly_income(self):
        """What you'll actually be paid next quarter at your current health / job status."""
        mult = self.health_multiplier() * self.layoff_mult
        if not self.has_car:
            mult *= self.NO_CAR_INCOME_MULT
        return int(self.potential_income() * mult)

    def living_expense(self):
        return self.price(self.base_living_expense)

    def health_decay(self):
        # Bodies wear out: -15 HP/qtr at 18 rising to -25 HP/qtr at 65.
        return 15 + (10 * (self.age_years - 18)) // 47

    def interest_rate(self):
        """Quarterly interest rate. Good credit = cheap money."""
        if self.refi_turns > 0:
            return self.REFI_RATE
        c = self.credit_score
        if c >= 800:
            return 0.02
        if c >= 650:
            return 0.035
        if c >= 500:
            return 0.05
        return 0.07

    def withdraw_penalty_rate(self):
        return 0.0 if self.age_years >= self.PENALTY_FREE_AGE else self.EARLY_WITHDRAW_PENALTY

    def grocery_cost(self):
        return self.price(300)

    def spa_cost(self):
        return self.price(800)

    def course_cost(self):
        return self.price(self.COURSE_BASE_COST * 1.5 ** self.courses_taken)

    def course_bonus(self):
        """Extra quarterly pay (in age-18 dollars) from the next course."""
        return self.COURSE_BASE_BONUS - 50 * self.courses_taken

    def medical_cost(self):
        # Healthcare gets pricier with age (up to +50% at 65) on top of inflation.
        return self.price(600 * (1 + 0.5 * (self.age_years - 18) / 47))

    def final_score(self):
        nw = self.get_net_worth()
        if self.death_reason == "RETIREMENT":
            if nw >= 0:
                # Credit is a multiplier: 0.5x at 0 credit, 1.0x at 1000 credit.
                return int(nw * self.score_multiplier())
            return int(nw)
        # Dying early: keep only a quarter of your wealth, plus a flat penalty.
        return int(min(nw, nw * 0.25) - self.DEATH_PENALTY)

    def score_multiplier(self):
        return 0.5 + self.credit_score / 2000

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def add_log(self, text, color=WHITE):
        self.log.append((f"Age {self.age_years} Q{(self.age_months // 3) + 1}: {text}", color))
        if len(self.log) > 6:
            self.log.pop(0)

    def update_credit(self, delta):
        self.credit_score = max(0, min(1000, self.credit_score + delta))

    def take_loan(self, amount):
        """Borrow money. An up-front fee (one quarter's interest) stops free same-turn loans."""
        fee = math.ceil(amount * self.interest_rate())
        self.debt += amount + fee
        self.update_collections()
        return fee

    def repay(self, amount):
        """Repay debt from cash. Credit gain scales with dollars repaid, not clicks."""
        pay = min(amount, self.debt, self.cash)
        if pay <= 0:
            return 0, 0
        self.cash -= pay
        self.debt -= pay
        gain = pay // 50
        self.update_credit(gain)
        self.update_collections()
        return pay, gain

    def update_collections(self):
        was = self.in_collections
        self.in_collections = self.debt > self.COLLECTIONS_RATIO * self.potential_income()
        if self.in_collections and not was:
            self.add_log("Debt sent to COLLECTIONS! 25% of wages garnished", RED)
        elif was and not self.in_collections:
            self.add_log("Out of collections. Wages no longer garnished", GREEN)

    # ------------------------------------------------------------------
    # Dashboard actions (kept on the class so they can be tested headless)
    # ------------------------------------------------------------------
    def can_buy_groceries(self):
        return self.cash >= self.grocery_cost()

    def buy_groceries(self):
        if not self.can_buy_groceries():
            return False
        cost = self.grocery_cost()
        self.cash -= cost
        self.health = min(100, self.health + 20)
        self.add_log(f"Bought healthy groceries (-${cost:,}, Health +20)", GREEN)
        return True

    def can_buy_spa(self):
        return self.cash >= self.spa_cost()

    def buy_spa(self):
        if not self.can_buy_spa():
            return False
        cost = self.spa_cost()
        self.cash -= cost
        self.health = min(100, self.health + 50)
        self.add_log(f"Went for health & spa treatment (-${cost:,}, Health +50)", GREEN)
        return True

    def can_pay_debt(self):
        return self.debt > 0 and self.cash >= min(500, self.debt)

    def quick_pay_debt(self):
        if not self.can_pay_debt():
            return False
        pay, gain = self.repay(500)
        self.add_log(f"Paid ${pay:,} debt. Credit +{gain}", GREEN)
        return True

    def can_invest(self):
        return self.cash >= 500

    def quick_invest(self):
        if not self.can_invest():
            return False
        self.cash -= 500
        self.investments += 500
        self.add_log("Invested $500 in Index Funds", BLUE)
        return True

    def can_withdraw(self):
        return self.investments > 0

    def quick_withdraw(self, amount=500):
        if not self.can_withdraw():
            return False
        amt = min(amount, self.investments)
        penalty = int(amt * self.withdraw_penalty_rate())
        self.investments -= amt
        self.cash += amt - penalty
        if penalty:
            self.add_log(f"Withdrew ${amt:,} (early withdrawal fee -${penalty:,})", ORANGE)
        else:
            self.add_log(f"Withdrew ${amt:,} from investments", BLUE)
        return True

    def can_declare_bankruptcy(self):
        return self.in_collections

    def declare_bankruptcy(self):
        """Last resort: creditors take your cash and investments, the rest of the debt is wiped."""
        if not self.can_declare_bankruptcy():
            return False
        assets = self.cash + self.investments
        seized = min(assets, self.debt)
        leftover = assets - seized
        self.cash = leftover
        self.investments = 0
        self.debt = 0
        self.credit_score = 300
        self.low_credit_turns = 0
        self.refi_turns = 0
        self.bankruptcies += 1
        self.in_collections = False
        self.add_log(f"BANKRUPTCY: ${seized:,} of assets seized, debt wiped. Credit -> 300", RED)
        return True

    # ------------------------------------------------------------------
    # Turn flow
    # ------------------------------------------------------------------
    def next_turn(self):
        # Age progression (3 months)
        self.age_months += 3
        if self.age_months >= 12:
            self.age_years += 1
            self.age_months = 0

        # Check retirement at 65
        if self.age_years >= 65:
            self.state = "game_over"
            self.death_reason = "RETIREMENT"
            return

        # Prices rise faster than wages
        self.price_index *= 1 + self.INFLATION_QTR
        self.wage_index *= 1 + self.RAISE_QTR

        # Income (depends on health at the start of the quarter, job and car)
        earned = self.quarterly_income()
        if self.layoff_turns > 0:
            self.layoff_turns -= 1
            if self.layoff_turns == 0:
                self.layoff_mult = 1.0
                self.add_log("Back on full pay!", GREEN)

        # Collections garnish wages straight to the debt
        if self.in_collections and self.debt > 0:
            garnish = min(self.debt, int(earned * self.GARNISH_RATE))
            self.debt -= garnish
            earned -= garnish
            self.add_log(f"Collections garnished ${garnish:,} of wages", RED)

        self.cash += earned

        # Passive decay of health (must buy food/care every quarter)
        self.health = max(0, self.health - self.health_decay())

        # Debt interest: rate depends on credit band; credit hit scales with debt vs income
        if self.debt > 0:
            rate = self.interest_rate()
            interest = math.ceil(self.debt * rate)
            self.debt += interest
            penalty = min(40, 5 + int(10 * self.debt / max(1, self.potential_income())))
            self.update_credit(-penalty)
            self.add_log(f"Debt interest +${interest:,} ({rate:.1%}), Credit -{penalty}", RED)
        else:
            self.update_credit(5)  # No debt boosts credit score
        if self.refi_turns > 0:
            self.refi_turns -= 1

        # Investment returns (-5% to +10% quarterly, with the odd market crash)
        if self.investments > 0:
            if self.rng.random() < self.CRASH_CHANCE:
                growth = -self.rng.uniform(*self.CRASH_RANGE)
                change = int(self.investments * growth)
                self.investments = max(0, self.investments + change)
                self.add_log(f"MARKET CRASH! Investments lost ${abs(change):,}", RED)
            else:
                growth = self.rng.uniform(*self.INVEST_RANGE)
                change = int(self.investments * growth)
                self.investments = max(0, self.investments + change)
                if change >= 0:
                    self.add_log(f"Investments grew by +${change:,}", GREEN)
                else:
                    self.add_log(f"Investments changed by -${abs(change):,}", RED)

        # Can user pay living expenses?
        expense = self.living_expense()
        if self.cash >= expense:
            self.cash -= expense
        else:
            deficit = expense - self.cash
            self.cash = 0
            self.debt += deficit
            self.update_credit(-30)
            self.add_log(f"Couldn't pay bills! +${deficit:,} Debt, Credit -30", RED)
        self.update_collections()

        # Health check (strike counter: bad quarters add, good quarters remove one)
        if self.health <= 0:
            self.zero_health_turns += 1
            if self.zero_health_turns >= 4:  # ~1 year at 0 health
                self.state = "game_over"
                self.death_reason = "HEALTH_FAILURE"
                return
        else:
            self.zero_health_turns = max(0, self.zero_health_turns - 1)

        # IRS Credit check (< 299 for ~2 years / 8 turns)
        if self.credit_score < 299:
            self.low_credit_turns += 1
            if self.low_credit_turns >= 8:
                self.state = "game_over"
                self.death_reason = "IRS_SEIZURE"
                return
        else:
            self.low_credit_turns = max(0, self.low_credit_turns - 1)

        # Trigger random quarter event
        self.trigger_quarter_event()

    def draw_event_key(self):
        for _ in range(len(self.EVENT_DECK) * 2):
            if not self.event_deck:
                self.event_deck = list(self.EVENT_DECK)
                self.rng.shuffle(self.event_deck)
            key = self.event_deck.pop()
            if key == "debt" and self.debt <= 0:
                continue  # No point offering refinancing to a debt-free player
            if key == "course" and self.courses_taken >= self.MAX_COURSES:
                continue
            return key
        return "medical"

    def build_event(self, key):
        c = {}
        if key == "medical":
            c["med"] = self.medical_cost()
            skip_hp = 20 if self.age_years < 45 else 25
            c["skip_hp"] = skip_hp
            return c, {
                "title": "Medical Checkup & Care",
                "desc": "Unexpected dental work and prescription fees came up.",
                "options": [
                    (f"Pay ${c['med']:,} in Cash (Health +30)", "pay_med"),
                    (f"Charge ${c['med']:,} to Credit Card (Health +30)", "debt_med"),
                    (f"Skip treatment (-{skip_hp} Health)", "skip_med")
                ]
            }
        if key == "market":
            c["invest"] = self.price(1000)
            c["invest_loan"] = self.price(2000)
            return c, {
                "title": "Stock Market Trend",
                "desc": "Market news is hyping an Index Fund. Remember: hype doesn't guarantee returns.",
                "options": [
                    (f"Invest ${c['invest']:,} in Index Funds", "invest_index"),
                    (f"Take out ${c['invest_loan']:,} loan to invest heavy", "loan_invest"),
                    ("Pass on opportunity", "pass")
                ]
            }
        if key == "car" and self.has_car:
            c["car"] = self.price(800)
            c["car_sale"] = self.price(1200)
            return c, {
                "title": "Car Maintenance",
                "desc": "Your car transmission needs repair to get to work.",
                "options": [
                    (f"Pay ${c['car']:,} cash to fix", "fix_car_cash"),
                    (f"Take out ${c['car']:,} repair loan", "fix_car_loan"),
                    (f"Sell car (+${c['car_sale']:,}, -10 Health, Income -5% while carless)", "sell_car")
                ]
            }
        if key == "car":
            c["used_car"] = self.price(3000)
            return c, {
                "title": "Commuting Without a Car",
                "desc": "Missed buses are costing you shifts. A used car is for sale nearby.",
                "options": [
                    (f"Buy a used car (${c['used_car']:,} cash)", "buy_car_cash"),
                    (f"Finance a used car (${c['used_car']:,} loan)", "buy_car_loan"),
                    ("Keep taking the bus (-10 Health)", "bus")
                ]
            }
        if key == "vacation":
            c["vacation"] = self.price(1500)
            c["extra_work"] = self.wage(600)
            return c, {
                "title": "Luxury Vacation Offer",
                "desc": "Friends invite you on a 7-day tropical trip.",
                "options": [
                    (f"Go on trip (${c['vacation']:,} Cash, +35 Health)", "vacation_cash"),
                    (f"Take out loan for trip (${c['vacation']:,} Debt, +35 Health)", "vacation_loan"),
                    (f"Decline and work extra shifts (+${c['extra_work']:,}, -10 Health)", "vacation_skip")
                ]
            }
        if key == "course":
            c["course"] = self.course_cost()
            c["bonus"] = self.course_bonus()
            bonus_now = self.wage(c["bonus"])
            n = self.courses_taken + 1
            return c, {
                "title": "Career Certification",
                "desc": f"Course {n} of {self.MAX_COURSES}: boost your pay. A better job also means pricier "
                        f"habits (+20% of the raise in living costs).",
                "options": [
                    (f"Pay ${c['course']:,} for course (Income +${bonus_now:,}/qtr)", "course_cash"),
                    (f"Finance course with ${c['course']:,} loan", "course_loan"),
                    ("Skip course", "pass")
                ]
            }
        if key == "debt":
            c["pay"] = min(self.debt, self.price(1000))
            c["refi_fee"] = self.price(250)
            return c, {
                "title": "Debt Consolidation Offer",
                "desc": "A bank offers to refinance your current loans with a structured payment.",
                "options": [
                    (f"Pay off ${c['pay']:,} Debt right now (+10 bonus Credit)", "pay_debt_now"),
                    (f"Refinance to {self.REFI_RATE:.0%}/qtr for {self.REFI_TURNS} qtrs (${c['refi_fee']:,} fee)",
                     "refinance"),
                    ("Ignore offer", "pass")
                ]
            }
        # layoff
        c["severance"] = self.wage(1500)
        return c, {
            "title": "Layoff Notice",
            "desc": "Your company is downsizing and your role is on the chopping block.",
            "options": [
                (f"Take severance & job hunt (+${c['severance']:,}, Income -50% for 2 qtrs, +10 Health)",
                 "layoff_severance"),
                ("Grab a temp gig (Income -25% for 2 qtrs, -15 Health)", "layoff_temp"),
                ("Fight to keep the job (50/50: no change, or Income -50% for 3 qtrs)", "layoff_gamble")
            ]
        }

    def trigger_quarter_event(self):
        key = self.draw_event_key()
        self.event_costs, self.current_event = self.build_event(key)
        self.state = "event"
        self.build_event_buttons()

    def option_block_reason(self, action):
        """Why an event option can't be picked right now (None if it can)."""
        c = self.event_costs
        cash_needed = {
            "pay_med": c.get("med"),
            "invest_index": c.get("invest"),
            "fix_car_cash": c.get("car"),
            "buy_car_cash": c.get("used_car"),
            "vacation_cash": c.get("vacation"),
            "course_cash": c.get("course"),
            "pay_debt_now": c.get("pay"),
            "refinance": c.get("refi_fee"),
        }
        need = cash_needed.get(action)
        if need is not None and self.cash < need:
            return f"need ${need:,} cash"

        credit_needed = {
            "debt_med": self.LOAN_MIN_CREDIT,
            "fix_car_loan": self.LOAN_MIN_CREDIT,
            "buy_car_loan": self.LOAN_MIN_CREDIT,
            "vacation_loan": self.LOAN_MIN_CREDIT,
            "course_loan": self.COURSE_LOAN_MIN_CREDIT,
            "loan_invest": self.INVEST_LOAN_MIN_CREDIT,
            "refinance": self.REFI_MIN_CREDIT,
        }
        need = credit_needed.get(action)
        if need is not None:
            if self.in_collections and action != "refinance":
                return "no loans while in collections"
            if self.credit_score < need:
                return f"needs credit {need}+"
        return None

    def build_event_buttons(self):
        self.event_buttons = []
        options = self.current_event["options"]
        bw, bh = 940, 110
        start_y = 1120  # Kept clear of the ADVANCE button underneath (y 1540+)
        spacing = 30

        for i, (text, action) in enumerate(options):
            reason = self.option_block_reason(action)
            label = text if reason is None else f"{text} [{reason}]"
            x = (VIRTUAL_WIDTH - bw) // 2
            y = start_y + i * (bh + spacing)
            btn = Button(x, y, bw, bh, label, BLUE, DARK_BLUE, FONT_REGULAR)
            btn.action = action
            btn.enabled = reason is None
            self.event_buttons.append(btn)

    def handle_choice(self, action):
        reason = self.option_block_reason(action)
        if reason is not None:
            # Unaffordable options no longer silently burn the event
            self.add_log(f"Can't choose that: {reason}", RED)
            return False

        c = self.event_costs
        credit_change = 0

        if action == "pay_med":
            self.cash -= c["med"]
            self.health = min(100, self.health + 30)
            self.add_log(f"Paid ${c['med']:,} medical bill. Health +30", GREEN)

        elif action == "debt_med":
            fee = self.take_loan(c["med"])
            self.health = min(100, self.health + 30)
            credit_change = -15
            self.add_log(f"Charged ${c['med']:,} (+${fee} fee) to card. Health +30, Credit -15", RED)

        elif action == "skip_med":
            self.health = max(0, self.health - c["skip_hp"])
            self.add_log(f"Skipped medical care. Health dropped by {c['skip_hp']}", ORANGE)

        elif action == "invest_index":
            self.cash -= c["invest"]
            self.investments += c["invest"]
            self.add_log(f"Invested ${c['invest']:,} into Index Funds", GREEN)

        elif action == "loan_invest":
            fee = self.take_loan(c["invest_loan"])
            self.investments += c["invest_loan"]
            credit_change = -25
            self.add_log(f"Took ${c['invest_loan']:,} loan (+${fee} fee) to invest. Credit -25", RED)

        elif action == "fix_car_cash":
            self.cash -= c["car"]
            self.add_log(f"Repaired car for ${c['car']:,} cash", GREEN)

        elif action == "fix_car_loan":
            fee = self.take_loan(c["car"])
            credit_change = -15
            self.add_log(f"Took ${c['car']:,} repair loan (+${fee} fee). Credit -15", RED)

        elif action == "sell_car":
            self.cash += c["car_sale"]
            self.has_car = False
            self.health = max(0, self.health - 10)
            self.add_log(f"Sold car for ${c['car_sale']:,}. -10 Health, Income -5% until you buy another",
                         YELLOW)

        elif action == "buy_car_cash":
            self.cash -= c["used_car"]
            self.has_car = True
            self.add_log(f"Bought a used car for ${c['used_car']:,}. Full income restored", GREEN)

        elif action == "buy_car_loan":
            fee = self.take_loan(c["used_car"])
            self.has_car = True
            credit_change = -15
            self.add_log(f"Financed a used car (${c['used_car']:,} + ${fee} fee). Credit -15", YELLOW)

        elif action == "bus":
            self.health = max(0, self.health - 10)
            self.add_log("Stuck with the bus. Health -10", ORANGE)

        elif action == "vacation_cash":
            self.cash -= c["vacation"]
            self.health = min(100, self.health + 35)
            self.add_log(f"Enjoyed ${c['vacation']:,} vacation! Health +35", GREEN)

        elif action == "vacation_loan":
            fee = self.take_loan(c["vacation"])
            self.health = min(100, self.health + 35)
            credit_change = -20
            self.add_log(f"Took ${c['vacation']:,} vacation loan (+${fee} fee). Credit -20", RED)

        elif action == "vacation_skip":
            self.cash += c["extra_work"]
            self.health = max(0, self.health - 10)
            self.add_log(f"Worked extra shifts instead: +${c['extra_work']:,}, Health -10", WHITE)

        elif action in ("course_cash", "course_loan"):
            if action == "course_cash":
                self.cash -= c["course"]
                note = "paid cash"
            else:
                fee = self.take_loan(c["course"])
                credit_change = -10
                note = f"financed, +${fee} fee, Credit -10"
            self.base_income += c["bonus"]
            self.base_living_expense += int(c["bonus"] * self.LIFESTYLE_CREEP)
            self.courses_taken += 1
            self.add_log(f"Course {self.courses_taken} done ({note})! Income +${self.wage(c['bonus']):,}/qtr",
                         GREEN if action == "course_cash" else YELLOW)

        elif action == "pay_debt_now":
            pay, gain = self.repay(c["pay"])
            credit_change = 10
            self.add_log(f"Paid off ${pay:,} debt! Credit +{gain + 10}", GREEN)

        elif action == "refinance":
            self.cash -= c["refi_fee"]
            self.refi_turns = self.REFI_TURNS
            self.add_log(f"Refinanced: debt at {self.REFI_RATE:.0%}/qtr for {self.REFI_TURNS} quarters", GREEN)

        elif action == "layoff_severance":
            self.cash += c["severance"]
            self.layoff_turns, self.layoff_mult = 2, 0.5
            self.health = min(100, self.health + 10)
            self.add_log(f"Laid off. Severance +${c['severance']:,}, half pay for 2 quarters", ORANGE)

        elif action == "layoff_temp":
            self.layoff_turns, self.layoff_mult = 2, 0.75
            self.health = max(0, self.health - 15)
            self.add_log("Took a temp gig: 75% pay for 2 quarters, Health -15", ORANGE)

        elif action == "layoff_gamble":
            if self.rng.random() < 0.5:
                self.add_log("You kept your job! No change", GREEN)
            else:
                self.layoff_turns, self.layoff_mult = 3, 0.5
                self.add_log("Gamble lost: laid off, half pay for 3 quarters", RED)

        elif action == "pass":
            self.add_log("Passed on option.", WHITE)

        if credit_change != 0:
            self.update_credit(credit_change)

        self.state = "main"
        return True


def draw_card_prompt(surface, game, buttons, mouse_pos):
    surface.fill(BG_COLOR)

    # Large Card Banner
    card_rect = pygame.Rect(70, 300, 940, 1100)
    pygame.draw.rect(surface, CARD_BG, card_rect, border_radius=24)
    pygame.draw.rect(surface, ACCENT, card_rect, 4, border_radius=24)

    # Title
    ts = FONT_TITLE.render("WELCOME TO LIFE", True, ACCENT)
    tr = ts.get_rect(center=(VIRTUAL_WIDTH // 2, 400))
    surface.blit(ts, tr)

    subtitle = FONT_HEADER.render("Financial Odyssey (18 - 65)", True, WHITE)
    sr = subtitle.get_rect(center=(VIRTUAL_WIDTH // 2, 480))
    surface.blit(subtitle, sr)

    # Message text
    msg_lines = [
        "Congratulations! You turn 18 today.",
        "You have officially APPLIED FOR YOUR FIRST CREDIT CARD!",
        "",
        "--- GAME RULES ---",
        "• 1 turn = 3 Months. Retire at 65 with max Net Worth.",
        "• Low Health lowers your pay.",
        "  (0 Health for about 1 year = DEATH)",
        "• Keep Credit Score above 299.",
        "  (Credit < 299 for about 2 years = IRS SEIZURE & DEATH)",
        "• Good credit = cheaper loans & a bigger final score.",
        "• Prices rise every quarter. Keep an emergency fund!",
        "• Markets can crash. Early withdrawals cost 10% (free at 60).",
        "• Debt over 3x your pay goes to collections.",
        "• Dying early wrecks your final score."
    ]

    y = 560
    for line in msg_lines:
        color = ACCENT if "---" in line else (GREEN if "APPLIED" in line else WHITE)
        font = FONT_MEDIUM if "---" in line or "APPLIED" in line else FONT_REGULAR
        t = font.render(line, True, color)
        r = t.get_rect(center=(VIRTUAL_WIDTH // 2, y))
        surface.blit(t, r)
        y += 50

    start_btn = Button(190, 1500, 700, 120, "BEGIN YOUR JOURNEY", GREEN, DARK_GREEN, FONT_TITLE)
    start_btn.check_hover(mouse_pos)
    start_btn.draw(surface)
    buttons.append(start_btn)


def draw_main_dashboard(surface, game, buttons, mouse_pos):
    surface.fill(BG_COLOR)

    # Top Header Panel
    header_rect = pygame.Rect(40, 40, 1000, 220)
    pygame.draw.rect(surface, CARD_BG, header_rect, border_radius=20)
    pygame.draw.rect(surface, GRAY, header_rect, 2, border_radius=20)

    # Age & Quarter
    qtr = (game.age_months // 3) + 1
    t_age = FONT_TITLE.render(f"AGE: {game.age_years} (Q{qtr})", True, ACCENT)
    surface.blit(t_age, (70, 70))

    t_nw = FONT_HEADER.render(f"Net Worth: ${game.get_net_worth():,}", True,
                              GREEN if game.get_net_worth() >= 0 else RED)
    surface.blit(t_nw, (70, 160))

    # Stats Panel
    stats_rect = pygame.Rect(40, 290, 1000, 560)
    pygame.draw.rect(surface, CARD_BG, stats_rect, border_radius=20)
    pygame.draw.rect(surface, GRAY, stats_rect, 2, border_radius=20)

    # Health Bar
    pay_pct = int(round(game.health_multiplier() * 100))
    t_h = FONT_MEDIUM.render(f"HEALTH: {game.health}/100  (pay {pay_pct}%)", True, WHITE)
    surface.blit(t_h, (80, 330))
    pygame.draw.rect(surface, DARK_GRAY, (80, 380, 880, 36), border_radius=18)
    h_width = int(880 * (game.health / 100))
    h_color = GREEN if game.health > 50 else (YELLOW if game.health > 25 else RED)
    if h_width > 0:
        pygame.draw.rect(surface, h_color, (80, 380, h_width, 36), border_radius=18)

    # Credit Score Bar (Cap 1000)
    t_c = FONT_MEDIUM.render(f"CREDIT SCORE: {game.credit_score} / 1000  (loans {game.interest_rate():.1%}/qtr)",
                             True, WHITE)
    surface.blit(t_c, (80, 440))
    pygame.draw.rect(surface, DARK_GRAY, (80, 490, 880, 36), border_radius=18)
    c_width = int(880 * (game.credit_score / 1000))
    c_color = GREEN if game.credit_score >= 700 else (YELLOW if game.credit_score >= 500 else RED)
    if c_width > 0:
        pygame.draw.rect(surface, c_color, (80, 490, c_width, 36), border_radius=18)

    # Threshold Warnings
    if game.credit_score < 299 or game.low_credit_turns > 0:
        w_t = FONT_SMALL.render(f"WARNING: IRS SEIZURE RISK ({game.low_credit_turns}/8 strikes)", True, RED)
        surface.blit(w_t, (80, 535))
    if game.health <= 0 or game.zero_health_turns > 0:
        w_h = FONT_SMALL.render(f"WARNING: CRITICAL HEALTH ({game.zero_health_turns}/4 strikes)", True, RED)
        surface.blit(w_h, (80, 560))

    # Financial Details Grid
    fin_items = [
        ("Cash Balance", f"${game.cash:,}", GREEN),
        ("Total Debt", f"${game.debt:,}", RED if game.debt > 0 else GRAY),
        ("Investments", f"${game.investments:,}", BLUE),
        ("Next Qtr Pay / Bills", f"${game.quarterly_income():,} / ${game.living_expense():,}", ACCENT)
    ]

    y_grid = 600
    for i, (label, val, col) in enumerate(fin_items):
        rx = 80 + (i % 2) * 450
        ry = y_grid + (i // 2) * 100
        tl = FONT_REGULAR.render(label, True, GRAY)
        tv = FONT_HEADER.render(val, True, col)
        surface.blit(tl, (rx, ry))
        surface.blit(tv, (rx, ry + 32))

    # Status line
    status = [f"Courses {game.courses_taken}/{game.MAX_COURSES}", "Car: yes" if game.has_car else "Car: NO (-5% pay)"]
    if game.layoff_turns > 0:
        status.append(f"LAID OFF ({int(game.layoff_mult * 100)}% pay, {game.layoff_turns} qtr left)")
    if game.refi_turns > 0:
        status.append(f"Refinanced ({game.refi_turns} qtr left)")
    if game.in_collections:
        status.append("IN COLLECTIONS")
    t_status = FONT_SMALL.render("  |  ".join(status), True, RED if game.in_collections else GRAY)
    surface.blit(t_status, (80, 805))

    # Health Purchase Actions + withdraw
    bw = 320
    buy_h1 = Button(40, 880, bw, 100, f"Buy Groceries (-${game.grocery_cost():,}, Health +20)", GREEN, DARK_GREEN,
                    FONT_REGULAR)
    buy_h1.action = "buy_groceries"
    buy_h1.enabled = game.can_buy_groceries()
    buy_h1.check_hover(mouse_pos)
    buy_h1.draw(surface)
    buttons.append(buy_h1)

    buy_h2 = Button(380, 880, bw, 100, f"Wellness & Spa (-${game.spa_cost():,}, Health +50)", BLUE, DARK_BLUE,
                    FONT_REGULAR)
    buy_h2.action = "buy_spa"
    buy_h2.enabled = game.can_buy_spa()
    buy_h2.check_hover(mouse_pos)
    buy_h2.draw(surface)
    buttons.append(buy_h2)

    fee_pct = int(game.withdraw_penalty_rate() * 100)
    wd_label = f"Withdraw $500 ({fee_pct}% fee)" if fee_pct else "Withdraw $500 (no fee)"
    wd_b = Button(720, 880, bw, 100, wd_label, PURPLE, DARK_BLUE, FONT_REGULAR)
    wd_b.action = "quick_withdraw"
    wd_b.enabled = game.can_withdraw()
    wd_b.check_hover(mouse_pos)
    wd_b.draw(surface)
    buttons.append(wd_b)

    # Debt / Invest Quick Actions
    pay_d = Button(40, 1010, bw, 100, "Pay $500 Debt", ORANGE, DARK_YELLOW, FONT_REGULAR)
    pay_d.action = "quick_pay_debt"
    pay_d.enabled = game.can_pay_debt()
    pay_d.check_hover(mouse_pos)
    pay_d.draw(surface)
    buttons.append(pay_d)

    inv_b = Button(380, 1010, bw, 100, "Invest $500", PURPLE, DARK_BLUE, FONT_REGULAR)
    inv_b.action = "quick_invest"
    inv_b.enabled = game.can_invest()
    inv_b.check_hover(mouse_pos)
    inv_b.draw(surface)
    buttons.append(inv_b)

    bk_label = "Declare Bankruptcy" if game.in_collections else "Bankruptcy (only in collections)"
    bk_b = Button(720, 1010, bw, 100, bk_label, RED, DARK_RED, FONT_REGULAR)
    bk_b.action = "declare_bankruptcy"
    bk_b.enabled = game.can_declare_bankruptcy()
    bk_b.check_hover(mouse_pos)
    bk_b.draw(surface)
    buttons.append(bk_b)

    # Log Panel
    log_rect = pygame.Rect(40, 1140, 1000, 360)
    pygame.draw.rect(surface, CARD_BG, log_rect, border_radius=20)
    pygame.draw.rect(surface, GRAY, log_rect, 2, border_radius=20)

    t_log = FONT_MEDIUM.render("RECENT EVENTS & TRANSACTIONS", True, ACCENT)
    surface.blit(t_log, (70, 1160))

    for i, (txt, col) in enumerate(game.log):
        lt = FONT_REGULAR.render(txt, True, col)
        surface.blit(lt, (70, 1220 + i * 42))

    # Advance Quarter Button
    next_btn = Button(140, 1540, 800, 120, "ADVANCE 3 MONTHS >>", ACCENT, DARK_YELLOW, FONT_TITLE, BLACK)
    next_btn.action = "next_quarter"
    next_btn.check_hover(mouse_pos)
    next_btn.draw(surface)
    buttons.append(next_btn)


def draw_event_screen(surface, game, buttons, mouse_pos):
    # Dark Overlay background
    overlay = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))
    overlay.set_alpha(220)
    overlay.fill((0, 0, 0))
    surface.blit(overlay, (0, 0))

    card_rect = pygame.Rect(50, 300, 980, 1260)
    pygame.draw.rect(surface, CARD_BG, card_rect, border_radius=24)
    pygame.draw.rect(surface, ACCENT, card_rect, 4, border_radius=24)

    # Event Header
    ev_tag = FONT_MEDIUM.render(f"QUARTERLY EVENT - AGE {game.age_years}", True, ACCENT)
    surface.blit(ev_tag, (VIRTUAL_WIDTH // 2 - ev_tag.get_width() // 2, 360))

    title = FONT_TITLE.render(game.current_event["title"], True, WHITE)
    surface.blit(title, (VIRTUAL_WIDTH // 2 - title.get_width() // 2, 440))

    # Description wrapping
    words = game.current_event["desc"].split()
    lines = []
    curr = ""
    for w in words:
        test = curr + (" " if curr else "") + w
        if FONT_MEDIUM.size(test)[0] < 880:
            curr = test
        else:
            lines.append(curr)
            curr = w
    if curr:
        lines.append(curr)

    y = 560
    for line in lines:
        t = FONT_MEDIUM.render(line, True, GRAY)
        surface.blit(t, (VIRTUAL_WIDTH // 2 - t.get_width() // 2, y))
        y += 50

    # Current Stats Summary
    stat_txt = f"Cash: ${game.cash:,}  |  Debt: ${game.debt:,}  |  Health: {game.health}  |  Credit: {game.credit_score}"
    st = FONT_REGULAR.render(stat_txt, True, ACCENT)
    surface.blit(st, (VIRTUAL_WIDTH // 2 - st.get_width() // 2, 1050))

    # Option buttons
    for btn in game.event_buttons:
        btn.check_hover(mouse_pos)
        btn.draw(surface)
        buttons.append(btn)


def draw_game_over_screen(surface, game, buttons, mouse_pos):
    surface.fill(BG_COLOR)

    card_rect = pygame.Rect(70, 250, 940, 1400)
    pygame.draw.rect(surface, CARD_BG, card_rect, border_radius=24)

    if game.death_reason == "RETIREMENT":
        borderColor = ACCENT
        title_text = "HAPPY RETIREMENT!"
        sub_text = "You reached Age 65 safely!"
    elif game.death_reason == "IRS_SEIZURE":
        borderColor = RED
        title_text = "IRS SEIZED YOUR ASSETS!"
        sub_text = "Credit score stayed under 299 for 2 years. You died in prison!"
    else:
        borderColor = RED
        title_text = "HEALTH COLLAPSED!"
        sub_text = "Health stayed at 0 for over a year. You passed away!"

    pygame.draw.rect(surface, borderColor, card_rect, 4, border_radius=24)

    t_main = FONT_TITLE.render(title_text, True, borderColor)
    surface.blit(t_main, (VIRTUAL_WIDTH // 2 - t_main.get_width() // 2, 350))

    t_sub = FONT_MEDIUM.render(sub_text, True, WHITE)
    surface.blit(t_sub, (VIRTUAL_WIDTH // 2 - t_sub.get_width() // 2, 450))

    # Final Score Calculation
    nw = game.get_net_worth()
    final_score = game.final_score()
    if game.death_reason == "RETIREMENT":
        rule = f"x{game.score_multiplier():.2f} (credit)" if nw >= 0 else "x1.00 (in debt)"
    else:
        rule = f"x0.25 - {game.DEATH_PENALTY:,}"

    stats = [
        ("Final Age Reached", f"{game.age_years}", WHITE),
        ("Final Net Worth", f"${nw:,}", GREEN if nw >= 0 else RED),
        ("Final Credit Score", f"{game.credit_score} / 1000", ACCENT),
        ("Remaining Cash", f"${game.cash:,}", GREEN),
        ("Remaining Debt", f"${game.debt:,}", RED if game.debt > 0 else GRAY),
        ("Score Modifier", rule, WHITE if game.death_reason == "RETIREMENT" else RED),
        ("FINAL SCORE", f"{final_score:,} PTS", ACCENT)
    ]

    y = 560
    for label, val, col in stats:
        f_lbl = FONT_TITLE if label == "FINAL SCORE" else FONT_HEADER
        f_val = FONT_TITLE if label == "FINAL SCORE" else FONT_HEADER

        tl = f_lbl.render(label, True, GRAY if label != "FINAL SCORE" else ACCENT)
        tv = f_val.render(val, True, col)

        surface.blit(tl, (120, y))
        surface.blit(tv, (960 - tv.get_width(), y))
        y += 90

    extra = f"Courses: {game.courses_taken}  |  Bankruptcies: {game.bankruptcies}  |  Seed: {game.seed}"
    t_extra = FONT_REGULAR.render(extra, True, GRAY)
    surface.blit(t_extra, (VIRTUAL_WIDTH // 2 - t_extra.get_width() // 2, 1240))

    restart_btn = Button(190, 1420, 700, 120, "PLAY AGAIN", GREEN, DARK_GREEN, FONT_TITLE)
    restart_btn.action = "restart"
    restart_btn.check_hover(mouse_pos)
    restart_btn.draw(surface)
    buttons.append(restart_btn)


def main():
    clock = pygame.time.Clock()
    game = LifeGame()
    running = True
    last_state = game.state
    ignore_clicks_until = 0

    while running:
        mouse_pos = pygame.mouse.get_pos()
        # Scale physical window coordinates back to 1080x1920 virtual surface
        scale_x = VIRTUAL_WIDTH / WINDOW_WIDTH
        scale_y = VIRTUAL_HEIGHT / WINDOW_HEIGHT
        virtual_mouse = (int(mouse_pos[0] * scale_x), int(mouse_pos[1] * scale_y))

        click = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    click = True
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

        if pygame.time.get_ticks() < ignore_clicks_until:
            click = False

        buttons = []
        virtual_surface.fill(BG_COLOR)

        if game.state == "card_prompt":
            draw_card_prompt(virtual_surface, game, buttons, virtual_mouse)

        elif game.state == "main":
            draw_main_dashboard(virtual_surface, game, buttons, virtual_mouse)

        elif game.state == "event":
            draw_main_dashboard(virtual_surface, game, [], virtual_mouse)
            draw_event_screen(virtual_surface, game, buttons, virtual_mouse)

        elif game.state == "game_over":
            draw_game_over_screen(virtual_surface, game, buttons, virtual_mouse)

        # Process clicks (only one button per click)
        for btn in buttons:
            if click and btn.is_clicked(virtual_mouse, click):
                if game.state == "card_prompt":
                    if btn.text == "BEGIN YOUR JOURNEY":
                        game.state = "main"
                        game.add_log("Credit card application approved! Journey begins.", GREEN)

                elif game.state == "main":
                    act = getattr(btn, "action", None)
                    if act == "next_quarter":
                        game.next_turn()
                    elif act == "buy_groceries":
                        game.buy_groceries()
                    elif act == "buy_spa":
                        game.buy_spa()
                    elif act == "quick_pay_debt":
                        game.quick_pay_debt()
                    elif act == "quick_invest":
                        game.quick_invest()
                    elif act == "quick_withdraw":
                        game.quick_withdraw()
                    elif act == "declare_bankruptcy":
                        game.declare_bankruptcy()

                elif game.state == "event":
                    act = getattr(btn, "action", None)
                    if act:
                        game.handle_choice(act)

                elif game.state == "game_over":
                    if getattr(btn, "action", None) == "restart":
                        game.reset()
                        game.state = "main"
                break

        if game.state != last_state:
            ignore_clicks_until = pygame.time.get_ticks() + CLICK_COOLDOWN_MS
            last_state = game.state

        # Scale virtual surface (1080x1920) onto window display with letterboxing / pillarboxing
        window.fill(BLACK)
        scaled_surface = pygame.transform.scale(virtual_surface, (WINDOW_WIDTH, WINDOW_HEIGHT))
        window.blit(scaled_surface, (0, 0))
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
