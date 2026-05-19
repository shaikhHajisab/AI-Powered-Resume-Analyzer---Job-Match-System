# tests/test_rag.py

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.vector_store import build_index, get_similar_jobs

resume_text = """
Python developer with 3 years experience.
Skills: FastAPI, PostgreSQL, Docker, REST APIs, SQLAlchemy, JWT.
Built microservices, deployed on AWS.
"""

if __name__ == "__main__":
    print("Building index...")
    build_index()

    print("\nFinding similar jobs...")
    jobs = get_similar_jobs(resume_text, top_k=3)

    for job in jobs:
        print(f"\n{job['title']} at {job['company']}")
        print(f"Location: {job['location']}")
        print(f"Similarity: {job['similarity_score']}%")