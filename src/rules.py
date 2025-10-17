from typing import Callable

try:
    import spacy
    from spacy.matcher import Matcher, PhraseMatcher
except ModuleNotFoundError:  # pragma: no cover - spaCy optional in this environment
    spacy = None
    Matcher = PhraseMatcher = None

from simple_spacy import SimpleMatcher, SimpleNLP, SimplePhraseMatcher


class RuleEngine:
    def __init__(self, cfg_categories: dict, cfg_exceptions: dict):
        self.cfg = cfg_categories
        self.exc = cfg_exceptions

        self._resolve_match: Callable[[object], str]
        if spacy is not None and Matcher is not None and PhraseMatcher is not None:
            try:
                self.nlp = spacy.load("en_core_web_sm")
                self.matcher = Matcher(self.nlp.vocab)
                self.phraser = PhraseMatcher(self.nlp.vocab, attr="LOWER")
                self._resolve_match = lambda mid: self.nlp.vocab.strings[mid]
            except Exception:  # pragma: no cover - spaCy model unavailable
                self.nlp = SimpleNLP()
                self.matcher = SimpleMatcher(self.nlp.vocab)
                self.phraser = SimplePhraseMatcher(self.nlp.vocab, attr="LOWER")
                self._resolve_match = lambda mid: mid  # type: ignore[return-value]
        else:  # spaCy missing, use lightweight fallback
            self.nlp = SimpleNLP()
            self.matcher = SimpleMatcher(self.nlp.vocab)
            self.phraser = SimplePhraseMatcher(self.nlp.vocab, attr="LOWER")
            self._resolve_match = lambda mid: mid  # type: ignore[return-value]

        # --- Build lexicon sets ---
        self.supernatural_lemmas = set(self.cfg.get("agent", {}).get("supernatural_nouns", []))
        self.proper_ex = set(self.exc.get("proper_name_exceptions", []))
        self.idiom_sup = set(self.exc.get("idiom_exclusions", {}).get("supernatural", []))
        self.negations = set(self.exc.get("negations", []))
        self.epist_comp = set(self.exc.get("epistemic_complements", []))
        self.hedges = set(self.exc.get("hedges", []))
        self.intens = set(self.exc.get("intensifiers", []))
        self.objects_need_det = set(self.exc.get("objects_require_determiner", []))

        # Build phrase matchers for presence types (multiword)
        presence_phrases = [p for p in self.cfg["presence"]["types"] if " " in p]
        self.phraser.add("PRESENCE_PHRASE", [self.nlp.make_doc(p) for p in presence_phrases])

        # Grammar patterns
        self.matcher.add("FELT_ADJ", [[{"LEMMA": "feel"}, {"POS": "ADJ"}]])
        self.matcher.add(
            "FELT_EPIST",
            [[{"LEMMA": "feel"}, {"LOWER": {"IN": list(self.epist_comp)}}]],
        )
        # Body noun cues: det + body noun
        body_nouns = set(
            self.cfg["bodystate"]["respiratory"]
            + self.cfg["bodystate"]["cardio"]
            + self.cfg["bodystate"]["general_state"]
        )
        self.matcher.add(
            "BODY_NOUN_CUE",
            [[{"POS": "DET"}, {"LEMMA": {"IN": list(body_nouns)}}]],
        )

        # Simple smell/taste/vision/voice triggers (token-level)
        self.olfactory = set(self.cfg["olfactory"]["smells"])
        self.gustatory = set(self.cfg["gustatory"]["tastes"])
        self.visual = set(sum(self.cfg["visual"].values(), []))
        self.auditory = set(sum(self.cfg["auditory"].values(), []))
        self.tactile = set(self.cfg["tactile"]["adjectives"] + self.cfg["tactile"]["verbs"])

        # Motor grouping
        self.motor = set(self.cfg["motor"]["postures"] + self.cfg["motor"]["movements"])

        # Objects
        self.sacred_objects = set(
            self.cfg["object"]["sacred_objects"] + self.cfg["object"]["ordinary"]
        )

        # Sensorimotor evaluatives to treat as embodied when following FEEL
        self.embodied_eval_adjs = set(self.cfg["bodystate"]["evaluative_embodied_adjs"])

    # ----------------- Utilities -----------------
    def _near_idiom(self, doc, i, window=3, idioms=None):
        idioms = idioms or []
        start = max(0, i - window)
        end = min(len(doc), i + window + 1)
        span = doc[start:end].text.lower()
        return any(phrase in span for phrase in idioms)

    def _is_negated(self, tok, window=5):
        # local dep/linear window negation
        for t in tok.subtree:
            if t.lower_ in self.negations:
                return True
        start = max(0, tok.i - window)
        end = min(len(tok.doc), tok.i + window + 1)
        span = tok.doc[start:end]
        try:
            iterator = iter(span)
        except TypeError:
            if hasattr(span, "doc") and hasattr(span, "start"):
                iterator = iter(span.doc.tokens[span.start : span.end])
            else:  # pragma: no cover - defensive fallback
                iterator = iter(())
        for t in iterator:
            if getattr(t, "lower_", str(t).lower()) in self.negations:
                return True
        return False

    def _confidence(self, doc):
        c = 0
        for t in doc:
            if t.lower_ in self.intens:
                c += 1
            if t.lower_ in self.hedges:
                c -= 1
        return max(0, min(3, 1 + c))  # 1..3

    def _needs_det_ok(self, tok):
        if tok.lemma_.lower() not in self.objects_need_det:
            return True
        # require determiner or possessor
        for child in tok.children:
            if child.dep_ in ("det", "poss"):
                return True
        # check immediate left token
        if tok.i > 0 and tok.nbor(-1).pos_ in ("DET", "PRON"):
            return True
        return False

    # ----------------- Supernatural / Agent -----------------
    def code_supernatural_agent(self, doc):
        # phrase/idom suppressors
        # agent code if noun is in supernatural lemmas and not an exception/idiom
        for tok in doc:
            low = tok.text.lower()
            lem = tok.lemma_.lower()
            if low in self.proper_ex:
                continue
            if tok.pos_ in ("NOUN", "PROPN") and lem in self.supernatural_lemmas:
                if self._near_idiom(doc, tok.i, idioms=self.idiom_sup):
                    continue
                return {
                    "agent_supernatural": 1,
                    "reason_agent": f"lemma={lem}, pos={tok.pos_}",
                    "conf": self._confidence(doc),
                }
        return {
            "agent_supernatural": 0,
            "reason_agent": "",
            "conf": self._confidence(doc),
        }

    # ----------------- Presence -----------------
    def code_presence(self, doc):
        # multiword first
        pres = []
        for _, start, end in self.phraser(doc):
            pres.append(doc[start:end].text)
        # single word fallbacks
        singles = [p for p in self.cfg["presence"]["types"] if " " not in p]
        for tok in doc:
            if tok.lemma_.lower() in singles:
                pres.append(tok.text)
        pres = list(dict.fromkeys(pres))  # dedup
        return {
            "presence_label": ";".join(pres) if pres else "",
            "reason_presence": "phrase" if pres else "",
        }

    # ----------------- Visual / Auditory / Tactile / Olfactory / Gustatory -----------------
    def _code_simple_lex(self, doc, lexset, label):
        hits = []
        for tok in doc:
            if tok.lemma_.lower() in lexset or tok.text.lower() in lexset:
                hits.append(tok.lemma_)
        return {
            f"{label}": 1 if hits else 0,
            f"reason_{label}": ",".join(sorted(set(hits))),
        }

    # ----------------- Body state & Sensorimotor (nuanced FEEL) -----------------
    def code_bodystate_sensorimotor(self, doc):
        matches = self.matcher(doc)
        labs = {self._resolve_match(mid) for mid, _, _ in matches}

        # Epistemic override: "feel/felt" + like/that/as if...
        if "FELT_EPIST" in labs:
            return {
                "sensorimotor": 0,
                "reason_sensorimotor": "epistemic_felt",
                "conf": self._confidence(doc),
            }

        # FEEL + ADJ where adj is embodied (gross, sweaty, dizzy…)
        for mid, start, end in matches:
            if self._resolve_match(mid) == "FELT_ADJ":
                adj = doc[start + 1]
                if adj.lemma_.lower() in self.embodied_eval_adjs and not self._is_negated(adj):
                    return {
                        "sensorimotor": 1,
                        "reason_sensorimotor": f"felt+{adj.lemma_.lower()}",
                        "conf": self._confidence(doc),
                    }

        # Body noun cues (det + body noun) + a state adjective/verb nearby
        if "BODY_NOUN_CUE" in labs:
            return {
                "sensorimotor": 1,
                "reason_sensorimotor": "body_noun_context",
                "conf": self._confidence(doc),
            }

        # Default: no sensorimotor
        return {"sensorimotor": 0, "reason_sensorimotor": "", "conf": self._confidence(doc)}

    # ----------------- Motor & Objects with POS/DET guards -----------------
    def code_motor(self, doc):
        hits = []
        for tok in doc:
            if tok.lemma_.lower() in self.motor:
                # prefer verbs (actions) and posture nouns with auxiliaries
                if tok.pos_ in ("VERB", "AUX") or tok.lemma_.lower() in self.cfg["motor"]["postures"]:
                    hits.append(tok.lemma_.lower())
        return {"motor": 1 if hits else 0, "reason_motor": ",".join(sorted(set(hits)))}

    def code_objects(self, doc):
        hits = []
        for tok in doc:
            lem = tok.lemma_.lower()
            if lem in self.sacred_objects and tok.pos_ == "NOUN":
                if not self._needs_det_ok(tok):
                    continue
                hits.append(lem)
        return {"object": 1 if hits else 0, "reason_object": ",".join(sorted(set(hits)))}

    # ----------------- Valence (keyword baseline; you can replace with classifier later) -----------------
    def code_valence(self, doc):
        pos_hits, neg_hi, neg_lo = [], [], []
        for tok in doc:
            w = tok.lemma_.lower()
            if w in set(
                self.cfg["valence"]["awe"]
                + self.cfg["valence"]["reverence"]
                + self.cfg["valence"]["peace"]
                + self.cfg["valence"]["comfort"]
                + self.cfg["valence"]["ecstasy"]
                + self.cfg["valence"]["positive_low_arousal"]
            ):
                pos_hits.append(w)
            if w in set(self.cfg["valence"]["negative_high_arousal"]):
                neg_hi.append(w)
            if w in set(self.cfg["valence"]["negative_low_arousal"]):
                neg_lo.append(w)
        label = ""
        if neg_hi:
            label = "negative_high_arousal"
        elif neg_lo:
            label = "negative_low_arousal"
        elif pos_hits:
            label = "positive"
        return {"valence_label": label, "reason_valence": ",".join(sorted(set(pos_hits + neg_hi + neg_lo)))}

    # ----------------- Settings -----------------
    def code_setting(self, doc):
        hits = []
        for tok in doc:
            lem = tok.lemma_.lower()
            if lem in set(
                self.cfg["setting"]["structural"]
                + self.cfg["setting"]["sacred_tokens"]
                + self.cfg["setting"]["liminal"]
            ):
                hits.append(lem)
        return {
            "setting_hits": ",".join(sorted(set(hits))) if hits else "",
            "reason_setting": "lex",
        }

    # ----------------- Public API -----------------
    def analyze_text(self, text: str) -> dict:
        doc = self.nlp(text or "")

        out = {}
        out.update(self.code_supernatural_agent(doc))
        out.update(self.code_presence(doc))
        out.update(self._code_simple_lex(doc, self.visual, "visual"))
        out.update(self._code_simple_lex(doc, self.auditory, "auditory"))
        out.update(self._code_simple_lex(doc, self.tactile, "tactile"))
        out.update(self._code_simple_lex(doc, self.olfactory, "olfactory"))
        out.update(self._code_simple_lex(doc, self.gustatory, "gustatory"))
        out.update(self.code_bodystate_sensorimotor(doc))
        out.update(self.code_motor(doc))
        out.update(self.code_objects(doc))
        out.update(self.code_valence(doc))
        out.update(self.code_setting(doc))

        return out
