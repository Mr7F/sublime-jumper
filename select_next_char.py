import sublime, sublime_plugin, re
from itertools import chain


def _select_next(view, selection, direction, char):
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
        view.sel().add(sublime.Region(target_idx, target_idx + 1))
        break


class SelectNextCharCommand(sublime_plugin.TextCommand):
    def run(self, edit, char, direction="next"):
        for selection in list(self.view.sel()):
            _select_next(self.view, selection, direction, char)

        selections = self.view.sel()
        if len(selections) == 1:
            self.view.show(selections[0])


class SelectNextCharSelectionCommand(sublime_plugin.TextCommand):
    def run(self, edit, direction="next"):
        for selection in list(self.view.sel()):
            a, b = sorted(selection.to_tuple())

            selection_text = self.view.substr(selection)
            if len(selection_text) == 1:
                _select_next(self.view, selection, direction, selection_text)
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
