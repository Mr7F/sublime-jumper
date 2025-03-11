import string
import json

filenames = [
    "Default (Linux).sublime-keymap",
    "Default (OSX).sublime-keymap",
    "Default (Windows).sublime-keymap",
]

shortcut_previous = "alt+ctrl+super+3"
shortcut_next = "alt+ctrl+super+4"

shortcut_choose_location = "alt+ctrl+super+7"
shortcut_choose_location_extend = "shift+alt+ctrl+super+7"

shortcut_previous_extend = "shift+ctrl+alt+super+3"
shortcut_next_extend = "shift+ctrl+alt+super+4"

# Select the next / previous selection
shortcut_previous_selection = "alt+ctrl+super+1"
shortcut_next_selection = "alt+ctrl+super+2"

# Select the next / previous selection
shortcut_previous_selection_extend = "alt+ctrl+shift+super+1"
shortcut_next_selection_extend = "alt+ctrl+shift+super+2"

data = [
    {
        "keys": [shortcut_previous_selection],
        "command": "select_next_char_selection",
        "args": {"direction": "previous"},
    },
    {
        "keys": [shortcut_next_selection],
        "command": "select_next_char_selection",
    },
    {
        "keys": [shortcut_previous_selection_extend],
        "command": "select_next_char_selection",
        "args": {"direction": "previous", "keep_selection": True},
    },
    {
        "keys": [shortcut_next_selection_extend],
        "command": "select_next_char_selection",
        "args": {"keep_selection": True},
    },
]


def add_key(char, c):
    global data
    for previous, next, extend in (
        (shortcut_previous, shortcut_next, False),
        (shortcut_previous_extend, shortcut_next_extend, True),
    ):
        data += [
            {
                "keys": [previous, c],
                "command": "select_next_char",
                "args": {"char": char, "direction": "previous", "extend": extend},
            },
            {
                "keys": [next, c],
                "command": "select_next_char",
                "args": {"char": char, "extend": extend},
            },
            {
                "keys": [previous, "shift", c],
                "command": "select_next_char",
                "args": {"char": char, "direction": "previous", "extend": extend},
            },
            {
                "keys": [next, "shift", c],
                "command": "select_next_char",
                "args": {"char": char, "extend": extend},
            },
        ]

    for shortcut, extend in (
        (shortcut_choose_location, False),
        (shortcut_choose_location_extend, True),
    ):
        data += [
            {
                "keys": [shortcut, c],
                "command": "select_char_selection",
                "args": {"char": char, "extend": extend},
            },
            {
                "keys": [shortcut, "shift", c],
                "command": "select_char_selection",
                "args": {"char": char, "extend": extend},
            },
        ]


if __name__ == "__main__":
    for c in string.printable:
        if c.strip():
            add_key(c, c)

    # https://www.sublimetext.com/docs/key_bindings.html#key-names
    for key, char in [
        ("plus", "+"),
        ("keypad_plus", "+"),
        ("keypad_multiply", "*"),
        ("keypad_minus", "-"),
        ("keypad_divide", "/"),
        ("keypad_period", "."),
    ]:
        # sublime.log_input(True)
        add_key(char, key)

    for i in range(10):
        add_key(str(i), "keypad" + str(i))

    for filename in filenames:
        with open(filename, "w") as file:
            file.write(json.dumps(data))
