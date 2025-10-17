import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(REPO_ROOT))
sys.path.append(str(REPO_ROOT / "src"))

import yaml

from rules import RuleEngine


with open("config/categories.yml", "r", encoding="utf-8") as f:
    CATS = yaml.safe_load(f)
with open("config/exceptions.yml", "r", encoding="utf-8") as f:
    EXC = yaml.safe_load(f)


def make_engine():
    return RuleEngine(CATS, EXC)


def test_god_vs_godfrey():
    eng = make_engine()
    a = eng.analyze_text("I prayed to God in the chapel.")
    b = eng.analyze_text("I had lunch with Godfrey.")
    assert a["agent_supernatural"] == 1
    assert b["agent_supernatural"] == 0


def test_epistemic_felt():
    eng = make_engine()
    a = eng.analyze_text("I felt gross after the dream.")
    b = eng.analyze_text("I felt like I was right about it.")
    assert a["sensorimotor"] == 1 and "felt+gross" in a["reason_sensorimotor"]
    assert b["sensorimotor"] == 0 and b["reason_sensorimotor"] == "epistemic_felt"


def test_negation_blocks_embodied():
    eng = make_engine()
    result = eng.analyze_text("I didn't feel dizzy during the ritual.")
    assert result["sensorimotor"] == 0


def test_determiner_guard_on_objects():
    eng = make_engine()
    a = eng.analyze_text("I held a ring and a mirror in my hands.")
    b = eng.analyze_text("They ring the bells and mirror our moves.")
    assert a["object"] == 1
    assert b["object"] == 0


def test_presence_multiword():
    eng = make_engine()
    result = eng.analyze_text("I heard a disembodied voice and felt a cold spot.")
    assert "disembodied voice" in result["presence_label"]
    assert "cold spot" in result["presence_label"]
