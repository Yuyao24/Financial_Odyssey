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
    FONT_MEDIUM = pygame.font.SysFont("arial", 34, bold=True)
    FONT_REGULAR = pygame.font.SysFont("arial", 26)
    FONT_SMALL = pygame.font.SysFont("arial", 20)
except:
    FONT_TITLE = pygame.font.Font(None, 64)
    FONT_HEADER = pygame.font.Font(None, 46)
    FONT_MEDIUM = pygame.font.Font(None, 34)
    FONT_REGULAR = pygame.font.Font(None, 26)
    FONT_SMALL = pygame.font.Font(None, 20)

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

        shadow_rect = self.rect.copy()
        shadow_rect.x += 4
        shadow_rect.y += 4
        pygame.draw.rect(surface, (0, 0, 0, 150), shadow_rect, border_radius=16)
        pygame.draw.rect(surface, draw_color, self.rect, border_radius=16)
        pygame.draw.rect(surface, WHITE if self.hovered and self.enabled else draw_color, self.rect, 3,
                         border_radius=16)

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
    START_INCOME = 3200  # Stricter quarterly income
    GROCERY_BASE = 1500  # Compulsory quarterly groceries
    HEALTH_BUY_COST = 1200  # Single option for health ($1200 for +30 Health)
    HEALTH_BUY_HP = 30
    INFLATION_QTR = 0.008  # High price inflation forcing tight money
    RAISE_QTR = 0.003  # Slow income growth

    CREDIT_CARD_LIMIT = 3000  # Initial credit limit
    OVERDRAFT_LIMIT = 1000  # Bank overdraft limit

    INVEST_RANGE = (-0.06, 0.08)
    CRASH_CHANCE = 1 / 25
    CRASH_RANGE = (0.25, 0.45)
    EARLY_WITHDRAW_PENALTY = 0.15
    PENALTY_FREE_AGE = 60

    MAX_COURSES = 5
    COURSE_BASE_COST = 1500
    COURSE_BASE_BONUS = 600

    DEATH_PENALTY = 100_000

    EVENT_DECK = (["medical"] * 3 + ["market"] * 2 + ["car"] * 2 + ["vacation"] * 2 +
                  ["course"] * 2 + ["debt"] * 2 + ["credit_edu"] * 3 + ["layoff"] * 2)

    def __init__(self, seed=None):
        self.reset(seed)

    def reset(self, seed=None):
        self.seed = seed if seed is not None else random.randrange(1_000_000)
        self.rng = random.Random(self.seed)

        self.age_years = 18
        self.age_months = 0
        self.turns_played = 0
        self.cash = 800
        self.credit_score = 550  # Initial score
        self.consecutive_on_time = 0  # Track consistent on-time payments

        self.debt = 0  # Total borrowed debt
        self.investments = 0
        self.health = 100

        self.low_credit_turns = 0
        self.zero_health_turns = 0

        self.state = "card_prompt"  # card_prompt, main, event, game_over
        self.death_reason = ""
        self.log = []
        self.current_event = None
        self.event_costs = {}
        self.event_buttons = []

        self.base_income = self.START_INCOME
        self.price_index = 1.0
        self.wage_index = 1.0

        self.has_car = True
        self.courses_taken = 0
        self.layoff_turns = 0
        self.layoff_mult = 1.0
        self.event_deck = []
        self.early_retire_offered = False

    def get_net_worth(self):
        return self.cash + self.investments - self.debt

    def price(self, amount):
        return int(round(amount * self.price_index))

    def wage(self, amount):
        return int(round(amount * self.wage_index))

    def health_multiplier(self):
        return 0.5 + 0.5 * (self.health / 100)

    def potential_income(self):
        return int(self.base_income * self.wage_index)

    def quarterly_income(self):
        mult = self.health_multiplier() * self.layoff_mult
        if not self.has_car:
            mult *= 0.90
        return int(self.potential_income() * mult)

    def compulsory_groceries(self):
        return self.price(self.GROCERY_BASE)

    def health_cost(self):
        return self.price(self.HEALTH_BUY_COST)

    def health_decay(self):
        return 18 + (12 * (self.age_years - 18)) // 47

    def interest_rate(self):
        if self.credit_score >= 800:
            return 0.03
        if self.credit_score >= 650:
            return 0.05
        if self.credit_score >= 500:
            return 0.075
        return 0.10

    def withdraw_penalty_rate(self):
        return 0.0 if self.age_years >= self.PENALTY_FREE_AGE else self.EARLY_WITHDRAW_PENALTY

    def final_score(self):
        nw = self.get_net_worth()
        if self.death_reason in ("RETIREMENT", "EARLY_RETIREMENT"):
            multiplier = 0.5 + (self.credit_score / 2000)
            return int(nw * multiplier) if nw >= 0 else int(nw)
        return int(min(nw, nw * 0.25) - self.DEATH_PENALTY)

    def add_log(self, text, color=WHITE):
        self.log.append((f"Age {self.age_years} Q{(self.age_months // 3) + 1}: {text}", color))
        if len(self.log) > 6:
            self.log.pop(0)

    def update_credit_on_payment(self, status):
        """
        Improved credit score rules:
        - 5 years history threshold (20 turns): can't exceed 700 before 20 turns.
        - Missing payment: -50 pts
        - Late payment: -20 pts
        - On-time payment: +5 pts initially
        - Consistently on-time: +2 pts per payment after streak
        - Very high score (>=750): +0 or +1 pt max per payment
        - Credit score capped strictly at 1000.
        """
        if status == "missing":
            delta = -50
            self.consecutive_on_time = 0
        elif status == "late":
            delta = -20
            self.consecutive_on_time = 0
        elif status == "on_time":
            self.consecutive_on_time += 1
            if self.credit_score >= 750:
                delta = self.rng.choice([0, 1])
            elif self.consecutive_on_time >= 3:
                delta = 2
            else:
                delta = 5
        else:
            delta = 0

        self.credit_score = max(0, self.credit_score + delta)

        # Credit history cap rule: Can't pass 700 until 5 years of history (20 quarters/turns)
        if self.turns_played < 20 and self.credit_score > 700:
            self.credit_score = 700

        self.credit_score = min(1000, self.credit_score)

    def take_user_loan(self, amount):
        """Allows player to explicitly request a loan."""
        if self.credit_score < 400:
            self.add_log("Loan denied! Credit score below 400.", RED)
            return False
        fee = math.ceil(amount * self.interest_rate())
        self.debt += amount + fee
        self.cash += amount
        self.add_log(f"Took out ${amount:,} bank loan (+${fee:,} fee). Debt +${amount + fee:,}", YELLOW)
        return True

    def repay(self, amount):
        pay = min(amount, self.debt, self.cash)
        if pay <= 0:
            return 0
        self.cash -= pay
        self.debt -= pay
        self.update_credit_on_payment("on_time")
        return pay

    def can_buy_health(self):
        return self.cash >= self.health_cost()

    def buy_health(self):
        if not self.can_buy_health():
            return False
        cost = self.health_cost()
        self.cash -= cost
        self.health = min(100, self.health + self.HEALTH_BUY_HP)
        self.add_log(f"Purchased healthcare & wellness (-${cost:,}, Health +{self.HEALTH_BUY_HP})", GREEN)
        return True

    def can_pay_debt(self):
        return self.debt > 0 and self.cash >= min(500, self.debt)

    def quick_pay_debt(self):
        if not self.can_pay_debt():
            return False
        pay = self.repay(500)
        self.add_log(f"Paid ${pay:,} debt. Credit updated!", GREEN)
        return True

    def can_invest(self):
        return self.cash >= 500

    def quick_invest(self):
        if not self.can_invest():
            return False
        self.cash -= 500
        self.investments += 500
        self.add_log("Invested $500 into Index Funds", BLUE)
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
            self.add_log(f"Withdrew ${amt:,} (early fee -${penalty:,})", ORANGE)
        else:
            self.add_log(f"Withdrew ${amt:,} from investments", BLUE)
        return True

    def next_turn(self):
        self.turns_played += 1
        self.age_months += 3
        if self.age_months >= 12:
            self.age_years += 1
            self.age_months = 0

        # Retirement at 65
        if self.age_years >= 65:
            self.state = "game_over"
            self.death_reason = "RETIREMENT"
            return

        # Check Early Retirement Option if $1 Million reached
        if self.get_net_worth() >= 1_000_000 and not self.early_retire_offered:
            self.early_retire_offered = True

        # Economic scaling
        self.price_index *= 1 + self.INFLATION_QTR
        self.wage_index *= 1 + self.RAISE_QTR

        # Income processing
        earned = self.quarterly_income()
        if self.layoff_turns > 0:
            self.layoff_turns -= 1
            if self.layoff_turns == 0:
                self.layoff_mult = 1.0
                self.add_log("Back on full salary!", GREEN)

        self.cash += earned

        # Compulsory Groceries (Strict financial drain)
        grocery = self.compulsory_groceries()
        if self.cash >= grocery:
            self.cash -= grocery
            self.add_log(f"Paid compulsory groceries (-${grocery:,})", WHITE)
        else:
            # Overdraft / Credit card fallback
            shortfall = grocery - self.cash
            self.cash = 0
            self.debt += shortfall
            self.add_log(f"Overdraft/Credit used for groceries (+${shortfall:,} debt)", RED)

        # Health decay
        self.health = max(0, self.health - self.health_decay())

        # Interest on debt & missed payment handling
        if self.debt > 0:
            rate = self.interest_rate()
            interest = math.ceil(self.debt * rate)
            self.debt += interest
            self.add_log(f"Debt interest +${interest:,} ({rate:.1%})", RED)

            # If debt exceeds credit limit + overdraft ($4,000 baseline), missing payment triggers penalty
            if self.debt > self.CREDIT_CARD_LIMIT + self.OVERDRAFT_LIMIT:
                self.update_credit_on_payment("missing")
                self.add_log("Over credit limit! Missed payment penalty (-50 Credit)", RED)
            else:
                self.update_credit_on_payment("late")
                self.add_log("Unpaid debt carried over (-20 Credit)", ORANGE)

        # Investment returns
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
                    self.add_log(f"Investments dropped by -${abs(change):,}", RED)

        # Check Health death condition
        if self.health <= 0:
            self.zero_health_turns += 1
            if self.zero_health_turns >= 4:
                self.state = "game_over"
                self.death_reason = "HEALTH_FAILURE"
                return
        else:
            self.zero_health_turns = max(0, self.zero_health_turns - 1)

        # IRS Credit death condition (< 299 for 2 years / 8 turns)
        if self.credit_score < 299:
            self.low_credit_turns += 1
            if self.low_credit_turns >= 8:
                self.state = "game_over"
                self.death_reason = "IRS_SEIZURE"
                return
        else:
            self.low_credit_turns = max(0, self.low_credit_turns - 1)

        self.trigger_quarter_event()

    def draw_event_key(self):
        for _ in range(len(self.EVENT_DECK) * 2):
            if not self.event_deck:
                self.event_deck = list(self.EVENT_DECK)
                self.rng.shuffle(self.event_deck)
            key = self.event_deck.pop()
            if key == "debt" and self.debt <= 0:
                continue
            if key == "course" and self.courses_taken >= self.MAX_COURSES:
                continue
            return key
        return "medical"

    def build_event(self, key):
        c = {}
        if key == "credit_edu":
            return c, {
                "title": "Credit Score Workshop",
                "desc": "A local financial workshop explains credit scoring rules:"

                        "• Paying with a credit card does NOT hurt score; only unpaid debt causes penalties."

                        "• Missing a payment: -50 pts | Late payment: -20 pts."

                        "• Score cannot cross 700 until 5 years of history.",
                "options": [
                    ("Attend Workshop (Gain +15 Credit)", "attend_edu"),
                    ("Skip Workshop", "pass")
                ]
            }
        if key == "medical":
            c["med"] = self.price(700)
            skip_hp = 25
            c["skip_hp"] = skip_hp
            return c, {
                "title": "Medical Care",
                "desc": "Unexpected medical treatment is needed.",
                "options": [
                    (f"Pay ${c['med']:,} Cash (Health +25)", "pay_med"),
                    (f"Charge ${c['med']:,} to Credit Card (Health +25)", "debt_med"),
                    (f"Skip treatment (-{skip_hp} Health)", "skip_med")
                ]
            }
        if key == "market":
            c["invest"] = self.price(800)
            c["invest_loan"] = self.price(1500)
            return c, {
                "title": "Stock Market Opportunity",
                "desc": "An index fund opportunity is available.",
                "options": [
                    (f"Invest ${c['invest']:,} in Cash", "invest_index"),
                    (f"Take ${c['invest_loan']:,} Loan to Invest", "loan_invest"),
                    ("Pass on opportunity", "pass")
                ]
            }
        if key == "car" and self.has_car:
            c["car"] = self.price(600)
            c["car_sale"] = self.price(1000)
            return c, {
                "title": "Vehicle Repair",
                "desc": "Your car needs urgent repairs.",
                "options": [
                    (f"Pay ${c['car']:,} cash to fix", "fix_car_cash"),
                    (f"Charge ${c['car']:,} to Credit Card", "fix_car_loan"),
                    (f"Sell car (+${c['car_sale']:,}, -10% Pay)", "sell_car")
                ]
            }
        if key == "car":
            c["used_car"] = self.price(2500)
            return c, {
                "title": "Commute Difficulty",
                "desc": "Taking transit is hurting your work performance.",
                "options": [
                    (f"Buy used car (${c['used_car']:,} Cash)", "buy_car_cash"),
                    (f"Finance used car (${c['used_car']:,} Debt)", "buy_car_loan"),
                    ("Keep taking public transit", "bus")
                ]
            }
        if key == "vacation":
            c["vacation"] = self.price(1200)
            c["extra_work"] = self.wage(500)
            return c, {
                "title": "Vacation Opportunity",
                "desc": "Friends invite you on a trip.",
                "options": [
                    (f"Go on trip (${c['vacation']:,} Cash, +25 HP)", "vacation_cash"),
                    (f"Charge trip to Credit Card (${c['vacation']:,}, +25 HP)", "vacation_loan"),
                    (f"Decline & work extra (+${c['extra_work']:,}, -10 HP)", "vacation_skip")
                ]
            }
        if key == "course":
            c["course"] = self.price(self.COURSE_BASE_COST * (1.4 ** self.courses_taken))
            c["bonus"] = self.COURSE_BASE_BONUS
            bonus_now = self.wage(c["bonus"])
            return c, {
                "title": "Career Course",
                "desc": f"Certification {self.courses_taken + 1}/{self.MAX_COURSES}: boost quarterly salary.",
                "options": [
                    (f"Pay ${c['course']:,} Cash (Income +${bonus_now:,}/qtr)", "course_cash"),
                    (f"Finance ${c['course']:,} on Credit Card", "course_loan"),
                    ("Skip course", "pass")
                ]
            }
        if key == "debt":
            c["pay"] = min(self.debt, self.price(1000))
            return c, {
                "title": "Debt Settlement",
                "desc": "Your bank offers a credit score bonus if you pay off debt now.",
                "options": [
                    (f"Pay ${c['pay']:,} Debt now (+10 Credit)", "pay_debt_now"),
                    ("Pass", "pass")
                ]
            }
        c["severance"] = self.wage(1200)
        return c, {
            "title": "Company Layoff",
            "desc": "Your company is cutting costs.",
            "options": [
                (f"Take severance (+${c['severance']:,}, 50% pay for 2 qtrs)", "layoff_severance"),
                ("Switch to temp role (75% pay for 2 qtrs)", "layoff_temp"),
                ("Pass", "pass")
            ]
        }

    def trigger_quarter_event(self):
        key = self.draw_event_key()
        self.event_costs, self.current_event = self.build_event(key)
        self.state = "event"
        self.build_event_buttons()

    def option_block_reason(self, action):
        c = self.event_costs
        cash_needed = {
            "pay_med": c.get("med"),
            "invest_index": c.get("invest"),
            "fix_car_cash": c.get("car"),
            "buy_car_cash": c.get("used_car"),
            "vacation_cash": c.get("vacation"),
            "course_cash": c.get("course"),
            "pay_debt_now": c.get("pay"),
        }
        need = cash_needed.get(action)
        if need is not None and self.cash < need:
            return f"need ${need:,} cash"
        return None

    def build_event_buttons(self):
        self.event_buttons = []
        options = self.current_event["options"]
        bw, bh = 940, 100
        start_y = 1140
        spacing = 25

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
        c = self.event_costs

        if action == "attend_edu":
            self.update_credit_on_payment("on_time")
            self.add_log("Attended Credit Workshop! Credit +15", GREEN)

        elif action == "pay_med":
            self.cash -= c["med"]
            self.health = min(100, self.health + 25)
            self.add_log(f"Paid ${c['med']:,} medical bill cash. Health +25", GREEN)

        elif action == "debt_med":
            # Paying with credit card DOES NOT lower credit score immediately. Only unpaid debt lowers it later.
            self.debt += c["med"]
            self.health = min(100, self.health + 25)
            self.add_log(f"Charged ${c['med']:,} to credit card. Debt +${c['med']:,}", YELLOW)

        elif action == "skip_med":
            self.health = max(0, self.health - c["skip_hp"])
            self.add_log(f"Skipped care. Health dropped by {c['skip_hp']}", ORANGE)

        elif action == "invest_index":
            self.cash -= c["invest"]
            self.investments += c["invest"]
            self.add_log(f"Invested ${c['invest']:,} in Index Funds", GREEN)

        elif action == "loan_invest":
            fee = math.ceil(c["invest_loan"] * self.interest_rate())
            self.debt += c["invest_loan"] + fee
            self.investments += c["invest_loan"]
            self.add_log(f"Borrowed ${c['invest_loan']:,} to invest. Debt +${c['invest_loan'] + fee:,}", YELLOW)

        elif action == "fix_car_cash":
            self.cash -= c["car"]
            self.add_log(f"Fixed car for ${c['car']:,} cash", GREEN)

        elif action == "fix_car_loan":
            self.debt += c["car"]
            self.add_log(f"Charged car repair (${c['car']:,}) to credit card", YELLOW)

        elif action == "sell_car":
            self.cash += c["car_sale"]
            self.has_car = False
            self.add_log(f"Sold car for ${c['car_sale']:,}. Salary reduced by 10%", YELLOW)

        elif action == "buy_car_cash":
            self.cash -= c["used_car"]
            self.has_car = True
            self.add_log(f"Bought car for ${c['used_car']:,} cash. Full salary restored", GREEN)

        elif action == "buy_car_loan":
            self.debt += c["used_car"]
            self.has_car = True
            self.add_log(f"Financed car (${c['used_car']:,}). Debt +${c['used_car']:,}", YELLOW)

        elif action == "bus":
            self.health = max(0, self.health - 10)
            self.add_log("Stuck with public transit. Health -10", ORANGE)

        elif action == "vacation_cash":
            self.cash -= c["vacation"]
            self.health = min(100, self.health + 25)
            self.add_log(f"Took vacation (${c['vacation']:,} cash). Health +25", GREEN)

        elif action == "vacation_loan":
            self.debt += c["vacation"]
            self.health = min(100, self.health + 25)
            self.add_log(f"Charged vacation (${c['vacation']:,}) to credit card", YELLOW)

        elif action == "vacation_skip":
            self.cash += c["extra_work"]
            self.health = max(0, self.health - 10)
            self.add_log(f"Worked extra shifts (+${c['extra_work']:,}, Health -10)", WHITE)

        elif action in ("course_cash", "course_loan"):
            if action == "course_cash":
                self.cash -= c["course"]
            else:
                self.debt += c["course"]
            self.base_income += c["bonus"]
            self.courses_taken += 1
            self.add_log(f"Completed Course {self.courses_taken}! Salary +${self.wage(c['bonus']):,}/qtr", GREEN)

        elif action == "pay_debt_now":
            pay = self.repay(c["pay"])
            self.update_credit_on_payment("on_time")
            self.add_log(f"Settled ${pay:,} debt! Bonus credit boost", GREEN)

        elif action == "layoff_severance":
            self.cash += c["severance"]
            self.layoff_turns, self.layoff_mult = 2, 0.5
            self.add_log(f"Laid off. Severance +${c['severance']:,}, 50% pay for 2 quarters", ORANGE)

        elif action == "layoff_temp":
            self.layoff_turns, self.layoff_mult = 2, 0.75
            self.add_log("Temp gig: 75% pay for 2 quarters", ORANGE)

        elif action == "pass":
            self.add_log("Passed on event option.", WHITE)

        self.state = "main"
        return True


