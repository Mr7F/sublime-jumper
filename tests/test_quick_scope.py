import sublime
from unittesting import DeferrableTestCase


class TestDeferrable(DeferrableTestCase):
    def setUp(self):
        self.view = sublime.active_window().new_file()
        self.view.set_scratch(True)

    def test_quick_scope(self):
        line = "This is a Test can you Type a char?"
        self.view.run_command("insert", {"characters": line})
        self.assertEqual(len(self.view.sel()), 1)
        self.assertEqual(self.view.sel()[0].to_tuple(), (35, 35))

        # Jump to beginning of Test
        self.view.run_command("jumper_quick_scope", {"character": "t", "extend": False})
        self.assertEqual(len(self.view.sel()), 1)
        self.assertEqual(self.view.sel()[0].to_tuple(), (23, 23))

        # Jump to beginning of Test
        self.view.run_command("jumper_quick_scope", {"character": "t", "extend": False})
        self.assertEqual(len(self.view.sel()), 1)
        self.assertEqual(self.view.sel()[0].to_tuple(), (23, 23))

        # Select until "you" included
        self.view.run_command(
            "jumper_quick_scope", {"character": "y", "extend": True, "included": True}
        )
        self.assertEqual(len(self.view.sel()), 1)
        self.assertEqual(self.view.sel()[0].to_tuple(), (23, 19))

        # Select until "This" non-included
        self.view.run_command(
            "jumper_quick_scope", {"character": "h", "extend": True, "included": False}
        )
        self.assertEqual(len(self.view.sel()), 1)
        self.assertEqual(self.view.sel()[0].to_tuple(), (19, 30))

        self.view.close()
