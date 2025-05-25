#!/usr/bin/env python3
"""
32-char emoji-Wordle solver for NahamCon “/guess” challenge
----------------------------------------------------------
author : you
python : 3.8+

Strategy
========
1.  Cardinality scan – 16 requests, one per hex symbol, to learn how many of
    each symbol are present (green+yellow count).
2.  Positional probing – fix every still-unknown position by inserting a
    candidate symbol only at that slot while padding the rest with a filler
    that is *guaranteed* to be absent from the flag.  A 🟩 there means we
    locked the symbol.
3.  (Rare) cleanup – if duplicates caused ambiguity, run a tiny DFS restricted
    to the still-unresolved slots.

This finishes in ≤ (16 + 32 × distinct_symbols + a handful) requests – generally
well under a second on a low-latency link.
"""

import requests, collections, itertools, sys

# --------------------------------------------------------------------------- #
#  CONFIGURATION
# --------------------------------------------------------------------------- #
URL      = "http://challenge.nahamcon.com:30095/guess"   # change if needed
TIMEOUT  = 5                                             # seconds
HEXCHARS = "0123456789abcdef"

# server’s feedback glyphs
GLYPH_TO_CODE = {"🟩": "g", "🟨": "y", "⬛": "b"}          # green / yellow / black


# --------------------------------------------------------------------------- #
#  HTTP helpers
# --------------------------------------------------------------------------- #
def request_flag(body: str) -> str:
    """
    Send POST /guess and return the raw 32-glyph feedback string.
    `body` must already be 32 chars long (no 'flag{ }' wrapper).
    """
    payload = {"guess": f"flag{{{body}}}"}
    r = requests.post(URL, json=payload, timeout=TIMEOUT)
    r.raise_for_status()
    # server answers:  {"result":"⬛🟨🟩…"}
    return r.json()["result"]


def decode(feedback: str):
    """
    Convert feedback glyphs to list of 'g', 'y', 'b'.
    Raise if the length is not 32.
    """
    codes = [GLYPH_TO_CODE.get(ch, "b") for ch in feedback]
    if len(codes) != 32:
        raise ValueError(f"Bad feedback length ({len(codes)}): {feedback!r}")
    return codes


# --------------------------------------------------------------------------- #
#  PHASE 1 – character counts
# --------------------------------------------------------------------------- #
def character_inventory():
    counts = collections.Counter()
    filler_char = None

    for ch in HEXCHARS:
        fb = decode(request_flag(ch * 32))
        present = fb.count("g") + fb.count("y")
        counts[ch] = present
        if present == 0 and filler_char is None:
            filler_char = ch                        # safe filler
        print(f"[scan] {ch} → {present}")

    # If the flag contains *all* 16 hex chars, pick a non-hex filler (e.g. 'g').
    if filler_char is None:
        filler_char = "g"

    print(f"[+] inventory  : {dict(counts)}")
    print(f"[+] filler char: {filler_char!r}\n")
    return counts, filler_char


# --------------------------------------------------------------------------- #
#  PHASE 2 – place symbols
# --------------------------------------------------------------------------- #
def positional_probe(counts, filler):
    solution = ["?"] * 32                 # final answer placeholder
    remaining = counts.copy()             # how many of each symbol still free

    for pos in range(32):
        if solution[pos] != "?":
            continue

        for ch in HEXCHARS:
            if remaining[ch] == 0:
                continue

            # craft test string: candidate at `pos`, filler everywhere else
            guess = "".join(
                solution[i] if solution[i] != "?"
                else (ch if i == pos else filler)
                for i in range(32)
            )
            fb = decode(request_flag(guess))

            if fb[pos] == "g":            # locked in!
                solution[pos] = ch
                remaining[ch] -= 1
                print(f"[lock] position {pos:02} = {ch}")
                break

    return solution, remaining


# --------------------------------------------------------------------------- #
#  PHASE 3 – back-tracking for leftovers (rarely needed)
# --------------------------------------------------------------------------- #
def confined_dfs(solution, remaining):
    if "?" not in solution:
        return solution                   # done

    slots = [i for i, c in enumerate(solution) if c == "?"]
    bag   = "".join(ch * remaining[ch] for ch in remaining.elements())

    print(f"[dfs] {len(slots)} slots, {len(bag)} chars to permute")

    for perm in set(itertools.permutations(bag, len(slots))):
        candidate = solution[:]
        for idx, sym in zip(slots, perm):
            candidate[idx] = sym
        fb = decode(request_flag("".join(candidate)))
        if all(c == "g" for c in fb):
            return candidate   # solved

    raise RuntimeError("DFS failed – logic error?")


# --------------------------------------------------------------------------- #
#  MAIN
# --------------------------------------------------------------------------- #
def main():
    counts, filler = character_inventory()
    partial, remain = positional_probe(counts, filler)

    if "?" in partial:
        partial = confined_dfs(partial, remain)

    flag = "flag{" + "".join(partial) + "}"
    print("\n!!! FLAG FOUND:", flag)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("\n[!] interrupted by user")
