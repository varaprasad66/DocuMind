
import pymupdf
import pytest

from app.ingestion.pdf_loader import extract_pdf_pages


def test_extract_pdf_pages(tmp_path):
    # Create a tiny PDF fixture with two pages.
    pdf_path = tmp_path / "sample.pdf"

    with pymupdf.open() as pdf:
        page1 = pdf.new_page()
        page1.insert_text((72, 72), "DocuMind page one")

        page2 = pdf.new_page()
        page2.insert_text((72, 72), "DocuMind page two")

        pdf.save(pdf_path)

    pages = extract_pdf_pages(pdf_path)

    assert len(pages) == 2
    assert pages[0]["page_number"] == 1
    assert "DocuMind page one" in pages[0]["text"]
    assert pages[1]["page_number"] == 2
    assert "DocuMind page two" in pages[1]["text"]


def test_missing_pdf_raises_error(tmp_path):
    missing_path = tmp_path / "missing.pdf"

    with pytest.raises(FileNotFoundError):
        extract_pdf_pages(missing_path)


def test_non_pdf_file_raises_error(tmp_path):
    text_path = tmp_path / "sample.txt"
    text_path.write_text("This is not a PDF.", encoding="utf-8")

    with pytest.raises(ValueError):
        extract_pdf_pages(text_path)
