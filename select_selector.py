import sublime
import sublime_plugin

from .utils import select_next_region

_string_with_quote = "meta.string | string.quoted.double.json"
_string_selector = f"(({_string_with_quote}) - punctuation.definition.string.begin - punctuation.definition.string.end) | meta.interpolation"


class JumperSelectSelectorCommand(sublime_plugin.TextCommand):
    """Select the next / previous text matching the selector.

    > https://www.sublimetext.com/docs/scope_naming.html
    > https://www.sublimetext.com/docs/selectors.html
    """

    def run(self, edit, direction="next", selector=None, extend=False):
        if selector is None:
            strings = self.view.find_by_selector(_string_selector)

            # Find empty strings
            all_strings = self.view.find_by_selector(_string_with_quote)
            strings += [
                sublime.Region(r.a + 1, r.b - 1) for r in all_strings if len(r) == 2
            ]
            # Triple quote empty in python
            strings += [
                sublime.Region(r.a + 3, r.b - 3)
                for r in all_strings
                if len(r) == 6
                and self.view.match_selector(r.a, "meta.string.python")
                and self.view.substr(r) in ('"' * 6, "'" * 6)
            ]
        else:
            strings = self.view.find_by_selector(selector)

        select_next_region(self.view, strings, direction, extend)
