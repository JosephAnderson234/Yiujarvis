import csv
import io
import json
import os
import shutil
import subprocess

import requests

from src.app_index import find_best_match, load_apps
from src.error_logger import ensure_error_logging, log_exception
from src.memory_store import load_memory, save_memory, set_preference


SYSTEM_ALIASES = {
    "explorador de archivos": "explorer",
    "file explorer": "explorer",
    "explorer": "explorer",
    "calculadora": "calculator",
    "notepad": "notepad",
    "bloc de notas": "notepad",
    "cmd": "cmd",
    "terminal": "wt",
    "powershell": "powershell",
    "configuracion": "ms-settings:",
    "settings": "ms-settings:",
}

IGNORED_OPEN_WINDOW_PROCESSES = {
    "applicationframehost",
    "lockapp",
    "searchhost",
    "shellhost",
    "shellexperiencehost",
    "startmenuexperiencehost",
    "systemsettings",
    "texthost",
    "textinputhost",
    "runtimebroker",
    "widgets",
    "msedgewebview2",
}


BLACKLISTED_PROCESS_NAMES = {
    "explorer",
    "explorer.exe",
    "system",
    "system.exe",
    "wininit",
    "wininit.exe",
    "csrss",
    "csrss.exe",
    "winlogon",
    "winlogon.exe",
}


WINDOWS_SILENT_FLAGS = 0
if hasattr(subprocess, "DETACHED_PROCESS"):
    WINDOWS_SILENT_FLAGS |= subprocess.DETACHED_PROCESS
if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
    WINDOWS_SILENT_FLAGS |= subprocess.CREATE_NEW_PROCESS_GROUP


ensure_error_logging()


def launch_silently(command):
    return subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        creationflags=WINDOWS_SILENT_FLAGS,
        shell=False,
    )


def _open_windows_target(target):
    if target.startswith("http") or target.startswith("ms-settings:"):
        os.startfile(target)
        return

    if os.path.exists(target):
        os.startfile(target)
        return

    launch_silently(["cmd", "/c", "start", "", target])


WEATHER_CODES = {
    0: "despejado",
    1: "mayormente despejado",
    2: "parcialmente nublado",
    3: "nublado",
    45: "niebla",
    48: "niebla con escarcha",
    51: "llovizna ligera",
    53: "llovizna",
    55: "llovizna intensa",
    61: "lluvia ligera",
    63: "lluvia",
    65: "lluvia intensa",
    71: "nieve ligera",
    73: "nieve",
    75: "nieve intensa",
    80: "chubascos ligeros",
    81: "chubascos",
    82: "chubascos violentos",
    95: "tormenta",
    96: "tormenta con granizo",
    99: "tormenta fuerte con granizo",
}


def _geocode_city(city):
    response = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city, "count": 1, "language": "es"},
        timeout=8,
    )
    response.raise_for_status()
    results = response.json().get("results") or []
    if not results:
        return None

    place = results[0]
    label = ", ".join(part for part in (place.get("name"), place.get("country")) if part)
    return place["latitude"], place["longitude"], label


def _locate_by_ip():
    response = requests.get("https://ipapi.co/json/", timeout=8)
    response.raise_for_status()
    data = response.json()
    label = ", ".join(part for part in (data.get("city"), data.get("country_name")) if part)
    return data["latitude"], data["longitude"], label or "tu ubicación"


def get_weather(city=""):
    try:
        location = _geocode_city(city) if city.strip() else _locate_by_ip()
        if location is None:
            return f"No encontré la ciudad {city}"

        latitude, longitude, label = location
        response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m",
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                "forecast_days": 1,
                "timezone": "auto",
            },
            timeout=8,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        log_exception(f"Error consultando el clima de {city or 'la ubicación actual'}")
        return f"No pude consultar el clima: {exc}"

    current = data.get("current", {})
    daily = data.get("daily", {})
    condition = WEATHER_CODES.get(current.get("weather_code"), "condición desconocida")

    def _first(values):
        return values[0] if values else "?"

    return (
        f"{label}: {current.get('temperature_2m')}°C (sensación {current.get('apparent_temperature')}°C), "
        f"{condition}, humedad {current.get('relative_humidity_2m')}%, viento {current.get('wind_speed_10m')} km/h. "
        f"Hoy: mín {_first(daily.get('temperature_2m_min', []))}°C / máx {_first(daily.get('temperature_2m_max', []))}°C, "
        f"probabilidad de lluvia {_first(daily.get('precipitation_probability_max', []))}%."
    )


