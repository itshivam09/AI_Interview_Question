import sys
import os

# Ensure server folder is in Python path
SERVER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server")
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

from server.main import app

if __name__ == "__main__":
    import uvicorn
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting RAG AI Interviewer server on http://{host}:{port}...")
    uvicorn.run("main:app", host=host, port=port, reload=True)
