import sublime
import sublime_plugin

from .utils import select_next_region


class JumperSelectNextBracketCommand(sublime_plugin.TextCommand):
    """Select the next / previous bracket / parenthesis content."""

    def run(self, edit, direction="next", mode="replace", brackets_text="[({})]"):
        assert len(brackets_text) % 2 == 0
        opening_bracket = brackets_text[: len(brackets_text) // 2]
        closing_bracket = brackets_text[len(brackets_text) // 2 :]
        opening_for_closing = dict(zip(reversed(closing_bracket), opening_bracket))

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

        # Create regions for content. Ignore unmatched brackets: incomplete code is
        # expected while editing and must not make the command fail.
        brackets = sorted(brackets, key=lambda s: s.a)
        pairs = []
        stack = []
        for bracket in brackets:
            character = self.view.substr(bracket)
            if character in opening_bracket:
                stack.append((character, bracket))
            elif stack and stack[-1][0] == opening_for_closing.get(character):
                _, opening_region = stack.pop()
                pairs.append((opening_region, bracket))

        regions = [sublime.Region(a.b, b.a) for a, b in pairs]
        select_next_region(self.view, regions, direction, mode)
