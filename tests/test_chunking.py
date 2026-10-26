
import pytest

from app.ingestion.chunker import chunk_pages


def test_short_page_produces_one_chunk():
    pages = [
        {
            "page_number": 1,
            "text": "Employees receive annual leave.",
        }
    ]

    chunks = chunk_pages(pages)

    assert len(chunks) == 1
    assert chunks[0]["page_number"] == 1
    assert chunks[0]["chunk_index"] == 0
    assert chunks[0]["text"] == "Employees receive annual leave."
    assert chunks[0]["char_start"] == 0
    assert chunks[0]["char_end"] == len(
        "Employees receive annual leave."
    )


def test_long_page_uses_expected_chunk_size_and_overlap():
    text = "A" * 2200
    pages = [{"page_number": 3, "text": text}]

    chunks = chunk_pages(pages, chunk_size=1000, overlap=150)

    assert len(chunks) == 3

    assert chunks[0]["char_start"] == 0
    assert chunks[0]["char_end"] == 1000
    assert len(chunks[0]["text"]) == 1000

    assert chunks[1]["char_start"] == 850
    assert chunks[1]["char_end"] == 1850
    assert len(chunks[1]["text"]) == 1000

    assert chunks[2]["char_start"] == 1700
    assert chunks[2]["char_end"] == 2200
    assert len(chunks[2]["text"]) == 500

    # Adjacent chunks share exactly 150 characters.
    assert chunks[0]["text"][-150:] == chunks[1]["text"][:150]
    assert chunks[1]["text"][-150:] == chunks[2]["text"][:150]


def test_chunks_preserve_page_numbers():
    pages = [
        {"page_number": 1, "text": "First page content."},
        {"page_number": 2, "text": "Second page content."},
    ]

    chunks = chunk_pages(pages)

    assert [chunk["page_number"] for chunk in chunks] == [1, 2]


def test_whitespace_only_pages_are_skipped():
    pages = [
        {"page_number": 1, "text": "   \n  "},
        {"page_number": 2, "text": "Actual content."},
    ]

    chunks = chunk_pages(pages)

    assert len(chunks) == 1
    assert chunks[0]["page_number"] == 2
    assert chunks[0]["text"] == "Actual content."


def test_empty_input_returns_no_chunks():
    assert chunk_pages([]) == []


@pytest.mark.parametrize(
    ("chunk_size", "overlap"),
    [
        (0, 0),
        (-1, 0),
        (100, -1),
        (100, 100),
        (100, 150),
    ],
)
def test_invalid_chunk_settings_raise_error(chunk_size, overlap):
    with pytest.raises(ValueError):
        chunk_pages(
            [{"page_number": 1, "text": "Example text."}],
            chunk_size=chunk_size,
            overlap=overlap,
        )


def test_missing_page_metadata_raises_error():
    with pytest.raises(ValueError):
        chunk_pages([{"text": "Content without a page number"}])


def test_non_string_page_text_raises_error():
    with pytest.raises(TypeError):
        chunk_pages([{"page_number": 1, "text": 123}])
