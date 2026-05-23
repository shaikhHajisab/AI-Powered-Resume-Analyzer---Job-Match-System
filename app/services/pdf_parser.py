import fitz
import io
from fastapi import HTTPException

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Takes raw PDF bytes, returns extracted text string.
    Raises HTTPException if file is not a valid PDF or text extraction fails.
    """
    try:
        pdf_document = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid PDF file")

    if pdf_document.page_count == 0:
        raise HTTPException(status_code=400, detail="PDF has no pages")

    extracted_text = []

    for page_num in range(pdf_document.page_count):
        page = pdf_document[page_num]
        text = page.get_text("text")
        if text.strip():
            extracted_text.append(text)

    pdf_document.close()

    full_text = "\n".join(extracted_text).strip()

    if not full_text:
        raise HTTPException(
            status_code=400,
            detail="Could not extract text. PDF may be a scanned image."
        )

    return full_text


def validate_pdf_file(filename: str, file_size_bytes: int) -> None:
    """
    Validates filename and size before we even open the file.
    Raises HTTPException if invalid.
    """
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    max_size = 5 * 1024 * 1024
    if file_size_bytes > max_size:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 5MB")