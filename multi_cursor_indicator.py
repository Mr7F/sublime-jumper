import sublime
import sublime_plugin


class SelectNextSameSelectionListener(sublime_plugin.ViewEventListener):
    """Show an indicator for the "main cursor" when they are many selections in the view.

    When we have many cursors, and we are moving with some commands,
    only one cursor might move. The purpose of this file is to show
    an indicator of the cursor that will get the modification.
    """

    last_sel_per_view = {}
    skip_next = False

    def on_selection_modified_async(self):
        if SelectNextSameSelectionListener.skip_next:
            SelectNextSameSelectionListener.skip_next = False
            return

        SelectNextSameSelectionListener.last_sel_per_view[self.view] = None
        self.view.erase_regions("jumper-select-next-same-selection")

    @classmethod
    def show_cursor(cls, view, position):
        cls.last_sel_per_view[view] = position

        if len(view.sel()) > 1:
            view.add_regions(
                "jumper-select-next-same-selection",
                [sublime.Region(position.a, position.a)],
                icon="",
                scope="region.greenish",
                flags=sublime.DRAW_EMPTY_AS_OVERWRITE,
            )
        else:
            view.erase_regions("jumper-select-next-same-selection")

    @classmethod
    def get_main_cursor(cls, view, default_last):
        if not cls.last_sel_per_view.get(view):
            cls.last_sel_per_view[view] = (
                max(view.sel()) if default_last else min(view.sel())
            )
        return cls.last_sel_per_view[view]
