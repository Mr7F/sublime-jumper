import sublime
import sublime_plugin


class SelectNextSameSelection(sublime_plugin.TextCommand):
    def run(self, edit, direction="next", keep_selection=False):
        to_show = None
        for sel in list(self.view.sel()):
            text = self.view.substr(sel)
            flags = sublime.LITERAL
            if direction != "next":
                flags |= sublime.REVERSE

            result = self.view.find(
                text, sel.end() if direction == "next" else sel.begin(), flags
            )
            if not result:
                continue
            if not keep_selection:
                self.view.sel().subtract(sel)

            self.view.sel().add(result)
            to_show = result

        if to_show:
            self.view.show(to_show)
