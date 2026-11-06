import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.task_store import TaskStore


class TaskStoreTests(unittest.TestCase):
    def test_due_tasks_survive_reopen_and_recover_interrupted_work(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tasks.sqlite3"
            store = TaskStore(path)
            later = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
            reminder_id = store.add("Revisar correo", later, kind="reminder")
            command_id = store.add("abre calculadora")

            claimed = TaskStore(path).claim_due()
            self.assertEqual(claimed["id"], command_id)
            self.assertIsNone(store.claim_due())
            self.assertEqual(store.list_recent()[0]["id"], command_id)

            reopened = TaskStore(path)
            reopened.recover()
            self.assertIsNone(reopened.claim_due())
            self.assertTrue(reopened.retry(command_id))
            self.assertEqual(reopened.claim_due()["id"], command_id)
            reopened.finish(command_id, "Listo")
            self.assertIsNone(reopened.claim_due())
            self.assertEqual(reopened.list_recent()[1]["id"], reminder_id)

    def test_rejects_empty_task_and_unknown_kind(self):
        with tempfile.TemporaryDirectory() as directory:
            store = TaskStore(Path(directory) / "tasks.sqlite3")
            with self.assertRaises(ValueError):
                store.add("  ")
            with self.assertRaises(ValueError):
                store.add("x", kind="other")

    def test_window_rules_persist_and_can_be_deleted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tasks.sqlite3"
            store = TaskStore(path)
            rule_id = store.add_window_rule("VS Code", "Revisa la tarea pendiente")
            self.assertEqual(TaskStore(path).list_window_rules()[0]["id"], rule_id)
            store.delete_window_rule(rule_id)
            self.assertEqual(store.list_window_rules(), [])


if __name__ == "__main__":
    unittest.main()
