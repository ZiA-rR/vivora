import os
import tempfile
import uuid

import streamlit as st

# ─────────────────────────────────────────────
# PAGE CONFIGURATION
# Must be the very first Streamlit command
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Vivora",
    page_icon=":material/auto_stories:",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def _use_fragment(func):
    """Use Streamlit fragments when available, with a harmless fallback."""
    fragment = getattr(st, "fragment", None)
    return fragment(func) if fragment else func

# ─────────────────────────────────────────────
# GLOBAL STYLES
# Small CSS layer on top of the dark teal theme
# ─────────────────────────────────────────────
st.markdown(
    """
    <style>
      /* Disable smooth-scroll and scroll-anchoring globally so nothing
         can animate the page to the bottom when new content appears
         after Analyze. */
      html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        scroll-behavior: auto !important;
        overflow-anchor: none !important;
      }

      /* page width + breathing room */
      .block-container { max-width: 1100px; padding-top: 1.5rem; padding-bottom: 4rem; }

      /* hero */
      .vm-hero { display:flex; align-items:center; gap:18px; padding: 6px 0 4px; }
      .vm-hero .badge {
        width:52px; height:52px; border-radius:12px;
        background: #0E1419;
        border: 1.5px solid #4EC9C0;
        display:flex; align-items:center; justify-content:center;
        font-family: 'Georgia', 'Times New Roman', serif;
        font-size: 28px; font-weight: 700; line-height: 1;
        color: #4EC9C0; letter-spacing: -0.02em;
      }
      .vm-hero h1 {
        margin:0; font-size: 2rem; font-weight:700; letter-spacing:-0.01em;
        color: #E4E9F0;
      }
      .vm-hero .tag { color:#9AA4B2; font-size: 0.95rem; margin-top:2px; }

      /* section titles a touch tighter */
      h2, h3 { letter-spacing: -0.01em; }

      /* buttons: rounder, no aggressive shadow */
      .stButton>button, .stDownloadButton>button {
        border-radius: 10px; font-weight: 600; padding: 0.55rem 1.1rem;
        border: 1px solid rgba(78,201,192,0.55);
        background-color: #1A222C;
        color: #E4E9F0;
      }
      .stButton>button:hover, .stDownloadButton>button:hover {
        border-color: #4EC9C0;
        background-color: #1F2933;
        color: #FFFFFF;
      }
      .stButton>button[kind="primary"], .stDownloadButton>button[kind="primary"] {
        background: linear-gradient(135deg,#4EC9C0,#2E75B6);
        color: #0E1419;
        border: none;
      }
      .stButton>button[kind="primary"]:hover, .stDownloadButton>button[kind="primary"]:hover {
        filter: brightness(1.1);
        color: #0E1419;
      }

      /* expanders & cards */
      div[data-testid="stExpander"] {
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 12px;
        background: #141B23;
      }

      /* metric tiles */
      div[data-testid="stMetric"] {
        background: #141B23; padding: 14px 18px; border-radius: 12px;
        border: 1px solid rgba(255,255,255,0.05);
      }

      /* chat bubbles */
      div[data-testid="stChatMessage"] { background:#141B23; border-radius:14px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.markdown(
    """
    <div id="vivora-top"></div>
    <div class="vm-hero">
      <div class="badge">V</div>
      <div>
        <h1>Vivora</h1>
        <div class="tag">Turn any GitHub repo into a viva-ready brief &mdash; profile, Q&amp;A, report and slides.</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()

# ─────────────────────────────────────────────
# INPUT SECTION
# ─────────────────────────────────────────────
github_url = st.text_input(
    label="GitHub Repository URL",
    placeholder="https://github.com/username/project-name"
)

analyze_button = st.button("Analyze Repo", type="primary")

# ─────────────────────────────────────────────
# SESSION STATE SETUP
# ─────────────────────────────────────────────
if "files" not in st.session_state:
    st.session_state.files = None

if "tech_stack" not in st.session_state:
    st.session_state.tech_stack = None

if "repo_url" not in st.session_state:
    st.session_state.repo_url = None

if "profile" not in st.session_state:
    st.session_state.profile = None

if "profile_error" not in st.session_state:
    st.session_state.profile_error = None

if "rag_ready" not in st.session_state:
    st.session_state.rag_ready = False

if "rag_error" not in st.session_state:
    st.session_state.rag_error = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "viva_questions" not in st.session_state:
    st.session_state.viva_questions = None

if "weak_areas" not in st.session_state:
    st.session_state.weak_areas = None

if "report" not in st.session_state:
    st.session_state.report = None

if "slides" not in st.session_state:
    st.session_state.slides = None

if "session_id" not in st.session_state:
    st.session_state.session_id = uuid.uuid4().hex

if "clone_dir" not in st.session_state:
    st.session_state.clone_dir = os.path.join(
        tempfile.gettempdir(),
        f"vivora_clone_{st.session_state.session_id}",
    )

if "vectorstore_dir" not in st.session_state:
    st.session_state.vectorstore_dir = os.path.join(
        tempfile.gettempdir(),
        f"vivora_vectorstore_{st.session_state.session_id}",
    )

# ─────────────────────────────────────────────
# STEP 1: CLONE + READ REPO
# ─────────────────────────────────────────────
if analyze_button:
    repo_url = github_url.strip()

    if not repo_url:
        st.error("Please enter a GitHub URL first.")

    elif not repo_url.startswith("https://github.com/"):
        st.error("Please enter a valid public GitHub URL (must start with https://github.com/)")

    else:
        # Reset everything when analyzing a new repo
        st.session_state.files = None
        st.session_state.tech_stack = None
        st.session_state.repo_url = None
        st.session_state.profile = None
        st.session_state.profile_error = None
        st.session_state.rag_ready = False
        st.session_state.rag_error = None
        st.session_state.chat_history = []
        st.session_state.viva_questions = None
        st.session_state.weak_areas = None
        st.session_state.report = None
        st.session_state.slides = None
        with st.spinner("Cloning repository... this may take a few seconds"):
            try:
                from repo_handler import clone_repo, detect_tech_stack, get_useful_files

                repo_path = clone_repo(repo_url, clone_dir=st.session_state.clone_dir)
                files = get_useful_files(repo_path)

                if not files:
                    st.error("No readable source or documentation files were found in this repo.")
                    st.info("Vivora reads common text/code files such as .py, .md, .js, .html, .css, .json, .yaml, and .toml.")
                else:
                    tech_stack = detect_tech_stack(files)

                    st.session_state.files = files
                    st.session_state.tech_stack = tech_stack
                    st.session_state.repo_url = repo_url

                    st.success(f"Repo cloned! Found {len(files)} useful files.")

            except Exception as e:
                st.error(f"Something went wrong: {e}")
                st.info("Make sure the repo is public and the URL is correct.")

# ─────────────────────────────────────────────
# STEP 2: GENERATE AI PROJECT PROFILE
# ─────────────────────────────────────────────
if (
    st.session_state.files is not None
    and st.session_state.profile is None
    and st.session_state.profile_error is None
):
    with st.spinner("Reading your repo and generating a project profile..."):
        try:
            from llm_chain import generate_project_profile

            profile = generate_project_profile(
                st.session_state.files,
                st.session_state.tech_stack
            )
            st.session_state.profile = profile
        except Exception as e:
            st.session_state.profile_error = f"Profile generation failed: {e}"

if st.session_state.profile_error and st.session_state.profile is None:
    st.error(st.session_state.profile_error)

# ─────────────────────────────────────────────
# STEP 3: BUILD RAG KNOWLEDGE BASE
# ─────────────────────────────────────────────
if st.session_state.profile and not st.session_state.rag_ready and st.session_state.rag_error is None:
    with st.spinner("Building knowledge base from repo files..."):
        from rag_engine import build_rag_pipeline, get_last_rag_error

        success = build_rag_pipeline(
            st.session_state.files,
            persist_dir=st.session_state.vectorstore_dir,
        )
        if success:
            st.session_state.rag_ready = True
            st.success("Knowledge base ready.")
        else:
            err = get_last_rag_error() or "unknown error (check terminal for traceback)"
            st.session_state.rag_error = f"Failed to build knowledge base: {err}"

if st.session_state.rag_error and not st.session_state.rag_ready:
    st.error(st.session_state.rag_error)

# ─────────────────────────────────────────────
# RESULTS SECTION
# ─────────────────────────────────────────────
if st.session_state.files is not None:

    st.divider()
    st.subheader("Repo Overview")

    tech = st.session_state.tech_stack
    files = st.session_state.files

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Files Found", len(files))
    with col2:
        st.metric("Languages", len(tech["languages"]))
    with col3:
        st.metric("Frameworks", len(tech["frameworks"]))

    st.markdown("**Languages Detected:**")
    if tech["languages"]:
        st.write(", ".join(tech["languages"]))
    else:
        st.write("None detected")

    st.markdown("**Frameworks / Libraries Detected:**")
    if tech["frameworks"]:
        st.write(", ".join(tech["frameworks"]))
    else:
        st.write("None detected")

    if tech["databases"]:
        st.markdown("**Databases Detected:**")
        st.write(", ".join(tech["databases"]))

    st.markdown("**Project Health Check:**")
    col1, col2, col3 = st.columns(3)
    with col1:
        if tech["has_readme"]:
            st.success("README found")
        else:
            st.error("No README")
    with col2:
        if tech["has_requirements"]:
            st.success("Requirements found")
        else:
            st.error("No requirements file")
    with col3:
        if tech["has_tests"]:
            st.success("Tests found")
        else:
            st.warning("No tests found")

    st.divider()
    st.subheader("Files Analyzed")
    with st.expander("Click to see all files"):
        for f in files:
            st.code(f["relative_path"], language=None)

# ─────────────────────────────────────────────
# AI PROJECT PROFILE
# Generated automatically — used as input by every downstream feature
# (chat, viva, weak areas, report, slides). Tucked into an expander so
# it doesn't dominate the page.
# ─────────────────────────────────────────────
if st.session_state.profile:
    st.divider()
    with st.expander("AI-Generated Project Profile (used internally by Chat / Viva / Report / Slides)", expanded=False):
        st.markdown(st.session_state.profile)

# ─────────────────────────────────────────────
# POST-ANALYSIS TOOLS
# Fragment reruns keep long generator actions from redrawing the whole app.
# ─────────────────────────────────────────────
@_use_fragment
def render_viva_section():
    st.divider()
    st.subheader("Viva Preparation")
    st.caption("AI-generated questions and suggested answers based on your actual project.")

    if st.button("Generate Viva Questions + Answers", type="primary", key="gen_viva"):
        st.session_state.viva_questions = None
        with st.spinner("Preparing your viva questions..."):
            try:
                from llm_chain import generate_viva_questions

                st.session_state.viva_questions = generate_viva_questions(
                    files=st.session_state.files,
                    tech_stack=st.session_state.tech_stack,
                    profile=st.session_state.profile,
                )
            except Exception as e:
                st.error(f"Could not generate questions: {e}")

    if st.session_state.viva_questions:
        from pdf_utils import viva_to_pdf

        st.markdown(st.session_state.viva_questions)
        st.download_button(
            label="Download Questions as PDF",
            data=viva_to_pdf(st.session_state.viva_questions),
            file_name="viva_questions.pdf",
            mime="application/pdf",
        )


@_use_fragment
def render_weak_area_section():
    st.divider()
    st.subheader("Weak Area Analysis")
    st.caption("Find out what's missing or weak in your project before your viva.")

    if st.button("Analyze Weak Areas", type="primary", key="gen_weak"):
        st.session_state.weak_areas = None
        with st.spinner("Analyzing your project for weak areas..."):
            try:
                from llm_chain import generate_weak_areas

                st.session_state.weak_areas = generate_weak_areas(
                    files=st.session_state.files,
                    tech_stack=st.session_state.tech_stack,
                    profile=st.session_state.profile,
                )
                st.success("Weak area analysis ready.")
            except Exception as e:
                st.error(f"Could not analyze weak areas: {e}")

    if st.session_state.weak_areas:
        st.markdown(st.session_state.weak_areas)
        st.download_button(
            label="Download Weak Area Report",
            data=st.session_state.weak_areas,
            file_name="weak_areas.txt",
            mime="text/plain",
        )


@_use_fragment
def render_report_section():
    st.divider()
    st.subheader("Project Report Generator")
    st.caption("Generate a full academic project report based on your repo.")
    st.info("Takes about 1-2 minutes; 11 sections are written one by one for quality.")

    if st.button("Generate Full Report", type="primary", key="gen_report"):
        st.session_state.report = None
        progress_bar = st.progress(0.0, text="Starting report generation...")

        def _on_progress(done, total, current_name):
            fraction = done / total if total else 0.0
            label = "Report complete!" if done == total else f"Writing: {current_name}..."
            progress_bar.progress(min(fraction, 1.0), text=label)

        try:
            from llm_chain import generate_full_report

            st.session_state.report = generate_full_report(
                files=st.session_state.files,
                tech_stack=st.session_state.tech_stack,
                profile=st.session_state.profile,
                weak_areas=st.session_state.weak_areas or "",
                progress_callback=_on_progress,
                persist_dir=st.session_state.vectorstore_dir,
            )
            st.success(f"Report ready; {len(st.session_state.report['sections'])} sections written.")
        except Exception as e:
            st.error(f"Report generation failed: {e}")

    if st.session_state.report:
        try:
            from docx_utils import report_to_docx

            docx_bytes = report_to_docx(st.session_state.report)
            st.download_button(
                label="Download Report (Word .docx)",
                data=docx_bytes,
                file_name=f"{st.session_state.report['project_name'].replace(' ', '_')}_report.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                type="primary",
            )
        except Exception as e:
            st.error(f"Word export failed: {e}")


@_use_fragment
def render_slides_section():
    st.divider()
    st.subheader("Presentation Slides Generator")
    st.caption("Generate a polished PowerPoint deck from your repo.")

    if st.session_state.report is None:
        st.warning("Tip: generate the project report above first; slides are richer when they can reference report content.")

    if st.button("Generate Presentation Slides", type="primary", key="gen_slides"):
        st.session_state.slides = None
        with st.spinner("Generating slide content..."):
            try:
                from llm_chain import generate_slide_content

                st.session_state.slides = generate_slide_content(
                    files=st.session_state.files,
                    tech_stack=st.session_state.tech_stack,
                    profile=st.session_state.profile,
                    report=st.session_state.report,
                )
                st.success(f"Generated {len(st.session_state.slides)} slides.")
            except Exception as e:
                st.error(f"Slide generation failed: {e}")

    if st.session_state.slides:
        try:
            from pptx_generator import create_presentation

            project_name = (
                st.session_state.report["project_name"]
                if st.session_state.report
                else "Project"
            )
            pptx_bytes = create_presentation(
                slides_data=st.session_state.slides,
                project_name=project_name,
            )
            st.download_button(
                label="Download Presentation (.pptx)",
                data=pptx_bytes,
                file_name=f"{project_name.replace(' ', '_')}_presentation.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                type="primary",
            )
        except Exception as e:
            st.error(f"PPTX export failed: {e}")


@_use_fragment
def render_chat_section():
    st.divider()
    st.subheader("Ask Anything About This Repo")
    st.caption("Ask about any file, feature, function, or concept in the project.")

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    with st.form("repo_chat_form", clear_on_submit=True):
        user_question = st.text_input(
            "Ask something about the repo",
            placeholder="Example: What does app.py do?",
        )
        submitted = st.form_submit_button("Ask", type="primary")

    if submitted:
        question = user_question.strip()
        if not question:
            st.warning("Please type a question first.")
            return

        with st.chat_message("user"):
            st.markdown(question)

        st.session_state.chat_history.append({
            "role": "user",
            "content": question,
        })

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    from llm_chain import answer_repo_question

                    result = answer_repo_question(
                        question=question,
                        chat_history=st.session_state.chat_history,
                        persist_dir=st.session_state.vectorstore_dir,
                    )
                    answer = result["answer"]
                    sources = result["sources"]

                    st.markdown(answer)

                    if sources:
                        with st.expander("Sources used"):
                            for source in sources:
                                st.code(source, language=None)

                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": answer,
                    })

                except Exception as e:
                    st.error(f"Could not get answer: {e}")


if st.session_state.rag_ready:
    render_chat_section()
    render_viva_section()
    render_weak_area_section()
    render_report_section()
    render_slides_section()
