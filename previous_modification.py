from binascii import b2a_base64
from collections import deque

import time

import sublime
import sublime_plugin


_history = []
_history_position = 0


class JumperPreviousModificationCommand(sublime_plugin.TextCommand):
    """Go to the previous / next modification.

    That command already exists in sublime text, but this one work across different files.

    TODO: option to navigate per file and not per line
    """

    def run(self, edit, direction="previous"):
        global _history, _history_position

        if _history_position >= len(_history):
            _history_position = len(_history) - 1
        if _history_position < 0:
            _history_position = 0

        print("_history_position", _history_position, len(_history))

        while True:
            _history_position += 1 if direction == "previous" else -1
            if _history_position >= len(_history) or _history_position < 0:
                return

            position = _history[_history_position]

            window = (
                position.window if position.window.is_valid() else self.view.window()
            )

            if position.file_name:
                window.bring_to_front()
                view = window.open_file(
                    position.file_name,
                    flags=sublime.FORCE_GROUP,
                    group=position.group,
                )
                if view.is_loading():
                    sublime.set_timeout_async(lambda: self._set_cursor(view, position))
                else:
                    self._set_cursor(view, position)
                return

            if position.window.is_valid():
                # not saved file
                window.bring_to_front()
                self._set_cursor(position.view, position)
                return

    def _set_cursor(self, view, position):
        for _ in range(1000):
            if not view.is_loading():
                break

            time.sleep(1 / 1000)

        if view != view.window().active_view():
            view.window().focus_view(view)

        region = view.transform_region_from(position.position, position.change_id).a
        if region < 0:
            region = position.position.a

        view.sel().clear()
        view.sel().add(region)
        view.show(region, animate=False)


class JumperPreviousModificationListener(sublime_plugin.ViewEventListener):
    def on_modified_async(self):
        global _history, _history_position

        # If we moved in the history, we need to clean it
        while (
            len(_history) >= _history_position and len(_history) and _history_position
        ):
            _history.pop()

        # If the previous history item is in the same line, keep the most recent one
        next_item = HistoryItem(self.view)
        _history = [
            h for h in _history if h.line(self.view) != next_item.line(self.view)
        ]

        _history.insert(0, next_item)
        _history_position = 0

        _history = _history[:1000]
        print(_history)


class HistoryItem:
    def __init__(self, view):
        # open_file
        self.view = view
        self.change_id = view.change_id()
        self.file_name = self.view.window().active_sheet().file_name()
        self.sheet = self.view.window().active_sheet()
        self.window = self.view.window()
        self.position = view.sel()[0]
        self.group = self.view.window().active_group()

    def region(self, view) -> int:
        region = view.transform_region_from(self.position, self.change_id).a
        return region if region >= 0 else self.position.a

    def line(self, view) -> int:
        return view.line(self.region(view))
