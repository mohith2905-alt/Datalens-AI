import io
import os

import pandas as pd
from flask import Flask, jsonify, render_template, request, send_file
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from analysis import DataAnalyzer
from chatbot import DataChatbot

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = os.path.join(BASE_DIR, "uploads")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

ALLOWED_EXTENSIONS = (".csv", ".xls", ".xlsx")

# Single-user, in-memory state (fine for a local demo app).
current_df = None
analyzer = None
chatbot = None


def load_dataframe(filepath: str) -> pd.DataFrame:
    """Read a CSV / Excel file into a DataFrame, tolerating odd encodings."""
    if filepath.lower().endswith(".csv"):
        for enc in ("utf-8-sig", "latin-1"):
            try:
                return pd.read_csv(filepath, encoding=enc, sep=None, engine="python")
            except UnicodeDecodeError:
                continue
        raise ValueError("Could not decode the CSV file.")
    return read_excel_any(filepath)


def read_excel_any(filepath: str) -> pd.DataFrame:
    """Read the first sheet. Falls back to the calamine engine, which also opens
    "Strict Open XML" workbooks that openpyxl cannot read."""
    first_error = None
    for engine in (None, "calamine"):
        try:
            return pd.read_excel(filepath, engine=engine)
        except ImportError:
            continue  # engine not installed
        except Exception as e:  # noqa: BLE001
            first_error = first_error or e
    raise ValueError(f"Could not read this Excel file ({first_error}). "
                     "Try re-saving it as a normal .xlsx or CSV.")


@app.errorhandler(RequestEntityTooLarge)
def too_large(_e):
    return jsonify({"error": "File is too large. Maximum size is 16 MB."}), 413


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload_file():
    global current_df, analyzer, chatbot

    if "file" not in request.files:
        return jsonify({"error": "No file part in the request."}), 400

    file = request.files["file"]
    if not file or not file.filename:
        return jsonify({"error": "No file selected."}), 400

    filename = secure_filename(file.filename)
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({"error": "Unsupported file format. Please upload a CSV or Excel file."}), 400
    if not filename:  # e.g. a name made entirely of non-ASCII characters
        filename = "dataset" + ext

    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    try:
        df = load_dataframe(filepath)
        if df.empty or len(df.columns) == 0:
            return jsonify({"error": "The file contains no data."}), 400

        df.columns = [str(c).strip() for c in df.columns]
        new_analyzer = DataAnalyzer(df)
        payload = {
            "message": "File uploaded successfully",
            "filename": filename,
            "summary": new_analyzer.get_summary(),
            "insights": new_analyzer.get_insights(),
            "plots": new_analyzer.generate_auto_visualizations(),
            "preview": new_analyzer.get_preview(n=100),
        }
        # Only replace the active dataset once everything succeeded.
        current_df, analyzer, chatbot = df, new_analyzer, DataChatbot(df)
        return jsonify(payload)

    except Exception as e:  # noqa: BLE001 - report any parse error to the UI
        return jsonify({"error": f"Could not read the file: {e}"}), 500


@app.route("/chat", methods=["POST"])
def chat():
    if chatbot is None:
        return jsonify({"error": "No dataset uploaded yet. Please upload a file first."}), 400

    data = request.get_json(silent=True) or {}
    query = (data.get("query") or "").strip()
    if not query:
        return jsonify({"error": "Empty query."}), 400

    try:
        return jsonify({"response": chatbot.ask(query)})
    except Exception as e:  # noqa: BLE001
        return jsonify({"response": f"⚠️ Sorry, something went wrong: {e}"})


@app.route("/aggregate")
def aggregate():
    if analyzer is None:
        return jsonify({"error": "No dataset uploaded yet."}), 400
    try:
        return jsonify(analyzer.aggregate(request.args.get("x", ""), request.args.get("y", "")))
    except KeyError as e:
        return jsonify({"error": str(e)}), 400


@app.route("/download-report")
def download_report():
    if current_df is None:
        return "No data to download. Upload a file first.", 400

    buf = io.BytesIO()
    current_df.describe(include="all").to_csv(buf)
    buf.seek(0)
    return send_file(buf, mimetype="text/csv", as_attachment=True, download_name="summary_report.csv")


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "1") == "1", port=int(os.getenv("PORT", "5000")))
