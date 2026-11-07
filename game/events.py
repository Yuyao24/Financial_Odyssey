import json
import random
from pathlib import Path
from game.state import Player

def load_events():
    events_path = Path(__file__).resolve().parent.parent / "data" / "events.json"
    with open(events_path, "r", encoding="utf-8") as f:
        return json.load(f)

def pick_event(player: Player, rng: random.Random):
    events = load_events()
    return rng.choice(events)

def apply_event_choice(player: Player, choice: dict):
    effect = choice.get("effect", {})
    player.cash += effect.get("cash", 0)
    player.card.balance += effect.get("card", 0)
    player.card.limit += effect.get("card_limit", 0)
    player.happiness = max(0, min(100, player.happiness + effect.get("happiness", 0)))