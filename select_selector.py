import sublime
import sublime_plugin

_string_selector = "(meta.string - punctuation.definition.string.begin - punctuation.definition.string.end) | meta.interpolation"


class JumperSelectSelectorCommand(sublime_plugin.TextCommand):
    """Select the next / previous text matching the selector.

    > https://www.sublimetext.com/docs/scope_naming.html
    > https://www.sublimetext.com/docs/selectors.html
    """

    def run(self, edit, direction="next", selector=_string_selector, extend=False, trim=0):
        strings = self.view.find_by_selector(selector)

        if direction == "next":
            strings = sorted(strings, key=lambda s: s.b)
        else:
            strings = sorted(strings, key=lambda s: s.a)

        if trim:
            strings = [sublime.Region(s.a + trim, s.b - trim) for s in strings]

        to_show = None
        for sel in list(self.view.sel()):
            if direction == "next":
                target = next((string for string in strings if sel.b < string.b), None)
            else:
                target = next(
                    (string for string in reversed(strings) if sel.a > string.a), None
                )

            if target is not None:
                if not extend:
                    self.view.sel().subtract(sel)
                self.view.sel().add(target)
                to_show = target

        if to_show:
            self.view.show(to_show)
