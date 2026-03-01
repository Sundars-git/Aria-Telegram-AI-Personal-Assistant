"""
doc_reader.py — Extract text from PDF documents.

Uses PyPDF2 to read PDF files sent by users and extract their text
content for analysis by Gemini.
"""

import io
import logging

from PyPDF2 import PdfReader

logger = logging.getLogger(__name__)

# Maximum characters to extract from a document
_MAX_TEXT_LENGTH = 8000


def extract_pdf_text(file_bytes: bytes) -> str:
    """
    Extract text content from a PDF file.

    Args:
        file_bytes: Raw bytes of the PDF file.

    Returns:
        Extracted text content, or an error message if extraction fails.
    """
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        pages_text = []

        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                pages_text.append(f"--- Page {i + 1} ---\n{text}")

        if not pages_text:
            return "Could not extract any text from this PDF. It may be image-based."

        full_text = "\n\n".join(pages_text)

        if len(full_text) > _MAX_TEXT_LENGTH:
            full_text = full_text[:_MAX_TEXT_LENGTH] + "\n\n[... truncated ...]"

        return full_text

    except Exception as exc:
        logger.exception("Failed to read PDF: %s", exc)
        return f"Failed to read this PDF: {exc}"
