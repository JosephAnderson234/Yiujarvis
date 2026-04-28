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
        tool_name = step.get("tool", "unknown")
        arguments = step.get("arguments", {})
        print(Fore.WHITE + f"  {index}. {tool_name} -> {arguments}")