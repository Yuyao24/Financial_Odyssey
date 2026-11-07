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
    FONT_TITLE = pygame.font.SysFont("arial", 60, bold=True)
    FONT_HEADER = pygame.font.SysFont("arial", 42, bold=True)
    FONT_MEDIUM = pygame.font.SysFont("arial", 32, bold=True)
    FONT_REGULAR = pygame.font.SysFont("arial", 24)
    FONT_SMALL = pygame.font.SysFont("arial", 19)
except:
    FONT_TITLE = pygame.font.Font(None, 60)
    FONT_HEADER = pygame.font.Font(None, 42)
    FONT_MEDIUM = pygame.font.Font(None, 32)
    FONT_REGULAR = pygame.font.Font(None, 24)
    FONT_SMALL = pygame.font.Font(None, 19)

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
        pygame.draw.rect(surface, WHITE if self.hovered and self.enabled else draw_color, self.rect, 3, border_radius=16)

        words = self.text.split()
        lines = []
        curr_line = ""
        for w in words:
            test = curr_line + (" " if curr_line else "") + w
            if self.font.size(test)[0] < self.rect.width - 25:
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
    START_INCOME = 3500            # Quarterly income
    GROCERY_BASE = 1400           # Compulsory quarterly expenses
    HAPPINESS_BUY_COST = 800       # Option to boost happiness ($800 for +30 Happiness)
    HAPPINESS_BUY_PTS = 30
    INFLATION_QTR = 0.007          # Quarterly inflation
    RAISE_QTR = 0.003              # Slow income growth
    
    CREDIT_CARD_LIMIT = 3000       # Initial credit limit
    OVERDRAFT_LIMIT = 1000         # Bank overdraft limit

    INVEST_RANGE = (-0.05, 0.08)
    CRASH_CHANCE = 1 / 25
    CRASH_RANGE = (0.20, 0.40)
    EARLY_WITHDRAW_PENALTY = 0.05

    MAX_COURSES = 5
    COURSE_BASE_COST = 1400
    COURSE_BASE_BONUS = 600

    DEATH_PENALTY = 100_000

    EVENT_DECK = (["leisure"] * 3 + ["market"] * 2 + ["car"] * 2 + ["vacation"] * 2 +
                  ["course"] * 2 + ["debt"] * 2 + ["credit_edu"] * 3 + ["layoff"] * 2)

    def __init__(self, seed=None):
        self.reset(seed)

    def reset(self, seed=None):
        self.seed = seed if seed is not None else random.randrange(1_000_000)
        self.rng = random.Random(self.seed)

        self.age_years = 18
        self.age_months = 0
        self.turns_played = 0
        self.cash = 1000
        self.credit_score = 550      # Initial score
        self.consecutive_on_time = 0
        
        self.debt = 0                # Total borrowed debt
        self.investments = 0
        self.happiness = 100         # Changed from Health to Happiness!

        self.low_credit_turns = 0
        self.zero_happiness_turns = 0

        self.state = "card_prompt"   # card_prompt, main, event, game_over
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

    def potential_income(self):
        return int(self.base_income * self.wage_index)

    def quarterly_income(self):
        # NO income penalty for low happiness! Income is purely based on salary & car status.
        mult = self.layoff_mult
        if not self.has_car:
            mult *= 0.90
        return int(self.potential_income() * mult)

    def compulsory_groceries(self):
        return self.price(self.GROCERY_BASE)

    def happiness_cost(self):
        return self.price(self.HAPPINESS_BUY_COST)

    def happiness_decay(self):
        # Work stress & life wear decay quarterly happiness
        return 15 + (10 * (self.age_years - 18)) // 47

    def interest_rate(self):
        """
        Adjusted quarterly interest rates (converted from annual rates for 3-month turns):
        - Excellent (800+): 0.75% / qtr (~3.0% APR)
        - Good (650-799): 1.25% / qtr (~5.0% APR)
        - Fair (500-649): 2.00% / qtr (~8.0% APR)
        - Poor (<500): 3.25% / qtr (~13.0% APR)
        """
        if self.credit_score >= 800:
            return 0.0075
        if self.credit_score >= 650:
            return 0.0125
        if self.credit_score >= 500:
            return 0.0200
        return 0.0325

    def withdraw_penalty_rate(self):
        return self.EARLY_WITHDRAW_PENALTY

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
        
        # Credit history cap rule: Can't pass 700 until 5 years of history (20 turns)
        if self.turns_played < 20 and self.credit_score > 700:
            self.credit_score = 700
            
        self.credit_score = min(1000, self.credit_score)

    def take_user_loan(self, amount):
        if self.credit_score < 400:
            self.add_log("Loan denied! Credit score below 400.", RED)
            return False
        fee = math.ceil(amount * self.interest_rate())
        self.debt += amount + fee
        self.cash += amount
        self.add_log(f"Took out ${amount:,} bank loan (+${fee:,} fee). Debt +${amount+fee:,}", YELLOW)
        return True

    def repay(self, amount):
        pay = min(amount, self.debt, self.cash)
        if pay <= 0:
            return 0
        self.cash -= pay
        self.debt -= pay
        self.update_credit_on_payment("on_time")
        return pay

    def can_buy_happiness(self):
        return self.cash >= self.happiness_cost()

    def buy_happiness(self):
        if not self.can_buy_happiness():
            return False
        cost = self.happiness_cost()
        self.cash -= cost
        self.happiness = min(100, self.happiness + self.HAPPINESS_BUY_PTS)
        self.add_log(f"Purchased leisure & hobbies (-${cost:,}, Happiness +{self.HAPPINESS_BUY_PTS})", GREEN)
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
        self.add_log("Invested $500 into Stock Market", BLUE)
        return True

    def can_withdraw(self):
        return self.investments > 0

    def quick_withdraw(self, amount=500):
        if not self.can_withdraw():
            return False
        amt = min(amount, self.investments)
        penalty = int(amt * self.withdraw_penalty_rate())
        self.investments -= amt
        self.cash += (amt - penalty)
        if penalty > 0:
            self.add_log(f"Retrieved ${amt-penalty:,} from investments (fee: -${penalty:,})", ORANGE)
        else:
            self.add_log(f"Retrieved ${amt:,} from investments", BLUE)
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

        # Early Retirement Option if $1 Million net worth reached
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

        # Compulsory Groceries & Essentials
        grocery = self.compulsory_groceries()
        if self.cash >= grocery:
            self.cash -= grocery
            self.add_log(f"Paid compulsory living costs (-${grocery:,})", WHITE)
        else:
            shortfall = grocery - self.cash
            self.cash = 0
            self.debt += shortfall
            self.add_log(f"Overdraft/Credit used for essentials (+${shortfall:,} debt)", RED)

        # Passive Happiness decay
        self.happiness = max(0, self.happiness - self.happiness_decay())

        # Interest on debt & missed payment handling
        if self.debt > 0:
            rate = self.interest_rate()
            interest = math.ceil(self.debt * rate)
            self.debt += interest
            self.add_log(f"Quarterly Interest +${interest:,} ({rate:.2%}/qtr)", RED)
            
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
                self.add_log(f"MARKET CRASH! Investments dropped ${abs(change):,}", RED)
            else:
                growth = self.rng.uniform(*self.INVEST_RANGE)
                change = int(self.investments * growth)
                self.investments = max(0, self.investments + change)
                if change >= 0:
                    self.add_log(f"Investments grew by +${change:,}", GREEN)
                else:
                    self.add_log(f"Investments dropped by -${abs(change):,}", RED)

        # Happiness check: Dying of DEPRESSION if happiness remains 0 for 4 quarters (1 year)
        if self.happiness <= 0:
            self.zero_happiness_turns += 1
            if self.zero_happiness_turns >= 4:
                self.state = "game_over"
                self.death_reason = "DEPRESSION"
                return
        else:
            self.zero_happiness_turns = max(0, self.zero_happiness_turns - 1)

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
        return "leisure"

    def build_event(self, key):
        c = {}
        if key == "credit_edu":
            return c, {
                "title": "Credit Score Workshop",
                "desc": "A workshop explains credit rules:"
                        "• High Score Benefits: Lower loan interest (~0.75%/qtr) & higher score bonus."
                        "• Low Score Drawbacks: Higher interest (~3.25%/qtr), loan rejections, IRS seizure."
                        "• How to Improve: Pay debt on time (+5 pts), maintain streaks (+2 pts), & avoid missing payments (-50 pts).",
                "options": [
                    ("Attend Workshop (Gain +15 Credit)", "attend_edu"),
                    ("Skip Workshop", "pass")
                ]
            }
        if key == "leisure":
            c["cost"] = self.price(500)
            skip_hp = 20
            c["skip_hp"] = skip_hp
            return c, {
                "title": "Weekend Getaway & Festival",
                "desc": "Your friends are planning a music festival trip to recharge and relax.",
                "options": [
                    (f"Pay ${c['cost']:,} Cash (Happiness +25)", "pay_leisure"),
                    (f"Charge ${c['cost']:,} to Credit Card (Happiness +25)", "debt_leisure"),
                    (f"Skip trip (-{skip_hp} Happiness)", "skip_leisure")
                ]
            }
        if key == "market":
            c["invest"] = self.price(800)
            c["invest_loan"] = self.price(1500)
            return c, {
                "title": "Stock Market Opportunity",
                "desc": "An index fund investment opportunity is available.",
                "options": [
                    (f"Invest ${c['invest']:,} Cash", "invest_index"),
                    (f"Take ${c['invest_loan']:,} Bank Loan to Invest", "loan_invest"),
                    ("Pass on opportunity", "pass")
                ]
            }
        if key == "car" and self.has_car:
            c["car"] = self.price(600)
            c["car_sale"] = self.price(1000)
            return c, {
                "title": "Vehicle Repair",
                "desc": "Your car transmission needs maintenance.",
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
                "desc": "Public transit delays are frustrating your daily schedule.",
                "options": [
                    (f"Buy used car (${c['used_car']:,} Cash)", "buy_car_cash"),
                    (f"Finance used car (${c['used_car']:,} Debt)", "buy_car_loan"),
                    ("Keep taking transit (-10 Happiness)", "bus")
                ]
            }
        if key == "vacation":
            c["vacation"] = self.price(1200)
            c["extra_work"] = self.wage(500)
            return c, {
                "title": "Tropical Resort Vacation",
                "desc": "You have an opportunity to book a relaxing beach vacation.",
                "options": [
                    (f"Book trip (${c['vacation']:,} Cash, +35 Happiness)", "vacation_cash"),
                    (f"Charge trip to Credit Card (${c['vacation']:,}, +35 Happiness)", "vacation_loan"),
                    (f"Decline & work overtime (+${c['extra_work']:,}, -15 Happiness)", "vacation_skip")
                ]
            }
        if key == "course":
            c["course"] = self.price(self.COURSE_BASE_COST * (1.4 ** self.courses_taken))
            c["bonus"] = self.COURSE_BASE_BONUS
            bonus_now = self.wage(c["bonus"])
            return c, {
                "title": "Career Certification",
                "desc": f"Certification {self.courses_taken+1}/{self.MAX_COURSES}: permanently boost your quarterly salary.",
                "options": [
                    (f"Pay ${c['course']:,} Cash (Income +${bonus_now:,}/qtr)", "course_cash"),
                    (f"Finance ${c['course']:,} on Credit Card", "course_loan"),
                    ("Skip course", "pass")
                ]
            }
        if key == "debt":
            c["pay"] = min(self.debt, self.price(1000))
            return c, {
                "title": "Debt Settlement Offer",
                "desc": "Your bank offers a credit score bonus if you pay off debt now.",
                "options": [
                    (f"Pay ${c['pay']:,} Debt now (+10 Credit)", "pay_debt_now"),
                    ("Pass", "pass")
                ]
            }
        c["severance"] = self.wage(1200)
        return c, {
            "title": "Company Layoff",
            "desc": "Your company is downsizing staff.",
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
            "pay_leisure": c.get("cost"),
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
        bw, bh = 940, 95
        start_y = 1150
        spacing = 20

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

        elif action == "pay_leisure":
            self.cash -= c["cost"]
            self.happiness = min(100, self.happiness + 25)
            self.add_log(f"Paid ${c['cost']:,} for weekend trip. Happiness +25", GREEN)

        elif action == "debt_leisure":
            self.debt += c["cost"]
            self.happiness = min(100, self.happiness + 25)
            self.add_log(f"Charged ${c['cost']:,} trip to credit card. Debt +${c['cost']:,}", YELLOW)

        elif action == "skip_leisure":
            self.happiness = max(0, self.happiness - c["skip_hp"])
            self.add_log(f"Skipped trip. Happiness dropped by {c['skip_hp']}", ORANGE)

        elif action == "invest_index":
            self.cash -= c["invest"]
            self.investments += c["invest"]
            self.add_log(f"Invested ${c['invest']:,} in Index Funds", GREEN)

        elif action == "loan_invest":
            fee = math.ceil(c["invest_loan"] * self.interest_rate())
            self.debt += c["invest_loan"] + fee
            self.investments += c["invest_loan"]
            self.add_log(f"Borrowed ${c['invest_loan']:,} to invest. Debt +${c['invest_loan']+fee:,}", YELLOW)

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
            self.happiness = max(0, self.happiness - 10)
            self.add_log("Stuck with public transit. Happiness -10", ORANGE)

        elif action == "vacation_cash":
            self.cash -= c["vacation"]
            self.happiness = min(100, self.happiness + 35)
            self.add_log(f"Took vacation (${c['vacation']:,} cash). Happiness +35", GREEN)

        elif action == "vacation_loan":
            self.debt += c["vacation"]
            self.happiness = min(100, self.happiness + 35)
            self.add_log(f"Charged vacation (${c['vacation']:,}) to credit card", YELLOW)

        elif action == "vacation_skip":
            self.cash += c["extra_work"]
            self.happiness = max(0, self.happiness - 15)
            self.add_log(f"Worked extra shifts (+${c['extra_work']:,}, Happiness -15)", WHITE)

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

    card_rect = pygame.Rect(70, 240, 940, 1240)
    pygame.draw.rect(surface, CARD_BG, card_rect, border_radius=24)
    pygame.draw.rect(surface, ACCENT, card_rect, 4, border_radius=24)

    ts = FONT_TITLE.render("WELCOME TO LIFE", True, ACCENT)
    tr = ts.get_rect(center=(VIRTUAL_WIDTH // 2, 310))
    surface.blit(ts, tr)

    subtitle = FONT_HEADER.render("Financial Odyssey (18 - 65)", True, WHITE)
    sr = subtitle.get_rect(center=(VIRTUAL_WIDTH // 2, 380))
    surface.blit(subtitle, sr)

    msg_lines = [
        "Congratulations! You turn 18 today.",
        "You have APPLIED FOR YOUR FIRST CREDIT CARD!",
        "",
        "--- GAME RULES & CREDIT GUIDE ---",
        "• Turn duration: 1 turn = 3 Months (18 to 65).",
        "• Happiness System: Spend cash on leisure to maintain happiness.",
        "  (0 Happiness for 1 year = DEATH BY DEPRESSION)",
        "• Income: Salary is NOT penalized by low happiness.",
        "• Credit Score Guide:",
        "  - High Credit: Low loan interest (~0.75%/qtr) & higher score bonus.",
        "  - Low Credit: High interest (~3.25%/qtr), loan rejection, IRS seizure.",
        "  - How to improve: Pay debt on time (+5 pts), streaks (+2 pts).",
        "  - Penalties: Missed payment (-50 pts), carrying debt (-20 pts).",
        "  - 5-Year History Cap: Credit score capped at 700 for first 5 years.",
        "• Retrieve Investment: Pull cash out of investments anytime ($500 button).",
        "• Early Retirement: Retire anytime once Net Worth reaches $1,000,000!"
    ]

    y = 450
    for line in msg_lines:
        color = ACCENT if "---" in line else (GREEN if "APPLIED" in line else WHITE)
        font = FONT_MEDIUM if "---" in line or "APPLIED" in line else FONT_REGULAR
        t = font.render(line, True, color)
        r = t.get_rect(center=(VIRTUAL_WIDTH // 2, y))
        surface.blit(t, r)
        y += 42

    start_btn = Button(190, 1500, 700, 110, "BEGIN YOUR JOURNEY", GREEN, DARK_GREEN, FONT_TITLE)
    start_btn.check_hover(mouse_pos)
    start_btn.draw(surface)
    buttons.append(start_btn)


def draw_main_dashboard(surface, game, buttons, mouse_pos):
    surface.fill(BG_COLOR)

    # Top Header Panel
    header_rect = pygame.Rect(40, 30, 1000, 200)
    pygame.draw.rect(surface, CARD_BG, header_rect, border_radius=20)
    pygame.draw.rect(surface, GRAY, header_rect, 2, border_radius=20)

    qtr = (game.age_months // 3) + 1
    t_age = FONT_TITLE.render(f"AGE: {game.age_years} (Q{qtr})", True, ACCENT)
    surface.blit(t_age, (70, 55))

    t_nw = FONT_HEADER.render(f"Net Worth: ${game.get_net_worth():,}", True,
                              GREEN if game.get_net_worth() >= 0 else RED)
    surface.blit(t_nw, (70, 140))

    # Stats Panel
    stats_rect = pygame.Rect(40, 250, 1000, 560)
    pygame.draw.rect(surface, CARD_BG, stats_rect, border_radius=20)
    pygame.draw.rect(surface, GRAY, stats_rect, 2, border_radius=20)

    # Happiness Bar (Replaced Health)
    t_h = FONT_MEDIUM.render(f"HAPPINESS: {game.happiness}/100", True, WHITE)
    surface.blit(t_h, (80, 285))
    pygame.draw.rect(surface, DARK_GRAY, (80, 325, 880, 32), border_radius=16)
    h_width = int(880 * (game.happiness / 100))
    h_color = GREEN if game.happiness > 50 else (YELLOW if game.happiness > 25 else RED)
    if h_width > 0:
        pygame.draw.rect(surface, h_color, (80, 325, h_width, 32), border_radius=16)

    # Credit Score Bar (Capped at 1000)
    history_note = " (5yr Cap: Max 700)" if game.turns_played < 20 else ""
    rate_str = f"Loan Rate: {game.interest_rate():.2%}/qtr"
    t_c = FONT_MEDIUM.render(f"CREDIT SCORE: {game.credit_score}/1000{history_note}  [{rate_str}]", True, WHITE)
    surface.blit(t_c, (80, 380))
    pygame.draw.rect(surface, DARK_GRAY, (80, 420, 880, 32), border_radius=16)
    c_width = int(880 * (game.credit_score / 1000))
    c_color = GREEN if game.credit_score >= 700 else (YELLOW if game.credit_score >= 500 else RED)
    if c_width > 0:
        pygame.draw.rect(surface, c_color, (80, 420, c_width, 32), border_radius=16)

    # Threshold Warnings
    if game.credit_score < 299 or game.low_credit_turns > 0:
        w_t = FONT_SMALL.render(f"WARNING: IRS SEIZURE RISK ({game.low_credit_turns}/8 strikes)", True, RED)
        surface.blit(w_t, (80, 462))
    if game.happiness <= 0 or game.zero_happiness_turns > 0:
        w_h = FONT_SMALL.render(f"WARNING: CRITICAL DEPRESSION ({game.zero_happiness_turns}/4 strikes)", True, RED)
        surface.blit(w_h, (80, 482))

    # Financial Details Grid
    fin_items = [
        ("Cash Balance", f"${game.cash:,}", GREEN),
        ("Total Debt", f"${game.debt:,}", RED if game.debt > 0 else GRAY),
        ("Investments", f"${game.investments:,}", BLUE),
        ("Qtr Pay / Essentials", f"${game.quarterly_income():,} / ${game.compulsory_groceries():,}", ACCENT)
    ]

    y_grid = 520
    for i, (label, val, col) in enumerate(fin_items):
        rx = 80 + (i % 2) * 450
        ry = y_grid + (i // 2) * 90
        tl = FONT_REGULAR.render(label, True, GRAY)
        tv = FONT_HEADER.render(val, True, col)
        surface.blit(tl, (rx, ry))
        surface.blit(tv, (rx, ry + 28))

    # Credit limit status
    status = [f"Credit Limit: ${game.CREDIT_CARD_LIMIT:,}", f"Overdraft Limit: ${game.OVERDRAFT_LIMIT:,}"]
    if game.early_retire_offered:
        status.append("EARLY RETIREMENT READY!")
    t_status = FONT_SMALL.render("  |  ".join(status), True, ACCENT if game.early_retire_offered else GRAY)
    surface.blit(t_status, (80, 750))

    # Action Buttons Grid
    bw = 460
    bh = 85
    
    # Row 1: Happiness & Retrieve Investment Buttons
    buy_h = Button(40, 830, bw, bh, f"Buy Leisure/Hobbies (-${game.happiness_cost():,}, +30 HP)", GREEN, DARK_GREEN, FONT_REGULAR)
    buy_h.action = "buy_happiness"
    buy_h.enabled = game.can_buy_happiness()
    buy_h.check_hover(mouse_pos)
    buy_h.draw(surface)
    buttons.append(buy_h)

    ret_inv = Button(540, 830, bw, bh, "Retrieve $500 Investment", PURPLE, DARK_BLUE, FONT_REGULAR)
    ret_inv.action = "quick_withdraw"
    ret_inv.enabled = game.can_withdraw()
    ret_inv.check_hover(mouse_pos)
    ret_inv.draw(surface)
    buttons.append(ret_inv)

    # Row 2: Take Bank Loan & Pay Debt
    loan_b = Button(40, 930, bw, bh, "Take $1,000 Bank Loan", YELLOW, DARK_YELLOW, FONT_REGULAR, BLACK)
    loan_b.action = "get_loan"
    loan_b.enabled = game.credit_score >= 400
    loan_b.check_hover(mouse_pos)
    loan_b.draw(surface)
    buttons.append(loan_b)

    pay_d = Button(540, 930, bw, bh, "Pay $500 Debt", ORANGE, DARK_YELLOW, FONT_REGULAR)
    pay_d.action = "quick_pay_debt"
    pay_d.enabled = game.can_pay_debt()
    pay_d.check_hover(mouse_pos)
    pay_d.draw(surface)
    buttons.append(pay_d)

    # Row 3: Invest $500
    inv_b = Button(40, 1030, 960, 65, "Invest $500 in Stock Market", BLUE, DARK_BLUE, FONT_REGULAR)
    inv_b.action = "quick_invest"
    inv_b.enabled = game.can_invest()
    inv_b.check_hover(mouse_pos)
    inv_b.draw(surface)
    buttons.append(inv_b)

    # Log Panel
    log_rect = pygame.Rect(40, 1115, 1000, 340)
    pygame.draw.rect(surface, CARD_BG, log_rect, border_radius=20)
    pygame.draw.rect(surface, GRAY, log_rect, 2, border_radius=20)

    t_log = FONT_MEDIUM.render("RECENT TRANSACTIONS & LOG", True, ACCENT)
    surface.blit(t_log, (70, 1135))

    for i, (txt, col) in enumerate(game.log):
        lt = FONT_REGULAR.render(txt, True, col)
        surface.blit(lt, (70, 1185 + i * 38))

    # Early Retirement button if eligible
    if game.early_retire_offered:
        retire_btn = Button(40, 1475, 1000, 70, "RETIRE EARLY ($1M+ NET WORTH REACHED!)", ACCENT, DARK_YELLOW, FONT_HEADER, BLACK)
        retire_btn.action = "early_retire"
        retire_btn.check_hover(mouse_pos)
        retire_btn.draw(surface)
        buttons.append(retire_btn)
        
    # Advance Quarter Button
    next_btn = Button(140, 1565, 800, 110, "ADVANCE 3 MONTHS >>", ACCENT, DARK_YELLOW, FONT_TITLE, BLACK)
    next_btn.action = "next_quarter"
    next_btn.check_hover(mouse_pos)
    next_btn.draw(surface)
    buttons.append(next_btn)


def draw_event_screen(surface, game, buttons, mouse_pos):
    overlay = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))
    overlay.set_alpha(220)
    overlay.fill((0, 0, 0))
    surface.blit(overlay, (0, 0))

    card_rect = pygame.Rect(50, 260, 980, 1320)
    pygame.draw.rect(surface, CARD_BG, card_rect, border_radius=24)
    pygame.draw.rect(surface, ACCENT, card_rect, 4, border_radius=24)

    ev_tag = FONT_MEDIUM.render(f"QUARTERLY EVENT - AGE {game.age_years}", True, ACCENT)
    surface.blit(ev_tag, (VIRTUAL_WIDTH // 2 - ev_tag.get_width() // 2, 310))

    title = FONT_TITLE.render(game.current_event["title"], True, WHITE)
    surface.blit(title, (VIRTUAL_WIDTH // 2 - title.get_width() // 2, 380))

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

    y = 470
    for line in lines:
        t = FONT_MEDIUM.render(line, True, GRAY)
        surface.blit(t, (VIRTUAL_WIDTH // 2 - t.get_width() // 2, y))
        y += 45

    # Informational Credit Guide Block (Credit Workshop)
    if game.current_event["title"] == "Credit Score Workshop":
        info_rect = pygame.Rect(80, 720, 920, 310)
        pygame.draw.rect(surface, (20, 30, 45), info_rect, border_radius=16)
        pygame.draw.rect(surface, ACCENT, info_rect, 2, border_radius=16)
        
        info_lines = [
            "--- CREDIT SCORE SUMMARY & GUIDE ---",
            "• High Score Benefits: Lower loan interest (~0.75%/qtr vs 3.25%/qtr) & higher final score multiplier.",
            "• Low Score Drawbacks: Expensive debt interest, rejected loans, & IRS asset seizure (<299 for 2 yrs).",
            "• How to Improve Credit Score:",
            "  1. Pay debt on time (+5 points).",
            "  2. Maintain consecutive payment streaks (+2 extra points).",
            "  3. Avoid missed payments (-50 points) and carrying unpaid debt (-20 points).",
            "  4. 5-Year History Cap: Cannot cross 700 points during the first 5 years."
        ]
        iy = 735
        for iline in info_lines:
            icol = ACCENT if "---" in iline else WHITE
            if "How to" in iline:
                icol = GREEN
            it = FONT_SMALL.render(iline, True, icol)
            surface.blit(it, (100, iy))
            iy += 35

    stat_txt = f"Cash: ${game.cash:,}  |  Debt: ${game.debt:,}  |  Happiness: {game.happiness}  |  Credit: {game.credit_score}"
    st = FONT_REGULAR.render(stat_txt, True, ACCENT)
    surface.blit(st, (VIRTUAL_WIDTH // 2 - st.get_width() // 2, 1070))

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
        sub_text = "Credit score stayed under 299 for 2 years. Died in prison!"
    else:
        borderColor = RED
        title_text = "DIED OF DEPRESSION!"
        sub_text = "Happiness remained at 0 for over a year."

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
                    elif act == "buy_happiness":
                        game.buy_happiness()
                    elif act == "quick_withdraw":
                        game.quick_withdraw(500)
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