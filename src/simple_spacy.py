from __future__ import annotations

from typing import Any, Dict, Iterable, List, Sequence, Tuple

import re


DETERMINERS = {
    "a",
    "an",
    "the",
    "my",
    "your",
    "his",
    "her",
    "its",
    "our",
    "their",
}

NEGATIONS = {"no", "not", "n't", "never", "without", "none", "nothing", "neither", "nor"}
VERB_LEMMAS = {
    "feel",
    "pray",
    "hear",
    "see",
    "hold",
    "have",
    "call",
    "watch",
    "move",
    "ring",
    "mirror",
}
ADJ_LEMMAS = {
    "gross",
    "dizzy",
    "nauseous",
    "sweaty",
    "shaky",
    "cold",
    "warm",
}
LEMMATIZATION_OVERRIDES = {
    "felt": "feel",
    "prayed": "pray",
    "heard": "hear",
    "held": "hold",
    "watched": "watch",
    "ringing": "ring",
    "mirroring": "mirror",
}


class SimpleStrings(dict):
    def __getitem__(self, key: Any) -> Any:  # pragma: no cover - defensive
        return key

    def add(self, key: str) -> str:
        return key


class SimpleVocab:
    def __init__(self) -> None:
        self.strings = SimpleStrings()


class SimpleMatcher:
    def __init__(self, vocab: SimpleVocab) -> None:
        self.vocab = vocab
        self.patterns: Dict[str, List[List[Dict[str, Any]]]] = {}

    def add(self, name: str, patterns: Sequence[List[Dict[str, Any]]]) -> None:
        self.patterns.setdefault(name, []).extend(patterns)

    def __call__(self, doc: "SimpleDoc") -> List[Tuple[str, int, int]]:
        matches: List[Tuple[str, int, int]] = []
        for name, pattern_list in self.patterns.items():
            for pattern in pattern_list:
                length = len(pattern)
                for start in range(len(doc) - length + 1):
                    if self._match_pattern(doc, start, pattern):
                        matches.append((name, start, start + length))
        return matches

    def _match_pattern(
        self, doc: "SimpleDoc", start: int, pattern: Sequence[Dict[str, Any]]
    ) -> bool:
        for offset, constraints in enumerate(pattern):
            token = doc[start + offset]
            for key, expected in constraints.items():
                if key == "LEMMA":
                    if token.lemma_.lower() != str(expected).lower():
                        return False
                elif key == "POS":
                    if token.pos_ != expected:
                        return False
                elif key == "LOWER":
                    if isinstance(expected, dict) and "IN" in expected:
                        if token.lower_ not in expected["IN"]:
                            return False
                    elif token.lower_ != str(expected).lower():
                        return False
                else:  # unsupported constraint in stub
                    return False
        return True


class SimplePhraseMatcher:
    def __init__(self, vocab: SimpleVocab, attr: str = "LOWER") -> None:
        self.vocab = vocab
        self.attr = attr
        self.patterns: Dict[str, List[List[str]]] = {}

    def add(self, name: str, docs: Iterable["SimpleDoc"]) -> None:
        sequences: List[List[str]] = []
        for doc in docs:
            sequences.append([self._token_attr(tok) for tok in doc])
        self.patterns[name] = sequences

    def _token_attr(self, token: "SimpleToken") -> str:
        if self.attr == "LOWER":
            return token.lower_
        return token.text

    def __call__(self, doc: "SimpleDoc") -> List[Tuple[str, int, int]]:
        doc_attrs = [self._token_attr(tok) for tok in doc]
        matches: List[Tuple[str, int, int]] = []
        for name, seqs in self.patterns.items():
            for seq in seqs:
                length = len(seq)
                for start in range(len(doc_attrs) - length + 1):
                    if doc_attrs[start : start + length] == seq:
                        matches.append((name, start, start + length))
        return matches


def _tokenize(text: str) -> List[str]:
    normalized = text.replace("n't", " n't ")
    normalized = re.sub(r"\s+", " ", normalized)
    pieces = re.findall(r"[A-Za-z']+|[^\w\s]", normalized)
    return [piece for piece in pieces if piece.strip()]


class SimpleToken:
    def __init__(self, doc: "SimpleDoc", text: str, index: int) -> None:
        self.doc = doc
        self.text = text
        self.i = index
        self._lower = text.lower()
        base = re.sub(r"^[^A-Za-z0-9]+|[^A-Za-z0-9]+$", "", self._lower)
        self.lemma_ = LEMMATIZATION_OVERRIDES.get(base, base or self._lower)
        self.pos_ = ""
        self.dep_ = ""

    @property
    def lower_(self) -> str:
        return self._lower

    @property
    def children(self) -> Tuple[()]:
        return tuple()

    @property
    def subtree(self) -> Tuple["SimpleToken", ...]:
        return (self,)

    def nbor(self, offset: int) -> "SimpleToken":
        return self.doc[self.i + offset]


class SimpleSpan:
    def __init__(self, doc: "SimpleDoc", start: int, end: int) -> None:
        self.doc = doc
        self.start = start
        self.end = end

    @property
    def text(self) -> str:
        return " ".join(token.text for token in self.doc.tokens[self.start : self.end])


class SimpleDoc:
    def __init__(self, nlp: "SimpleNLP", text: str) -> None:
        self.nlp = nlp
        self.text = text
        token_texts = _tokenize(text)
        self.tokens: List[SimpleToken] = [SimpleToken(self, tok, i) for i, tok in enumerate(token_texts)]
        self._assign_pos_tags()

    @property
    def vocab(self) -> SimpleVocab:
        return self.nlp.vocab

    def _assign_pos_tags(self) -> None:
        for idx, token in enumerate(self.tokens):
            lower = token.lower_
            if lower in DETERMINERS:
                token.pos_ = "DET"
            elif lower in NEGATIONS:
                token.pos_ = "PART"
            elif lower in ADJ_LEMMAS or lower.endswith("y"):
                token.pos_ = "ADJ"
            elif lower in VERB_LEMMAS:
                # treat as noun if preceded by determiner
                if idx > 0 and self.tokens[idx - 1].lower_ in DETERMINERS:
                    token.pos_ = "NOUN"
                else:
                    token.pos_ = "VERB"
            else:
                token.pos_ = "NOUN"

    def __iter__(self):
        return iter(self.tokens)

    def __len__(self) -> int:
        return len(self.tokens)

    def __getitem__(self, item):
        if isinstance(item, slice):
            start, stop, step = item.indices(len(self.tokens))
            if step != 1:
                raise ValueError("Slicing with step not supported in stub")
            return SimpleSpan(self, start, stop)
        return self.tokens[item]


class SimpleNLP:
    def __init__(self) -> None:
        self.vocab = SimpleVocab()

    def __call__(self, text: str) -> SimpleDoc:
        return SimpleDoc(self, text)

    def make_doc(self, text: str) -> SimpleDoc:
        return SimpleDoc(self, text)


__all__ = [
    "SimpleMatcher",
    "SimpleNLP",
    "SimplePhraseMatcher",
]
