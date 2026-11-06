"""Opt-in foreground-window rules; window titles never leave this process."""

import ctypes
import sys
import threading
import time


def foreground_title():
    if sys.platform != "win32":
        return ""
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    window = user32.GetForegroundWindow()
    if not window:
        return ""
    length = user32.GetWindowTextLengthW(window)
    if length <= 0:
        return ""
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(window, buffer, len(buffer))
    return buffer.value


class WindowWatcher:
    def __init__(self, store, events, stop, paused):
        self.store = store
        self.events = events
        self.stop = stop
        self.paused = paused
        self.thread = threading.Thread(target=self._run, daemon=True, name="yiujarvis-window-watch")

    def start(self):
        self.thread.start()

    def _run(self):
        last_title = ""
        last_alert = {}
        while not self.stop.wait(1):
            if self.paused.is_set():
                last_title = ""
                continue
            title = foreground_title()
            if not title or title == last_title:
                continue
            last_title = title
            now = time.monotonic()
            for rule in self.store.list_window_rules():
                if rule["title_contains"].casefold() in title.casefold() and now - last_alert.get(rule["id"], -600) >= 300:
                    last_alert[rule["id"]] = now
                    self.events.put(("window_rule", rule["message"]))
