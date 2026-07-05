from collections import defaultdict


def _dedupe(seq):
    seen = set()
    out = []

    for x in seq:
        if x not in seen:
            out.append(x)
            seen.add(x)

    return out


def _matching(items, candidates_by_index):
    owner_by_label = {}
    label_by_index = {}

    def visit(index, seen):
        for label in candidates_by_index[index]:
            if label in seen:
                continue

            seen.add(label)

            old_owner = owner_by_label.get(label)

            if old_owner is None or visit(old_owner, seen):
                owner_by_label[label] = index
                label_by_index[index] = label
                return True

        return False

    order = sorted(
        [item["index"] for item in items],
        key=lambda index: len(candidates_by_index[index]),
    )

    for index in order:
        if not visit(index, set()):
            return None

    return label_by_index


def _suffix_chars_for_text(text, alphabet):
    """
    Preferred second/third/etc chars for a label.

    For:
        example

    this gives roughly:
        x, a, m, p, l, e, ...

    Then it falls back to the whole alphabet.
    """
    alphabet_set = set(alphabet)
    chars = []

    def add(c):
        if c in alphabet_set:
            chars.append(c)

    # Immediate next char: ex for example
    if len(text) >= 2:
        add(text[1])

    # Useful token chars: f + e from for_example
    separators = set("_-.:/\\[](){}\"' ")

    for i in range(1, len(text)):
        if text[i - 1] in separators:
            add(text[i])

    # Any later character in the word
    for c in text[1:]:
        add(c)

    # Final fallback: any jump key
    chars.extend(alphabet)

    return _dedupe(chars)


def _label_cost(label, text, alphabet_pos):
    """
    Smaller is better.

    Prefer:
    - shorter labels
    - chars that appear earlier in the matched text
    - alphabet order as fallback
    """
    score = 0

    for c in label[1:]:
        pos = text.find(c, 1)

        if pos >= 0:
            score += pos
        else:
            score += 1000 + alphabet_pos.get(c, 999)

    return len(label), score, label


def _make_leaf_pool(first, chars, needed):
    """
    Create prefix-free labels.

    Example, needed = 12, chars = a..z:

        ba, bb, bc, ... bz

    all 2 chars.

    Example, needed = 30, chars = a..z:

        most labels are b?
        only the overflow becomes b??

    This avoids making the whole bucket 3 chars.
    """
    chars = _dedupe(chars)

    if not chars:
        raise RuntimeError("No suffix chars available")

    if len(chars) == 1 and needed > 1:
        raise RuntimeError("Need at least 2 suffix chars for multiple labels")

    leaves = [first + c for c in chars]

    while len(leaves) < needed:
        # Expand the least-preferred shortest leaf.
        # This preserves as many short labels as possible.
        min_len = min(len(label) for label in leaves)

        expand_i = max(i for i, label in enumerate(leaves) if len(label) == min_len)

        prefix = leaves.pop(expand_i)

        children = [prefix + c for c in chars]

        leaves[expand_i:expand_i] = children

    return leaves


def make_prefix_free_labels(texts, alphabet, case_sensitive=True):
    """Assign a prefix-free label to each text, keyed by its index in `texts`."""
    alphabet = _dedupe(
        [c.lower() if not case_sensitive else c for c in alphabet if len(c) == 1]
    )

    alphabet_pos = {c: i for i, c in enumerate(alphabet)}

    items = []

    for i, text in enumerate(texts):
        if not text:
            continue

        if not case_sensitive:
            text = text.lower()

        items.append(
            {
                "index": i,
                "text": text,
                "first": text[0],
            }
        )

    root_buckets = defaultdict(list)

    for item in items:
        root_buckets[item["first"]].append(item)

    labels = {}

    for first, bucket in root_buckets.items():
        # Single target may use the first char alone.
        if len(bucket) == 1:
            labels[bucket[0]["index"]] = first
            continue

        # Multiple targets with same first char:
        # never use `b`, because then `bo`, `br`, etc would be ambiguous.
        chars = []

        for item in bucket:
            chars.extend(
                _suffix_chars_for_text(
                    item["text"],
                    alphabet,
                )
            )

        chars = _dedupe(chars)

        leaf_pool = _make_leaf_pool(
            first=first,
            chars=chars,
            needed=len(bucket),
        )

        candidates_by_index = {}

        for item in bucket:
            candidates_by_index[item["index"]] = sorted(
                leaf_pool,
                key=lambda label: _label_cost(
                    label,
                    item["text"],
                    alphabet_pos,
                ),
            )

        matched = _matching(
            bucket,
            candidates_by_index,
        )

        if matched is None:
            raise RuntimeError("Could not assign prefix-free labels")

        labels.update(matched)

    return labels
