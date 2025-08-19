import sublime
import sublime_plugin
from .utils import select_next_region


class JumperSelectSelectorCommand(sublime_plugin.TextCommand):
    """Select the next / previous text matching the selector.

    > https://www.sublimetext.com/docs/scope_naming.html
    > https://www.sublimetext.com/docs/selectors.html
    """

    def run(
        self,
        edit,
        direction="next",
        selector=None,
        extend=False,
        trim=False,
    ):
        if selector is None:
            raw_strings = self.view.find_by_selector(
                "meta.string | string.quoted | markup.raw.inline.markdown"
            )

            selector = "meta.string"
            for _ in range(5):
                # String inside template string
                selector += " meta.string"
                to_add = self.view.find_by_selector(selector)
                raw_strings += to_add
                if not to_add:
                    break

            # remove the quotes
            strings = []
            for region in raw_strings.copy():
                scopes = self.view.extract_tokens_with_scopes(region)
                scopes = [(r, s.strip().split(" ")[-1]) for r, s in scopes]
                start = next(
                    (
                        i
                        for i in range(len(scopes))
                        if "punctuation.definition.string.begin" not in scopes[i][1]
                        and "punctuation.definition.raw.begin.markdown"
                        not in scopes[i][1]
                    ),
                    None,
                )
                end = next(
                    (
                        i
                        for i in range(len(scopes) - 1, -1, -1)
                        if "punctuation.definition.string.end" not in scopes[i][1]
                        and "punctuation.definition.raw.end.markdown"
                        not in scopes[i][1]
                    ),
                    None,
                )
                if start is None or end is None:
                    continue

                r = [x for rr, _ in scopes[start : end + 1] for x in rr]
                if r:
                    strings.append(sublime.Region(min(r), max(r)))
                else:
                    # empty string, heuristic, take the middle of the string
                    mid = (region.a + region.b) // 2
                    strings.append(sublime.Region(mid, mid))

        else:
            strings = self.view.find_by_selector(selector)

        if trim:
            # Don't select starting / ending whitespace if any
            old_strings = strings
            strings = []
            for reg in old_strings:
                content = self.view.substr(reg)
                l = len(content) - len(content.lstrip())
                r = len(content) - len(content.rstrip())
                strings.append(sublime.Region(reg.a + l, reg.b - r) if r or l else reg)

        select_next_region(self.view, strings, direction, extend)
