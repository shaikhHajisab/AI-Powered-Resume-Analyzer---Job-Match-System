from pydantic import ValidationError
from app.schemas.user import UserCreate, UserResponse
from app.schemas.resume import ResumeAnalysisRequest, AnalysisStatus
from datetime import datetime


def test_valid_user_create():
    user = UserCreate(
        email="john@example.com",
        password="SecurePass123",
        full_name="John Doe"
    )

    print(f"✅ Valid user created: {user.email}, {user.full_name}")
    assert user.email == "john@example.com"


def test_invalid_email():
    try:
        user = UserCreate(
            email="not-an-email",
            password="SecurePass123",
            full_name="John Doe"
        )

        print("❌ Should have failed!")

    except ValidationError as e:
        print(f"✅ Caught invalid email: {e.error_count()} error(s)")

        for error in e.errors():
            print(f"   Field: {error['loc']}, Issue: {error['msg']}")


def test_password_too_short():
    try:
        user = UserCreate(
            email="john@example.com",
            password="short",
            full_name="John Doe"
        )

    except ValidationError as e:
        print(f"✅ Caught short password: {e.errors()[0]['msg']}")


def test_password_no_uppercase():
    try:
        user = UserCreate(
            email="john@example.com",
            password="alllowercase123",
            full_name="John Doe"
        )

    except ValidationError as e:
        print(f"✅ Caught no-uppercase: {e.errors()[0]['msg']}")


def test_multiple_errors_at_once():
    try:
        user = UserCreate(
            email="bad-email",
            password="no",
            full_name="J"
        )

    except ValidationError as e:
        print(f"✅ Caught {e.error_count()} errors simultaneously:")

        for error in e.errors():
            print(f"   {error['loc']}: {error['msg']}")


def test_type_coercion():
    from app.schemas.resume import ScoreBreakdown

    score = ScoreBreakdown(
        tfidf_score="85.5",
        semantic_score=90.0,
        final_score=87.5,
    )

    print(
        f"✅ Type coercion works: tfidf_score = {score.tfidf_score} "
        f"(type: {type(score.tfidf_score).__name__})"
    )


def test_enum_validation():
    try:
        from app.schemas.resume import AnalysisResponse

        status = AnalysisStatus("random_value")

    except ValueError as e:
        print(f"✅ Enum rejected invalid value: {e}")

    status = AnalysisStatus.COMPLETED
    print(f"✅ Valid enum: {status} (value: {status.value})")


def test_serialization():
    from app.schemas.resume import ScoreBreakdown

    score = ScoreBreakdown(
        tfidf_score=82.5,
        semantic_score=79.0,
        final_score=80.75,
        matched_keywords=["Python", "FastAPI", "Docker"],
        missing_keywords=["Kubernetes", "AWS"]
    )

    as_dict = score.model_dump()
    print(f"✅ As dict: {as_dict}")

    as_json = score.model_dump_json(indent=2)
    print(f"✅ As JSON:\n{as_json}")


if __name__ == "__main__":
    print("\n=== Running Schema Tests ===\n")

    test_valid_user_create()
    test_invalid_email()
    test_password_too_short()
    test_password_no_uppercase()
    test_multiple_errors_at_once()
    test_type_coercion()
    test_enum_validation()
    test_serialization()

    print("\n=== All tests passed ===\n")