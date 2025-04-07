import re
from itertools import chain

import sublime
import sublime_plugin


def get_word_separators(view):
    word_separators = view.settings().get("word_separators")
    return word_separators or "./\\()\"'-:,.;<>~!@#$%^&*|+=[]{}`~?"


class JumperQuickScopeCommand(sublime_plugin.TextCommand):
    """Go to the character."""

    def run(self, edit, character, extend=False):
        regions = _quick_scope_get_labels(self.view)

        if character in regions:
            region = regions[character]
            selection = self.view.sel()[0]
            self.view.sel().clear()
            if not extend:
                self.view.sel().add(sublime.Region(region.a, region.a))
            else:
                a, b = sorted(selection.to_tuple())

                if a < region.a:
                    # Select until the end of the word
                    end = (
                        self.view.word(region.a).b
                        if self.view.substr(sublime.Region(region.a, region.a + 1))
                        not in get_word_separators(self.view)
                        else region.b
                    )
                    self.view.sel().add(sublime.Region(a, end))
                else:
                    self.view.sel().add(sublime.Region(b, region.a))


class SelectionShowQuickScopeWordListener(sublime_plugin.EventListener):
    """Add a line bellow the characters for which we can do a quick scope."""

    def on_activated_async(self, view):
        self.on_selection_modified_async(view)

    def on_deactivated(self, view):
        view.add_regions("jumper_quick_scope", [])

    def on_selection_modified_async(self, view):
        if not view.settings().get("jumper_quick_scope"):
            return

        view.add_regions(
            "jumper_quick_scope",
            list(_quick_scope_get_labels(view).values()),
            scope="white",
            flags=1024 | 32 | 256,
        )


def _quick_scope_get_labels(view):
    if len(view.sel()) != 1:
        return {}

    target = view.settings().get("jumper_quick_scope")

    a, b = sorted(view.sel()[0].to_tuple())
    visible_region = (
        view.line(view.sel()[0]) if target == "line" else view.visible_region()
    )

    word_bounds = re.escape(get_word_separators(view))

    search_re = f"((?<=[{word_bounds}\\s\\n])[^{word_bounds}\\s\\n])|[{word_bounds}]"
    result = view.find_all(search_re, within=visible_region)
    result = sorted(result, key=lambda r: abs(r.a - a))

    regions = {}
    done = set()
    for r in result:
        if view.sel()[0] in r:
            # Do not highlight the current cursor position
            continue
        # TODO: single quote and double quote should be the same
        s = view.substr(r)

        for c in s:
            if c not in done:
                break
        else:
            # Can not find a label
            # TODO: better algorithm
            continue

        done.add(c)
        regions[c] = r

    return regions
