from typing import Optional
from pydantic import BaseModel


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
