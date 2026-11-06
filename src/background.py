"""Windows tray host for Yiujarvis."""

import ctypes
import queue
import sys
import threading
import tkinter as tk
from datetime import datetime, timezone
from pathlib import Path
from tkinter import messagebox, ttk
import winreg

from src.core.agent_loop import (
    build_system_prompt,
    build_tool_registry,
    compact_conversation,
    run_agent_turn,
    run_direct_command,
)
from src.config import get_model_config
from src.intent import is_direct_command
from src.memory_store import MemorySession, load_memory
from src.planner.executor import PlanExecutor
from src.planner.planner import Planner
from src.task_store import TaskStore
from src.window_watch import WindowWatcher


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_NAME = "Yiujarvis"


def startup_command(provider):
    python = Path(sys.executable)
    if python.name.lower() == "python.exe":
        candidate = python.with_name("pythonw.exe")
        if candidate.exists():
            python = candidate
    main = Path(__file__).resolve().parent.parent / "main.py"
    return f'"{python}" "{main}" --background --model {provider}'


def startup_enabled(provider):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            value, _ = winreg.QueryValueEx(key, RUN_NAME)
            return value == startup_command(provider)
    except FileNotFoundError:
        return False


def set_startup(enabled, provider):
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
        if enabled:
            winreg.SetValueEx(key, RUN_NAME, 0, winreg.REG_SZ, startup_command(provider))
        else:
            try:
                winreg.DeleteValue(key, RUN_NAME)
            except FileNotFoundError:
                pass


class BackgroundAgent:
    def __init__(self, provider, store, ui_events):
        self.provider = provider
        self.store = store
        self.ui_events = ui_events
        self.stop = threading.Event()
        self.paused = threading.Event()
        self.thread = threading.Thread(target=self._work, daemon=True, name="yiujarvis-worker")

    def start(self):
        self.store.recover()
        self.thread.start()

    def _approve(self, tool, kwargs):
        decision = threading.Event()
        reply = {"approved": False}
        self.ui_events.put(("approval", tool, kwargs, decision, reply))
        decision.wait(60)
        return reply["approved"] and not self.stop.is_set()

    def _work(self):
        memory = MemorySession(load_memory())
        registry = None
        try:
            try:
                config = get_model_config(self.provider)
                model_error = None
            except Exception as exc:
                config = None
                model_error = str(exc)
            registry = build_tool_registry(memory)
            registry.set_confirmation_callback(self._approve)
            planner = Planner(registry=registry, memory_store=memory.data)
            executor = PlanExecutor(registry)
            messages = [{"role": "system", "content": build_system_prompt(memory.data)}]
            summary = ""
            self.ui_events.put(("status", "Listo" if config else f"Recordatorios activos; modelo no disponible: {model_error}"))
            while not self.stop.is_set():
                if self.paused.is_set():
                    self.stop.wait(0.5)
                    continue
                task = self.store.claim_due()
                if task is None:
                    self.stop.wait(0.5)
                    continue
                try:
                    if task["kind"] == "reminder":
                        result = task["prompt"]
                    else:
                        text = task["prompt"]
                        memory.append_history("user", text)
                        planner.memory_store = memory.data
                        result = None
                        if is_direct_command(text):
                            result = run_direct_command(planner, executor, text)
                            if result is not None:
                                messages.extend([
                                    {"role": "user", "content": text},
                                    {"role": "assistant", "content": result},
                                ])
                        if result is None:
                            if config is None:
                                raise RuntimeError(model_error)
                            hints = planner.build_plan(text).context
                            summary = compact_conversation(config["client"], config["model_name"], messages, summary)
                            messages[0]["content"] = build_system_prompt(
                                memory.data, hints.get("relevant_memory", []),
                                hints.get("ranked_tools", []), summary,
                            )
                            messages.append({"role": "user", "content": text})
                            result = run_agent_turn(config["client"], config["model_name"], messages, registry)
                        memory.append_history("assistant", result)
                        memory.save()
                    self.store.finish(task["id"], result)
                    self.ui_events.put(("done", task["id"], result))
                except Exception as exc:
                    self.store.finish(task["id"], str(exc), failed=True)
                    self.ui_events.put(("failed", task["id"], str(exc)))
        except Exception as exc:
            self.ui_events.put(("status", f"Error de inicio: {exc}"))
        finally:
            memory.save()
            if registry is not None and registry.mcp_client is not None:
                registry.mcp_client.close()


