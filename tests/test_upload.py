# tests/test_upload.py
# Run with: python tests/test_upload.py

import requests

# your running FastAPI server
BASE_URL = "http://localhost:8000"

def test_upload():
    # open a real PDF file — change path to any PDF on your machine
    pdf_path = "tests/sample_resume.pdf"  # put any PDF here

    with open(pdf_path, "rb") as f:
        response = requests.post(
            f"{BASE_URL}/resume/upload",
            files={"file": ("resume.pdf", f, "application/pdf")},
            data={
                "job_description": "We are looking for a Python developer with FastAPI experience and knowledge of machine learning. The candidate should have experience with REST APIs, SQL databases, and cloud deployment.",
                "job_title": "Python Backend Developer"
            }
        )

    print(f"Status: {response.status_code}")
    print(f"Response text: {response.text}")


def test_get_resume(resume_id: int):
    response = requests.get(f"{BASE_URL}/resume/{resume_id}")
    print(f"Status: {response.status_code}")
    print(f"Response text: {response.text}")


if __name__ == "__main__":
    test_upload()