import sublime
import sublime_plugin

_main_cursors = {}  # {view: Region}


class SelectNextSameSelectionListener(sublime_plugin.ViewEventListener):
    """Show an indicator for the "main cursor" when they are many selections in the view.

    When we have many cursors, and we are moving with some commands,
    only one cursor might move. The purpose of this file is to show
    an indicator of the cursor that will get the modification.
    """

    def on_selection_modified(self):
        if (
            _main_cursors.get(self.view)
            and _main_cursors[self.view] not in self.view.sel()
        ):
            del _main_cursors[self.view]
            self.view.erase_regions("jumper-select-next-same-selection")

    @classmethod
    def get_main_cursor(cls, view):
        return _main_cursors.get(view)


class MultiCursorAddCommand(sublime_plugin.TextCommand):
    def run(self, edit, cursor, scope="region.greenish"):
        global _main_cursors

        cursor = sublime.Region(*cursor)
        _main_cursors[self.view] = cursor
        self.view.sel().add(cursor)
        self.view.show(cursor)

        if len(self.view.sel()) >= 1:
            self.view.add_regions(
                "jumper-select-next-same-selection",
                [sublime.Region(cursor.b - 1, cursor.b - 1)],
                scope=scope,
                icon="dot",
                flags=sublime.HIDE_ON_MINIMAP | 64,
            )
        else:
            self.view.erase_regions("jumper-select-next-same-selection")
