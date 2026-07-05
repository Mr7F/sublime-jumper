import sublime
from unittesting import DeferrableTestCase


_comment_args = {
    "selector": "comment",
    "trim_selector": "punctuation",
    "trim": True,
}


class TestDeferrable(DeferrableTestCase):
    def setUp(self):
        self.view = sublime.active_window().new_file()
        self.view.set_scratch(True)
        self.view.assign_syntax("Python.sublime-syntax")

    def tearDown(self):
        self.view.close()

    def _assert_selection(self, expected_region, expected_text):
        selection = self.view.sel()[0]
        self.assertEqual(selection.to_tuple(), expected_region)
        self.assertEqual(self.view.substr(selection), expected_text)

    def test_select_empty_triple_quoted_comment(self):
        text = 'def f():\n    """"""\n    pass'
        self.view.run_command("insert", {"characters": text})

        buffer_text = self.view.substr(sublime.Region(0, self.view.size()))
        empty_string = buffer_text.index('""""""')
        expected = empty_string + 3

        self.view.sel().clear()
        self.view.sel().add(sublime.Region(0, 0))
        self.view.run_command("jumper_select_selector", _comment_args)
        self.assertEqual(self.view.sel()[0].to_tuple(), (expected, expected))

        self.view.sel().clear()
        self.view.sel().add(sublime.Region(self.view.size(), self.view.size()))
        self.view.run_command(
            "jumper_select_selector",
            {**_comment_args, "direction": "previous"},
        )
        self.assertEqual(self.view.sel()[0].to_tuple(), (expected, expected))

    def test_select_empty_triple_quoted_string(self):
        text = 'value = """"""'
        self.view.run_command("insert", {"characters": text})

        expected = text.index('""""""') + 3
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(0, 0))
        self.view.run_command("jumper_select_selector")

        self.assertEqual(self.view.sel()[0].to_tuple(), (expected, expected))

    def test_string_boundary_punctuation_is_trimmed(self):
        text = 'value = " hello! "'
        self.view.run_command("insert", {"characters": text})

        expected = text.index('"') + 1
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(0, 0))
        self.view.run_command("jumper_select_selector")

        self.assertEqual(
            self.view.sel()[0].to_tuple(),
            (expected, expected + len(" hello! ")),
        )

    def test_navigate_nested_f_strings(self):
        text = 'f"aaaa{\'test1\'}bbb{\'test2\'}ccc{\'test3\'}"'
        self.view.run_command("insert", {"characters": text})

        outer = (text.index('"') + 1, text.rindex('"'))
        first_start = text.index("'test1'") + 1
        second_start = text.index("'test2'") + 1
        third_start = text.index("'test3'") + 1
        first = (first_start, first_start + len("test1"))
        second = (second_start, second_start + len("test2"))
        third = (third_start, third_start + len("test3"))
        outer_text = text[outer[0] : outer[1]]

        self.view.sel().clear()
        self.view.sel().add(sublime.Region(0, 0))

        expected_right = [
            (outer, outer_text),
            (first, "test1"),
            (second, "test2"),
            (third, "test3"),
        ]
        for expected_region, expected_text in expected_right:
            self.view.run_command("jumper_select_selector")
            self._assert_selection(expected_region, expected_text)

        expected_left = [
            (second, "test2"),
            (first, "test1"),
            (outer, outer_text),
            (outer, outer_text),
        ]
        for expected_region, expected_text in expected_left:
            self.view.run_command(
                "jumper_select_selector",
                {"direction": "previous"},
            )
            self._assert_selection(expected_region, expected_text)

    def test_navigate_nested_javascript_template_strings(self):
        self.view.assign_syntax("JavaScript.sublime-syntax")
        text = '`test${\'test1\'}test${"test2" + "test3"}`'
        self.view.run_command("insert", {"characters": text})

        outer = (text.index("`") + 1, text.rindex("`"))
        first_start = text.index("'test1'") + 1
        second_start = text.index('"test2"') + 1
        third_start = text.index('"test3"') + 1
        first = (first_start, first_start + len("test1"))
        second = (second_start, second_start + len("test2"))
        third = (third_start, third_start + len("test3"))
        outer_text = text[outer[0] : outer[1]]

        self.view.sel().clear()
        self.view.sel().add(sublime.Region(0, 0))

        expected_right = [
            (outer, outer_text),
            (first, "test1"),
            (second, "test2"),
            (third, "test3"),
        ]
        for expected_region, expected_text in expected_right:
            self.view.run_command("jumper_select_selector")
            self._assert_selection(expected_region, expected_text)

        expected_left = [
            (second, "test2"),
            (first, "test1"),
            (outer, outer_text),
            (outer, outer_text),
        ]
        for expected_region, expected_text in expected_left:
            self.view.run_command(
                "jumper_select_selector",
                {"direction": "previous"},
            )
            self._assert_selection(expected_region, expected_text)

    def test_trim_comment_punctuation_and_whitespace(self):
        text = 'def f():\n    """ hello! """'
        self.view.run_command("insert", {"characters": text})
        yield 25  # Wait for syntax highlighting.

        buffer_text = self.view.substr(sublime.Region(0, self.view.size()))
        expected = buffer_text.index("hello!")
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(0, 0))
        self.view.run_command("jumper_select_selector", _comment_args)

        self.assertEqual(
            self.view.sel()[0].to_tuple(),
            (expected, expected + len("hello!")),
        )

    def test_select_empty_line_comment_at_eof(self):
        self.view.run_command("insert", {"characters": "#"})

        self.view.sel().clear()
        self.view.sel().add(sublime.Region(0, 0))
        self.view.run_command("jumper_select_selector", _comment_args)

        self.assertEqual(self.view.sel()[0].to_tuple(), (1, 1))
