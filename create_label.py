from collections import defaultdict


_SEPARATORS = set("_-.:/\\[](){}\"' ")


def _dedupe(seq):
    seen = set()
    out = []

    for x in seq:
        if x not in seen:
            out.append(x)
            seen.add(x)

    return out


def _item_priority(item, alphabet_set):
    """Less-specific items go first.

    The augmenting matcher lets later items steal labels from earlier items.
    So plain "1" runs before "1a", allowing "1a" to reclaim good labels.
    """
    useful_suffix_chars = {c for c in item["text"][1:] if c in alphabet_set}

    return (
        len(useful_suffix_chars),
        len(item["text"]),
        item["index"],
    )


def _matching(items, candidates_by_index, label_count, alphabet_set):
    """Augmenting-path matching using integer label IDs."""
    owner_by_label = [-1] * label_count
    label_by_index = {}

    seen = [0] * label_count
    seen_token = 0

    def visit(start_index, cursor_by_candidates):
        # Stack of pending reassignments:
        # if the search succeeds, each `(index, label_id)` is applied while
        # unwinding, just like the recursive version.
        stack = []
        index = start_index

        while True:
            candidates = candidates_by_index[index]
            candidates_key = id(candidates)

            pos = cursor_by_candidates.get(candidates_key, 0)
            descended = False

            while pos < len(candidates):
                label_id = candidates[pos]
                pos += 1
                cursor_by_candidates[candidates_key] = pos

                if seen[label_id] == seen_token:
                    continue

                seen[label_id] = seen_token

                old_owner = owner_by_label[label_id]

                if old_owner == -1:
                    # Found a free label. Assign it to the current item.
                    owner_by_label[label_id] = index
                    label_by_index[index] = label_id

                    # Reassign the path back to the start item.
                    while stack:
                        previous_index, previous_label_id = stack.pop()
                        owner_by_label[previous_label_id] = previous_index
                        label_by_index[previous_index] = previous_label_id

                    return True

                # Try to move the old owner somewhere else.
                stack.append((index, label_id))
                index = old_owner
                descended = True
                break

            if descended:
                continue

            # Current item could not be moved. Backtrack to the previous item
            # and continue after the label that led here.
            if not stack:
                return False

            index, _label_id = stack.pop()

    order = [
        item["index"]
        for item in sorted(
            items,
            key=lambda item: _item_priority(item, alphabet_set),
        )
    ]

    for index in order:
        seen_token += 1
        cursor_by_candidates = {}

        if not visit(index, cursor_by_candidates):
            return None

    return label_by_index


def _suffix_chars_for_text(text, alphabet, alphabet_set):
    """
    Preferred second/third/etc chars for a label.

    For:
        example

    this gives roughly:
        x, a, m, p, l, e, ...

    Then it falls back to the whole alphabet.
    """
    seen = set()
    chars = []

    def add(c):
        if c in alphabet_set and c not in seen:
            chars.append(c)
            seen.add(c)

    # Immediate next char: ex for example
    if len(text) >= 2:
        add(text[1])

    # Useful token chars: f + e from for_example
    for i in range(1, len(text)):
        if text[i - 1] in _SEPARATORS:
            add(text[i])

    # Any later character in the word
    for c in text[1:]:
        add(c)

    # Final fallback: any jump key
    for c in alphabet:
        add(c)

    return chars


def _char_costs_for_text(text, alphabet_pos):
    """
    Precompute per-char costs for one text.

    This replaces repeated:

        text.find(c, 1)

    inside candidate sorting.
    """
    costs = {c: 1000 + pos for c, pos in alphabet_pos.items()}

    seen = set()

    for pos, c in enumerate(text[1:], start=1):
        if c in costs and c not in seen:
            costs[c] = pos
            seen.add(c)

    return costs


def _label_cost(label_info, char_costs):
    """
    Smaller is better.

    Prefer:
    - shorter labels
    - chars that appear earlier in the matched text
    - alphabet order as fallback
    """
    _label_id, label, label_len, suffix = label_info

    score = 0

    for c in suffix:
        score += char_costs[c]

    return label_len, score, label


def _candidate_label_ids(leaf_infos, item):
    """Return this item's candidate label IDs, sorted by preference."""
    return tuple(
        label_id
        for label_id, _label, _label_len, _suffix in sorted(
            leaf_infos,
            key=lambda label_info: _label_cost(
                label_info,
                item["char_costs"],
            ),
        )
    )


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


def _match_bucket(bucket, leaf_pool, alphabet_set):
    """Build candidates and run matching."""
    leaf_infos = [
        (label_id, label, len(label), label[1:])
        for label_id, label in enumerate(leaf_pool)
    ]

    candidates_by_index = {}
    candidates_cache = {}

    for item in bucket:
        # Many pathological cases have hundreds of identical texts like "1".
        # Their sorted candidate lists are identical, so compute once.
        candidates = candidates_cache.get(item["text"])

        if candidates is None:
            candidates = _candidate_label_ids(
                leaf_infos,
                item,
            )
            candidates_cache[item["text"]] = candidates

        candidates_by_index[item["index"]] = candidates

    matched = _matching(
        bucket,
        candidates_by_index,
        len(leaf_infos),
        alphabet_set,
    )

    if matched is None:
        raise RuntimeError("Could not assign prefix-free labels")

    return {index: leaf_pool[label_id] for index, label_id in matched.items()}


def make_prefix_free_labels(texts, alphabet, case_sensitive=True):
    """Assign a prefix-free label to each text, keyed by its index in `texts`."""
    alphabet = _dedupe(
        [c.lower() if not case_sensitive else c for c in alphabet if len(c) == 1]
    )

    alphabet_set = set(alphabet)
    alphabet_pos = {c: i for i, c in enumerate(alphabet)}

    char_costs_cache = {}
    items = []

    for i, text in enumerate(texts):
        if not text:
            continue

        if not case_sensitive:
            text = text.lower()

        char_costs = char_costs_cache.get(text)

        if char_costs is None:
            char_costs = _char_costs_for_text(text, alphabet_pos)
            char_costs_cache[text] = char_costs

        items.append(
            {
                "index": i,
                "text": text,
                "first": text[0],
                "char_costs": char_costs,
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
        # never use `first` alone, because then `first + something`
        # would be ambiguous.
        chars = []

        for item in bucket:
            chars.extend(
                _suffix_chars_for_text(
                    item["text"],
                    alphabet,
                    alphabet_set,
                )
            )

        leaf_pool = _make_leaf_pool(
            first=first,
            chars=chars,
            needed=len(bucket),
        )

        labels.update(
            _match_bucket(
                bucket,
                leaf_pool,
                alphabet_set,
            )
        )

    return labels

