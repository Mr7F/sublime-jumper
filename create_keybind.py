import string
import json

filenames = [
    "Default (Linux).sublime-keymap",
    "Default (OSX).sublime-keymap",
    "Default (Windows).sublime-keymap",
]

shortcut_previous = "alt+ctrl+shift+super+1"
shortcut_next = "alt+ctrl+shift+super+2"

# Select the next / previous selection
shortcut_previous_selection = "alt+ctrl+super+1"
shortcut_next_selection = "alt+ctrl+super+2"

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
]


def add_key(char, c):
    global data
    data += [
        {
            "keys": [shortcut_previous, c],
            "command": "select_next_char",
            "args": {"char": char, "direction": "previous"},
        },
        {
            "keys": [shortcut_next, c],
            "command": "select_next_char",
            "args": {"char": char},
        },
        {
            "keys": [shortcut_previous, "shift", c],
            "command": "select_next_char",
            "args": {"char": char, "direction": "previous"},
        },
        {
            "keys": [shortcut_next, "shift", c],
            "command": "select_next_char",
            "args": {"char": char},
        },
    ]


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
