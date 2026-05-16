# app/services/pdf_parser.py

import fitz  # fitz is the Python name for PyMuPDF
import io
from fastapi import HTTPException


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Takes raw PDF bytes, returns extracted text string.
    Raises HTTPException if file is not a valid PDF or text extraction fails.
    """
    try:
        # fitz.open() can open from bytes using stream parameter
        # filetype="pdf" tells PyMuPDF what to expect
        pdf_document = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid PDF file")

    if pdf_document.page_count == 0:
        raise HTTPException(status_code=400, detail="PDF has no pages")

    extracted_text = []

    for page_num in range(pdf_document.page_count):
        page = pdf_document[page_num]
        # get_text() extracts all text from this page
        # "text" mode preserves reading order (top to bottom, left to right)
        text = page.get_text("text")
        if text.strip():  # skip blank pages
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
    # check extension
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    # 5MB limit — Render free tier has limited memory
    max_size = 5 * 1024 * 1024  # 5MB in bytes
    if file_size_bytes > max_size:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 5MB")