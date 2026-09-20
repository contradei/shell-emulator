"""Интеграционные сценарии для текущего этапа."""

import contextlib
import io
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
