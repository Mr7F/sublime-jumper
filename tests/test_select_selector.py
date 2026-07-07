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

    def test_replace_advances_only_the_latest_added_selection(self):
        text = '"one" "two" "three"'
        self.view.run_command("insert", {"characters": text})

        self.view.sel().clear()
        self.view.sel().add(sublime.Region(0, 0))

        # Select the first target, retain the second, then replace only that
        # latest target with the third one.
        self.view.run_command("jumper_select_selector")
        self.view.run_command("jumper_select_selector", {"mode": "add"})
        self.view.run_command("jumper_select_selector")

        self.assertEqual(
            [self.view.substr(region) for region in self.view.sel()],
            ["one", "three"],
        )
        self.assertEqual(
            [
                self.view.substr(region)
                for region in self.view.get_regions(
                    "jumper-selection-frontier-indicators"
                )
            ],
            ["three"],
        )

    def test_add_moves_frontier_through_existing_selections(self):
        text = '"one" "two" "three"'
        self.view.run_command("insert", {"characters": text})

        self.view.sel().clear()
        self.view.sel().add(sublime.Region(0, 0))

        self.view.run_command("jumper_select_selector")
        self.view.run_command("jumper_select_selector", {"mode": "add"})
        self.view.run_command("jumper_select_selector", {"mode": "add"})

        # Moving backward with add keeps all selections and moves only the
        # frontier from `three` to the already-selected `two`.
        self.view.run_command(
            "jumper_select_selector",
            {"direction": "previous", "mode": "add"},
        )
        self.assertEqual(
            [self.view.substr(region) for region in self.view.sel()],
            ["one", "two", "three"],
        )
        self.assertEqual(
            [
                self.view.substr(region)
                for region in self.view.get_regions(
                    "jumper-selection-frontier-indicators"
                )
            ],
            ["two"],
        )

        # Replacing toward the next target removes only `two`; `three` was
        # already selected and simply becomes the new frontier.
        self.view.run_command("jumper_select_selector")
        self.assertEqual(
            [self.view.substr(region) for region in self.view.sel()],
            ["one", "three"],
        )

    def test_add_previous_visits_existing_selection_before_unselected_target(self):
        text = "'a' 'b' 'c' 'd'"
        self.view.run_command("insert", {"characters": text})

        def selected_text():
            return [self.view.substr(region) for region in self.view.sel()]

        def frontier_text():
            return [
                self.view.substr(region)
                for region in self.view.get_regions("jumper-selection-frontier")
            ]

        # Start after `a`, select `b`, and add `c`.
        after_a = text.index("'a'") + len("'a'")
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(after_a))

        self.view.run_command("jumper_select_selector")
        self.assertEqual(selected_text(), ["b"])
        self.assertEqual(frontier_text(), ["b"])

        self.view.run_command("jumper_select_selector", {"mode": "add"})
        self.assertEqual(selected_text(), ["b", "c"])
        self.assertEqual(frontier_text(), ["c"])

        # `b` is already selected, but it must still be the immediate previous
        # target. The unselected `a` must not be reached yet.
        self.view.run_command(
            "jumper_select_selector",
            {"direction": "previous", "mode": "add"},
        )
        self.assertEqual(selected_text(), ["b", "c"])
        self.assertEqual(frontier_text(), ["b"])

    def test_native_arrow_movement_clears_frontier(self):
        text = '"one" "two"'
        self.view.run_command("insert", {"characters": text})

        self.view.sel().clear()
        self.view.sel().add(sublime.Region(0))
        self.view.run_command("jumper_select_selector")

        self.assertTrue(self.view.get_regions("jumper-selection-frontier"))
        self.assertTrue(self.view.get_regions("jumper-selection-frontier-indicators"))

        # This is the command Sublime runs for a right-arrow key press.
        self.view.run_command(
            "move",
            {"by": "characters", "forward": True},
        )

        self.assertEqual(
            self.view.get_regions("jumper-selection-frontier"),
            [],
        )
        self.assertEqual(
            self.view.get_regions("jumper-selection-frontier-indicators"),
            [],
        )

    def test_navigate_nested_f_strings(self):
        text = "f\"aaaa{'test1'}bbb{'test2'}ccc{'test3'}\""
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
            (outer, outer_text),
        ]
        for expected_region, expected_text in expected_right:
            self.view.run_command("jumper_select_selector")
            self._assert_selection(expected_region, expected_text)

        expected_left = [
            (third, "test3"),
            (second, "test2"),
            (first, "test1"),
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
            (outer, outer_text),
        ]
        for expected_region, expected_text in expected_right:
            self.view.run_command("jumper_select_selector")
            self._assert_selection(expected_region, expected_text)

        expected_left = [
            (third, "test3"),
            (second, "test2"),
            (first, "test1"),
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

    def test_multi_cursors(self):
        text = 'def f():\n    a = """ hello! """  # comment\n    "test" # comment 2'
        self.view.run_command("insert", {"characters": text})

        self.view.sel().clear()
        self.view.sel().add_all([sublime.Region(12, 12), sublime.Region(32, 32)])
        sel = self.view.sel()
        self.assertEqual(len(sel), 2)

        # select next string
        self.view.run_command("jumper_select_selector")
        sel = self.view.sel()
        self.assertEqual(len(sel), 2)
        self.assertEqual(sel[0].to_tuple(), (24, 32))
        self.assertEqual(sel[1].to_tuple(), (60, 64))

        # select next comment
        self.view.run_command("jumper_select_selector", _comment_args)
        sel = self.view.sel()
        self.assertEqual(len(sel), 2)
        self.assertEqual(sel[0].to_tuple(), (39, 46))
        self.assertEqual(sel[1].to_tuple(), (68, 77))

        # select previous string
        self.view.run_command("jumper_select_selector", {"direction": "previous"})
        sel = self.view.sel()
        self.assertEqual(len(sel), 2)
        self.assertEqual(sel[0].to_tuple(), (24, 32))
        self.assertEqual(sel[1].to_tuple(), (60, 64))
