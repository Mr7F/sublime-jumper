import importlib

import sublime
from unittesting import DeferrableTestCase


_package = __package__.split(".")[0] if __package__ else "sublime-jumper"
navigation = importlib.import_module(_package + ".utils")


class TestDeferrable(DeferrableTestCase):
    def setUp(self):
        self.view = sublime.active_window().new_file()
        self.view.set_scratch(True)
        self.view.run_command("insert", {"characters": "abcdefg"})

    def tearDown(self):
        self.view.close()

    def test_frontier_uses_merged_native_selection(self):
        retained = sublime.Region(0, 4)
        origin = sublime.Region(6)
        target = sublime.Region(3, 7)

        self.view.sel().clear()
        self.view.sel().add_all([retained, origin])

        navigation.apply_selection_targets(
            self.view,
            [origin],
            [target],
        )

        self.assertEqual(
            [region.to_tuple() for region in self.view.sel()],
            [(0, 7)],
        )
        self.assertEqual(
            [
                region.to_tuple()
                for region in self.view.get_regions("jumper-selection-frontier")
            ],
            [(0, 7)],
        )
