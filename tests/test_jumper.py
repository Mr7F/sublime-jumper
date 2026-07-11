import importlib

import sublime
from unittesting import DeferrableTestCase

_package = __package__.split(".")[0] if __package__ else "sublime-jumper"
jumper = importlib.import_module(_package + ".jumper")

_line = "This is a Test can you Type a char?"

# Charset from Jumper.sublime-settings: "ntesiroamglpufywjbhd,cxkv:z".
# A character that can continue the search of a match is never used as a
# label, so the labelled matches get the first chars that remain available.


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

    def _labels(self, command, view=None):
        return {
            label: region.to_tuple()
            for label, region in command.positions[view or self.view].items()
        }

    def test_jump(self):
        self.assertEqual(self.view.sel()[0].to_tuple(), (35, 35))

        command = self._run_jumper("Test")

        # A single match: its first letter is already its jump char
        self.assertEqual(self._labels(command), {})
        self.assertEqual(command.narrowed[self.view], [(10, 14, "t", 0)])

        # "t" narrows down to the only match, which jumps immediately
        command.on_change("t")
        self.assertEqual(len(self.view.sel()), 1)
        self.assertEqual(self.view.sel()[0].to_tuple(), (10, 10))

        # The input panel view is reused by other panels (eg rename file),
        # the keybindings must not stay active there
        self.assertFalse(command.input_view.settings().get("jumper_input"))

    def test_labels_shown_immediately(self):
        # "This", "Test" and "Type" sorted by distance to the cursor:
        # "Type" (23), "Test" (10), "This" (0). Only their shared first
        # letter "t" is excluded, the other charset chars label them, shown
        # after the first letter (gap of 1)
        command = self._run_jumper(r"T\w+")
        self.assertEqual(
            self._labels(command),
            {"n": (23, 27), "e": (10, 14), "s": (0, 4)},
        )
        self.assertEqual(
            command.narrowed[self.view],
            [(23, 27, "n", 1), (10, 14, "e", 1), (0, 4, "s", 1)],
        )

        # Typing a label jumps without any search
        command.on_change("n")
        self.assertEqual(len(self.view.sel()), 1)
        self.assertEqual(self.view.sel()[0].to_tuple(), (23, 23))

    def test_narrowing(self):
        # After "t" the next letter of each match is unique: it becomes the
        # jump char of its match, no label is needed
        command = self._run_jumper(r"T\w+")
        command.on_change("t")
        self.assertFalse(command.exit)
        self.assertEqual(self._labels(command), {})
        self.assertEqual(
            command.narrowed[self.view],
            [(23, 27, "y", 0), (10, 14, "e", 0), (0, 4, "h", 0)],
        )

        # Typing the jump char narrows down to one match and jumps
        command.on_change("ty")
        self.assertEqual(len(self.view.sel()), 1)
        self.assertEqual(self.view.sel()[0].to_tuple(), (23, 23))

    def test_search_matches_word_start(self):
        # "i" is inside "This" but starts no match
        # (and is not one of the assigned labels)
        command = self._run_jumper(r"T\w+")
        command.on_change("i")
        self.assertFalse(command.exit)
        self.assertEqual(command.narrowed[self.view], [])

    def test_labels(self):
        # Identical matches cannot be told apart by typing: they get labels,
        # the closest match first, and narrowing on "a" keeps them
        command = self._run_jumper("a")
        labels = {"n": (32, 33), "t": (28, 29), "e": (16, 17), "s": (8, 9)}
        self.assertEqual(self._labels(command), labels)

        command.on_change("a")
        self.assertFalse(command.exit)
        self.assertEqual(self._labels(command), labels)

        # Typing the label jumps
        command.on_change("at")
        self.assertEqual(len(self.view.sel()), 1)
        self.assertEqual(self.view.sel()[0].to_tuple(), (28, 28))

    def test_backspace_restores_labels(self):
        command = self._run_jumper("a")
        labels = self._labels(command)

        command.on_change("a")
        # The narrowing is replayed, each match keeps its label
        command.on_change("")
        self.assertEqual(self._labels(command), labels)

    def test_labels_exhausted(self):
        self.view.run_command("select_all")
        self.view.run_command("insert", {"characters": "test " * 30})

        command = self._run_jumper("test")

        # 27 charset chars minus the continuation "t": 26 labels,
        # the other matches are only highlighted
        self.assertEqual(len(command.positions[self.view]), 26)
        self.assertEqual(len(command.narrowed[self.view]), 30)

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
            self.assertEqual(command.narrowed, {self.view: [(19, 22, "y", 0)]})
            self.assertNotIn(other, command.positions)
            command.on_cancel()

            # One match in each view, each with a unique first letter
            command = self._run_jumper("see|you", current_line=False)
            self.assertEqual(
                command.narrowed,
                {self.view: [(19, 22, "y", 0)], other: [(11, 14, "s", 0)]},
            )

            # Enable the "select until included" mode
            command.input_view.run_command("jumper_input_set_mode", {"extend": 2})

            # Only the other view matches "s": neither the autojump nor its
            # jump char can be used cross-view
            command.on_change("s")
            self.assertFalse(command.exit)
            self.assertEqual(command.narrowed[other], [(11, 14, "e", 0)])
            command.on_change("se")
            self.assertFalse(command.exit)
            self.assertEqual(other.sel()[0].to_tuple(), (14, 14))

            # But after a backspace the current view still selects
            command.on_change("")
            command.on_change("y")
            self.assertEqual(len(self.view.sel()), 1)
            self.assertEqual(self.view.sel()[0].to_tuple(), (35, 19))
        finally:
            other.close()
            window.set_layout(original_layout)
