"""Регрессия Windows launcher: кавычки, cwd и коды завершения."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


@unittest.skipUnless(os.name == "nt", "Windows BAT launcher")
class TestLauncher(unittest.TestCase):
    """Проверяет запуск через настоящий cmd.exe."""

    def test_paths_with_spaces(self):
        """BAT передаёт оба абсолютных пути из другого каталога."""
        launcher = Path("run.bat").resolve()
        with tempfile.TemporaryDirectory(prefix="shell test ") as directory:
            script = Path(directory) / "startup with spaces.txt"
            vfs = Path(directory) / "vfs with spaces.xml"
            script.write_text("ls\nexit\n", encoding="utf-8")
            vfs.write_text('<vfs><file name="forwarded.txt"/></vfs>',
                           encoding="utf-8")
            command = (f'cmd /d /s /c ""{launcher}" --vfs "{vfs}" '
                       f'--script "{script}""')
            environment = dict(os.environ)
            environment["PATH"] = (str(Path(sys.executable).parent)
                                   + os.pathsep + environment["PATH"])
            result = subprocess.run(command, cwd=directory, input="",
                                    capture_output=True, text=True,
                                    env=environment, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("forwarded.txt", result.stdout)

    def test_failure_exit_code(self):
        """BAT сохраняет ненулевой код ошибки Python."""
        environment = dict(os.environ)
        environment["PATH"] = (str(Path(sys.executable).parent)
                               + os.pathsep + environment["PATH"])
        result = subprocess.run(
            ["cmd", "/d", "/c", "run.bat", "--vfs", "vfs/missing.xml"],
            input="", capture_output=True, text=True,
            env=environment, timeout=10,
        )
        self.assertEqual(result.returncode, 1)
