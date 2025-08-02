import html
import re

import sublime
import sublime_plugin

from .utils import (
    JumperLabel,
    get_element_html_positions,
    get_word_separators,
    setting,
)

sheets_per_view = {}
active_view = {}
views = {}


class JumperGoToAnywhereCommand(sublime_plugin.TextCommand):
    """Highlight all the characters visible on the screen, with a letter for each, press that letter to jump to the position.

    Similar package:
    > https://packagecontrol.io/packages/EasyMotion
    > https://github.com/ice9js/ace-jump-sublime
    > https://github.com/jfcherng-sublime/ST-AceJump-Chinese
    """

    def run(self, edit, character, extend=False, is_regex=False):
        global views, sheets_per_view, active_view

        self.extend = int(extend)
        self.is_regex = is_regex
        self.word_mode = setting("jumper_go_to_anywhere_word_mode", self.view)

        views = {v: v.visible_region() for v in self._active_views if v is not None}
        active_view[self.view.window()] = self.view.window().active_view()

        for sheet in sheets_per_view.values():
            sheet.close()
        sheets_per_view = {}

        self.edit = edit
        self.charset = setting("jumper_go_to_anywhere_charset", self.view)
        self.case_sensitive = setting("jumper_go_to_anywhere_case_sensitive", self.view)

        self.charset = re.sub(r"[\s\t|]", "", self.charset)  # Reserved for commands

        if not self.case_sensitive:
            self.charset = self.charset.lower()

        self.jump_next_c = "."

        # Remove redundant characters (and `.` is used when we need morel labels)
        cleaned_charset = ""
        for c in self.charset:
            if c not in cleaned_charset and c != self.jump_next_c:
                cleaned_charset += c
        self.charset = list(cleaned_charset)

        # Show many jumps characters if needed
        base_charset = self.charset.copy()
        for i in range(1, 5):
            self.charset.extend([i * self.jump_next_c + c for c in base_charset])

        assert len(set(self.charset)) == len(self.charset)

        self.exit = False
        self._find_match_views(character)

        self.view.window().show_input_panel(
            "Select to" if extend else "Jump to",
            character + (" " if self.extend else ""),
            self.on_cancel,
            self.on_change,
            self.on_cancel,
        )

    def _find_match(self, char, view, charset) -> "dict[str, JumperLabel]":
        if not char.strip() and len(char) > 2:
            return {}
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
            flags = 0
            if not self.case_sensitive:
                flags |= sublime.IGNORECASE
            if not self.is_regex:
                char = re.escape(char)
            if self.word_mode:
                seps = get_word_separators(view) + " \n"
                if not char.startswith(tuple(seps)):
                    char = f"(?<=[{re.escape(seps)}])({char})[^{re.escape(seps)}]*"

            matches = view.find_all(char, flags, within=visible_region)

        matches = sorted(matches, key=lambda x: abs(x.begin() - start_cursor))
        matches = matches[: len(charset)]
        # Make labels deterministic
        before = [m for m in matches if m.begin() < start_cursor]
        if view != self.view:
            # view not having the focus, do not hide label for current position
            start_cursor -= 1
        after = [m for m in matches if m.begin() > start_cursor]
        positions = {}
        for i, region in enumerate(after):
            if i >= len(charset) // 2:
                break
            c = charset[2 * i]
            positions[c] = JumperLabel(region, c)

        for i, region in enumerate(before):
            if i >= len(charset) // 2:
                break
            c = charset[2 * i + 1]
            positions[c] = JumperLabel(region, c)

        return positions

    def _find_match_views(self, char, label_search=""):
        """Find the matching chars in all active view and add labels."""
        if char != getattr(self, "char", None):
            self.positions: "dict[View, dict[str, JumperLabel]]" = {}
            self.char = char
            if len(char) >= self.search_length:
                charset = self.charset.copy()
                for view in views:
                    self.positions[view] = self._find_match(char, view, charset)
                    charset = [c for c in charset if c not in self.positions[view]]

        self._show_labels(label_search)

    @property
    def search_length(self):
        return setting("jumper_go_to_anywhere_search_length", self.view, 1)

    def _show_labels(self, label_search=""):
        for view, values in self.positions.items():
            view.run_command(
                "select_char_selection_add_labels",
                {
                    "positions": [
                        (c, label.label_region.a, label.label_region.b)
                        for c, label in values.items()
                    ],
                    "label_search": label_search,
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

    def on_change(self, value):
        char, search_label = value[: self.search_length], value[self.search_length :]

        cmd = ""
        if search_label and search_label[0] in " \t|":
            cmd = search_label[0]
            search_label = search_label[1:]

        target_view, jump = next(
            (
                (view, values[search_label])
                for view, values in self.positions.items()
                if search_label in values
            ),
            (None, None),
        )

        if jump is not None:
            self.on_cancel()

        # Switch selection mode
        if cmd == " " and not search_label:
            self.extend = 1
            self._find_match_views(char, search_label)
            return

        if cmd == "\t" and not search_label:
            self.extend = 2
            self._find_match_views(char, search_label)
            return

        if cmd == "|" and not search_label:
            self.extend = 3
            self._find_match_views(char, search_label)
            return

        if not search_label:
            self.extend = 0
            self._find_match_views(char, search_label)
            return

        if jump is not None:
            self.view.window().focus_view(target_view)

            selection = list(target_view.sel())
            if not selection and not self.extend:
                selection = [target_view.visible_region()]

            if self.extend != 3:
                target_view.sel().clear()
            for sel in selection:
                jump.jump_to(target_view, sel, self.extend in (1, 2), self.extend == 2)

            target_view.show(target_view.sel()[0])

        else:
            self._find_match_views(char, search_label)

    def on_cancel(self, *args, **kwargs):
        if self.exit:
            return
        self.exit = True

        for view in views:
            view.run_command("select_char_selection_remove_labels")

        self.view.window().run_command("hide_panel", {"cancel": True})
        self.view.window().focus_view(active_view[self.view.window()])


class SelectCharSelectionAddLabelsCommand(sublime_plugin.TextCommand):
    """Do those modifications in a command, to easily undo it once we are done."""

    def run(self, edit, positions, label_search, extend):
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

        positions = sorted(positions, key=lambda x: x[1], reverse=True)
        for i, (c, a, b) in enumerate(positions):
            html_position = html_positions.get(a - offset_region)
            if not html_position:
                continue

            color = (
                ({1: style["yellowish"], 2: style["bluish"], 3: style["greenish"]}).get(
                    int(extend), style["pinkish"]
                )
                if c.startswith(label_search)
                else style["caret"]
            )

            add_style = {
                "background-color": style["inactive_selection"],
                "border-radius": "5px",
            }

            start, size = html_position

            if "<br" in text[start : start + size]:
                size = 0  # Jump to end of line

            if setting("jumper_go_to_anywhere_no_borders_label", self.view):
                label = c[len(label_search) : len(label_search) + 1] or c[-1]

            else:
                # Show border to specify the number of time we need to press the "multi-label" character
                label = c[-1]
                borders = next(
                    (i for i, (a, b) in enumerate(zip(label_search, c)) if a != b),
                    len(c) - len(label_search),
                )
                borders -= 1

                if borders >= 1:
                    add_style["background-color"] = ""
                    add_style["border-radius"] = "0px"
                    add_style["padding-bottom"] = "-1px"
                    add_style["border-bottom"] = f"1px solid {color}"
                if borders >= 2:
                    add_style["padding-right"] = "-1px"
                    add_style["border-right"] = f"1px solid {color}"
                if borders >= 3:
                    add_style["padding-top"] = "-1px"
                    add_style["border-top"] = f"1px solid {color}"
                if borders >= 4:
                    add_style["padding-left"] = "-1px"
                    add_style["border-left"] = f"1px solid {color}"

            text = (
                text[:start]
                + make_element(
                    "span",
                    label,
                    {
                        "color": color,
                        "font-style": "normal",
                        "font-weight": "bold",
                        **add_style,
                    },
                )
                + text[start + size :]
            )

        offset = 1  # Adjust, so the text don't move

        text += "<style>html, body {padding: 0px; margin: 0px}</style>"
        text = text.replace("<br>", "<br>&#8203;")

        scroll_x, scroll_y = self.view.viewport_position()
        gutter_width = scroll_x - self.view.window_to_layout((0, 0))[0] + offset

        padding_top = self.view.text_to_layout(visible_region.a)[1] - scroll_y - offset

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


def make_element(tag, content, style, is_content_html=False):
    style = ";".join(f"{name}: {value}" for name, value in style.items())
    return f'<{tag} style="{style}">{content if is_content_html else html.escape(content)}</{tag}>'
