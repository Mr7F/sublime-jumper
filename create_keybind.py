import json
import string

filenames = [
    # "Default.sublime-keymap",
]

shortcut_choose_location = "alt+ctrl+super+find"
shortcut_choose_location_extend = "shift+alt+ctrl+super+find"

data = []


def add_key(character, c):
    global data

    for shortcut, extend in (
        (shortcut_choose_location, False),
        (shortcut_choose_location_extend, True),
    ):
        data += [
            {
                "keys": [shortcut, c],
                "command": "jumper_go_to_anywhere",
                "args": {"character": character, "extend": extend},
            },
            {
                "keys": [shortcut, "shift", c],
                "command": "jumper_go_to_anywhere",
                "args": {"character": character, "extend": extend},
            },
        ]


if __name__ == "__main__":
    for c in string.printable:
        if c.strip():
            add_key(c, c)

    add_key(" ", " ")
    add_key("\t", "tab")
    add_key("enter", "enter")

    # https://www.sublimetext.com/docs/key_bindings.html#key-names
    for key, character in [
        ("plus", "+"),
        ("keypad_plus", "+"),
        ("keypad_multiply", "*"),
        ("keypad_minus", "-"),
        ("keypad_divide", "/"),
        ("keypad_period", "."),
    ]:
        # sublime.log_input(True)
        add_key(character, key)

    for i in range(10):
        add_key(str(i), "keypad" + str(i))

    for filename in filenames:
        with open(filename, "w") as file:
            file.write(json.dumps(data))
