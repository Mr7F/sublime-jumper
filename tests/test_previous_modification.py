import os
import sublime
import time
from unittesting import DeferrableTestCase

_content = """
A
B
C
""".strip()


class TestDeferrable(DeferrableTestCase):
    def setUp(self):
        self.file_closed = f"/dev/shm/.test_sublime_{os.urandom(8).hex()}"
        self.file_opened = f"/dev/shm/.test_sublime_{os.urandom(8).hex()}"

        with open(self.file_closed, "w") as file:
            file.write(_content[::-1])

        with open(self.file_opened, "w") as file:
            file.write(_content)

        self.view_saved = sublime.active_window().open_file(self.file_opened)
        self.view_closed = sublime.active_window().open_file(self.file_closed)
        self.view_tmp = sublime.active_window().new_file()

    def test_previous_modification(self):
        sublime.active_window().focus_view(self.view_closed)

        yield lambda: not self.view_closed.is_loading()
        self.view_closed.sel().clear()
        self.view_closed.sel().add(sublime.Region(3, 3))
        self._insert("1", self.view_closed)

        self.view_closed.sel().clear()
        self.view_closed.sel().add(sublime.Region(5, 5))
        self._insert("2", self.view_closed)
        self._insert("3", self.view_closed)
        self._insert("4", self.view_closed)

        # self.view_closed.run_command("save")
        # self.view_closed.close()

        # sublime.active_window().focus_view(self.view_tmp)
        # yield lambda: not self.view_tmp.is_loading()
        # self._insert("5", self.view_tmp)
        # self._insert("6", self.view_tmp)
        # self._insert("7", self.view_tmp)

        # sublime.active_window().focus_view(self.view_saved)

    def _insert(self, s, view):
        view.run_command("insert", {"characters": s})
        view.run_command("insert", {"characters": "\n"})
