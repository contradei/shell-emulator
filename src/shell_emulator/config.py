import argparse


def parse_arguments():
    """Парсит параметры запуска эмулятора."""

    parser = argparse.ArgumentParser(
        description="UNIX-like shell emulator"
    )

    parser.add_argument(
        "--vfs",
        help="Path to the virtual file system"
    )

    parser.add_argument(
        "--script",
        help="Path to the startup script"
    )

    return parser.parse_args()