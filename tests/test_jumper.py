import importlib

import sublime
from unittesting import DeferrableTestCase

_package = __package__.split(".")[0] if __package__ else "sublime-jumper"
jumper = importlib.import_module(_package + ".jumper")

_line = "This is a Test can you Type a char?"


class TestDeferrable(DeferrableTestCase):
    def setUp(self):
        self.view = sublime.active_window().new_file()
        self.view.set_scratch(True)
        self.view.run_command("insert", {"characters": _line})

    def tearDown(self):
        window = self.view.window()
        command = jumper.active_jumper_by_window.get(window.id())
        if command is not None:
            command.on_cancel()
        window.run_command("show_panel", {"panel": "output.UnitTesting"})
        self.view.close()

    def _run_jumper(self, regex, extend=False, current_line=True):
        self.view.window().focus_view(self.view)
        self.view.run_command(
            "jumper",
            {"regex": regex, "extend": extend, "current_line": current_line},
        )
        return jumper.active_jumper_by_window[self.view.window().id()]

    def test_jump(self):
        self.assertEqual(self.view.sel()[0].to_tuple(), (35, 35))

        command = self._run_jumper("Test")
        labels = command.positions[self.view]

        # A single match with a unique first letter is labelled by it
        self.assertEqual(list(labels), ["t"])
        self.assertEqual(labels["t"].region.to_tuple(), (10, 14))

        # Jump to the beginning of "Test"
        command.on_change("t")
        self.assertEqual(len(self.view.sel()), 1)
        self.assertEqual(self.view.sel()[0].to_tuple(), (10, 10))

        # The input panel view is reused by other panels (eg rename file),
        # the keybindings must not stay active there
        self.assertFalse(command.input_view.settings().get("jumper_input"))

    def test_select_included(self):
        # Select until "you" included
        command = self._run_jumper("you", extend=2)
        command.on_change("y")
        self.assertEqual(len(self.view.sel()), 1)
        self.assertEqual(self.view.sel()[0].to_tuple(), (35, 19))

    def test_select_excluded(self):
        # Select until "you" excluded
        command = self._run_jumper("you", extend=1)
        command.on_change("y")
        self.assertEqual(len(self.view.sel()), 1)
        self.assertEqual(self.view.sel()[0].to_tuple(), (35, 22))

    def test_add_cursor(self):
        # Add a new cursor at "Test", keeping the current one
        command = self._run_jumper("Test", extend=3)
        command.on_change("t")
        self.assertEqual(
            [s.to_tuple() for s in self.view.sel()],
            [(10, 10), (35, 35)],
        )

    def test_extend_not_cross_view(self):
        window = self.view.window()
        original_layout = window.layout()
        window.set_layout(
            {
                "cols": [0.0, 0.5, 1.0],
                "rows": [0.0, 1.0],
                "cells": [[0, 0, 1, 1], [1, 0, 2, 1]],
            }
        )
        other = window.new_file()
        other.set_scratch(True)
        window.set_view_index(other, 1, 0)
        other.run_command("insert", {"characters": "Nothing to see"})

        try:
            # The current-line mode only labels the current view
            command = self._run_jumper("see|you")
            self.assertEqual(list(command.positions[self.view]), ["y"])
            self.assertNotIn(other, command.positions)
            command.on_cancel()

            # One match in each view
            command = self._run_jumper("see|you", current_line=False)
            self.assertEqual(list(command.positions[self.view]), ["y"])
            self.assertEqual(list(command.positions[other]), ["s"])

            # Enable the "select until included" mode
            command.input_view.run_command("jumper_input_set_mode", {"extend": 2})

            # The label of the other view cannot be used anymore
            command.on_change("s")
            self.assertFalse(command.exit)
            self.assertEqual(other.sel()[0].to_tuple(), (14, 14))

            # But the label of the current view still selects
            command.on_change("y")
            self.assertEqual(len(self.view.sel()), 1)
            self.assertEqual(self.view.sel()[0].to_tuple(), (35, 19))
        finally:
            other.close()
            window.set_layout(original_layout)

    def test_prefix_free_labels(self):
        # "This", "Test" and "Type" share the same first letter
        command = self._run_jumper(r"T\w+")
        labels = command.positions[self.view]

        self.assertEqual(
            sorted(label.region.to_tuple() for label in labels.values()),
            [(0, 4), (10, 14), (23, 27)],
        )

        for label in labels:
            self.assertTrue(label.startswith("t"))

        # No label is the prefix of another one
        for label in labels:
            for other in labels:
                if label != other:
                    self.assertFalse(other.startswith(label))

        # The labels are still usable to jump
        label = next(
            c for c, target in labels.items() if target.region.to_tuple() == (0, 4)
        )
        command.on_change(label)
        self.assertEqual(len(self.view.sel()), 1)
        self.assertEqual(self.view.sel()[0].to_tuple(), (0, 0))

    def test_visible_label_for(self):
        """Test that the label displayed and the number of borders are correct."""
        _label_for = jumper.SelectCharSelectionAddLabelsCommand.visible_label_for

        # simple case, the label has the same size of the label
        self.assertEqual(_label_for("1234", "", len("abcd")), ("1234", 0, 0))
        self.assertEqual(_label_for("1234", "1", len("abcd")), ("1234", 0, 1))
        self.assertEqual(_label_for("1234", "12", len("abcd")), ("1234", 0, 2))
        self.assertEqual(_label_for("1234", "123", len("abcd")), ("1234", 0, 3))
        self.assertEqual(_label_for("1234", "1234", len("abcd")), ("1234", 0, None))

        # simple case, the label has less char than the label
        self.assertEqual(_label_for("12", "", len("abcd")), ("12", 0, 0))
        self.assertEqual(_label_for("12", "1", len("abcd")), ("12", 0, 1))
        self.assertEqual(_label_for("12", "12", len("abcd")), ("12", 0, None))
        self.assertEqual(_label_for("12", "123", len("abcd")), ("12", 0, None))
        self.assertEqual(_label_for("12", "1234", len("abcd")), ("12", 0, None))

        # hard case, the label has more chars than the word
        # should scroll through the label
        self.assertEqual(_label_for("1234", "", len("a")), ("1", 3, 0))
        self.assertEqual(_label_for("1234", "1", len("a")), ("2", 2, 0))
        self.assertEqual(_label_for("1234", "12", len("a")), ("3", 1, 0))
        self.assertEqual(_label_for("1234", "123", len("a")), ("4", 0, 0))
        self.assertEqual(_label_for("1234", "1234", len("a")), ("4", 0, None))

        self.assertEqual(_label_for("1234", "", len("ab")), ("12", 2, 0))
        self.assertEqual(_label_for("1234", "1", len("ab")), ("23", 1, 0))
        self.assertEqual(_label_for("1234", "12", len("ab")), ("34", 0, 0))
        self.assertEqual(_label_for("1234", "123", len("ab")), ("34", 0, 1))
        self.assertEqual(_label_for("1234", "1234", len("ab")), ("34", 0, None))

        # no highlight when the typed input does not match the label
        self.assertEqual(_label_for("1234", "9", len("a")), ("1", 0, None))
        self.assertEqual(_label_for("1234", "19", len("a")), ("2", 0, None))
        self.assertEqual(_label_for("1234", "9", len("abcd")), ("1234", 0, None))
        self.assertEqual(_label_for("1234", "13", len("abcd")), ("1234", 0, None))
