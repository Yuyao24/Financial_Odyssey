"""Modal overlays drawn over the canvas: life events, popups, settings and toasts."""

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..formatting import money
from .theme import CANVAS, W_BOLD, W_NORMAL, W_SEMI, T
from .widgets import Badge, Card, IconButton, WrapButton, clear_layout, label


class Overlay(QWidget):
    """Full-canvas dimmed layer with a centred modal card."""

    def __init__(self, parent, width):
        super().__init__(parent)
        self.setGeometry(0, 0, parent.width(), parent.height())
        outer = QVBoxLayout(self)
        outer.setContentsMargins(40, 40, 40, 40)
        outer.addStretch(1)
        row = QHBoxLayout()
        row.addStretch(1)
        self.modal = Card("modal")
        self.modal.setFixedWidth(width)
        row.addWidget(self.modal)
        row.addStretch(1)
        outer.addLayout(row)
        outer.addStretch(1)
        self.body = QVBoxLayout(self.modal)
        self.body.setContentsMargins(48, 42, 48, 42)
        self.body.setSpacing(20)
        self.hide()

    def paintEvent(self, e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(*T["overlay"]))
        p.end()

    def mousePressEvent(self, e):
        e.accept()                                  # block clicks to the page below

    def clear(self):
        self.hide()            # new children of a visible widget would otherwise stay hidden
        clear_layout(self.body)


TONE_VARIANT = {"cash": "green", "card": "purple", "loan": "amber", "bad": "red",
                "good": "teal", "info": "blue", "skip": "slate"}


