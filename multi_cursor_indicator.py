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
            and any(c not in self.view.sel() for c in _main_cursors[self.view])
        ):
            del _main_cursors[self.view]
            self.view.erase_regions("jumper-select-next-same-selection")

    @classmethod
    def get_main_cursors(cls, view):
        return _main_cursors.get(view)


class MultiCursorAddCommand(sublime_plugin.TextCommand):
    def run(self, edit, cursors, scope="region.greenish"):
        global _main_cursors

        cursors = [sublime.Region(*c) for c in cursors]
        _main_cursors[self.view] = cursors
        self.view.sel().add_all(cursors)
        self.view.show(cursors[0])

        self.view.window().run_command(
            # Add the new selection in the Jump Back / Next history
            # (if we execute the same command, it throttles it to 1 second)
            "add_jump_record",
            {"selection": [s.to_tuple() for s in self.view.sel()]},
        )

        if len(self.view.sel()) >= 1:
            print(cursors)
            self.view.add_regions(
                "jumper-select-next-same-selection",
                [sublime.Region(c.b - 1, c.b - 1) for c in cursors],
                scope=scope,
                icon="dot",
                flags=sublime.HIDE_ON_MINIMAP | 64,
            )
        else:
            self.view.erase_regions("jumper-select-next-same-selection")
