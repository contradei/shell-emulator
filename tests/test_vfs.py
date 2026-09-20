"""Проверки XML, данных и изоляции виртуальной файловой системы."""

import base64
import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from src.shell_emulator import main
from src.shell_emulator.vfs import VirtualFileSystem, VfsError


def sample_vfs():
    """Создаёт независимую VFS для каждого теста."""
    vfs = VirtualFileSystem()
    vfs.load("vfs/several_files.xml")
    return vfs


class TestVfs(unittest.TestCase):
    """Проверяет загрузку, навигацию, XML и Base64."""

    def test_fixtures(self):
        """Все положительные XML-примеры загружаются."""
        for name in ("minimal", "several_files", "nested", "base64"):
            with self.subTest(name=name):
                vfs = VirtualFileSystem()
                vfs.load(f"vfs/{name}.xml")
                self.assertEqual(vfs.get_current_path(), "/")

    def test_navigation(self):
        """Пути разрешаются в VFS, переход выше корня безопасен."""
        vfs = sample_vfs()
        vfs.change_directory("/home")
        self.assertEqual(vfs.get_current_path(), "/home")
        vfs.change_directory(".././../../")
        self.assertEqual(vfs.get_current_path(), "/")
        with self.assertRaises(VfsError):
            vfs.change_directory("/home/hello.txt")
        self.assertEqual(vfs.get_current_path(), "/")
        with self.assertRaises(VfsError):
            vfs.resolve("/home/hello.txt/..")
        with self.assertRaises(VfsError):
            vfs.resolve("/home/hello.txt/")

    def test_nested(self):
        """Три уровня каталогов и файл на четвёртом доступны."""
        vfs = VirtualFileSystem()
        vfs.load("vfs/nested.xml")
        vfs.change_directory("home/user/documents")
        self.assertEqual(vfs.get_current_path(), "/home/user/documents")
        self.assertEqual(vfs.list_directory()[0].name, "report.txt")

    def test_invalid_fixtures(self):
        """Отсутствующий XML, XML-синтаксис и Base64 дают VfsError."""
        for path in ("vfs/missing.xml", "vfs/invalid.xml",
                     "vfs/invalid_base64.xml", "vfs"):
            with self.subTest(path=path), self.assertRaises(VfsError):
                VirtualFileSystem().load(path)

    def test_invalid_structure(self):
        """Проверяет неверный корень, узлы, дубликаты и кодировки."""
        documents = [
            '<file name="x"/>', '<vfs><unknown name="x"/></vfs>',
            '<vfs><file/></vfs>', '<vfs><file name="../x"/></vfs>',
            '<vfs><file name="x"/><file name="x"/></vfs>',
            '<vfs><file name="x"><file name="y"/></file></vfs>',
            '<vfs><file name="x" encoding="bad"/></vfs>',
            '<vfs><file name="x" encoding="base64">я</file></vfs>',
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.xml"
            for document in documents:
                path.write_text(document, encoding="utf-8")
                with self.subTest(document=document):
                    with self.assertRaises(VfsError):
                        VirtualFileSystem().load(path)

    def test_binary_and_memory(self):
        """Двоичные данные сохраняются; XML не нужен после загрузки."""
        data = bytes(range(256))
        encoded = base64.b64encode(data).decode("ascii")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "binary.xml"
            path.write_text('<vfs><file name="data" encoding="base64">'
                            + encoded + '</file></vfs>', encoding="utf-8")
            vfs = VirtualFileSystem()
            vfs.load(path)
        self.assertEqual(vfs.resolve("data").data, data)

    def test_failed_reload_is_atomic(self):
        """Ошибка повторной загрузки не уничтожает прежнее дерево."""
        vfs = sample_vfs()
        original = vfs.root
        with self.assertRaises(VfsError):
            vfs.load("vfs/invalid_base64.xml")
        self.assertIs(vfs.root, original)

    def test_ls_cd_and_errors(self):
        """Реальные ls/cd работают и сообщают об ошибках."""
        vfs = sample_vfs()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main.execute_line("ls", vfs),
                             main.CommandStatus.success)
            self.assertEqual(main.execute_line("cd home", vfs),
                             main.CommandStatus.success)
            self.assertEqual(main.execute_line("cd missing", vfs),
                             main.CommandStatus.error)
        self.assertIn("home", output.getvalue())
        self.assertEqual(vfs.get_current_path(), "/home")