class EventOverlay(Overlay):
    def __init__(self, parent, on_choose, desktop):
        super().__init__(parent, 1300 if desktop else 970)
        self.desktop = desktop
        self.on_choose = on_choose
        self.key = None

    def show_event(self, g):
        ev = g.current_event
        if self.isVisible() and self.key is ev:
            return
        self.key = ev
        self.clear()
        b = self.body
        top = QHBoxLayout()
        tag = Badge(f"QUARTERLY EVENT  ·  AGE {g.age_years}  ·  Q{g.quarter()}", 19, 40)
        tag.set_tint("blue")
        top.addWidget(tag, 0)
        top.addStretch(1)
        b.addLayout(top)
        b.addWidget(label(ev["title"], 54, W_BOLD, wrap=True))
        b.addWidget(label(ev["desc"], 28, W_NORMAL, T["text2"], wrap=True))
        if ev.get("info"):
            box = Card("infobox")
            bl = QVBoxLayout(box)
            bl.setContentsMargins(28, 20, 28, 22)
            bl.setSpacing(6)
            bl.addWidget(label("Why it matters", 22, W_BOLD))
            bl.addWidget(label(ev["info"], 23, W_NORMAL, T["text2"], wrap=True))
            b.addWidget(box)
        # plain text status line (information, not buttons)
        b.addWidget(label(f"Cash {money(g.cash)}     Card credit left {money(g.card_available())}     "
                          f"Happiness {g.happiness}     Credit {g.credit_score}", 21, W_SEMI, T["muted"], wrap=True))
        b.addWidget(label("Choose one:", 22, W_BOLD, T["text"]))

        grid = QGridLayout()
        grid.setSpacing(16)
        opts = ev["options"]
        cols = 2 if self.desktop and len(opts) >= 3 else 1
        for i, o in enumerate(opts):
            reason = g.option_block_reason(o)
            text = o["label"] + (f"\n(unavailable: {reason})" if reason else "")
            btn = WrapButton(text, TONE_VARIANT.get(o["tone"], "slate"), 26, W_SEMI, height=110)
            btn.setEnabled(reason is None)
            btn.clicked.connect(lambda _=False, idx=i: self.on_choose(idx))
            span = 2 if cols == 2 and i == len(opts) - 1 and len(opts) % 2 else 1
            grid.addWidget(btn, i // cols, i % cols, 1, span)
        b.addLayout(grid)
        self.show()
        self.raise_()


class PopupOverlay(Overlay):
    KIND_TINT = {"warning": "red", "success": "green", "info": "blue", "gold": "amber"}

    def __init__(self, parent, on_close, desktop):
        super().__init__(parent, 1300 if desktop else 980)
        self.width_ = 1300 if desktop else 980
        self.max_h = 1000 if desktop else 1160
        self.on_close = on_close

    def show_popup(self, title, body_html, kind="info", buttons=None):
        self.clear()
        b = self.body
        top = QHBoxLayout()
        badge = Badge({"warning": "HEADS UP", "success": "NICE WORK", "gold": "GUIDE"}.get(kind, "INFO"), 19, 40)
        badge.set_tint(self.KIND_TINT.get(kind, "blue"))
        top.addWidget(badge)
        top.addStretch(1)
        b.addLayout(top)
        b.addWidget(label(title, 50, W_BOLD, wrap=True))

        body = label(body_html, 25, W_NORMAL, T["text2"], wrap=True, rich=True)
        body.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        holder = QWidget()
        hl = QVBoxLayout(holder)
        hl.setContentsMargins(0, 0, 18, 0)
        hl.addWidget(body)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(holder)
        need = body.heightForWidth(self.width_ - 96 - 30) + 64
        scroll.setFixedHeight(max(110, min(self.max_h, need)))
        b.addWidget(scroll)

        row = QHBoxLayout()
        row.setSpacing(14)
        for text, variant, cb in (buttons or [("Got it", "primary", None)]):
            btn = WrapButton(text, variant, 27, W_SEMI, height=92)
            btn.setEnabled(cb is not False)
            btn.clicked.connect(lambda _=False, c=cb: self._clicked(c))
            row.addWidget(btn)
        b.addLayout(row)
        self.show()
        self.raise_()

    def _clicked(self, cb):
        self.hide()
        if callable(cb):
            cb()
        self.on_close()


class SettingsOverlay(Overlay):
    def __init__(self, parent, ui, desktop):
        super().__init__(parent, 1100 if desktop else 960)
        self.ui = ui

    def _segmented(self, options, current, on_pick):
        wrap = Card("segwrap")
        wrap.setFixedHeight(84)
        lay = QHBoxLayout(wrap)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(8)
        for text, value, icon in options:
            btn = WrapButton(text, "segon" if value == current else "seg", 25, W_SEMI, height=68, icon=icon)
            btn.clicked.connect(lambda _=False, v=value: on_pick(v))
            lay.addWidget(btn)
        return wrap

    def open(self):
        self.clear()
        ui, win = self.ui, self.ui.win
        b = self.body
        b.setSpacing(16)
        top = QHBoxLayout()
        top.addWidget(label("Settings", 58, W_BOLD))
        top.addStretch(1)
        close = IconButton("close", 76)
        close.clicked.connect(self.close_)
        top.addWidget(close)
        b.addLayout(top)

        def section(title, hint=None):
            b.addSpacing(8)
            b.addWidget(label(title, 26, W_BOLD))
            if hint:
                b.addWidget(label(hint, 21, W_NORMAL, T["muted"], wrap=True))

        section("Appearance")
        b.addWidget(self._segmented([("Light", "light", "sun"), ("Dark", "dark", "moon")],
                                    win.settings["theme"], win.set_theme))
        section("Layout", "Mobile is a vertical 9:16 screen, desktop a horizontal 16:9 screen. Either one scales "
                          "to fit any window or monitor, with bars filling any leftover space.")
        b.addWidget(self._segmented([("Mobile  ·  vertical", "mobile", None), ("Desktop  ·  horizontal", "desktop", None)],
                                    win.settings["layout"], win.set_layout))
        section("Display")
        fs = WrapButton("Exit fullscreen  (F11)" if win.isFullScreen() else "Enter fullscreen  (F11)",
                        "soft", 25, W_SEMI, height=80)
        fs.clicked.connect(lambda: (win.toggle_fullscreen(), self.open()))
        b.addWidget(fs)

        section("Help")
        row = QHBoxLayout()
        row.setSpacing(14)
        guide = WrapButton("Credit 101 guide", "blue", 25, W_SEMI, height=80, icon="book")
        guide.clicked.connect(lambda: (self.hide(), ui.show_guide()))
        row.addWidget(guide)
        tut = WrapButton("Replay tutorial", "soft", 25, W_SEMI, height=80, icon="replay")
        tut.clicked.connect(lambda: (self.hide(), ui.replay_tutorial()))
        row.addWidget(tut)
        b.addLayout(row)

        section("Game", "Progress saves automatically after every move, and when you close the window.")
        row = QHBoxLayout()
        row.setSpacing(14)
        if win.page == "game" and ui.game.state in ("main", "event"):
            menu = WrapButton("Save & main menu", "outline", 25, W_SEMI, height=88, icon="home")
            menu.clicked.connect(lambda: (self.hide(), ui.to_menu()))
            row.addWidget(menu)
            quit_ = WrapButton("Save & quit", "danger", 27, W_BOLD, height=88, icon="power")
        else:
            quit_ = WrapButton("Quit game", "danger", 27, W_BOLD, height=88, icon="power")
        quit_.clicked.connect(win.close)
        row.addWidget(quit_)
        b.addLayout(row)
        self.show()
        self.raise_()

    def close_(self):
        self.hide()
        self.ui.after_overlay()


class Toast(QFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("toast")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(30, 18, 30, 18)
        lay.setSpacing(16)
        self.dot = QLabel()
        self.dot.setFixedSize(16, 16)
        lay.addWidget(self.dot)
        self.lbl = label("", 24, W_SEMI, T["primary_text"], wrap=True)
        lay.addWidget(self.lbl, 1)
        self.queue = []
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._next)
        self.hide()

    def push(self, text, tone="gold"):
        self.queue.append((text, tone))
        if not self.isVisible():
            self._next()

    def _next(self):
        if not self.queue:
            self.hide()
            return
        text, tone = self.queue.pop(0)
        dot = {"bad": "#F87171", "good": "#4ADE80", "gold": "#FACC15"}.get(tone, "#818CF8")
        self.dot.setStyleSheet(f"background:{dot}; border-radius:8px;")
        self.lbl.setText(text)
        parent = self.parentWidget()
        pw = parent.width() if parent is not None else CANVAS["mobile"][0]
        w = min(900, pw - 80)
        h = self.lbl.heightForWidth(w - 92) + 40
        self.setGeometry((pw - w) // 2, 28, w, max(80, h))
        self.show()
        self.raise_()
        self.timer.start(2800)

    def mousePressEvent(self, e):
        self.timer.stop()
        self._next()
