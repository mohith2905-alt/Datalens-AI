🤖 Agentic Data Analyst

An AI-powered web application that lets you upload a CSV or Excel dataset and instantly get data summaries, insights, interactive visualizations, and natural-language answers to questions about your data, with no SQL or Python required.

Built with Python, Flask, Pandas, Plotly, and Google Gemini AI.

🚀 Features
📂 Upload CSV, XLS, and XLSX files (up to 16 MB)
🔢 Show total records and columns
⚠️ Detect missing values
📋 Detect duplicate records
🧮 Generate statistical summaries
📈 Identify numerical and categorical columns
📊 Auto-generate interactive visualizations
🔍 Preview the uploaded dataset
💬 Ask questions about your data in plain English
🤖 Gemini AI fallback for complex analytical questions
📥 Download a statistical summary report
🎨 Responsive, interactive web interface
🧠 How It Works
User uploads dataset
        ↓
   Flask backend
        ↓
  Pandas processing
        ↓
   Data analyzer
     ┌───┴────┐
Statistics  Visualizations
     └───┬────┘
         ↓
  Interactive UI
         ↓
   AI data chatbot
         ↓
 Natural-language answer
Chatbot: two-level approach
User question
      ↓
Built-in Pandas analysis
      ↓
 Can it answer?
   ↙        ↘
 Yes         No
  ↓           ↓
Answer    Gemini AI → generates analysis → executes → answer

Common questions are answered instantly by built-in Pandas logic, for example:

How many rows are there?
What are the column names?
Are there missing values?
What is the average / maximum / minimum of a column?
Show the first 10 rows
What are the unique values?
Show the correlation

More complex questions are passed to the Google Gemini API.

🛠️ Tech Stack
Layer	Technologies
Backend	Python, Flask, Pandas, NumPy, OpenPyXL
AI	Google Gemini API, Google Generative AI SDK
Visualization	Plotly, Chart.js
Frontend	HTML5, CSS3, JavaScript
Environment	Python virtual environment, python-dotenv
Tooling	Git & GitHub
📁 Project Structure
Agentic_Data_Analysts/
└── agentic data/
    ├── app.py              # Flask app and API routes
    ├── analysis.py         # Dataset analysis and visualization logic
    ├── chatbot.py          # Natural-language data chatbot
    ├── test_script.py      # Tests for data-analysis operations
    ├── requirements.txt    # Python dependencies
    ├── templates/
    │   └── index.html      # Main web interface
    ├── static/
    │   ├── css/style.css   # UI styling
    │   └── js/script.js    # Frontend logic and API calls
    └── uploads/            # Uploaded files (git-ignored)
⚙️ Installation

1. Clone the repository

bash
git clone https://github.com/YOUR_USERNAME/Agentic_Data_Analysts.git
cd Agentic_Data_Analysts

2. Create a virtual environment

bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate

3. Install dependencies

bash
pip install -r "agentic data/requirements.txt"
🔑 Gemini API Configuration

Get a free API key from Google AI Studio, then create a .env file in the folder that contains app.py:

env
GEMINI_API_KEY=your_api_key_here

⚠️ Never commit your .env file or API key to GitHub. Add this to .gitignore:

.env
venv/
__pycache__/
*.pyc
uploads/

Without an API key the app still works; only the Gemini fallback for complex questions is disabled.

▶️ Run the Application
bash
cd "agentic data"
python app.py

Open the URL shown in the terminal, usually http://127.0.0.1:5000

💬 Example Questions

After uploading a dataset, try:

How many rows are there?
Show me the column names
Are there any missing values?
What is the average salary?
What is the maximum sales?
Show the first 10 rows
Which column has the highest mean?
Show the correlation between numerical columns
🔌 API Endpoints
Method	Endpoint	Description
GET	/	Main application interface
POST	/upload	Upload and analyze a CSV/Excel file
POST	/chat	Ask a natural-language question about the dataset
GET	/download-report	Download the statistical summary report

Example /chat request

json
{ "query": "How many rows are there?" }
🔮 Future Enhancements
🔐 User authentication
🗄️ Database integration
📊 More advanced visualizations
🧠 More powerful AI agents
📑 PDF report generation
☁️ Cloud deployment
📁 Multiple dataset support
🔄 Persistent conversation history
🧹 Automated data cleaning
📈 Predictive analytics
🧪 Automated anomaly detection
🐳 Docker deployment
🎯 Use Cases

Useful for data analysts, business analysts, students, researchers, developers, and non-technical users who want to explore datasets using natural language instead of writing Python or SQL.

👨‍💻 Author

Mohith K B.E. Computer Science & Engineering (Cybersecurity) 
KPR Institute of Engineering and Technology

Interests: Python · Data Science · Machine Learning · Cybersecurity

GitHub: @mohith2905-alt

⭐ Project Highlights

An intelligent data-analysis assistant that turns raw datasets into actionable insights through automated analytics, interactive visualizations, and natural-language AI interaction.

If you find this project useful, consider giving it a ⭐ on GitHub!