def _normalize_process_name(process_name):
    normalized = process_name.lower().strip()
    return normalized if normalized.endswith(".exe") else f"{normalized}.exe"


def _get_open_window_processes():
    command = (
        "Get-Process | "
        "Where-Object { $_.MainWindowHandle -ne 0 -and $_.MainWindowTitle } | "
        "Select-Object Id,ProcessName,MainWindowTitle | "
        "ConvertTo-Json -Depth 2"
    )

    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
        errors="replace",
    )

    payload = completed.stdout.strip()
    if not payload:
        return []

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return []

    if isinstance(data, dict):
        data = [data]

    processes = []
    for item in data:
        if not isinstance(item, dict):
            continue

        process_name = item.get("ProcessName", "")
        window_title = item.get("MainWindowTitle", "")
        pid = item.get("Id")

        if not process_name or not window_title or pid is None:
            continue

        if process_name.lower() in IGNORED_OPEN_WINDOW_PROCESSES:
            continue

        processes.append(
            {
                "name": process_name,
                "pid": str(pid),
                "window_title": window_title,
            }
        )

    return processes


def list_running_processes(limit=30):
    processes = _get_open_window_processes()[: max(1, int(limit))]
    return json.dumps(processes, ensure_ascii=False, indent=2)


def close_program(process_name):
    process_name = process_name.strip()
    normalized_target = process_name.lower().strip()

    if normalized_target in BLACKLISTED_PROCESS_NAMES:
        return f"No se permite cerrar {process_name}"

    target_processes = _get_open_window_processes()

    if not target_processes:
        return "No hay apps abiertas para cerrar"

    exact_matches = [
        process
        for process in target_processes
        if normalized_target in {process["name"].lower(), process["window_title"].lower()}
        or normalized_target in process["window_title"].lower()
    ]

    if exact_matches:
        target_process = exact_matches[0]
    else:
        names = [process["name"] for process in target_processes]
        match = find_best_match(normalized_target, {name: name for name in names})
        target_process = next((process for process in target_processes if process["name"] == match), None)

    if not target_process:
        available = ", ".join(process["name"] for process in target_processes[:10])
        return f"No encontré una app abierta que coincida con {process_name}. Abiertas ahora: {available}"

    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", f"Stop-Process -Id {target_process['pid']} -Force"],
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
        errors="replace",
    )

    if completed.returncode == 0:
        return f"Programa cerrado: {target_process['name']}"

    message = completed.stderr.strip() or completed.stdout.strip() or "No se pudo cerrar el proceso"
    return f"No se pudo cerrar {target_process['name']}: {message}"


def open_app(app):
    app = app.lower().strip()
    apps = load_apps()
    target = SYSTEM_ALIASES.get(app, app)

    match = find_best_match(target, apps)

    try:
        if match:
            _open_windows_target(apps[match])
            return f"Abriendo {match}..."

        if target.startswith("http"):
            os.startfile(target)
            return f"Abriendo {target}..."

        if target.startswith("ms-settings:"):
            os.startfile(target)
            return f"Abriendo {app}..."

        if target in SYSTEM_ALIASES.values():
            _open_windows_target(target)
            return f"Abriendo {app}..."

        executable = shutil.which(target)
        if executable:
            _open_windows_target(executable)
            return f"Abriendo {app}..."

        _open_windows_target(target)
        return f"Intentando abrir {app}..."
    except Exception as exc:
        log_exception(f"Error abriendo app {app}")
        return f"No se pudo abrir {app}: {exc}"


def preview_close_program(process_name):
    process_name = process_name.strip()
    normalized_target = process_name.lower().strip()

    if normalized_target in BLACKLISTED_PROCESS_NAMES:
        return f"No se permite cerrar {process_name}"

    return f"Cerraría {process_name} si se confirma"


def save_user_preference(key, value):
    memory = load_memory()
    memory = set_preference(memory, key, value)
    save_memory(memory)
    return f"Guardado: {key} = {value}"