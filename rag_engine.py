import os
import tempfile
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

load_dotenv()

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Default to the OS temp dir so it works on Streamlit Cloud (where the
# git mount is read-only) and on Windows / macOS / Linux locally without
# config. Override with VIVORA_VECTORSTORE_DIR if you want persistence.
_DEFAULT_VECTORSTORE_DIR = os.path.join(tempfile.gettempdir(), "vivora_vectorstore")


def _persist_dir() -> str:
    return os.getenv("VIVORA_VECTORSTORE_DIR", _DEFAULT_VECTORSTORE_DIR)


_embeddings_singleton = None

def _get_embeddings():
    """Load the embedding model once and reuse it.

    Imported lazily so importing this module doesn't drag in
    transformers / torch (~500 MB of warnings on first import)
    until embeddings are actually needed.
    """
    global _embeddings_singleton
    if _embeddings_singleton is None:
        from langchain_huggingface import HuggingFaceEmbeddings
        print(f"Loading embedding model: {EMBEDDING_MODEL} (first run downloads ~80MB)...")
        _embeddings_singleton = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embeddings_singleton


def _faiss():
    """Lazy FAISS import — keeps initial app boot fast."""
    from langchain_community.vectorstores import FAISS
    return FAISS


def chunk_files(files: list) -> list:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,
        chunk_overlap=200,
        length_function=len,
    )

    all_documents = []
    for file in files:
        chunks = splitter.split_text(file["content"])
        for i, chunk in enumerate(chunks):
            doc = Document(
                page_content=chunk,
                metadata={
                    "file_name": file["file_name"],
                    "relative_path": file["relative_path"],
                    "chunk_index": i,
                }
            )
            all_documents.append(doc)
    return all_documents


def build_vector_store(documents: list, persist_dir: str | None = None):
    import shutil, gc, time

    persist_dir = persist_dir or _persist_dir()
    embeddings = _get_embeddings()

    if os.path.exists(persist_dir):
        gc.collect()
        try:
            shutil.rmtree(persist_dir)
        except PermissionError:
            time.sleep(0.5)
            shutil.rmtree(persist_dir, ignore_errors=True)
    os.makedirs(persist_dir, exist_ok=True)

    print(f"Embedding {len(documents)} chunks locally...")
    vector_store = _faiss().from_documents(documents=documents, embedding=embeddings)
    vector_store.save_local(persist_dir)
    return vector_store


def get_retriever(persist_dir: str | None = None):
    persist_dir = persist_dir or _persist_dir()
    vector_store = _faiss().load_local(
        persist_dir,
        _get_embeddings(),
        allow_dangerous_deserialization=True,
    )
    return vector_store.as_retriever(search_kwargs={"k": 5})


_LAST_RAG_ERROR: str | None = None

def get_last_rag_error() -> str | None:
    return _LAST_RAG_ERROR


def build_rag_pipeline(files: list) -> bool:
    """
    Takes repo files and builds the complete RAG knowledge base.
    Returns True on success, False on failure. Use get_last_rag_error()
    to read the latest error message (also printed to terminal).
    """
    global _LAST_RAG_ERROR
    _LAST_RAG_ERROR = None
    try:
        print(f"Chunking {len(files)} files...")
        documents = chunk_files(files)
        print(f"Created {len(documents)} chunks")

        if not documents:
            _LAST_RAG_ERROR = "Chunking produced 0 documents — no readable content in repo."
            print(f"RAG PIPELINE ERROR: {_LAST_RAG_ERROR}")
            return False

        build_vector_store(documents)
        print("Vector store ready.")
        return True

    except Exception as err:
        import traceback
        _LAST_RAG_ERROR = f"{type(err).__name__}: {err}"
        print("RAG PIPELINE ERROR:")
        print(traceback.format_exc())
        return False


def retrieve_context(query: str, persist_dir: str | None = None) -> str:
    retriever = get_retriever(persist_dir or _persist_dir())
    relevant_docs = retriever.invoke(query)

    combined_context = ""
    for doc in relevant_docs:
        source = doc.metadata.get("relative_path", "unknown file")
        combined_context += f"\n\n--- From {source} ---\n{doc.page_content}"

    return combined_context
