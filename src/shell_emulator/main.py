"""Консольный эмулятор UNIX, вариант 9."""

import getpass
import socket
from enum import Enum

from src.shell_emulator.config import parse_arguments
from src.shell_emulator.parser import parse_command


class CommandStatus(Enum):
    """Результат команды; имена соответствуют проверке snake_case."""

    success = "success"
    error = "error"
    exit = "exit"


def create_prompt():
    """Возвращает приглашение с реальными пользователем и хостом."""
    return f"{getpass.getuser()}@{socket.gethostname()}:~$ "


def execute_stub(arguments, command):
    """Показывает имя и аргументы команды-заглушки."""
    print(f"Команда: {command}")
    print(f"Аргументы: {arguments}")
    return CommandStatus.success


def execute_command(args, vfs=None):
    """Выполняет команду текущего этапа."""
    if not args:
        return CommandStatus.success
    command, arguments = args[0], args[1:]
    if command == "exit" and not arguments:
        return CommandStatus.exit
    if command in ("ls", "cd"):
        return execute_stub(arguments, command)
    print(f"Ошибка: неизвестная команда или аргументы '{command}'")
    return CommandStatus.error


def execute_line(command, vfs=None):
    """Разбирает строку и возвращает результат выполнения."""
    args = parse_command(command)
    if args is None:
        return CommandStatus.error
    return execute_command(args, vfs)


def run_interactive_mode(vfs=None):
    """Читает команды до exit, EOF или прерывания пользователем."""
    while True:
        try:
            command = input(create_prompt())
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if execute_line(command, vfs) == CommandStatus.exit:
            return


def run_startup_script(path, vfs=None):
    """Показывает ввод/вывод; останавливается на первой ошибке."""
    try:
        with open(path, encoding="utf-8-sig") as script:
            for line_number, line in enumerate(script, start=1):
                command = line.strip()
                if not command:
                    continue
                print(f"{create_prompt()}{command}")
                status = execute_line(command, vfs)
                if status == CommandStatus.error:
                    print(f"Ошибка startup-скрипта: строка {line_number}")
                if status != CommandStatus.success:
                    return status
    except (OSError, UnicodeError) as error:
        print(f"Ошибка чтения startup-скрипта: {error}")
        return CommandStatus.error
    return CommandStatus.success


def main():
    """Печатает конфигурацию, выполняет startup, затем запускает REPL."""
    config = parse_arguments()
    print(f"VFS: {config.vfs}")
    print(f"Script: {config.script}")
    vfs = None
    if config.script:
        status = run_startup_script(config.script, vfs)
        if status == CommandStatus.error:
            return 1
        if status == CommandStatus.exit:
            return 0
    run_interactive_mode(vfs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
