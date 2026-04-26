from src.agent import Yiujarvis
from src.app_index import ensure_apps_index
from src.memory_store import load_memory


def run(provider="githubmodel"):
    ensure_apps_index()
    Yiujarvis(load_memory(), provider=provider)