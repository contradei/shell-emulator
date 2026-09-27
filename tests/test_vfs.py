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


class TestTextCommands(unittest.TestCase):
    """Проверяет head, tail, history и ошибки их аргументов."""

    def test_head_tail(self):
        """Head/tail выбирают правильные десять строк из 15."""
        vfs = sample_vfs()
        vfs.resolve("/home/lines.txt").data = "\n".join(
            str(number) for number in range(15)
        ).encode("utf-8")
        for command, expected in (("head", range(10)), ("tail", range(5, 15))):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main.execute_line(f"{command} /home/lines.txt", vfs)
            self.assertEqual(status, main.CommandStatus.success)
            self.assertEqual(output.getvalue().splitlines(),
                             [str(number) for number in expected])

    def test_text_errors(self):
        """Отсутствие файла, каталог, binary и аргументы дают ошибку."""
        vfs = sample_vfs()
        vfs.resolve("/home/hello.txt").data = b"\xff"
        commands = ("head", "tail", "head missing", "tail /home",
                    "head /home/hello.txt", "head a b", "history extra",
                    "ls bad", "cd a b", "exit bad")
        with contextlib.redirect_stdout(io.StringIO()):
            for command in commands:
                with self.subTest(command=command):
                    self.assertEqual(main.execute_line(command, vfs),
                                     main.CommandStatus.error)

    def test_empty_and_short_text(self):
        """Короткие и пустые файлы обрабатываются без лишних строк."""
        vfs = sample_vfs()
        for content in (b"", b"one\ntwo\n"):
            vfs.resolve("/home/hello.txt").data = content
            for command in ("head", "tail"):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    main.execute_line(f"{command} /home/hello.txt", vfs)
                self.assertEqual(output.getvalue(), content.decode())

    def test_history(self):
        """История содержит ошибки, команды и сам вызов history."""
        main.command_history.clear()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            main.execute_line("bad", sample_vfs())
            main.execute_line("history", sample_vfs())
        self.assertIn("1  bad", output.getvalue())
        self.assertIn("2  history", output.getvalue())


class TestChown(unittest.TestCase):
    """Проверяет chown, каталоги и неизменность исходного XML."""

    def test_owner_only_in_memory(self):
        """Владелец меняется в памяти и не переносится в новую VFS."""
        path = Path("vfs/several_files.xml")
        before = path.read_bytes()
        vfs = sample_vfs()
        for name in ("/home/hello.txt", "/home"):
            status = main.execute_line(f'chown "New Owner" {name}', vfs)
            self.assertEqual(status, main.CommandStatus.success)
            self.assertEqual(vfs.resolve(name).owner, "New Owner")
            self.assertEqual(sample_vfs().resolve(name).owner, "root")
        self.assertEqual(path.read_bytes(), before)

    def test_chown_errors(self):
        """Неверные аргументы и отсутствующий путь дают ошибку."""
        vfs = sample_vfs()
        with contextlib.redirect_stdout(io.StringIO()):
            for command in ("chown", "chown a", "chown a b c",
                            "chown a missing", 'chown "" /home'):
                with self.subTest(command=command):
                    self.assertEqual(main.execute_line(command, vfs),
                                     main.CommandStatus.error)
