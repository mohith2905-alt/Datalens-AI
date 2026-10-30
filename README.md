🤖 Agentic Data Analyst
An AI-powered Agentic Data Analysis web application that allows users to upload CSV or Excel datasets and automatically generate data summaries, insights, visualizations, and natural-language answers to questions about their data.

The application combines Python, Flask, Pandas, Plotly, and Google Gemini AI to provide an interactive data analysis experience without requiring users to write SQL or Python code.

🚀 Features 📂 Upload CSV, XLS, and XLSX files 📊 Automatically analyze uploaded datasets 🔢 Display total records and columns ⚠️ Detect missing values 📋 Detect duplicate records 🧮 Generate statistical summaries 📈 Identify numerical and categorical columns 📊 Automatically generate visualizations 🔍 Preview uploaded dataset 💬 Ask questions about the uploaded dataset using natural language 🤖 Gemini AI fallback for complex analytical questions 📥 Download a statistical summary report 🎨 Interactive and responsive web interface 🧠 How It Works

The application follows a simple data-analysis pipeline:

User Uploads Dataset ↓ Flask Backend ↓ Pandas Processing ↓ Data Analyzer ↓ ┌──────┴────────┐ ↓ ↓ Statistics Visualizations ↓ ↓ └──────┬────────┘ ↓ Interactive UI ↓ AI Data Chatbot ↓ Natural Language Answer Chatbot Processing

The chatbot uses a two-level approach:

User Question ↓ Built-in Data Analysis ↓ Can it answer? ↙ ↘ Yes No ↓ ↓ Answer Gemini AI ↓ Generate Analysis ↓ Execute ↓ Answer

For common questions such as:

How many rows are there? What are the column names? Are there missing values? What is the average of a column? What is the maximum value? What is the minimum value? Show the first 10 rows What are the unique values? Show correlation

the application uses built-in Pandas-based analysis.

For more complex questions, the application can use Google Gemini API. 🛠️ Tech Stack Backend Python Flask Pandas NumPy OpenPyXL AI Google Gemini API Google Generative AI Data Visualization Plotly Chart.js Frontend HTML5 CSS3 JavaScript Environment Python Virtual Environment python-dotenv Git & GitHub 📁 Project Structure agentic data/ │ └── agentic data/ │ ├── app.py ├── analysis.py ├── chatbot.py ├── test_script.py ├── requirements.txt │ ├── templates/ │ └── index.html │ ├── static/ │ ├── css/ │ │ └── style.css │ │ │ └── js/ │ └── script.js │ └── uploads/ Main Files File Description app.py Flask application and API routes analysis.py Dataset analysis and visualization logic chatbot.py Natural-language data analysis chatbot index.html Main web interface style.css UI styling script.js Frontend interaction and API communication requirements.txt Python dependencies test_script.py Testing data-analysis operations ⚙️ Installation

Clone the repository git clone https://github.com/YOUR_USERNAME/Agentic_Data_Analysts.git
Navigate to the project cd Agentic_Data_Analysts
Create a virtual environment
Windows:

python -m venv venv

Activate it:

venv\Scripts\activate

Linux/macOS:

python3 -m venv venv source venv/bin/activate 4. Install dependencies pip install -r "agentic data/agentic data/requirements.txt" 🔑 Gemini API Configuration

To enable AI-powered analysis, create a .env file inside the application directory.

GEMINI_API_KEY=your_api_key_here

Do not upload your .env file or API key to GitHub.

Add the following to .gitignore:

.env venv/ pycache/ .pyc uploads/ ▶️ Run the Application Navigate to the directory containing app.py:

cd "agentic data/agentic data"

Run:

python app.py

The Flask development server will start.

Open the URL shown in your terminal, usually:

http://127.0.0.1:5000 💬 Example Questions

After uploading a dataset, you can ask:

How many rows are there? Show me the column names Are there any missing values? What is the average salary? What is the maximum sales? Show the first 10 rows Which column has the highest mean? Show the correlation between numerical columns 📊 Supported File Formats

The application currently supports:

.csv .xls .xlsx

Maximum upload size:

16 MB 🔌 API Endpoints Home GET /

Displays the main application interface.

Upload Dataset POST /upload

Uploads and analyzes a CSV or Excel file.

Chat POST /chat

Accepts a natural-language question about the uploaded dataset.

Example request:

{ "query": "How many rows are there?" } Download Report GET /download-report

Generates and downloads a statistical summary report.

🔮 Future Enhancements 🔐 User authentication 🗄️ Database integration 📊 More advanced visualizations 🧠 More powerful AI agents 📑 PDF report generation ☁️ Cloud deployment 📁 Multiple dataset support 🔄 Persistent conversation history 🧹 Automated data cleaning 📈 Predictive analytics 🧪 Automated anomaly detection 🐳 Docker deployment 🎯 Use Cases

This project can be useful for:

Data analysts Students Business analysts Researchers Developers Non-technical users who want to explore datasets

Users can interact with their data using natural language instead of writing Python or SQL queries.

👩‍💻 Author

Kaniga K

Computer Science & Engineering (Cybersecurity)

Interested in:

Python Data Science Machine Learning Deep Learning Generative AI LLM Applications Cybersecurity ⭐ Project Highlights

An intelligent data-analysis assistant that transforms raw datasets into actionable insights through automated analytics, interactive visualizations, and natural-language AI interaction.

If you find this project useful, consider giving it a ⭐ on GitHub!
