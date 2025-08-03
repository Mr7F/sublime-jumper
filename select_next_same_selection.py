import sublime
import sublime_plugin


from .multi_cursor_indicator import SelectNextSameSelectionListener


class SelectNextSameSelection(sublime_plugin.TextCommand):
    def run(self, edit, direction="next", keep_selection=False):
        sel = SelectNextSameSelectionListener.get_main_cursor(
            self.view,
            direction == "next",
        )

        if sel.a == sel.b:
            self.view.sel().add(self.view.word(sel))
            return
        text = self.view.substr(sel)
        flags = sublime.LITERAL
        if direction != "next":
            flags |= sublime.REVERSE

        result = self.view.find(
            text, sel.end() if direction == "next" else sel.begin(), flags
        )
        if not result:
            return
        if not keep_selection:
            self.view.sel().subtract(sel)

        SelectNextSameSelectionListener.skip_next = True
        self.view.sel().add(result)
        self.view.show(result)
        SelectNextSameSelectionListener.show_cursor(self.view, result)
