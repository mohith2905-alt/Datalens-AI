"""DataLens AI chatbot.

Two layers:
  1. An offline engine that answers common questions (counts, averages, group-bys,
     missing values, correlations ...) instantly, without any API key.
  2. Google Gemini for everything else. Gemini writes a short pandas expression,
     which is validated and run in a restricted sandbox against the DataFrame.
"""
import ast
import os
import re

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from pandas.api import types as pdt

load_dotenv()

# ── Gemini setup (new `google-genai` SDK preferred, legacy SDK as fallback) ──
API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
_SDK = None
genai = None
if API_KEY:
    try:
        from google import genai  # type: ignore  # pip install google-genai
        _SDK = "new"
    except ImportError:
        try:
            import google.generativeai as genai  # type: ignore  # legacy SDK
            genai.configure(api_key=API_KEY)
            _SDK = "legacy"
        except ImportError:
            genai, _SDK = None, None

GENAI_AVAILABLE = bool(API_KEY and _SDK)
MODEL_CANDIDATES = [m for m in [os.getenv("GEMINI_MODEL"), "gemini-2.5-flash", "gemini-2.0-flash",
                                "gemini-flash-latest", "gemini-1.5-flash"] if m]

# ── Sandbox for model-written code ──────────────────────────────────────────
_SAFE_BUILTINS = {n: __builtins__[n] if isinstance(__builtins__, dict) else getattr(__builtins__, n)
                  for n in ("len", "sum", "min", "max", "round", "abs", "sorted", "list", "dict", "set",
                            "tuple", "str", "int", "float", "bool", "range", "enumerate", "zip", "any",
                            "all", "isinstance", "reversed", "map", "filter", "True", "False", "None")}
_BLOCKED_NAMES = {"open", "exec", "eval", "compile", "__import__", "globals", "locals", "getattr", "setattr",
                  "delattr", "input", "breakpoint", "vars", "dir", "os", "sys", "subprocess"}
_BLOCKED_ATTRS = {"to_csv", "to_excel", "to_pickle", "to_sql", "to_json", "to_parquet", "to_feather",
                  "to_hdf", "to_clipboard", "to_html", "to_latex", "read_csv", "read_excel", "read_pickle",
                  "read_json", "read_sql", "read_html", "read_parquet", "eval", "query", "pipe"}

_STOPWORDS = {"the", "a", "an", "of", "in", "for", "by", "per", "each", "is", "are", "what", "which", "show",
              "me", "give", "list", "all", "total", "average", "mean", "sum", "max", "min", "maximum",
              "minimum", "count", "number", "highest", "lowest", "most", "least", "top", "first", "value",
              "values", "data", "dataset", "rows", "row", "column", "columns", "has", "have", "with", "and",
              "to", "how", "many", "much", "median", "unique", "distinct", "across", "group", "date", "type"}


def _validate_code(code: str) -> None:
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            raise ValueError("imports are not allowed")
        if isinstance(node, ast.Attribute) and (node.attr.startswith("_") or node.attr in _BLOCKED_ATTRS):
            raise ValueError(f"attribute '{node.attr}' is not allowed")
        if isinstance(node, ast.Name) and (node.id in _BLOCKED_NAMES or node.id.startswith("__")):
            raise ValueError(f"name '{node.id}' is not allowed")


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[_\-]+", " ", str(text).lower())).strip()


