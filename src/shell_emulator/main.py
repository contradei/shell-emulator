"""Консольный эмулятор UNIX, вариант 9."""

import getpass
import socket
from enum import Enum

from src.shell_emulator.config import parse_arguments
from src.shell_emulator.parser import parse_command
from src.shell_emulator.vfs import VirtualFileSystem, VfsError


command_history = []


single_argument = 1
count_arguments = 2
option_arguments = 3
default_lines = 10


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
    detailed = "-l" in arguments
    paths = [value for value in arguments if value != "-l"]
    if arguments.count("-l") > single_argument or len(paths) > single_argument:
        raise VfsError("используйте ls [-l] [каталог]")
    path = paths[0] if paths else "."
    if not path or path.startswith("-"):
        raise VfsError("укажите каталог; поддерживается только флаг -l")
    for node in vfs.list_directory(path):
        print(f"{node.owner}  {node.name}" if detailed else node.name)
    return CommandStatus.success


def execute_cd(arguments, vfs):
    """Меняет текущий каталог; без аргумента переходит в корень."""
    if len(arguments) > single_argument:
        raise VfsError("используйте cd [каталог]")
    vfs.change_directory(arguments[0] if arguments else "/")
    return CommandStatus.success


def parse_text_arguments(arguments):
    """Разбирает файл, файл N или [-n N] файл; N неотрицательно."""
    values = list(arguments)
    if len(values) == option_arguments and "-n" in values:
        index = values.index("-n")
        if index == len(values) - 1:
            raise VfsError("после -n укажите число строк")
        count = values.pop(index + 1)
        values.pop(index)
        values.append(count)
    if len(values) == single_argument:
        return values[0], default_lines
    if len(values) != count_arguments or not values[1].isascii():
        raise VfsError("используйте команду [-n N] файл или файл N")
    if not values[1].isdigit():
        raise VfsError("число строк должно быть целым неотрицательным")
    try:
        return values[0], int(values[1])
    except ValueError as error:
        raise VfsError("слишком большое число строк") from error


def execute_text(arguments, vfs, from_end=False):
    """Выводит заданное число первых/последних строк; по умолчанию 10."""
    path, count = parse_text_arguments(arguments)
    try:
        lines = vfs.get_file(path).data.decode("utf-8").splitlines()
    except UnicodeDecodeError as error:
        raise VfsError("файл не является текстовым") from error
    selected = lines[-count:] if from_end else lines[:count]
    for line in selected if count else []:
        print(line)
    return CommandStatus.success


def execute_history(arguments):
    """Выводит историю с номерами, включая сам вызов history."""
    if arguments:
        raise VfsError("history не принимает аргументы")
    for number, command in enumerate(command_history, start=1):
        print(f"{number}  {command}")
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
