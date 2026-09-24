"""Directory arguments and configurable head/tail line counts."""

import contextlib
import io
import unittest

from src.shell_emulator import main
from tests.test_vfs import sample_vfs


def run_command(command, vfs):
    """Capture a command's status and printed lines."""
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        status = main.execute_line(command, vfs)
    return status, output.getvalue().splitlines()


class TestStageArguments(unittest.TestCase):
    """Check real commands and preserve current-directory state."""

    def test_ls_paths(self):
        """List relative/absolute directories without changing cwd."""
        vfs = sample_vfs()
        for command in ('ls home', 'ls /home', 'ls ./home', 'ls -l home',
                        'ls home -l'):
            status, lines = run_command(command, vfs)
            self.assertEqual(status, main.CommandStatus.success)
            self.assertTrue(any('hello.txt' in line for line in lines))
            self.assertEqual(vfs.get_current_path(), '/')
        vfs.change_directory('/home')
        self.assertIn('home', run_command('ls ..', vfs)[1])
        self.assertEqual(vfs.get_current_path(), '/home')

    def test_ls_quoted_path(self):
        """Quoted directory names remain valid parser arguments."""
        vfs = sample_vfs()
        vfs.resolve('/home').name = 'my folder'
        status, lines = run_command('ls "my folder"', vfs)
        self.assertEqual(status, main.CommandStatus.success)
        self.assertIn('hello.txt', lines)

    def test_line_counts(self):
        """Support -n before/after the file and a trailing numeric count."""
        vfs = sample_vfs()
        vfs.resolve('/home/lines.txt').data = b'one\ntwo\nthree\nfour\n'
        lines = ['one', 'two', 'three', 'four']
        for count in (0, 1, 3, 20):
            for command in ('head', 'tail'):
                expected = (lines[:count] if command == 'head'
                            else lines[-count:])
                expected = expected if count else []
                for args in (f'-n {count} /home/lines.txt',
                             f'/home/lines.txt -n {count}',
                             f'/home/lines.txt {count}'):
                    with self.subTest(command=command, args=args):
                        status, output = run_command(f'{command} {args}', vfs)
                        self.assertEqual(status, main.CommandStatus.success)
                        self.assertEqual(output, expected)

    def test_invalid_arguments(self):
        """Reject files as directories, extra arguments and invalid counts."""
        vfs = sample_vfs()
        commands = ['ls /home/hello.txt', 'ls missing', 'ls home other',
                    'ls -x', 'ls -l -l', 'ls ""']
        for name in ('head', 'tail'):
            for args in ('-n', '-n 2', '-n -1 /home/lines.txt',
                         '-n word /home/lines.txt', '/home/lines.txt 1.5',
                         '-x 2 /home/lines.txt', '/home/lines.txt 2 extra'):
                commands.append(f'{name} {args}')
        for command in commands:
            with self.subTest(command=command):
                self.assertEqual(run_command(command, vfs)[0],
                                 main.CommandStatus.error)
