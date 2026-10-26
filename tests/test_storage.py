
import pymupdf
import pytest

from app.ingestion.ingest import ingest_pdf
from app.storage.database import (
    get_chunks_for_document,
    list_documents,
)


def create_test_pdf(path, text):
    """Create a one-page PDF for an ingestion test."""
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        if text:
            page.insert_text((72, 72), text)
        pdf.save(path)


def test_ingest_persists_pdf_and_chunks(tmp_path):
    source = tmp_path / "handbook.pdf"
    db_path = tmp_path / "data" / "documind.db"
    documents_dir = tmp_path / "documents"

    create_test_pdf(
        source,
        "Employees receive annual leave. "
        "Their manager must approve leave requests.",
    )

    result = ingest_pdf(source, db_path, documents_dir)

    assert result["document_id"] == 1
    assert result["chunk_count"] >= 1
    assert result["already_ingested"] is False

    # The original PDF has been retained in the document directory.
    saved_pdf = list(documents_dir.glob("*.pdf"))
    assert len(saved_pdf) == 1
    assert saved_pdf[0].exists()

    # The document metadata persists in SQLite.
    documents = list_documents(db_path)
    assert len(documents) == 1
    assert documents[0]["filename"] == "handbook.pdf"

    # Its text passages are stored and linked to the document.
    chunks = get_chunks_for_document(db_path, result["document_id"])
    assert len(chunks) == result["chunk_count"]
    assert all(chunk["page_number"] == 1 for chunk in chunks)
    assert any("annual leave" in chunk["text"] for chunk in chunks)


def test_identical_content_is_not_ingested_twice(tmp_path):
    source1 = tmp_path / "handbook.pdf"
    source2 = tmp_path / "renamed_handbook.pdf"
    db_path = tmp_path / "data" / "documind.db"
    documents_dir = tmp_path / "documents"

    create_test_pdf(source1, "Employees receive annual leave.")
    source2.write_bytes(source1.read_bytes())

    first = ingest_pdf(source1, db_path, documents_dir)
    second = ingest_pdf(source2, db_path, documents_dir)

    assert first["document_id"] == second["document_id"]
    assert second["already_ingested"] is True
    assert len(list_documents(db_path)) == 1


def test_missing_pdf_raises_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        ingest_pdf(
            tmp_path / "missing.pdf",
            tmp_path / "documind.db",
            tmp_path / "documents",
        )


def test_pdf_without_extractable_text_is_rejected(tmp_path):
    source = tmp_path / "blank.pdf"
    documents_dir = tmp_path / "documents"

    create_test_pdf(source, "")

    with pytest.raises(ValueError, match="No extractable text"):
        ingest_pdf(
            source,
            tmp_path / "documind.db",
            documents_dir,
        )

    # A failed ingestion should not leave a newly copied PDF behind.
    assert list(documents_dir.glob("*.pdf")) == []
    assert list_documents(tmp_path / "documind.db") == []
