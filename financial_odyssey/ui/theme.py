"""Canvas sizes, light/dark colour themes, fonts and the Qt stylesheet."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont

# Mobile: 1080x1920 portrait canvas.
# Desktop: 2880x1620 landscape canvas (1.5x a 1080p screen). Elements use the same pixel
# sizes as mobile, so on a desktop monitor they appear ~1/3 smaller with much more
# whitespace (desktop type scale: ~14-16px body, ~28-32px figures; 8pt spacing grid with
# 16-24px card padding, ~24px card gaps and ~64px page margins at 1x).
CANVAS = {"mobile": (1080, 1920), "desktop": (2880, 1620)}

_TINTS_LIGHT = {  # name: (background, hover background, text)
    "blue":   ("#E0E7FF", "#C7D2FE", "#312E81"),
    "purple": ("#EDE9FE", "#DDD6FE", "#4C1D95"),
    "amber":  ("#FEF3C7", "#FDE68A", "#78350F"),
    "teal":   ("#CCFBF1", "#99F6E4", "#134E4A"),
    "green":  ("#DCFCE7", "#BBF7D0", "#14532D"),
    "red":    ("#FEE2E2", "#FECACA", "#7F1D1D"),
    "pink":   ("#FCE7F3", "#FBCFE8", "#831843"),
    "slate":  ("#F1F2F5", "#E4E6EB", "#1F2937"),
}
_TINTS_DARK = {
    "blue":   ("#23274A", "#2E3363", "#C7D2FE"),
    "purple": ("#2A2347", "#362D5C", "#DDD6FE"),
    "amber":  ("#33270F", "#443416", "#FDE68A"),
    "teal":   ("#0F2E2B", "#153F3A", "#99F6E4"),
    "green":  ("#11301D", "#174027", "#BBF7D0"),
    "red":    ("#3A1717", "#4B1E1E", "#FECACA"),
    "pink":   ("#3A1A2A", "#4B2237", "#FBCFE8"),
    "slate":  ("#20242D", "#2B303B", "#E5E7EB"),
}
THEMES = {
    "light": dict(
        bg_top="#F4F5F7", bg_bot="#E6E9EE", card="#FFFFFF", border="#E7E9ED", border_strong="#CDD2DA",
        surface="#F4F5F8", text="#0F1115", text2="#374151", muted="#6B7280", dim="#A3A9B5", track="#ECEEF2",
        primary="#111317", primary_hover="#2B2E35", primary_text="#FFFFFF",
        accent="#4F46E5", accent_hover="#4338CA", accent_text="#FFFFFF",
        danger="#DC2626", danger_hover="#B91C1C", danger_text="#FFFFFF",
        modal="#FFFFFF", modal_border="#E7E9ED", overlay=(17, 19, 24, 110), coach=(10, 12, 18, 150),
        disabled_bg="#F1F2F4", disabled_text="#B4BAC4",
        green="#16A34A", red="#DC2626", amber="#D97706", gold="#B7791F", blue="#4F46E5",
        purple="#7C3AED", teal="#0D9488", lime="#65A30D", pink="#DB2777",
        seg_fill="#A5B4FC", tints=_TINTS_LIGHT, solid_green_text="#FFFFFF"),
    "dark": dict(
        bg_top="#0F1116", bg_bot="#07080B", card="#16191F", border="#242832", border_strong="#3D4350",
        surface="#1D2129", text="#F4F5F7", text2="#D1D5DB", muted="#9CA3AF", dim="#5F6673", track="#232833",
        primary="#F4F5F7", primary_hover="#FFFFFF", primary_text="#0F1115",
        accent="#818CF8", accent_hover="#A5B4FC", accent_text="#0B0D2A",
        danger="#F87171", danger_hover="#FCA5A5", danger_text="#1A0505",
        modal="#16191F", modal_border="#2B303B", overlay=(0, 0, 0, 170), coach=(0, 0, 0, 185),
        disabled_bg="#1A1D23", disabled_text="#4B5160",
        green="#4ADE80", red="#F87171", amber="#FBBF24", gold="#FACC15", blue="#818CF8",
        purple="#A78BFA", teal="#2DD4BF", lime="#A3E635", pink="#F472B6",
        seg_fill="#818CF8", tints=_TINTS_DARK, solid_green_text="#06210F"),
}
T = dict(THEMES["light"])          # the active theme; mutated in place on switch


def use_theme(name):
    T.clear()
    T.update(THEMES.get(name, THEMES["light"]))


def rgba(hex_color, alpha):
    c = QColor(hex_color)
    return f"rgba({c.red()},{c.green()},{c.blue()},{alpha})"


FAMILIES = ["Segoe UI", "SF Pro Display", "Inter", "Helvetica Neue", "Roboto",
            "Noto Sans", "Arial", "DejaVu Sans"]
W_LIGHT, W_NORMAL, W_MED, W_SEMI, W_BOLD = (QFont.Weight.Light, QFont.Weight.Normal, QFont.Weight.Medium,
                                            QFont.Weight.DemiBold, QFont.Weight.Bold)
AL_C = Qt.AlignmentFlag.AlignCenter
AL_L = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
AL_R = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter


def make_font(px, weight=W_NORMAL):
    f = QFont()
    f.setFamilies(FAMILIES)
    f.setPixelSize(int(px))            # pixel sizes => identical layout at any DPI
    f.setWeight(weight)
    f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    if hasattr(f, "setFeature"):
        f.setFeature(QFont.Tag("tnum"), 1)   # tabular figures: every digit has the same width
    return f


def set_color(lb, color):
    lb.setStyleSheet(f"color:{color}; background:transparent;")


def build_stylesheet():
    t = T
    qss = [f"""
    QWidget#root {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {t['bg_top']}, stop:1 {t['bg_bot']}); }}
    QFrame#card {{ background-color:{t['card']}; border:1px solid {t['border']}; border-radius:32px; }}
    QFrame#tile, QFrame#soft, QFrame#infobox {{ background-color:{t['surface']}; border:none; border-radius:24px; }}
    QFrame#modal {{ background-color:{t['modal']}; border:1px solid {t['modal_border']}; border-radius:40px; }}
    QFrame#bubble {{ background-color:{t['modal']}; border:3px solid {t['accent']}; border-radius:32px; }}
    QFrame#segwrap {{ background-color:{t['surface']}; border:none; border-radius:30px; }}
    QFrame#toast {{ background-color:{t['primary']}; border:none; border-radius:28px; }}
    QFrame#divider {{ background-color:{t['border']}; border:none; }}

    /* clickable buttons: solid fill or even outline, a hover state and a hand cursor */
    QPushButton {{ border-radius:22px; border:none; }}
    QPushButton QLabel {{ background:transparent; }}

    QPushButton[variant="primary"] {{ background:{t['primary']}; }}
    QPushButton[variant="primary"]:hover {{ background:{t['primary_hover']}; }}
    QPushButton[variant="primary"] QLabel {{ color:{t['primary_text']}; }}
    QPushButton[variant="accent"] {{ background:{t['accent']}; }}
    QPushButton[variant="accent"]:hover {{ background:{t['accent_hover']}; }}
    QPushButton[variant="accent"] QLabel {{ color:{t['accent_text']}; }}
    QPushButton[variant="danger"] {{ background:{t['danger']}; }}
    QPushButton[variant="danger"]:hover {{ background:{t['danger_hover']}; }}
    QPushButton[variant="danger"] QLabel {{ color:{t['danger_text']}; }}
    QPushButton[variant="solid_green"] {{ background:{t['green']}; }}
    QPushButton[variant="solid_green"]:hover {{ border:3px solid {t['text']}; }}
    QPushButton[variant="solid_green"] QLabel {{ color:{t['solid_green_text']}; }}

    QPushButton[variant="outline"], QPushButton[variant="soft"], QPushButton[variant="chip"] {{
        border:2px solid {t['border_strong']}; }}
    QPushButton[variant="outline"] {{ background:{t['card']}; }}
    QPushButton[variant="soft"], QPushButton[variant="chip"] {{ background:{t['surface']}; }}
    QPushButton[variant="outline"]:hover, QPushButton[variant="soft"]:hover, QPushButton[variant="chip"]:hover {{
        border-color:{t['text']}; }}
    QPushButton[variant="outline"] QLabel, QPushButton[variant="soft"] QLabel, QPushButton[variant="chip"] QLabel {{
        color:{t['text']}; }}

    QPushButton[variant="seg"] {{ background:transparent; border-radius:24px; }}
    QPushButton[variant="seg"]:hover {{ background:{t['card']}; }}
    QPushButton[variant="seg"] QLabel {{ color:{t['muted']}; }}
    QPushButton[variant="segon"] {{ background:{t['primary']}; border-radius:24px; }}
    QPushButton[variant="segon"] QLabel {{ color:{t['primary_text']}; }}

    QSpinBox {{ background-color:{t['card']}; color:{t['text']}; border:2px solid {t['border_strong']};
               border-radius:22px; padding:0px 6px; selection-background-color:{t['accent']}; }}
    QSpinBox:focus {{ border-color:{t['accent']}; }}
    QSpinBox::up-button, QSpinBox::down-button {{ width:0px; border:none; }}
    QSpinBox::up-arrow, QSpinBox::down-arrow {{ width:0px; height:0px; }}
    QCheckBox {{ color:{t['text2']}; spacing:14px; background:transparent; }}
    QCheckBox::indicator {{ width:32px; height:32px; border-radius:10px; border:3px solid {t['border_strong']};
                            background:{t['card']}; }}
    QCheckBox::indicator:hover {{ border-color:{t['accent']}; }}
    QCheckBox::indicator:checked {{ background:{t['accent']}; border-color:{t['accent']}; }}
    QScrollArea {{ background:transparent; border:none; }}
    QScrollArea > QWidget > QWidget {{ background:transparent; }}
    QScrollBar:vertical {{ width:12px; background:transparent; margin:4px; }}
    QScrollBar::handle:vertical {{ background:{t['border_strong']}; border-radius:4px; min-height:50px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background:transparent; }}
    QToolTip {{ background:{t['card']}; color:{t['text']}; border:1px solid {t['border']}; padding:6px; }}
    """]
    for name, (bg, hov, fg) in t["tints"].items():
        qss.append(f"""
        QFrame#tint_{name} {{ background-color:{bg}; border:none; border-radius:28px; }}
        QPushButton[variant="{name}"] {{ background:{bg}; border:2px solid {rgba(fg, 0.30)};
                                          }}
        QPushButton[variant="{name}"]:hover {{ background:{hov}; border-color:{rgba(fg, 0.6)}; }}
        QPushButton[variant="{name}"] QLabel {{ color:{fg}; }}
        """)
    # disabled = flat + dashed outline, so it reads as "not clickable right now"
    for name in list(t["tints"]) + ["primary", "accent", "danger", "outline", "soft", "chip", "solid_green"]:
        qss.append(f'QPushButton[variant="{name}"]:disabled {{ background:{t["disabled_bg"]}; '
                   f'border:2px dashed {t["border_strong"]}; }}'
                   f'QPushButton[variant="{name}"] QLabel:disabled {{ color:{t["disabled_text"]}; }}')
    return "\n".join(qss)
