import requests
import numpy as np
import time
from fastapi import HTTPException
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

HF_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
HF_API_URL = f"https://api-inference.huggingface.co/models/sentence-transformers/all-MiniLM-L6-v2"

MAX_CHARS = 800

def get_embedding(text: str, retries: int = 3, delay: int = 5) -> list[float]:
    headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}"}
    payload = {
        "inputs": text,
        "options": {"wait_for_model": True}
    }

    for attempt in range(retries):
        try:
            response = requests.post(
                HF_API_URL,
                headers=headers,
                json=payload,
                timeout=60
            )

            if response.status_code == 200:
                embedding = response.json()
                if isinstance(embedding[0], list):
                    embedding = embedding[0]
                return embedding
            
            logger.warning(f"HF API attempt {attempt + 1} failed: {response.status_code} - {response.text}")
            
        except requests.RequestException as e:
            logger.warning(f"HF API attempt {attempt + 1} exception: {str(e)}")

        if attempt < retries - 1:
            time.sleep(delay)

    raise HTTPException(status_code=503, detail="HuggingFace API unavailable after retries")


def chunk_text(text: str, chunk_size: int = MAX_CHARS) -> list[str]:
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    step = chunk_size - 200

    for i in range(0, len(text), step):
        chunk = text[i: i + chunk_size]
        if chunk.strip():
            chunks.append(chunk)
        if i + chunk_size >= len(text):
            break

    return chunks


def get_document_embedding(text: str) -> list[float]:
    chunks = chunk_text(text)

    if len(chunks) == 1:
        return get_embedding(chunks[0])

    embeddings = []
    for chunk in chunks[:4]:
        emb = get_embedding(chunk)
        embeddings.append(emb)

    averaged = np.mean(embeddings, axis=0).tolist()
    return averaged


def cosine_similarity_vectors(vec1: list[float], vec2: list[float]) -> float:
    a = np.array(vec1)
    b = np.array(vec2)
    dot = np.dot(a, b)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    if norm == 0:
        return 0.0
    return float(dot / norm)


def calculate_semantic_score(resume_text: str, job_description: str) -> dict:
    resume_embedding = get_document_embedding(resume_text)
    jd_embedding = get_document_embedding(job_description)

    similarity = cosine_similarity_vectors(resume_embedding, jd_embedding)
    score = round(similarity * 100, 2)

    return {
        "semantic_score": score,
        "model_used": HF_MODEL,
        "chunks_used": len(chunk_text(resume_text))
    }