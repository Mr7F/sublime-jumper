import os.path

import sublime
import sublime_plugin


_history = []
_history_position = 0
_views_to_close = set()
_cursor_queue = {}  # Will set the cursor at the given position when the view is loaded


def _set_cursor(view, position):
    """Set the cursor at the given position."""
    assert not view.is_loading()

    if view != view.window().active_view():
        view.window().focus_view(view)

    region = view.transform_region_from(position.position, position.change_id).a
    if region < 0:
        print("Can not find original position", position.position, region)
        region = position.position.a

    view.sel().clear()
    view.sel().add(region)
    view.show(region, animate=False)


class JumperPreviousModificationCommand(sublime_plugin.TextCommand):
    """Go to the previous / next modification.

    That command already exists in sublime text, but this one work across different files.
    """

    def run(self, edit, direction="previous", per_file=False):
        global _history, _history_position, _views_to_close, _cursor_queue

        if _history_position >= len(_history):
            _history_position = len(_history) - 1
        if _history_position < -1:
            _history_position = -1

        next_history_position = _history_position

        while True:
            next_history_position += 1 if direction == "previous" else -1
            if next_history_position >= len(_history) or next_history_position < 0:
                return

            position = _history[next_history_position]

            if position.view == self.view:
                if per_file or position.line(self.view) in [
                    self.view.line(s.a) for s in self.view.sel()
                ]:
                    continue

            if per_file and direction == "next":
                # show the latest modification in the file
                while (
                    next_history_position - 1 >= 0
                    and _history[next_history_position - 1].view
                    == _history[next_history_position].view
                ):
                    next_history_position -= 1
                position = _history[next_history_position]

            window = (
                position.window
                if position.window and position.window.is_valid()
                else self.view.window()
            )

            if position.file_name:
                if not os.path.isfile(position.file_name):
                    continue
                _history_position = next_history_position
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
                    _cursor_queue[view] = position
                else:
                    _set_cursor(view, position)
                return

            if position.view.window():
                # not saved file
                _history_position = next_history_position
                position.view.window().bring_to_front()
                self._close_view_to_be_closed(position.view)
                _set_cursor(position.view, position)
                return

    def _close_view_to_be_closed(self, except_view):
        global _views_to_close
        for view_to_close in _views_to_close.copy():
            if view_to_close != except_view:
                # view_to_close.set_scratch(True)
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

    def on_load(self):
        global _cursor_queue
        if self.view in _cursor_queue:
            _set_cursor(self.view, _cursor_queue[self.view])
            del _cursor_queue[self.view]


class HistoryItem:
    def __init__(self, view):
        # open_file
        self.view = view
        self.change_id = view.change_id()
        self.file_name = self.view.file_name()
        self.window = self.view.window()
        self.position = view.sel()[0]
        self.group = self.view.sheet().group()

    def region(self, view) -> int:
        region = view.transform_region_from(self.position, self.change_id).a
        return region if region >= 0 else self.position.a

    def line(self, view) -> int:
        return view.line(self.region(view))
