import sublime
import sublime_plugin

from .utils import select_next_region


_string_boundary_selector = (
    "punctuation.definition.string | punctuation.definition.raw"
)


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
        trim_selector=None,
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

            strings = raw_strings
            trim_selector = trim_selector or _string_boundary_selector

        else:
            strings = self.view.find_by_selector(selector)

        if trim_selector:
            strings = [
                _trim_region_by_selector(self.view, region, trim_selector)
                for region in strings
            ]

        if trim:
            strings = [_trim_whitespace(self.view, region) for region in strings]

        select_next_region(self.view, strings, direction, extend)


def _trim_region_by_selector(view, region, selector):
    """Trim matching boundary tokens, preserving matching tokens inside."""
    tokens = view.extract_tokens_with_scopes(region)
    content = [
        token_region.intersection(region)
        for token_region, scope in tokens
        if sublime.score_selector(scope, selector) == 0
    ]

    if content:
        return sublime.Region(content[0].begin(), content[-1].end())

    # All tokens were trimmed. Place the cursor after the opening token.
    point = min(tokens[0][0].end(), region.end()) if tokens else region.begin()
    return sublime.Region(point, point)


def _trim_whitespace(view, region):
    """Trim boundary whitespace, collapsing whitespace-only regions."""
    content = view.substr(region)
    left = len(content) - len(content.lstrip())
    right = len(content) - len(content.rstrip())

    begin = region.begin() + left
    end = region.end() - right
    if begin < end:
        return sublime.Region(begin, end)
    return sublime.Region(region.begin(), region.begin())
