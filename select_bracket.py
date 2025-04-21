import sublime
import sublime_plugin

from .utils import select_next_region


class JumperSelectNextBracketCommand(sublime_plugin.TextCommand):
    """Select the next / previous bracket / parenthesis content."""

    def run(self, edit, direction="next", extend=False, brackets_text="[({})]"):
        assert len(brackets_text) % 2 == 0
        opening_bracket = brackets_text[: len(brackets_text) // 2]
        _closing_bracket = brackets_text[len(brackets_text) // 2 :]

        _brackets = self.view.find_by_selector("punctuation.section | punctuation.definition")
        brackets = []
        for bracket in _brackets:
            a, b = bracket.to_tuple()
            for i in range(a, b):
                new_region = sublime.Region(i, i + 1)
                if self.view.substr(new_region) in brackets_text:
                    brackets.append(new_region)

        if not brackets:
            return

        # Create regions for content
        brackets = sorted(brackets, key=lambda s: s.a)
        i = next(
            i for i, b in enumerate(brackets) if self.view.substr(b) in opening_bracket
        )
        brackets = brackets[i:]  # Force starting with opening bracket

        pairs = []
        stack = []
        for bracket in brackets:
            if self.view.substr(bracket) in opening_bracket:
                stack.append(bracket)
            else:
                pairs.append((stack.pop(), bracket))

        regions = [sublime.Region(a.b, b.a) for a, b in pairs]
        select_next_region(self.view, regions, direction, extend)
