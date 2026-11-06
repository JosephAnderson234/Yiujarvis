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
    parser.add_argument(
        "--admin",
        action="store_true",
        help="Reinicia Yiujarvis como administrador (solo si una tool lo necesita)",
    )
    parser.add_argument(
        "--background",
        action="store_true",
        help="Ejecuta Yiujarvis en la bandeja de Windows",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.admin and relaunch_as_admin_if_needed():
        sys.exit(0)

    if args.background:
        from src.background import run_background

        run_background(provider=args.model)
    else:
        run(provider=args.model)
