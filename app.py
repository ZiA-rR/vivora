import streamlit as st
import streamlit.components.v1 as components
from repo_handler import clone_repo, get_useful_files, detect_tech_stack
from llm_chain import (
    generate_project_profile,
    answer_repo_question,
    generate_viva_questions,
    generate_weak_areas,
    generate_full_report,
    generate_slide_content,
)
from rag_engine import build_rag_pipeline, get_last_rag_error
from pdf_utils import viva_to_pdf
from docx_utils import report_to_docx
from pptx_generator import create_presentation

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

# ─────────────────────────────────────────────
# GLOBAL STYLES
# Small CSS layer on top of the dark teal theme
# ─────────────────────────────────────────────
st.markdown(
    """
    <style>
      /* page width + breathing room. Bottom padding must clear the
         floating st.chat_input bar (~80px) or buttons at the end of
         the page sit underneath it and look unclickable. */
      .block-container { max-width: 1100px; padding-top: 1.5rem; padding-bottom: 9rem; }

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

if "rag_ready" not in st.session_state:
    st.session_state.rag_ready = False

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

# ─────────────────────────────────────────────
# STEP 1: CLONE + READ REPO
# ─────────────────────────────────────────────
if analyze_button:

    if not github_url.strip():
        st.error("Please enter a GitHub URL first.")

    elif not github_url.startswith("https://github.com/"):
        st.error("Please enter a valid public GitHub URL (must start with https://github.com/)")

    else:
        # Reset everything when analyzing a new repo
        st.session_state.profile = None
        st.session_state.rag_ready = False
        st.session_state.chat_history = []
        st.session_state.viva_questions = None
        st.session_state.weak_areas = None
        st.session_state.report = None
        st.session_state.slides = None
        # Tell the end-of-page hook to scroll back to the top after this
        # rerun completes — counteracts the browser's tendency to scroll
        # to the new st.chat_input element that gets added once rag_ready
        # becomes True. Reset the chat-render memo so the scroll-to-top
        # also fires the moment the chat section appears for this new repo.
        st.session_state._scroll_to_top = True
        st.session_state._chat_rendered_once = False

        with st.spinner("Cloning repository... this may take a few seconds"):
            try:
                repo_path = clone_repo(github_url)
                files = get_useful_files(repo_path)
                tech_stack = detect_tech_stack(files)

                st.session_state.files = files
                st.session_state.tech_stack = tech_stack
                st.session_state.repo_url = github_url

                st.success(f"Repo cloned! Found {len(files)} useful files.")

            except Exception as e:
                st.error(f"Something went wrong: {e}")
                st.info("Make sure the repo is public and the URL is correct.")

# ─────────────────────────────────────────────
# STEP 2: GENERATE AI PROJECT PROFILE
# ─────────────────────────────────────────────
if st.session_state.files is not None and st.session_state.profile is None:
    with st.spinner("Gemini is reading your repo and generating a project profile..."):
        try:
            profile = generate_project_profile(
                st.session_state.files,
                st.session_state.tech_stack
            )
            st.session_state.profile = profile
        except Exception as e:
            st.error(f"Profile generation failed: {e}")

# ─────────────────────────────────────────────
# STEP 3: BUILD RAG KNOWLEDGE BASE
# ─────────────────────────────────────────────
if st.session_state.profile and not st.session_state.rag_ready:
    with st.spinner("Building knowledge base from repo files..."):
        success = build_rag_pipeline(st.session_state.files)
        if success:
            st.session_state.rag_ready = True
            st.success("Knowledge base ready.")
        else:
            err = get_last_rag_error() or "unknown error (check terminal for traceback)"
            st.error(f"Failed to build knowledge base: {err}")

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
# GENERATION SECTIONS
# Each is wrapped in @st.fragment so that running an LLM in one
# section does NOT dim/disable the others. Without fragments, a single
# Generate click puts the whole page into Streamlit's "script running"
# state for the full 5-30 s LLM call, freezing every other button.
# ─────────────────────────────────────────────

@st.fragment
def viva_section():
    st.divider()
    st.subheader("Viva Preparation")
    st.caption("AI-generated questions and suggested answers based on your actual project.")

    if st.button("Generate Viva Questions + Answers", type="primary", key="gen_viva"):
        with st.spinner("Preparing your viva questions..."):
            try:
                st.session_state.viva_questions = generate_viva_questions(
                    files=st.session_state.files,
                    tech_stack=st.session_state.tech_stack,
                    profile=st.session_state.profile,
                )
            except Exception as e:
                st.error(f"Could not generate questions: {e}")

    if st.session_state.viva_questions:
        st.markdown(st.session_state.viva_questions)
        st.download_button(
            label="Download Questions as PDF",
            data=viva_to_pdf(st.session_state.viva_questions),
            file_name="viva_questions.pdf",
            mime="application/pdf",
        )


@st.fragment
def weak_section():
    st.divider()
    st.subheader("Weak Area Analysis")
    st.caption("Find out what's missing or weak in your project before your viva.")

    if st.button("Analyze Weak Areas", type="primary", key="gen_weak"):
        with st.spinner("Analyzing your project for weak areas..."):
            try:
                st.session_state.weak_areas = generate_weak_areas(
                    files=st.session_state.files,
                    tech_stack=st.session_state.tech_stack,
                    profile=st.session_state.profile,
                )
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


@st.fragment
def report_section():
    st.divider()
    st.subheader("Project Report Generator")
    st.caption("Generate a full academic project report based on your repo.")
    st.info("Takes about 1-2 minutes — 11 sections are written one by one for quality.")

    if st.button("Generate Full Report", type="primary", key="gen_report"):
        st.session_state.report = None
        progress_bar = st.progress(0.0, text="Starting report generation...")

        def _on_progress(done, total, current_name):
            fraction = done / total if total else 0.0
            label = "Report complete!" if done == total else f"Writing: {current_name}..."
            progress_bar.progress(min(fraction, 1.0), text=label)

        try:
            st.session_state.report = generate_full_report(
                files=st.session_state.files,
                tech_stack=st.session_state.tech_stack,
                profile=st.session_state.profile,
                weak_areas=st.session_state.weak_areas or "",
                progress_callback=_on_progress,
            )
            st.success(f"Report ready — {len(st.session_state.report['sections'])} sections written.")
        except Exception as e:
            st.error(f"Report generation failed: {e}")

    if st.session_state.report:
        try:
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


@st.fragment
def slides_section():
    st.divider()
    st.subheader("Presentation Slides Generator")
    st.caption("Generate a polished PowerPoint deck from your repo.")

    if st.session_state.report is None:
        st.warning("Tip: generate the project report above first — slides are richer when they can reference report content.")

    if st.button("Generate Presentation Slides", type="primary", key="gen_slides"):
        st.session_state.slides = None
        with st.spinner("Generating slide content..."):
            try:
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


if st.session_state.rag_ready:
    viva_section()
    weak_section()
    report_section()
    slides_section()

# ─────────────────────────────────────────────
# REPO CHATBOT
# Placed last so newly rendered messages sit directly above the
# floating chat input — no scrolling back up to find the answer.
# ─────────────────────────────────────────────
if st.session_state.rag_ready:
    st.divider()
    st.subheader("Ask Anything About This Repo")
    st.caption("Ask about any file, feature, function, or concept in the project. Type below from anywhere on the page — the answer appears right here.")

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_question = st.chat_input("Ask something about the repo...")

    if user_question:
        with st.chat_message("user"):
            st.markdown(user_question)

        st.session_state.chat_history.append({
            "role": "user",
            "content": user_question,
        })

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    result = answer_repo_question(
                        question=user_question,
                        chat_history=st.session_state.chat_history,
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

        # Drop an anchor right at the bottom of the chat block and
        # scroll the parent window to it via scrollIntoView. The unique
        # nonce forces the iframe to re-render on every submission.
        import time as _time
        _nonce = int(_time.time() * 1000)
        st.markdown(
            f'<div id="vivora-chat-end" data-nonce="{_nonce}" style="height:1px;"></div>',
            unsafe_allow_html=True,
        )
        components.html(
            f"""
            <script>
              // nonce={_nonce}
              (function() {{
                function scroll() {{
                  try {{
                    var doc = window.parent.document;
                    var anchor = doc.getElementById('vivora-chat-end');
                    if (anchor && anchor.scrollIntoView) {{
                      anchor.scrollIntoView({{ behavior: 'smooth', block: 'end' }});
                      console.log('[vivora] scrolled to anchor');
                      return true;
                    }}
                    // Fallback: scroll the top window
                    window.parent.scrollTo(0, 99999999);
                    console.log('[vivora] fallback scroll');
                  }} catch (e) {{
                    console.error('[vivora] scroll error:', e);
                  }}
                  return false;
                }}
                setTimeout(scroll, 50);
                setTimeout(scroll, 300);
                setTimeout(scroll, 700);
                setTimeout(scroll, 1500);
              }})();
            </script>
            """,
            height=1,
        )

# ─────────────────────────────────────────────
# SCROLL-TO-TOP HOOK
# The browser auto-scrolls to the newly added st.chat_input the first
# time `rag_ready` flips True (Analyze finished). Counteract it by
# firing scrollTo(0,0) repeatedly across the first 3 seconds so we win
# the timing race against the browser. Fires on Analyze AND on the
# first render where the chat section appears.
# ─────────────────────────────────────────────
_first_chat_render = (
    st.session_state.rag_ready
    and not st.session_state.get("_chat_rendered_once", False)
)
if _first_chat_render:
    st.session_state._chat_rendered_once = True

if st.session_state.pop("_scroll_to_top", False) or _first_chat_render:
    import time as _time
    _top_nonce = int(_time.time() * 1000)
    components.html(
        f"""
        <script>
          // nonce={_top_nonce}
          (function() {{
            var W;
            try {{ W = window.parent; }} catch (_) {{ W = window; }}

            // Stop the browser from restoring scroll position across reruns.
            try {{ W.history.scrollRestoration = 'manual'; }} catch (_) {{}}

            // Block all scrollIntoView calls for 3 s — this is what the
            // newly added st.chat_input was using to drag the page to the
            // bottom. Restore after to not break legit user actions.
            try {{
              var ElemProto = W.Element && W.Element.prototype;
              if (ElemProto && !ElemProto.__vivora_patched) {{
                var orig = ElemProto.scrollIntoView;
                ElemProto.__vivora_patched = true;
                ElemProto.scrollIntoView = function() {{ /* suppressed */ }};
                setTimeout(function() {{
                  ElemProto.scrollIntoView = orig;
                  delete ElemProto.__vivora_patched;
                }}, 3000);
              }}
            }} catch (e) {{ console.warn('[vivora] sIV patch failed:', e); }}

            function up() {{
              try {{
                var doc = W.document;
                var targets = [
                  doc.querySelector('[data-testid="stAppViewContainer"]'),
                  doc.querySelector('section.main'),
                  doc.scrollingElement, doc.documentElement, doc.body,
                ];
                for (var i = 0; i < targets.length; i++) {{
                  if (targets[i]) {{
                    try {{ targets[i].scrollTop = 0; }} catch (_) {{}}
                  }}
                }}
                try {{ W.scrollTo(0, 0); }} catch (_) {{}}
              }} catch (e) {{ console.warn('[vivora] top-scroll failed:', e); }}
            }}

            // Hammer scrollTo every 100 ms for 3 s so nothing else can
            // sneak a scroll past us.
            up();
            var iv = setInterval(up, 100);
            setTimeout(function() {{ clearInterval(iv); }}, 3000);
          }})();
        </script>
        """,
        height=1,
    )