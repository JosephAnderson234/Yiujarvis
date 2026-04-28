import os

from colorama import Fore, Style, init


init(autoreset=True)


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def show_banner():
    clear_screen()
    print(Fore.CYAN + Style.BRIGHT + "═" * 62)
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