from collections import defaultdict

# AI generated

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
    """Weakest claims go first.

    The augmenting matcher lets later items steal labels from earlier items,
    so the last processed item has the strongest claim on its preferred label.

    - Items whose text offers no (or one) useful suffix char run first: they
      are indifferent, so anything more specific may steal from them
      (plain "1" runs before "1a", allowing "1a" to reclaim "1a").
    - The count is capped: beyond "a couple of options" more useful chars do
      not make a claim weaker, and the cap lets proximity decide instead.
    - `matches` arrive sorted by distance to the cursor, so a smaller index is
      a closer match: process it last so it wins contested labels.
    """
    useful_suffix_chars = {c for c in item["text"][1:] if c in alphabet_set}

    return (
        min(len(useful_suffix_chars), 2),
        -item["index"],
    )


def _matching(items, candidates_by_index, label_count, alphabet_set):
    """Augmenting-path matching using integer label IDs.

    Items sharing the same candidates tuple (same "class") are
    interchangeable: stealing a label from a same-class owner just swaps two
    identical roles and never improves the outcome. So each class keeps a
    persistent watermark: the prefix of its candidate list observed to be
    owned by class members, which every search skips.

    The watermark only ever advances. A later cross-class steal can punch a
    hole below it; skipping the hole is harmless for quality (the hole's new
    owner out-prioritized us) and completeness is restored by the full-rescan
    fallback below.
    """
    owner_by_label = [-1] * label_count
    label_by_index = {}

    # Intern the candidate tuples: the cache in `_match_bucket` guarantees
    # items with equal candidates share one tuple object.
    tid_by_obj = {}
    tuples = []
    tid_by_index = {}

    for index, cand in candidates_by_index.items():
        key = id(cand)
        tid = tid_by_obj.get(key)

        if tid is None:
            tid = len(tuples)
            tid_by_obj[key] = tid
            tuples.append(cand)

        tid_by_index[index] = tid

    ntuples = len(tuples)
    watermark = [0] * ntuples

    seen = [0] * label_count
    seen_token = 0

    def visit(start_index, cursors):
        # Stack of pending reassignments:
        # if the search succeeds, each `(index, label_id)` is applied while
        # unwinding, just like the recursive version.
        # `cursors` holds one scan position per class, shared by every item
        # of that class touched during this search.
        stack = []
        index = start_index
        tid = tid_by_index[index]

        while True:
            candidates = tuples[tid]
            n = len(candidates)
            pos = cursors[tid]
            descended = False

            while pos < n:
                label_id = candidates[pos]
                pos += 1

                if seen[label_id] == seen_token:
                    continue

                seen[label_id] = seen_token
                old_owner = owner_by_label[label_id]
                cursors[tid] = pos

                if old_owner == -1:
                    # Found a free label. Assign it to the current item,
                    # then reassign the path back to the start item.
                    owner_by_label[label_id] = index
                    label_by_index[index] = label_id

                    while stack:
                        prev_index, prev_label_id = stack.pop()
                        owner_by_label[prev_label_id] = prev_index
                        label_by_index[prev_index] = prev_label_id

                    return True

                # Try to move the old owner somewhere else.
                stack.append((index, label_id))
                index = old_owner
                tid = tid_by_index[index]
                descended = True
                break

            if descended:
                continue

            cursors[tid] = pos

            # Current item could not be moved. Backtrack to the previous item
            # and continue after the label that led here.
            if not stack:
                return False

            index, _label_id = stack.pop()
            tid = tid_by_index[index]

    def redistribute():
        """Give the best label of each class to its closest member.

        Class members are interchangeable during matching, so which member
        got which label is arbitrary. Their texts are identical, only
        proximity distinguishes them: smaller index = closer to the cursor.
        """
        members_by_tid = {}

        for index, tid in tid_by_index.items():
            members_by_tid.setdefault(tid, []).append(index)

        for tid, members in members_by_tid.items():
            if len(members) < 2:
                continue

            rank = {label_id: pos for pos, label_id in enumerate(tuples[tid])}
            owned = sorted(
                (label_by_index[index] for index in members),
                key=rank.__getitem__,
            )

            for index, label_id in zip(sorted(members), owned):
                label_by_index[index] = label_id
                owner_by_label[label_id] = index

    order = [
        item["index"]
        for item in sorted(
            items,
            key=lambda item: _item_priority(item, alphabet_set),
        )
    ]

    for index in order:
        tid = tid_by_index[index]
        cand = tuples[tid]
        w = watermark[tid]
        n = len(cand)

        # Advance the class watermark past labels owned by classmates.
        while w < n:
            o = owner_by_label[cand[w]]

            if o == -1 or tid_by_index[o] != tid:
                break

            w += 1

        watermark[tid] = w

        seen_token += 1

        if not visit(index, watermark[:]):
            # Safety net: full rescan without the watermark shortcut.
            seen_token += 1

            if not visit(index, [0] * ntuples):
                return None

    redistribute()

    return label_by_index


