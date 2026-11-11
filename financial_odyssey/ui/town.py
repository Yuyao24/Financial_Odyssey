"""The painted town: six buildings you click to visit, a walking avatar and the seasons.

Everything is drawn with QPainter inside this one widget (no child widgets, no graphics
effects), so the optional animation is just a timer that advances `phase` and repaints.
Layout uses fractions of the widget size, so the same scene works on the mobile and
desktop canvases.
"""

import math

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QWidget

from .theme import W_BOLD, T, make_font

# key, name, row, x0, x1, height  (x and height are fractions of the scene size)
LOCATIONS = [
    ("office", "Office", "back", 0.04, 0.30, 0.34),
    ("college", "College", "back", 0.37, 0.63, 0.25),
    ("bank", "Bank", "back", 0.70, 0.96, 0.23),
    ("home", "Home", "front", 0.04, 0.30, 0.24),
    ("grocery", "Grocery", "front", 0.37, 0.63, 0.21),
    ("fun", "Fun Park", "front", 0.70, 0.96, 0.27),
]
LOC = {k: (name, row, x0, x1, hh) for k, name, row, x0, x1, hh in LOCATIONS}

BACK_BASE, ROAD_TOP, ROAD_BOT, FRONT_TOP, FRONT_BASE = 0.46, 0.49, 0.63, 0.66, 0.93
LANE_Y = 0.565
STAND_Y = {"back": 0.60, "front": 0.655}

SEASONS = {
    1: dict(name="Winter", sky=("#AFCDE6", "#EAF3FA"), hill="#D5E2EE", grass="#EEF3F8", grass2="#DCE6EF",
            tree="#6E9A84", tree2="#58836E"),
    2: dict(name="Spring", sky=("#7FC1EE", "#DDF1FB"), hill="#A6D795", grass="#9CD38A", grass2="#88C577",
            tree="#F4A6C6", tree2="#5DB362"),
    3: dict(name="Summer", sky=("#4FAEEB", "#CBEAFB"), hill="#78C26A", grass="#79C267", grass2="#66B456",
            tree="#3A9A4C", tree2="#2C8740"),
    4: dict(name="Autumn", sky=("#F0B979", "#FBE4C3"), hill="#D79D58", grass="#C8B068", grass2="#B69D59",
            tree="#E2793A", tree2="#C05329"),
}


def season_name(quarter):
    return SEASONS.get(quarter, SEASONS[3])["name"]


def _mix(a, b, t):
    ca, cb = QColor(a), QColor(b)
    return QColor(int(ca.red() + (cb.red() - ca.red()) * t), int(ca.green() + (cb.green() - ca.green()) * t),
                  int(ca.blue() + (cb.blue() - ca.blue()) * t))


def _rand(i, salt=0):
    """Deterministic pseudo-random number in [0, 1) for particle i."""
    x = math.sin(i * 12.9898 + salt * 78.233) * 43758.5453
    return x - math.floor(x)


