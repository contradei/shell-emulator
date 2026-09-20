"""Проверки поведения команд соответствующего этапа."""

import contextlib
import io
import subprocess
import sys
import unittest
from unittest.mock import patch

from src.shell_emulator import main
from src.shell_emulator.parser import parse_command


class TestShell(unittest.TestCase):
    """Проверяет интерфейс, парсер и обработку ошибок."""

    def test_parser(self):
        """Проверяет кавычки, пустой ввод и неправильную строку."""
        self.assertEqual(parse_command('cd "my folder"'), ["cd", "my folder"])
        self.assertEqual(parse_command("  "), [])
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertIsNone(parse_command('head "unfinished'))

    def test_prompt(self):
        """Проверяет использование реальных данных ОС."""
        with patch.object(main.getpass, "getuser", return_value="user"):
            with patch.object(main.socket, "gethostname", return_value="host"):
                self.assertEqual(main.create_prompt(), "user@host:~$ ")

    def test_exit_and_error(self):
        """Проверяет пустую команду, exit и неизвестную команду."""
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main.execute_line(""), main.CommandStatus.success)
            self.assertEqual(main.execute_line("exit"), main.CommandStatus.exit)
            self.assertEqual(main.execute_line("bad"), main.CommandStatus.error)

    def test_repl_eof(self):
        """EOF завершает процесс без traceback."""
        result = subprocess.run(
            [sys.executable, "-m", "src.shell_emulator.main"],
            input="", capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_repl_recovers(self):
        """После ошибки интерактивный ввод продолжает работать."""
        result = subprocess.run(
            [sys.executable, "-m", "src.shell_emulator.main"],
            input='bad\n"broken\nexit\n', capture_output=True,
            text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
