# Sublime - Select Next Char
Press a shortcut, then a key to select the next / previous character corresponding to the key pressed.

Because of the way shortcut work in sublime, you need to run `create_keybind.py` in order to generate the shortcut file.

An other shortcut can select the next / previous text matching the current selection.


Taking inspiration from [EasyMotion](https://github.com/tednaleid/sublime-EasyMotion), it's also possible to press a shortcut,
followed by a key, to highlight all matching character with a small label. Pressing the label jump to that position.
In that mode, you can press
- "space" then the label to select everything between the cursor and the target label excluded (the color will change)
- "tab" then the label to select everything between the cursor and the target label included (the color will change)

Example:
- `<shortcut> + a + x`: jump to the "a" labelled "x"
- `<shortcut> + a + " " + x`: select between the cursor and the "a" labelled "x" ("a" excluded)
- `<shortcut> + a + "tab" + x`: select between the cursor and the "a" labelled "x" ("a" included)
- `<shortcut> + " " + x`: jump to the beginning of the non-empty line labelled "x"

If the charset is not big enough, you can press many keys to jump where you want.

[![Demo](https://img.youtube.com/vi/AVkC4VIXuBY/maxresdefault.jpg)](https://www.youtube.com/watch?v=AVkC4VIXuBY)

Settings
```json
{
    "select_next_char_charset": "tnseriaogmdhc,x.plfuwyvkbj:z123456789TNSERIAOGMDHCXPLFUWYVKBJ{}@%$&!#|^'-_=/;()"
}
```

You can type
- space to jump at the beginning of non-empty line
- tab to jump at the end of non-empty line

The jump work when many files are open (but not the extend, because we can not edit 2 files at the same time).

# Technical
Sublime text doesn't support "phantom on top of text", so the default implementation use HTML sheet, but you can change in the code if
you prefer something else:
- phantoms: the text will shift to the right
- buffer: we will change the buffer, but the "redo" history can not be cleaned
- popup: we show a popup, but you will see a shadow and you can not jump to the first line
- sheet: the default implementation, only drawback is that when you are in "label typing" mode, you can not select text with the mousse
