import io
import re
import numpy as np
from typing import List, Dict, Optional
from pypdf import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Common section keywords in resumes
SECTION_KEYWORDS = {
    "SUMMARY": ["summary", "profile", "objective", "about me"],
    "SKILLS": ["skills", "technologies", "competencies", "tools"],
    "PROJECTS": ["projects", "key projects", "academic projects"],
    "EXPERIENCE": ["experience", "employment", "work history", "internship"],
    "EDUCATION": ["education", "academic", "qualifications"],
    "CERTIFICATIONS": ["certification", "licenses", "awards", "achievements"]
}


class RAGService:
    """
    Simple 4-Step RAG Pipeline:
    1. extract_text_from_file -> Read PDF or TXT
    2. parse_resume_sections  -> Group text into sections (SKILLS, PROJECTS, etc.)
    3. chunk_resume           -> Split text into small searchable paragraphs
    4. retrieve_relevant_chunks -> Search most relevant chunks using similarity
    """
    def __init__(self, gemini_api_key: Optional[str] = None):
        self.api_key = gemini_api_key

    def extract_text_from_file(self, file_bytes: bytes, filename: str) -> str:
        """Step 1: Extract text from PDF or TXT file."""
        if filename.lower().endswith(".pdf"):
            reader = PdfReader(io.BytesIO(file_bytes))
            return "\n\n".join(page.extract_text().strip() for page in reader.pages if page.extract_text())
        return file_bytes.decode("utf-8", errors="replace").strip()

    def parse_resume_sections(self, text: str) -> Dict[str, str]:
        """Step 2: Group resume text into logical sections."""
        sections: Dict[str, List[str]] = {"GENERAL": []}
        current_sec = "GENERAL"

        for line in text.splitlines():
            cleaned = line.strip()
            if not cleaned:
                continue

            # Check if line looks like a section header
            line_lower = re.sub(r"[#\*\-\:\d\.]+", " ", cleaned).strip().lower()
            if len(line_lower) < 40:
                matched = next((sec for sec, words in SECTION_KEYWORDS.items() if any(w in line_lower for w in words)), None)
                if matched:
                    current_sec = matched
                    sections.setdefault(current_sec, [])
                    continue

            sections.setdefault(current_sec, []).append(cleaned)

        return {sec: "\n".join(lines) for sec, lines in sections.items() if lines}

    def chunk_resume(self, sections: Dict[str, str], max_words: int = 180) -> List[Dict[str, str]]:
        """Step 3: Split sections into small paragraph chunks for AI retrieval."""
        chunks = []
        for sec, content in sections.items():
            paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
            for p in paragraphs:
                words = p.split()
                if len(words) <= max_words:
                    if len(words) >= 4:
                        chunks.append({"section": sec, "text": p})
                else:
                    for i in range(0, len(words), max_words - 20):
                        sub = " ".join(words[i:i + max_words])
                        if len(sub.split()) >= 4:
                            chunks.append({"section": sec, "text": sub})

        return chunks or [{"section": "GENERAL", "text": " ".join(sections.values())}]

    def retrieve_relevant_chunks(
        self, query: str, chunk_texts: List[str], chunk_metadata: List[Dict], top_k: int = 3
    ) -> List[Dict]:
        """Step 4: Search and return top matching resume chunks using TF-IDF similarity."""
        if not chunk_texts:
            return []

        try:
            vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
            tfidf_matrix = vectorizer.fit_transform(chunk_texts)
            query_vec = vectorizer.transform([query])
            scores = cosine_similarity(query_vec, tfidf_matrix).flatten()

            top_indices = np.argsort(scores)[::-1][:top_k]
            return [
                {
                    "text": chunk_texts[i],
                    "section": chunk_metadata[i].get("section", "GENERAL"),
                    "similarity": round(float(scores[i]), 4)
                }
                for i in top_indices
            ]
        except Exception:
            # Simple keyword matching fallback
            q_words = set(query.lower().split())
            scored = sorted(
                enumerate(chunk_texts),
                key=lambda item: len(q_words.intersection(set(item[1].lower().split()))),
                reverse=True
            )
            return [
                {"text": text, "section": chunk_metadata[i].get("section", "GENERAL"), "similarity": 0.5}
                for i, text in scored[:top_k]
            ]
