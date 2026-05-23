from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import Tuple
import re

def clean_text(text: str) -> str:
    """Basic text cleaning before vectorizing"""
    text = text.lower()
    text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_keywords(text: str, top_n: int = 20) -> list[str]:
    """
    Extract top N important keywords from text using TF-IDF.
    We fit on just this one document — IDF becomes 1 for all terms,
    so it reduces to TF ranking. Good enough for keyword extraction.
    """
    cleaned = clean_text(text)

    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        max_features=5000
    )

    tfidf_matrix = vectorizer.fit_transform([cleaned])
    feature_names = vectorizer.get_feature_names_out()
    scores = tfidf_matrix.toarray()[0]

    word_scores = list(zip(feature_names, scores))
    word_scores.sort(key=lambda x: x[1], reverse=True)

    return [word for word, score in word_scores[:top_n] if score > 0]

def calculate_tfidf_score(resume_text: str, job_description: str) -> dict:
    """
    Calculate match score between resume and job description.
    Returns score 0-100 plus matched and missing keywords.
    """
    cleaned_resume = clean_text(resume_text)
    cleaned_jd = clean_text(job_description)

    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        max_features=5000
    )

    tfidf_matrix = vectorizer.fit_transform([cleaned_resume, cleaned_jd])
    similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
    score = round(float(similarity) * 100, 2)

    jd_keywords = set(extract_keywords(job_description, top_n=20))
    resume_keywords = set(extract_keywords(resume_text, top_n=30))

    matched = list(jd_keywords & resume_keywords)
    missing = list(jd_keywords - resume_keywords)

    return {
        "tfidf_score": score,
        "matched_keywords": matched,
        "missing_keywords": missing,
    }

def calculate_final_score(tfidf_score: float, semantic_score: float) -> float:
    """
    Weighted combination of both scores.
    Semantic weighted higher — understands meaning not just keywords.
    """
    final = (tfidf_score * 0.4) + (semantic_score * 0.6)
    return round(final, 2)