import sublime
import sublime_plugin


_FRONTIER_REGIONS = "jumper-selection-frontier"
_FRONTIER_INDICATORS = "jumper-selection-frontier-indicators"
_FRONTIER_REVISION = "jumper_selection_frontier_revision"


def same_region(left, right):
    """Compare selection bounds without transient Region metadata."""
    return left.begin() == right.begin() and left.end() == right.end()


def clear_frontier(view):
    view.erase_regions(_FRONTIER_REGIONS)
    view.erase_regions(_FRONTIER_INDICATORS)
    _advance_frontier_revision(view)


def get_frontier(view):
    """Return the selections which should advance on the next navigation."""
    frontier = view.get_regions(_FRONTIER_REGIONS)
    if not frontier:
        return None

    if any(
        not any(same_region(region, selection) for selection in view.sel())
        for region in frontier
    ):
        clear_frontier(view)
        return None

    return frontier


def set_frontier(view, regions, scope="region.greenish"):
    """Persist and display the selections which form the navigation frontier."""
    regions = list(regions)
    if not regions:
        clear_frontier(view)
        return

    # Keep the complete regions in a hidden region set. Unlike Python Region
    # objects, Sublime updates these positions when the buffer changes.
    view.add_regions(
        _FRONTIER_REGIONS,
        regions,
        flags=sublime.HIDDEN,
    )
    view.add_regions(
        _FRONTIER_INDICATORS,
        regions,
        scope=scope,
        icon="dot",
        flags=(
            sublime.HIDE_ON_MINIMAP
            | sublime.DRAW_EMPTY
            | sublime.DRAW_NO_FILL
            | sublime.DRAW_NO_OUTLINE
        ),
    )
    _advance_frontier_revision(view)


def get_frontier_revision(view):
    return view.settings().get(_FRONTIER_REVISION, 0)


def _advance_frontier_revision(view):
    view.settings().set(_FRONTIER_REVISION, get_frontier_revision(view) + 1)


class SelectionFrontierListener(sublime_plugin.ViewEventListener):
    """Clear the navigation frontier after its selections are changed.

    Other selections may be retained, but every frontier selection must remain
    present for the next navigation command to advance it.
    """

    def on_selection_modified(self):
        get_frontier(self.view)
