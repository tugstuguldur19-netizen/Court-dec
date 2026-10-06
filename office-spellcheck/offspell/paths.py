"""Where dictionaries, the personal dictionary and settings live."""

import json
import os
import sys

APP_NAME = "OfficeSpellcheck"


def _package_root():
    if getattr(sys, "frozen", False):
        # PyInstaller: bundled data sits in sys._MEIPASS
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def user_dir():
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, APP_NAME)
    if sys.platform == "darwin":
        return os.path.join(os.path.expanduser("~/Library/Application Support"), APP_NAME)
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, "office-spellcheck")


def dictionary_folders():
    """Bundled dictionaries first, then a folder next to the .exe, then the
    user's own folder. Drop extra .aff/.dic pairs or .txt word lists into
    either of the last two."""
    folders = [os.path.join(_package_root(), "dictionaries")]
    if getattr(sys, "frozen", False):
        folders.append(os.path.join(os.path.dirname(sys.executable), "dictionaries"))
    folders.append(os.path.join(user_dir(), "dictionaries"))
    seen, out = set(), []
    for f in folders:
        key = os.path.normcase(os.path.abspath(f))
        if key not in seen:
            seen.add(key)
            out.append(f)
    return out


def personal_dictionary():
    return os.path.join(user_dir(), "personal.txt")


def _settings_path():
    return os.path.join(user_dir(), "settings.json")


def load_settings():
    try:
        with open(_settings_path(), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_settings(data):
    try:
        os.makedirs(user_dir(), exist_ok=True)
        with open(_settings_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass
