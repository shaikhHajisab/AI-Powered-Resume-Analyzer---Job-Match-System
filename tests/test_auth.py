# tests/test_auth.py
# run with: python tests/test_auth.py

import requests

BASE = "http://localhost:8000"

def test_register():
    res = requests.post(f"{BASE}/auth/register", json={
        "email": "dev@example.com",
        "password": "SecurePass123",
        "full_name": "Dev User"
    })
    print(f"Register: {res.status_code} → {res.json()}")
    return res.json()


def test_login():
    # login uses form data (not JSON) — OAuth2 standard
    res = requests.post(f"{BASE}/auth/login", data={
        "username": "dev@example.com",  # field is called username per OAuth2 spec
        "password": "SecurePass123"
    })
    print(f"Login: {res.status_code} → {res.json()}")
    return res.json().get("access_token")


def test_get_me(token: str):
    res = requests.get(
        f"{BASE}/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"Me: {res.status_code} → {res.json()}")


def test_upload_without_token():
    """should get 401"""
    res = requests.post(f"{BASE}/resume/upload", data={
        "job_description": "Python developer role"
    })
    print(f"Upload without token: {res.status_code} → {res.json()}")


def test_upload_with_token(token: str):
    with open("tests/sample_resume.pdf", "rb") as f:
        res = requests.post(
            f"{BASE}/resume/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("resume.pdf", f, "application/pdf")},
            data={
                "job_description": "Looking for Python developer with FastAPI and ML experience. Must know SQL, REST APIs, and Docker.",
                "job_title": "Python Developer"
            }
        )
    print(f"Upload with token: {res.status_code} → {res.json()}")


def test_wrong_password():
    """should get 401"""
    res = requests.post(f"{BASE}/auth/login", data={
        "username": "dev@example.com",
        "password": "WrongPassword"
    })
    print(f"Wrong password: {res.status_code} → {res.json()}")


if __name__ == "__main__":
    print("\n=== Auth Flow Tests ===\n")
    test_register()
    token = test_login()
    test_get_me(token)
    test_upload_without_token()
    test_wrong_password()
    test_upload_with_token(token)
    print("\n=== Done ===")