"""Data analysis helpers for DataLens AI.

Everything returned from this module is plain JSON-safe Python (no NaN / inf,
no numpy scalars, no Timestamps) so the browser's strict JSON.parse never fails.
"""
import math

import numpy as np
import pandas as pd
from pandas.api import types as pdt


def _clean(value):
    """Convert any scalar to a JSON-safe Python value (None for NaN/NaT/inf)."""
    if value is None:
        return None
    if isinstance(value, (pd.Timestamp, pd.Timedelta)):
        return None if pd.isna(value) else str(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        f = float(value)
        return None if (math.isnan(f) or math.isinf(f)) else f
    if isinstance(value, (np.bool_,)):
        return bool(value)
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def _fmt(x: float) -> str:
    """Human friendly number formatting for insight cards."""
    if abs(x) >= 1000:
        return f"{x:,.0f}"
    return f"{x:,.2f}"


class DataAnalyzer:
    def __init__(self, df: pd.DataFrame):
        self.df = df

    # ── column classification ────────────────────────────────────────────────
    @staticmethod
    def _kind(series: pd.Series) -> str:
        if pdt.is_bool_dtype(series):
            return "object"
        if pdt.is_numeric_dtype(series):
            return "numeric"
        if pdt.is_datetime64_any_dtype(series):
            return "datetime"
        return "object"

    @property
    def numeric_columns(self) -> list:
        return [c for c in self.df.columns if self._kind(self.df[c]) == "numeric"]

    @property
    def categorical_columns(self) -> list:
        return [c for c in self.df.columns if self._kind(self.df[c]) == "object"]

    def _is_id_like(self, col) -> bool:
        s = self.df[col].dropna()
        if s.empty:
            return False
        name = str(col).lower().replace(" ", "_")
        looks_like_id = name == "id" or name.endswith("_id") or name.startswith("id_") or name.endswith("id")
        return bool(looks_like_id and s.nunique() >= 0.9 * len(s))

    def _measure_columns(self) -> list:
        """Numeric columns that are real measurements (not identifiers)."""
        cols = [c for c in self.numeric_columns if not self._is_id_like(c)]
        return cols or self.numeric_columns

    def _dimension_columns(self) -> list:
        """Categorical columns with a chart-friendly number of distinct values."""
        n = max(len(self.df), 1)
        out = []
        for c in self.categorical_columns:
            u = self.df[c].nunique(dropna=True)
            if 2 <= u <= 20 and u <= 0.5 * n:
                out.append(c)
        return out

    # ── summary ──────────────────────────────────────────────────────────────
    def get_summary(self) -> dict:
        df = self.df
        numeric_cols = self.numeric_columns
        cat_cols = self.categorical_columns
        return {
            "rows": int(len(df)),
            "columns": int(len(df.columns)),
            "numeric_cols": len(numeric_cols),
            "categorical_cols": len(cat_cols),
            "missing_values": int(df.isnull().sum().sum()),
            "duplicate_rows": int(df.duplicated().sum()),
            "column_types": [{"name": str(c), "type": self._kind(df[c])} for c in df.columns],
            "numeric_column_names": [str(c) for c in numeric_cols],
            "categorical_column_names": [str(c) for c in cat_cols],
            "measure_column_names": [str(c) for c in self._measure_columns()],
            "dimension_column_names": [str(c) for c in (self._dimension_columns() or cat_cols)],
        }

    def get_preview(self, n: int = 100) -> list:
        head = self.df.head(n)
        records = []
        for row in head.itertuples(index=False, name=None):
            records.append({str(c): _clean(v) for c, v in zip(head.columns, row)})
        return records

    # ── insight cards (computed on the FULL dataset, not just the preview) ───
    def get_insights(self) -> list:
        df = self.df
        cards = []
        measures = self._measure_columns()
        if measures:
            col = measures[0]
            s = df[col].replace([np.inf, -np.inf], np.nan).dropna()
            if not s.empty:
                cards.append({"icon": "📐", "title": f"Mean — {col}", "value": _fmt(float(s.mean())), "type": "type-a"})
                cards.append({"icon": "🔺", "title": f"Max — {col}", "value": _fmt(float(s.max())), "type": "type-b"})
                cards.append({"icon": "🔻", "title": f"Min — {col}", "value": _fmt(float(s.min())), "type": "type-c"})

        total_cells = max(df.shape[0] * df.shape[1], 1)
        rate = df.isnull().sum().sum() / total_cells * 100
        cards.append({"icon": "⚠️", "title": "Missing Rate", "value": f"{rate:.1f}%", "type": "type-a"})
        cards.append({"icon": "📦", "title": "Total Records", "value": f"{len(df):,}", "type": "type-b"})

        dims = self._dimension_columns() or self.categorical_columns
        if dims:
            cards.append({"icon": "🏷", "title": f"Unique — {dims[0]}",
                          "value": int(df[dims[0]].nunique(dropna=True)), "type": "type-c"})
        return cards

    # ── chart payloads (full dataset) ────────────────────────────────────────
    def generate_auto_visualizations(self) -> list:
        df = self.df
        measures = self._measure_columns()
        dims = self._dimension_columns()
        plots = []

        if dims and measures:
            grp = (df.groupby(dims[0], dropna=True)[measures[0]]
                   .mean().dropna().sort_values(ascending=False).head(10))
            if not grp.empty:
                plots.append({
                    "type": "bar",
                    "title": f"Average {measures[0]} by {dims[0]}",
                    "labels": [str(k) for k in grp.index],
                    "values": [round(float(v), 4) for v in grp.values],
                })

        if measures:
            vals = df[measures[0]].replace([np.inf, -np.inf], np.nan).dropna()
            if len(vals) > 0:
                counts, edges = np.histogram(vals, bins=10)
                plots.append({
                    "type": "histogram",
                    "title": f"Distribution of {measures[0]}",
                    "labels": [f"{e:,.1f}" for e in edges[:-1]],
                    "values": [int(c) for c in counts],
                })

        if dims:
            vc = df[dims[0]].value_counts().head(8)
            plots.append({
                "type": "pie",
                "title": f"Breakdown of {dims[0]}",
                "labels": [str(k) for k in vc.index],
                "values": [int(v) for v in vc.values],
            })
        return plots

    def aggregate(self, x: str, y: str, top: int = 20) -> dict:
        """Mean of y per distinct x (or counts if y is not numeric), over the full dataset."""
        df = self.df
        if x not in df.columns or y not in df.columns:
            raise KeyError("Unknown column.")
        if self._kind(df[y]) == "numeric":
            grp = df.groupby(x, dropna=True)[y].mean().dropna()
            label = f"Average {y}"
        else:
            grp = df.groupby(x, dropna=True)[y].count()
            label = f"Count of {y}"
        grp = grp.sort_values(ascending=False).head(top)
        return {"labels": [str(k) for k in grp.index],
                "values": [round(float(v), 4) for v in grp.values],
                "label": label}

    def describe(self) -> dict:
        desc = self.df.describe(include="all").fillna("").astype(str)
        return desc.to_dict()
