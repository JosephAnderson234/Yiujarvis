import difflib
import json
import os
from pathlib import Path


APP_INDEX_FILE = Path("apps_index.json")
APP_INDEX_VERSION = 2


def normalize_app_key(value):
    return "".join(character for character in value.lower() if character.isalnum())

SEARCH_PATHS = [
    Path("C:/Program Files"),
    Path("C:/Program Files (x86)"),
    Path("C:/ProgramData/Microsoft/Windows/Start Menu/Programs"),
    Path(os.getenv("PROGRAMDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
    Path(os.getenv("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
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

STANDARD_APP_ALIASES = {
    "fileexplorer",
    "microsoftaccess",
    "microsoftedge",
    "microsoftnotepad",
    "microsoftonenote",
    "microsoftoutlook",
    "microsoftpowerpoint",
    "microsoftsettings",
    "microsoftteams",
    "microsoftvisio",
    "microsoftword",
    "windowsterminal",
}

USEFUL_APP_KEYS = {normalize_app_key(name) for name in USEFUL_APP_NAMES} | STANDARD_APP_ALIASES

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
    normalized_key = normalize_app_key(normalized_name)
    base_key = normalize_app_key(base_name)

    if any(fragment in normalized_name for fragment in IGNORED_NAME_FRAGMENTS):
        return False

    if normalized_key in USEFUL_APP_KEYS:
        return True

    return base_key in USEFUL_APP_KEYS


def _iter_app_candidates(base_path):
    for root, _, files in os.walk(base_path, onerror=lambda _: None):
        for file_name in files:
            lower_name = file_name.lower()
            if lower_name.endswith((".exe", ".lnk")):
                yield root, file_name


def index_apps():
    apps = {}

    for base_path in SEARCH_PATHS:
        if not base_path.exists():
            continue

        for root, file_name in _iter_app_candidates(base_path):
            app_name = Path(file_name).stem.lower()
            full_path = os.path.join(root, file_name)

            if app_name not in apps and is_useful_app(app_name, full_path):
                apps[app_name] = full_path

    with APP_INDEX_FILE.open("w", encoding="utf-8") as file_handle:
        json.dump({"version": APP_INDEX_VERSION, "apps": apps}, file_handle, indent=2, ensure_ascii=False)

    return apps


def load_index_payload():
    try:
        with APP_INDEX_FILE.open("r", encoding="utf-8") as file_handle:
            return json.load(file_handle)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def load_apps():
    payload = load_index_payload()

    if isinstance(payload, dict) and "apps" in payload:
        return payload["apps"] if isinstance(payload["apps"], dict) else {}

    return payload if isinstance(payload, dict) else {}


def find_best_match(app_name, apps):
    matches = difflib.get_close_matches(app_name, list(apps.keys()), n=1, cutoff=0.4)
    return matches[0] if matches else None


def ensure_apps_index():
    payload = load_index_payload()

    if not payload:
        print("🔎 Indexando aplicaciones (esto tarda un poco)...")
        index_apps()
        print("✅ Apps indexadas")
        return

    apps = load_apps()
    if (
        not isinstance(payload, dict)
        or payload.get("version") != APP_INDEX_VERSION
        or not isinstance(payload.get("apps"), dict)
        or not apps
        or any(not is_useful_app(app_name, full_path) for app_name, full_path in apps.items())
    ):
        print("🔄 Reindexando aplicaciones útiles...")
        index_apps()
        print("✅ Apps útiles indexadas")