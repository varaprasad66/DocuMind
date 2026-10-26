
from pathlib import Path
import tempfile

import streamlit as st

from app.ingestion.ingest import ingest_pdf
from app.generation.answer import answer_question
from app.storage.database import list_documents


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "documind.db"
DOCUMENTS_DIR = BASE_DIR / "data" / "documents"


st.set_page_config(
    page_title="DocuMind",
    page_icon="📚",
    layout="wide",
)

st.title("📚 DocuMind")
st.caption("Ask questions about your documents, with source references.")

# ---------- Document upload ----------

st.header("1. Upload documents")

uploaded_files = st.file_uploader(
    "Choose PDF files from your computer",
    type=["pdf"],
    accept_multiple_files=True,
)

if st.button("Upload and process PDFs", type="primary"):
    if not uploaded_files:
        st.warning("Select at least one PDF first.")
    else:
        for uploaded_file in uploaded_files:
            safe_name = Path(uploaded_file.name).name

            try:
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_path = Path(temp_dir) / safe_name
                    temp_path.write_bytes(uploaded_file.getvalue())

                    result = ingest_pdf(
                        source_path=temp_path,
                        db_path=DB_PATH,
                        documents_dir=DOCUMENTS_DIR,
                    )

                status = (
                    "Already ingested"
                    if result["already_ingested"]
                    else "Successfully ingested"
                )
                st.success(
                    f"{status}: {result['filename']} "
                    f"({result['chunk_count']} chunks)"
                )

            except Exception as exc:
                st.error(f"Could not process {safe_name}: {exc}")

# ---------- Stored documents ----------

st.header("2. Your document library")

try:
    documents = list_documents(DB_PATH) if DB_PATH.exists() else []
except Exception as exc:
    documents = []
    st.error(f"Could not load the document library: {exc}")

if documents:
    for document in documents:
        st.write(
            f"**{document['filename']}** "
            f"— document ID {document['id']}"
        )
else:
    st.info("No documents stored yet. Upload a PDF above.")

# ---------- Chat ----------

st.header("3. Ask your documents")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        if message["role"] == "assistant" and message.get("sources"):
            with st.expander("View sources and retrieved evidence"):
                for source in message["sources"]:
                    st.markdown(
                        f"**{source['label']}** — "
                        f"{source['filename']}, "
                        f"page {source['page_number']}"
                    )
                    if source.get("excerpt"):
                        st.text(source["excerpt"])

question = st.chat_input("Ask a question about your PDFs...")

if question:
    st.session_state.messages.append(
        {"role": "user", "content": question}
    )

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Searching documents and generating an answer..."):
            try:
                result = answer_question(
                    db_path=str(DB_PATH),
                    question=question,
                )
                answer = result["answer"]
                sources = result["sources"]

                st.markdown(answer)

                if sources:
                    with st.expander("View sources and retrieved evidence"):
                        for source in sources:
                            st.markdown(
                                f"**{source['label']}** — "
                                f"{source['filename']}, "
                                f"page {source['page_number']}"
                            )
                            if source.get("excerpt"):
                                st.text(source["excerpt"])
                else:
                    st.caption("No matching document passages were found.")

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "sources": sources,
                    }
                )

            except Exception as exc:
                error_message = f"Unable to answer: {exc}"
                st.error(error_message)
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": error_message,
                        "sources": [],
                    }
                )
