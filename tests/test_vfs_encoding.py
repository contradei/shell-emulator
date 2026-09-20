"""Проверка единого Base64-формата файлов VFS."""

import base64
from pathlib import Path
import unittest
from xml.etree.ElementTree import parse


class TestVfsEncoding(unittest.TestCase):
    """Проверяет все положительные XML-примеры в каталоге vfs."""

    def test_all_file_contents_are_base64(self):
        """Текстовые и двоичные файлы имеют корректный Base64 payload."""
        for path in Path("vfs").glob("*.xml"):
            if path.name in ("invalid.xml", "invalid_base64.xml"):
                continue
            for node in parse(path).getroot().iter("file"):
                with self.subTest(path=path, name=node.get("name")):
                    self.assertEqual(node.get("encoding"), "base64")
                    payload = "".join((node.text or "").split())
                    base64.b64decode(payload, validate=True)
