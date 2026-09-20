"""Виртуальная файловая система: XML читается только при загрузке."""

import base64
from xml.etree.ElementTree import ParseError, parse


class VfsError(Exception):
    """Ошибка виртуальной файловой системы."""


class VfsNode:
    """Файл или каталог в оперативной памяти."""

    def __init__(self, name, node_type, data=b"", owner="root"):
        """Создаёт узел без привязки к файловой системе хоста."""
        self.name = name
        self.node_type = node_type
        self.data = data
        self.owner = owner
        self.children = []
        self.parent = None


class VirtualFileSystem:
    """Дерево VFS и текущий каталог."""

    def __init__(self):
        """Создаёт пустой корневой каталог."""
        self.root = VfsNode("/", "directory")
        self.current_directory = self.root

    def load(self, path):
        """Атомарно заменяет дерево после проверки XML и Base64."""
        try:
            element = parse(path).getroot()
            if element.tag not in ("vfs", "directory"):
                raise VfsError("корень VFS должен быть каталогом")
            root = self._parse_node(element, is_root=True)
        except (OSError, ParseError, RecursionError) as error:
            raise VfsError(f"Не удалось загрузить VFS: {error}") from error
        self.root = root
        self.current_directory = root

    def _parse_node(self, element, is_root=False):
        """Проверяет узел и рекурсивно строит дочерние узлы."""
        name = element.get("name", "")
        allowed = ("vfs", "directory") if is_root else ("directory", "file")
        if element.tag not in allowed:
            raise VfsError(f"Неизвестный тип узла: {element.tag}")
        if not is_root and (not name or name in (".", "..") or "/" in name):
            raise VfsError("Некорректное имя узла")
        if element.tag == "file":
            return self._parse_file(element, name)
        node = VfsNode(name, "directory", owner=element.get("owner", "root"))
        names = set()
        for child in element:
            child_node = self._parse_node(child)
            if child_node.name in names:
                raise VfsError(f"Повторное имя узла: {child_node.name}")
            names.add(child_node.name)
            child_node.parent = node
            node.children.append(child_node)
        return node

    def _parse_file(self, element, name):
        """Читает текст или строгие Base64-данные файла."""
        if len(element):
            raise VfsError("Файл не может содержать дочерние узлы")
        encoding = element.get("encoding", "text")
        text = element.text or ""
        if encoding == "base64":
            data = self.decode_data("".join(text.split()))
        elif encoding in ("text", "utf-8"):
            data = text.encode("utf-8")
        else:
            raise VfsError(f"Неизвестная кодировка: {encoding}")
        return VfsNode(name, "file", data, element.get("owner", "root"))

    def resolve(self, path):
        """Разрешает относительный/абсолютный путь внутри дерева VFS."""
        node = self.root if path.startswith("/") else self.current_directory
        for part in path.split("/"):
            if not part:
                continue
            if node.node_type != "directory":
                raise VfsError(f"Не является каталогом: {node.name}")
            if part == ".":
                continue
            if part == "..":
                node = node.parent or node
            else:
                node = self._find_child(node, part)
        if path.endswith("/") and node.node_type != "directory":
            raise VfsError(f"Не является каталогом: {path}")
        return node

    def _find_child(self, node, name):
        """Находит дочерний узел или сообщает об отсутствии."""
        for child in node.children:
            if child.name == name:
                return child
        raise VfsError(f"Файл или каталог не найден: {name}")

    def list_directory(self):
        """Возвращает элементы текущего каталога."""
        return list(self.current_directory.children)

    def change_directory(self, path):
        """Переходит в каталог, сохраняя состояние при ошибке."""
        node = self.resolve(path)
        if node.node_type != "directory":
            raise VfsError(f"Не является каталогом: {path}")
        self.current_directory = node

    def get_current_path(self):
        """Возвращает абсолютный путь текущего каталога."""
        parts = []
        node = self.current_directory
        while node.parent is not None:
            parts.append(node.name)
            node = node.parent
        return "/" + "/".join(reversed(parts))

    def decode_data(self, value):
        """Декодирует Base64 без игнорирования неверных символов."""
        try:
            return base64.b64decode(value, validate=True)
        except ValueError as error:
            raise VfsError("Некорректные данные Base64") from error
