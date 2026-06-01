from fastapi import FastAPI, HTTPException, Response
from pdf_utils import viva_to_pdf
from docx_utils import report_to_docx
from pptx_generator import create_presentation

from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import os
import re
import tempfile

# Your existing logic modules
from sessions import create_session, get_session
from repo_handler import clone_repo, get_useful_files, detect_tech_stack
from llm_chain import (
    GEMINI_MODEL,
    GROQ_MODEL,
    LLM_PROVIDER,
    generate_project_profile,
    generate_viva_questions,
    generate_weak_areas,
    answer_repo_question,
    generate_full_report,
    generate_slide_content,
)

from rag_engine import build_rag_pipeline, get_last_rag_error

def _require_session(session_id: str) -> dict:
    """Fetch a session, or return a clean 404 if the id is unknown.

    get_session() raises KeyError when the id isn't in the store; we
    translate that into a proper HTTP 404 so the browser gets a clear
    'Session not found' instead of a 500 crash.
    """
    try:
        return get_session(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found. Analyze a repo first.")

def _safe_download_name(name: str | None, fallback: str) -> str:
    """Return an ASCII-ish filename segment that is safe for download headers."""
    candidate = (name or fallback).strip()
    candidate = re.sub(r"[^A-Za-z0-9._-]+", "_", candidate).strip("._")
    return candidate or fallback


app = FastAPI(title="Vivora API")

def _get_cors_origins() -> list[str]:
    origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
    extra_origins = os.getenv("FRONTEND_ORIGIN", "")
    for origin in extra_origins.split(","):
        clean_origin = origin.strip().rstrip("/")
        if clean_origin and clean_origin not in origins:
            origins.append(clean_origin)
    return origins


app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "ok", "service": "vivora", "health": "/api/health", "docs": "/docs"}


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "vivora",
        "llm_provider": LLM_PROVIDER,
        "gemini_model": GEMINI_MODEL,
        "groq_model": GROQ_MODEL,
    }

class AnalyzeRequest(BaseModel):
    repo_url: str

class ChatRequest(BaseModel):
    session_id: str
    question: str
    history: list[dict] = Field(default_factory=list)   # [{"role": "user"/"assistant", "content": "..."}]

class SessionRequest(BaseModel):
    session_id: str

@app.post("/api/analyze")
def analyze(body: AnalyzeRequest):

    repo_url = body.repo_url.strip()
    if not repo_url.startswith("https://github.com/"):
        raise HTTPException(status_code=400, detail="URL must start with https://github.com/")

    session_id = create_session()
    session = get_session(session_id)
    clone_dir = os.path.join(tempfile.gettempdir(), f"vivora_clone_{session_id}")
    try:
        repo_path = clone_repo(repo_url, clone_dir=clone_dir)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not clone repo: {e}")
    
    files = get_useful_files(repo_path)
    if not files:
        raise HTTPException(status_code=422, detail="No readable files found in this repo.")
    
    tech_stack = detect_tech_stack(files)

    try:
        profile = generate_project_profile(files, tech_stack)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Profile generation failed: {type(e).__name__}: {e}")

    ok = build_rag_pipeline(files, persist_dir=session["vectorstore_dir"])
    if not ok:
        raise HTTPException(status_code=500, detail=f"Knowledge base build failed: {get_last_rag_error()}")
    
    session["files"] = files
    session["tech_stack"] = tech_stack
    session["profile"] = profile

    return {
        "session_id": session_id,
        "tech_stack": tech_stack,
        "profile": profile,
        "file_count": len(files),
        "files": [f["relative_path"] for f in files],
    }

@app.post("/api/chat")
def chat(body: ChatRequest):
    session = _require_session(body.session_id)
    if session["files"] is None:
        raise HTTPException(status_code=400, detail="Repo not analyzed yet.")
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # answer_repo_question already takes history + the session's vectorstore.
    return answer_repo_question(
        question=body.question.strip(),
        chat_history=body.history,
        persist_dir=session["vectorstore_dir"],
    )  # returns {"answer": ..., "sources": [...]}


@app.post("/api/viva")
def viva(body: SessionRequest):
    session = _require_session(body.session_id)
    if session["files"] is None:
        raise HTTPException(status_code=400, detail="Repo not analyzed yet.")
    markdown = generate_viva_questions(
        session["files"], session["tech_stack"], session["profile"]
    )
    session["viva"] = markdown   # cache it — the PDF download will reuse this
    return {"markdown": markdown}


@app.post("/api/weak-areas")
def weak_areas(body: SessionRequest):
    session = _require_session(body.session_id)
    if session["files"] is None:
        raise HTTPException(status_code=400, detail="Repo not analyzed yet.")
    markdown = generate_weak_areas(
        session["files"], session["tech_stack"], session["profile"]
    )
    session["weak_areas"] = markdown   # cache
    return {"markdown": markdown}

@app.post("/api/report")
def report(body: SessionRequest):
    session = _require_session(body.session_id)
    if session["files"] is None:
        raise HTTPException(status_code=400, detail="Repo not analyzed yet.")

    try:
        result = generate_full_report(
            files=session["files"],
            tech_stack=session["tech_stack"],
            profile=session["profile"],
            weak_areas=session["weak_areas"] or "",
            persist_dir=session["vectorstore_dir"],
        )
    except Exception as e:
        # Surface the real cause instead of a bare 500.
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")

    session["report"] = result
    return result



@app.post("/api/slides")
def slides(body: SessionRequest):
    session = _require_session(body.session_id)
    if session["files"] is None:
        raise HTTPException(status_code=400, detail="Repo not analyzed yet.")

    # report may be None (user didn't generate it) — the function treats
    # that as "no report context available", which is fine.
    slides_data = generate_slide_content(
        files=session["files"],
        tech_stack=session["tech_stack"],
        profile=session["profile"],
        report=session["report"],
    )
    session["slides"] = slides_data     # cache the list
    return {"slides": slides_data}

@app.get("/api/download/viva/{session_id}")
def download_viva(session_id: str):
    session = _require_session(session_id)
    markdown = session.get("viva")
    if not markdown:
        raise HTTPException(status_code=400, detail="Generate viva questions first.")

    pdf_bytes = viva_to_pdf(markdown)   # your existing function → returns bytes
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="viva_questions.pdf"'},
    )


@app.get("/api/download/report/{session_id}")
def download_report(session_id: str):
    session = _require_session(session_id)
    report = session.get("report")
    if not report:
        raise HTTPException(status_code=400, detail="Generate the report first.")

    docx_bytes = report_to_docx(report)
    filename = f"{_safe_download_name(report.get('project_name'), 'Project_Report')}_report.docx"
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/download/slides/{session_id}")
def download_slides(session_id: str):
    session = _require_session(session_id)
    slides_data = session.get("slides")
    if not slides_data:
        raise HTTPException(status_code=400, detail="Generate the slides first.")

    project_name = session["report"]["project_name"] if session.get("report") else "Project"
    pptx_bytes = create_presentation(slides_data, project_name=project_name)
    filename = f"{_safe_download_name(project_name, 'Project')}_presentation.pptx"
    return Response(
        content=pptx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