class TownView(QWidget):
    FPS_MS = 33

    def __init__(self, on_pick=None, interactive=True):
        super().__init__()
        self.on_pick = on_pick
        self.interactive = interactive
        self.quarter = 3
        self.night = False
        self.age = 18
        self.selected = None
        self.hover = None
        self.badges = {}                 # key -> "todo" | "done" | "due" | "sleep"
        self.animate = True
        self.phase = 0.0
        self.feet = (0.17, STAND_Y["front"])  # avatar feet, as fractions
        self.path = []                   # remaining waypoints while walking
        self.facing = 1
        self.walking = False
        self.setMouseTracking(True)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)

    # ------------------------------------------------------------ state ---
    def set_state(self, quarter, night, age, selected, badges, animate):
        self.quarter, self.night, self.age = quarter, night, age
        self.selected, self.badges = selected, badges
        if animate != self.animate:
            self.animate = animate
            if not animate:
                self._finish_walk()
        self._sync_timer()
        self.update()

    def stand_point(self, key):
        _, row, x0, x1, _ = LOC[key]
        return ((x0 + x1) / 2, STAND_Y[row])

    def place_at(self, key):
        self.path = []
        self.walking = False
        self.feet = self.stand_point(key)
        self.update()

    def walk_to(self, key):
        target = self.stand_point(key)
        if not self.animate or not self.isVisible():
            self.place_at(key)
            return
        x, y = self.feet
        self.path = [(x, LANE_Y), (target[0], LANE_Y), target]
        self.walking = True
        self._sync_timer()

    def _finish_walk(self):
        if self.path:
            self.feet = self.path[-1]
        self.path = []
        self.walking = False

    def _sync_timer(self):
        run = self.isVisible() and (self.animate or self.walking)
        if run and not self.timer.isActive():
            self.timer.start(self.FPS_MS)
        elif not run and self.timer.isActive():
            self.timer.stop()

    def showEvent(self, e):
        self._sync_timer()
        super().showEvent(e)

    def hideEvent(self, e):
        self._finish_walk()
        self._sync_timer()
        super().hideEvent(e)

    def _tick(self):
        dt = self.FPS_MS / 1000
        self.phase += dt
        if self.path:
            speed = 0.75 * dt                       # scene widths per second
            x, y = self.feet
            tx, ty = self.path[0]
            dx, dy = tx - x, (ty - y) * (self.height() / max(1, self.width()))
            dist = math.hypot(dx, dy)
            if dist <= speed:
                self.feet = (tx, ty)
                self.path.pop(0)
            else:
                f = speed / dist
                self.feet = (x + (tx - x) * f, y + (ty - y) * f)
            if abs(dx) > 1e-4:
                self.facing = 1 if dx > 0 else -1
            if not self.path:
                self.walking = False
                self._sync_timer()
        self.update()

    # --------------------------------------------------------- geometry ---
    def building_rect(self, key):
        _, row, x0, x1, hh = LOC[key]
        w, h = self.width(), self.height()
        base = (BACK_BASE if row == "back" else FRONT_BASE) * h
        return QRectF(x0 * w, base - hh * h, (x1 - x0) * w, hh * h)

    def _hit(self, pt):
        for key, *_ in LOCATIONS:
            r = self.building_rect(key).adjusted(-10, -30, 10, 10)
            if r.contains(pt):
                return key
        return None

    def mouseMoveEvent(self, e):
        if not self.interactive:
            return
        key = self._hit(e.position())
        if key != self.hover:
            self.hover = key
            self.setCursor(Qt.CursorShape.PointingHandCursor if key else Qt.CursorShape.ArrowCursor)
            self.update()

    def leaveEvent(self, e):
        if self.hover:
            self.hover = None
            self.update()

    def mousePressEvent(self, e):
        if not self.interactive or e.button() != Qt.MouseButton.LeftButton:
            return
        key = self._hit(e.position())
        if key and self.on_pick:
            self.on_pick(key)

    # ------------------------------------------------------------ paint ---
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = float(self.width()), float(self.height())
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(0, 0, w, h), 32, 32)
        p.setClipPath(clip)
        s = SEASONS.get(self.quarter, SEASONS[3])
        self._sky(p, w, h, s)
        self._ground(p, w, h, s)
        for key in ("office", "college", "bank"):
            self._building(p, key, s)
        self._road(p, w, h)
        self._avatar(p, w, h)
        for key in ("home", "grocery", "fun"):
            self._building(p, key, s)
        self._particles(p, w, h)
        for key, *_ in LOCATIONS:
            self._sign_and_badge(p, key)
        p.end()

    def _dark(self, color, amount=0.45):
        return _mix(color, "#0A1024", amount) if self.night else QColor(color)

    def _sky(self, p, w, h, s):
        g = QLinearGradient(0, 0, 0, h * ROAD_TOP)
        if self.night:
            g.setColorAt(0, QColor("#0A1330"))
            g.setColorAt(1, QColor("#2A3B68"))
        else:
            g.setColorAt(0, QColor(s["sky"][0]))
            g.setColorAt(1, QColor(s["sky"][1]))
        p.fillRect(QRectF(0, 0, w, h * ROAD_TOP + 2), g)
        p.setPen(Qt.PenStyle.NoPen)
        if self.night:
            for i in range(46):
                tw = 0.5 + 0.5 * math.sin(self.phase * 2 + i) if self.animate else 1
                c = QColor(255, 255, 255, int(110 + 120 * tw))
                p.setBrush(c)
                p.drawEllipse(QPointF(_rand(i, 1) * w, _rand(i, 2) * h * 0.36), 2.2, 2.2)
            p.setBrush(QColor("#F4F1DE"))
            p.drawEllipse(QPointF(w * 0.86, h * 0.1), h * 0.045, h * 0.045)
            p.setBrush(QColor("#2A3B68"))
            p.drawEllipse(QPointF(w * 0.875, h * 0.09), h * 0.04, h * 0.04)
        else:
            sun = QColor("#FFE08A") if self.quarter != 4 else QColor("#FFC66B")
            glow = QColor(sun)
            glow.setAlpha(70)
            p.setBrush(glow)
            p.drawEllipse(QPointF(w * 0.86, h * 0.1), h * 0.075, h * 0.075)
            p.setBrush(sun)
            p.drawEllipse(QPointF(w * 0.86, h * 0.1), h * 0.05, h * 0.05)
        cloud = QColor(255, 255, 255, 70 if self.night else 225)
        p.setBrush(cloud)
        for i in range(4):
            speed = 0.010 + 0.006 * i
            x = ((_rand(i, 3) + self.phase * speed) % 1.3 - 0.15) * w
            y = h * (0.05 + 0.07 * _rand(i, 4))
            r = h * (0.028 + 0.012 * _rand(i, 5))
            for dx, dy, k in ((0, 0, 1.0), (r * 1.1, r * 0.25, 0.8), (-r * 1.1, r * 0.3, 0.75), (r * 0.4, -r * 0.45, 0.8)):
                p.drawEllipse(QPointF(x + dx, y + dy), r * k * 1.25, r * k)
        hill = QPainterPath()
        hill.moveTo(0, h * BACK_BASE)
        hill.cubicTo(w * 0.2, h * 0.30, w * 0.4, h * 0.40, w * 0.55, h * 0.36)
        hill.cubicTo(w * 0.7, h * 0.32, w * 0.85, h * 0.38, w, h * 0.33)
        hill.lineTo(w, h * BACK_BASE)
        hill.closeSubpath()
        p.setBrush(self._dark(s["hill"], 0.55))
        p.drawPath(hill)

    def _ground(self, p, w, h, s):
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self._dark(s["grass"]))
        p.drawRect(QRectF(0, h * FRONT_TOP, w, h * (1 - FRONT_TOP)))
        p.setBrush(self._dark(s["grass2"]))
        for i in range(18):                              # grass tufts / snow drifts
            x = _rand(i, 7) * w
            y = h * (FRONT_TOP + 0.02 + (1 - FRONT_TOP - 0.04) * _rand(i, 8))
            p.drawEllipse(QPointF(x, y), w * 0.018, h * 0.006)

    def _road(self, p, w, h):
        p.setPen(Qt.PenStyle.NoPen)
        walk = self._dark("#D9D4CC", 0.5)
        p.setBrush(walk)
        p.drawRect(QRectF(0, h * BACK_BASE, w, h * (ROAD_TOP - BACK_BASE)))
        p.drawRect(QRectF(0, h * ROAD_BOT, w, h * (FRONT_TOP - ROAD_BOT)))
        p.setBrush(self._dark("#5D6470", 0.4))
        p.drawRect(QRectF(0, h * ROAD_TOP, w, h * (ROAD_BOT - ROAD_TOP)))
        p.setBrush(self._dark("#F3E9C6", 0.3))
        dash, gap = w * 0.05, w * 0.035
        x = -((self.phase * 0) % (dash + gap))
        while x < w:
            p.drawRoundedRect(QRectF(x, h * (LANE_Y + 0.003) - 3, dash, 6), 3, 3)
            x += dash + gap
        p.setBrush(self._dark("#BDB6AA", 0.5))
        for y in (ROAD_TOP, ROAD_BOT):
            p.drawRect(QRectF(0, h * y - 2, w, 4))

    # ------------------------------------------------------------ buildings
    def _windows(self, p, r, cols, rows, top_pad, color, lit_color, gap=0.28, seed=0):
        cw = r.width() / cols
        ch = (r.height() - top_pad) / rows
        for i in range(cols):
            for j in range(rows):
                lit = self.night and _rand(i * 7 + j * 3 + seed, 9) < 0.6
                p.setBrush(QColor(lit_color) if lit else QColor(color))
                p.drawRoundedRect(QRectF(r.x() + i * cw + cw * gap / 2, r.y() + top_pad + j * ch + ch * gap / 2,
                                         cw * (1 - gap), ch * (1 - gap)), 3, 3)

    def _snow_cap(self, p, path_points):
        if self.quarter != 1:
            return
        p.setBrush(QColor("#FBFDFF"))
        p.drawPolygon(path_points)

    def _building(self, p, key, s):
        r = self.building_rect(key)
        x, y, bw, bh = r.x(), r.y(), r.width(), r.height()
        p.setPen(Qt.PenStyle.NoPen)
        # soft shadow on the ground
        p.setBrush(QColor(0, 0, 0, 40))
        p.drawEllipse(QPointF(x + bw / 2, y + bh), bw * 0.52, bh * 0.05)
        lit = "#FFD978"
        if key == "office":
            tower = QRectF(x + bw * 0.12, y, bw * 0.56, bh)
            side = QRectF(x + bw * 0.62, y + bh * 0.38, bw * 0.34, bh * 0.62)
            p.setBrush(self._dark("#4E6E9E"))
            p.drawRect(side)
            p.setBrush(self._dark("#5E83BB"))
            p.drawRect(tower)
            p.setBrush(self._dark("#3F5C88"))
            p.drawRect(QRectF(tower.x(), tower.y(), tower.width(), bh * 0.05))
            self._windows(p, tower.adjusted(bw * 0.04, 0, -bw * 0.04, -bh * 0.1), 4, 7, bh * 0.08,
                          self._dark("#BBD3F2", 0.35), lit, seed=1)
            self._windows(p, side.adjusted(bw * 0.03, 0, -bw * 0.03, -bh * 0.08), 2, 4, bh * 0.05,
                          self._dark("#A9C3E6", 0.35), lit, seed=2)
            p.setBrush(self._dark("#2E3F5C"))
            p.drawRect(QRectF(tower.center().x() - bw * 0.07, y + bh * 0.88, bw * 0.14, bh * 0.12))
            self._snow_cap(p, [QPointF(tower.left(), tower.top()), QPointF(tower.right(), tower.top()),
                               QPointF(tower.right(), tower.top() + bh * 0.025), QPointF(tower.left(), tower.top() + bh * 0.025)])
        elif key == "college":
            body = QRectF(x, y + bh * 0.34, bw, bh * 0.66)
            p.setBrush(self._dark("#EAD9B4"))
            p.drawRect(body)
            p.setBrush(self._dark("#E3CFA5"))
            p.drawRect(QRectF(x + bw * 0.36, y + bh * 0.08, bw * 0.28, bh * 0.3))      # clock tower
            p.setBrush(self._dark("#B5523B"))
            p.drawPolygon([QPointF(x + bw * 0.33, y + bh * 0.1), QPointF(x + bw * 0.5, y - bh * 0.06),
                           QPointF(x + bw * 0.67, y + bh * 0.1)])
            p.drawPolygon([QPointF(x - bw * 0.03, y + bh * 0.36), QPointF(x + bw * 0.5, y + bh * 0.2),
                           QPointF(x + bw * 1.03, y + bh * 0.36)])
            self._snow_cap(p, [QPointF(x + bw * 0.4, y + bh * 0.02), QPointF(x + bw * 0.5, y - bh * 0.06),
                               QPointF(x + bw * 0.6, y + bh * 0.02)])
            cx, cy, cr = x + bw * 0.5, y + bh * 0.22, bh * 0.07
            p.setBrush(QColor("#FFFDF5"))
            p.drawEllipse(QPointF(cx, cy), cr, cr)
            p.setPen(QPen(QColor("#5B4A35"), max(2.0, cr * 0.15), cap=Qt.PenCapStyle.RoundCap))
            ang = self.phase * 0.6 if self.animate else 1.0
            p.drawLine(QPointF(cx, cy), QPointF(cx + math.sin(ang) * cr * 0.75, cy - math.cos(ang) * cr * 0.75))
            p.drawLine(QPointF(cx, cy), QPointF(cx + math.sin(ang / 12) * cr * 0.5, cy - math.cos(ang / 12) * cr * 0.5))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(self._dark("#F6EEDC"))
            for i in range(5):
                p.drawRect(QRectF(x + bw * (0.08 + i * 0.2), y + bh * 0.42, bw * 0.05, bh * 0.5))
            self._windows(p, QRectF(x + bw * 0.02, y + bh * 0.44, bw * 0.96, bh * 0.4), 8, 2, 0,
                          self._dark("#9FB8CF", 0.35), lit, gap=0.5, seed=3)
            p.setBrush(self._dark("#8A5A3C"))
            p.drawRect(QRectF(x + bw * 0.44, y + bh * 0.78, bw * 0.12, bh * 0.22))
        elif key == "bank":
            p.setBrush(self._dark("#ECE8E0"))
            p.drawRect(QRectF(x, y + bh * 0.3, bw, bh * 0.62))
            p.setBrush(self._dark("#DCD6CA"))
            p.drawRect(QRectF(x - bw * 0.03, y + bh * 0.9, bw * 1.06, bh * 0.1))                 # steps
            p.drawRect(QRectF(x - bw * 0.02, y + bh * 0.24, bw * 1.04, bh * 0.07))
            p.setBrush(self._dark("#C9C1B1"))
            p.drawPolygon([QPointF(x - bw * 0.04, y + bh * 0.25), QPointF(x + bw * 0.5, y),
                           QPointF(x + bw * 1.04, y + bh * 0.25)])
            self._snow_cap(p, [QPointF(x + bw * 0.1, y + bh * 0.2), QPointF(x + bw * 0.5, y),
                               QPointF(x + bw * 0.9, y + bh * 0.2), QPointF(x + bw * 0.5, y + bh * 0.05)])
            p.setBrush(QColor("#E5B83B"))
            p.drawEllipse(QPointF(x + bw * 0.5, y + bh * 0.15), bh * 0.065, bh * 0.065)
            p.setPen(QPen(QColor("#8A6A12"), 2))
            p.setFont(make_font(max(12, int(bh * 0.09)), W_BOLD))
            p.drawText(QRectF(x + bw * 0.5 - bh * 0.07, y + bh * 0.08, bh * 0.14, bh * 0.14),
                       Qt.AlignmentFlag.AlignCenter, "$")
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(self._dark("#FBF9F4"))
            for i in range(5):
                p.drawRect(QRectF(x + bw * (0.07 + i * 0.2), y + bh * 0.33, bw * 0.07, bh * 0.56))
            p.setBrush(self._dark("#4B5563"))
            p.drawRect(QRectF(x + bw * 0.43, y + bh * 0.62, bw * 0.14, bh * 0.28))
        elif key == "home":
            body = QRectF(x + bw * 0.08, y + bh * 0.38, bw * 0.84, bh * 0.62)
            p.setBrush(self._dark("#B0463F"))
            p.drawRect(QRectF(x + bw * 0.66, y + bh * 0.04, bw * 0.1, bh * 0.25))              # chimney
            p.setBrush(self._dark("#F4C9A2"))
            p.drawRect(body)
            p.setBrush(self._dark("#C2524A"))
            roof = [QPointF(x, y + bh * 0.42), QPointF(x + bw * 0.5, y), QPointF(x + bw, y + bh * 0.42)]
            p.drawPolygon(roof)
            self._snow_cap(p, [QPointF(x + bw * 0.1, y + bh * 0.33), QPointF(x + bw * 0.5, y),
                               QPointF(x + bw * 0.9, y + bh * 0.33), QPointF(x + bw * 0.5, y + bh * 0.08)])
            if self.animate:                                                               # chimney smoke
                for i in range(3):
                    t = (self.phase * 0.35 + i / 3) % 1
                    c = QColor(235, 235, 235, int(150 * (1 - t)))
                    p.setBrush(c)
                    p.drawEllipse(QPointF(x + bw * 0.71 + math.sin(t * 6) * bw * 0.03, y + bh * (0.02 - t * 0.35)),
                                  bh * (0.03 + t * 0.04), bh * (0.03 + t * 0.04))
            p.setBrush(self._dark("#7A4B2E"))
            p.drawRoundedRect(QRectF(x + bw * 0.43, y + bh * 0.66, bw * 0.15, bh * 0.34), 6, 6)
            win = QColor(lit) if self.night else self._dark("#BFE0F5")
            p.setBrush(win)
            for wx in (0.17, 0.66):
                p.drawRoundedRect(QRectF(x + bw * wx, y + bh * 0.52, bw * 0.17, bh * 0.2), 4, 4)
            p.setBrush(self._dark(SEASONS[self.quarter]["tree2"]))
            p.drawEllipse(QPointF(x + bw * 0.08, y + bh * 0.92), bw * 0.08, bh * 0.1)                 # bush
            p.drawEllipse(QPointF(x + bw * 0.93, y + bh * 0.93), bw * 0.07, bh * 0.09)
        elif key == "grocery":
            body = QRectF(x, y + bh * 0.22, bw, bh * 0.78)
            p.setBrush(self._dark("#FFF4E2"))
            p.drawRect(body)
            p.setBrush(self._dark("#3E8E5B"))
            p.drawRect(QRectF(x - bw * 0.02, y + bh * 0.12, bw * 1.04, bh * 0.12))
            stripes = 8
            sw = bw * 1.04 / stripes
            for i in range(stripes):                                                       # awning
                p.setBrush(self._dark("#3E8E5B" if i % 2 == 0 else "#F7F3EA"))
                sx = x - bw * 0.02 + i * sw
                p.drawRect(QRectF(sx, y + bh * 0.24, sw, bh * 0.12))
                p.drawEllipse(QPointF(sx + sw / 2, y + bh * 0.36), sw / 2, bh * 0.04)
            self._snow_cap(p, [QPointF(x - bw * 0.02, y + bh * 0.12), QPointF(x + bw * 1.02, y + bh * 0.12),
                               QPointF(x + bw * 1.02, y + bh * 0.15), QPointF(x - bw * 0.02, y + bh * 0.15)])
            p.setBrush(QColor(lit) if self.night else self._dark("#CFE8F5"))
            shop = QRectF(x + bw * 0.06, y + bh * 0.48, bw * 0.54, bh * 0.36)
            p.drawRoundedRect(shop, 6, 6)
            for i in range(10):                                                            # produce
                p.setBrush(QColor(["#E5533D", "#F2A93B", "#7CB342", "#F7D046"][i % 4]))
                p.drawEllipse(QPointF(shop.x() + shop.width() * (0.08 + 0.093 * i), shop.bottom() - bh * 0.05),
                              bh * 0.035, bh * 0.035)
            p.setBrush(self._dark("#3E8E5B"))
            p.drawRoundedRect(QRectF(x + bw * 0.7, y + bh * 0.52, bw * 0.2, bh * 0.48), 6, 6)
            p.setBrush(self._dark("#9ED1E6"))
            p.drawRect(QRectF(x + bw * 0.73, y + bh * 0.56, bw * 0.14, bh * 0.2))
        elif key == "fun":
            t = SEASONS[self.quarter]
            cx, cy, R = x + bw * 0.58, y + bh * 0.4, bh * 0.38
            p.setBrush(self._dark("#8E7CC3"))
            p.drawPolygon([QPointF(cx, cy), QPointF(cx - R * 0.55, y + bh), QPointF(cx - R * 0.4, y + bh)])
            p.drawPolygon([QPointF(cx, cy), QPointF(cx + R * 0.55, y + bh), QPointF(cx + R * 0.4, y + bh)])
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(self._dark("#6A55B0"), max(3.0, R * 0.05)))
            p.drawEllipse(QPointF(cx, cy), R, R)
            rot = self.phase * 0.35 if self.animate else 0.3
            colors = ["#EF5B5B", "#F5B83D", "#4FB6E8", "#7AC36A", "#E36BB4", "#F08A3C"]
            for i in range(6):
                a = rot + i * math.pi / 3
                px, py = cx + math.cos(a) * R, cy + math.sin(a) * R
                p.setPen(QPen(self._dark("#6A55B0"), max(2.0, R * 0.03)))
                p.drawLine(QPointF(cx, cy), QPointF(px, py))
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(self._dark(colors[i]))
                p.drawRoundedRect(QRectF(px - R * 0.13, py - R * 0.02, R * 0.26, R * 0.22), 5, 5)
            p.setBrush(self._dark("#F5B83D"))
            p.drawEllipse(QPointF(cx, cy), R * 0.09, R * 0.09)
            p.setBrush(self._dark("#FFF2F0"))                                              # ticket booth
            p.drawRect(QRectF(x + bw * 0.02, y + bh * 0.66, bw * 0.24, bh * 0.34))
            for i in range(4):
                p.setBrush(self._dark("#E35D5D" if i % 2 == 0 else "#FFFFFF"))
                p.drawRect(QRectF(x + bw * (0.0 + i * 0.07), y + bh * 0.6, bw * 0.07, bh * 0.08))
            p.setBrush(QColor(lit) if self.night else self._dark("#BFE0F5"))
            p.drawRect(QRectF(x + bw * 0.07, y + bh * 0.74, bw * 0.14, bh * 0.1))
            for tx, k in ((0.94, 1.0), (0.34, 0.8)):                                       # trees
                p.setBrush(self._dark("#7A5236"))
                p.drawRect(QRectF(x + bw * tx - bw * 0.012, y + bh * (1 - 0.22 * k), bw * 0.024, bh * 0.22 * k))
                p.setBrush(self._dark(t["tree"]))
                p.drawEllipse(QPointF(x + bw * tx, y + bh * (1 - 0.27 * k)), bw * 0.07 * k, bh * 0.11 * k)

    def _particles(self, p, w, h):
        """Snow in winter, petals in spring, leaves in autumn (static when animation is off)."""
        if self.quarter == 3:
            return
        p.setPen(Qt.PenStyle.NoPen)
        n = {1: 60, 2: 22, 4: 26}[self.quarter]
        for i in range(n):
            speed = 0.03 + 0.04 * _rand(i, 11)
            t = (_rand(i, 12) + self.phase * speed) % 1.0
            x = (_rand(i, 13) * w + math.sin(self.phase * 1.3 + i) * w * 0.015) % w
            y = t * h
            if self.quarter == 1:
                p.setBrush(QColor(255, 255, 255, 220))
                r = 2.5 + 3 * _rand(i, 14)
                p.drawEllipse(QPointF(x, y), r, r)
            else:
                col = QColor("#F7B6D2") if self.quarter == 2 else QColor(["#E2793A", "#C05329", "#E8A93B"][i % 3])
                p.setBrush(col)
                p.save()
                p.translate(x, y)
                p.rotate((self.phase * 90 + i * 40) % 360)
                p.drawEllipse(QRectF(-7, -4, 14, 8))
                p.restore()

    def _sign_and_badge(self, p, key):
        name, row, *_ = LOC[key]
        r = self.building_rect(key)
        h = self.height()
        if key == self.selected or key == self.hover:
            sel = key == self.selected
            c = QColor(T["accent"]) if sel else QColor(255, 255, 255, 200)
            p.setPen(QPen(c, 6 if sel else 4))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(r.adjusted(-12, -16, 12, 10), 22, 22)
        px = max(15, int(h * 0.027))
        font = make_font(px, W_BOLD)
        p.setFont(font)
        tw = p.fontMetrics().horizontalAdvance(name) + px * 1.4
        th = px * 1.75
        sx = r.center().x() - tw / 2
        sy = r.bottom() + h * 0.008 if row == "back" else r.bottom() - th - h * 0.012
        if row == "back":
            sy = min(sy, h * ROAD_TOP - th - 2)
        sel = key == self.selected
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(T["accent"]) if sel else QColor(20, 24, 33, 215))
        p.drawRoundedRect(QRectF(sx, sy, tw, th), th / 2, th / 2)
        p.setPen(QColor(T["accent_text"]) if sel else QColor("#FFFFFF"))
        p.drawText(QRectF(sx, sy, tw, th), Qt.AlignmentFlag.AlignCenter, name)

        kind = self.badges.get(key)
        if not kind:
            return
        br = max(16.0, h * 0.026)
        right = r.x() + r.width() * 0.68 if key == "office" else r.right()
        bx, by = right - br * 0.2, r.top() + br * 0.4
        if self.animate and kind in ("todo", "due"):
            by -= abs(math.sin(self.phase * 3)) * br * 0.35
        fill, text = {"todo": ("#EF4444", "!"), "due": ("#F59E0B", "$"), "done": ("#22C55E", "✓"),
                      "sleep": ("#6366F1", "z")}[kind]
        p.setPen(QPen(QColor("#FFFFFF"), 3))
        p.setBrush(QColor(fill))
        p.drawEllipse(QPointF(bx, by), br, br)
        f = make_font(int(br * 1.15), W_BOLD)
        f.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        p.setFont(f)
        p.drawText(QRectF(bx - br, by - br, 2 * br, 2 * br), Qt.AlignmentFlag.AlignCenter, text)

    # ----------------------------------------------------------- avatar ---
    def _avatar(self, p, w, h):
        fx, fy = self.feet
        x, y = fx * w, fy * h
        s = h * 0.11
        walking = self.walking
        swing = math.sin(self.phase * 14) if walking else 0.0
        bob = abs(math.sin(self.phase * 14)) * s * 0.03 if walking else 0.0
        y -= bob
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 55))
        p.drawEllipse(QPointF(x, fy * h), s * 0.22, s * 0.05)
        leg = QPen(QColor("#2F3A56"), s * 0.09, cap=Qt.PenCapStyle.RoundCap)
        p.setPen(leg)
        hip = QPointF(x, y - s * 0.36)
        p.drawLine(hip, QPointF(x - s * 0.06 + swing * s * 0.12, y - s * 0.02))
        p.drawLine(hip, QPointF(x + s * 0.06 - swing * s * 0.12, y - s * 0.02))
        shirt = QColor("#F06449") if self.age < 40 else QColor("#4F8FCB") if self.age < 55 else QColor("#7E6BC4")
        p.setPen(QPen(QColor("#F2C29B"), s * 0.07, cap=Qt.PenCapStyle.RoundCap))
        sh = QPointF(x, y - s * 0.66)
        p.drawLine(sh, QPointF(x - s * 0.17 - swing * s * 0.08, y - s * 0.4))
        p.drawLine(sh, QPointF(x + s * 0.17 + swing * s * 0.08, y - s * 0.4))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(shirt)
        p.drawRoundedRect(QRectF(x - s * 0.15, y - s * 0.72, s * 0.3, s * 0.4), s * 0.1, s * 0.1)
        p.setBrush(QColor("#F2C29B"))
        head = QPointF(x, y - s * 0.86)
        p.drawEllipse(head, s * 0.14, s * 0.14)
        hair = QColor("#3B2A20") if self.age < 45 else QColor("#8C8C8C") if self.age < 58 else QColor("#D9D9D9")
        p.setBrush(hair)
        p.drawChord(QRectF(head.x() - s * 0.15, head.y() - s * 0.16, s * 0.3, s * 0.26), 0, 180 * 16)
        p.setBrush(QColor("#1F2433"))
        p.drawEllipse(QPointF(head.x() + self.facing * s * 0.05, head.y() + s * 0.01), s * 0.018, s * 0.018)
