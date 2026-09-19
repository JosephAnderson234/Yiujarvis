import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.memory_store import (
    DEFAULT_MEMORY,
    add_fact,
    append_history,
    build_memory_context,
    load_memory,
    normalize_memory,
    save_memory,
    set_preference,
)


class NormalizeMemoryTests(unittest.TestCase):
    def test_none_payload_returns_default_shape(self):
        self.assertEqual(normalize_memory(None), DEFAULT_MEMORY)

    def test_legacy_flat_payload_is_treated_as_preferences(self):
        normalized = normalize_memory({"nombre": "Jose"})
        self.assertEqual(normalized["preferences"]["nombre"], "Jose")
        self.assertEqual(normalized["facts"], [])
        self.assertEqual(normalized["history"], [])

    def test_history_is_capped_at_fifty_entries(self):
        payload = {"history": [{"role": "user", "content": str(i)} for i in range(60)]}
        normalized = normalize_memory(payload)
        self.assertEqual(len(normalized["history"]), 50)
        self.assertEqual(normalized["history"][0]["content"], "10")


class MutationHelperTests(unittest.TestCase):
    def test_set_preference(self):
        memory = set_preference(copy.deepcopy(DEFAULT_MEMORY), "color", "azul")
        self.assertEqual(memory["preferences"]["color"], "azul")

    def test_add_fact_avoids_duplicates(self):
        memory = add_fact(copy.deepcopy(DEFAULT_MEMORY), "le gusta el cafe")
        memory = add_fact(memory, "le gusta el cafe")
        self.assertEqual(memory["facts"], ["le gusta el cafe"])

    def test_append_history_accumulates_across_calls(self):
        # Regression test: append_history returns a new dict rather than
        # mutating in place, so callers must chain the return value or
        # entries are silently lost.
        memory = copy.deepcopy(DEFAULT_MEMORY)
        memory = append_history(memory, "user", "hola")
        memory = append_history(memory, "assistant", "hola, como estas")

        self.assertEqual(
            memory["history"],
            [
                {"role": "user", "content": "hola"},
                {"role": "assistant", "content": "hola, como estas"},
            ],
        )

    def test_append_history_ignores_empty_content(self):
        memory = append_history(copy.deepcopy(DEFAULT_MEMORY), "user", "")
        self.assertEqual(memory["history"], [])


class BuildMemoryContextTests(unittest.TestCase):
    def test_includes_preferences_facts_and_recent_messages(self):
        memory = {
            "preferences": {"color": "azul"},
            "facts": ["le gusta el cafe"],
            "history": [{"role": "user", "content": "hola"}],
        }
        context_json = build_memory_context(memory, recent_messages=[{"role": "user", "content": "hola"}])
        self.assertIn("azul", context_json)
        self.assertIn("le gusta el cafe", context_json)


class LoadSaveMemoryTests(unittest.TestCase):
    def test_load_missing_file_returns_default(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            missing_path = Path(tmp_dir) / "does_not_exist.json"
            with patch("src.memory_store.MEMORY_FILE", missing_path):
                self.assertEqual(load_memory(), DEFAULT_MEMORY)

    def test_save_then_load_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            memory_path = Path(tmp_dir) / "memory.json"
            with patch("src.memory_store.MEMORY_FILE", memory_path):
                memory = set_preference(copy.deepcopy(DEFAULT_MEMORY), "nombre", "Jose")
                save_memory(memory)
                loaded = load_memory()

        self.assertEqual(loaded["preferences"]["nombre"], "Jose")


if __name__ == "__main__":
    unittest.main()
