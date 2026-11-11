"""Where saves and settings live, and safe JSON read/write."""

import json
import os

from PyQt6.QtCore import QStandardPaths


def data_dir():
    d = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    if not d:
        d = os.path.join(os.path.expanduser("~"), ".financial_odyssey")
    os.makedirs(d, exist_ok=True)
    return d


def read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def write_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.replace(tmp, path)                 # atomic: a crash never leaves a half-written save
