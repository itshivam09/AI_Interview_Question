import datetime
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from database import Base


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)
    full_text = Column(Text, nullable=False)
    parsed_sections = Column(Text, default="{}")  # JSON string

    chunks = relationship("RAGChunk", back_populates="resume", cascade="all, delete-orphan")
    sessions = relationship("InterviewSession", back_populates="resume")


class RAGChunk(Base):
    __tablename__ = "rag_chunks"

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    section_name = Column(String(100), default="General")
    chunk_text = Column(Text, nullable=False)
    embedding = Column(Text, default="[]")  # JSON array of floats

    resume = relationship("Resume", back_populates="chunks")


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(String(64), primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False)
    target_role = Column(String(100), nullable=False)
    difficulty = Column(String(50), default="Mid-Level")
    total_questions = Column(Integer, default=5)
    current_question_index = Column(Integer, default=0)
    status = Column(String(50), default="in_progress")  # in_progress, completed
    
    # Scorecard statistics
    overall_score = Column(Float, default=0.0)  # 0 to 100 percentage
    correct_count = Column(Integer, default=0)
    partially_correct_count = Column(Integer, default=0)
    incorrect_count = Column(Integer, default=0)
    hiring_recommendation = Column(String(100), default="")
    summary_feedback = Column(Text, default="")
    skill_breakdown = Column(Text, default="{}")  # JSON metrics

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    resume = relationship("Resume", back_populates="sessions")
    questions = relationship("InterviewQuestion", back_populates="session", cascade="all, delete-orphan", order_by="InterviewQuestion.q_index")


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False)
    q_index = Column(Integer, nullable=False)
    question_text = Column(Text, nullable=False)
    category = Column(String(100), default="Technical")
    resume_context = Column(Text, default="")
    ideal_points = Column(Text, default="[]")  # JSON list of strings

    session = relationship("InterviewSession", back_populates="questions")
    answer = relationship("InterviewAnswer", back_populates="question", uselist=False, cascade="all, delete-orphan")


class InterviewAnswer(Base):
    __tablename__ = "interview_answers"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("interview_questions.id", ondelete="CASCADE"), unique=True, nullable=False)
    session_id = Column(String(64), ForeignKey("interview_sessions.id"), nullable=False)
    candidate_answer = Column(Text, nullable=False)
    
    # Grading metrics
    score = Column(Float, default=0.0)  # 0 to 10
    correctness_status = Column(String(50), default="Incorrect")  # Correct, Partially Correct, Incorrect
    is_correct = Column(Boolean, default=False)
    feedback = Column(Text, default="")
    strengths = Column(Text, default="[]")  # JSON list
    improvements = Column(Text, default="[]")  # JSON list
    ideal_answer_summary = Column(Text, default="")
    submitted_at = Column(DateTime, default=datetime.datetime.utcnow)

    question = relationship("InterviewQuestion", back_populates="answer")
