import os
import tempfile
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

load_dotenv()

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"

# Default to the OS temp dir so it works on Streamlit Cloud (where the
# git mount is read-only) and on Windows / macOS / Linux locally without
# config. Override with VIVORA_VECTORSTORE_DIR if you want persistence.
_DEFAULT_VECTORSTORE_DIR = os.path.join(tempfile.gettempdir(), "vivora_vectorstore")


def _persist_dir() -> str:
    return os.getenv("VIVORA_VECTORSTORE_DIR", _DEFAULT_VECTORSTORE_DIR)


_embeddings_singleton = None

class _FastEmbedAdapter(Embeddings):
    """Thin Embeddings adapter using fastembed directly.

    Avoids langchain_community.embeddings.FastEmbedEmbeddings, which
    pulls in extra langchain wrappers we don't need. Subclassing
    Embeddings is important because FAISS checks that interface before
    deciding whether to call the object directly.
    """

    def __init__(self, model_name: str):
        from fastembed import TextEmbedding
        self._model = TextEmbedding(model_name=model_name)

    def embed_documents(self, texts):
        return [list(v) for v in self._model.embed(list(texts))]

    def embed_query(self, text: str):
        return list(next(iter(self._model.embed([text]))))


def _get_embeddings():
    """Load the embedding model once and reuse it.

    fastembed (ONNX) instead of sentence-transformers (PyTorch) keeps
    memory low enough for Streamlit Cloud. If fastembed is missing, fail
    clearly instead of falling back to the heavy torch stack.
    """
    global _embeddings_singleton
    if _embeddings_singleton is None:
        print(f"Loading embedding model: {EMBEDDING_MODEL} via fastembed...")
        try:
            _embeddings_singleton = _FastEmbedAdapter(EMBEDDING_MODEL)
        except ImportError as err:
            raise RuntimeError(
                "fastembed is required for local embeddings. Install dependencies "
                "from requirements.txt and make sure fastembed is available."
            ) from err
    return _embeddings_singleton


def _faiss():
    """Lazy FAISS import — keeps initial app boot fast."""
    from langchain_community.vectorstores import FAISS
    return FAISS


def chunk_files(files: list) -> list:
    from langchain_text_splitters import RecursiveCharacterTextSplitter

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


def build_rag_pipeline(files: list, persist_dir: str | None = None) -> bool:
    """
    Takes repo files and builds the complete RAG knowledge base.
    Returns True on success, False on failure. `persist_dir` lets each
    Streamlit session keep an isolated vector store. Use get_last_rag_error()
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

        build_vector_store(documents, persist_dir=persist_dir)
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
