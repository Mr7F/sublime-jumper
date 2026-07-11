import html
from collections import Counter

import sublime
import sublime_plugin

from .utils import (
    clean_charset,
    get_next_element,
    jump_to,
    setting,
)

sheets_per_view = {}
active_view = {}
views = {}
active_jumper_input = {}
active_jumper_by_window = {}


class JumperCommand(sublime_plugin.TextCommand):
    """Highlight the matches visible on the screen with a one-letter label.

    Typing either narrows the matches (the typed text must match the start of
    their text) or jumps to a match (when the typed character is its label),
    like flash.nvim: a character that can continue the search of a match is
    never used as a label, so the two are always unambiguous. Narrowing down
    to a single match jumps immediately, and when the next character of a
    match already narrows down to it, that character is shown as its jump
    char instead of a label.

    The labels are visible as soon as the command starts: each match shows
    its first letter followed by the label it will have once that letter is
    typed, so the whole key sequence is readable right away.

    Similar package:
    > https://github.com/folke/flash.nvim
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
        self.search = ""
        self.sticky_labels = {}

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
        self.matches = {view: self._find_match(view) for view in views}
        self._assign_labels()
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

    def _find_match(self, view) -> "list[tuple[sublime.Region, str]]":
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
        # Rendering more matches than that would be unusable anyway
        matches = matches[: len(self.charset) ** 2]

        texts = [view.substr(region) for region in matches]
        if not self.case_sensitive:
            texts = [text.lower() for text in texts]

        return list(zip(matches, texts))

    def _assign_labels(self):
        """flash.nvim-style labels for the matches narrowed by the search.

        The search matches the start of the text of a match. A character that
        can still continue the search of a match is never used as a label, so
        typing it always narrows instead of jumping. When the next character
        of a match cannot continue any other match, typing it narrows down to
        that single match and jumps: that character becomes the jump char of
        the match, no label is needed. The remaining charset goes to the
        closest matches first, keeping the label a match got on the previous
        keystrokes; when the charset runs out, the extra matches stay
        unlabelled until the search narrows them down.

        With an empty search, the labels are computed per first-letter group,
        as if that letter was already typed, and only previewed: typing the
        first letter then shows the same labels, in the same place, for real.
        """
        matched = [
            (view, region, text)
            for view, matches in self.matches.items()
            for region, text in matches
            if text.startswith(self.search)
        ]

        self.targets = [(view, region) for view, region, _text in matched]
        self.narrowed = {view: [] for view in self.matches}
        self.positions = {view: {} for view in self.matches}

        if self.search:
            self._label_matches(matched)
            return

        # At rest, preview for each match the label it will have once its
        # first letter is typed, so the whole key sequence is readable right
        # away. The previewed labels are not typable yet: the first key
        # always narrows.
        groups = {}
        for match in matched:
            groups.setdefault(match[2][:1], []).append(match)

        for group in groups.values():
            if len(group) == 1:
                # A single match: its first letter narrows down to it and jumps
                view, region, text = group[0]
                self.narrowed[view].append((region.a, region.b, text[:1], 0))
            else:
                self._label_matches(group, preview=True)

    def _label_matches(self, matched, preview=False):
        search_len = 1 if preview else len(self.search)
        matched = [
            (view, region, text[search_len : search_len + 1])
            for view, region, text in matched
        ]

        counts = Counter(next_char for _view, _region, next_char in matched)
        pool = [c for c in self.charset if c not in counts]

        # A next char that only one match can follow is its jump char
        matched = [
            (view, region, next_char if next_char and counts[next_char] == 1 else "")
            for view, region, next_char in matched
        ]

        labels = {}
        for view, region, jump_char in matched:
            key = (view.id(), region.a)
            sticky = self.sticky_labels.get(key)
            if not jump_char and sticky in pool:
                pool.remove(sticky)
                labels[key] = sticky

        for view, region, jump_char in matched:
            key = (view.id(), region.a)
            if not jump_char and key not in labels and pool:
                labels[key] = self.sticky_labels[key] = pool.pop(0)

        # The preview sits after the first letter, keeping it readable
        gap = int(preview)

        for view, region, jump_char in matched:
            if jump_char:
                self.narrowed[view].append((region.a, region.b, jump_char, gap))
                continue

            label = labels.get((view.id(), region.a))
            self.narrowed[view].append((region.a, region.b, label, gap if label else 0))
            if label and not preview:
                self.positions[view][label] = region

    def _show_labels(self):
        for view, matches in self.narrowed.items():
            if self.extend and view != self.view:
                # The "extend" modes cannot work cross-view
                matches = []

            view.run_command(
                "select_char_selection_add_labels",
                {
                    "positions": [
                        (label or "", a, b, gap) for a, b, label, gap in matches
                    ],
                    "search_length": len(self.search),
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
        if not self.case_sensitive:
            value = value.lower()

        if not value.startswith(self.search):
            # Backspace or an edit: replay the narrowing from the new text
            self.search = ""
            self._assign_labels()

        for char in value[len(self.search) :]:
            target = self._label_target(char)
            if target is not None:
                self._jump(*target)
                return

            self.search += char
            self._assign_labels()

            # A single match left: no need to type its label
            if len(self.targets) == 1:
                view, region = self.targets[0]
                if not self.extend or view == self.view:
                    self._jump(view, region)
                    return

        self._show_labels()

    def _label_target(self, char):
        for view, values in self.positions.items():
            # The "extend" modes cannot work cross-view
            if char in values and (not self.extend or view == self.view):
                return view, values[char]

        return None

    def _jump(self, target_view, region):
        self.on_cancel()

        self.view.window().focus_view(target_view)

        selection = list(target_view.sel())
        if not selection and not self.extend:
            selection = [target_view.visible_region()]

        if self.extend != 3:
            target_view.sel().clear()

        for sel in selection:
            jump_to(
                target_view,
                region,
                sel,
                self.extend in (1, 2),
                self.extend == 2,
            )

        target_view.show(target_view.sel()[0])

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
        self._show_labels()


class SelectCharSelectionAddLabelsCommand(sublime_plugin.TextCommand):
    """Do those modifications in a command, to easily undo it once we are done."""

    def run(self, edit, positions, search_length, extend):
        visible_region = views.get(self.view) or self.view.visible_region()

        text = self.view.export_to_html(visible_region, minihtml=True)
        text = self._split_wrapped_lines(text, visible_region)

        offset_region = visible_region.a

        line_padding_bottom = self.view.settings().get("line_padding_bottom", 0)
        line_padding_top = self.view.settings().get("line_padding_top", 0)
        line_height = int(
            self.view.line_height() + line_padding_bottom + line_padding_top
        )
        html_positions = self._get_element_html_positions(
            text,
            [p[1] - offset_region for p in positions],
            visible_region,
        )

        style = self.view.style()
        label_color = (
            {1: style["yellowish"], 2: style["bluish"], 3: style["greenish"]}
        ).get(int(extend), style["orangish"])

        highlight_style = {
            "background-color": style["inactive_selection"],
            "border-radius": "5px",
        }

        positions = sorted(positions, key=lambda x: x[1], reverse=True)
        for label, a, b, gap in positions:
            html_position = html_positions.get(a - offset_region)
            if not html_position:
                continue

            start, _ = html_position

            # The label never overflows the word: when the search reaches its
            # end, the label replaces the last letter of the word
            prefix_count = search_length
            if label and a + prefix_count + gap >= b:
                if gap:
                    gap = 0
                else:
                    prefix_count -= 1

            # HTML sizes of the matched prefix, of the characters kept as-is
            # before the label, and of the character covered by the label.
            # Tags are never replaced (eg `<br>` when the label lands at the
            # end of the line), the label is only inserted before them.
            prefix_size = self._html_size(text, start, prefix_count)
            keep_size = self._html_size(text, start + prefix_size, gap)
            label_size = (
                self._html_size(text, start + prefix_size + keep_size, 1)
                if label
                else 0
            )

            replacement = ""
            if prefix_size:
                replacement += make_element(
                    "span",
                    text[start : start + prefix_size],
                    highlight_style,
                    True,
                )

            replacement += text[start + prefix_size : start + prefix_size + keep_size]

            if label:
                replacement += make_element(
                    "span",
                    label,
                    {
                        "color": label_color,
                        "font-style": "normal",
                        "font-weight": "bold",
                        **highlight_style,
                    },
                )

            text = (
                text[:start]
                + replacement
                + text[start + prefix_size + keep_size + label_size :]
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

    def _get_element_html_positions(self, html, indexes, visible_region):
        """Map source-text offsets to exported HTML positions."""
        wanted = set(indexes)
        if not wanted:
            return {}

        found = {}
        column = 0
        source = self.view.substr(visible_region)
        tab_size = max(int(self.view.settings().get("tab_size", 4)), 1)

        def text_elements():
            index = 0
            while index < len(html):
                size, text_size = get_next_element(html, index)
                if text_size:
                    yield index, size
                index += size

        elements = iter(text_elements())

        for source_index, character in enumerate(source):
            element = next(elements, None)
            if element is None:
                break

            start, size = element
            if source_index in wanted:
                found[source_index] = (start, size)
                if len(found) == len(wanted):
                    return found

            if character == "\n":
                exported_width = 1
                column = 0
            elif character == "\t":
                exported_width = tab_size - column % tab_size
                column += exported_width
            else:
                exported_width = 1
                column += 1

            # The first exported element was consumed above. Sublime exports a
            # tab as one element per visual column, all representing one buffer
            # character, so skip the remaining elements of that tab.
            for _ in range(exported_width - 1):
                if next(elements, None) is None:
                    return found

        return found

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

        wrap_positions = self._get_element_html_positions(
            text,
            [p - offset_region for p in wrap_points],
            visible_region,
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

    @staticmethod
    def _html_size(text, start, char_count):
        """HTML size covering `char_count` buffer characters from `start`."""
        size = 0
        covered = 0

        while covered < char_count and start + size < len(text):
            if text[start + size] == "<":
                break
            html_size, text_size = get_next_element(text, start + size)
            size += html_size
            covered += text_size

        return size


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

        jumper._show_labels()


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
    style = html.escape(style, quote=True)
    content = content if is_content_html else html.escape(content)
    return f'<{tag} style="{style}">{content}</{tag}>'
