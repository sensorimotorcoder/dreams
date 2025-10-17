from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.lexicon_extender import apply_extenders


def test_apply_extenders_generates_inflections():
    proposals = apply_extenders(["dizzy"], {})
    assert "dizzy" in proposals
    generated = {item["term"] for item in proposals["dizzy"]}
    assert "dizzier" in generated
    assert "dizziest" in generated


def test_apply_extenders_applies_spelling_map():
    proposals = apply_extenders(["color"], {"color": "colour"})
    generated = {item["term"] for item in proposals["color"]}
    assert "colour" in generated
