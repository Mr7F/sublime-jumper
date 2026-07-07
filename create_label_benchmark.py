import random
import statistics
import time
from .create_label import make_prefix_free_labels


def _benchmark_case(name, texts, alphabet="abcdefghijklmnopqrstuvwxyz", repeat=20):
    # Warmup
    make_prefix_free_labels(
        texts=texts,
        alphabet=alphabet,
        case_sensitive=False,
    )

    times = []

    for _ in range(repeat):
        start = time.perf_counter()

        labels = make_prefix_free_labels(
            texts=texts,
            alphabet=alphabet,
            case_sensitive=False,
        )

        elapsed = time.perf_counter() - start
        times.append(elapsed)

        assert len(labels) == len(texts)

    print(
        f"{name}: "
        f"n={len(texts)}, "
        f"min={min(times) * 1000:.2f}ms, "
        f"avg={statistics.mean(times) * 1000:.2f}ms, "
        f"max={max(times) * 1000:.2f}ms"
    )


def benchmark_make_prefix_free_labels():
    alphabet = "abcdefghijklmnopqrstuvwxyz"

    # Normal case:
    # mixed first letters, realistic code-ish identifiers.
    normal_words = [
        "Component",
        "CheckBox",
        "DomainSelectorDialog",
        "SelectMenu",
        "useService",
        "Property",
        "template",
        "components",
        "defaultProps",
        "childProps",
        "class",
        "props",
        "name",
        "type",
        "value",
        "onChange",
        "isReadonly",
        "slots",
        "tooltip",
        "inputAttributes",
    ]

    normal = [f"{word}{i}" for i in range(20) for word in normal_words]

    # Shuffle so we do not accidentally benchmark a too-friendly order.
    random.Random(0).shuffle(normal)

    # Worst case:
    # many matches in the same first-letter bucket, with many repeated texts.
    # This stresses candidate caching and matching.
    worst_line = [
        "1",
        "1",
        "1",
        "1",
        "11",
        "1",
        "1",
        "1",
        "1\\",
        "1",
        "1",
        "1a",
        "1",
        "1",
    ]

    _benchmark_case(
        "normal",
        normal,
        alphabet=alphabet,
        repeat=20,
    )

    _benchmark_case(
        "worst",
        worst_line * 80,
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789\\",
        repeat=20,
    )

    odoo_doc = """
        write vals

        Updates all records in self with the provided values.

        param dict vals fields to update and the value to set on them
        raise AccessError if user is not allowed to modify the specified records fields
        raise ValidationError if invalid values are specified for selection fields
        raise UserError if a loop would be created in a hierarchy of objects
        a result of the operation such as setting an object as its own parent

        For numeric fields Integer Float the value should be of the corresponding type
        For Boolean the value should be a bool
        For Selection the value should match the selection values generally str sometimes int
        For Many2one the value should be the database identifier of the record to set
        The expected value of a One2many or Many2many relational field is a list of Command
        that manipulate the relation they implement There are a total of 7 commands
        Command create
        Command update
        Command delete
        Command unlink
        Command link
        Command clear
        Command set
        For Date and Datetime the value should be either a date time or a string
        warning
        If a string is provided for Date time fields
        it must be UTC only and formatted according to DEFAULT_SERVER_DATE_FORMAT
        and DEFAULT_SERVER_DATETIME_FORMAT
        Other non relational fields use a string for value
    """.split()

    _benchmark_case(
        "odoo-doc",
        odoo_doc,
        alphabet=alphabet,
        repeat=20,
    )

    js_drag = """
        elements:
            this.renderedColumnsCount === 1
                ? "*:is(.o_property_field, .o_field_property_group_label)"
                : ".o_property_field",
        groups: ".o_property_group",
        connectGroups: true,
        cursor: "grabbing",
        onDragStart: ({ element, group }) => {
            this.propertiesRef.el.classList.add("o_property_dragging");
            element.classList.add("o_property_drag_item");
            group.classList.add("o_property_drag_group");
            // without this, if we edit a char property, move it,
            // the change will be reset when we drop the property
            document.activeElement.blur();
        },
        onDrop: async ({ parent, element, next, previous }) => {
            const from = element.getAttribute("property-name");
            let to = previous && previous.getAttribute("property-name");
            let moveBefore = false;
            if (!to && next) {
                // we move the element at the first position inside a group
                // or at the first position of a column
                if (next.classList.contains("o_field_property_group_label")) {
                    // mono-column layout, move before the separator
                    next = next.closest(".o_property_group");
                }
                to = next.getAttribute("property-name");
                moveBefore = !!to;
            }
            if (!to) {
                // we move in an empty group or outside of the DOM element
                // move the element at the end of the group
                const groupName = parent.getAttribute("property-name");
                const group = this.groupedPropertiesList.find(
                    (group) => group.name === groupName
                );
                if (!group) {
                    to = null;
                    moveBefore = false;
                } else {
                    to = group.elements.length ? group.elements.at(-1).name : groupName;
                }
            }
            await this.onPropertyMoveTo(from, to, moveBefore);
        },
    """
    import re

    js_drag_words = re.findall(
        r"[A-Za-z_][A-Za-z0-9_]*",
        js_drag,
    )
    _benchmark_case(
        "js-drag",
        js_drag_words,
        alphabet=alphabet,
        repeat=20,
    )


