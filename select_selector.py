import sublime
import sublime_plugin

from .utils import select_next_region

_string_selector = "((meta.string | string.quoted.double.json) - punctuation.definition.string.begin - punctuation.definition.string.end) | meta.interpolation"


class JumperSelectSelectorCommand(sublime_plugin.TextCommand):
    """Select the next / previous text matching the selector.

    > https://www.sublimetext.com/docs/scope_naming.html
    > https://www.sublimetext.com/docs/selectors.html
    """

    def run(self, edit, direction="next", selector=_string_selector, extend=False):
        strings = self.view.find_by_selector(selector)

        select_next_region(self.view, strings, direction, extend)
