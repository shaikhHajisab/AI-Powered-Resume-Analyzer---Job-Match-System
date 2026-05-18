# tests/test_full_pipeline.py

import requests

BASE = "http://localhost:8000"

# ── helpers ──────────────────────────────────────────────

def register_and_login():
    """create account and return token"""
    requests.post(f"{BASE}/auth/register", json={
        "email": "mltest@example.com",
        "password": "SecurePass123",
        "full_name": "ML Tester"
    })
    res = requests.post(f"{BASE}/auth/login", data={
        "username": "mltest@example.com",
        "password": "SecurePass123"
    })
    return res.json()["access_token"]


def upload_resume(token: str, pdf_path: str) -> int:
    """upload PDF, return resume_id"""
    with open(pdf_path, "rb") as f:
        res = requests.post(
            f"{BASE}/resume/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("resume.pdf", f, "application/pdf")},
            data={
                "job_description": """
                    We are looking for a senior Python developer with strong experience
                    in FastAPI, PostgreSQL, Docker, and machine learning. The candidate
                    should know REST API design, SQLAlchemy, and have deployed ML models.
                    Experience with scikit-learn, numpy, and pandas is required.
                    Knowledge of JWT authentication and cloud deployment is a plus.
                """,
                "job_title": "Senior Python Developer"
            }
        )
    print(f"Upload: {res.status_code}")
    data = res.json()
    print(f"Resume ID: {data['resume_id']}")
    print(f"Text preview: {data['preview'][:100]}...")
    return data["resume_id"]


def run_tfidf_only(token: str, resume_id: int):
    """test TF-IDF endpoint alone"""
    res = requests.post(
        f"{BASE}/resume/{resume_id}/analyze-tfidf",
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"\nTF-IDF only: {res.status_code}")
    data = res.json()
    print(f"Score: {data['tfidf_score']}/100")
    print(f"Matched: {data['matched_keywords']}")
    print(f"Missing: {data['missing_keywords']}")


def run_full_analysis(token: str, resume_id: int):
    """test full pipeline with semantic"""
    print("\nRunning full analysis (this calls HuggingFace API)...")
    res = requests.post(
        f"{BASE}/resume/{resume_id}/analyze",
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"Full analysis: {res.status_code}")
    data = res.json()

    if res.status_code == 200:
        scores = data["scores"]
        print(f"\n{'='*40}")
        print(f"TF-IDF Score:   {scores['tfidf_score']}/100")
        print(f"Semantic Score: {scores['semantic_score']}/100")
        print(f"Final Score:    {scores['final_score']}/100")
        print(f"Interpretation: {data['interpretation']}")
        print(f"{'='*40}")
        print(f"Matched keywords: {data['keywords']['matched']}")
        print(f"Missing keywords: {data['keywords']['missing']}")
    else:
        print(f"Error: {data}")


def test_unauthorized():
    """no token should get 401"""
    res = requests.post(f"{BASE}/resume/1/analyze")
    print(f"\nNo token → {res.status_code} (expected 401)")


# ── run ──────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Full ML Pipeline Test ===\n")

    token = register_and_login()
    print(f"Token obtained: {token[:30]}...")

    # change path to your actual PDF
    resume_id = upload_resume(token, "tests/sample_resume.pdf")

    run_tfidf_only(token, resume_id)
    run_full_analysis(token, resume_id)
    test_unauthorized()

    print("\n=== Pipeline test complete ===")