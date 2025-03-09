import string
import json

filenames = [
    "Default (Linux).sublime-keymap",
    "Default (OSX).sublime-keymap",
    "Default (Windows).sublime-keymap",
]

shortcut_next = "alt+ctrl+super+2"
shortcut_previous = "alt+ctrl+super+1"


data = []
for c in string.printable:
    if not c.strip():
        continue
    char = c
    if c in "'\"":
        char = "'\""

    data += [
        {
            "keys": [shortcut_previous, c],
            "command": "select_next_char",
            "args": {
                "char": char,
                "direction": "previous",
            },
        },
        {
            "keys": [shortcut_next, c],
            "command": "select_next_char",
            "args": {"char": char},
        },
        {
            "keys": [shortcut_previous, "shift", c],
            "command": "select_next_char",
            "args": {
                "char": char,
                "direction": "previous",
            },
        },
        {
            "keys": [shortcut_next, "shift", c],
            "command": "select_next_char",
            "args": {"char": char},
        },
    ]

for filename in filenames:
    with open(filename, "w") as file:
        file.write(json.dumps(data))
