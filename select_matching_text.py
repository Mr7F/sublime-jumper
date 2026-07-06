import re

import sublime
import sublime_plugin


from .selection_frontier import (
    get_frontier_revision,
    get_frontier,
)
from .utils import apply_selection_targets, selection_mode_adds


_MATCH_MODE = "jumper_matching_text_match_mode"
_MATCH_FRONTIER_REVISION = "jumper_matching_text_frontier_revision"


def _get_match_mode(view):
    return view.settings().get(_MATCH_MODE, "text")


def _set_match_mode(view, mode):
    view.settings().set(_MATCH_MODE, mode)


def _owns_frontier(view):
    revision = view.settings().get(_MATCH_FRONTIER_REVISION, -1)
    return revision == get_frontier_revision(view)


def _remember_frontier(view):
    view.settings().set(_MATCH_FRONTIER_REVISION, get_frontier_revision(view))


class JumperSelectMatchingTextCommand(sublime_plugin.TextCommand):
    def run(self, edit, direction="next", mode="replace"):
        selection_mode_adds(mode)

        view = self.view
        if view.element():
            # The focus is in the search bar
            view = view.window().active_view()

        sel = get_frontier(view)
        if sel is None or not _owns_frontier(view):
            _set_match_mode(view, "text")  # Cursor moved or another command ran
        if sel is None:
            sel = list(view.sel())

        if all(s.a == s.b for s in sel):
            _set_match_mode(view, "word")
            changed = apply_selection_targets(
                view,
                sel,
                [view.word(s.a) for s in sel],
                mode="replace",
                scope="region.cyanish",
            )
            if changed:
                _remember_frontier(view)
            return

        flags = sublime.WRAP
        color = "region.greenish"
        if direction != "next":
            flags |= sublime.REVERSE
        word_mode = _get_match_mode(view) == "word"
        if word_mode:
            flags |= sublime.WHOLEWORD
            color = "region.cyanish"
        else:
            flags |= sublime.LITERAL

        result = []
        for s in sel:
            pattern = view.substr(s)
            if word_mode:
                # WHOLEWORD is a regex search mode in some Sublime builds.
                # Escape the selected word instead of combining it with LITERAL.
                pattern = re.escape(pattern)
            r = view.find(
                pattern,
                s.end() if direction == "next" else s.begin(),
                flags,
            )
            if r:
                result.append(r)

        if not result:
            return
        changed = apply_selection_targets(
            view,
            sel,
            result,
            mode=mode,
            scope=color,
        )
        if changed:
            _remember_frontier(view)
