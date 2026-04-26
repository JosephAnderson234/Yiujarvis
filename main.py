import argparse

from src.cli import run


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
    args = parse_args()
    run(provider=args.model)