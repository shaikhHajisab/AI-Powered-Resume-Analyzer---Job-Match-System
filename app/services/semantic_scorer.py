# app/services/semantic_scorer.py

import requests
import numpy as np
from app.core.config import settings

HF_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
HF_API_URL = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{HF_MODEL}"

# model handles max 256 word pieces comfortably
# beyond this quality degrades — better to chunk
MAX_CHARS = 800


def get_embedding(text: str) -> list[float]:
    """Get embedding from HuggingFace API"""
    headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}"}
    payload = {
        "inputs": text,
        "options": {"wait_for_model": True}
    }

    response = requests.post(
        HF_API_URL,
        headers=headers,
        json=payload,
        timeout=60
    )

    if response.status_code != 200:
        raise Exception(f"HF API error {response.status_code}: {response.text}")

    embedding = response.json()

    # flatten if nested list
    if isinstance(embedding[0], list):
        embedding = embedding[0]

    return embedding


def chunk_text(text: str, chunk_size: int = MAX_CHARS) -> list[str]:
    """
    Split long text into overlapping chunks.
    Overlap ensures skills that fall at a chunk boundary aren't lost.
    """
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    # 200 char overlap between chunks
    step = chunk_size - 200

    for i in range(0, len(text), step):
        chunk = text[i: i + chunk_size]
        if chunk.strip():
            chunks.append(chunk)
        # stop if we've covered all text
        if i + chunk_size >= len(text):
            break

    return chunks


def get_document_embedding(text: str) -> list[float]:
    """
    For long documents — chunk, embed each chunk, average the embeddings.
    Averaging works because embedding space is linear:
    average of chunk embeddings ≈ embedding of whole document
    """
    chunks = chunk_text(text)

    if len(chunks) == 1:
        return get_embedding(chunks[0])

    # get embedding for each chunk
    embeddings = []
    for chunk in chunks[:4]:  # max 4 chunks to stay within HF rate limits
        emb = get_embedding(chunk)
        embeddings.append(emb)

    # average all chunk embeddings
    # np.mean across axis=0 → average each dimension across all chunks
    averaged = np.mean(embeddings, axis=0).tolist()
    return averaged


def cosine_similarity_vectors(vec1: list[float], vec2: list[float]) -> float:
    """Cosine similarity between two vectors"""
    a = np.array(vec1)
    b = np.array(vec2)
    dot = np.dot(a, b)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    if norm == 0:
        return 0.0
    return float(dot / norm)


def calculate_semantic_score(resume_text: str, job_description: str) -> dict:
    """
    Semantic similarity using chunked embeddings.
    Handles long resumes properly.
    """
    # get embeddings — chunks handled internally
    resume_embedding = get_document_embedding(resume_text)
    jd_embedding = get_document_embedding(job_description)

    similarity = cosine_similarity_vectors(resume_embedding, jd_embedding)
    score = round(similarity * 100, 2)

    return {
        "semantic_score": score,
        "model_used": HF_MODEL,
        "chunks_used": len(chunk_text(resume_text))
    }