import html

import sublime
import sublime_plugin

from .create_label import make_prefix_free_labels
from .utils import (
    JumperLabel,
    clean_charset,
    get_element_html_positions,
    get_next_element,
    setting,
)

sheets_per_view = {}
active_view = {}
views = {}
active_jumper_input = {}
active_jumper_by_window = {}


class JumperCommand(sublime_plugin.TextCommand):
    """Highlight all the characters visible on the screen, with a letter for each, press that letter to jump to the position.

    Similar package:
    > https://packagecontrol.io/packages/EasyMotion
    > https://github.com/ice9js/ace-jump-sublime
    > https://github.com/jfcherng-sublime/ST-AceJump-Chinese
    """

    def run(self, edit, regex, extend=False, current_line=False):
        if self.restart_without_current_line(regex, extend, current_line):
            return

        self.extend = int(extend)
        self.search_regex = regex
        self.current_line = current_line

        self.case_sensitive = setting("jumper_case_sensitive", self.view)
        self.charset = clean_charset(
            setting("jumper_charset", self.view),
            self.case_sensitive,
        )

        window = self.view.window()
        active_jumper_by_window[window.id()] = self

        views.clear()
        views.update(
            {v: v.visible_region() for v in self._active_views if v is not None}
        )

        active_view[window] = window.active_view()

        for sheet in list(sheets_per_view.values()):
            sheet.close()

        sheets_per_view.clear()

        self.exit = False
        self._init_labels()
        self._show_labels()

        input_view = window.show_input_panel(
            "Select to" if extend else "Jump to",
            "",
            self.on_cancel,
            self.on_change,
            self.on_cancel,
        )

        input_view.settings().set("jumper_input", True)
        active_jumper_input[input_view.id()] = self
        self.input_view = input_view

    def restart_without_current_line(self, regex, extend, current_line):
        """Re-running the command while it shows the current line escalates it to the whole screen."""
        if not current_line:
            return False

        previous = active_jumper_by_window.get(self.view.window().id())

        if (
            previous is None
            or not previous.current_line
            or not setting("jumper_escalate_line_to_screen", previous.view, False)
        ):
            return False

        target_view = previous.view

        previous.on_cancel(restore_focus=False)

        sublime.set_timeout(
            lambda: target_view.run_command(
                "jumper",
                {
                    "regex": regex,
                    "extend": extend,
                    "current_line": False,
                },
            ),
            0,
        )

        return True

    def _find_match(self, view) -> "list[sublime.Region]":
        visible_region = views[view]

        cursor = (
            view.sel()[0].b
            if view.sel()
            else (visible_region.a + visible_region.b) // 2
        )

        search_region = (
            view.line(cursor).intersection(visible_region)
            if self.current_line
            else visible_region
        )

        flags = 0 if self.case_sensitive else sublime.IGNORECASE
        matches = view.find_all(self.search_regex, flags, within=search_region)

        matches = sorted(matches, key=lambda x: abs(x.begin() - cursor))
        # More matches than two-characters labels would be unusable anyway
        return matches[: len(self.charset) ** 2]

    def _init_labels(self):
        """Create the labels for the current regex, unique across all the views."""
        matches = [
            (view, region) for view in views for region in self._find_match(view)
        ]

        labels = make_prefix_free_labels(
            texts=[view.substr(region) for view, region in matches],
            alphabet=self.charset,
            case_sensitive=self.case_sensitive,
        )

        self.positions: "dict[View, dict[str, JumperLabel]]" = {
            view: {} for view in views
        }
        for i, (view, region) in enumerate(matches):
            label = labels.get(i)
            if label is not None:
                self.positions[view][label] = JumperLabel(region, label)

    def _show_labels(self, label_search=""):
        for view, values in self.positions.items():
            if self.extend and view != self.view:
                # The "extend" modes cannot work cross-view
                values = {}

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
        if self.extend or self.current_line:
            return [self.view]
        views = [
            self.view.window().active_view_in_group(group)
            for group in range(self.view.window().num_groups())
        ]
        return sorted(views, key=lambda v: v != self.view)

    def on_change(self, value):
        label_search = value

        target_view, jump = next(
            (
                (view, values[label_search])
                for view, values in self.positions.items()
                if label_search in values
                # The "extend" modes cannot work cross-view
                and (not self.extend or view == self.view)
            ),
            (None, None),
        )

        if jump is not None:
            self.on_cancel()

        if not label_search:
            self._show_labels(label_search)
            return

        if jump is not None:
            self.view.window().focus_view(target_view)

            selection = list(target_view.sel())
            if not selection and not self.extend:
                selection = [target_view.visible_region()]

            if self.extend != 3:
                target_view.sel().clear()

            for sel in selection:
                jump.jump_to(
                    target_view,
                    sel,
                    self.extend in (1, 2),
                    self.extend == 2,
                )

            target_view.show(target_view.sel()[0])
        else:
            self._show_labels(label_search)

    def on_cancel(self, *args, restore_focus=True, **kwargs):
        if self.exit:
            return

        self.exit = True

        window = self.view.window()
        window_id = window.id()

        if active_jumper_by_window.get(window_id) is self:
            active_jumper_by_window.pop(window_id, None)

        if hasattr(self, "input_view"):
            active_jumper_input.pop(self.input_view.id(), None)
            # The input panel view is reused by other panels (eg rename file),
            # the keybindings must not stay active there
            self.input_view.settings().erase("jumper_input")

        for view in list(views):
            view.run_command("select_char_selection_remove_labels")

        window.run_command("hide_panel", {"cancel": True})

        view_to_focus = active_view.pop(window, None)

        if restore_focus and view_to_focus is not None:
            window.focus_view(view_to_focus)

    def reset_mode(self):
        self.extend = 0
        self._show_labels("")


