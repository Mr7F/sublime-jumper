import re

import sublime


def get_next_element(html, index):
    # Return the size of the next element (in HTML code and in inner text)
    if html[index] == "<":
        m = re.match(r"^<.*?>", html[index:])
        if "<br" in m.group(0).lower():
            return m.end(), 1
        return m.end(), 0
    if html[index] == "&":
        return re.match(r"^&.*?;", html[index:]).end(), 1
    return 1, 1


def get_element_html_positions(html, indexes):
    # Return the index in the HTML code of the given text
    indexes = sorted(indexes)
    text_index = 0
    i = 0

    found = {}

    for index in indexes:
        while True:
            if i >= len(html):
                return found

            html_size, text_size = get_next_element(html, i)

            if text_index == index and text_size:
                found[index] = (i, html_size)
                i += html_size
                text_index += text_size
                break

            if text_index > index:
                break

            i += html_size
            text_index += text_size

    return found


def get_element_html_position(html, index):
    return get_element_html_positions(html, [index])[index]


class JumperLabel:
    def __init__(self, region, character, label_region=None):
        """Represent a label in the editor where we can jump to.

        :param region: The region where we can jump / select
        :param character: The character used to jump to the region
        :param label_region: Where that character is displayed
        """
        self.region = region
        self.character = character
        self.label_region = region if label_region is None else label_region

    def jump_to(self, view, cursor_region, extend, included):
        """Jump to the target region.

        :param view: View in which the jump will happen
        :param cursor_region: The cursor region from which we will jump
        :param extend: True if we should extend the selection
        :param included: Used when `extend == True`, used so know if we should
            include the target region in the selection or not
        """
        if not extend:
            # Jump before the region
            view.sel().add(sublime.Region(self.region.a, self.region.a))
            return

        cursor_a, cursor_b = sorted(cursor_region.to_tuple())

        if self.region.a < cursor_a:
            if included:
                view.sel().add(sublime.Region(cursor_b, self.region.a))
            else:
                view.sel().add(sublime.Region(cursor_b, self.region.b))
        else:
            if included:
                view.sel().add(sublime.Region(cursor_a, self.region.b))
            else:
                view.sel().add(sublime.Region(cursor_a, self.region.a))


def select_next_region(view, regions, direction="next", extend=False):
    """Given a list of region, select the next / previous one.

    The region can overlap (eg a nested json, etc).
    """
    if direction == "next":
        # use max here to always explore child before parent
        regions = sorted(regions, key=lambda r: min(r))
    else:
        regions = sorted(regions, key=lambda r: min(r), reverse=True)

    if extend:
        # Remove regions inside selection
        regions = [
            r
            for r in regions
            if all(max(r) > max(sel) or min(r) < min(sel) for sel in view.sel())
        ]

    to_show = None
    for sel in list(view.sel()):
        if direction == "next":
            # use max here to always explore child before parent
            target = next((r for r in regions if min(sel) < min(r)), None)
        else:
            target = next(
                (
                    r
                    for r in regions
                    if min(sel) > min(r)
                    # If the cursor is just after the opening parenthesis
                    # and that we "select the previous parenthesis",
                    # we want to select the content of the `()` where we are
                    or (min(sel) == min(r) and max(sel) < max(r))
                ),
                None,
            )

        if target is not None:
            if not extend:
                view.sel().subtract(sel)
            view.sel().add(target)
            to_show = target

    if to_show is not None:
        view.show(to_show)
        view.show(sublime.Region(to_show.a, to_show.a))


def get_word_separators(view):
    word_separators = view.settings().get("word_separators")
    return word_separators or "./\\()\"'-:,.;<>~!@#$%^&*|+=[]{}`~?"


def setting(name, view, default=None):
    # Load settings from the user preferences first, and then from the Jumper settings
    default = sublime.load_settings("Jumper.sublime-settings").get(name, default)
    return view.settings().get(name, default)
