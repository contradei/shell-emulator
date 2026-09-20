"""Разбор команд с кавычками."""

import shlex


def parse_command(command):
    """Разбирает строку команды на имя команды и аргументы."""

    try:
        return shlex.split(command)
    except ValueError as error:
        print(f"Ошибка разбора команды: {error}")
        return None
