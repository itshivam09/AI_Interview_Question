import os
import sys
import json

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fastapi.testclient import TestClient
from main import app
from database import init_db, SessionLocal
from models import Resume, InterviewSession
from rag_service import RAGService
from ai_interviewer import AIInterviewer

def test_full_pipeline():
    print("--- [1] Initializing Database ---")
    init_db()
    db = SessionLocal()
    assert db is not None, "Failed to connect to SQLite"
    print("[OK] SQLite initialized successfully.")

    print("\n--- [2] Testing RAG Service Chunking & Extraction ---")
    rag = RAGService()
    with open("sample_resume.txt", "rb") as f:
        resume_bytes = f.read()
    
    extracted_text = rag.extract_text_from_file(resume_bytes, "sample_resume.txt")
    assert len(extracted_text) > 100, "Text extraction failed"
    print(f"[OK] Extracted {len(extracted_text)} characters.")

    sections = rag.parse_resume_sections(extracted_text)
    print(f"[OK] Detected Sections: {list(sections.keys())}")
    assert "PROJECTS" in sections or "SKILLS" in sections, "Key sections not parsed"

    chunks = rag.chunk_resume(sections)
    print(f"[OK] Created {len(chunks)} RAG chunks.")
    assert len(chunks) > 0, "No chunks created"

    # Test retrieval
    chunk_texts = [c["text"] for c in chunks]
    chunk_meta = [{"section": c["section"]} for c in chunks]
    retrieved = rag.retrieve_relevant_chunks("payment microservice redis latency", chunk_texts, chunk_meta, top_k=2)
    print(f"[OK] Retrieved {len(retrieved)} relevant chunks for query.")
    print(f"  Top Match (Score: {retrieved[0]['similarity']}): {retrieved[0]['text'][:80]}...")

    print("\n--- [3] Testing FastAPI Endpoints with TestClient ---")
    client = TestClient(app)

    # Health check
    res = client.get("/api/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    print(f"[OK] Health Check: {res.json()}")

    # Upload Resume
    with open("sample_resume.txt", "rb") as f:
        res = client.post(
            "/api/upload-resume",
            files={"file": ("sample_resume.txt", f, "text/plain")}
        )
    assert res.status_code == 200, f"Upload failed: {res.text}"
    upload_data = res.json()
    resume_id = upload_data["resume_id"]
    print(f"[OK] Uploaded resume ID: {resume_id} ({upload_data['chunks_indexed']} chunks)")

    # Start Interview
    res = client.post(
        "/api/start-interview",
        json={
            "resume_id": resume_id,
            "target_role": "Full Stack / Python Developer",
            "difficulty": "Mid-Level",
            "total_questions": 3
        }
    )
    assert res.status_code == 200, f"Start interview failed: {res.text}"
    start_data = res.json()
    session_id = start_data["session_id"]
    total_q = start_data["total_questions"]
    print(f"[OK] Started session {session_id} with {total_q} questions.")

    # Get First Question
    res = client.get(f"/api/session/{session_id}/question/1")
    assert res.status_code == 200, f"Get question failed: {res.text}"
    q1 = res.json()
    print(f"[OK] Question 1: '{q1['question_text'][:70]}...'")

    # Submit Good Answer (Correct)
    print("\n--- [4] Submitting Strong Answer (Expecting Correct) ---")
    good_answer = (
        "In our payment microservice, we structured the architecture using FastAPI's asynchronous route handlers "
        "combined with Redis caching for idempotent transaction verification. We used connection pooling with SQLAlchemy "
        "and configured database transaction isolation levels to Serializable on payment webhooks to prevent race conditions "
        "and double-spend anomalies. We verified this using pytest with high concurrency simulated via Locust."
    )
    res = client.post(
        f"/api/session/{session_id}/submit-answer",
        json={
            "question_id": q1["question_id"],
            "candidate_answer": good_answer
        }
    )
    assert res.status_code == 200, f"Submit answer 1 failed: {res.text}"
    ans1_eval = res.json()["evaluation"]
    print(f"[OK] Answer 1 Result: Status='{ans1_eval['correctness_status']}', Score={ans1_eval['score']}/10")

    # Submit Second Answer (Partially Correct / Incomplete)
    print("\n--- [5] Submitting Weak Answer (Expecting Partially Correct or Incorrect) ---")
    res = client.get(f"/api/session/{session_id}/question/2")
    q2 = res.json()
    weak_answer = "I used python and wrote some code."
    res = client.post(
        f"/api/session/{session_id}/submit-answer",
        json={
            "question_id": q2["question_id"],
            "candidate_answer": weak_answer
        }
    )
    assert res.status_code == 200, f"Submit answer 2 failed: {res.text}"
    ans2_eval = res.json()["evaluation"]
    print(f"[OK] Answer 2 Result: Status='{ans2_eval['correctness_status']}', Score={ans2_eval['score']}/10")

    # Fetch Final Scorecard
    print("\n--- [6] Fetching Final Scorecard & Statistics ---")
    res = client.get(f"/api/session/{session_id}/scorecard")
    assert res.status_code == 200, f"Scorecard generation failed: {res.text}"
    card = res.json()
    print(f"[OK] Overall Score: {card['overall_score']}%")
    print(f"[OK] Recommendation: {card['hiring_recommendation']}")
    print(f"[OK] Breakdown: Correct={card['correct_count']}, Partial={card['partially_correct_count']}, Incorrect={card['incorrect_count']}")
    print(f"[OK] Questions in Review: {len(card['questions_review'])}")
    assert len(card['questions_review']) == total_q, "All questions should be listed in review"
    print("\n========================================================")
    print(">>> ALL VERIFICATION TESTS PASSED SUCCESSFULLY! <<<")
    print("========================================================")

if __name__ == "__main__":
    test_full_pipeline()
