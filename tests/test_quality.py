"""Проверки правил методички для всех отслеживаемых исходников."""

import ast
from pathlib import Path
import re
import unittest


max_file_lines = 1000
max_python_line = 80
max_other_line = 120
max_function_lines = 40
max_arguments = 7
snake_case = re.compile(r"^_?[a-z][a-z0-9_]*$|^__[a-z_]+__$")
class_case = re.compile(r"^[A-Z][a-zA-Z0-9]+$")


class TestQuality(unittest.TestCase):
    """Проверяет структуру, размеры, документацию и имена."""

    def test_structure(self):
        """Все обязательные файлы и каталоги существуют."""
        for name in ("README.md", ".gitignore", "src", "tests", "run.bat"):
            self.assertTrue(Path(name).exists(), name)
        self.assertIn("%*", Path("run.bat").read_text(encoding="utf-8"))

    def test_python_files(self):
        """Проверяет длину строк, функций и AST каждого Python-файла."""
        for folder in ("src", "tests"):
            for path in Path(folder).rglob("*.py"):
                with self.subTest(path=path):
                    source = path.read_text(encoding="utf-8")
                    lines = source.splitlines()
                    self.assertLessEqual(len(lines), max_file_lines)
                    for line in lines:
                        self.assertLessEqual(len(line), max_python_line, line)
                    tree = ast.parse(source)
                    self.assertTrue(ast.get_docstring(tree), str(path))
                    self.check_nodes(tree)

    def check_nodes(self, tree):
        """Проверяет определения, аргументы и числовые сравнения."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.assertRegex(node.name, snake_case)
                self.assertTrue(ast.get_docstring(node), node.name)
                self.assertLessEqual(node.end_lineno - node.lineno + 1,
                                     max_function_lines, node.name)
                args = node.args
                count = len(args.posonlyargs + args.args + args.kwonlyargs)
                count += bool(args.vararg) + bool(args.kwarg)
                self.assertLessEqual(count, max_arguments, node.name)
            elif isinstance(node, ast.ClassDef):
                self.assertRegex(node.name, class_case)
                self.assertTrue(ast.get_docstring(node), node.name)
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                self.assertRegex(node.id, snake_case)
            elif isinstance(node, ast.arg):
                self.assertRegex(node.arg, snake_case)
            elif isinstance(node, ast.Compare):
                for value in [node.left, *node.comparators]:
                    if isinstance(value, ast.Constant):
                        self.assertNotIsInstance(value.value, (int, float))

    def test_text_sizes(self):
        """Демонстрационные файлы и README тоже укладываются в лимиты."""
        paths = [Path("README.md"), Path("run.bat"), Path(".gitignore")]
        for folder in ("scripts", "vfs"):
            paths.extend(path for path in Path(folder).glob("*")
                         if path.is_file())
        for path in paths:
            lines = path.read_text(encoding="utf-8").splitlines()
            self.assertLessEqual(len(lines), max_file_lines, str(path))
            for line in lines:
                self.assertLessEqual(len(line), max_other_line, str(path))
