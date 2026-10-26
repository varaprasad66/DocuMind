
from contextlib import closing
from pathlib import Path
import sqlite3


def _connect(db_path: str | Path) -> sqlite3.Connection:
    """Open a SQLite connection with foreign-key checks enabled."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def init_db(db_path: str | Path) -> None:
    """Create the DocuMind database tables if they do not exist."""
    with closing(_connect(db_path)) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                sha256 TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY,
                document_id INTEGER NOT NULL,
                page_number INTEGER NOT NULL,
                chunk_index INTEGER NOT NULL,
                char_start INTEGER NOT NULL,
                char_end INTEGER NOT NULL,
                text TEXT NOT NULL,

                FOREIGN KEY (document_id)
                    REFERENCES documents(id)
                    ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_chunks_document_id
                ON chunks(document_id);

            CREATE INDEX IF NOT EXISTS idx_chunks_page
                ON chunks(document_id, page_number);
            """
        )


def find_document_by_hash(
    db_path: str | Path,
    sha256: str,
) -> dict | None:
    """Return a document with this content hash, or None."""
    with closing(_connect(db_path)) as connection:
        row = connection.execute(
            """
            SELECT id, filename, file_path, sha256, created_at
            FROM documents
            WHERE sha256 = ?
            """,
            (sha256,),
        ).fetchone()

    return dict(row) if row else None


def store_document_and_chunks(
    db_path: str | Path,
    filename: str,
    file_path: str | Path,
    sha256: str,
    chunks: list[dict],
) -> int:
    """
    Store one document and all its chunks atomically.

    If the same file content is already indexed, return its existing ID.
    """
    init_db(db_path)

    with closing(_connect(db_path)) as connection:
        try:
            # Lock for writing before checking for duplicate content.
            connection.execute("BEGIN IMMEDIATE")

            existing = connection.execute(
                "SELECT id FROM documents WHERE sha256 = ?",
                (sha256,),
            ).fetchone()

            if existing:
                connection.commit()
                return existing["id"]

            cursor = connection.execute(
                """
                INSERT INTO documents (filename, file_path, sha256)
                VALUES (?, ?, ?)
                """,
                (filename, str(file_path), sha256),
            )
            document_id = cursor.lastrowid

            connection.executemany(
                """
                INSERT INTO chunks (
                    document_id,
                    page_number,
                    chunk_index,
                    char_start,
                    char_end,
                    text
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        document_id,
                        chunk["page_number"],
                        chunk["chunk_index"],
                        chunk["char_start"],
                        chunk["char_end"],
                        chunk["text"],
                    )
                    for chunk in chunks
                ],
            )

            connection.commit()
            return document_id

        except Exception:
            connection.rollback()
            raise


def list_documents(db_path: str | Path) -> list[dict]:
    """Return indexed documents, newest first."""
    with closing(_connect(db_path)) as connection:
        rows = connection.execute(
            """
            SELECT id, filename, file_path, sha256, created_at
            FROM documents
            ORDER BY id DESC
            """
        ).fetchall()

    return [dict(row) for row in rows]


def get_chunks_for_document(
    db_path: str | Path,
    document_id: int,
) -> list[dict]:
    """Return all chunks for one document in source order."""
    with closing(_connect(db_path)) as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                document_id,
                page_number,
                chunk_index,
                char_start,
                char_end,
                text
            FROM chunks
            WHERE document_id = ?
            ORDER BY page_number, chunk_index
            """,
            (document_id,),
        ).fetchall()

    return [dict(row) for row in rows]
