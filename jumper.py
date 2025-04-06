import html
import string
from collections import defaultdict


import sublime
import sublime_plugin

from .utils import get_element_html_positions

sheets_per_view = {}
active_view = {}
views = {}


class SelectCharSelectionCommand(sublime_plugin.TextCommand):
    """Highlight all the characters visible on the screen, with a letter for each, press that letter to jump to the position.

    Similar package:
    > https://packagecontrol.io/packages/EasyMotion
    > https://github.com/ice9js/ace-jump-sublime
    > https://github.com/jfcherng-sublime/ST-AceJump-Chinese
    """

    CHARSET = string.ascii_letters + string.digits + "@%${}&!#[]':-\"/|;^_="

    def run(self, edit, character, extend=False, is_regex=False):
        global views, sheets_per_view, active_view

        self.extend = int(extend)
        self.is_regex = is_regex

        views = {v: v.visible_region() for v in self._active_views if v is not None}
        active_view[self.view.window()] = self.view.window().active_view()

        for sheet in sheets_per_view.values():
            sheet.close()
        sheets_per_view = {}

        self.char = character

        self.edit = edit
        self.charset = list(
            self.view.settings().get("select_next_char_charset") or self.CHARSET
        )

        # Show many jump characters if needed
        self.jump_next_c = "."
        self.charset = [c for c in self.charset if c != "."]
        base_charset = self.charset.copy()
        for i in range(1, 5):
            self.charset.extend([i * self.jump_next_c + c for c in base_charset])

        assert len(set(self.charset)) == len(self.charset)

        self.exit = False
        self._find_match_views(character)

        self.view.window().show_input_panel(
            "Select to" if extend else "Jump to",
            " " if self.extend else "",
            self.on_cancel,
            self.on_change,
            self.on_cancel,
        )

    def _find_match(self, char, view, charset) -> "dict[str, sublime.Region]":
        visible_region = views[view]
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
            if self.is_regex:
                matches = view.find_all(char)
            else:
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
        for view in views:
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
                    "extend": self.extend,
                },
            )

    @property
    def _active_views(self):
        if self.extend:
            return [self.view]
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
        if value.strip() in self.positions:
            self.on_cancel()

        # Switch selection mode
        if value == " ":
            self.extend = 1
            self._show_labels(value.strip())
            return

        if value == "\t":
            self.extend = 2
            self._show_labels(value.strip())
            return

        if not value:
            self.extend = 0
            self._show_labels(value.strip())
            return

        value = value.strip()

        if value in self.positions:
            target_view = self.positions[value][1]
            if self.extend:
                to_jump = []
                for sel in target_view.sel():
                    target_idx = self.positions[value][0].a

                    if self.extend == 1 and target_idx < min(sel.a, sel.b):
                        # Do not select the match
                        target_idx += 1

                    if self.extend == 2 and target_idx > min(sel.a, sel.b):
                        # Select the match
                        target_idx += 1

                    to_jump.append(
                        sublime.Region(
                            min(target_idx, sel.a, sel.b),
                            max(target_idx, sel.a, sel.b),
                        )
                    )

                target_view.sel().clear()
                for r in to_jump:
                    target_view.sel().add(r)

                target_view.show(to_jump[0])

            else:
                for view in views:
                    view.sel().clear()

                to_jump = sublime.Region(
                    self.positions[value][0].a,
                    self.positions[value][0].a,
                )
                target_view.sel().add(to_jump)
                target_view.show(to_jump)

            self.view.window().focus_view(target_view)

        else:
            # Update color of phantom
            self._show_labels(value)

    def on_cancel(self, *args, **kwargs):
        if self.exit:
            return
        self.exit = True

        self.view.window().run_command("hide_panel", {"cancel": True})
        for view in views:
            view.run_command("select_char_selection_remove_labels")


class SelectCharSelectionAddLabelsCommand(sublime_plugin.TextCommand):
    """Do those modifications in a command, to easily undo it once we are done."""

    def run(self, edit, positions, search, extend):
        self.extend = extend

        visible_region = views.get(self.view) or self.view.visible_region()

        text = self.view.export_to_html(visible_region, minihtml=True)

        line_padding_bottom = self.view.settings().get("line_padding_bottom", 0)
        line_padding_top = self.view.settings().get("line_padding_top", 0)
        line_height = int(
            self.view.line_height() + line_padding_bottom + line_padding_top
        )

        offset_region = visible_region.a
        html_positions = get_element_html_positions(
            text,
            [p[1] - offset_region for p in positions],
        )

        style = self.view.style()
        # print(style)

        positions = sorted(positions, key=lambda x: x[1], reverse=True)
        for i, (c, a, b) in enumerate(positions):
            html_position = html_positions.get(a - offset_region)
            if not html_position:
                continue

            color = (
                (style["pinkish"] if not self.extend else style["yellowish"])
                if c.startswith(search)
                else style["caret"]
            )

            add_style = {"background-color": style["inactive_selection"]}
            if self.extend == 2:
                add_style = {
                    "background-color": style["selection"],
                    "border": f"1px solid {style['yellowish']}",
                    "padding": "-1px",
                }

            label = c[len(search) : len(search) + 1] or c[-1]
            start, size = html_position

            if "<br" in text[start : start + size]:
                size = 0  # Jump to end of line

            text = (
                text[:start]
                + "<style>html, body {padding: 0px; margin: 0px}</style>"
                + make_element(
                    "span",
                    label,
                    {
                        "color": color,
                        "font-style": "normal",
                        "font-weight": "bold",
                        "border-radius": "5px",
                        **add_style,
                    },
                )
                + text[start + size :]
            )

        text = text.replace("<br>", "<br>&#8203;")

        scroll_x, scroll_y = self.view.viewport_position()
        gutter_width = scroll_x - self.view.window_to_layout((0, 0))[0]

        padding_top = self.view.text_to_layout(visible_region.a)[1] - scroll_y

        # print(self.view.text_to_layout(visible_region.a))
        # print(self.view.text_to_window(visible_region.a))
        # print(self.view.viewport_position())
        # print(self.view.layout_to_window((0, 0)))
        # print(self.view.window_to_layout((0, 0)))

        content = make_element(
            "div",
            text,
            {
                "line-height": f"{line_height}px",
                "padding-left": f"{gutter_width - scroll_x}px",
                "padding-top": f"{padding_top}px",
            },
            True,
        )
        if (
            self.view.id() not in sheets_per_view
            or not sheets_per_view[self.view.id()].is_selected()
        ):
            sheet = self.view.window().new_html_sheet(
                "Labels",
                "",
                flags=4,
                group=self.view.sheet().group(),
            )
            sheets_per_view[self.view.id()] = sheet

        sheets_per_view[self.view.id()].set_contents(content)


class SelectCharSelectionRemoveLabelsCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if self.view.id() in sheets_per_view:
            sheets_per_view.pop(self.view.id()).close()

        self.view.window().focus_view(active_view[self.view.window()])


def make_element(tag, content, style, is_content_html=False):
    style = ";".join(f"{name}: {value}" for name, value in style.items())
    return f'<{tag} style="{style}">{content if is_content_html else html.escape(content)}</{tag}>'