class SelectCharSelectionAddLabelsCommand(sublime_plugin.TextCommand):
    """Do those modifications in a command, to easily undo it once we are done."""

    def run(self, edit, positions, label_search, extend):
        self.extend = extend

        visible_region = views.get(self.view) or self.view.visible_region()

        text = self.view.export_to_html(visible_region, minihtml=True)
        text = self._split_wrapped_lines(text, visible_region)

        offset_region = visible_region.a

        line_padding_bottom = self.view.settings().get("line_padding_bottom", 0)
        line_padding_top = self.view.settings().get("line_padding_top", 0)
        line_height = int(
            self.view.line_height() + line_padding_bottom + line_padding_top
        )
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

            start, _ = html_position

            visible_label_max_width = max(b - a, 1)
            visible_label, borders = self.visible_label_for(
                c,
                label_search,
                visible_label_max_width,
            )

            # HTML length of the text replaced by the label. Tags are never
            # replaced (eg `<br>` when jumping to the end of the line), the
            # label is only inserted before them.
            consumed = 0
            covered = 0
            while covered < len(visible_label) and start + consumed < len(text):
                if text[start + consumed] == "<":
                    break
                html_size, text_size = get_next_element(text, start + consumed)
                consumed += html_size
                covered += text_size

            borders_style = {}
            if borders >= 1:
                borders_style["background-color"] = ""
                borders_style["border-radius"] = "0px"
                borders_style["padding-bottom"] = "-1px"
                borders_style["border-bottom"] = f"1px solid {color}"
            if borders >= 2:
                borders_style["padding-right"] = "-1px"
                borders_style["border-right"] = f"1px solid {color}"
            if borders >= 3:
                borders_style["padding-top"] = "-1px"
                borders_style["border-top"] = f"1px solid {color}"
            if borders >= 4:
                borders_style["padding-left"] = "-1px"
                borders_style["border-left"] = f"1px solid {color}"

            text = (
                text[:start]
                + make_element(
                    "span",
                    visible_label[:-1],
                    {
                        "color": color,
                        "font-style": "normal",
                        "font-weight": "bold",
                        **add_style,
                    },
                )
                + make_element(
                    "span",
                    visible_label[-1],
                    {
                        "color": color,
                        "font-style": "normal",
                        "font-weight": "bold",
                        **add_style,
                        **borders_style,
                    },
                )
                + text[start + consumed :]
            )

        offset = 1  # Adjust, so the text don't move

        text += "<style>html, body {padding: 0px; margin: 0px}</style>"
        text = text.replace("<br>", "<br>&#8203;")

        scroll_x, scroll_y = self.view.viewport_position()
        gutter_width = scroll_x - self.view.window_to_layout((0, 0))[0] + offset

        padding_top = self.view.text_to_layout(visible_region.a)[1] - scroll_y - offset

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

    def _split_wrapped_lines(self, text, visible_region):
        """Break the lines of the exported HTML at the same places as the editor.

        The sheet does not wrap the text (the export uses `&nbsp;`), so without
        this the wrapped lines are clipped and the following labels shift up.
        """
        if self.view.settings().get("word_wrap") is False:
            return text

        if self.view.layout_extent()[0] > self.view.viewport_extent()[0]:
            # Lines wider than the viewport: `word_wrap` ("auto") is resolved
            # to disabled, nothing is wrapped
            return text

        wrap_points = self._wrap_points(visible_region)

        if not wrap_points:
            return text

        offset_region = visible_region.a
        em_width = self.view.em_width()

        wrap_positions = get_element_html_positions(
            text,
            [p - offset_region for p in wrap_points],
        )

        for offset, (start, _) in sorted(wrap_positions.items(), reverse=True):
            wrap_element = '<br class="wrap">'

            # Reproduce the editor indentation of the wrapped row, measured
            # from the layout (it depends on the language and the settings).
            # The point after the row's first character is the first one
            # reported on the row.
            x = self.view.text_to_layout(offset + offset_region + 1)[0]
            indent = round(x / em_width) - 1

            if indent > 0:
                wrap_element += '<span class="wrap">' + "&nbsp;" * indent + "</span>"

            text = text[:start] + wrap_element + text[start:]

        return text

    def _wrap_points(self, visible_region):
        """The points where the editor visually wraps a line (start of a new visual row)."""
        view = self.view
        points = []
        point = visible_region.begin()
        end = visible_region.end()

        while point < end:
            row_y = view.text_to_layout(point)[1]

            if view.text_to_layout(end)[1] == row_y:
                break

            # First point reported on a next visual row
            lo, hi = point + 1, end
            while lo < hi:
                mid = (lo + hi) // 2
                if view.text_to_layout(mid)[1] > row_y:
                    hi = mid
                else:
                    lo = mid + 1

            # A point at the wrap boundary is reported at the end of the
            # previous row, so the character starting the next row is just
            # before `lo`
            wrap_start = lo - 1

            if "\n" not in view.substr(sublime.Region(wrap_start - 1, wrap_start + 1)):
                points.append(wrap_start)

            point = lo

        return points

    def visible_label_for(self, label, typed, width):
        width = max(width, 1)

        if len(label) <= width:
            return label, 0

        matched = 0
        for a, b in zip(typed, label):
            if a != b:
                break
            matched += 1

        if width == 1:
            # Show the next char to type.
            last_i = min(matched, len(label) - 1)
            visible = label[last_i]
        else:
            # Keep first width - 1 chars stable.
            # Only the last visible char scrolls.
            last_i = max(width - 1, matched - 1)
            last_i = min(last_i, len(label) - 1)

            if last_i < width:
                visible = label[:width]
            else:
                visible = label[: width - 1] + label[last_i]

        borders = len(label) - last_i - 1
        # the borders in the number of chars hidden on the right
        return visible, borders


class SelectCharSelectionRemoveLabelsCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if self.view.id() in sheets_per_view:
            sheets_per_view.pop(self.view.id()).close()


class JumperInputSetModeCommand(sublime_plugin.TextCommand):
    def run(self, edit, extend):
        jumper = active_jumper_input.get(self.view.id())
        if not jumper:
            return

        extend = int(extend)

        if jumper.extend == extend:
            jumper.extend = 0
        else:
            jumper.extend = extend

        label_search = self.view.substr(sublime.Region(0, self.view.size()))

        jumper._show_labels(label_search)


class JumperInputListener(sublime_plugin.EventListener):
    def on_text_command(self, view, command_name, args):
        if not view.settings().get("jumper_input"):
            return None

        jumper = active_jumper_input.get(view.id())
        if not jumper:
            return None

        # Backspace with text: keep normal behavior.
        # Backspace with empty input: reset mode.
        if command_name == "left_delete" and view.size() == 0:
            jumper.reset_mode()
            return ("noop", {})

        return None


def make_element(tag, content, style, is_content_html=False):
    style = ";".join(f"{name}: {value}" for name, value in style.items())
    return f'<{tag} style="{style}">{content if is_content_html else html.escape(content)}</{tag}>'
