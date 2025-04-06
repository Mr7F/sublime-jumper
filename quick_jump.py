import re
from itertools import chain


import sublime
import sublime_plugin


def get_word_separators(view):
    word_separators = view.settings().get("word_separators")
    return word_separators or "./\\()\"'-:,.;<>~!@#$%^&*|+=[]{}`~?"


def _select_next(view, selection, direction, character, extend=False, start_word=True):
    a, b = sorted(selection.to_tuple())
    if direction == "next" and not extend:
        a += 1
        b += 1

    if extend:
        if direction == "next":
            b += 1
        else:
            a -= 1

    word_separators = get_word_separators(view) + " \n"

    if character in "'\"`":
        character = "'\"`"

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
            file_content = list(reversed(file_content))

        char_idx = next(
            (
                i
                for i, c in enumerate(file_content)
                if c in character
                and (
                    not start_word
                    or (
                        direction == "next"
                        and i > 0
                        and file_content[i - 1] in word_separators
                        or direction != "next"
                        and i < len(file_content) - 1
                        and file_content[i + 1] in word_separators
                    )
                    or c in word_separators
                )
            ),
            None,
        )
        if char_idx is None:
            continue

        if direction == "next":
            target_idx = idx + char_idx
        else:
            target_idx = idx - char_idx - 1
            if extend and target_idx < a:
                target_idx += 1

        view.sel().subtract(selection)
        end_target = target_idx
        # end_target = target_idx + 1
        if extend:
            target_idx = min(target_idx, a, b)
            end_target = max(end_target, a, b)

        view.sel().add(sublime.Region(target_idx, end_target))
        break


class SelectNextCharCommand(sublime_plugin.TextCommand):
    """Go to the character."""

    def run(self, edit, character, direction="next", extend=False, start_word=True):
        for selection in list(self.view.sel()):
            _select_next(self.view, selection, direction, character, extend, start_word)

        selections = self.view.sel()
        if len(selections) == 1:
            self.view.show(selections[0])


class SelectNextSameSelectionCommand(sublime_plugin.TextCommand):
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


class SelectionShowQuickJumpWordListener(sublime_plugin.EventListener):
    """Add a line bellow the characters for which we can do a quick jump."""

    def run(self, edit):
        pass

    def on_selection_modified(self, view):
        if not view.settings().get("quick_jump_show_word_bounds"):
            return

        all_lines = view.settings().get("quick_jump_show_all_lines")

        if len(view.sel()) != 1:
            view.add_regions("jumper_quick_jump", [])
            return

        a, b = sorted(view.sel()[0].to_tuple())
        visible_region = (
            view.visible_region() if all_lines else view.line(view.sel()[0])
        )

        word_bounds = re.escape(get_word_separators(view))

        # Search backward
        search_re = (
            f"((?<=[{word_bounds}\\s\\n])[^{word_bounds}\\s\\n])|[{word_bounds}]"
        )
        result = view.find_all(
            search_re, within=sublime.Region(max(0, visible_region.a), a)
        )
        result = sorted(result, key=lambda r: r.a, reverse=True)
        regions = []
        done = set()
        for r in result:
            s = view.substr(r)
            if s in "'\"":
                s = "'"
            if s in done:
                continue
            done.add(s)
            regions.append(r)

        # Search forward
        search_re = (
            f"((?<=[{word_bounds}\\s\\n])[^{word_bounds}\\s\\n])|[{word_bounds}]"
        )
        result = view.find_all(search_re, within=sublime.Region(b, visible_region.b))
        result = sorted(result, key=lambda r: r.a)
        done = set()
        for r in result:
            s = view.substr(r)
            if s in "'\"":
                s = "'"
            if s in done:
                continue
            done.add(s)
            regions.append(r)

        view.add_regions(
            "jumper_quick_jump", regions, scope="white", flags=1024 | 32 | 256
        )
