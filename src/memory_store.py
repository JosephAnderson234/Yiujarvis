import json
from pathlib import Path


MEMORY_FILE = Path("memory.json")


def load_memory():
    try:
        with MEMORY_FILE.open("r", encoding="utf-8") as file_handle:
            return json.load(file_handle)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_memory(memory):
    with MEMORY_FILE.open("w", encoding="utf-8") as file_handle:
        json.dump(memory, file_handle, indent=2, ensure_ascii=False)