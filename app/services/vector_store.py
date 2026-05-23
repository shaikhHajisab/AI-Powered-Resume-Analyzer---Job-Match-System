import faiss
import numpy as np
import json
import os
import logging
from pathlib import Path
from app.services.semantic_scorer import get_embedding
from app.data.sample_jobs import SAMPLE_JOBS

logger = logging.getLogger(__name__)

# Resolve absolute paths safely
DATA_DIR = Path(__file__).parent.parent / "data"
INDEX_PATH = DATA_DIR / "jobs.index"
JOBS_META_PATH = DATA_DIR / "jobs_meta.json"

_index = None
_jobs_metadata = None

def build_index() -> None:
    global _index, _jobs_metadata

    logger.info("Building FAISS index from job descriptions...")
    embeddings = []
    metadata = []

    for job in SAMPLE_JOBS:
        text = f"{job['title']} {job['description']}"
        emb = get_embedding(text)
        embeddings.append(emb)
        metadata.append({
            "id": job["id"],
            "title": job["title"],
            "company": job["company"],
            "location": job["location"],
            "url": job["url"]
        })

    vectors = np.array(embeddings, dtype=np.float32)
    dimension = vectors.shape[1]

    faiss.normalize_L2(vectors)

    _index = faiss.IndexFlatIP(dimension)
    _index.add(vectors)

    faiss.write_index(_index, str(INDEX_PATH))
    with open(JOBS_META_PATH, "w") as f:
        json.dump(metadata, f)

    _jobs_metadata = metadata
    logger.info(f"FAISS index built: {_index.ntotal} jobs indexed")

def load_index() -> None:
    global _index, _jobs_metadata

    if INDEX_PATH.exists() and JOBS_META_PATH.exists():
        _index = faiss.read_index(str(INDEX_PATH))
        with open(JOBS_META_PATH, "r") as f:
            _jobs_metadata = json.load(f)
        logger.info(f"FAISS index loaded from disk: {_index.ntotal} jobs")
    else:
        logger.info("FAISS index files not found on disk. Building index...")
        build_index()

def get_similar_jobs(resume_text: str, top_k: int = 3) -> list[dict]:
    global _index, _jobs_metadata

    if _index is None:
        load_index()

    resume_emb = get_embedding(resume_text[:800])
    query_vector = np.array([resume_emb], dtype=np.float32)
    faiss.normalize_L2(query_vector)

    D, I = _index.search(query_vector, top_k)

    results = []
    for score, idx in zip(D[0], I[0]):
        if idx == -1:
            continue
        job = _jobs_metadata[idx].copy()
        job["similarity_score"] = round(float(score) * 100, 2)
        results.append(job)

    return results