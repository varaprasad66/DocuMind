
from pathlib import Path

import pymupdf


def extract_pdf_pages(file_path: str | Path) -> list[dict]:
    """
    Extract text from a PDF, preserving its original page numbers.

    Returns:
        A list of dictionaries, one per page:
        [
            {"page_number": 1, "text": "Text from page one..."},
            {"page_number": 2, "text": "Text from page two..."},
        ]
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    if not path.is_file():
        raise ValueError(f"Path is not a file: {path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a PDF file, got: {path.suffix}")

    pages = []

    with pymupdf.open(path) as pdf:
        for page_index, page in enumerate(pdf):
            text = page.get_text("text").strip()

            pages.append(
                {
                    "page_number": page_index + 1,
                    "text": text,
                }
            )

    return pages
