# app/services/semantic_scorer.py

import requests
import numpy as np
from app.core.config import settings

# free model on hugging face — good balance of speed and quality
# 384 dimensional embeddings
HF_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
HF_API_URL = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{HF_MODEL}"


def get_embedding(text: str) -> list[float]:
    """
    Call Hugging Face API to get embedding vector for a text.
    Returns list of floats (384 numbers).
    """
    headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}"}

    # HF feature-extraction expects this format
    payload = {
        "inputs": text[:512],  # model max token limit — truncate long text
        "options": {"wait_for_model": True}  # wait if model is cold starting
    }

    response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=30)

    if response.status_code != 200:
        raise Exception(f"HuggingFace API error: {response.status_code} {response.text}")

    embedding = response.json()

    # HF returns nested list for some models — flatten if needed
    # shape can be (1, 384) or (384,) depending on model
    if isinstance(embedding[0], list):
        embedding = embedding[0]

    return embedding


def cosine_similarity_manual(vec1: list[float], vec2: list[float]) -> float:
    """
    Calculate cosine similarity between two vectors.
    Same math sklearn uses — doing it manually so you understand it.
    """
    a = np.array(vec1)
    b = np.array(vec2)

    # dot product
    dot = np.dot(a, b)

    # magnitudes
    magnitude_a = np.linalg.norm(a)
    magnitude_b = np.linalg.norm(b)

    # avoid division by zero
    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return float(dot / (magnitude_a * magnitude_b))


def calculate_semantic_score(resume_text: str, job_description: str) -> dict:
    """
    Get semantic similarity score between resume and job description.
    Uses Hugging Face embeddings + cosine similarity.
    """
    # get embeddings for both texts
    resume_embedding = get_embedding(resume_text[:1000])  # limit text length
    jd_embedding = get_embedding(job_description[:1000])

    # calculate similarity
    similarity = cosine_similarity_manual(resume_embedding, jd_embedding)

    # convert to 0-100
    score = round(similarity * 100, 2)

    return {
        "semantic_score": score,
        "model_used": HF_MODEL,
    }