import os
import sys
import threading
import time

from colorama import Fore, Style, init


init(autoreset=True)


ANIMATIONS_ENABLED = True
SPINNER_FRAMES = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")


def set_animations_enabled(enabled):
    global ANIMATIONS_ENABLED
    ANIMATIONS_ENABLED = bool(enabled)


def animations_enabled():
    return (
        ANIMATIONS_ENABLED
        and os.getenv("YIUJARVIS_NO_ANIMATION", "").lower() not in {"1", "true", "yes"}
        and hasattr(sys.stdout, "isatty")
        and sys.stdout.isatty()
    )


class Spinner:
    """Small terminal-only animation for blocking work."""

    def __init__(self, label):
        self.label = label
        self._stop = threading.Event()
        self._thread = None
        self._active = False

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, _type, _value, _traceback):
        self.stop()

    def start(self):
        if not animations_enabled() or self._active:
            return
        self._active = True

        def animate():
            index = 0
            while not self._stop.is_set():
                frame = SPINNER_FRAMES[index % len(SPINNER_FRAMES)]
                sys.stdout.write(f"\r{Fore.CYAN}{frame} {self.label}{Style.RESET_ALL}")
                sys.stdout.flush()
                index += 1
                self._stop.wait(0.09)

        self._thread = threading.Thread(target=animate, daemon=True, name="yiujarvis-spinner")
        self._thread.start()

    def stop(self):
        if not self._active:
            return
        self._stop.set()
        self._thread.join(timeout=1)
        sys.stdout.write("\r" + " " * (len(self.label) + 8) + "\r")
        sys.stdout.flush()
        self._active = False


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def show_banner():
    clear_screen()
    print(Fore.CYAN + Style.BRIGHT + "═" * 62)
    if animations_enabled():
        title = "   Yiujarvis"
        for character in title:
            sys.stdout.write(Fore.CYAN + Style.BRIGHT + character)
            sys.stdout.flush()
            time.sleep(0.025)
        print()
    else:
        print(Fore.CYAN + Style.BRIGHT + "   Yiujarvis")
    print(Fore.WHITE + "   Asistente local para Windows")
    print(Fore.CYAN + Style.BRIGHT + "═" * 62)


def show_startup_status(provider, tools_count):
    print(Fore.GREEN + f"Proveedor activo: {provider}")
    print(Fore.GREEN + f"Tools disponibles: {tools_count}")


def prompt_user():
    return Fore.YELLOW + Style.BRIGHT + "🧑 Tú: " + Style.RESET_ALL


def print_assistant(text):
    print(Fore.MAGENTA + Style.BRIGHT + "🤖 Yiujarvis:" + Style.RESET_ALL, text)


def print_assistant_prefix():
    print(Fore.MAGENTA + Style.BRIGHT + "🤖 Yiujarvis:" + Style.RESET_ALL, end=" ", flush=True)


def print_tool_call(name, arguments):
    rendered = ", ".join(f"{key}={value!r}" for key, value in arguments.items())
    print(Fore.CYAN + Style.DIM + f"  ⚙ {name}({rendered})" + Style.RESET_ALL)


def print_notice(text):
    print(Fore.BLUE + Style.BRIGHT + "ℹ" + Style.RESET_ALL, text)


def print_warning(text):
    print(Fore.RED + Style.BRIGHT + "⚠" + Style.RESET_ALL, text)


def print_plan(title, steps):
    print(Fore.CYAN + Style.BRIGHT + f"{title}")
    for index, step in enumerate(steps, start=1):
        if hasattr(step, "to_dict"):
            printable = step.to_dict()
        elif isinstance(step, dict):
            printable = step
        else:
            printable = {
                "action": getattr(step, "action", "unknown"),
                "params": getattr(step, "params", {}),
                "condition": getattr(step, "condition_name", ""),
                "description": getattr(step, "description", ""),
            }

        action = printable.get("action", printable.get("tool", "unknown"))
        params = printable.get("params", printable.get("arguments", {}))
        condition = printable.get("condition", "")
        description = printable.get("description", "")
        line = f"  {index}. {action} -> {params}"
        if condition:
            line += f" [{condition}]"
        if description:
            line += f" - {description}"

        print(Fore.WHITE + line)
