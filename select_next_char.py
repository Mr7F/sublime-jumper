import sublime, sublime_plugin, re


class SelectNextCharCommand(sublime_plugin.TextCommand):
    def run(self, edit, char, direction="next"):
        selections = self.view.sel()

        for selection in list(selections):
            a, b = sorted(selection.to_tuple())

            itr = (
                range(b, self.view.size(), 1000)
                if direction == "next"
                else range(a, 0, -1000)
            )

            for idx in itr:
                if direction == "next":
                    end_idx = min(idx + 1000, self.view.size())
                else:
                    end_idx = max(idx - 1000, 0)

                file_content = self.view.substr(sublime.Region(idx, end_idx))
                if direction != "next":
                    file_content = reversed(file_content)

                char_idx = next(
                    (i for i, c in enumerate(file_content) if c in char), None
                )
                if char_idx is None:
                    continue

                if direction == "next":
                    target_idx = idx + char_idx
                else:
                    target_idx = idx - char_idx - 1

                self.view.sel().subtract(selection)
                self.view.sel().add(sublime.Region(target_idx, target_idx + 1))
                break
