import sublime
from unittesting import DeferrableTestCase

_code = """
def f(a=[1, 3], b={3, 4, [True]}):
    return a + [[x] or "[Dont jump here]" for x in b]
""".strip()


class TestDeferrable(DeferrableTestCase):
    def setUp(self):
        self.view = sublime.active_window().new_file()
        self.view.set_scratch(True)
        self.view.assign_syntax("Python.sublime-syntax")

    def test_select_bracket(self):
        self.view.run_command("insert", {"characters": _code})

        self.assertEqual(len(self.view.sel()), 1)
        self.assertEqual(self.view.sel()[0].to_tuple(), (92, 92))

        self.view.run_command(
            "jumper_select_next_bracket",
            {"direction": "previous", "extend": False, "brackets_text": "[]"},
        )
        self.assertEqual(len(self.view.sel()), 1)
        self.assertEqual(self.view.sel()[0].to_tuple(), (56, 57))

        self.view.run_command(
            "jumper_select_next_bracket",
            {"direction": "previous", "extend": False, "brackets_text": "[]"},
        )
        self.assertEqual(len(self.view.sel()), 1)
        self.assertEqual(self.view.sel()[0].to_tuple(), (55, 91))

        self.view.run_command(
            "jumper_select_next_bracket",
            {"direction": "previous", "extend": False, "brackets_text": "[]"},
        )
        self.assertEqual(len(self.view.sel()), 1)
        self.assertEqual(self.view.sel()[0].to_tuple(), (26, 30))

        self.view.run_command(
            "jumper_select_next_bracket",
            {"direction": "previous", "extend": False, "brackets_text": "{}"},
        )
        self.assertEqual(len(self.view.sel()), 1)
        self.assertEqual(self.view.sel()[0].to_tuple(), (19, 31))

        self.view.run_command(
            "jumper_select_next_bracket",
            {"direction": "previous", "extend": True, "brackets_text": "[]"},
        )
        self.assertEqual(len(self.view.sel()), 2)
        self.assertEqual(self.view.sel()[0].to_tuple(), (9, 13))
        self.assertEqual(self.view.sel()[1].to_tuple(), (19, 31))

        self.view.run_command(
            "jumper_select_next_bracket",
            {"direction": "next", "extend": True, "brackets_text": "[]"},
        )
        self.assertEqual(len(self.view.sel()), 3)
        self.assertEqual(self.view.sel()[0].to_tuple(), (9, 13))
        self.assertEqual(self.view.sel()[1].to_tuple(), (19, 31))
        self.assertEqual(self.view.sel()[2].to_tuple(), (55, 91))

        self.view.run_command(
            "jumper_select_next_bracket",
            {"direction": "previous", "extend": False, "brackets_text": "{}"},
        )
        self.assertEqual(len(self.view.sel()), 2)
        self.assertEqual(self.view.sel()[0].to_tuple(), (9, 13))
        self.assertEqual(self.view.sel()[1].to_tuple(), (19, 31))

        self.view.run_command(
            "jumper_select_next_bracket",
            {"direction": "next", "extend": False, "brackets_text": "{}"},
        )
        self.assertEqual(len(self.view.sel()), 1)
        self.assertEqual(self.view.sel()[0].to_tuple(), (19, 31))

        # Cursor just at the border of the (), should select the () content
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(6, 12))
        self.view.run_command(
            "jumper_select_next_bracket",
            {"direction": "previous", "extend": False, "brackets_text": "()"},
        )
        self.assertEqual(len(self.view.sel()), 1)
        self.assertEqual(self.view.sel()[0].to_tuple(), (6, 32))
        self.view.close()
