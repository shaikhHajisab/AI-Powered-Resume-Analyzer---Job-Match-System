# app/services/ml_scorer.py

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import tuple
import re


def clean_text(text: str) -> str:
    """Basic text cleaning before vectorizing"""
    # lowercase everything
    text = text.lower()
    # remove special characters, keep letters numbers spaces
    text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text)
    # collapse multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_keywords(text: str, top_n: int = 20) -> list[str]:
    """
    Extract top N important keywords from text using TF-IDF.
    We fit on just this one document — IDF becomes 1 for all terms,
    so it reduces to TF ranking. Good enough for keyword extraction.
    """
    cleaned = clean_text(text)

    # TfidfVectorizer converts text to TF-IDF matrix
    # stop_words="english" removes common words (the, is, at, etc.)
    # ngram_range=(1,2) captures single words AND two-word phrases
    # "machine learning" scores higher than "machine" + "learning" separately
    # max_features limits vocabulary size
    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        max_features=5000
    )

    # fit_transform on a single document returns a sparse matrix
    tfidf_matrix = vectorizer.fit_transform([cleaned])

    # get feature names (the words/phrases)
    feature_names = vectorizer.get_feature_names_out()

    # get scores for this document (first row, convert sparse to array)
    scores = tfidf_matrix.toarray()[0]

    # pair each word with its score, sort descending, take top N
    word_scores = list(zip(feature_names, scores))
    word_scores.sort(key=lambda x: x[1], reverse=True)

    # return just the words (not scores)
    return [word for word, score in word_scores[:top_n] if score > 0]


def calculate_tfidf_score(resume_text: str, job_description: str) -> dict:
    """
    Calculate match score between resume and job description.
    Returns score 0-100 plus matched and missing keywords.
    """
    cleaned_resume = clean_text(resume_text)
    cleaned_jd = clean_text(job_description)

    # fit vectorizer on BOTH documents together
    # this way IDF is calculated across both — words rare in both score high
    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        max_features=5000
    )

    # transform both documents into TF-IDF vectors
    # tfidf_matrix shape: (2, vocabulary_size)
    tfidf_matrix = vectorizer.fit_transform([cleaned_resume, cleaned_jd])

    # cosine_similarity returns a 2x2 matrix
    # [0][1] = similarity between doc 0 (resume) and doc 1 (jd)
    similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]

    # convert to 0-100 scale
    score = round(float(similarity) * 100, 2)

    # --- keyword matching ---
    # extract top keywords from JD — these are what the employer wants
    jd_keywords = set(extract_keywords(job_description, top_n=20))

    # extract top keywords from resume — these are what candidate has
    resume_keywords = set(extract_keywords(resume_text, top_n=30))

    # matched = in both
    matched = list(jd_keywords & resume_keywords)

    # missing = employer wants but resume doesn't show
    missing = list(jd_keywords - resume_keywords)

    return {
        "tfidf_score": score,
        "matched_keywords": matched,
        "missing_keywords": missing,
    }