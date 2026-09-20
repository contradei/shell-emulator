import getpass
import socket
from enum import Enum

from src.shell_emulator.config import parse_arguments
from src.shell_emulator.parser import parse_command
from src.shell_emulator.vfs import VirtualFileSystem, VfsError


class CommandStatus(Enum):

    SUCCESS = "success"
    ERROR = "error"
    EXIT = "exit"


def create_prompt():

    username = getpass.getuser()
    hostname = socket.gethostname()

    return f"{username}@{hostname}:~$ "


def execute_command(args, vfs):

    if not args:
        return CommandStatus.SUCCESS

    command = args[0]
    arguments = args[1:]

    if command == "exit":
        return CommandStatus.EXIT

    if command == "ls":
        for node in vfs.list_directory():
            print(node.name)

        return CommandStatus.SUCCESS

    if command == "cd":
        if not arguments:
            return CommandStatus.SUCCESS

        try:
            vfs.change_directory(arguments[0])
        except VfsError as error:
            print(f"Ошибка: {error}")
            return CommandStatus.ERROR

        return CommandStatus.SUCCESS

    print(f"Ошибка: неизвестная команда '{command}'")
    return CommandStatus.ERROR


def run_startup_script(path, vfs):

    try:
        with open(path, encoding="utf-8") as script:
            for line_number, line in enumerate(script, start=1):
                command = line.strip()

                if not command:
                    continue

                print(f"{create_prompt()}{command}")

                args = parse_command(command)

                if args is None:
                    print(
                        f"Ошибка startup-скрипта: строка "
                        f"{line_number}"
                    )
                    return CommandStatus.ERROR

                status = execute_command(args, vfs)

                if status == CommandStatus.ERROR:
                    print(
                        f"Ошибка startup-скрипта: строка "
                        f"{line_number}"
                    )
                    return CommandStatus.ERROR

                if status == CommandStatus.EXIT:
                    return CommandStatus.EXIT

    except OSError as error:
        print(f"Ошибка открытия startup-скрипта: {error}")
        return CommandStatus.ERROR

    return CommandStatus.SUCCESS


def main():
    config = parse_arguments()

    vfs = VirtualFileSystem()

    if config.vfs:
        try:
            vfs.load(config.vfs)
            print(f"VFS загружена: {config.vfs}")
        except VfsError as error:
            print(f"Ошибка загрузки VFS: {error}")
            return

    print(f"Script: {config.script}")

    if config.script:
        status = run_startup_script(config.script, vfs)

        if status == CommandStatus.EXIT:
            return

    while True:
        prompt = create_prompt()
        command = input(prompt)

        args = parse_command(command)

        if args is None:
            continue

        status = execute_command(args, vfs)

        if status == CommandStatus.EXIT:
            break


if __name__ == "__main__":
    main()