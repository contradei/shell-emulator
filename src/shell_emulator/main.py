"""Консольный эмулятор UNIX, вариант 9."""

import getpass
import socket
from enum import Enum

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


def execute_command(args):
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


def execute_line(command):
    """Разбирает строку и возвращает результат выполнения."""
    args = parse_command(command)
    if args is None:
        return CommandStatus.error
    return execute_command(args)


def run_interactive_mode():
    """Читает команды до exit, EOF или прерывания пользователем."""
    while True:
        try:
            command = input(create_prompt())
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if execute_line(command) == CommandStatus.exit:
            return


def main():
    """Запускает интерактивный эмулятор."""
    run_interactive_mode()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
