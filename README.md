# 🎯 AI Interview Question & Evaluation System (RAG-Powered)

An intelligent, full-stack AI interview practice platform powered by **FastAPI**, **Google Gemini**, and **RAG (Retrieval-Augmented Generation)** with SQLite vector storage.

---

## 🌟 Key Features

- **📄 Resume Analysis & Ingestion**: Upload resumes in PDF or plain text format; automatically parsed into chunks.
- **🔍 RAG Vector Retrieval**: Generates contextual questions tailored directly to the candidate's specific projects, work history, and skills.
- **🤖 Adaptive AI Interviewer**: Conducts realistic multi-question technical and behavioral interviews customized to difficulty level and target role.
- **📊 Real-Time Scorecard & Evaluation**: Instant multi-dimensional scoring (accuracy, depth, structure, clarity) with constructive feedback on candidate answers.
- **🎨 Interactive Web UI**: Modern, responsive dark-themed interface built with Vanilla JS and CSS.
- **🔐 Flexible API Key Management**: Provide Gemini API keys through `.env`, HTTP headers, or dynamic UI input.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.10+, FastAPI, Uvicorn, SQLAlchemy, Pydantic
- **AI & Embeddings**: Google Gemini API (`google-genai`), NumPy cosine similarity
- **Database**: SQLite (with relational models for sessions, questions, answers, and RAG embeddings)
- **Frontend**: HTML5, CSS3, Modern JavaScript (Vanilla)

---

## 🚀 Getting Started

### 1. Prerequisites

- Python 3.10 or higher
- A Google Gemini API Key (obtain from [Google AI Studio](https://aistudio.google.com/))

### 2. Clone the Repository

```bash
git clone https://github.com/itshivam09/AI_Interview_Question.git
cd AI_Interview_Question
```

### 3. Set Up Virtual Environment

```bash
# Windows
python -m venv myenv
myenv\Scripts\activate

# Linux / macOS
python3 -m venv myenv
source myenv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables

Copy the example configuration file and add your Gemini API key:

```bash
cp .env.example .env
```

Edit `.env`:
```env
GEMINI_API_KEY="your_actual_gemini_api_key"
HOST=127.0.0.1
PORT=8000
```

### 6. Run the Application

```bash
# Run with Python
python main.py

# Or with Uvicorn
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Open your browser and navigate to:
```
http://127.0.0.1:8000
```

---

## 📁 Project Structure

```
AI_Interview_Question/
├── main.py                     # Root FastAPI application entrypoint & static mount
│
├── client/                     # Frontend UI assets
│   ├── index.html              # Main HTML application
│   ├── css/
│   │   └── style.css           # Modern dark-theme styling
│   └── js/
│       └── app.js              # Frontend logic & API interaction
│
├── server/                     # Backend Python business logic
│   ├── routes.py               # REST API endpoints (APIRouter)
│   ├── database.py             # DB connection & session engine
│   ├── models.py               # SQLAlchemy database tables
│   ├── schemas.py              # Pydantic request models
│   ├── rag_service.py          # Resume parsing & chunk retrieval (RAG)
│   ├── ai_interviewer.py       # Gemini AI interviewer & evaluation engine
│   ├── sample_resume.txt       # Sample resume for quick testing
│   └── test_system.py          # System and integration tests
│
├── .env.example                # Environment variables template
├── .gitignore                  # Git ignore rules for secrets and temp files
├── render.yaml                 # Render cloud deployment blueprint
├── requirements.txt            # Python dependencies
└── README.md                   # Project documentation
```

---

## ☁️ Deployment Guides

### Deploy to Render (Recommended - Free & 1-Click)

1. Sign up / Log in to [Render](https://render.com/).
2. Click **New +** -> **Web Service**.
3. Connect your GitHub repository: `https://github.com/itshivam09/AI_Interview_Question`.
4. Configure settings:
   - **Name**: `ai-interview-platform`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Under **Environment Variables**, add:
   - `GEMINI_API_KEY`: `your_gemini_api_key`
   - `PYTHON_VERSION`: `3.11.9`
6. Click **Create Web Service**. Your app is live!



## 📄 License & Terms

Copyright (c) 2026 Shivam Yadav. All Rights Reserved.

This project is made available for educational and personal viewing/demonstration purposes only.
You may view and run the code locally, but you are not permitted to modify, resell, or redistribute it without explicit permission.
