"""The main window: settings, saving/loading, theme and layout switching, fullscreen."""

import os

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QGuiApplication, QKeySequence, QShortcut
from PyQt6.QtWidgets import QMainWindow

from ..engine import LifeGame
from ..storage import data_dir, read_json, write_json
from .game_ui import GameUI
from .theme import CANVAS, THEMES, use_theme
from .view import ScaledView


class MainWindow(QMainWindow):
    def __init__(self, storage_dir=None):
        super().__init__()
        self.setWindowTitle("Financial Odyssey: 18 to 65")
        self.setStyleSheet("QMainWindow { background:#000; }")
        self.dir = storage_dir or data_dir()
        os.makedirs(self.dir, exist_ok=True)
        self.save_path = os.path.join(self.dir, "savegame.json")
        self.settings_path = os.path.join(self.dir, "settings.json")

        self.settings = {"theme": "light", "layout": "mobile", "tutorial_done": False, "tips_seen": []}
        saved = read_json(self.settings_path) or {}
        if saved.get("theme") in THEMES:
            self.settings["theme"] = saved["theme"]
        if saved.get("layout") in CANVAS:
            self.settings["layout"] = saved["layout"]
        if isinstance(saved.get("tutorial_done"), bool):
            self.settings["tutorial_done"] = saved["tutorial_done"]
        if isinstance(saved.get("tips_seen"), list):
            self.settings["tips_seen"] = [str(x) for x in saved["tips_seen"]]
        self.game = self.load_game() or LifeGame()
        self.has_save = self.game.state in ("main", "event")
        self.page = "menu"
        self.ui = None
        self.view = None

        self.setMinimumSize(320, 320)
        self.rebuild()
        self.fit_window()
        QShortcut(QKeySequence("F11"), self, self.toggle_fullscreen)
        QShortcut(QKeySequence("Esc"), self, lambda: self.showNormal() if self.isFullScreen() else None)

    # -------------------------------------------------------------- saving --
    def load_game(self):
        d = read_json(self.save_path)
        if not d:
            return None
        try:
            g = LifeGame.from_dict(d)
            return g if g.state in ("main", "event") else None
        except Exception:
            return None

    def save_exists(self):
        return os.path.exists(self.save_path)

    def save_game(self):
        if self.page == "game" and self.game.state in ("main", "event"):
            try:
                write_json(self.save_path, self.game.to_dict())
            except OSError:
                pass

    def delete_save(self):
        try:
            os.remove(self.save_path)
        except OSError:
            pass

    def save_settings(self):
        try:
            write_json(self.settings_path, self.settings)
        except OSError:
            pass

    def restart_new_game(self):
        if self.ui is not None:
            self.ui.new_game()

    def closeEvent(self, e):
        self.save_game()
        self.save_settings()
        super().closeEvent(e)

    # ------------------------------------------------------- theme & layout --
    def rebuild(self, reopen_settings=False):
        use_theme(self.settings["theme"])
        mode = self.settings["layout"] if self.settings["layout"] in CANVAS else "mobile"
        carry = [q for q in (self.ui.popup_queue if self.ui else []) if not q.get("buttons")]
        self.ui = GameUI(self, mode)
        self.ui.popup_queue[:0] = carry
        cw, ch = CANVAS[mode]
        if self.view is None:
            self.view = ScaledView(self.ui, cw, ch)
            self.setCentralWidget(self.view)
        else:
            self.view.set_root(self.ui, cw, ch)
        if reopen_settings:
            self.ui.open_settings()
        else:
            self.ui._pump()
            self.ui.tut.refresh()

    def rebuild_later(self, reopen_settings=False):
        # defer so we never delete the widget whose click handler is still running
        QTimer.singleShot(0, lambda: self.rebuild(reopen_settings))

    def set_theme(self, name, reopen=True):
        if name in THEMES and name != self.settings["theme"]:
            self.settings["theme"] = name
            self.save_settings()
            self.rebuild_later(reopen_settings=reopen)

    def set_layout(self, mode):
        if mode in CANVAS and mode != self.settings["layout"]:
            self.settings["layout"] = mode
            self.save_settings()
            self.rebuild_later(reopen_settings=True)
            QTimer.singleShot(0, self.fit_window)

    def fit_window(self):
        """Size the window to the layout's aspect ratio (still letterboxes if resized freely)."""
        if self.isFullScreen() or self.isMaximized():
            return
        cw, ch = CANVAS.get(self.settings["layout"], CANVAS["mobile"])
        screen = self.screen() or QGuiApplication.primaryScreen()
        if screen is None:                    # no display information available
            return
        scr = screen.availableGeometry()
        h = int(scr.height() * 0.90)
        w = int(h * cw / ch)
        if w > scr.width() * 0.92:
            w = int(scr.width() * 0.92)
            h = int(w * ch / cw)
        self.resize(w, h)
        self.move(scr.x() + (scr.width() - w) // 2, scr.y() + (scr.height() - h) // 2)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.fit_window()
        else:
            self.showFullScreen()
