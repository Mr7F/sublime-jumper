import sublime, sublime_plugin
from itertools import chain
from collections import defaultdict
import string
import html
from .utils import get_element_html_positions

ALLOW_N_CHARS_LABEL = True
LABEL_MODE = "popup"
assert LABEL_MODE in ("phantoms", "popup", "buffer")
assert not ALLOW_N_CHARS_LABEL or LABEL_MODE != "phantoms"
syntax_per_view = {}
phantom_sets = {}


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
    sublime_plugin.TextCommand,
    sublime_plugin.WindowCommand,
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

        self.char = char

        self.view.window().show_input_panel(
            "Jump to",
            "",
            self.on_cancel,
            self.on_change,
            self.on_cancel,
        )
        self.edit = edit
        self.extend = extend
        self.charset = list(
            self.view.settings().get("select_next_char_charset") or self.CHARSET
        )

        # Show many jump characters if needed
        self.jump_next_c = self.charset[15]
        if ALLOW_N_CHARS_LABEL:
            self.charset = self.charset[:15] + self.charset[16:]
            base_charset = self.charset.copy()
            for i in range(1, 5):
                self.charset.extend([i * self.jump_next_c + c for c in base_charset])

            assert len(set(self.charset)) == len(self.charset)

        self.exit = False
        self._find_match_views(char)

    def _find_match(self, char, view, charset) -> "dict[str, sublime.Region]":
        visible_region = view.visible_region()
        start_cursor = (
            view.sel()[0].begin()
            if view.sel()
            else (visible_region.a + visible_region.b) // 2
        )
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
        return dict(zip(charset, matches))

    def _find_match_views(self, char, search=""):
        """Find the matching chars in all active view and add labels."""
        self.positions = {}
        done = 0
        for view in self._active_views:
            positions = self._find_match(char, view, self.charset[done:])
            done += len(positions)
            self.positions.update(
                {c: (region, view) for c, region in positions.items()}
            )

        self._show_labels(search)

    def _show_labels(self, search=""):
        for view, values in self._positions_per_view.items():
            view.run_command(
                "select_char_selection_add_labels",
                {
                    "positions": [(c, m.a, m.b) for c, m in values],
                    "search": search,
                },
            )

    @property
    def _active_views(self):
        views = [
            self.view.window().active_view_in_group(group)
            for group in range(self.view.window().num_groups())
        ]
        return sorted(views, key=lambda v: v != self.view)

    @property
    def _positions_per_view(self):
        res = defaultdict(list)
        for c, (region, view) in self.positions.items():
            res[view].append((c, region))
        return res

    def on_change(self, value):
        if value in self.positions or not ALLOW_N_CHARS_LABEL:
            self.on_cancel()

        if value in self.positions:
            if not self.extend:
                for view in self._active_views:
                    view.sel().clear()

            to_jump = sublime.Region(
                self.positions[value][0].a,
                self.positions[value][0].a,
            )
            self.positions[value][1].sel().add(to_jump)
            self.positions[value][1].show(to_jump)
            self.view.window().focus_view(self.positions[value][1])

        elif ALLOW_N_CHARS_LABEL:
            # Update color of phantom
            self._show_labels(value)

    def on_cancel(self, *args, **kwargs):
        if self.exit:
            return
        self.exit = True

        self.view.window().run_command("hide_panel", {"cancel": True})
        for view in self._active_views:
            view.run_command("select_char_selection_remove_labels")
            if view.id() in syntax_per_view:
                view.set_syntax_file(syntax_per_view[view.id()])


class SelectCharSelectionAddLabelsCommand(sublime_plugin.TextCommand):
    """Do those modifications in a command, to easily undo it once we are done."""

    def run(self, edit, positions, search):
        if syntax_per_view.get(self.view.id(), "").endswith("GoToChar.tmLanguage"):
            syntax_per_view[self.view.id()] = self.view.syntax()
            self.view.set_syntax_file(
                "Packages/sublime-select-next-char/GoToChar.tmLanguage"
            )

        if LABEL_MODE == "phantoms":
            if self.view.id() not in phantom_sets:
                phantom_sets[self.view.id()] = sublime.PhantomSet(self.view)

            positions = sorted(positions, key=lambda x: x[1], reverse=True)

            phantoms = []
            for i, (c, a, b) in enumerate(positions):
                color = "#c778dd" if c.startswith(search) else "#abb2bf"
                phantoms.append(
                    sublime.Phantom(
                        sublime.Region(a, b),
                        "".join(
                            f"""<span style='color: #abb2bf'>{a}</span>"""
                            for a in c[: len(search)]
                        )
                        + "".join(
                            f"""<span style='color: {color}'>{a}</span>"""
                            for a in c[len(search) :]
                        ),
                        sublime.LAYOUT_INLINE,
                    ),
                )

            phantom_sets[self.view.id()].update(phantoms)

        elif LABEL_MODE == "popup":
            # text = html.escape(self.view.substr(self.view.visible_region()))
            # text = text.replace(" ", "&nbsp;").replace("\n", "<br/>&#8203;")

            visible_region = self.view.visible_region()

            text = self.view.export_to_html(visible_region, minihtml=True)

            line_padding_bottom = self.view.settings().get("line_padding_bottom", 0)
            line_padding_top = self.view.settings().get("line_padding_top", 0)
            line_height = (
                self.view.line_height() + line_padding_bottom + line_padding_top
            )

            offset_region = visible_region.a

            html_positions = get_element_html_positions(
                text,
                [p[1] - offset_region for p in positions],
            )

            positions = sorted(positions, key=lambda x: x[1], reverse=True)
            for i, (c, a, b) in enumerate(positions):
                html_position = html_positions.get(a - offset_region)
                if not html_position:
                    continue

                color = "#c778dd" if c.startswith(search) else "#abb2bf"
                label = c[len(search) : len(search) + 1] or c[-1]
                start, size = html_position
                text = (
                    text[:start]
                    + f"<span style='color: {color}; font-style: normal;'>{html.escape(label)}</span>"
                    + text[start + size :]
                )

            text = text.replace("<br>", "<br>&#8203;")

            self.view.show_popup(
                f"<style>html {{padding: -9px -10px}}</style><div style='background-color: var(--background); line-height: {line_height}px; padding: -{line_height + 12 - 10}px 10px; padding-right: 5000px'>{text}</div>",
                location=visible_region.a,
                max_width=10_000,
                max_height=10_000,
                flags=32,
                # on_hide=lambda: not self.view.is_popup_visible() and self.view.window().run_command("hide_panel", {"cancel": True}),
            )

        else:
            self.view.add_regions(
                "select_char_jump",
                [sublime.Region(a, b) for _, a, b in positions],
                "region.bluish",
                flags=sublime.DRAW_NO_FILL,
            )
            for c, a, b in positions:
                self.view.replace(edit, sublime.Region(a, b), c)


class SelectCharSelectionRemoveLabelsCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if LABEL_MODE == "phantoms":
            if self.view.id() in phantom_sets:
                phantom_sets[self.view.id()].update([])
        elif LABEL_MODE == "popup":
            self.view.hide_popup()
        else:
            # TODO: clean redo stack but not undo
            self.view.erase_regions("select_char_jump")
            self.view.end_edit(edit)
            self.view.run_command("undo")
