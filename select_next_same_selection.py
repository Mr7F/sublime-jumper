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

        sel = SelectNextSameSelectionListener.get_main_cursors(view)
        print('sel', sel)
        if sel is None:
            _selection_mode[view] = "text"  # Cursor moved
            sel = list(view.sel())

        if all(s.a == s.b for s in sel):
            _selection_mode[view] = "word"
            view.run_command(
                "multi_cursor_add",
                {"cursors": [view.word(s.a).to_tuple() for s in sel], "scope": "region.cyanish"},
            )
            return


        flags = sublime.WRAP
        color = "region.greenish"
        if direction != "next":
            flags |= sublime.REVERSE
        if _selection_mode.get(view, "text") == "word":
            flags |= sublime.WHOLEWORD
            color = "region.cyanish"
        else:
            flags |= sublime.LITERAL

        result = []
        for s in sel:
            r = view.find(
                view.substr(s),
                s.end() if direction == "next" else s.begin(),
                flags,
            )
            if r:
                result.append(r)

        if not result:
            return
        if not keep_selection:
            for s in sel:
                view.sel().subtract(s)

        view.run_command(
            "multi_cursor_add",
            {"cursors": [r.to_tuple() for r in result], "scope": color},
        )
