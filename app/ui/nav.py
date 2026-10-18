"""Navigation structure shared by the window and the hotkey editor."""
from ..core.registry import CATEGORY_BY_KEY

# (group label or None, [(page key, title, icon)])
NAV = [
    (None, [("dashboard", "Overview", "dashboard")]),
    ("Control", [(k, CATEGORY_BY_KEY[k].title, k) for k in
                 ("player", "combat", "weapon", "fun", "vehicle", "players", "world", "inventory")]),
    ("Manage", [("settings", "Interface", "settings"), ("diag", "Diagnostics", "diag"),
                ("sec", "Security", "sec"), ("access", "Access", "access")]),
    ("Project", [("features", "Feature status", "features"), ("logs", "Logs", "logs")]),
]
PAGE_TITLES = {key: title for _, items in NAV for key, title, _ in items}
