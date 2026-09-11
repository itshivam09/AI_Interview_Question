import os
import sys
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Ensure server folder is in Python path
SERVER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server")
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

from server.database import init_db
from server.routes import router as api_router

# Load environment & initialize DB tables
load_dotenv()
init_db()

app = FastAPI(
    title="RAG-Based AI Interviewer Platform",
    description="Intelligent AI Interview practice platform with resume RAG retrieval and scorecard.",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. Register API Routes
app.include_router(api_router)

# 2. Mount Client Frontend & Serve Index
CLIENT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "client"))

if os.path.exists(CLIENT_DIR):
    app.mount("/static", StaticFiles(directory=CLIENT_DIR), name="static")

@app.get("/")
def serve_index():
    index_file = os.path.join(CLIENT_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "AI Interviewer API is running."}


if __name__ == "__main__":
    import uvicorn
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting RAG AI Interviewer server on http://{host}:{port}...")
    uvicorn.run("main:app", host=host, port=port, reload=True)
