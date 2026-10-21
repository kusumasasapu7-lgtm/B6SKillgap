"""Reusable, explicit cleaning rules for CSV-backed project data."""
from __future__ import annotations

import numpy as np
import pandas as pd


class DataCleaner:
    """Normalize common CSV issues without hiding invalid records."""

    SPELLING = {
        "human resources specialist": "Human Resources Specialists",
        "human resources specialists": "Human Resources Specialists",
        "general and operations manager": "General and Operations Managers",
        "general and operations managers": "General and Operations Managers",
        "medical scientist, except epidemiologists": "Medical Scientists, Except Epidemiologists",
        "medical scientists, except epidemiologists": "Medical Scientists, Except Epidemiologists",
        "biological technician": "Biological Technicians",
        "biological technicians": "Biological Technicians",
        "industrial production manager": "Industrial Production Managers",
        "industrial production managers": "Industrial Production Managers",
    }

    def clean(self, frame: pd.DataFrame, columns: list[str], *, id_column: str,
              numeric: tuple[str, ...] = (), categorical: tuple[str, ...] = (),
              date_columns: tuple[str, ...] = (), bounds: dict[str, tuple[float, float]] | None = None) -> pd.DataFrame:
        """Return a schema-aligned copy; numeric gaps use the median, categories Unknown."""
        result = frame.copy()
        result.columns = [str(column).strip() for column in result.columns]
        result = result.reindex(columns=columns)
        result = result.replace(r"^\s*$", np.nan, regex=True)
        for column in result.select_dtypes(include="object").columns:
            result[column] = result[column].map(lambda value: value.strip() if isinstance(value, str) else value)
            result[column] = result[column].map(
                lambda value: self.SPELLING.get(value.casefold(), value) if isinstance(value, str) else value
            )
        for column in numeric:
            result[column] = pd.to_numeric(result[column], errors="coerce")
            if result[column].isna().any():
                median = result[column].median()
                fill_value = float(median) if pd.notna(median) else 0.0
                result[column] = result[column].fillna(fill_value)
        for column in categorical:
            result[column] = result[column].fillna("Unknown").astype(str)
        for column in date_columns:
            result[column] = pd.to_datetime(result[column], errors="coerce", format="mixed")
        if bounds:
            keep = pd.Series(True, index=result.index)
            for column, (minimum, maximum) in bounds.items():
                keep &= result[column].between(minimum, maximum, inclusive="both")
            result = result.loc[keep].copy()
        if id_column in result.columns:
            result[id_column] = result[id_column].fillna("").astype(str).str.strip()
            result = result[result[id_column].ne("")]
            result = result.drop_duplicates(subset=[id_column], keep="last")
        result = result.drop_duplicates(keep="last").reset_index(drop=True)
        return result.reindex(columns=columns)
