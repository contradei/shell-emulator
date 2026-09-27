"""Консольный эмулятор UNIX, вариант 9."""

import getpass
import socket
from enum import Enum

from src.shell_emulator.config import parse_arguments
from src.shell_emulator.parser import parse_command
from src.shell_emulator.vfs import VirtualFileSystem, VfsError


command_history = []


single_argument = 1
owner_arguments = 2


class CommandStatus(Enum):
    """Результат команды; имена соответствуют проверке snake_case."""

    success = "success"
    error = "error"
    exit = "exit"


def create_prompt():
    """Возвращает приглашение с реальными пользователем и хостом."""
    return f"{getpass.getuser()}@{socket.gethostname()}:~$ "


def execute_ls(arguments, vfs):
    """Выводит содержимое каталога, с владельцами для -l."""
    if arguments not in ([], ["-l"]):
        raise VfsError("используйте ls или ls -l")
    for node in vfs.list_directory():
        print(f"{node.owner}  {node.name}" if arguments else node.name)
    return CommandStatus.success


def execute_cd(arguments, vfs):
    """Меняет текущий каталог; без аргумента переходит в корень."""
    if len(arguments) > single_argument:
        raise VfsError("используйте cd [каталог]")
    vfs.change_directory(arguments[0] if arguments else "/")
    return CommandStatus.success


def execute_text(arguments, vfs, from_end=False):
    """Выводит первые или последние десять строк UTF-8 файла."""
    if len(arguments) != single_argument:
        raise VfsError("укажите один файл")
    try:
        lines = vfs.get_file(arguments[0]).data.decode("utf-8").splitlines()
    except UnicodeDecodeError as error:
        raise VfsError("файл не является текстовым") from error
    for line in (lines[-10:] if from_end else lines[:10]):
        print(line)
    return CommandStatus.success


def execute_history(arguments):
    """Выводит историю с номерами, включая сам вызов history."""
    if arguments:
        raise VfsError("history не принимает аргументы")
    for number, command in enumerate(command_history, start=1):
        print(f"{number}  {command}")
    return CommandStatus.success


def execute_chown(arguments, vfs):
    """Изменяет владельца узла только в оперативной памяти."""
    if len(arguments) != owner_arguments or not arguments[0]:
        raise VfsError("используйте chown <владелец> <путь>")
    vfs.change_owner(arguments[1], arguments[0])
    return CommandStatus.success


def execute_command(args, vfs=None):
    """Проверяет команду и преобразует ошибки VFS в статус."""
    if not args:
        return CommandStatus.success
    vfs = vfs if vfs is not None else VirtualFileSystem()
    command, arguments = args[0], args[1:]
    if command == "exit" and not arguments:
        return CommandStatus.exit
    handlers = {
        "ls": lambda: execute_ls(arguments, vfs),
        "cd": lambda: execute_cd(arguments, vfs),
        "head": lambda: execute_text(arguments, vfs),
        "tail": lambda: execute_text(arguments, vfs, True),
        "history": lambda: execute_history(arguments),
        "chown": lambda: execute_chown(arguments, vfs),
    }
    try:
        if command in handlers:
            return handlers[command]()
        raise VfsError(f"неизвестная команда или аргументы '{command}'")
    except VfsError as error:
        print(f"Ошибка: {error}")
        return CommandStatus.error


def execute_line(command, vfs=None):
    """Разбирает строку и возвращает результат выполнения."""
    if command.strip():
        command_history.append(command)
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
    command_history.clear()
    config = parse_arguments()
    print(f"VFS: {config.vfs}")
    print(f"Script: {config.script}")
    vfs = VirtualFileSystem()
    if config.vfs:
        try:
            vfs.load(config.vfs)
        except VfsError as error:
            print(f"Ошибка загрузки VFS: {error}")
            return 1
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
