import sublime
import sublime_plugin


class SelectNextSameSelection(sublime_plugin.TextCommand):
    def run(self, edit, direction="next", keep_selection=False):
        sel = max(self.view.sel()) if direction == "next" else min(self.view.sel())
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

        self.view.sel().add(result)
        self.view.show(result)
