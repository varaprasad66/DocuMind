
import pymupdf
import pytest

from app.ingestion.ingest import ingest_pdf
from app.retrieval.search import search_chunks


def create_test_pdf(path, text):
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        page.insert_text((72, 72), text)
        pdf.save(path)


@pytest.fixture
def indexed_document(tmp_path):
    source = tmp_path / "handbook.pdf"
    create_test_pdf(
        source,
        "Employees receive annual leave. "
        "Their manager must approve leave requests. "
        "Travel expenses require receipts.",
    )

    db_path = tmp_path / "data" / "documind.db"
    documents_dir = tmp_path / "documents"
    ingest_pdf(source, db_path, documents_dir)

    return db_path


def test_retrieves_relevant_chunk(indexed_document):
    results = search_chunks(
        indexed_document,
        "Who approves annual leave requests?",
        top_k=3,
    )

    assert results
    assert any(
        "approve" in result["text"].lower()
        and "leave" in result["text"].lower()
        for result in results
    )


def test_returns_document_and_page_citations(indexed_document):
    results = search_chunks(
        indexed_document,
        "travel expenses receipts",
    )

    assert results
    assert results[0]["filename"] == "handbook.pdf"
    assert results[0]["page_number"] == 1
    assert isinstance(results[0]["chunk_id"], int)


def test_returns_empty_list_when_nothing_matches(indexed_document):
    results = search_chunks(
        indexed_document,
        "volcanic eruptions on Mars",
    )

    assert results == []


def test_handles_punctuation(indexed_document):
    results = search_chunks(
        indexed_document,
        'Who approves leave??? "manager"',
    )

    assert results


def test_rejects_invalid_top_k(indexed_document):
    with pytest.raises(ValueError):
        search_chunks(indexed_document, "leave", top_k=0)


def test_rejects_non_string_question(indexed_document):
    with pytest.raises(TypeError):
        search_chunks(indexed_document, 123)
