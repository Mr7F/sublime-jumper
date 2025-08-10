import sublime
import sublime_plugin


from .multi_cursor_indicator import SelectNextSameSelectionListener


class SelectNextSameSelection(sublime_plugin.TextCommand):
    def run(self, edit, direction="next", keep_selection=False):
        view = self.view
        if view.element():
            # The focus is in the search bar
            view = view.window().active_view()

        sel = SelectNextSameSelectionListener.get_main_cursor(view, direction == "next")

        if sel.a == sel.b:
            view.sel().add(view.word(sel))
            return

        text = view.substr(sel)
        flags = sublime.LITERAL | sublime.WRAP
        if direction != "next":
            flags |= sublime.REVERSE

        result = view.find(
            text,
            sel.end() if direction == "next" else sel.begin(),
            flags,
        )
        if not result:
            return
        if not keep_selection:
            view.sel().subtract(sel)

        SelectNextSameSelectionListener.skip_next = True
        view.sel().add(result)
        view.show(result)
        SelectNextSameSelectionListener.show_cursor(view, result)
