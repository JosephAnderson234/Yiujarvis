"""Persistent queue for commands and reminders."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from src.paths import PROJECT_ROOT


TASKS_FILE = PROJECT_ROOT / "tasks.sqlite3"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class TaskStore:
    def __init__(self, path=TASKS_FILE):
        self.path = str(path)
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY,
                prompt TEXT NOT NULL,
                due_at TEXT NOT NULL,
                kind TEXT NOT NULL DEFAULT 'command',
                status TEXT NOT NULL,
                result TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS window_rules (
                id INTEGER PRIMARY KEY,
                title_contains TEXT NOT NULL,
                message TEXT NOT NULL
            )""")

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def add(self, prompt, due_at=None, kind="command"):
        prompt = prompt.strip()
        if not prompt:
            raise ValueError("La tarea no puede estar vacía")
        if kind not in {"command", "reminder"}:
            raise ValueError("Tipo de tarea inválido")
        due_at = due_at or utc_now()
        now = utc_now()
        with self._connect() as db:
            cursor = db.execute(
                "INSERT INTO tasks (prompt, due_at, kind, status, created_at, updated_at) VALUES (?, ?, ?, 'pending', ?, ?)",
                (prompt, due_at, kind, now, now),
            )
            return cursor.lastrowid

    def claim_due(self):
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM tasks WHERE status='pending' AND due_at <= ? ORDER BY due_at, id LIMIT 1",
                (utc_now(),),
            ).fetchone()
            if row is None:
                return None
            db.execute("UPDATE tasks SET status='running', updated_at=? WHERE id=?", (utc_now(), row["id"]))
            return dict(row)

    def finish(self, task_id, result, failed=False):
        with self._connect() as db:
            db.execute(
                "UPDATE tasks SET status=?, result=?, updated_at=? WHERE id=?",
                ("failed" if failed else "done", result, utc_now(), task_id),
            )

    def recover(self):
        with self._connect() as db:
            db.execute("UPDATE tasks SET status='interrupted', updated_at=? WHERE status='running'", (utc_now(),))

    def retry(self, task_id):
        with self._connect() as db:
            cursor = db.execute(
                "UPDATE tasks SET status='pending', result='', updated_at=? "
                "WHERE id=? AND status IN ('interrupted', 'failed')",
                (utc_now(), task_id),
            )
            return cursor.rowcount == 1

    def list_recent(self, limit=30):
        with self._connect() as db:
            return [dict(row) for row in db.execute(
                "SELECT * FROM tasks ORDER BY id DESC LIMIT ?", (limit,)
            )]

    def add_window_rule(self, title_contains, message):
        title_contains = title_contains.strip()
        message = message.strip()
        if not title_contains or not message:
            raise ValueError("Indica el título de ventana y el aviso")
        with self._connect() as db:
            cursor = db.execute(
                "INSERT INTO window_rules (title_contains, message) VALUES (?, ?)",
                (title_contains, message),
            )
            return cursor.lastrowid

    def list_window_rules(self):
        with self._connect() as db:
            return [dict(row) for row in db.execute("SELECT * FROM window_rules ORDER BY id DESC")]

    def delete_window_rule(self, rule_id):
        with self._connect() as db:
            db.execute("DELETE FROM window_rules WHERE id=?", (rule_id,))
