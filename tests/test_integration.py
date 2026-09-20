"""Интеграционные сценарии для текущего этапа."""

import contextlib
import io
import subprocess
import sys
import unittest
from unittest.mock import patch

from src.shell_emulator import main


class TestInterface(unittest.TestCase):
    """Проверяет прерывание, вывод ls/cd и завершение сеанса."""

    def test_interrupt(self):
        """Ctrl+C завершается без необработанного исключения."""
        with patch("builtins.input", side_effect=KeyboardInterrupt):
            with contextlib.redirect_stdout(io.StringIO()):
                main.run_interactive_mode()

    def test_ls_cd(self):
        """Базовые команды принимаются на каждом этапе."""
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main.execute_line("ls"),
                             main.CommandStatus.success)
            self.assertEqual(main.execute_line("cd ."),
                             main.CommandStatus.success)


class TestParameters(unittest.TestCase):
    """Проверяет argparse, пути с пробелами и startup-вывод."""

    def test_parameters(self):
        """Оба параметра сохраняют полное значение пути."""
        from src.shell_emulator.config import parse_arguments

        with patch.object(sys, "argv", ["shell", "--vfs", "my vfs.xml",
                                        "--script", "my script.txt"]):
            config = parse_arguments()
        self.assertEqual(config.vfs, "my vfs.xml")
        self.assertEqual(config.script, "my script.txt")

    def test_invalid_parameter(self):
        """Неизвестный параметр и отсутствие значения дают код 2."""
        for arguments in (["--unknown"], ["--vfs"], ["--script"]):
            result = subprocess.run(
                [sys.executable, "-m", "src.shell_emulator.main", *arguments],
                input="", text=True, capture_output=True, timeout=10,
            )
            self.assertEqual(result.returncode, 2)

    def test_startup_success(self):
        """Успешный startup показывает ввод и вывод, затем exit."""
        result = subprocess.run(
            [sys.executable, "-m", "src.shell_emulator.main", "--script",
             "scripts/startup_basic.txt"], input="", text=True,
            capture_output=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("VFS:", result.stdout)
        self.assertIn("Script:", result.stdout)
        self.assertIn("$ ls", result.stdout)
        self.assertIn("$ exit", result.stdout)


class TestVfsCli(unittest.TestCase):
    """Проверяет настоящие сценарии startup и ошибки загрузки."""

    def test_demo(self):
        """Демонстрация всех успешных команд завершается успешно."""
        result = subprocess.run(
            [sys.executable, "-m", "src.shell_emulator.main", "--vfs",
             "vfs/several_files.xml", "--script", "startup.txt"],
            input="", text=True, capture_output=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def test_load_errors(self):
        """Ошибки VFS дают код 1 и не запускают REPL."""
        for name in ("missing", "invalid", "invalid_base64"):
            result = subprocess.run(
                [sys.executable, "-m", "src.shell_emulator.main", "--vfs",
                 f"vfs/{name}.xml"], input="never_run\nexit\n", text=True,
                capture_output=True, timeout=10,
            )
            self.assertEqual(result.returncode, 1)
            self.assertNotIn("never_run", result.stdout)
            self.assertNotIn("Traceback", result.stderr)
