import sublime, sublime_plugin, re
from itertools import chain
import string


def _select_next(view, selection, direction, char, extend=False):
    a, b = sorted(selection.to_tuple())

    if char in "'\"":
        char = "'\""

    itr = (
        chain(range(b, view.size(), 1000), range(0, b, 1000))
        if direction == "next"
        else chain(range(a, 0, -1000), range(view.size(), a, -1000))
    )

    for idx in itr:
        if direction == "next":
            end_idx = min(idx + 1000, view.size())
        else:
            end_idx = max(idx - 1000, 0)

        file_content = view.substr(sublime.Region(idx, end_idx))
        if direction != "next":
            file_content = reversed(file_content)

        char_idx = next((i for i, c in enumerate(file_content) if c in char), None)
        if char_idx is None:
            continue

        if direction == "next":
            target_idx = idx + char_idx
        else:
            target_idx = idx - char_idx - 1

        view.sel().subtract(selection)
        end_target = target_idx + 1
        if extend:
            target_idx = min(target_idx, a)
            end_target = max(end_target, b)

        view.sel().add(sublime.Region(target_idx, end_target))
        break


class SelectNextCharCommand(sublime_plugin.TextCommand):
    """Go to the character and select it."""

    def run(self, edit, char, direction="next", extend=False):
        for selection in list(self.view.sel()):
            _select_next(self.view, selection, direction, char, extend)

        selections = self.view.sel()
        if len(selections) == 1:
            self.view.show(selections[0])


class SelectNextCharSelectionCommand(sublime_plugin.TextCommand):
    """Go to the next string matching the current selection and select it."""

    def run(self, edit, direction="next", keep_selection=False):
        for selection in list(self.view.sel()):
            a, b = sorted(selection.to_tuple())

            selection_text = self.view.substr(selection)
            if len(selection_text) == 1:
                _select_next(self.view, selection, direction, selection_text)
                if keep_selection:
                    self.view.sel().add(selection)
                continue

            itr = (
                chain(range(b, self.view.size(), 1000), range(0, b, 1000))
                if direction == "next"
                else chain(range(a, 0, -1000), range(self.view.size(), a, -1000))
            )

            for idx in itr:
                if direction == "next":
                    end_idx = min(idx + 1000, self.view.size())
                else:
                    end_idx = max(idx - 1000, 0)

                file_content = self.view.substr(sublime.Region(idx, end_idx))
                it = range(len(file_content))
                if direction != "next":
                    it = reversed(it)

                char_idx = next(
                    (
                        j
                        for j, i in enumerate(it)
                        if file_content[i : i + len(selection_text)] == selection_text
                    ),
                    None,
                )
                if char_idx is None:
                    continue

                if direction == "next":
                    target_idx = idx + char_idx
                else:
                    target_idx = idx - char_idx - 1

                if not keep_selection:
                    self.view.sel().subtract(selection)
                self.view.sel().add(
                    sublime.Region(target_idx, target_idx + len(selection_text))
                )
                break

        selections = list(self.view.sel())
        if len(selections) == 1:
            self.view.show(selections[0])
        if all(s.a == s.b for s in selections):
            self.view.run_command("find_under_expand")


phantom_sets = {}


class SelectCharSelectionCommand(sublime_plugin.TextCommand):
    """Highlight all the characters visible on the screen, with a letter for each, press that letter to jump to the position.

    Similar package:
    > https://github.com/jfcherng-sublime/ST-AceJump-Chinese
    """

    charset = string.ascii_letters + string.digits + "@%${}&!#[]':-\"/|;^_="

    def run(self, edit, char):
        self.view.window().show_input_panel(
            "Jump to", "", self.on_cancel, self.on_change, self.on_cancel
        )
        self.char = char
        self.edit = edit

        visible_region = self.view.visible_region()
        start_visible = visible_region.begin()
        start_cursor = self.view.sel()[0].begin()
        matches = self.view.find_all(self.char, sublime.LITERAL)

        # TODO: use `within=visible_region` instead
        # >>> print(self.view.find_all.__doc__)
        a, b = sorted(visible_region.to_tuple())
        matches = [m for m in matches if m.a >= a and m.b < b][: len(self.charset)]
        matches = [sublime.Region(m.a, m.b) for m in matches]

        self.positions = dict(zip(self.charset, matches))

        relative_cursor = max(start_cursor - start_visible, 0)
        self.matches = sorted(matches, key=lambda x: abs(x.begin() - relative_cursor))

        if self.view.id not in phantom_sets:
            phantom_sets[self.view.id] = sublime.PhantomSet(self.view)

        phantoms = [
            sublime.Phantom(
                region,
                f"<span style='border: 1px solid #60b0f4; border-radius: 5px; padding: 0 2px; font-size: 15px'>{c}</span>",
                sublime.LAYOUT_INLINE,
            )
            for c, region in zip(self.charset, matches)
        ]

        phantom_sets[self.view.id].update(phantoms)

    def on_change(self, value):
        if not value:
            return

        if value in self.positions:
            self.view.sel().clear()
            self.view.sel().add(self.positions[value])

        self.on_cancel()

    def on_cancel(self, *args, **kwargs):
        phantom_sets[self.view.id].update([])
        self.view.window().run_command("hide_panel", {"cancel": True})
