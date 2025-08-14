import sublime
import sublime_plugin


from .multi_cursor_indicator import SelectNextSameSelectionListener

_selection_mode = {}


class SelectNextSameSelection(sublime_plugin.TextCommand):
    def run(self, edit, direction="next", keep_selection=False):
        view = self.view
        if view.element():
            # The focus is in the search bar
            view = view.window().active_view()

        sel = SelectNextSameSelectionListener.get_main_cursor(view)
        if sel is None:
            _selection_mode[view] = "text"  # Cursor moved
            sel = max(view.sel()) if direction == "next" else min(view.sel())

        if sel.a == sel.b:
            _selection_mode[view] = "word"
            view.run_command(
                "multi_cursor_add",
                {"cursor": view.word(sel.a).to_tuple(), "scope": "region.cyanish"},
            )
            return

        text = view.substr(sel)
        flags = sublime.WRAP
        color = "region.greenish"
        if direction != "next":
            flags |= sublime.REVERSE
        if _selection_mode.get(view, "text") == "word":
            flags |= sublime.WHOLEWORD
            color = "region.cyanish"
        else:
            flags |= sublime.LITERAL

        result = view.find(
            text,
            sel.end() if direction == "next" else sel.begin(),
            flags,
        )
        if not result:
            return
        if not keep_selection:
            view.sel().subtract(sel)

        view.run_command(
            "multi_cursor_add",
            {"cursor": result.to_tuple(), "scope": color},
        )
