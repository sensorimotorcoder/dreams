import argparse
import sys
from pathlib import Path

import pandas as pd
import yaml

from io_utils import load_sheet, save_df
from rules import RuleEngine

OUTPUT_COLUMNS = [
    "agent_supernatural",
    "reason_agent",
    "presence_label",
    "reason_presence",
    "visual",
    "reason_visual",
    "auditory",
    "reason_auditory",
    "tactile",
    "reason_tactile",
    "olfactory",
    "reason_olfactory",
    "gustatory",
    "reason_gustatory",
    "sensorimotor",
    "reason_sensorimotor",
    "conf",
    "motor",
    "reason_motor",
    "object",
    "reason_object",
    "valence_label",
    "reason_valence",
    "setting_hits",
    "reason_setting",
]


def load_cfgs():
    with open("config/categories.yml", "r", encoding="utf-8") as f:
        cats = yaml.safe_load(f)
    with open("config/exceptions.yml", "r", encoding="utf-8") as f:
        exc = yaml.safe_load(f)
    return cats, exc


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--in_file", required=True)
    parser.add_argument("--text_col", default="text")
    parser.add_argument("--out_file", default=None)
    args = parser.parse_args()

    df = load_sheet(args.in_file)
    if args.text_col not in df.columns:
        print(f"Missing column: {args.text_col}", file=sys.stderr)
        sys.exit(1)

    cats, exc = load_cfgs()
    engine = RuleEngine(cats, exc)

    coded_rows = [engine.analyze_text(str(text)) for text in df[args.text_col].fillna("")]
    coded_df = pd.concat([df, pd.DataFrame(coded_rows)[OUTPUT_COLUMNS]], axis=1)

    out_file = args.out_file or f"data/processed/coded_{Path(args.in_file).stem}.csv"
    save_df(coded_df, out_file)
    print(f"Wrote {out_file}")


if __name__ == "__main__":
    main()
