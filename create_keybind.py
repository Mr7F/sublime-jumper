import string
import json

filenames = [
    "Default (Linux).sublime-keymap",
    "Default (OSX).sublime-keymap",
    "Default (Windows).sublime-keymap",
]

shortcut_previous = "alt+ctrl+super+1"
shortcut_next = "alt+ctrl+super+2"

# Select the next / previous selection
shortcut_previous_selection = "alt+ctrl+shift+super+1"
shortcut_next_selection = "alt+ctrl+shift+super+2"

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

for c in string.printable:
    if not c.strip():
        continue

    data += [
        {
            "keys": [shortcut_previous, c],
            "command": "select_next_char",
            "args": {
                "char": c,
                "direction": "previous",
            },
        },
        {
            "keys": [shortcut_next, c],
            "command": "select_next_char",
            "args": {"char": c},
        },
        {
            "keys": [shortcut_previous, "shift", c],
            "command": "select_next_char",
            "args": {
                "char": c,
                "direction": "previous",
            },
        },
        {
            "keys": [shortcut_next, "shift", c],
            "command": "select_next_char",
            "args": {"char": c},
        },
    ]

for filename in filenames:
    with open(filename, "w") as file:
        file.write(json.dumps(data))
