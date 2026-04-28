import importlib.util
from pathlib import Path

from src.error_logger import log_exception


def _load_module_from_path(module_path):
    spec = importlib.util.spec_from_file_location(module_path.stem, module_path)
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_plugins(registry, plugins_root="plugins"):
    root_path = Path(plugins_root)

    if not root_path.exists():
        return []

    loaded_plugins = []

    for plugin_file in root_path.glob("*/plugin.py"):
        try:
            module = _load_module_from_path(plugin_file)
            if module is None:
                continue

            register_tools = getattr(module, "register_tools", None)
            if callable(register_tools):
                register_tools(registry)
                loaded_plugins.append(plugin_file.parent.name)
        except Exception:
            log_exception(f"Error cargando plugin {plugin_file.parent.name}")

    return loaded_plugins