import requests
import time
import logging
from fastapi import HTTPException
from app.core.config import settings

logger = logging.getLogger(__name__)

HF_API_URL = "https://api-inference.huggingface.co/models/google/flan-t5-large"


def call_hf_llm(prompt: str, max_new_tokens: int = 300, retries: int = 3, delay: int = 5) -> str:
    """
    Call HuggingFace text generation API.
    Returns generated text string.
    """
    headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}"}
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": max_new_tokens,
            "temperature": 0.7,
            "do_sample": True,
            "repetition_penalty": 1.3
        },
        "options": {
            "wait_for_model": True,
            "use_cache": False
        }
    }

    for attempt in range(retries):
        try:
            response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=60)

            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    return result[0].get("generated_text", "").strip()
                raise Exception(f"Unexpected LLM response format: {result}")
                
            logger.warning(f"HF API attempt {attempt + 1} failed: {response.status_code} - {response.text}")
        except requests.RequestException as e:
            logger.warning(f"HF API attempt {attempt + 1} exception: {str(e)}")

        if attempt < retries - 1:
            time.sleep(delay)

    raise HTTPException(status_code=503, detail="HuggingFace LLM API unavailable after retries")


def build_suggestion_prompt(
    resume_text: str,
    job_description: str,
    matched_keywords: list,
    missing_keywords: list,
    final_score: float
) -> str:
    resume_snippet = resume_text[:800]
    jd_snippet = job_description[:500]
    missing_str = ", ".join(missing_keywords[:10]) if missing_keywords else "none identified"
    matched_str = ", ".join(matched_keywords[:10]) if matched_keywords else "none identified"

    prompt = f"""You are a professional resume coach. Analyze this resume against the job description and provide exactly 5 specific improvement suggestions.

Job Description Summary:
{jd_snippet}

Resume Summary:
{resume_snippet}

Match Score: {final_score}/100
Keywords found in resume: {matched_str}
Keywords missing from resume: {missing_str}

Provide exactly 5 specific, actionable suggestions to improve this resume for this job. Format each as:
1. [suggestion]
2. [suggestion]
3. [suggestion]
4. [suggestion]
5. [suggestion]

Suggestions:"""

    return prompt


def parse_suggestions(raw_text: str) -> list[dict]:
    suggestions = []
    lines = raw_text.strip().split('\n')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line and line[0].isdigit():
            clean = line.lstrip('0123456789.-) ').strip()
            if len(clean) > 10:
                category = categorize_suggestion(clean)
                suggestions.append({
                    "category": category,
                    "suggestion": clean,
                    "priority": assign_priority(suggestions)
                })

    if not suggestions:
        suggestions.append({
            "category": "General",
            "suggestion": raw_text[:500],
            "priority": "medium"
        })

    return suggestions[:5]


def categorize_suggestion(text: str) -> str:
    text_lower = text.lower()
    if any(w in text_lower for w in ["skill", "technology", "tool", "framework", "language"]):
        return "Skills"
    elif any(w in text_lower for w in ["experience", "project", "achievement", "accomplish"]):
        return "Experience"
    elif any(w in text_lower for w in ["keyword", "ats", "term", "phrase"]):
        return "Keywords"
    elif any(w in text_lower for w in ["format", "structure", "layout", "section"]):
        return "Format"
    else:
        return "Content"


def assign_priority(existing: list) -> str:
    if len(existing) < 2:
        return "high"
    return "medium"


def generate_resume_suggestions(
    resume_text: str,
    job_description: str,
    matched_keywords: list,
    missing_keywords: list,
    final_score: float
) -> list[dict]:
    prompt = build_suggestion_prompt(
        resume_text,
        job_description,
        matched_keywords,
        missing_keywords,
        final_score
    )

    raw_output = call_hf_llm(prompt)
    suggestions = parse_suggestions(raw_output)

    return suggestions