class BackgroundWindow:
    def __init__(self, provider):
        self.provider = provider
        self.root = tk.Tk()
        self.root.title("Yiujarvis")
        self.root.geometry("690x580")
        self.root.protocol("WM_DELETE_WINDOW", self.hide)
        self.events = queue.Queue()
        self.store = TaskStore()
        self.agent = BackgroundAgent(provider, self.store, self.events)
        self.watcher = WindowWatcher(self.store, self.events, self.agent.stop, self.agent.paused)
        self.icon = None
        self.status = tk.StringVar(value="Iniciando...")
        self.prompt = tk.StringVar()
        self.when = tk.StringVar()
        self.rule_title = tk.StringVar()
        self.rule_message = tk.StringVar()
        self._build_ui()
        self._start_tray()
        self._start_hotkey()
        self.agent.start()
        self.watcher.start()
        self.root.after(200, self._poll_events)

    def _build_ui(self):
        frame = ttk.Frame(self.root, padding=14)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Yiujarvis · agente en segundo plano", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        ttk.Label(frame, text="Ctrl+Alt+J abre esta ventana. Al cerrarla, Yiujarvis sigue activo.").pack(anchor="w", pady=(4, 12))
        ttk.Entry(frame, textvariable=self.prompt).pack(fill="x")
        ttk.Button(frame, text="Enviar tarea ahora", command=self._add_command).pack(anchor="w", pady=(6, 10))
        ttk.Label(frame, text="Recordatorio (fecha y hora local: AAAA-MM-DD HH:MM)").pack(anchor="w")
        row = ttk.Frame(frame)
        row.pack(fill="x", pady=(4, 8))
        ttk.Entry(row, textvariable=self.when).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Programar recordatorio", command=self._add_reminder).pack(side="left", padx=(8, 0))
        ttk.Label(frame, text="Avisar cuando el título de una ventana contenga:").pack(anchor="w")
        rule_row = ttk.Frame(frame)
        rule_row.pack(fill="x", pady=(4, 3))
        ttk.Entry(rule_row, textvariable=self.rule_title, width=22).pack(side="left")
        ttk.Label(rule_row, text="Mensaje:").pack(side="left", padx=(8, 4))
        ttk.Entry(rule_row, textvariable=self.rule_message).pack(side="left", fill="x", expand=True)
        ttk.Button(rule_row, text="Crear regla", command=self._add_rule).pack(side="left", padx=(8, 0))
        self.rules = ttk.Combobox(frame, state="readonly")
        self.rules.pack(fill="x")
        ttk.Button(frame, text="Eliminar regla seleccionada", command=self._delete_rule).pack(anchor="w", pady=(4, 8))
        self.tasks = ttk.Treeview(frame, columns=("state", "when", "prompt"), show="headings", height=10)
        for name, title, width in (("state", "Estado", 80), ("when", "Fecha", 145), ("prompt", "Tarea", 340)):
            self.tasks.heading(name, text=title)
            self.tasks.column(name, width=width, stretch=name == "prompt")
        self.tasks.pack(fill="both", expand=True)
        self.tasks.bind("<Double-1>", self._show_task_result)
        controls = ttk.Frame(frame)
        controls.pack(fill="x", pady=(8, 0))
        ttk.Button(controls, text="Pausar/Reanudar", command=self.toggle_pause).pack(side="left")
        ttk.Button(controls, text="Reintentar seleccionada", command=self._retry_selected).pack(side="left", padx=8)
        ttk.Button(controls, text="Inicio con Windows", command=self.toggle_startup).pack(side="left", padx=8)
        ttk.Button(controls, text="Salir", command=self.quit).pack(side="right")
        ttk.Label(frame, textvariable=self.status).pack(anchor="w", pady=(8, 0))
        self._refresh_tasks()
        self._refresh_rules()

    def _refresh_tasks(self):
        for item in self.tasks.get_children():
            self.tasks.delete(item)
        for task in self.store.list_recent():
            date = datetime.fromisoformat(task["due_at"]).astimezone().strftime("%Y-%m-%d %H:%M")
            self.tasks.insert("", "end", iid=str(task["id"]), values=(task["status"], date, task["prompt"]))

    def _show_task_result(self, _event):
        selected = self.tasks.selection()
        if not selected:
            return
        task = next((item for item in self.store.list_recent() if str(item["id"]) == selected[0]), None)
        if task:
            messagebox.showinfo("Resultado de la tarea", task["result"] or "Sin resultado todavía", parent=self.root)

    def _retry_selected(self):
        selected = self.tasks.selection()
        if selected and self.store.retry(int(selected[0])):
            self._refresh_tasks()

    def _refresh_rules(self):
        self.rule_rows = self.store.list_window_rules()
        self.rules["values"] = [f"{rule['title_contains']} → {rule['message']}" for rule in self.rule_rows]
        self.rules.set("")

    def _add_rule(self):
        try:
            self.store.add_window_rule(self.rule_title.get(), self.rule_message.get())
            self.rule_title.set("")
            self.rule_message.set("")
            self._refresh_rules()
        except ValueError as exc:
            messagebox.showerror("Yiujarvis", str(exc), parent=self.root)

    def _delete_rule(self):
        index = self.rules.current()
        if index >= 0:
            self.store.delete_window_rule(self.rule_rows[index]["id"])
            self._refresh_rules()

    def _add_command(self):
        try:
            self.store.add(self.prompt.get())
            self.prompt.set("")
            self._refresh_tasks()
        except ValueError as exc:
            messagebox.showerror("Yiujarvis", str(exc), parent=self.root)

    def _add_reminder(self):
        try:
            local_time = datetime.strptime(self.when.get().strip(), "%Y-%m-%d %H:%M").astimezone()
            if local_time <= datetime.now().astimezone():
                raise ValueError("La fecha debe estar en el futuro")
            self.store.add(self.prompt.get(), local_time.astimezone(timezone.utc).isoformat(), kind="reminder")
            self.prompt.set("")
            self.when.set("")
            self._refresh_tasks()
        except (ValueError, OverflowError) as exc:
            messagebox.showerror("Yiujarvis", f"Revisa el texto y la fecha: {exc}", parent=self.root)

    def _start_tray(self):
        import pystray
        from PIL import Image, ImageDraw

        image = Image.new("RGB", (64, 64), "#14213d")
        draw = ImageDraw.Draw(image)
        draw.ellipse((6, 6, 58, 58), fill="#00b4d8")
        draw.text((20, 17), "Y", fill="white")
        self.icon = pystray.Icon(
            "Yiujarvis", image, "Yiujarvis",
            menu=pystray.Menu(
                pystray.MenuItem("Abrir Yiujarvis", lambda *_: self.events.put(("show",)), default=True),
                pystray.MenuItem("Pausar/Reanudar", lambda *_: self.events.put(("pause",))),
                pystray.MenuItem("Salir", lambda *_: self.events.put(("quit",))),
            ),
        )
        self.icon.run_detached()

    def _start_hotkey(self):
        def listen():
            if sys.platform != "win32":
                return
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            if not user32.RegisterHotKey(None, 1, 0x0002 | 0x0001, ord("J")):
                self.events.put(("status", "Atajo Ctrl+Alt+J ocupado; usa la bandeja."))
                return
            msg = wintypes.MSG()
            try:
                while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                    if msg.message == 0x0312:
                        self.events.put(("show",))
            finally:
                user32.UnregisterHotKey(None, 1)

        threading.Thread(target=listen, daemon=True, name="yiujarvis-hotkey").start()

    def _poll_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]
                if kind == "approval":
                    _, tool, kwargs, decision, reply = event
                    try:
                        self.show()
                        reply["approved"] = self._ask_approval(tool, kwargs)
                    finally:
                        decision.set()
                elif kind in {"done", "failed"}:
                    self._refresh_tasks()
                    self._notify("Tarea completada" if kind == "done" else "Tarea fallida", event[2])
                elif kind == "status":
                    self.status.set(event[1])
                elif kind == "window_rule":
                    self._notify("Yiujarvis · regla de ventana", event[1])
                elif kind == "show":
                    self.show()
                elif kind == "pause":
                    self.toggle_pause()
                elif kind == "quit":
                    self.quit()
                    return
        except queue.Empty:
            pass
        self.root.after(200, self._poll_events)

    def _ask_approval(self, tool, kwargs):
        dialog = tk.Toplevel(self.root)
        dialog.title("Yiujarvis solicita permiso")
        dialog.transient(self.root)
        dialog.grab_set()
        answer = {"approved": False}
        ttk.Label(
            dialog,
            text=f"Herramienta: {tool.name}\nRiesgo: {tool.risk}\nArgumentos: {kwargs}",
            padding=16,
            wraplength=450,
        ).pack()
        row = ttk.Frame(dialog, padding=(16, 0, 16, 16))
        row.pack()

        def close(approved=False):
            answer["approved"] = approved
            dialog.destroy()

        ttk.Button(row, text="Denegar", command=close).pack(side="left")
        ttk.Button(row, text="Autorizar", command=lambda: close(True)).pack(side="left", padx=8)
        dialog.protocol("WM_DELETE_WINDOW", close)
        dialog.after(59000, close)
        self.root.wait_window(dialog)
        return answer["approved"]

    def _notify(self, title, message):
        try:
            self.icon.notify(message[:180], title)
        except Exception:
            self.status.set(f"{title}: {message[:120]}")

    def show(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def hide(self):
        self.root.withdraw()

    def toggle_pause(self):
        if self.agent.paused.is_set():
            self.agent.paused.clear()
            self.status.set("Listo")
        else:
            self.agent.paused.set()
            self.status.set("Pausado")

    def toggle_startup(self):
        try:
            enabled = not startup_enabled(self.provider)
            set_startup(enabled, self.provider)
            self.status.set("Inicio con Windows activado" if enabled else "Inicio con Windows desactivado")
        except OSError as exc:
            messagebox.showerror("Yiujarvis", f"No se pudo cambiar el inicio automático: {exc}", parent=self.root)

    def quit(self):
        self.agent.stop.set()
        if self.icon:
            self.icon.stop()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def run_background(provider="githubmodel"):
    if sys.platform != "win32":
        raise RuntimeError("El modo en segundo plano requiere Windows")
    BackgroundWindow(provider).run()
