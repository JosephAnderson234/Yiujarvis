import copy
import json
from pathlib import Path


MEMORY_FILE = Path("memory.json")
DEFAULT_MEMORY = {
    "preferences": {},
    "facts": [],
    "history": [],
}


def _coerce_list(value, limit=None):
    if not isinstance(value, list):
        return []

    if limit is None:
        return list(value)

    return list(value[-limit:])


def normalize_memory(payload):
    normalized = copy.deepcopy(DEFAULT_MEMORY)

    if not isinstance(payload, dict):
        return normalized

    if any(key in payload for key in DEFAULT_MEMORY):
        preferences = payload.get("preferences")
        if isinstance(preferences, dict):
            normalized["preferences"].update(preferences)

        normalized["facts"] = _coerce_list(payload.get("facts"), limit=100)
        normalized["history"] = _coerce_list(payload.get("history"), limit=50)

        for key, value in payload.items():
            if key not in DEFAULT_MEMORY:
                normalized["preferences"][key] = value

        return normalized

    normalized["preferences"].update(payload)
    return normalized


def load_memory():
    try:
        with MEMORY_FILE.open("r", encoding="utf-8") as file_handle:
            return normalize_memory(json.load(file_handle))
    except (FileNotFoundError, json.JSONDecodeError):
        return copy.deepcopy(DEFAULT_MEMORY)


def save_memory(memory):
    memory = normalize_memory(memory)

    with MEMORY_FILE.open("w", encoding="utf-8") as file_handle:
        json.dump(memory, file_handle, indent=2, ensure_ascii=False)


def set_preference(memory, key, value):
    memory = normalize_memory(memory)
    memory["preferences"][key] = value
    return memory


def add_fact(memory, fact):
    memory = normalize_memory(memory)

    if fact not in memory["facts"]:
        memory["facts"].append(fact)

    memory["facts"] = memory["facts"][-100:]
    return memory


def append_history(memory, role, content):
    memory = normalize_memory(memory)

    if not content:
        return memory

    memory["history"].append({"role": role, "content": content})
    memory["history"] = memory["history"][-50:]
    return memory


def build_memory_context(memory, recent_messages=None):
    memory = normalize_memory(memory)
    recent_messages = recent_messages or []

    context = {
        "preferences": memory.get("preferences", {}),
        "facts": memory.get("facts", [])[-10:],
        "recent_history": memory.get("history", [])[-5:],
        "recent_messages": list(recent_messages)[-10:],
    }

    return json.dumps(context, ensure_ascii=False, indent=2)