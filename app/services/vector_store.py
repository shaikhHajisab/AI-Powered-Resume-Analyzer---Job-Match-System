
import faiss
import numpy as np
import json
import os
from app.services.semantic_scorer import get_embedding
from app.data.sample_jobs import SAMPLE_JOBS

# path to save the FAISS index on disk
# persisting means we don't rebuild it on every app restart
INDEX_PATH = "app/data/jobs.index"
JOBS_META_PATH = "app/data/jobs_meta.json"

# global variables — index loaded once when app starts
_index = None
_jobs_metadata = None


def build_index() -> None:
    """
    Build FAISS index from sample jobs.
    Called once at startup or when jobs data changes.
    """
    global _index, _jobs_metadata

    print("Building FAISS index from job descriptions...")
    embeddings = []
    metadata = []

    for job in SAMPLE_JOBS:
        # embed the job description
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

    # convert to numpy array — FAISS requires float32
    vectors = np.array(embeddings, dtype=np.float32)

    # dimension = length of each embedding vector (384 for MiniLM)
    dimension = vectors.shape[1]

    # IndexFlatIP = flat index with inner product similarity
    # for normalized vectors inner product == cosine similarity
    # normalize vectors first
    faiss.normalize_L2(vectors)  # normalizes in place

    _index = faiss.IndexFlatIP(dimension)
    _index.add(vectors)  # add all job vectors to the index

    # save to disk
    faiss.write_index(_index, INDEX_PATH)
    with open(JOBS_META_PATH, "w") as f:
        json.dump(metadata, f)

    _jobs_metadata = metadata
    print(f"FAISS index built: {_index.ntotal} jobs indexed")


def load_index() -> None:
    """Load existing FAISS index from disk"""
    global _index, _jobs_metadata

    if os.path.exists(INDEX_PATH) and os.path.exists(JOBS_META_PATH):
        _index = faiss.read_index(INDEX_PATH)
        with open(JOBS_META_PATH, "r") as f:
            _jobs_metadata = json.load(f)
        print(f"FAISS index loaded: {_index.ntotal} jobs")
    else:
        # index doesn't exist yet — build it
        build_index()


def get_similar_jobs(resume_text: str, top_k: int = 3) -> list[dict]:
    """
    Find top_k most similar jobs to the resume.
    Uses cosine similarity via FAISS inner product on normalized vectors.
    """
    global _index, _jobs_metadata

    # load index if not already loaded
    if _index is None:
        load_index()

    # embed the resume
    resume_emb = get_embedding(resume_text[:800])

    # convert to numpy float32 — FAISS requirement
    query_vector = np.array([resume_emb], dtype=np.float32)

    # normalize query vector (same as we did for index vectors)
    faiss.normalize_L2(query_vector)

    # search — returns distances and indices of top_k results
    # D = similarity scores, I = indices into _jobs_metadata
    D, I = _index.search(query_vector, top_k)

    results = []
    for score, idx in zip(D[0], I[0]):
        if idx == -1:  # FAISS returns -1 for empty slots
            continue
        job = _jobs_metadata[idx].copy()
        job["similarity_score"] = round(float(score) * 100, 2)
        results.append(job)

    return results