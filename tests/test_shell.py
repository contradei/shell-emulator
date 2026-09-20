"""Проверки поведения команд соответствующего этапа."""

import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
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


class TestStartup(unittest.TestCase):
    """Проверяет успешное выполнение и остановку startup."""

    def run_script(self, content):
        """Выполняет временный скрипт и возвращает вывод и статус."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "startup with spaces.txt"
            path.write_text(content, encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main.run_startup_script(path)
            return status, output.getvalue()

    def test_script_error(self):
        """Ошибка останавливает скрипт до следующей команды."""
        status, output = self.run_script("bad\nnever_run\n")
        self.assertEqual(status, main.CommandStatus.error)
        self.assertIn("bad", output)
        self.assertIn("1", output)
        self.assertNotIn("never_run", output)

    def test_script_parse_error(self):
        """Незакрытые кавычки останавливают скрипт."""
        status, output = self.run_script('"broken\nnever_run\n')
        self.assertEqual(status, main.CommandStatus.error)
        self.assertNotIn("never_run", output)

    def test_script_exit(self):
        """Exit прекращает обработку, пустые строки разрешены."""
        status, output = self.run_script("\nexit\nnever_run\n")
        self.assertEqual(status, main.CommandStatus.exit)
        self.assertIn("exit", output)
        self.assertNotIn("never_run", output)

    def test_script_empty(self):
        """Пустой скрипт считается успешным."""
        status, output = self.run_script("\n")
        self.assertEqual(status, main.CommandStatus.success)
        self.assertEqual(output, "")

    def test_script_cli_error(self):
        """Ошибка startup даёт ненулевой код и не запускает REPL."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.txt"
            path.write_text("bad\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-m", "src.shell_emulator.main",
                 "--script", str(path)], input="never_run\nexit\n",
                capture_output=True, text=True, timeout=10,
            )
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("never_run", result.stdout)

    def test_script_unreadable(self):
        """Отсутствие и неверная кодировка дают управляемую ошибку."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.txt"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main.run_startup_script(path),
                                 main.CommandStatus.error)
                path.write_bytes(b"\xff\xfe\xff")
                self.assertEqual(main.run_startup_script(path),
                                 main.CommandStatus.error)

    def test_script_success_output(self):
        """Успешные команды показывают ввод и завершаются без ошибки."""
        status, output = self.run_script("ls\ncd .\n")
        self.assertEqual(status, main.CommandStatus.success)
        self.assertIn("$ ls", output)
        self.assertIn("$ cd .", output)

    def test_script_bom(self):
        """UTF-8 BOM в Windows-скрипте не становится частью команды."""
        status, output = self.run_script("\ufeffexit\nnever_run\n")
        self.assertEqual(status, main.CommandStatus.exit)
        self.assertNotIn("never_run", output)

    def test_script_reports_physical_line(self):
        """Пустые строки не смещают номер ошибочной команды."""
        status, output = self.run_script("\n\nbad\nnever_run\n")
        self.assertEqual(status, main.CommandStatus.error)
        self.assertIn("строка 3", output)
        self.assertNotIn("never_run", output)
