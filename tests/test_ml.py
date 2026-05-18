# tests/test_ml.py

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.ml_scorer import calculate_tfidf_score, extract_keywords

resume = """
John Doe — Python Developer
Skills: Python, FastAPI, Django, PostgreSQL, Docker, Machine Learning, scikit-learn
Experience: 3 years building REST APIs with FastAPI and Flask.
Deployed ML models using Docker on AWS. Familiar with pandas, numpy, TF-IDF.
"""

job_description = """
We are looking for a Python Backend Developer with strong FastAPI experience.
Must know PostgreSQL, Docker, and REST API design.
Machine learning experience is a plus. Knowledge of scikit-learn and numpy preferred.
"""

def test_keywords():
    keywords = extract_keywords(resume, top_n=10)
    print(f"Top resume keywords: {keywords}")

def test_scoring():
    result = calculate_tfidf_score(resume, job_description)
    print(f"\nTF-IDF Score: {result['tfidf_score']}/100")
    print(f"Matched keywords: {result['matched_keywords']}")
    print(f"Missing keywords: {result['missing_keywords']}")

if __name__ == "__main__":
    test_keywords()
    test_scoring()