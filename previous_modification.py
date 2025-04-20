from binascii import b2a_base64
from collections import deque

import time

import sublime
import sublime_plugin


_history = []
_history_position = 0
_views_to_close = set()


class JumperPreviousModificationCommand(sublime_plugin.TextCommand):
    """Go to the previous / next modification.

    That command already exists in sublime text, but this one work across different files.

    TODO: option to navigate per file and not per line
    """

    def run(self, edit, direction="previous", per_file=False):
        global _history, _history_position, _views_to_close

        if _history_position >= len(_history):
            _history_position = len(_history) - 1
        if _history_position < -1:
            _history_position = -1

        while True:
            _history_position += 1 if direction == "previous" else -1
            if _history_position >= len(_history) or _history_position < 0:
                return

            position = _history[_history_position]

            if position.view == self.view and (
                per_file
                or position.line(self.view)
                in [self.view.line(s.a) for s in self.view.sel()]
            ):
                continue

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

                if position.view != view:
                    # Open a new view, close it if no modification
                    _views_to_close.add(view)

                    # Update history to match the new view / window
                    from_view = position.view
                    from_window = position.window
                    for h in _history:
                        if h.view == from_view and h.window == from_window:
                            h.view = view
                            h.window = window

                self._close_view_to_be_closed(view)

                if view.is_loading():
                    sublime.set_timeout_async(lambda: self._set_cursor(view, position))
                else:
                    self._set_cursor(view, position)
                return

            if position.view.window():
                # not saved file
                position.view.window().bring_to_front()
                self._close_view_to_be_closed(position.view)
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
            print("Can not find original position", position.position, region)
            region = position.position.a

        view.sel().clear()
        view.sel().add(region)
        view.show(region, animate=False)

    def _close_view_to_be_closed(self, except_view):
        global _views_to_close
        for view_to_close in _views_to_close.copy():
            if view_to_close != except_view:
                view_to_close.close()
                _views_to_close.remove(view_to_close)


class JumperPreviousModificationListener(sublime_plugin.ViewEventListener):
    def on_modified_async(self):
        global _history, _history_position, _views_to_close

        if self.view in _views_to_close:
            _views_to_close.remove(self.view)

        # If the previous history item is in the same line, keep the most recent one
        next_item = HistoryItem(self.view)
        _history = [
            h
            for h in _history
            if h.view != self.view or h.line(self.view) != next_item.line(self.view)
        ]

        _history.insert(0, next_item)
        _history_position = -1

        _history = _history[:1000]


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
