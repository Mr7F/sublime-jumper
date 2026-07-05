import sublime
import sublime_plugin

from .create_label import make_prefix_free_labels
from .utils import clean_charset, setting


class SelectionShowQuickScopeWordListener(sublime_plugin.EventListener):
    """Underline the current-line chars used by generated jumper labels."""

    def on_activated_async(self, view):
        self.on_selection_modified_async(view)

    def on_deactivated(self, view):
        view.erase_regions("jumper_quick_scope")
        view.erase_regions("jumper_quick_scope_line")

    def on_selection_modified_async(self, view):
        if setting("jumper_quick_scope_regex", view):
            _quick_scope_show_labels(view)


def _quick_scope_show_labels(view):
    """
    Show the labels that would be generated for current_line=True.

    It underlines the chars from the matched text that are used by the label.

    If a label contains generated chars that are not present in the matched text,
    that label is not shown.
    """
    view.erase_regions("jumper_quick_scope")
    view.erase_regions("jumper_quick_scope_line")

    if not view.sel():
        return

    regex = setting("jumper_quick_scope_regex", view)

    case_sensitive = setting("jumper_case_sensitive", view)
    alphabet = clean_charset(
        setting("jumper_charset", view),
        case_sensitive,
    )

    if not alphabet:
        return

    visible_region = view.visible_region()
    flags = 0 if case_sensitive else sublime.IGNORECASE

    # Keep this close to `current_line=True`, but support multiple cursors.
    # Labels are generated in a single pass so they stay unique across cursors.
    matches = []
    seen = set()

    for selection in view.sel():
        cursor = selection.b
        line_region = view.line(cursor).intersection(visible_region)

        if line_region.empty():
            continue

        line_matches = view.find_all(regex, flags, within=line_region)
        line_matches.sort(key=lambda r: abs(r.begin() - cursor))

        for match_region in line_matches:
            key = match_region.to_tuple()
            if key not in seen:
                seen.add(key)
                matches.append(match_region)

    if not matches:
        return

    labels = make_prefix_free_labels(
        texts=[view.substr(region) for region in matches],
        alphabet=alphabet,
        case_sensitive=case_sensitive,
    )

    underline_regions = []

    for i, match_region in enumerate(matches):
        label = labels.get(i)

        if not label:
            continue

        regions = _quick_scope_regions_for_label(
            view=view,
            match_region=match_region,
            label=label,
            case_sensitive=case_sensitive,
        )

        # If the generated label contains chars that are not present
        # in the matched text, show nothing for that label.
        if regions is None:
            continue

        underline_regions.extend(regions)

    if not underline_regions:
        return

    scope = "text.plain" if view.element() else "comment"

    flags = (
        sublime.DRAW_SOLID_UNDERLINE | sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE
    )

    view.add_regions(
        "jumper_quick_scope_line",
        underline_regions,
        scope=f"{scope} meta.quickscope meta.quickscope.current-line",
        flags=flags,
    )


def _quick_scope_regions_for_label(view, match_region, label, case_sensitive):
    text = view.substr(match_region)

    if not case_sensitive:
        text_to_search = text.lower()
        label_to_search = label.lower()
    else:
        text_to_search = text
        label_to_search = label

    regions = []
    start = 0

    for c in label_to_search:
        index = text_to_search.find(c, start)

        if index == -1:
            return None

        a = match_region.a + index
        regions.append(sublime.Region(a, a + 1))

        start = index + 1

    return regions
