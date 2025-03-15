import sublime, sublime_plugin
from itertools import chain
import string


def _select_next(view, selection, direction, char, extend=False):
    a, b = sorted(selection.to_tuple())

    if char in "'\"`":
        char = "'\"`"

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


class SelectNextCharSelectionCommand(
    sublime_plugin.TextCommand, sublime_plugin.WindowCommand
):
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
    > https://packagecontrol.io/packages/EasyMotion
    > https://github.com/ice9js/ace-jump-sublime
    > https://github.com/jfcherng-sublime/ST-AceJump-Chinese
    """

    CHARSET = string.ascii_letters + string.digits + "@%${}&!#[]':-\"/|;^_="

    def run(self, edit, char, extend=False):
        if char == "enter" and not extend:
            return

        self.multi_mode = char == "enter"
        self.multi_mode_char = None
        self.multi_mode_old_value = ""

        self.view.window().show_input_panel(
            "Jump to",
            "",
            self.on_cancel,
            self.on_change,
            self.on_cancel,
        )
        self.edit = edit
        self.extend = extend
        self.charset = (
            self.view.settings().get("select_next_char_charset") or self.CHARSET
        )
        if char != "enter":
            self._find_match_views(char)

    def _find_match(self, char, view, charset) -> "dict[str, sublime.Region]":
        visible_region = view.visible_region()
        start_cursor = (
            view.sel()[0].begin()
            if view.sel()
            else (visible_region.a + visible_region.b) // 2
        )
        print("start_cursor", start_cursor)
        if char == " ":
            matches = view.find_all(r"^\s*[^\s]")
            matches = [sublime.Region(m.b - 1, m.b - 1) for m in matches]
        elif char == "\t":
            matches = view.find_all(r"[^\s]$")
            matches = [sublime.Region(m.b, m.b) for m in matches]
        elif char in "'\"":
            # Find any quotes types
            matches = view.find_all(r"['\"`]")
        else:
            # TODO: use `within=visible_region` instead
            # >>> print(self.view.find_all.__doc__)
            matches = view.find_all(char, sublime.LITERAL)

        a, b = sorted(visible_region.to_tuple())
        matches = [m for m in matches if m.a >= a and m.b < b]
        matches = sorted(matches, key=lambda x: abs(x.begin() - start_cursor))
        matches = matches[: len(charset)]

        positions = dict(zip(charset, matches))

        if view.id() not in phantom_sets:
            phantom_sets[view.id()] = sublime.PhantomSet(view)

        # TODO: make it work in multi view
        # self.syntax = view.syntax()
        # view.set_syntax_file(
        #     "Packages/sublime-select-next-char/GoToChar.tmLanguage"
        # )

        phantoms = [
            sublime.Phantom(
                sublime.Region(region.a, region.b),
                f"<span style='color: #c778dd; border: 1px solid #c778dd; border-radius: 5px; padding: 0 2px; font-size: 15px'>{c}</span>",
                sublime.LAYOUT_INLINE,
            )
            for c, region in zip(charset, matches)
        ]
        phantom_sets[view.id()].update(phantoms)

        # for i, (m, c) in enumerate(sorted(zip(self.matches, self.charset), key=lambda x: x[0].b)):
        #     self.view.replace(edit, sublime.Region(m.a - i, m.b - i), "")
        return positions

    def _find_match_views(self, char):
        self.positions = {}
        done = 0
        print(self._active_views)
        for view in self._active_views:
            positions = self._find_match(char, view, self.charset[done:])
            done += len(positions)
            self.positions.update(
                {c: (region, view) for c, region in positions.items()}
            )

    @property
    def _active_views(self):
        views = [
            self.view.window().active_view_in_group(group)
            for group in range(self.view.window().num_groups())
        ]
        return sorted(views, key=lambda v: v != self.view)

    def on_change(self, value):
        if not value:
            return

        if self.multi_mode:
            v = value[-1:]
            if self.multi_mode_char is None:
                self.multi_mode_char = v
                self._find_match_views(v)
            elif v in self.positions:
                self.multi_mode_char = None
                for view in self._active_views:
                    phantom_sets[view.id()].update([])

                if not self.multi_mode_old_value.startswith(value) or len(
                    self.multi_mode_old_value
                ) <= len(value):
                    # If we didn't press backspace
                    self.positions[0].view.sel().add(self.positions[v][1])

            self.multi_mode_old_value = value

            return

        self.on_cancel()

        if not self.extend:
            for view in self._active_views:
                view.sel().clear()

        if value in self.positions:
            self.positions[value][1].sel().add(self.positions[value][0])

    def on_cancel(self, *args, **kwargs):
        for view in self._active_views:
            phantom_sets[view.id()].update([])

        self.view.window().run_command("hide_panel", {"cancel": True})
        # self.view.run_command("soft_undo")
        # self.view.set_syntax_file(self.syntax)
