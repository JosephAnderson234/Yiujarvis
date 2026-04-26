import difflib
import json
import os
from pathlib import Path


APP_INDEX_FILE = Path("apps_index.json")

SEARCH_PATHS = [
    Path("C:/Program Files"),
    Path("C:/Program Files (x86)"),
    Path(os.getenv("LOCALAPPDATA", "")),
    Path(os.getenv("APPDATA", "")),
]

USEFUL_APP_NAMES = {
    "brave",
    "calc",
    "calculator",
    "chrome",
    "cmd",
    "code",
    "discord",
    "edge",
    "epicgameslauncher",
    "explorer",
    "firefox",
    "msedge",
    "msaccess",
    "notepad",
    "onenote",
    "opera",
    "outlook",
    "powershell",
    "powerpnt",
    "settings",
    "slack",
    "spotify",
    "steam",
    "studio64",
    "teams",
    "telegram",
    "visio",
    "vivaldi",
    "whatsapp.root",
    "whatsapp",
    "winword",
    "word",
    "wt",
}

IGNORED_NAME_FRAGMENTS = (
    "install",
    "setup",
    "unins",
    "update",
    "updater",
    "helper",
    "service",
    "crashpad",
    "runtime",
    "launcher",
    "maintenance",
    "repair",
    "diag",
    "telemetry",
    "uninstall",
    "proxy",
    "stub",
    "bridge",
    "loader",
    "broker",
    "surrogate",
    "converter",
    "cnv",
    "redist",
)


def is_useful_app(app_name, full_path):
    normalized_name = app_name.lower()
    base_name = normalized_name.split(".", 1)[0]

    if any(fragment in normalized_name for fragment in IGNORED_NAME_FRAGMENTS):
        return False

    if normalized_name in USEFUL_APP_NAMES:
        return True

    return base_name in USEFUL_APP_NAMES


def index_apps():
    apps = {}

    for base_path in SEARCH_PATHS:
        if not base_path.exists():
            continue

        for root, _, files in os.walk(base_path):
            for file_name in files:
                if file_name.endswith(".exe"):
                    app_name = file_name.removesuffix(".exe").lower()
                    full_path = os.path.join(root, file_name)

                    if app_name not in apps and is_useful_app(app_name, full_path):
                        apps[app_name] = full_path

    with APP_INDEX_FILE.open("w", encoding="utf-8") as file_handle:
        json.dump(apps, file_handle, indent=2, ensure_ascii=False)

    return apps


def load_apps():
    try:
        with APP_INDEX_FILE.open("r", encoding="utf-8") as file_handle:
            return json.load(file_handle)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def find_best_match(app_name, apps):
    matches = difflib.get_close_matches(app_name, list(apps.keys()), n=1, cutoff=0.4)
    return matches[0] if matches else None


def ensure_apps_index():
    if not APP_INDEX_FILE.exists():
        print("🔎 Indexando aplicaciones (esto tarda un poco)...")
        index_apps()
        print("✅ Apps indexadas")
        return

    apps = load_apps()
    if apps and any(not is_useful_app(app_name, full_path) for app_name, full_path in apps.items()):
        print("🔄 Reindexando aplicaciones útiles...")
        index_apps()
        print("✅ Apps útiles indexadas")