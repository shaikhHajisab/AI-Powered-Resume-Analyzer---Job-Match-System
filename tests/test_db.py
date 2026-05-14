# tests/test_db.py

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import SessionLocal
from app.models.user import User
from app.models.resume import Resume

def run():
    db = SessionLocal()

    # create user
    user = User(email="test@example.com", hashed_password="fakehash", full_name="Test User")
    db.add(user)
    db.commit()
    db.refresh(user)
    print(f"created user: id={user.id}, email={user.email}")

    # create resume linked to user
    resume = Resume(user_id=user.id, filename="cv.pdf", status="pending")
    db.add(resume)
    db.commit()
    db.refresh(resume)
    print(f"created resume: id={resume.id}, user_id={resume.user_id}")

    # read back
    found = db.query(User).filter(User.email == "test@example.com").first()
    print(f"found user: {found}, resumes: {len(found.resumes)}")

    # delete user → resume should cascade delete
    db.delete(found)
    db.commit()
    print("deleted user and cascaded to resumes")

    # verify
    gone = db.query(Resume).filter(Resume.id == resume.id).first()
    print(f"resume after cascade delete: {gone}")  # should be None

    db.close()

if __name__ == "__main__":
    run()