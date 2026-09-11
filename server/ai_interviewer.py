import os
import json
import re
from typing import List, Dict, Any, Optional

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


def clean_json_response(raw_text: str) -> Any:
    """Extract and parse valid JSON from AI output without complex regex."""
    text = raw_text.strip()

    # 1. Remove markdown code blocks if present (e.g. ```json ... ```)
    if text.startswith("```"):
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1:]  # remove the first line (```json)
        if text.endswith("```"):
            text = text[:-3]                 # remove the closing ```
        text = text.strip()

    # 2. Try parsing the clean text directly
    try:
        return json.loads(text)
    except Exception:
        pass

    # 3. If AI added introductory or ending text, find the { } or [ ] portion
    start_brace = text.find("{")
    end_brace = text.rfind("}")
    start_bracket = text.find("[")
    end_bracket = text.rfind("]")

    if start_brace != -1 and end_brace != -1 and (start_bracket == -1 or start_brace < start_bracket):
        return json.loads(text[start_brace : end_brace + 1])
    elif start_bracket != -1 and end_bracket != -1:
        return json.loads(text[start_bracket : end_bracket + 1])

    raise ValueError("Could not find valid JSON in AI response.")


class AIInterviewer:
    """
    Beginner-Friendly AI Interviewer:
    1. generate_interview_questions -> Asks Gemini to tailor questions based on candidate's resume
    2. evaluate_candidate_answer     -> Scores candidate answer (0-10) with RAG resume verification
    3. generate_overall_scorecard    -> Aggregates performance, skill breakdown & hiring recommendation
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    def _get_client(self, api_key_override: Optional[str] = None):
        """Initializes Gemini Client using key from request, constructor, or .env file."""
        from dotenv import dotenv_values
        root_env = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
        env_vals = dotenv_values(root_env) if os.path.exists(root_env) else dotenv_values(".env")
        key = (
            api_key_override
            or self.api_key
            or env_vals.get("GEMINI_API_KEY")
            or env_vals.get("GOOGLE_API_KEY")
            or os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
        )
        if not key:
            raise ValueError("GEMINI_API_KEY is not configured in .env or environment.")
        if not GENAI_AVAILABLE:
            raise RuntimeError("google-genai package is not installed.")
        return genai.Client(api_key=str(key).strip("'\" "))

    def _generate(self, client, prompt: str, system_instruction: str, temperature: float = 0.3):
        """Calls Gemini models with automatic fallback."""
        models = ["gemini-3.6-flash", "gemini-3.7-flash", "gemini-flash-latest"]
        last_error = RuntimeError("All Gemini models failed.")
        for model in models:
            try:
                return client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=temperature,
                        response_mime_type="application/json"
                    )
                )
            except Exception as err:
                last_error = err
                continue
        raise last_error

    def generate_interview_questions(
        self,
        resume_sections: Dict[str, str],
        chunks_sample: List[Dict[str, str]],
        target_role: str,
        difficulty: str = "Mid-Level",
        num_questions: int = 5,
        api_key_override: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Step 1: Ask Gemini to generate tailored questions grounded in candidate's resume."""
        resume_summary = "\n".join([f"### {sec}\n{text[:600]}" for sec, text in resume_sections.items()])
        prompt = f"""
Role: {target_role} | Difficulty: {difficulty} | Number of Questions: {num_questions}
Candidate's Resume:
{resume_summary}

Generate exactly {num_questions} interview questions covering:
- 'Project Deep Dive': Architecture and trade-offs of their projects.
- 'Technical Core': Fundamental languages and frameworks from resume.
- 'Problem Solving': Real-world scenario for {target_role}.

Return strictly JSON list:
[
  {{
    "question": "Question text...",
    "category": "Project Deep Dive",
    "resume_context": "Project from resume...",
    "ideal_points": ["Key technical point 1", "Key technical point 2"]
  }}
]
"""
        try:
            client = self._get_client(api_key_override)
            res = self._generate(client, prompt, "You are an expert technical interviewer.", temperature=0.3)
            data = clean_json_response(res.text)
            return (data if isinstance(data, list) else data.get("questions", []))[:num_questions]
        except Exception as e:
            print(f"Question Generation error ({e}), using fallback questions.")
            return self._fallback_questions(resume_sections, target_role, num_questions)

    def evaluate_candidate_answer(
        self,
        question_text: str,
        category: str,
        resume_context: str,
        ideal_points: List[str],
        candidate_answer: str,
        relevant_rag_chunks: List[Dict],
        api_key_override: Optional[str] = None
    ) -> Dict[str, Any]:
        """Step 2: Score candidate's answer (0-10) using resume RAG context and ideal criteria."""
        rag_text = "\n".join([f"- [{c.get('section', 'RESUME')}]: {c.get('text')}" for c in relevant_rag_chunks])
        prompt = f"""
Question: {question_text}
Category: {category} | Resume Grounding: {resume_context}
Resume Evidence (RAG):
{rag_text}
Ideal Evaluation Points:
{json.dumps(ideal_points)}

Candidate's Answer:
\"{candidate_answer.strip()}\"

Grading Guidelines:
- Score: 0.0 to 10.0
- Correctness Status: "Correct" (>=8.0), "Partially Correct" (5.0 - 7.9), or "Incorrect" (<5.0)

Return strictly JSON:
{{
  "score": 8.5,
  "correctness_status": "Correct",
  "is_correct": true,
  "feedback": "2-3 sentences of feedback.",
  "strengths": ["Strength 1", "Strength 2"],
  "improvements": ["Improvement 1"],
  "ideal_answer_summary": "Ideal answer overview."
}}
"""
        try:
            client = self._get_client(api_key_override)
            res = self._generate(client, prompt, "You are a fair technical interviewer and grader.", temperature=0.2)
            data = clean_json_response(res.text)
            score = float(data.get("score", 5.0))
            status = data.get("correctness_status") or ("Correct" if score >= 8.0 else "Partially Correct" if score >= 5.0 else "Incorrect")
            return {
                "score": round(score, 1),
                "correctness_status": status,
                "is_correct": score >= 7.5,
                "feedback": data.get("feedback", "Answer evaluated."),
                "strengths": data.get("strengths", ["Addressed the question"]),
                "improvements": data.get("improvements", ["Provide deeper technical details"]),
                "ideal_answer_summary": data.get("ideal_answer_summary", "Detailed explanation required.")
            }
        except Exception as e:
            print(f"Evaluation error ({e}), using fallback evaluation.")
            return self._fallback_evaluate(candidate_answer)

    def generate_overall_scorecard(
        self,
        questions_and_answers: List[Dict[str, Any]],
        target_role: str,
        difficulty: str,
        api_key_override: Optional[str] = None
    ) -> Dict[str, Any]:
        """Step 3: Summarize interview results, calculate statistics, and provide recommendation."""
        total = len(questions_and_answers)
        if total == 0:
            return {"overall_score": 0.0, "correct_count": 0, "partially_correct_count": 0, "incorrect_count": 0, "hiring_recommendation": "Incomplete", "summary_feedback": "No answers given.", "skill_breakdown": {}}

        total_score = sum(q.get("score", 0.0) for q in questions_and_answers)
        percentage = round((total_score / (total * 10.0)) * 100, 1)

        correct = sum(1 for q in questions_and_answers if q.get("correctness_status") == "Correct")
        partial = sum(1 for q in questions_and_answers if q.get("correctness_status") == "Partially Correct")
        incorrect = sum(1 for q in questions_and_answers if q.get("correctness_status") == "Incorrect")

        # Category scores
        category_scores: Dict[str, List[float]] = {}
        for qa in questions_and_answers:
            cat = qa.get("category", "General")
            category_scores.setdefault(cat, []).append(qa.get("score", 0.0) * 10)
        skill_breakdown = {cat: round(sum(s) / len(s), 1) for cat, s in category_scores.items()}

        prompt = f"""
Candidate scored {percentage}% for role {target_role} ({difficulty}).
Questions summary:
{json.dumps([{'question': qa['question'], 'status': qa.get('correctness_status'), 'score': qa.get('score')} for qa in questions_and_answers])}

Return strictly JSON:
{{
  "hiring_recommendation": "Strong Hire" | "Hire" | "Needs Improvement" | "Not Recommended",
  "summary_feedback": "3-4 sentence comprehensive evaluation.",
  "top_strengths": ["Strength 1", "Strength 2"],
  "areas_for_growth": ["Growth area 1", "Growth area 2"]
}}
"""
        rec_default = "Strong Hire" if percentage >= 85 else "Hire" if percentage >= 70 else "Needs Improvement" if percentage >= 50 else "Not Recommended"
        try:
            client = self._get_client(api_key_override)
            res = self._generate(client, prompt, "You are an executive hiring manager.", temperature=0.3)
            data = clean_json_response(res.text)
            return {
                "overall_score": percentage,
                "correct_count": correct,
                "partially_correct_count": partial,
                "incorrect_count": incorrect,
                "hiring_recommendation": data.get("hiring_recommendation", rec_default),
                "summary_feedback": data.get("summary_feedback", f"Candidate scored {percentage}%."),
                "top_strengths": data.get("top_strengths", ["Solid foundational knowledge"]),
                "areas_for_growth": data.get("areas_for_growth", ["Explore architecture trade-offs"]),
                "skill_breakdown": skill_breakdown
            }
        except Exception:
            return {
                "overall_score": percentage,
                "correct_count": correct,
                "partially_correct_count": partial,
                "incorrect_count": incorrect,
                "hiring_recommendation": rec_default,
                "summary_feedback": f"Candidate completed the interview with a final score of {percentage}%.",
                "top_strengths": ["Completed technical questions"],
                "areas_for_growth": ["Deepen edge case considerations"],
                "skill_breakdown": skill_breakdown
            }

    def _fallback_questions(self, resume_sections: Dict[str, str], target_role: str, count: int) -> List[Dict[str, Any]]:
        """Fallback question set when Gemini is offline or rate-limited."""
        projects = resume_sections.get("PROJECTS", "Application development")[:100]
        skills = resume_sections.get("SKILLS", "Python, APIs, Databases")[:60]
        defaults = [
            {"question": f"Walk me through the architecture of a major project listed on your resume: {projects}. How did you structure components?", "category": "Project Deep Dive", "resume_context": projects, "ideal_points": ["System design", "Database schema", "Error handling"]},
            {"question": f"You mentioned experience with {skills}. Describe a difficult bug you solved using these tools.", "category": "Problem Solving", "resume_context": skills, "ideal_points": ["Root cause analysis", "Testing", "Solution trade-offs"]},
            {"question": f"For a {target_role} role, how do you ensure high performance, security, and test coverage?", "category": "Technical Core", "resume_context": target_role, "ideal_points": ["Testing", "Security", "Query optimization"]},
            {"question": "How do you handle async tasks, database transactions, and concurrency under high traffic?", "category": "System Architecture", "resume_context": "Best practices", "ideal_points": ["Concurrency", "Transactions", "Monitoring"]},
            {"question": "Describe a time you quickly learned a new technology under tight deadlines.", "category": "Behavioral", "resume_context": "Experience", "ideal_points": ["STAR approach", "Proactive learning", "Impact"]}
        ]
        return defaults[:count]

    def _fallback_evaluate(self, candidate_answer: str) -> Dict[str, Any]:
        """Simple word-count heuristic evaluator when Gemini is offline."""
        words = len(candidate_answer.strip().split())
        if words < 10:
            return {"score": 3.0, "correctness_status": "Incorrect", "is_correct": False, "feedback": "Answer was too brief.", "strengths": ["Attempted response"], "improvements": ["Provide concrete technical mechanisms."], "ideal_answer_summary": "Thorough explanation required."}
        elif words < 35:
            return {"score": 6.5, "correctness_status": "Partially Correct", "is_correct": False, "feedback": "Good direction, but lacks depth.", "strengths": ["Understands basic premise"], "improvements": ["Include architectural trade-offs."], "ideal_answer_summary": "Comprehensive explanation required."}
        else:
            return {"score": 8.5, "correctness_status": "Correct", "is_correct": True, "feedback": "Thorough and technically sound explanation.", "strengths": ["Detailed explanation", "Demonstrates practical knowledge"], "improvements": ["Mention monitoring or future scalability."], "ideal_answer_summary": "Strong technical answer."}
