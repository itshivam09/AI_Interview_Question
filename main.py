import os
import uuid
import json
import datetime
from typing import Optional
from dotenv import load_dotenv, dotenv_values
from fastapi import FastAPI, UploadFile, File, Header, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import (
    init_db, get_db, 
    Resume, RAGChunk, InterviewSession, InterviewQuestion, InterviewAnswer
)
from rag_service import RAGService
from ai_interviewer import AIInterviewer

load_dotenv()
init_db()

app = FastAPI(
    title="RAG-Based AI Interviewer Platform",
    description="Intelligent AI Interview practice platform with resume RAG retrieval and scorecard.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag_service = RAGService()
ai_interviewer = AIInterviewer()


# 2. Pydantic request models
class StartInterviewRequest(BaseModel):
    resume_id: int
    target_role: str
    difficulty: str = "Mid-Level"
    total_questions: int = 5
    api_key: Optional[str] = None

class SubmitAnswerRequest(BaseModel):
    question_id: int
    candidate_answer: str
    api_key: Optional[str] = None


def resolve_api_key(explicit_key: Optional[str] = None, header_key: Optional[str] = None) -> Optional[str]:
    """Dynamically get Gemini API key from request, header, or .env file."""
    env_vals = dotenv_values(".env")
    key = explicit_key or header_key or env_vals.get("GEMINI_API_KEY") or env_vals.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    return str(key).strip("'\" ") if key else None


# 3. API Routes

@app.get("/api/health")
def health_check():
    """Check API status and verify if an API key is available."""
    return {
        "status": "online",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "has_server_gemini_key": bool(resolve_api_key())
    }


@app.post("/api/upload-resume")
async def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Step 1: Upload resume PDF/TXT, parse sections, index chunks for RAG."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    file_bytes = await file.read()
    raw_text = rag_service.extract_text_from_file(file_bytes, file.filename)
    if not raw_text or len(raw_text.strip()) < 50:
        raise HTTPException(status_code=400, detail="Could not extract readable text from resume.")

    sections = rag_service.parse_resume_sections(raw_text)
    resume = Resume(filename=file.filename, full_text=raw_text, parsed_sections=json.dumps(sections))
    db.add(resume)
    db.commit()
    db.refresh(resume)

    # Chunk and store in RAG table
    chunks = rag_service.chunk_resume(sections)
    for idx, c in enumerate(chunks):
        db.add(RAGChunk(
            resume_id=resume.id, chunk_index=idx,
            section_name=c.get("section", "GENERAL"), chunk_text=c.get("text", "")
        ))
    db.commit()

    return {
        "success": True,
        "resume_id": resume.id,
        "filename": resume.filename,
        "detected_sections": list(sections.keys()),
        "chunks_indexed": len(chunks),
        "text_preview": raw_text[:300] + "..."
    }


@app.post("/api/start-interview")
def start_interview(
    req: StartInterviewRequest,
    x_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Step 2: Generate tailored questions grounded in candidate's resume & role."""
    resume = db.query(Resume).filter_by(id=req.resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    sections = json.loads(resume.parsed_sections or "{}")
    chunks = db.query(RAGChunk).filter_by(resume_id=resume.id).all()
    chunk_dicts = [{"section": c.section_name, "text": c.chunk_text} for c in chunks]

    questions = ai_interviewer.generate_interview_questions(
        resume_sections=sections,
        chunks_sample=chunk_dicts,
        target_role=req.target_role,
        difficulty=req.difficulty,
        num_questions=req.total_questions,
        api_key_override=resolve_api_key(req.api_key, x_api_key)
    )

    session_id = str(uuid.uuid4())
    session = InterviewSession(
        id=session_id, resume_id=resume.id, target_role=req.target_role,
        difficulty=req.difficulty, total_questions=len(questions),
        current_question_index=1, status="in_progress"
    )
    db.add(session)

    first_question = None
    for idx, q in enumerate(questions, 1):
        db.add(InterviewQuestion(
            session_id=session_id, q_index=idx, question_text=q.get("question", ""),
            category=q.get("category", "Technical"), resume_context=q.get("resume_context", ""),
            ideal_points=json.dumps(q.get("ideal_points", []))
        ))
        if idx == 1:
            first_question = {
                "q_index": 1, "question_text": q.get("question", ""),
                "category": q.get("category", "Technical"), "resume_context": q.get("resume_context", "")
            }
    db.commit()

    return {
        "session_id": session_id, "target_role": req.target_role,
        "difficulty": req.difficulty, "total_questions": len(questions),
        "first_question": first_question
    }


@app.get("/api/session/{session_id}/question/{q_index}")
def get_question(session_id: str, q_index: int, db: Session = Depends(get_db)):
    """Step 3: Retrieve a specific question and candidate answer if already given."""
    session = db.query(InterviewSession).filter_by(id=session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")

    question = db.query(InterviewQuestion).filter_by(session_id=session_id, q_index=q_index).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    ans = db.query(InterviewAnswer).filter_by(question_id=question.id).first()
    ans_data = {
        "candidate_answer": ans.candidate_answer, "score": ans.score,
        "correctness_status": ans.correctness_status, "feedback": ans.feedback,
        "strengths": json.loads(ans.strengths or "[]"),
        "improvements": json.loads(ans.improvements or "[]"),
        "ideal_answer_summary": ans.ideal_answer_summary
    } if ans else None

    return {
        "session_id": session_id, "q_index": question.q_index, "question_id": question.id,
        "question_text": question.question_text, "category": question.category,
        "resume_context": question.resume_context, "total_questions": session.total_questions,
        "is_answered": ans is not None, "answer_data": ans_data
    }


@app.post("/api/session/{session_id}/submit-answer")
def submit_answer(
    session_id: str,
    req: SubmitAnswerRequest,
    x_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Step 4: Evaluate candidate answer with RAG resume verification and grading."""
    session = db.query(InterviewSession).filter_by(id=session_id).first()
    question = db.query(InterviewQuestion).filter_by(id=req.question_id, session_id=session_id).first()
    if not session or not question:
        raise HTTPException(status_code=404, detail="Session or question not found")

    # Fetch RAG context to verify claims against the resume
    chunks = db.query(RAGChunk).filter_by(resume_id=session.resume_id).all()
    relevant_chunks = rag_service.retrieve_relevant_chunks(
        query=f"{question.question_text} {req.candidate_answer[:200]}",
        chunk_texts=[c.chunk_text for c in chunks],
        chunk_metadata=[{"section": c.section_name} for c in chunks],
        top_k=3
    )

    eval_result = ai_interviewer.evaluate_candidate_answer(
        question_text=question.question_text, category=question.category,
        resume_context=question.resume_context, ideal_points=json.loads(question.ideal_points or "[]"),
        candidate_answer=req.candidate_answer, relevant_rag_chunks=relevant_chunks,
        api_key_override=resolve_api_key(req.api_key, x_api_key)
    )

    # Save or update candidate answer
    ans = db.query(InterviewAnswer).filter_by(question_id=question.id).first() or InterviewAnswer(question_id=question.id, session_id=session.id)
    ans.candidate_answer = req.candidate_answer
    ans.score = eval_result["score"]
    ans.correctness_status = eval_result["correctness_status"]
    ans.is_correct = eval_result["is_correct"]
    ans.feedback = eval_result["feedback"]
    ans.strengths = json.dumps(eval_result["strengths"])
    ans.improvements = json.dumps(eval_result["improvements"])
    ans.ideal_answer_summary = eval_result["ideal_answer_summary"]
    ans.submitted_at = datetime.datetime.utcnow()
    db.add(ans)

    if question.q_index >= session.current_question_index and question.q_index < session.total_questions:
        session.current_question_index = question.q_index + 1
    db.commit()

    has_next = question.q_index < session.total_questions
    return {
        "success": True, "evaluation": eval_result, "has_next": has_next,
        "next_q_index": question.q_index + 1 if has_next else None, "is_final_question": not has_next
    }


@app.get("/api/session/{session_id}/scorecard")
def get_scorecard(
    session_id: str,
    x_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Step 5: Generate complete scorecard, statistics, and hiring decision."""
    session = db.query(InterviewSession).filter_by(id=session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")

    questions = db.query(InterviewQuestion).filter_by(session_id=session_id).order_by(InterviewQuestion.q_index).all()
    qa_list = []
    for q in questions:
        ans = db.query(InterviewAnswer).filter_by(question_id=q.id).first()
        qa_list.append({
            "q_index": q.q_index, "question_id": q.id, "question": q.question_text, "category": q.category,
            "resume_context": q.resume_context, "candidate_answer": ans.candidate_answer if ans else "Not Answered",
            "score": ans.score if ans else 0.0, "correctness_status": ans.correctness_status if ans else "Incorrect",
            "is_correct": ans.is_correct if ans else False, "feedback": ans.feedback if ans else "Candidate did not submit an answer.",
            "strengths": json.loads(ans.strengths) if (ans and ans.strengths) else [],
            "improvements": json.loads(ans.improvements) if (ans and ans.improvements) else ["Answer was omitted."],
            "ideal_answer_summary": ans.ideal_answer_summary if ans else ""
        })

    summary = ai_interviewer.generate_overall_scorecard(
        questions_and_answers=qa_list, target_role=session.target_role,
        difficulty=session.difficulty, api_key_override=resolve_api_key(None, x_api_key)
    )

    session.overall_score = summary["overall_score"]
    session.correct_count = summary["correct_count"]
    session.partially_correct_count = summary["partially_correct_count"]
    session.incorrect_count = summary["incorrect_count"]
    session.hiring_recommendation = summary["hiring_recommendation"]
    session.summary_feedback = summary["summary_feedback"]
    session.skill_breakdown = json.dumps(summary["skill_breakdown"])
    session.status = "completed"
    session.completed_at = datetime.datetime.utcnow()
    db.commit()

    return {
        "session_id": session.id, "target_role": session.target_role, "difficulty": session.difficulty,
        "total_questions": session.total_questions, "overall_score": summary["overall_score"],
        "correct_count": summary["correct_count"], "partially_correct_count": summary["partially_correct_count"],
        "incorrect_count": summary["incorrect_count"], "hiring_recommendation": summary["hiring_recommendation"],
        "summary_feedback": summary["summary_feedback"], "top_strengths": summary.get("top_strengths", []),
        "areas_for_growth": summary.get("areas_for_growth", []), "skill_breakdown": summary["skill_breakdown"],
        "questions_review": qa_list
    }


# 4. Mount Static UI Files & Root Page
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def serve_index():
    return FileResponse("static/index.html")


if __name__ == "__main__":
    import uvicorn
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting RAG AI Interviewer server on http://{host}:{port}...")
    uvicorn.run("main:app", host=host, port=port, reload=True)
