
import re
import sqlite3
from contextlib import closing
from pathlib import Path

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can",
    "could", "did", "do", "does", "for", "from", "give",
    "how", "i", "in", "is", "it", "me", "of", "on", "or",
    "please", "show", "tell", "that", "the", "their", "this",
    "to", "was", "what", "when", "where", "which", "who",
    "why", "with", "would", "you", "your",
}

def _connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    if not path.exists():
        raise FileNotFoundError(f"Database not found: {path}")

    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def ensure_search_index(db_path: str | Path) -> None:
    """Create the FTS5 index, index existing chunks, and maintain it."""
    with closing(_connect(db_path)) as connection:
        connection.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts
            USING fts5(chunk_id UNINDEXED, text)
            """
        )

        connection.executescript(
            """
            CREATE TRIGGER IF NOT EXISTS chunks_ai
            AFTER INSERT ON chunks
            BEGIN
                INSERT INTO chunks_fts(rowid, chunk_id, text)
                VALUES (new.id, new.id, new.text);
            END;

            CREATE TRIGGER IF NOT EXISTS chunks_ad
            AFTER DELETE ON chunks
            BEGIN
                DELETE FROM chunks_fts WHERE rowid = old.id;
            END;

            CREATE TRIGGER IF NOT EXISTS chunks_au
            AFTER UPDATE OF text ON chunks
            BEGIN
                DELETE FROM chunks_fts WHERE rowid = old.id;
                INSERT INTO chunks_fts(rowid, chunk_id, text)
                VALUES (new.id, new.id, new.text);
            END;
            """
        )

        # Index chunks already stored before the search index existed.
        connection.execute(
            """
            INSERT INTO chunks_fts(rowid, chunk_id, text)
            SELECT c.id, c.id, c.text
            FROM chunks AS c
            WHERE NOT EXISTS (
                SELECT 1
                FROM chunks_fts AS f
                WHERE f.rowid = c.id
            )
            """
        )
        connection.commit()


def _build_fts_query(question: str) -> str:
    """Build a safe FTS5 query while ignoring common question words."""
    terms = re.findall(r"\w+", question, flags=re.UNICODE)
    terms = [
        term for term in terms
        if len(term) > 1 and term.casefold() not in STOPWORDS
    ]
    return " OR ".join(f'"{term.replace(chr(34), chr(34) * 2)}"' for term in terms)


def search_chunks(
    db_path: str | Path,
    question: str,
    top_k: int = 5,
) -> list[dict]:
    """Return the top matching text chunks, ranked by BM25."""
    if not isinstance(question, str):
        raise TypeError("question must be a string")

    if not isinstance(top_k, int) or isinstance(top_k, bool):
        raise TypeError("top_k must be an integer")

    if top_k <= 0:
        raise ValueError("top_k must be greater than zero")

    fts_query = _build_fts_query(question)
    if not fts_query:
        return []

    ensure_search_index(db_path)

    with closing(_connect(db_path)) as connection:
        rows = connection.execute(
            """
            SELECT
                c.id AS chunk_id,
                c.document_id,
                d.filename,
                c.page_number,
                c.chunk_index,
                c.text,
                bm25(chunks_fts) AS score
            FROM chunks_fts
            JOIN chunks AS c ON c.id = chunks_fts.chunk_id
            JOIN documents AS d ON d.id = c.document_id
            WHERE chunks_fts MATCH ?
            ORDER BY score ASC
            LIMIT ?
            """,
            (fts_query, top_k),
        ).fetchall()

    return [dict(row) for row in rows]
