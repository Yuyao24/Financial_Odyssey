"""The controller that owns the pages and overlays and routes every button press."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QStackedWidget, QWidget

from ..engine import LifeGame
from ..formatting import money
from .overlays import EventOverlay, PopupOverlay, SettingsOverlay, Toast
from .pages.game_over import GameOverPage
from .pages.insights import InsightsPage
from .pages.play import PlayPage
from .pages.start import StartPage
from .theme import CANVAS, T, build_stylesheet, make_font
from .tutorial import Tutorial


class GameUI(QWidget):
    def __init__(self, win, mode):
        super().__init__()
        self.win = win
        self.mode = mode
        desktop = mode == "desktop"
        self.desktop = desktop
        cw, ch = CANVAS[mode]
        self.setObjectName("root")
        self.setFixedSize(cw, ch)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(build_stylesheet())
        self.setFont(make_font(24))
        self.popup_queue = []

        self.stack = QStackedWidget(self)
        self.stack.setGeometry(0, 0, cw, ch)
        self.start_page = StartPage(self, desktop)
        self.play = PlayPage(self, desktop)
        self.over_page = GameOverPage(self, desktop)
        self.insights = InsightsPage(self, desktop)
        for w in (self.start_page, self.play, self.over_page, self.insights):
            self.stack.addWidget(w)

        self.event_overlay = EventOverlay(self, self.choose, desktop)
        self.tut = Tutorial(self, desktop)
        self.popup = PopupOverlay(self, self.after_overlay, desktop)
        self.settings = SettingsOverlay(self, self, desktop)
        self.toast = Toast(self)

        if win.page == "menu":
            self.stack.setCurrentWidget(self.start_page)
        else:
            self.after(save=False)

    @property
    def game(self):
        return self.win.game

    def switch_page(self, w):
        if self.stack.currentWidget() is not w:
            self.stack.setCurrentWidget(w)

    def open_insights(self):
        self.tut.coach.hide()
        self.event_overlay.hide()
        self.insights.refresh()
        self.switch_page(self.insights)

    def close_insights(self):
        if self.game.state == "game_over":
            self.switch_page(self.over_page)
        else:
            self.after(save=False)

    # ----------------------------------------------------------- navigation --
    def new_game(self):
        self.win.delete_save()
        self.win.game = LifeGame()
        self.win.game.start()
        self.win.page = "game"
        self.popup_queue.clear()
        self.event_overlay.hide()
        self.play.wake_up()
        if not self.win.settings.get("tutorial_done"):
            self.tut.start()
        self.after()

    def confirm_new_game(self):
        g = self.game
        body = (f"<p>Starting a new credit card <b>permanently deletes</b> your saved game:</p>"
                f"<p><b>Age {g.age_years} Q{g.quarter()}</b> · net worth {money(g.get_net_worth())} · "
                f"credit {g.credit_score}</p><p>This can't be undone.</p>")
        self.popup_queue.insert(0, {"title": "Delete your saved game?", "body": body, "kind": "warning",
                                    "buttons": [("Delete & start new", "danger", self.win.restart_new_game),
                                                ("Keep my save", "soft", None)]})
        self._pump()

    def resume(self):
        self.win.page = "game"
        self.after(save=False)

    def to_menu(self):
        self.win.save_game()
        self.win.page = "menu"
        self.win.has_save = self.win.save_exists()
        self.event_overlay.hide()
        self.tut.coach.hide()
        self.popup.hide()
        self.popup_queue.clear()
        # rebuild only the start page (its saved-game card changed) and switch to it
        old = self.start_page
        self.start_page = StartPage(self, self.desktop)
        self.stack.insertWidget(0, self.start_page)
        self.switch_page(self.start_page)
        self.stack.removeWidget(old)
        old.deleteLater()

    def open_settings(self):
        self.tut.coach.hide()
        self.settings.open()

    def replay_tutorial(self):
        self.win.settings["tutorial_done"] = False
        self.win.settings["tips_seen"] = []
        self.win.save_settings()
        if self.win.page == "game" and self.game.state == "main":
            self.tut.start()
            self.after()
        else:
            self.toast.push("The tutorial will play when you start or resume a game.", "good")
            self.after_overlay()

    def after_overlay(self):
        if self.win.page == "game" and self.game.state in ("main", "event"):
            self.play.refresh()
        self._pump()
        self.tut.refresh()

    # -------------------------------------------------------------- actions --
    def act(self, key, fn):
        res = fn()
        ok = not (isinstance(res, tuple) and not res[0])
        if not ok and res[1]:
            self.toast.push(res[1], "bad")
        if ok:
            self.tut.notify(key)
        self.after()

    def do(self, fn):
        self.act(None, fn)

    def choose(self, idx):
        self.act("choose", lambda: self.game.choose_option(idx))

    def advance(self):
        """Sleep at home. If anything important is undone, ask first."""
        g = self.game
        if g.state != "main":
            return
        rem = g.remaining_due()
        warn = []
        if rem > 0:
            hit = "a LATE payment (−20 credit)" if g.paid_this_qtr else "a MISSED payment (−50 credit)"
            warn.append(f"<b>{money(rem)}</b> of your minimum payment is still due: sleeping now counts as "
                        f"<b style='color:{T['red']}'>{hit}</b>.")
        if not g.work_plan:
            warn.append("You haven't <b>worked</b> this quarter, so there's no paycheck.")
        if not g.groceries:
            warn.append(f"No <b>groceries</b>: you'll live on takeout ({money(g.takeout_cost())}, "
                        f"{g.TAKEOUT_HAPPY} happiness).")
        short = g.essentials_total() - g.cash
        if not g.essentials_on_card and short > 0:
            warn.append(f"You're <b>{money(short)} short</b> for tonight's rent & bills: it'll go into overdraft, "
                        "onto your card or to collections.")
        if not warn:
            self._advance_now()
            return
        can_pay = rem > 0 and g.cash >= rem
        buttons = []
        if rem > 0:
            buttons.append((f"Pay {money(rem)} & sleep", "green", self._pay_and_advance if can_pay else False))
        buttons += [("Sleep anyway", "red" if rem > 0 else "primary", self._advance_now), ("Not yet", "soft", None)]
        body = "<p>Before you go to bed:</p><ul>" + "".join(f"<li>{w}</li>" for w in warn) + "</ul>"
        self.popup_queue.insert(0, {"title": "Go to sleep?", "body": body, "kind": "warning", "buttons": buttons})
        self.tut.coach.hide()
        self._pump()

    def _pay_and_advance(self):
        self.game.pay_minimum()
        self._advance_now()

    def _advance_now(self):
        self.game.next_turn()
        self.play.wake_up()
        self.tut.notify("advance")
        self.after()

    def confirm_retire(self):
        g = self.game
        mult = g.credit_multiplier()
        body = (f"<p>Retire now with a net worth of <b>{money(g.get_net_worth())}</b>?</p>"
                f"<p>Your final score will be net worth × {mult:.2f} (credit multiplier) = "
                f"<b>{int(g.get_net_worth() * mult):,}</b>.</p>")
        self.popup_queue.insert(0, {"title": "Retire early?", "body": body, "kind": "gold",
                                    "buttons": [("Retire now", "solid_green", lambda: self.do(g.retire_early)),
                                                ("Keep working", "soft", None)]})
        self._pump()

    def show_guide(self):
        self.tut.coach.hide()
        self.popup_queue.insert(0, {"title": "Credit 101", "body": self.game.credit_guide_html(), "kind": "gold"})
        self._pump()

    # ------------------------------------------------------------------------
    def after(self, save=True):
        g = self.game
        for text, tone in g.toasts:
            self.toast.push(text, tone)
        g.toasts.clear()
        for p in g.popups:
            item = dict(p)
            if p.get("guide"):
                item["buttons"] = [("Open full credit guide", "blue", self.show_guide), ("Got it", "primary", None)]
            self.popup_queue.append(item)
        g.popups.clear()

        if g.state == "game_over":
            self.event_overlay.hide()
            self.tut.coach.hide()
            self.popup_queue = [q for q in self.popup_queue if q["title"] == "Credit 101"]
            self.over_page.show_game(g)
            self.switch_page(self.over_page)
            self.win.delete_save()
        elif g.state in ("main", "event"):
            self.switch_page(self.play)
            self.play.refresh()
            if g.state == "event":
                self.event_overlay.show_event(g)
            else:
                self.event_overlay.hide()
            if save:
                self.win.save_game()
        self._pump()
        self.tut.refresh()

    def _pump(self):
        if self.popup.isVisible() or not self.popup_queue:
            if self.popup.isVisible():
                self.popup.raise_()
            return
        item = self.popup_queue.pop(0)
        self.tut.coach.hide()
        self.popup.show_popup(item["title"], item["body"], item.get("kind", "info"), item.get("buttons"))
        self.toast.raise_()