def _word_boundaries(original):
    """Positions starting a new word, on the original (pre-lowercase) text.

    For:
        on_dragStart

    this gives the positions of `d` and `S`: after a separator or at a
    camelCase hump.
    """
    positions = []

    for i in range(1, len(original)):
        if original[i - 1] in _SEPARATORS or (
            original[i].isupper() and not original[i - 1].isupper()
        ):
            positions.append(i)

    return positions


def _suffix_chars_for_text(text, boundaries, alphabet, alphabet_set):
    """
    Preferred second/third/etc chars for a label.

    For:
        exampleWord

    this gives roughly:
        x, w, a, m, p, l, e, ...

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

    # Word-start chars: f + e from for_example, o + d from onDrag
    for i in boundaries:
        add(text[i])

    # Any later character in the word
    for c in text[1:]:
        add(c)

    # Final fallback: any jump key
    for c in alphabet:
        add(c)

    return chars


def _char_costs_for_text(text, boundaries, alphabet_pos):
    """
    Precompute per-char costs for one text. Smaller is better.

    The immediate next char stays the best choice ("se" for "select"),
    then chars starting a word: "DomainSelectorDialog" reads better as
    "ds" than as "dm". Other chars cost their position in the text, and
    chars absent from the text fall back to the alphabet order.
    """
    costs = {c: 1000 + pos for c, pos in alphabet_pos.items()}
    seen = set()

    if len(text) >= 2 and text[1] in costs:
        costs[text[1]] = 1
        seen.add(text[1])

    for nth, i in enumerate(boundaries):
        c = text[i]

        if c in costs and c not in seen:
            costs[c] = 2 + nth
            seen.add(c)

    # Plain chars never cost less than the boundary chars.
    floor = 2 + len(boundaries)

    for pos, c in enumerate(text[1:], start=1):
        if c in costs and c not in seen:
            costs[c] = max(pos, floor)
            seen.add(c)

    return costs


def _label_cost(label_info, char_costs):
    """
    Smaller is better.

    Prefer:
    - shorter labels
    - chars that appear earlier in the matched text (word starts first)
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
        # Key the cache by the char-cost signature, not the text:
        # identical texts share it, but so do "Component0" and "Component7",
        # which differ only in chars outside the alphabet. The shared tuple
        # object is also what `_matching` uses to group interchangeable items.
        candidates = candidates_cache.get(item["cost_sig"])

        if candidates is None:
            candidates = _candidate_label_ids(
                leaf_infos,
                item,
            )
            candidates_cache[item["cost_sig"]] = candidates

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

        # Word boundaries come from the original text: lowercasing first
        # would erase the camelCase humps.
        original = text

        if not case_sensitive:
            text = text.lower()

        cached = char_costs_cache.get(original)

        if cached is None:
            boundaries = _word_boundaries(original)
            char_costs = _char_costs_for_text(text, boundaries, alphabet_pos)
            cost_sig = tuple(char_costs[c] for c in alphabet)
            cached = (char_costs, cost_sig, boundaries)
            char_costs_cache[original] = cached

        char_costs, cost_sig, boundaries = cached

        items.append(
            {
                "index": i,
                "text": text,
                "first": text[0],
                "char_costs": char_costs,
                "cost_sig": cost_sig,
                "boundaries": boundaries,
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
                    item["boundaries"],
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