class DataChatbot:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.client = genai.Client(api_key=API_KEY) if _SDK == "new" else None
        self._model_name = None
        self._cols = {c: _norm(c) for c in df.columns}
        self._numeric = [c for c in df.columns if pdt.is_numeric_dtype(df[c]) and not pdt.is_bool_dtype(df[c])]
        self._categorical = [c for c in df.columns if c not in self._numeric]

    # ── helpers ──────────────────────────────────────────────────────────────
    def _find_columns(self, q: str):
        """Return (columns mentioned in order of appearance, question text with column names removed)."""
        found, remaining = [], q
        for col, name in sorted(self._cols.items(), key=lambda kv: -len(kv[1])):
            if name and re.search(rf"(?<![a-z0-9]){re.escape(name)}(?![a-z0-9])", remaining):
                found.append((remaining.index(name), col))
                remaining = remaining.replace(name, " ")
        tokens = set(re.findall(r"[a-z0-9]+", remaining)) - _STOPWORDS
        for tok in tokens:
            if len(tok) < 3:
                continue
            hits = [c for c, n in self._cols.items() if tok in n.split() and c not in {f[1] for f in found}]
            if len(hits) == 1:  # unambiguous single-word reference, e.g. "region"
                found.append((q.find(tok), hits[0]))
                remaining = re.sub(rf"\b{re.escape(tok)}\b", " ", remaining)
        return [c for _, c in sorted(found)], remaining

    @staticmethod
    def _fmt_num(x) -> str:
        if isinstance(x, (int, np.integer)):
            return f"{int(x):,}"
        if isinstance(x, (float, np.floating)):
            return f"{x:,.2f}" if abs(x) >= 1 else f"{x:,.4f}"
        return str(x)

    def _fmt_result(self, result) -> str:
        if isinstance(result, pd.DataFrame):
            return "```\n" + result.head(30).to_string() + "\n```" + (f"\n…({len(result)} rows total)" if len(result) > 30 else "")
        if isinstance(result, pd.Series):
            return "```\n" + result.head(30).to_string() + "\n```" + (f"\n…({len(result)} items total)" if len(result) > 30 else "")
        if isinstance(result, (list, tuple, set)):
            return ", ".join(map(str, list(result)[:50]))
        return self._fmt_num(result)

    # ── offline engine ───────────────────────────────────────────────────────
    _AGGS = [  # (regex, pandas agg, label)
        (r"\b(average|avg|mean)\b", "mean", "Average"),
        (r"\b(median)\b", "median", "Median"),
        (r"\b(sum|total)\b", "sum", "Total"),
        (r"\b(max|maximum|highest|largest|biggest|greatest)\b", "max", "Maximum"),
        (r"\b(min|minimum|lowest|smallest|least)\b", "min", "Minimum"),
    ]

    def _builtin_answer(self, query: str):
        q, df = _norm(query), self.df
        cols, rest = self._find_columns(q)
        num = [c for c in cols if c in self._numeric]
        cat = [c for c in cols if c not in self._numeric]
        is_group = bool(re.search(r"\b(by|per|each|across|group(ed)? by|for every)\b", rest))
        which = re.search(r"\b(which|what|who)\b", rest) is not None
        ranking = re.search(r"\b(highest|largest|most|biggest|top|lowest|smallest|least|best|worst)\b", rest) is not None
        low = re.search(r"\b(lowest|smallest|least|worst|minimum|min)\b", rest) is not None

        agg = next(((fn, label) for rx, fn, label in self._AGGS if re.search(rx, rest)), None)

        # missing values
        if re.search(r"\b(missing|null|nan|blank|empty)\b", q):
            miss = df.isnull().sum()
            miss = miss[miss > 0].sort_values(ascending=False)
            if miss.empty:
                return "✅ No missing values found in this dataset."
            lines = "\n".join(f"- **{c}**: {v} ({v / len(df):.1%})" for c, v in miss.items())
            return f"**{int(miss.sum())} missing values** across {len(miss)} columns:\n{lines}"

        # duplicates
        if "duplicate" in q:
            return f"The dataset has **{int(df.duplicated().sum())}** duplicate rows."

        # correlation
        if "correlat" in q:
            if len(num) >= 2:
                return f"Correlation between **{num[0]}** and **{num[1]}**: `{df[num[0]].corr(df[num[1]]):.4f}`"
            numeric = df[self._numeric]
            if numeric.shape[1] < 2:
                return "Not enough numeric columns to compute correlation."
            return f"**Correlation matrix:**\n```\n{numeric.corr().round(3).to_string()}\n```"

        # which column has the highest mean/average
        if re.search(r"\bcolumn\b", q) and agg and agg[0] == "mean" and not num:
            if not self._numeric:
                return "No numeric columns found."
            means = df[self._numeric].mean()
            best = means.idxmin() if low else means.idxmax()
            return f"The column with the {'lowest' if low else 'highest'} mean is **{best}** (mean = `{means[best]:,.4f}`)."

        # grouped aggregation: "average profit by segment", "total sales per region"
        if num and cat and is_group and (agg or re.search(r"\b(how many|count|number)\b", q) is None):
            fn, label = agg or ("sum", "Total")
            res = df.groupby(cat[0])[num[0]].agg(fn).sort_values(ascending=low)
            return f"**{label} {num[0]} by {cat[0]}:**\n```\n{res.round(2).to_string()}\n```"

        # "which region has the highest total sales"
        if num and cat and which and ranking:
            fn = agg[0] if agg and agg[0] in ("mean", "median", "sum") else "sum"
            res = df.groupby(cat[0])[num[0]].agg(fn)
            winner = res.idxmin() if low else res.idxmax()
            word = {"mean": "mean", "median": "median", "sum": "sum"}[fn]
            return (f"**{winner}** has the {'lowest' if low else 'highest'} **{num[0]}** "
                    f"({word} = `{self._fmt_num(res[winner])}`).\n```\n{res.sort_values(ascending=low).round(2).to_string()}\n```")

        # category counts: "how many orders per product category", "distribution of region"
        if cat and (is_group or re.search(r"\b(distribution|breakdown|value counts?|frequency)\b", q)) \
                and re.search(r"\b(how many|count|number|distribution|breakdown|value counts?|frequency)\b", q):
            vc = df[cat[0]].value_counts()
            return f"**Count by {cat[0]}:**\n```\n{vc.to_string()}\n```"

        # unique values
        if re.search(r"\b(unique|distinct)\b", q) and cols:
            col = cols[0]
            n = df[col].nunique()
            extra = f": {', '.join(map(str, df[col].dropna().unique()[:10]))}" if n <= 10 else ""
            return f"**{col}** has `{n}` unique values{extra}."

        # simple aggregation of one numeric column
        if num and agg and not is_group:
            fn, label = agg
            return f"✅ {label} of **{num[0]}**: `{self._fmt_num(getattr(df[num[0]], fn)())}`"

        # first / top N rows
        m = re.search(r"\b(first|head|top|last|tail)\s*(\d+)?\s*rows?\b", q)
        if m:
            n = int(m.group(2)) if m.group(2) else 5
            part = df.tail(n) if m.group(1) in ("last", "tail") else df.head(n)
            return f"**{'Last' if m.group(1) in ('last', 'tail') else 'First'} {n} rows:**\n```\n{part.to_string()}\n```"

        # structure questions
        if re.search(r"\b(shape|size|how many rows|number of rows|how many records|dimensions|rows and columns)\b", q):
            return f"The dataset has **{df.shape[0]:,} rows** and **{df.shape[1]} columns**."
        if re.search(r"\b(column names?|columns?|features?|fields?)\b", q) and not num and not agg:
            if re.search(r"\b(how many)\b", q) and not re.search(r"\b(names?|list|what are)\b", q):
                return f"The dataset has **{df.shape[1]} columns**."
            return f"The dataset has **{df.shape[1]} columns**: {', '.join(map(str, df.columns))}."
        if re.search(r"\b(shape|size|how many rows|number of rows|how many records|dimensions)\b", q):
            return f"The dataset has **{df.shape[0]:,} rows** and **{df.shape[1]} columns**."
        if re.search(r"\b(dtypes?|data types?|types of columns)\b", q):
            return "Column data types:\n" + "\n".join(f"- **{c}**: {t}" for c, t in df.dtypes.items())
        if re.search(r"\b(describe|summary|statistics|stats)\b", q):
            return f"**Statistical summary:**\n```\n{df.describe().round(2).to_string()}\n```"
        return None

    # ── Gemini ───────────────────────────────────────────────────────────────
    _SYSTEM = """You are DataLens AI, an expert data analyst.
A pandas DataFrame named `df` is already loaded (pandas is `pd`, numpy is `np`).

Rules:
1. If the question needs computation, write ONE ```python code block that assigns the answer to `result`.
   Use only pandas/numpy on `df`. No imports, no file or network access, no df.query()/df.eval().
2. Use exact column names from the metadata. Never invent columns.
3. After the code, explain the answer in one or two plain-English sentences.
4. If the question is descriptive (no computation), answer directly without code."""

    def _context(self) -> str:
        df = self.df
        info = {
            "shape": df.shape,
            "columns": list(df.columns),
            "dtypes": {c: str(t) for c, t in df.dtypes.items()},
            "sample_3_rows": df.head(3).astype(object).where(df.head(3).notna(), None).to_dict(orient="records"),
            "missing_per_col": {c: int(v) for c, v in df.isnull().sum().items() if v},
        }
        if self._numeric:
            info["numeric_describe"] = df[self._numeric].describe().round(3).to_dict()
        return str(info)

    def _generate(self, prompt: str) -> str:
        last_err = None
        for name in ([self._model_name] if self._model_name else MODEL_CANDIDATES):
            try:
                if _SDK == "new":
                    text = self.client.models.generate_content(model=name, contents=prompt).text
                else:
                    text = genai.GenerativeModel(name).generate_content(prompt).text
                self._model_name = name
                return text or ""
            except Exception as e:  # noqa: BLE001
                last_err = e
                if any(k in str(e).lower() for k in ("not found", "404", "not supported", "deprecated")):
                    self._model_name = None
                    continue  # try the next model name
                raise
        raise last_err or RuntimeError("No Gemini model available.")

    @staticmethod
    def _extract_code(text: str):
        m = re.search(r"```(?:python)?\s*\n?(.*?)```", text, re.DOTALL)
        return m.group(1).strip() if m else None

    def _run_code(self, code: str):
        _validate_code(code)
        env = {"__builtins__": _SAFE_BUILTINS, "df": self.df.copy(), "pd": pd, "np": np, "result": None}
        exec(compile(code, "<agent>", "exec"), env)  # noqa: S102 - validated + restricted above
        return env["result"]

    # ── public API ───────────────────────────────────────────────────────────
    def ask(self, query: str) -> str:
        builtin = self._builtin_answer(query)
        if builtin:
            return builtin

        if not GENAI_AVAILABLE:
            reason = ("Add `GEMINI_API_KEY` to your `.env` file" if not API_KEY
                      else "Install the Gemini SDK with `pip install google-genai`")
            return ("🤔 I couldn't answer that offline, and the AI model isn't enabled. "
                    f"{reason} to unlock open-ended questions.\n\nTry:\n"
                    "- Average Profit by Customer_Segment\n- Which region has the highest total sales?\n"
                    "- How many rows?\n- Show missing values")

        try:
            ai_text = self._generate(self._build_prompt(query))
        except Exception as e:  # noqa: BLE001
            return f"⚠️ Gemini API error: {e}"

        code = self._extract_code(ai_text)
        if not code:
            return ai_text.strip() or "I couldn't produce an answer for that."

        explanation = re.sub(r"```.*?```", "", ai_text, flags=re.DOTALL).strip() or "Computation completed."
        try:
            result = self._run_code(code)
        except Exception as err:  # noqa: BLE001
            return (f"⚠️ I couldn't run the generated analysis (`{err}`). Try rephrasing, e.g.:\n"
                    "- Sum of [column]\n- Average [column] by [category]\n- Show first 5 rows")
        one_line = "; ".join(line.strip() for line in code.splitlines() if line.strip())
        return f"✅ **Result:** {self._fmt_result(result)}\n\n{explanation}\n\n(Agent logic: `{one_line}`)"

    def _build_prompt(self, query: str) -> str:
        return (f"{self._SYSTEM}\n\n=== Dataset metadata ===\n{self._context()}\n\n"
                f"=== User question ===\n{query}\n")
