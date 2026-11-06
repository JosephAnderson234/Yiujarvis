from src.agent import Yiujarvis
from src.app_index import ensure_apps_index
from src.core.agent_loop import build_tool_registry
from src.memory_store import MemorySession, load_memory
from src.terminal_ui import show_banner, show_startup_status


def run(provider="githubmodel"):
    ensure_apps_index()
    memory_session = MemorySession(load_memory())
    registry = build_tool_registry(memory_session)
    show_banner()
    show_startup_status(provider, len(registry.get_available_tools()))
    Yiujarvis(memory_session, provider=provider, registry=registry)
