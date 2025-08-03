import sublime
import sublime_plugin


last_sel_per_view = {}
skip_next = False


class SelectNextSameSelection(sublime_plugin.TextCommand):
    def run(self, edit, direction="next", keep_selection=False):
        global last_sel_per_view, skip_next
        if not last_sel_per_view.get(self.view):
            last_sel_per_view[self.view] = (
                max(self.view.sel()) if direction == "next" else min(self.view.sel())
            )

        sel = last_sel_per_view[self.view]

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

        skip_next = True
        self.view.sel().add(result)
        self.view.show(result)
        last_sel_per_view[self.view] = result

        if len(self.view.sel()) > 1:
            self.view.add_regions(
                "jumper-select-next-same-selection",
                [sublime.Region(result.a, result.a)],
                icon="",
                scope="region.greenish",
                flags=sublime.DRAW_EMPTY_AS_OVERWRITE,
            )


class SelectNextSameSelectionListener(sublime_plugin.ViewEventListener):
    def on_selection_modified_async(self):
        global skip_next
        if skip_next:
            skip_next = False
            return

        last_sel_per_view[self.view] = None
        self.view.erase_regions("jumper-select-next-same-selection")
