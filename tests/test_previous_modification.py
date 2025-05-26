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
        sublime.active_window().focus_view(self.view_saved)

        yield lambda: not self.view_saved.is_loading()
        self.view_saved.sel().clear()
        self.view_saved.sel().add(sublime.Region(3, 3))
        yield from self._insert("1", self.view_saved)

        self.view_closed.sel().clear()
        self.view_closed.sel().add(sublime.Region(5, 5))
        yield from self._insert("2", self.view_closed)
        yield from self._insert("3", self.view_closed)
        yield from self._insert("4", self.view_closed)

        self.view_closed.run_command("save")
        self.view_closed.close()

        sublime.active_window().focus_view(self.view_tmp)
        yield lambda: not self.view_tmp.is_loading()
        yield from self._insert("5", self.view_tmp)
        yield from self._insert("6", self.view_tmp)
        yield from self._insert("7", self.view_tmp)

        views = list(sublime.active_window().views())
        view_count = len(views)
        print("view_count", view_count)

        sublime.active_window().focus_view(self.view_saved)
        self.assertEqual(self._current_position(), (self.view_saved, 5))

        sublime.active_window().run_command("jumper_previous_modification")
        self.assertEqual(self._current_position(), (self.view_tmp, 6))

        sublime.active_window().run_command("jumper_previous_modification")
        self.assertEqual(self._current_position(), (self.view_tmp, 5))

        sublime.active_window().run_command("jumper_previous_modification")
        self.assertEqual(self._current_position(), (self.view_tmp, 3))

        sublime.active_window().run_command(
            "jumper_previous_modification", {"direction": "next"}
        )
        self.assertEqual(self._current_position(), (self.view_tmp, 5))

        sublime.active_window().run_command(
            "jumper_previous_modification", {"direction": "next"}
        )
        self.assertEqual(self._current_position(), (self.view_tmp, 6))

        sublime.active_window().run_command("jumper_previous_modification")
        sublime.active_window().run_command("jumper_previous_modification")
        sublime.active_window().run_command("jumper_previous_modification")
        self.assertEqual(self._current_position(), (self.view_tmp, 1))

        sublime.active_window().run_command("jumper_previous_modification")
        yield 25
        self.assertEqual(
            len(sublime.active_window().views()),
            view_count + 1,
            "Should open the closed file",
        )
        view_closed = next(v for v in sublime.active_window().views() if v not in views)
        self.assertEqual(self._current_position(), (view_closed, 11))

        sublime.active_window().run_command("jumper_previous_modification")
        self.assertEqual(self._current_position(), (view_closed, 10))

        sublime.active_window().run_command("jumper_previous_modification")
        self.assertEqual(self._current_position(), (view_closed, 8))

        sublime.active_window().run_command("jumper_previous_modification")
        self.assertEqual(self._current_position(), (view_closed, 6))

        # Test that we close the file, except if we save
        sublime.active_window().run_command("jumper_previous_modification")
        yield 25
        self.assertEqual(self._current_position(), (self.view_saved, 5))
        self.assertEqual(
            len(sublime.active_window().views()), view_count, "Should close the file"
        )

        sublime.active_window().run_command(
            "jumper_previous_modification", {"direction": "next"}
        )
        yield 25
        self.assertEqual(
            len(sublime.active_window().views()), view_count + 1, "Should open the file"
        )
        view_closed = next(v for v in sublime.active_window().views() if v not in views)
        yield from self._insert(
            "Test", view_closed
        )  # After editing, don't automatically close
        self.assertEqual(self._current_position(), (view_closed, 11))

        sublime.active_window().run_command("jumper_previous_modification")
        self.assertEqual(self._current_position(), (view_closed, 10))

        # Now that we edited, when going back, restart from the top of the history
        sublime.active_window().run_command("jumper_previous_modification")
        self.assertEqual(
            len(sublime.active_window().views()),
            view_count + 1,
            "Should not close the file",
        )
        self.assertEqual(self._current_position(), (self.view_tmp, 6))

        self.view_tmp.set_scratch(True)
        self.view_tmp.close()
        self.view_saved.set_scratch(True)
        self.view_saved.close()
        view_closed.set_scratch(True)
        view_closed.close()

    def _insert(self, s, view):
        view.run_command("insert", {"characters": s})
        yield 25
        view.run_command("insert", {"characters": "\n"})
        yield 25

    def _current_position(self):
        view = sublime.active_window().active_view()
        assert len(view.sel()) == 1
        return view, view.sel()[0].a
