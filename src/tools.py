import csv
import io
import json
import os
import shutil
import subprocess

from src.app_index import find_best_match, load_apps
from src.memory_store import load_memory, save_memory


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


WINDOWS_SILENT_FLAGS = 0
if hasattr(subprocess, "DETACHED_PROCESS"):
    WINDOWS_SILENT_FLAGS |= subprocess.DETACHED_PROCESS
if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
    WINDOWS_SILENT_FLAGS |= subprocess.CREATE_NEW_PROCESS_GROUP


def launch_silently(command):
    return subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        creationflags=WINDOWS_SILENT_FLAGS,
        shell=False,
    )


def get_weather():
    return "Hace 22°C y está soleado"


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
            launch_silently([apps[match]])
            return f"Abriendo {match}..."

        if target.startswith("http"):
            os.startfile(target)
            return f"Abriendo {target}..."

        if target.startswith("ms-settings:"):
            os.startfile(target)
            return f"Abriendo {app}..."

        if target in SYSTEM_ALIASES.values():
            launch_silently(["cmd", "/c", "start", "", target])
            return f"Abriendo {app}..."

        executable = shutil.which(target)
        if executable:
            launch_silently([executable])
            return f"Abriendo {app}..."

        launch_silently(["cmd", "/c", "start", "", target])
        return f"Intentando abrir {app}..."
    except Exception as exc:
        return f"No se pudo abrir {app}: {exc}"


def save_user_preference(key, value):
    memory = load_memory()
    memory[key] = value
    save_memory(memory)
    return f"Guardado: {key} = {value}"