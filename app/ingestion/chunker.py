
from typing import Any


def chunk_pages(
    pages: list[dict[str, Any]],
    chunk_size: int = 1000,
    overlap: int = 150,
) -> list[dict[str, Any]]:
    """
    Split extracted PDF pages into overlapping text chunks.

    Each chunk preserves its source page number and character offsets.

    Args:
        pages: Page records returned by extract_pdf_pages().
        chunk_size: Maximum number of characters in a chunk.
        overlap: Number of shared characters between adjacent chunks.

    Returns:
        A list of chunk dictionaries containing:
        - page_number
        - chunk_index (zero-based within each page)
        - char_start
        - char_end (exclusive)
        - text
    """
    if not isinstance(chunk_size, int) or isinstance(chunk_size, bool):
        raise TypeError("chunk_size must be an integer")

    if not isinstance(overlap, int) or isinstance(overlap, bool):
        raise TypeError("overlap must be an integer")

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError(
            "overlap must be non-negative and smaller than chunk_size"
        )

    chunks = []
    step = chunk_size - overlap

    for page in pages:
        if "page_number" not in page or "text" not in page:
            raise ValueError(
                "Each page must contain 'page_number' and 'text'"
            )

        page_number = page["page_number"]
        text = page["text"]

        if not isinstance(text, str):
            raise TypeError("Page text must be a string")

        # Skip pages with no meaningful text.
        if not text.strip():
            continue

        chunk_index = 0
        start = 0

        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk_text = text[start:end]

            # Preserve the exact substring and its character offsets.
            if chunk_text.strip():
                chunks.append(
                    {
                        "page_number": page_number,
                        "chunk_index": chunk_index,
                        "char_start": start,
                        "char_end": end,
                        "text": chunk_text,
                    }
                )
                chunk_index += 1

            start += step

    return chunks