def _assert_labels_valid(texts, alphabet="abcdefghijklmnopqrstuvwxyz"):
    labels = make_prefix_free_labels(
        texts=texts,
        alphabet=alphabet,
        case_sensitive=False,
    )

    values = list(labels.values())
    assert len(values) == len(set(values)) == len(texts)
    for index, text in enumerate(texts):
        # Hard rule, the first letter of the word should be the first letter of the label
        assert labels[index].startswith(text[0].lower())

    for label in values:
        for other in values:
            if label != other:
                assert not other.startswith(label)

    return labels


if __name__ == "__main__":
    texts = ["accccccc", "bccccccc", "cccccccc", "daccccccc", "eaccccccc"]
    labels = _assert_labels_valid(texts)
    assert labels.get(0) == "a"
    assert labels.get(1) == "b"
    assert labels.get(2) == "c"
    assert labels.get(3) == "d"
    assert labels.get(4) == "e"

    # when 2 words start with the same letter, no one can get that letter as label
    texts = ["SelectMenu", "slots"]
    labels = _assert_labels_valid(texts)
    assert labels.get(0) == "se"
    assert labels.get(1) == "sl"

    # prefer the second letter
    texts = ["select", "slots", "static"]
    labels = _assert_labels_valid(texts)
    assert labels[0] == "se"
    assert labels[1] == "sl"
    assert labels[2] == "st"

    # when the preferred second letter conflicts, one word gets it,
    # the other falls back to another useful letter
    texts = ["static", "String"]
    labels = _assert_labels_valid(texts)
    assert set(labels.values()) in ({"st", "sa"}, {"st", "sr"})

    # complex case: `se` should not be skipped just because multiple words start with `se`
    texts = ["SelectMenu", "SelectMenu", "slots", "static", "String"]
    labels = _assert_labels_valid(texts)
    assert all(label.startswith("s") for label in labels.values())
    # "sm" reads as Select*M*enu since the camelCase boundary boost
    assert labels.get(0) in ("se", "sm", "sl", "sc")
    assert labels.get(1) in ("se", "sm", "sl", "sc")
    assert "se" in (labels.get(0), labels.get(1))
    assert labels.get(texts.index("slots")) in ("so", "sl", "st")
    assert labels.get(texts.index("static")) in ("st", "sa")
    assert labels.get(texts.index("String")) in ("st", "sr")

    # boost after word boundary
    texts = ["foo_bar", "foo_baz"]
    labels = _assert_labels_valid(texts)
    assert set(labels.values()) == {"fo", "fb"}

    # more labels than the alphabet can build, make label bigger
    texts = ["aa", "ab", "ac"]
    labels = _assert_labels_valid(texts, alphabet="ab")
    assert len(labels) == 3
    assert all(label.startswith("a") for label in labels.values())
    assert max(len(label) for label in labels.values()) > 2
    assert sorted([len(label) for label in labels.values()]) == [2, 3, 3]

    # fallback to the alphabet order when the chars are not in the alphabet
    texts = ["sXYZ", "SUVW"]
    labels = _assert_labels_valid(texts, alphabet="sabc")
    assert set(labels.values()) == {"sa", "ss"}

    # duplicate text get unique label
    texts = ["SelectMenu", "SelectMenu", "SelectMenu"]
    labels = _assert_labels_valid(texts)
    assert len(set(labels.values())) == 3
    assert all(label.startswith("s") for label in labels.values())
    assert any(label == "se" for label in labels.values())

    # case where short label can conflict with long label
    # check that label are leave in the tree
    texts = ["aa", "ab", "ac", "ad"]
    labels = _assert_labels_valid(texts, alphabet="ab")
    values = set(labels.values())
    assert "a" not in values
    assert all(label.startswith("a") for label in values)
    for label in values:
        for other in values:
            if label != other:
                assert not other.startswith(label)

    benchmark_make_prefix_free_labels()
