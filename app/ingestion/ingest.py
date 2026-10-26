
import hashlib
import shutil
from pathlib import Path

from app.ingestion.chunker import chunk_pages
from app.ingestion.pdf_loader import extract_pdf_pages
from app.storage.database import (
    find_document_by_hash,
    init_db,
    store_document_and_chunks,
)


def calculate_sha256(file_path: str | Path) -> str:
    """Calculate a file's SHA-256 fingerprint without loading it all at once."""
    digest = hashlib.sha256()

    with Path(file_path).open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def ingest_pdf(
    source_path: str | Path,
    db_path: str | Path = "data/documind.db",
    documents_dir: str | Path = "data/documents",
) -> dict:
    """
    Save a PDF, extract its text, chunk it, and persist its records.

    Returns a summary containing the document ID and chunk count.
    """
    source = Path(source_path)

    if not source.exists():
        raise FileNotFoundError(f"PDF not found: {source}")

    if not source.is_file():
        raise ValueError(f"Source path is not a file: {source}")

    if source.suffix.lower() != ".pdf":
        raise ValueError("Only PDF files are supported by this ingestion function")

    db_path = Path(db_path)
    documents_dir = Path(documents_dir)

    init_db(db_path)

    sha256 = calculate_sha256(source)

    # Avoid indexing identical content more than once.
    existing = find_document_by_hash(db_path, sha256)
    if existing:
        return {
            "document_id": existing["id"],
            "filename": existing["filename"],
            "chunk_count": len(
                get_chunks_for_document(db_path, existing["id"])
            ),
            "already_ingested": True,
        }

    documents_dir.mkdir(parents=True, exist_ok=True)

    # The hash prefix avoids collisions between different files with
    # the same original filename.
    stored_path = documents_dir / f"{sha256[:12]}_{source.name}"
    copied_new_file = not stored_path.exists()

    if copied_new_file:
        shutil.copy2(source, stored_path)

    try:
        pages = extract_pdf_pages(stored_path)
        chunks = chunk_pages(pages)

        if not chunks:
            raise ValueError(
                "No extractable text found in the PDF. "
                "It may be scanned and require OCR."
            )

        document_id = store_document_and_chunks(
            db_path=db_path,
            filename=source.name,
            file_path=stored_path,
            sha256=sha256,
            chunks=chunks,
        )

        saved_chunks = get_chunks_for_document(db_path, document_id)

        return {
            "document_id": document_id,
            "filename": source.name,
            "chunk_count": len(saved_chunks),
            "already_ingested": False,
        }

    except Exception:
        # Avoid leaving a newly copied file behind after a failed ingest.
        if copied_new_file and stored_path.exists():
            stored_path.unlink()
        raise


# Import used by the duplicate-ingestion branch above.
from app.storage.database import get_chunks_for_document
