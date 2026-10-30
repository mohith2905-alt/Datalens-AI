"""Smoke tests: run with `python test_app.py` from the project folder."""
import io
import json
import os
import sys

from app import app
from chatbot import DataChatbot

UPLOADS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")


def strict_json(text):
    def bad(const):
        raise ValueError(f"invalid JSON constant {const}")
    return json.loads(text, parse_constant=bad)  # rejects NaN / Infinity like a browser does


def main():
    client = app.test_client()
    failures = 0

    # 1. every dataset in /uploads must load and produce browser-safe JSON
    for name in sorted(os.listdir(UPLOADS)):
        if not name.lower().endswith((".csv", ".xlsx", ".xls")) or name == "summary_report.csv":
            continue
        with open(os.path.join(UPLOADS, name), "rb") as fh:
            r = client.post("/upload", data={"file": (io.BytesIO(fh.read()), name)},
                            content_type="multipart/form-data")
        try:
            d = strict_json(r.get_data(as_text=True))
            ok = r.status_code == 200 and d["summary"]["rows"] > 0 and isinstance(d["preview"], list)
            detail = f"{d['summary']['rows']} rows x {d['summary']['columns']} cols, {len(d['plots'])} plots, {len(d['insights'])} insights"
        except Exception as e:  # noqa: BLE001
            ok, detail = False, f"{r.status_code} {e}"
        failures += not ok
        print(("PASS" if ok else "FAIL"), "upload", name, "-", detail)

    # 2. chat + aggregate on the sales dataset
    with open(os.path.join(UPLOADS, "sales_test_data.csv"), "rb") as fh:
        client.post("/upload", data={"file": (io.BytesIO(fh.read()), "sales_test_data.csv")},
                    content_type="multipart/form-data")
    checks = {
        "How many rows and columns?": "300 rows",
        "What is the max Total_Sales?": "95,000",
        "Which region has the highest total sales?": "North",
        "Average Profit by Customer_Segment": "Small Business",
        "Show missing values": "31 missing",
    }
    for q, expect in checks.items():
        ans = client.post("/chat", json={"query": q}).get_json()["response"]
        ok = expect in ans
        failures += not ok
        print(("PASS" if ok else "FAIL"), "chat:", q)

    agg = client.get("/aggregate?x=Region&y=Profit").get_json()
    ok = len(agg["labels"]) == 5
    failures += not ok
    print(("PASS" if ok else "FAIL"), "aggregate Region/Profit")

    # 3. error handling
    r = client.post("/upload", data={"file": (io.BytesIO(b"x"), "notes.txt")}, content_type="multipart/form-data")
    ok = r.status_code == 400 and "error" in r.get_json()
    failures += not ok
    print(("PASS" if ok else "FAIL"), "rejects unsupported file type")
    r = client.get("/download-report")
    ok = r.status_code == 200 and b"count" in r.data
    failures += not ok
    print(("PASS" if ok else "FAIL"), "download-report")

    # 4. code sandbox must run safe pandas and reject dangerous code
    import pandas as pd
    bot = DataChatbot(pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "x"]}))
    ok = bot._run_code("result = df.groupby('b')['a'].sum().to_dict()") == {"x": 4, "y": 2}
    failures += not ok
    print(("PASS" if ok else "FAIL"), "sandbox runs safe code")
    for evil in ["import os", "result = open('/etc/passwd').read()", "result = df.__class__",
                 "result = df.to_csv('x.csv')", "result = __import__('os').listdir('.')"]:
        try:
            bot._run_code(evil)
            ok = False
        except Exception:  # noqa: BLE001
            ok = True
        failures += not ok
        print(("PASS" if ok else "FAIL"), "sandbox blocks:", evil)

    print("\nAll tests passed." if not failures else f"\n{failures} test(s) FAILED.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
