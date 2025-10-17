"""Deterministic utilities for expanding lexicon candidates."""
from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple


def inflections(term: str) -> List[str]:
    """Generate a conservative set of inflections for a term."""

    t = term.lower()
    out: Set[str] = {t}
    if t.endswith("y") and len(t) > 3:
        out.add(t[:-1] + "ier")
        out.add(t[:-1] + "iest")
    if t.endswith("e"):
        out.add(t + "r")
        out.add(t + "st")
    for suffix in ("ed", "ing", "s"):
        out.add(t + suffix)
    return sorted(out)


def hyphen_space_variants(term: str) -> List[str]:
    """Return hyphenated/space-separated alternatives for a phrase."""

    t = term.lower()
    if " " in t:
        return [t, t.replace(" ", "-")]
    if "-" in t:
        return [t, t.replace("-", " ")]
    return [t]


def british_american(term: str, br_am: Dict[str, str]) -> List[str]:
    """Return British/American spelling alternatives when available."""

    t = term.lower()
    out: Set[str] = {t}
    if t in br_am:
        out.add(br_am[t].lower())
    reverse = {v.lower(): k.lower() for k, v in br_am.items()}
    if t in reverse:
        out.add(reverse[t])
    return sorted(out)


def apply_extenders(
    terms: List[str], br_am: Dict[str, str]
) -> Dict[str, List[Dict[str, Any]]]:
    """Generate extension proposals for each input term.

    The extender keeps track of previously seen lower-cased forms to avoid
    duplicate proposals across multiple heuristics.
    """

    proposals: Dict[str, List[Dict[str, Any]]] = {}
    seen: Set[str] = {term.lower() for term in terms}

    for base in terms:
        candidates: Set[Tuple[str, str]] = set()
        for variant in inflections(base):
            candidates.add(("inflection", variant))
        for variant in hyphen_space_variants(base):
            candidates.add(("hyphen", variant))
        for variant in british_american(base, br_am):
            candidates.add(("british_american", variant))

        for source, value in sorted(candidates):
            if value.lower() in seen:
                continue
            proposals.setdefault(base, []).append(
                {"term": value, "source": source}
            )
            seen.add(value.lower())

    return proposals
