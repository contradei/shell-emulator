import base64
import xml.etree.ElementTree as ET


class VfsError(Exception):
    """Ошибка виртуальной файловой системы."""


class VfsNode:
    """Элемент виртуальной файловой системы."""

    def __init__(self, name, node_type, data=b""):
        """Создаёт элемент VFS."""

        self.name = name
        self.node_type = node_type
        self.data = data
        self.children = []
        self.parent = None


class VirtualFileSystem:
    """Виртуальная файловая система, загруженная из XML."""

    def __init__(self):
        """Создаёт пустую виртуальную файловую систему."""

        self.root = None
        self.current_directory = None

    def load(self, path):
        """Загружает виртуальную файловую систему из XML."""

        try:
            tree = ET.parse(path)
        except FileNotFoundError as error:
            raise VfsError(
                f"VFS-файл не найден: {path}"
            ) from error
        except ET.ParseError as error:
            raise VfsError(
                f"Некорректный формат VFS-файла: {path}"
            ) from error

        xml_root = tree.getroot()
        self.root = self._parse_node(xml_root)
        self.current_directory = self.root

    def _parse_node(self, element):
        """Преобразует XML-элемент в узел VFS."""

        name = element.get("name", "")
        node_type = element.tag

        if node_type == "file":
            data = element.text or ""

            if element.get("encoding") == "base64":
                decoded_data = self.decode_data(data.strip())
            else:
                decoded_data = data.encode("utf-8")

            return VfsNode(
                name,
                "file",
                decoded_data
            )
        node = VfsNode(name, "directory")

        for child in element:
            child_node = self._parse_node(child)
            child_node.parent = node
            node.children.append(child_node)

        return node

    def list_directory(self):
        """Возвращает содержимое текущего каталога."""

        if self.current_directory is None:
            return []

        return self.current_directory.children

    def get_file(self, name):
        """Возвращает файл из текущего каталога."""

        if self.current_directory is None:
            raise VfsError("VFS не загружена")

        for child in self.current_directory.children:
            if child.name == name:
                if child.node_type != "file":
                    raise VfsError(
                        f"Не является файлом: {name}"
                    )

                return child

        raise VfsError(
            f"Файл не найден: {name}"
        )

    def change_directory(self, name):
        """Переходит в указанный каталог."""

        if name == ".":
            return

        if name == "..":
            if self.current_directory.parent is not None:
                self.current_directory = (
                    self.current_directory.parent
                )
            return

        for child in self.current_directory.children:
            if child.name == name:
                if child.node_type != "directory":
                    raise VfsError(
                        f"Не является каталогом: {name}"
                    )

                self.current_directory = child
                return

        raise VfsError(
            f"Каталог не найден: {name}"
        )

    def get_current_path(self):
        """Возвращает путь текущего каталога."""

        if self.current_directory is None:
            return "/"

        parts = []
        node = self.current_directory

        while node is not None:
            if node.parent is not None:
                parts.append(node.name)
            node = node.parent

        parts.reverse()

        if not parts:
            return "/"

        return "/" + "/".join(parts)

    def decode_data(self, value):
        """Декодирует данные файла из Base64."""

        try:
            return base64.b64decode(value, validate=True)
        except ValueError as error:
            raise VfsError(
                "Некорректные данные Base64"
            ) from error