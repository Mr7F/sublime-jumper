import sublime
from unittesting import DeferrableTestCase

_code = """
test

testaa

Test

testbb

testaa

testaa

testbb
""".strip()


class TestDeferrable(DeferrableTestCase):
    def setUp(self):
        self.view = sublime.active_window().new_file()
        self.view.set_scratch(True)
        self.view.assign_syntax("Python.sublime-syntax")

    def test_select_bracket(self):
        yield from self._run_cmd("insert", {"characters": _code})

        # Test word mode
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(33, 33))
        yield from self._run_cmd(
            "select_next_same_selection", {"keep_selection": False}
        )
        self.assertEqual(len(self.view.sel()), 1)
        self.assertEqual(self.view.sel()[0].to_tuple(), (28, 34))

        yield from self._run_cmd(
            "select_next_same_selection", {"keep_selection": False}
        )
        self.assertEqual(len(self.view.sel()), 1)
        self.assertEqual(self.view.sel()[0].to_tuple(), (36, 42))

        yield from self._run_cmd(
            "select_next_same_selection",
            {"keep_selection": False, "direction": "previous"},
        )
        self.assertEqual(len(self.view.sel()), 1)
        self.assertEqual(self.view.sel()[0].to_tuple(), (28, 34))

        yield from self._run_cmd(
            "select_next_same_selection",
            {"keep_selection": True, "direction": "previous"},
        )
        self.assertEqual(len(self.view.sel()), 2)
        self.assertEqual(self.view.sel()[0].to_tuple(), (6, 12))
        self.assertEqual(self.view.sel()[1].to_tuple(), (28, 34))

        yield from self._run_cmd(
            "select_next_same_selection",
            {"keep_selection": True, "direction": "previous"},
        )
        self.assertEqual(len(self.view.sel()), 3)
        self.assertEqual(self.view.sel()[0].to_tuple(), (6, 12))
        self.assertEqual(self.view.sel()[1].to_tuple(), (28, 34))
        self.assertEqual(self.view.sel()[2].to_tuple(), (36, 42))

        yield from self._run_cmd(
            "select_next_same_selection",
            {"keep_selection": False, "direction": "previous"},
        )
        self.assertEqual(len(self.view.sel()), 2)
        self.assertEqual(self.view.sel()[0].to_tuple(), (6, 12))
        self.assertEqual(self.view.sel()[1].to_tuple(), (28, 34))

        # Test text mode
        yield from self._run_cmd(
            # Move the cursor to reset
            "expand_selection",
            {"to": "line"},
        )
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(28, 31))

        yield from self._run_cmd(
            "select_next_same_selection", {"keep_selection": False}
        )
        self.assertEqual(len(self.view.sel()), 1)
        self.assertEqual(self.view.sel()[0].to_tuple(), (36, 39))

        yield from self._run_cmd(
            "select_next_same_selection", {"keep_selection": False}
        )
        self.assertEqual(len(self.view.sel()), 1)
        self.assertEqual(self.view.sel()[0].to_tuple(), (44, 47))

        yield from self._run_cmd("select_next_same_selection", {"keep_selection": True})
        self.assertEqual(len(self.view.sel()), 2)
        self.assertEqual(self.view.sel()[0].to_tuple(), (0, 3))
        self.assertEqual(self.view.sel()[1].to_tuple(), (44, 47))

        yield from self._run_cmd("select_next_same_selection", {"keep_selection": True})
        self.assertEqual(len(self.view.sel()), 3)
        self.assertEqual(self.view.sel()[0].to_tuple(), (0, 3))
        self.assertEqual(self.view.sel()[1].to_tuple(), (6, 9))
        self.assertEqual(self.view.sel()[2].to_tuple(), (44, 47))

        for _ in range(2):
            yield from self._run_cmd(
                "select_next_same_selection",
                {"keep_selection": True, "direction": "previous"},
            )
            self.assertEqual(len(self.view.sel()), 3)
            self.assertEqual(self.view.sel()[0].to_tuple(), (0, 3))
            self.assertEqual(self.view.sel()[1].to_tuple(), (6, 9))
            self.assertEqual(self.view.sel()[2].to_tuple(), (44, 47))

        yield from self._run_cmd(
            "select_next_same_selection",
            {"keep_selection": True, "direction": "previous"},
        )
        self.assertEqual(len(self.view.sel()), 4)
        self.assertEqual(self.view.sel()[0].to_tuple(), (0, 3))
        self.assertEqual(self.view.sel()[1].to_tuple(), (6, 9))
        self.assertEqual(self.view.sel()[2].to_tuple(), (36, 39))
        self.assertEqual(self.view.sel()[3].to_tuple(), (44, 47))
        self.view.close()

    def _run_cmd(self, cmd, args):
        yield 25  # Need to wait `on_selection_modified`
        self.view.run_command(cmd, args)
