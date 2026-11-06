import queue
import unittest
from unittest.mock import patch

from src.window_watch import WindowWatcher


class _StopAfterTwoChecks:
    def __init__(self):
        self.calls = 0

    def wait(self, _seconds):
        self.calls += 1
        return self.calls > 2


class WindowWatcherTests(unittest.TestCase):
    def test_matching_window_sends_one_notice_for_repeated_title(self):
        store = type("Store", (), {"list_window_rules": lambda self: [
            {"id": 1, "title_contains": "code", "message": "Revisa tu tarea"}
        ]})()
        events = queue.Queue()
        paused = type("Pause", (), {"is_set": lambda self: False})()
        watcher = WindowWatcher(store, events, _StopAfterTwoChecks(), paused)

        with patch("src.window_watch.foreground_title", return_value="Visual Studio Code"):
            watcher._run()

        self.assertEqual(events.get_nowait(), ("window_rule", "Revisa tu tarea"))
        self.assertTrue(events.empty())


if __name__ == "__main__":
    unittest.main()
