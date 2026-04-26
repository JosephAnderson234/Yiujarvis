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