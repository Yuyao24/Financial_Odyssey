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
    def __init__(self):
        self.reset()

    def reset(self):
        self.age_years = 18
        self.age_months = 0
        self.cash = 1500
        self.credit_score = 650  # Cap: 1000, Death threshold < 299 for 8 turns (2 years)
        self.debt = 0
        self.investments = 0
        self.health = 100  # Cap 100, Death threshold <= 0 for 4 turns (1 year)

        self.low_credit_turns = 0
        self.zero_health_turns = 0

        self.state = "card_prompt"  # card_prompt, main, event, game_over
        self.death_reason = ""
        self.log = []
        self.current_event = None
        self.event_buttons = []
        self.message = ""

        # Quarter stats
        self.base_income = 4500  # Quarterly earnings
        self.base_living_expense = 2000

    def get_net_worth(self):
        return self.cash + self.investments - self.debt

    def add_log(self, text, color=WHITE):
        self.log.append((f"Age {self.age_years} Q{(self.age_months // 3) + 1}: {text}", color))
        if len(self.log) > 6:
            self.log.pop(0)

    def update_credit(self, delta):
        self.credit_score = max(0, min(1000, self.credit_score + delta))

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

        # Income & living costs
        earned = self.base_income
        self.cash += earned

        # Passive decay of health (must buy food/care every quarter)
        self.health = max(0, self.health - 15)

        # Debt interest (5% quarterly interest ~ 20% APR)
        if self.debt > 0:
            interest = int(self.debt * 0.05)
            self.debt += interest
            self.update_credit(-15)  # Carrying debt continuously hurts credit rating
            self.add_log(f"Debt interest +${interest}, Credit -15", RED)
        else:
            self.update_credit(5)  # No debt boosts credit score

        # Investment returns (-5% to +8% quarterly)
        if self.investments > 0:
            growth = random.uniform(-0.04, 0.08)
            change = int(self.investments * growth)
            self.investments = max(0, self.investments + change)
            if change >= 0:
                self.add_log(f"Investments grew by +${change}", GREEN)
            else:
                self.add_log(f"Investments changed by -${abs(change)}", RED)

        # Can user pay living expenses?
        if self.cash >= self.base_living_expense:
            self.cash -= self.base_living_expense
        else:
            deficit = self.base_living_expense - self.cash
            self.cash = 0
            self.debt += deficit
            self.update_credit(-30)
            self.add_log(f"Couldn't pay bills! +${deficit} Debt, Credit -30", RED)

        # Health check
        if self.health <= 0:
            self.zero_health_turns += 1
            if self.zero_health_turns >= 4:  # 1 year at 0 health
                self.state = "game_over"
                self.death_reason = "HEALTH_FAILURE"
                return
        else:
            self.zero_health_turns = 0

        # IRS Credit check (< 299 for 2 years / 8 turns)
        if self.credit_score < 299:
            self.low_credit_turns += 1
            if self.low_credit_turns >= 8:
                self.state = "game_over"
                self.death_reason = "IRS_SEIZURE"
                return
        else:
            self.low_credit_turns = 0

        # Trigger random quarter event
        self.trigger_quarter_event()

    def trigger_quarter_event(self):
        events = [
            {
                "title": "Medical Checkup & Care",
                "desc": "Unexpected dental work and prescription fees came up.",
                "options": [
                    ("Pay $600 in Cash (Health +20)", "pay_med"),
                    ("Charge $600 to Credit Card (Debt +$600)", "debt_med"),
                    ("Skip treatment (-15 Health)", "skip_med")
                ]
            },
            {
                "title": "Stock Market Trend",
                "desc": "Market news highlights a booming Index Fund opportunity.",
                "options": [
                    ("Invest $1,000 in Index Funds", "invest_index"),
                    ("Take out $2,000 loan to invest heavy", "loan_invest"),
                    ("Pass on opportunity", "pass")
                ]
            },
            {
                "title": "Car Maintenance",
                "desc": "Your car transmission needs repair to get to work.",
                "options": [
                    ("Pay $800 cash to fix", "fix_car_cash"),
                    ("Take out $800 repair loan", "fix_car_loan"),
                    ("Sell car (+ $1,200 cash, -10 Health from transit)", "sell_car")
                ]
            },
            {
                "title": "Luxury Vacation Offer",
                "desc": "Friends invite you on a 7-day tropical trip.",
                "options": [
                    ("Go on trip ($1,500 Cash, +35 Health)", "vacation_cash"),
                    ("Take out loan for trip ($1,500 Debt, +35 Health)", "vacation_loan"),
                    ("Decline and work extra", "vacation_skip")
                ]
            },
            {
                "title": "Career Certification",
                "desc": "A professional course can boost your future quarterly income.",
                "options": [
                    ("Pay $1,200 for course (Income +$500/qtr)", "course_cash"),
                    ("Finance course with $1,200 loan", "course_loan"),
                    ("Skip course", "pass")
                ]
            },
            {
                "title": "Debt Consolidation Offer",
                "desc": "A bank offers to refinance your current loans with a structured payment.",
                "options": [
                    ("Pay off $1,000 Debt right now (Credit +40)", "pay_debt_1000"),
                    ("Pay off $500 Debt right now (Credit +20)", "pay_debt_500"),
                    ("Ignore offer", "pass")
                ]
            }
        ]

        self.current_event = random.choice(events)
        self.state = "event"
        self.build_event_buttons()

    def build_event_buttons(self):
        self.event_buttons = []
        options = self.current_event["options"]
        bw, bh = 940, 110
        start_y = 1180
        spacing = 30

        for i, (text, action) in enumerate(options):
            x = (VIRTUAL_WIDTH - bw) // 2
            y = start_y + i * (bh + spacing)
            btn = Button(x, y, bw, bh, text, BLUE, DARK_BLUE, FONT_MEDIUM)
            btn.action = action
            self.event_buttons.append(btn)

    def handle_choice(self, action):
        credit_change = 0

        if action == "pay_med":
            if self.cash >= 600:
                self.cash -= 600
                self.health = min(100, self.health + 20)
                credit_change = 10
                self.add_log("Paid $600 medical bill. Health +20, Credit +10", GREEN)
            else:
                self.debt += 600
                self.health = min(100, self.health + 10)
                credit_change = -20
                self.add_log("Insufficient cash! Added $600 to debt. Credit -20", RED)

        elif action == "debt_med":
            self.debt += 600
            self.health = min(100, self.health + 20)
            credit_change = -15
            self.add_log("Charged $600 to credit card. Debt +600, Credit -15", RED)

        elif action == "skip_med":
            self.health = max(0, self.health - 15)
            self.add_log("Skipped medical care. Health dropped by 15", ORANGE)

        elif action == "invest_index":
            if self.cash >= 1000:
                self.cash -= 1000
                self.investments += 1000
                credit_change = 15
                self.add_log("Invested $1,000 into Index Funds. Credit +15", GREEN)
            else:
                self.add_log("Not enough cash to invest $1,000!", RED)

        elif action == "loan_invest":
            self.debt += 2000
            self.investments += 2000
            credit_change = -25
            self.add_log("Took $2,000 loan to invest. Debt +2000, Credit -25", RED)

        elif action == "fix_car_cash":
            if self.cash >= 800:
                self.cash -= 800
                credit_change = 10
                self.add_log("Repaired car for $800 cash. Credit +10", GREEN)
            else:
                self.debt += 800
                credit_change = -20
                self.add_log("Insufficient cash! Auto repair added to debt", RED)

        elif action == "fix_car_loan":
            self.debt += 800
            credit_change = -15
            self.add_log("Took $800 repair loan. Credit -15", RED)

        elif action == "sell_car":
            self.cash += 1200
            self.health = max(0, self.health - 10)
            self.add_log("Sold car for $1,200 cash. Transit fatigue -10 Health", YELLOW)

        elif action == "vacation_cash":
            if self.cash >= 1500:
                self.cash -= 1500
                self.health = min(100, self.health + 35)
                self.add_log("Enjoyed $1,500 vacation! Health +35", GREEN)
            else:
                self.add_log("Not enough cash for vacation!", RED)

        elif action == "vacation_loan":
            self.debt += 1500
            self.health = min(100, self.health + 35)
            credit_change = -30
            self.add_log("Took out $1,500 vacation loan. Debt +1500, Credit -30", RED)

        elif action == "vacation_skip":
            self.add_log("Skipped vacation to save money.", WHITE)

        elif action == "course_cash":
            if self.cash >= 1200:
                self.cash -= 1200
                self.base_income += 500
                credit_change = 20
                self.add_log("Completed course! Quarterly Income +$500", GREEN)
            else:
                self.add_log("Not enough cash for course!", RED)

        elif action == "course_loan":
            self.debt += 1200
            self.base_income += 500
            credit_change = -10
            self.add_log("Financed course! Income +$500/qtr, Debt +$1200", YELLOW)

        elif action == "pay_debt_1000":
            if self.debt > 0 and self.cash >= 1000:
                pay = min(1000, self.debt)
                self.cash -= pay
                self.debt -= pay
                credit_change = 40
                self.add_log(f"Paid off ${pay} debt! Credit +40", GREEN)
            else:
                self.add_log("Cannot perform debt repayment!", RED)

        elif action == "pay_debt_500":
            if self.debt > 0 and self.cash >= 500:
                pay = min(500, self.debt)
                self.cash -= pay
                self.debt -= pay
                credit_change = 20
                self.add_log(f"Paid off ${pay} debt! Credit +20", GREEN)
            else:
                self.add_log("Cannot perform debt repayment!", RED)

        elif action == "pass":
            self.add_log("Passed on option.", WHITE)

        if credit_change != 0:
            self.update_credit(credit_change)

        self.state = "main"


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
        "• Turn duration: 1 turn = 3 Months.",
        "• Your goal: Reach age 65 with maximum Net Worth.",
        "• Credit Score cap: 1000.",
        "• Keep Health high by spending on living/wellness.",
        "  (0 Health for 1 year = DEATH)",
        "• Keep Credit Score above 299.",
        "  (Credit < 299 for 2 years = IRS SEIZURE & DEATH)",
        "• Unpaid loans collect interest and destroy your credit!"
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
    t_h = FONT_MEDIUM.render(f"HEALTH: {game.health}/100", True, WHITE)
    surface.blit(t_h, (80, 330))
    pygame.draw.rect(surface, DARK_GRAY, (80, 380, 880, 36), border_radius=18)
    h_width = int(880 * (game.health / 100))
    h_color = GREEN if game.health > 50 else (YELLOW if game.health > 25 else RED)
    if h_width > 0:
        pygame.draw.rect(surface, h_color, (80, 380, h_width, 36), border_radius=18)

    # Credit Score Bar (Cap 1000)
    t_c = FONT_MEDIUM.render(f"CREDIT SCORE: {game.credit_score} / 1000", True, WHITE)
    surface.blit(t_c, (80, 440))
    pygame.draw.rect(surface, DARK_GRAY, (80, 490, 880, 36), border_radius=18)
    c_width = int(880 * (game.credit_score / 1000))
    c_color = GREEN if game.credit_score >= 700 else (YELLOW if game.credit_score >= 500 else RED)
    if c_width > 0:
        pygame.draw.rect(surface, c_color, (80, 490, c_width, 36), border_radius=18)

    # Threshold Warnings
    if game.credit_score < 299:
        w_t = FONT_SMALL.render(f"WARNING: IRS SEIZURE IMMINENT ({game.low_credit_turns}/8 turns low)", True, RED)
        surface.blit(w_t, (80, 535))
    if game.health <= 0:
        w_h = FONT_SMALL.render(f"WARNING: CRITICAL HEALTH ({game.zero_health_turns}/4 turns zero)", True, RED)
        surface.blit(w_h, (80, 560))

    # Financial Details Grid
    fin_items = [
        ("Cash Balance", f"${game.cash:,}", GREEN),
        ("Total Debt", f"${game.debt:,}", RED if game.debt > 0 else GRAY),
        ("Investments", f"${game.investments:,}", BLUE),
        ("Qtr Income", f"${game.base_income:,}", ACCENT)
    ]

    y_grid = 600
    for i, (label, val, col) in enumerate(fin_items):
        rx = 80 + (i % 2) * 450
        ry = y_grid + (i // 2) * 100
        tl = FONT_REGULAR.render(label, True, GRAY)
        tv = FONT_HEADER.render(val, True, col)
        surface.blit(tl, (rx, ry))
        surface.blit(tv, (rx, ry + 32))

    # Health Purchase Actions
    buy_h1 = Button(40, 880, 480, 100, "Buy Groceries (+$300, Health +20)", GREEN, DARK_GREEN, FONT_REGULAR)
    buy_h1.action = "buy_groceries"
    buy_h1.enabled = game.cash >= 300
    buy_h1.check_hover(mouse_pos)
    buy_h1.draw(surface)
    buttons.append(buy_h1)

    buy_h2 = Button(560, 880, 480, 100, "Wellness & Spa (+$800, Health +50)", BLUE, DARK_BLUE, FONT_REGULAR)
    buy_h2.action = "buy_spa"
    buy_h2.enabled = game.cash >= 800
    buy_h2.check_hover(mouse_pos)
    buy_h2.draw(surface)
    buttons.append(buy_h2)

    # Debt / Invest Quick Actions
    pay_d = Button(40, 1010, 480, 100, "Pay $500 Debt", ORANGE, DARK_YELLOW, FONT_REGULAR)
    pay_d.action = "quick_pay_debt"
    pay_d.enabled = game.cash >= 500 and game.debt > 0
    pay_d.check_hover(mouse_pos)
    pay_d.draw(surface)
    buttons.append(pay_d)

    inv_b = Button(560, 1010, 480, 100, "Invest $500", PURPLE, DARK_BLUE, FONT_REGULAR)
    inv_b.action = "quick_invest"
    inv_b.enabled = game.cash >= 500
    inv_b.check_hover(mouse_pos)
    inv_b.draw(surface)
    buttons.append(inv_b)

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

    card_rect = pygame.Rect(50, 300, 980, 1320)
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
        sub_text = "Credit score remained under 299 for 2 years. You died in prison!"
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
    final_score = int(nw + (game.credit_score * 50))

    stats = [
        ("Final Age Reached", f"{game.age_years}", WHITE),
        ("Final Net Worth", f"${nw:,}", GREEN if nw >= 0 else RED),
        ("Final Credit Score", f"{game.credit_score} / 1000", ACCENT),
        ("Remaining Cash", f"${game.cash:,}", GREEN),
        ("Remaining Debt", f"${game.debt:,}", RED if game.debt > 0 else GRAY),
        ("FINAL SCORE", f"{final_score:,} PTS", ACCENT)
    ]

    y = 580
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

        # Process clicks
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
                        if game.cash >= 300:
                            game.cash -= 300
                            game.health = min(100, game.health + 20)
                            game.add_log("Bought healthy groceries (+$300, Health +20)", GREEN)
                    elif act == "buy_spa":
                        if game.cash >= 800:
                            game.cash -= 800
                            game.health = min(100, game.health + 50)
                            game.add_log("Went for health & spa treatment (+$800, Health +50)", GREEN)
                    elif act == "quick_pay_debt":
                        if game.cash >= 500 and game.debt > 0:
                            pay = min(500, game.debt)
                            game.cash -= pay
                            game.debt -= pay
                            game.update_credit(20)
                            game.add_log(f"Paid ${pay} debt. Credit +20", GREEN)
                    elif act == "quick_invest":
                        if game.cash >= 500:
                            game.cash -= 500
                            game.investments += 500
                            game.update_credit(10)
                            game.add_log("Invested $500 in Index Funds. Credit +10", BLUE)

                elif game.state == "event":
                    act = getattr(btn, "action", None)
                    if act:
                        game.handle_choice(act)

                elif game.state == "game_over":
                    if getattr(btn, "action", None) == "restart":
                        game.reset()
                        game.state = "main"

        # Scale virtual surface (1080x1920) onto window display with letterboxing / pillarboxing
        window.fill(BLACK)
        scaled_surface = pygame.transform.scale(virtual_surface, (WINDOW_WIDTH, WINDOW_HEIGHT))
        window.blit(scaled_surface, (0, 0))
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
