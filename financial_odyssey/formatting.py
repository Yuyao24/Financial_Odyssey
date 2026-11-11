"""Small text helpers shared by the engine and the UI."""

import html


def money(v):
    v = int(v)
    return f"-${abs(v):,}" if v < 0 else f"${v:,}"


def esc(text):
    return html.escape(str(text))
