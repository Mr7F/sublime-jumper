# Sublime - Jumper
## Quick Jump
Taking inspiration from [Quick Scope](https://github.com/unblevable/quick-scope),
the command `jumper_quick_jump`, go to the next / previous occurrence of the character that start a word.

You can also extend the selection up to the next / previous occurrence of the character that start a word.

The settings `"jumper_quick_jump_show_word_bounds": true,` will show the characters where you can jump to with that command
(only on the current line by default, to show them all, set `jumper_quick_jump_show_all_lines` to true).

You can also just jump to the next / previous occurrence of the character even if it does not start a word (character included).

## Go To Anywhere
Taking inspiration from [EasyMotion](https://github.com/tednaleid/sublime-EasyMotion) and [Ace Jump](https://github.com/acejump/AceJump) it's also possible to press a shortcut,
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
    "jumper_go_to_anywhere_charset": "tnseriaogmdhc,x.plfuwyvkbj:z123456789TNSERIAOGMDHCXPLFUWYVKBJ{}@%$&!#|^'-_=/;()"
}
```

You can type
- space to jump at the beginning of non-empty line
- tab to jump at the end of non-empty line

The jump work when many files are open (but not the extend, because we can not edit 2 files at the same time).

## Technical
Sublime text doesn't support "phantom on top of text", so the default implementation use HTML sheet, but you can change in the code if
you prefer something else:
- phantoms: the text will shift to the right
- buffer: we will change the buffer, but the "redo" history can not be cleaned
- popup: we show a popup, but you will see a shadow and you can not jump to the first line
- sheet: the default implementation, only drawback is that when you are in "label typing" mode, you can not select text with the mousse

# Select Next Selection Match
The command `select_next_same_selection` will select the next / previous text matching the current selection
(you can also add it to the current selection, and it will be the same as `find_under_expand`).

# Quick Scope
Taking inspiration from [Quick Scope](https://github.com/unblevable/quick-scope), each words get labelled by one letter inside of it,
pressing a shortcut and then that letter will jump at the *start* of the word.

```
this is a test
|    |  |  |

```
- `<shortcut> t`: jump to *start* of "this"
- `<shortcut> i`: jump to *start* of "is"
- `<shortcut> e`: jump to *start* of "test"

To enable the highlight, set the settings `jumper_quick_scope` to true. Or, if you want to enable the feature only for the current line, set it to `"line"`.

In comparison to "Quick Jump", there's no direction, it will try to cover as many word as possible and the label is not necessary the
first letter of the word.

You can also select until the matching word (that word included).

# TODO
- Remove `create_keybind.py` and add keybind in the readme once https://github.com/sublimehq/sublime_text/issues/6650 is fixed
- Find a way to add letter as row number to jump faster
- "Go To Anywhere", when clicking on a tab, the input panel should close
- "Go To Anywhere", read `word_wrap` settings (set to "auto")
