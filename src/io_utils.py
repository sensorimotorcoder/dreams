from pathlib import Path
from typing import Union

import pandas as pd


def load_sheet(path: Union[str, Path]) -> pd.DataFrame:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(file_path)
    if file_path.suffix.lower() == ".csv":
        return pd.read_csv(file_path)
    if file_path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(file_path)
    raise ValueError(f"Unsupported file type: {file_path.suffix}")


def save_df(df: pd.DataFrame, path: Union[str, Path]) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    if file_path.suffix.lower() != ".csv":
        file_path = file_path.with_suffix(".csv")
    df.to_csv(file_path, index=False)
