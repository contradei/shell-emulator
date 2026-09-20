import shlex


def parse_command(command):
    try:
        return shlex.split(command)
    except ValueError as error:
        print(f"Ошибка разбора команды: {error}")
        return None