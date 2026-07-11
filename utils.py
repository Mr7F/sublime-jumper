import re

import sublime

from .selection_frontier import (
    get_frontier,
    same_region,
    set_frontier,
)


def get_next_element(html, index):
    # Return the size of the next element (in HTML code and in inner text)
    if html[index] == "<":
        m = re.match(r"^<.*?>", html[index:])
        tag = m.group(0).lower()
        if "<br" in tag:
            # `<br class="wrap">` are the visual line wraps added by the
            # plugin, they do not exist in the buffer
            return m.end(), 0 if "wrap" in tag else 1
        if tag.startswith('<span class="wrap"'):
            # Indentation of the wrapped rows added by the plugin, its
            # content does not exist in the buffer
            end = html.index("</span>", index) + len("</span>")
            return end - index, 0
        return m.end(), 0
    if html[index] == "&":
        return re.match(r"^&.*?;", html[index:]).end(), 1
    return 1, 1


def jump_to(view, region, cursor_region, extend, included):
    """Jump to the target region.

    :param view: View in which the jump will happen
    :param region: The region where we jump / select
    :param cursor_region: The cursor region from which we jump
    :param extend: True if we should extend the selection
    :param included: Used when `extend == True`, to know if we should
        include the target region in the selection or not
    """
    if not extend:
        # Jump before the region
        view.sel().add(sublime.Region(region.a, region.a))
        return

    cursor_a, cursor_b = sorted(cursor_region.to_tuple())

    if region.a < cursor_a:
        view.sel().add(sublime.Region(cursor_b, region.a if included else region.b))
    else:
        view.sel().add(sublime.Region(cursor_a, region.b if included else region.a))


def apply_selection_targets(
    view,
    origins,
    targets,
    mode="replace",
    scope="region.greenish",
):
    """Apply resolved targets and make them the next navigation frontier."""
    add = selection_mode_adds(mode)
    targets = [target for target in targets if target is not None]
    if not targets:
        return False

    if not add:
        for origin in origins:
            view.sel().subtract(origin)

    view.sel().add_all(targets)

    # Sublime merges intersecting selections. Store the resulting native
    # selections as the frontier so it remains valid after that normalization.
    frontier = []
    for selection in view.sel():
        if any(
            selection.begin() <= target.begin()
            and selection.end() >= target.end()
            for target in targets
        ):
            frontier.append(selection)

    set_frontier(view, frontier, scope=scope)
    view.show(frontier[0])

    view.window().run_command(
        "add_jump_record",
        {"selection": [selection.to_tuple() for selection in view.sel()]},
    )
    return True


def selection_mode_adds(mode):
    if mode not in ("replace", "add"):
        raise ValueError("mode must be 'replace' or 'add'")
    return mode == "add"


def select_next_region(view, regions, direction="next", mode="replace"):
    """Given a list of region, select the next / previous one.

    The region can overlap (eg a nested json, etc).
    """
    if direction == "next":
        regions = sorted(regions, key=lambda r: min(r))
    else:
        regions = sorted(regions, key=lambda r: min(r), reverse=True)

    origins = get_frontier(view) or list(view.sel())

    add = selection_mode_adds(mode)

    if add:
        # Exact existing selections remain navigable so `add` can move the
        # frontier through the retained selection set. A target strictly
        # contained by a larger selection cannot become a distinct Sublime
        # selection, so continue to exclude those merged targets.
        regions = [
            r
            for r in regions
            if any(same_region(r, sel) for sel in view.sel())
            or all(max(r) > max(sel) or min(r) < min(sel) for sel in view.sel())
        ]

    targets = []
    for sel in origins:
        if direction == "next":
            target = next(
                (r for r in regions if min(sel) < min(r)),
                regions[0] if regions else None,
            )
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
                regions[0] if regions else None,
            )

        if target is not None:
            targets.append(target)

    apply_selection_targets(
        view,
        origins,
        targets,
        mode=mode,
    )


def clean_charset(charset, case_sensitive):
    # Remove the characters used by the mode-switching commands
    charset = re.sub(r"[\s|]", "", charset)
    if not case_sensitive:
        charset = charset.lower()
    return list(dict.fromkeys(charset))


def setting(name, view, default=None):
    # Load settings from the user preferences first, and then from the Jumper settings
    default = sublime.load_settings("Jumper.sublime-settings").get(name, default)
    return view.settings().get(name, default)
