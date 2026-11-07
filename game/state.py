from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class CreditCard:
    balance: float = 0.0
    statement_balance: float = 0.0
    limit: float = 1000.0
    apr: float = 0.24  # 24% APR
    min_payment_due: float = 0.0
    paid_this_month: float = 0.0

    @property
    def utilisation(self) -> float:
        return self.balance / self.limit if self.limit > 0 else 1.0

@dataclass
class Loan:
    name: str
    principal: float
    apr: float
    term_months_left: int
    monthly_payment: float
    is_mortgage: bool = False
    property_value: float = 0.0

@dataclass
class MonthlyStatement:
    month: int
    income_received: float
    bills_paid: float
    interest_charged: float
    late_fees: float
    old_score: int
    new_score: int
    score_breakdown: dict[str, float]
    reasons: List[str]          # Plain-language reasons for TTS / Statement UI
    jargon_reasons: List[str]   # Standard financial wording

@dataclass
class Player:
    month: int = 1
    cash: float = 1500.0
    savings: float = 500.0
    investments: float = 0.0
    income: float = 2200.0
    living_costs: float = 1100.0  # Rent + mandatory needs
    happiness: int = 70           # 0-100 scale
    
    card: CreditCard = field(default_factory=CreditCard)
    loans: List[Loan] = field(default_factory=list)
    
    credit_score: int = 680
    first_account_age_months: int = 12
    
    # Rolling histories for the credit score engine
    payment_history: List[bool] = field(default_factory=lambda: [True] * 12)
    hard_inquiries_months_ago: List[int] = field(default_factory=list)
    
    # Tracking for end-of-game graphs and bankruptcy check
    score_history: List[int] = field(default_factory=lambda: [680])
    net_worth_history: List[float] = field(default_factory=lambda: [2000.0])
    months_insolvent: int = 0
    plain_language_mode: bool = True

    @property
    def total_debt(self) -> float:
        loan_debt = sum(l.principal for l in self.loans)
        return self.card.balance + loan_debt

    @property
    def property_equity(self) -> float:
        return sum(l.property_value for l in self.loans if l.is_mortgage)

    @property
    def net_worth(self) -> float:
        assets = self.cash + self.savings + self.investments + self.property_equity
        return assets - self.total_debt