def draw_card_prompt(surface, game, buttons, mouse_pos):
    surface.fill(BG_COLOR)

    card_rect = pygame.Rect(70, 260, 940, 1200)
    pygame.draw.rect(surface, CARD_BG, card_rect, border_radius=24)
    pygame.draw.rect(surface, ACCENT, card_rect, 4, border_radius=24)

    ts = FONT_TITLE.render("WELCOME TO LIFE", True, ACCENT)
    tr = ts.get_rect(center=(VIRTUAL_WIDTH // 2, 340))
    surface.blit(ts, tr)

    subtitle = FONT_HEADER.render("Financial Odyssey (18 - 65)", True, WHITE)
    sr = subtitle.get_rect(center=(VIRTUAL_WIDTH // 2, 420))
    surface.blit(subtitle, sr)

    msg_lines = [
        "Congratulations! You turn 18 today.",
        "You have APPLIED FOR YOUR FIRST CREDIT CARD!",
        "",
        "--- KEY RULES & CHECKLIST UPDATES ---",
        "• Turn duration: 1 turn = 3 Months (18 to 65).",
        "• Compulsory Expenses: Groceries billed automatically.",
        "• Single Health Buy: $1,200 for +30 Health.",
        "• Paying with Credit Card does NOT drop score.",
        "  Score drops only when debt is carried or missed!",
        "• Credit Score limits:",
        "  - Missed payment: -50 pts | Unpaid debt: -20 pts",
        "  - Max 700 score before 5 years of history.",
        "  - On-time payments boost score (Capped at 1000).",
        "• Early Retirement: Available once reaching $1M Net Worth!",
        "• Credit < 299 for 2 yrs or 0 Health for 1 yr = DEATH"
    ]

    y = 500
    for line in msg_lines:
        color = ACCENT if "---" in line else (GREEN if "APPLIED" in line else WHITE)
        font = FONT_MEDIUM if "---" in line or "APPLIED" in line else FONT_REGULAR
        t = font.render(line, True, color)
        r = t.get_rect(center=(VIRTUAL_WIDTH // 2, y))
        surface.blit(t, r)
        y += 45

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
    t_h = FONT_MEDIUM.render(f"HEALTH: {game.health}/100 (Work Efficiency: {pay_pct}%)", True, WHITE)
    surface.blit(t_h, (80, 330))
    pygame.draw.rect(surface, DARK_GRAY, (80, 375, 880, 34), border_radius=17)
    h_width = int(880 * (game.health / 100))
    h_color = GREEN if game.health > 50 else (YELLOW if game.health > 25 else RED)
    if h_width > 0:
        pygame.draw.rect(surface, h_color, (80, 375, h_width, 34), border_radius=17)

    # Credit Score Bar (Capped at 1000)
    history_note = " (Under 5yr Limit: Max 700)" if game.turns_played < 20 else ""
    t_c = FONT_MEDIUM.render(f"CREDIT SCORE: {game.credit_score} / 1000{history_note}", True, WHITE)
    surface.blit(t_c, (80, 435))
    pygame.draw.rect(surface, DARK_GRAY, (80, 480, 880, 34), border_radius=17)
    c_width = int(880 * (game.credit_score / 1000))
    c_color = GREEN if game.credit_score >= 700 else (YELLOW if game.credit_score >= 500 else RED)
    if c_width > 0:
        pygame.draw.rect(surface, c_color, (80, 480, c_width, 34), border_radius=17)

    # Threshold Warnings
    if game.credit_score < 299 or game.low_credit_turns > 0:
        w_t = FONT_SMALL.render(f"WARNING: IRS SEIZURE RISK ({game.low_credit_turns}/8 strikes)", True, RED)
        surface.blit(w_t, (80, 525))
    if game.health <= 0 or game.zero_health_turns > 0:
        w_h = FONT_SMALL.render(f"WARNING: CRITICAL HEALTH ({game.zero_health_turns}/4 strikes)", True, RED)
        surface.blit(w_h, (80, 545))

    # Financial Details Grid
    fin_items = [
        ("Cash Balance", f"${game.cash:,}", GREEN),
        ("Total Debt", f"${game.debt:,}", RED if game.debt > 0 else GRAY),
        ("Investments", f"${game.investments:,}", BLUE),
        ("Qtr Pay / Groceries", f"${game.quarterly_income():,} / ${game.compulsory_groceries():,}", ACCENT)
    ]

    y_grid = 585
    for i, (label, val, col) in enumerate(fin_items):
        rx = 80 + (i % 2) * 450
        ry = y_grid + (i // 2) * 95
        tl = FONT_REGULAR.render(label, True, GRAY)
        tv = FONT_HEADER.render(val, True, col)
        surface.blit(tl, (rx, ry))
        surface.blit(tv, (rx, ry + 30))

    # Credit limit & Overdraft status
    status = [f"Credit Limit: ${game.CREDIT_CARD_LIMIT:,}", f"Overdraft: ${game.OVERDRAFT_LIMIT:,}"]
    if game.early_retire_offered:
        status.append("EARLY RETIREMENT AVAILABLE!")
    t_status = FONT_SMALL.render("  |  ".join(status), True, ACCENT if game.early_retire_offered else GRAY)
    surface.blit(t_status, (80, 785))

    # Single Option to Buy Health
    bw = 460
    buy_h = Button(40, 860, bw, 95, f"Buy Healthcare (-${game.health_cost():,}, Health +30)", GREEN, DARK_GREEN,
                   FONT_REGULAR)
    buy_h.action = "buy_health"
    buy_h.enabled = game.can_buy_health()
    buy_h.check_hover(mouse_pos)
    buy_h.draw(surface)
    buttons.append(buy_h)

    # Get a Bank Loan
    loan_b = Button(540, 860, bw, 95, "Take $1,000 Bank Loan", YELLOW, DARK_YELLOW, FONT_REGULAR, BLACK)
    loan_b.action = "get_loan"
    loan_b.enabled = game.credit_score >= 400
    loan_b.check_hover(mouse_pos)
    loan_b.draw(surface)
    buttons.append(loan_b)

    # Debt / Invest Quick Actions
    pay_d = Button(40, 970, bw, 95, "Pay $500 Debt", ORANGE, DARK_YELLOW, FONT_REGULAR)
    pay_d.action = "quick_pay_debt"
    pay_d.enabled = game.can_pay_debt()
    pay_d.check_hover(mouse_pos)
    pay_d.draw(surface)
    buttons.append(pay_d)

    inv_b = Button(540, 970, bw, 95, "Invest $500", PURPLE, DARK_BLUE, FONT_REGULAR)
    inv_b.action = "quick_invest"
    inv_b.enabled = game.can_invest()
    inv_b.check_hover(mouse_pos)
    inv_b.draw(surface)
    buttons.append(inv_b)

    # Log Panel
    log_rect = pygame.Rect(40, 1100, 1000, 360)
    pygame.draw.rect(surface, CARD_BG, log_rect, border_radius=20)
    pygame.draw.rect(surface, GRAY, log_rect, 2, border_radius=20)

    t_log = FONT_MEDIUM.render("RECENT EVENTS & TRANSACTIONS", True, ACCENT)
    surface.blit(t_log, (70, 1120))

    for i, (txt, col) in enumerate(game.log):
        lt = FONT_REGULAR.render(txt, True, col)
        surface.blit(lt, (70, 1175 + i * 40))

    # Early Retirement button if eligible
    if game.early_retire_offered:
        retire_btn = Button(40, 1480, 1000, 70, "RETIRE EARLY ($1M+ REACHED!)", ACCENT, DARK_YELLOW, FONT_HEADER, BLACK)
        retire_btn.action = "early_retire"
        retire_btn.check_hover(mouse_pos)
        retire_btn.draw(surface)
        buttons.append(retire_btn)

    # Advance Quarter Button
    next_btn = Button(140, 1570, 800, 110, "ADVANCE 3 MONTHS >>", ACCENT, DARK_YELLOW, FONT_TITLE, BLACK)
    next_btn.action = "next_quarter"
    next_btn.check_hover(mouse_pos)
    next_btn.draw(surface)
    buttons.append(next_btn)


def draw_event_screen(surface, game, buttons, mouse_pos):
    overlay = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))
    overlay.set_alpha(220)
    overlay.fill((0, 0, 0))
    surface.blit(overlay, (0, 0))

    card_rect = pygame.Rect(50, 280, 980, 1300)
    pygame.draw.rect(surface, CARD_BG, card_rect, border_radius=24)
    pygame.draw.rect(surface, ACCENT, card_rect, 4, border_radius=24)

    ev_tag = FONT_MEDIUM.render(f"QUARTERLY EVENT - AGE {game.age_years}", True, ACCENT)
    surface.blit(ev_tag, (VIRTUAL_WIDTH // 2 - ev_tag.get_width() // 2, 330))

    title = FONT_TITLE.render(game.current_event["title"], True, WHITE)
    surface.blit(title, (VIRTUAL_WIDTH // 2 - title.get_width() // 2, 410))

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

    y = 510
    for line in lines:
        t = FONT_MEDIUM.render(line, True, GRAY)
        surface.blit(t, (VIRTUAL_WIDTH // 2 - t.get_width() // 2, y))
        y += 45

    stat_txt = f"Cash: ${game.cash:,}  |  Debt: ${game.debt:,}  |  Health: {game.health}  |  Credit: {game.credit_score}"
    st = FONT_REGULAR.render(stat_txt, True, ACCENT)
    surface.blit(st, (VIRTUAL_WIDTH // 2 - st.get_width() // 2, 1050))

    for btn in game.event_buttons:
        btn.check_hover(mouse_pos)
        btn.draw(surface)
        buttons.append(btn)


def draw_game_over_screen(surface, game, buttons, mouse_pos):
    surface.fill(BG_COLOR)

    card_rect = pygame.Rect(70, 250, 940, 1400)
    pygame.draw.rect(surface, CARD_BG, card_rect, border_radius=24)

    if game.death_reason in ("RETIREMENT", "EARLY_RETIREMENT"):
        borderColor = ACCENT
        title_text = "CONGRATULATIONS!"
        sub_text = "Early Retirement Achieved!" if game.death_reason == "EARLY_RETIREMENT" else "You reached Age 65 safely!"
    elif game.death_reason == "IRS_SEIZURE":
        borderColor = RED
        title_text = "IRS SEIZED YOUR ASSETS!"
        sub_text = "Credit score stayed under 299 for 2 years. Bankrupt & Bankrupt!"
    else:
        borderColor = RED
        title_text = "HEALTH COLLAPSED!"
        sub_text = "Health stayed at 0 for too long."

    pygame.draw.rect(surface, borderColor, card_rect, 4, border_radius=24)

    t_main = FONT_TITLE.render(title_text, True, borderColor)
    surface.blit(t_main, (VIRTUAL_WIDTH // 2 - t_main.get_width() // 2, 340))

    t_sub = FONT_MEDIUM.render(sub_text, True, WHITE)
    surface.blit(t_sub, (VIRTUAL_WIDTH // 2 - t_sub.get_width() // 2, 440))

    nw = game.get_net_worth()
    final_score = game.final_score()

    stats = [
        ("Final Age Reached", f"{game.age_years}", WHITE),
        ("Final Net Worth", f"${nw:,}", GREEN if nw >= 0 else RED),
        ("Final Credit Score", f"{game.credit_score} / 1000", ACCENT),
        ("Remaining Cash", f"${game.cash:,}", GREEN),
        ("Remaining Debt", f"${game.debt:,}", RED if game.debt > 0 else GRAY),
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
                    elif act == "buy_health":
                        game.buy_health()
                    elif act == "get_loan":
                        game.take_user_loan(1000)
                    elif act == "quick_pay_debt":
                        game.quick_pay_debt()
                    elif act == "quick_invest":
                        game.quick_invest()
                    elif act == "early_retire":
                        game.state = "game_over"
                        game.death_reason = "EARLY_RETIREMENT"

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

        window.fill(BLACK)
        scaled_surface = pygame.transform.scale(virtual_surface, (WINDOW_WIDTH, WINDOW_HEIGHT))
        window.blit(scaled_surface, (0, 0))
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()