"""Pure game logic with no Qt dependency.

    from financial_odyssey.engine import LifeGame
    g = LifeGame(seed=1); g.start(); g.pay_all(); g.next_turn()
"""

from .game import LifeGame

__all__ = ["LifeGame"]
