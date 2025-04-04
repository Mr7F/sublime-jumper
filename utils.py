import re

a = 1


def get_next_element(html, index):
    # Return the size of the next element (in HTML code and in inner text)
    if html[index] == "<":
        m = re.match(r"^<.*?>", html[index:])
        if "<br" in m.group(0).lower():
            return m.end(), 1
        return m.end(), 0
    if html[index] == "&":
        return re.match(r"^&.*?;", html[index:]).end(), 1
    return 1, 1


def get_element_html_positions(html, indexes):
    # Return the index in the HTML code of the given text
    indexes = sorted(indexes)
    text_index = 0
    i = 0

    found = {}

    for index in indexes:
        while True:
            if i >= len(html):
                return found

            html_size, text_size = get_next_element(html, i)

            if text_index == index and text_size:
                found[index] = (i, html_size)
                i += html_size
                text_index += text_size
                break

            if text_index > index:
                break

            i += html_size
            text_index += text_size

    return found


def get_element_html_position(html, index):
    return get_element_html_positions(html, [index])[index]
