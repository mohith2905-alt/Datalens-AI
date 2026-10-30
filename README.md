# Agentic Data Analysis (DataLens AI)

Upload a CSV / Excel file and get instant stats, charts, insights and a chat assistant.

## Run
```bash
pip install -r requirements.txt
python app.py            # then open http://127.0.0.1:5000
```
Optional: put `GEMINI_API_KEY=...` in `.env` (see `.env.example`) to let the chat answer
open-ended questions. Without a key, the chat still answers common questions offline.

## Test
```bash
python test_app.py       # checks every dataset in uploads/, chat, charts, sandbox
```
Try `uploads/sales_test_data.csv` (has missing values and one outlier) with:
- Average Profit by Customer_Segment
- Which region has the highest total sales?
- Show missing values

## Files
- `app.py` Flask routes (`/upload`, `/chat`, `/aggregate`, `/download-report`)
- `analysis.py` summary, insights and chart data (JSON-safe)
- `chatbot.py` offline question engine + Gemini fallback with sandboxed code execution
- `templates/index.html` the UI (static/css and static/js are unused older files)
