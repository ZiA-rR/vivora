import os
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from rag_engine import retrieve_context

load_dotenv()

LLM_MODEL = "llama-3.1-8b-instant"

_llm = None


def _get_llm():
    """Lazily construct the Groq client.

    Initializing ChatGroq at module-import time crashes the entire
    Streamlit app if GROQ_API_KEY is missing or invalid (e.g. a stale
    Cloud secret), because the page can't render anything. Constructing
    on first use means the app loads cleanly and the user only sees an
    error in the section that actually tried to call the LLM.
    """
    global _llm
    if _llm is None:
        from langchain_groq import ChatGroq
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Add it to your local .env file or, "
                "if deployed, to Streamlit Cloud's Settings → Secrets."
            )
        _llm = ChatGroq(
            model=LLM_MODEL,
            groq_api_key=api_key,
            temperature=0.3,
        )
    return _llm


# Back-compat alias so existing `llm.invoke(...)` call sites keep working
# without touching every function below — `llm` is now a lazy proxy.
class _LazyLLM:
    def invoke(self, *args, **kwargs):
        return _get_llm().invoke(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(_get_llm(), name)


llm = _LazyLLM()

def get_key_files_content(files: list, max_chars: int = 12000) -> str:
    priority_files = []
    other_files = []

    for f in files:
        name = f["file_name"].lower()
        # README and requirements are the most informative
        if name in ("readme.md", "readme.txt", "requirements.txt",
                    "pyproject.toml", "package.json"):
            priority_files.append(f)
        else:
            other_files.append(f)

    ordered_files = priority_files + other_files
    combined = ""
    for f in ordered_files:
        # Add a clear header before each file so Gemini knows which file it's reading
        chunk = f"\n\n=== FILE: {f['relative_path']} ===\n{f['content']}"

        # Stop adding files if we're approaching the character limit
        if len(combined) + len(chunk) > max_chars:
            break
    
        combined += chunk
    
    return combined

def generate_project_profile(files: list, tech_stack: dict) -> str:
    """
    Sends the repo content to Gemini and asks it to
    generate a structured project profile.

    Returns the profile as a formatted string.
    """
    repo_content = get_key_files_content(files)

    prompt_template = PromptTemplate(
        input_variables=["repo_content", "languages", "frameworks"],
        template="""
You are an expert software project analyst.

Analyze the following GitHub repository files and generate a structured project profile.

Repository Files:
{repo_content}

Detected Tech Stack:
- Languages: {languages}
- Frameworks: {frameworks}

Generate a clear and structured project profile with the following sections:

1. PROJECT NAME
   (guess the project name from README or main file)

2. MAIN PURPOSE
   (what does this project do? one clear sentence)

3. TARGET USERS
   (who would use this project?)

4. MAIN FEATURES
   (list 3-5 main features)

5. TECH STACK
   (languages, frameworks, libraries actually used)

6. MAIN FILES AND THEIR ROLES
   (explain what each important file does)

7. HOW THE SYSTEM WORKS
   (brief explanation of the flow/architecture)

8. PROJECT TYPE
   (web app / CLI tool / API / ML model / library / etc)

Be specific and base your answer ONLY on what you can see in the files.
Do not guess or make up features that are not visible in the code.
"""
    )

    formatted_prompt = prompt_template.format(
        repo_content=repo_content,
        languages=", ".join(tech_stack["languages"]) or "Not detected",
        frameworks=", ".join(tech_stack["frameworks"]) or "Not detected"
    )
    response = llm.invoke(formatted_prompt)

    return response.content

def answer_repo_question(
    question: str,
    chat_history: list | None = None,
    persist_dir: str | None = None,
) -> dict:
    context = retrieve_context(question, persist_dir=persist_dir)
    chat_history = chat_history or []

    history_text = ""
    for msg in chat_history[-6:]:  # only last 6 messages to save tokens
        role = "User" if msg["role"] == "user" else "Assistant"
        history_text += f"{role}: {msg['content']}\n"

    prompt_template = PromptTemplate(
        input_variables=["context", "history", "question"],
        template="""
You are Vivora, an expert assistant that helps students understand
and defend their GitHub projects.

You have access to the actual code and files from the student's repository.
Use this information to give accurate, specific answers.

Relevant code and files from the repository:
{context}

Previous conversation:
{history}

Student's question: {question}

Instructions:
- Answer based ONLY on what you can see in the repository files above
- Be specific — mention actual file names, function names, and code details
- If something is not visible in the files, say so honestly
- Keep the answer clear and helpful for a student preparing for viva
- If the question is about explaining code, explain it simply
"""
    )

    formatted_prompt = prompt_template.format(
        context=context,
        history=history_text if history_text else "No previous conversation.",
        question=question
    )
    response = llm.invoke(formatted_prompt)

    sources = []
    for line in context.split("\n"):
        if line.startswith("--- From "):
            source = line.replace("--- From ", "").replace(" ---", "").strip()
            if source not in sources:
                sources.append(source)

    return {
        "answer": response.content,
        "sources": sources
    }

def generate_viva_questions(files: list, tech_stack: dict, profile: str) -> str:
    repo_content = get_key_files_content(files)

    prompt_template = PromptTemplate(
        input_variables=["repo_content", "profile", "languages", "frameworks", "has_tests"],
        template="""
You are Vivora, an expert academic viva coach.

A student needs to prepare for their project viva/defense.
Below is their GitHub project content and profile.

Project Profile:
{profile}

Repository Files:
{repo_content}

Tech Stack:
- Languages: {languages}
- Frameworks: {frameworks}
- Has Tests: {has_tests}

Generate exactly 12 viva questions with suggested answers.
Organize them into 4 categories of 3 questions each.

Format your response EXACTLY like this:

## 📌 Basic Questions

**Q1: [question here]**
> **Suggested Answer:** [answer here based on the actual project]

**Q2: [question here]**
> **Suggested Answer:** [answer here based on the actual project]

**Q3: [question here]**
> **Suggested Answer:** [answer here based on the actual project]

## 💻 Technical Questions

**Q4: [question about specific code, files, or functions]**
> **Suggested Answer:** [answer mentioning actual file names and code]

**Q5: [question here]**
> **Suggested Answer:** [answer here]

**Q6: [question here]**
> **Suggested Answer:** [answer here]

## 🛠️ Tools and Libraries Questions

**Q7: [question about why a specific library or tool was used]**
> **Suggested Answer:** [answer explaining the choice based on actual requirements]

**Q8: [question here]**
> **Suggested Answer:** [answer here]

**Q9: [question here]**
> **Suggested Answer:** [answer here]

## ⚠️ Weak Area Questions

**Q10: [question about something missing or weak in the project]**
> **Suggested Answer:** [honest answer + how student would improve it]

**Q11: [question here]**
> **Suggested Answer:** [answer here]

**Q12: [question here]**
> **Suggested Answer:** [answer here]

IMPORTANT RULES:
- Every question and answer must be specific to THIS project
- Mention actual file names, function names, and library names
- Do not generate generic questions that could apply to any project
- Weak area questions should reflect what is actually missing from this repo
- Answers should be 2-4 sentences, clear and confident
"""
    )

    formatted_prompt = prompt_template.format(
        repo_content=repo_content,
        profile=profile,
        languages=", ".join(tech_stack["languages"]) or "Not detected",
        frameworks=", ".join(tech_stack["frameworks"]) or "Not detected",
        has_tests="Yes" if tech_stack["has_tests"] else "No"
    )

    response = llm.invoke(formatted_prompt)
    return response.content


# ─────────────────────────────────────────────
# FUNCTION: Weak Area Analysis
# ─────────────────────────────────────────────

def generate_weak_areas(files: list, tech_stack: dict, profile: str) -> str:
    """
    Analyzes the repo for missing elements, poor practices,
    and areas that need improvement before a viva.

    Combines rule-based checks with AI analysis
    for a complete weakness report.
    """

    # ── PART 1: Rule-based checks ──
    rule_based_issues = []
    rule_based_suggestions = []

    if not tech_stack["has_readme"]:
        rule_based_issues.append("❌ No README file found")
        rule_based_suggestions.append("Add a README.md with project description, setup instructions, and usage guide")

    if not tech_stack["has_requirements"]:
        rule_based_issues.append("❌ No requirements.txt or dependency file found")
        rule_based_suggestions.append("Add requirements.txt listing all dependencies with versions")

    if not tech_stack["has_tests"]:
        rule_based_issues.append("❌ No test files found")
        rule_based_suggestions.append("Add unit tests for core functions using pytest or unittest")

    file_names = [f["file_name"].lower() for f in files]
    all_content = " ".join([f["content"].lower() for f in files])

    if ".gitignore" not in file_names:
        rule_based_issues.append("❌ No .gitignore file found")
        rule_based_suggestions.append("Add a .gitignore to prevent sensitive files and cache from being committed")

    if "license" not in " ".join(file_names):
        rule_based_issues.append("⚠️ No LICENSE file found")
        rule_based_suggestions.append("Add a LICENSE file (MIT is common for student projects)")

    if "screenshot" not in all_content and "demo" not in all_content:
        rule_based_issues.append("⚠️ No screenshots or demo mentioned")
        rule_based_suggestions.append("Add screenshots or a demo GIF to README to show the project working")

    if "deploy" not in all_content and "installation" not in all_content:
        rule_based_issues.append("⚠️ No deployment or installation instructions found")
        rule_based_suggestions.append("Add clear installation and deployment instructions to README")

    if rule_based_issues:
        rule_based_text = "RULE-BASED CHECKS FOUND THESE ISSUES:\n"
        rule_based_text += "\n".join(rule_based_issues)
        rule_based_text += "\n\nSUGGESTIONS:\n"
        rule_based_text += "\n".join(rule_based_suggestions)
    else:
        rule_based_text = "RULE-BASED CHECKS: All basic files present."

    # ── PART 2: AI-powered deep analysis ──
    repo_content = get_key_files_content(files)

    prompt_template = PromptTemplate(
        input_variables=["repo_content", "profile", "rule_based", "frameworks"],
        template="""
You are Vivora, an expert code reviewer and academic project evaluator.

A student needs honest feedback on their project's weak areas before their viva.

Project Profile:
{profile}

Automated checks already found:
{rule_based}

Repository Files:
{repo_content}

Tech Stack: {frameworks}

Now do a DEEP analysis of the actual code and content quality.
Look for issues that automated checks miss.

Generate a structured weak area report with this EXACT format:

## 🔍 Automated Checks
[List what the automated checks found above, formatted nicely]

## 🤖 AI Code Analysis

### Code Quality Issues
[List specific issues found in the actual code — mention file names]
Examples to look for:
- No comments or docstrings in functions
- No error handling (try/except blocks missing)
- Hardcoded values that should be constants or configs
- Very long functions that should be broken up
- No input validation

### Documentation Issues
[Issues with README quality, comments, or docs]
Examples:
- README exists but is too brief
- No explanation of how to run the project
- No explanation of what the project does

### Project Structure Issues
[Issues with how the project is organized]
Examples:
- Everything in one file
- No separation of concerns
- No config file

### Security Issues
[Any obvious security concerns]
Examples:
- Hardcoded credentials
- No environment variables for secrets
- SQL injection risks

## 💡 Top 5 Improvements Before Viva
[List the 5 most important things to fix or prepare to explain]

## 🎤 How to Answer Weak Area Questions in Viva
[Give the student 2-3 sentences they can say if asked about these weaknesses]
Example format: "While the project currently lacks X, I am aware of this limitation.
In future work, I would address this by..."

IMPORTANT:
- Be specific — mention actual file names and line-level issues
- Be honest but constructive
- Focus on what matters most for a student viva
- Do not make up issues that don't exist in the code
"""
    )

    formatted_prompt = prompt_template.format(
        repo_content=repo_content,
        profile=profile,
        rule_based=rule_based_text,
        frameworks=", ".join(tech_stack["frameworks"]) or "Not detected"
    )

    response = llm.invoke(formatted_prompt)
    return response.content


# ─────────────────────────────────────────────
# FUNCTION: Project Report Generator (section-by-section)
# ─────────────────────────────────────────────

def generate_report_section(
    section_name: str,
    instruction: str,
    context: str,
    profile: str,
) -> str:
    """Generate one focused section of the academic report."""
    prompt_template = PromptTemplate(
        input_variables=["section_name", "instruction", "context", "profile"],
        template="""
You are Vivora, an expert academic report writer.

You are writing the "{section_name}" section of a university project report.

Project Profile:
{profile}

Relevant project content:
{context}

Your task:
{instruction}

Rules:
- Write in formal academic language (third person; avoid "we"/"I").
- Be specific — use actual project details, file names, tools, and features.
- Do not write generic content that could apply to any project.
- Length: 150-250 words.
- Do not include the section heading — just the body content.
- Use short paragraphs. Use markdown bullet lists (- item) when listing.
- Use **bold** sparingly for key terms only.
- Base everything on the project content above.
"""
    )

    formatted_prompt = prompt_template.format(
        section_name=section_name,
        instruction=instruction,
        context=context,
        profile=profile,
    )
    response = llm.invoke(formatted_prompt)
    return response.content.strip()


def _extract_project_name(profile: str) -> str:
    """Best-effort extraction of the project name from the profile text."""
    import re
    for line in profile.split("\n"):
        stripped = line.strip()
        m = re.search(r"project\s*name[:\s\-]+(.+)", stripped, re.IGNORECASE)
        if m:
            candidate = m.group(1).strip().strip("*").strip()
            if candidate and "guess" not in candidate.lower() and len(candidate) < 80:
                return candidate
    return "Project Report"


def generate_full_report(
    files: list,
    tech_stack: dict,
    profile: str,
    weak_areas: str = "",
    progress_callback=None,
    persist_dir: str | None = None,
) -> dict:
    """
    Generate the full academic report section-by-section.

    progress_callback(done:int, total:int, current_name:str) is called
    before each section starts and once more when complete.
    """
    from rag_engine import retrieve_context

    intro_context   = retrieve_context("project purpose goals objectives overview", persist_dir=persist_dir)
    tech_context    = retrieve_context("libraries frameworks tools dependencies requirements", persist_dir=persist_dir)
    impl_context    = retrieve_context("implementation code functions classes modules", persist_dir=persist_dir)
    arch_context    = retrieve_context("system architecture flow structure design", persist_dir=persist_dir)
    results_context = retrieve_context("output results features functionality", persist_dir=persist_dir)
    full_context    = get_key_files_content(files, max_chars=8000)

    sections_spec = [
        ("Abstract",
         "Write a concise abstract summarizing the entire project in one paragraph. Cover what it does, why it was built, how it works at a high level, and the main outcome.",
         full_context),
        ("Introduction",
         "Write an introduction explaining the project background: the domain, why this problem matters, what motivated the project, and a brief overview of what the report covers.",
         intro_context),
        ("Problem Statement",
         "Write a clear problem statement: the specific problem this project solves, the current situation without this solution, and who is affected.",
         intro_context),
        ("Objectives",
         "List 4-6 main objectives as a bullet list. Each should start with an action verb such as 'To develop', 'To implement', 'To design', 'To evaluate'.",
         intro_context),
        ("Tools and Technologies",
         "Describe all tools, languages, frameworks, and libraries used. For each: what it is, why it was chosen, and what role it plays. Mention versions if visible.",
         tech_context),
        ("System Architecture",
         "Describe the overall system architecture: how components connect, the flow of data, what each major module does, and how files are organized.",
         arch_context),
        ("Implementation Details",
         "Describe the key implementation details: the most important functions, classes, or modules. Mention specific file names and what they do.",
         impl_context),
        ("Results and Expected Output",
         "Describe what the project produces: what the user sees, the expected results, how the system behaves under normal conditions, and what success looks like.",
         results_context),
        ("Limitations",
         f"Describe the project's current limitations honestly. Reference this weak-area analysis: {weak_areas[:500] if weak_areas else 'Not available'}. Also mention scalability, performance, or feature gaps.",
         full_context),
        ("Future Enhancements",
         "Suggest 4-6 realistic future improvements as a bullet list. These should be practical additions that build on the existing codebase.",
         full_context),
        ("Conclusion",
         "Write a conclusion: what was built, whether objectives were achieved, what was learned, and the overall significance of the work.",
         full_context),
    ]

    project_name = _extract_project_name(profile)
    report_sections: dict[str, str] = {}
    combined_markdown = f"# {project_name}\n\n**Generated by Vivora**\n\n---\n\n"

    total = len(sections_spec)
    for index, (name, instruction, context) in enumerate(sections_spec, start=1):
        if progress_callback:
            progress_callback(index - 1, total, name)
        content = generate_report_section(name, instruction, context, profile)
        report_sections[name] = content
        combined_markdown += f"## {name}\n\n{content}\n\n---\n\n"

    if progress_callback:
        progress_callback(total, total, "Done")

    return {
        "project_name": project_name,
        "sections": report_sections,
        "markdown": combined_markdown,
    }


# ─────────────────────────────────────────────
# FUNCTION: Presentation Slide Content (JSON)
# ─────────────────────────────────────────────

def generate_slide_content(
    files: list,
    tech_stack: dict,
    profile: str,
    report: dict | None = None,
) -> list:
    """Ask the LLM for slide content as a JSON array of {title, bullets, notes}."""
    repo_content = get_key_files_content(files, max_chars=6000)

    report_summary = ""
    if report and "sections" in report:
        for section_name, content in list(report["sections"].items())[:6]:
            report_summary += f"\n{section_name}:\n{content[:300]}\n"

    prompt_template = PromptTemplate(
        input_variables=["repo_content", "profile", "frameworks", "report_summary"],
        template="""
You are Vivora creating a university project presentation.

Project Profile:
{profile}

Tech Stack: {frameworks}

Project Report Summary:
{report_summary}

Repository Files:
{repo_content}

Generate exactly 12 presentation slides as a JSON array.
Each slide must have: title (string), bullets (4-5 descriptive strings), notes (2-3 sentences).

Slide order:
1.  Title Slide              — project name + one-line tagline as the first bullet
2.  Project Overview
3.  Problem Statement
4.  Objectives
5.  Proposed Solution
6.  Tools and Technologies
7.  System Architecture
8.  Implementation Details
9.  Key Features
10. Results and Output
11. Limitations and Future Work
12. Conclusion

Return ONLY the raw JSON array. No prose, no markdown fences, no commentary.

Example shape:
[
  {{
    "title": "Slide Title",
    "bullets": ["short point one", "short point two", "short point three"],
    "notes": "What to say while presenting this slide."
  }}
]

RULES:
- Every bullet MUST be a complete descriptive phrase of 8-16 words.
- NEVER write label-style bullets like "Python project" or "Feedparser lib" — they convey nothing.
- Each bullet must say WHAT something does or WHY it matters, not just name it.
- Mention real file names, library names, and features from THIS project.
- Speaker notes: 2-3 plain sentences expanding on the bullets.
- Return ONLY the JSON array — start with [ and end with ].

GOOD vs BAD bullet examples (follow the GOOD style):
  BAD:  "Python project"
  GOOD: "Built in Python 3 using a modular four-module architecture"

  BAD:  "Feedparser lib"
  GOOD: "Uses feedparser to fetch and normalize RSS/Atom feed entries"

  BAD:  "HTML2text"
  GOOD: "Converts scraped HTML article bodies to clean text via html2text"

  BAD:  "Streamlit UI"
  GOOD: "Streamlit front-end renders results with reactive widgets and download buttons"
"""
    )

    formatted_prompt = prompt_template.format(
        repo_content=repo_content,
        profile=profile,
        frameworks=", ".join(tech_stack["frameworks"]) or "Not detected",
        report_summary=report_summary or "Not available",
    )

    response = llm.invoke(formatted_prompt)
    raw = response.content.strip()

    import json, re
    # Strip optional ```json fences the model sometimes adds
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw).strip()
    # If model leaked text before/after JSON, slice between first [ and last ]
    if not raw.startswith("["):
        start = raw.find("[")
        end = raw.rfind("]")
        if start != -1 and end != -1 and end > start:
            raw = raw[start:end + 1]

    try:
        slides = json.loads(raw)
        if not isinstance(slides, list) or not slides:
            raise ValueError("Response was not a non-empty JSON array.")
        return slides
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Slide JSON parse error: {e}")
        print(f"Raw response (first 500 chars): {raw[:500]}")
        return [{"title": "Error generating slides", "bullets": ["Please try again."], "notes": ""}]
