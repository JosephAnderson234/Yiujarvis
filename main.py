import argparse
import ctypes
import os
import sys

from src.cli import run


def is_running_as_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def relaunch_as_admin_if_needed():
    if os.name != "nt" or is_running_as_admin():
        return False

    script_path = os.path.abspath(__file__)
    arguments = [sys.executable, script_path] + sys.argv[1:]
    result = ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        sys.executable,
        " ".join(f'"{argument}"' for argument in [script_path, *sys.argv[1:]]),
        None,
        1,
    )

    if result <= 32:
        raise RuntimeError("No se pudo reiniciar Yiujarvis como administrador")

    return True


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model",
        choices=["githubmodel", "groq"],
        default="githubmodel",
        help="Proveedor de IA a usar",
    )
    return parser.parse_args()


if __name__ == "__main__":
    if relaunch_as_admin_if_needed():
        sys.exit(0)

    args = parse_args()
    run(provider=args.model)