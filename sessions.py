"""
In-memory session store for Vivora's FastAPI backend.

WHY THIS EXISTS
---------------
Streamlit gave every browser tab its own `st.session_state` automatically.
FastAPI does not — it is "stateless": each HTTP request is independent and
the server forgets everything between requests.

So when the browser calls POST /api/analyze, we clone the repo and build the
RAG index ONCE, then we need to remember the result so the later calls
(/api/chat, /api/report, ...) can reuse it without re-cloning.

We solve that with a plain Python dict keyed by a random `session_id`:

    SESSIONS = {
        "ab12cd...": {            # one entry per analyzed repo
            "files": [...],        # the repo's useful files
            "tech_stack": {...},
            "profile": "...",
            "vectorstore_dir": "/tmp/vivora_vs_ab12cd",
            "weak_areas": "...",   # cached after first generation
            "report": {...},       # cached
            "slides": [...],       # cached
        },
        ...
    }

LIMITATIONS (fine for a demo / single user, important to know for a viva):
  - Lives in RAM only: restart the server and all sessions are gone.
  - Not shared across multiple server processes (one uvicorn worker only).
  - No expiry/cleanup. For production you'd use Redis or a database.
"""

from __future__ import annotations

import os
import tempfile
import uuid

# The actual store. Module-level dict = lives as long as the process does.
SESSIONS: dict[str, dict] = {}


def create_session() -> str:
    """Make a new session, return its id.

    We also pre-compute a unique vectorstore directory for this session so
    two different analyzed repos never overwrite each other's FAISS index.
    """
    session_id = uuid.uuid4().hex  # e.g. "9f8c2a1b...." — random, unguessable
    SESSIONS[session_id] = {
        "files": None,
        "tech_stack": None,
        "profile": None,
        "vectorstore_dir": os.path.join(
            tempfile.gettempdir(), f"vivora_vs_{session_id}"
        ),
        "weak_areas": None,
        "report": None,
        "slides": None,
    }
    return session_id


def get_session(session_id: str) -> dict:
    """Fetch a session or raise KeyError if it doesn't exist.

    The API layer turns that KeyError into a clean 404 response.
    """
    if session_id not in SESSIONS:
        raise KeyError(session_id)
    return SESSIONS[session_id]
