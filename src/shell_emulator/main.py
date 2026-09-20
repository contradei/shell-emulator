import getpass
import socket
from pathlib import Path

from src.shell_emulator.parser import parse_command


def create_prompt():
    username = getpass.getuser()
    hostname = socket.gethostname()

    return f"{username}@{hostname}:~$ "


def execute_command(args):
    if not args:
        return True

    command = args[0]
    arguments = args[1:]

    if command == "exit":
        return False

    if command == "ls":
        print("Команда: ls")
        print(f"Аргументы: {arguments}")
        return True

    if command == "cd":
        print("Команда: cd")
        print(f"Аргументы: {arguments}")
        return True

    print(f"Ошибка: неизвестная команда '{command}'")
    return True


def main():
    while True:
        prompt = create_prompt()
        command = input(prompt)

        args = parse_command(command)

        if args is None:
            continue

        if not execute_command(args):
            break


if __name__ == "__main__":
    main()