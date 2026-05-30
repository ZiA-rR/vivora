import os
import shutil
import git
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

# File types we WANT to read
# These are text-based files that contain actual project code and docs
ALLOWED_EXTENSIONS = {
    '.py',    # Python source code
    '.md',    # README and documentation
    '.txt',   # Plain text files
    '.json',  # Config and data files
    '.yaml',  # Config files
    '.yml',   # Config files
    '.toml',  # Config files like pyproject.toml
    '.rst',   # Documentation files
    '.js',    # JavaScript files
    '.html',  # Web pages
    '.css',   # Stylesheets
}

# Folders we want to completely SKIP
# These contain installed packages, cache, or secrets — not actual project code
IGNORED_FOLDERS = {
    '.git',
    'venv', 'env', '.venv',
    'node_modules',
    '__pycache__',
    '.idea', '.vscode',
    'dist', 'build',
    'migrations',
    '.pytest_cache',
}

# Safety limits so huge repos don't crash your app
MAX_FILES = 80          # maximum number of files to read
MAX_FILE_SIZE_KB = 200  # skip files larger than this


# ─────────────────────────────────────────────
# FUNCTION 1: Clone the repo
# ─────────────────────────────────────────────

def clone_repo(github_url: str, clone_dir: str = "L:/dev-cache/cloned_repo") -> str:
    """
    Takes a public GitHub URL and downloads the entire repo
    to a local folder on your computer.

    If a previous clone already exists, it deletes it first
    so you always get a fresh copy.

    Returns the path to the cloned folder.
    """
    import stat

    # This function is called by shutil.rmtree when it hits a read-only file
    # It removes the read-only protection then retries the delete
    def remove_readonly(func, path, _):
        os.chmod(path, stat.S_IWRITE)
        func(path)

    if os.path.exists(clone_dir):
        shutil.rmtree(clone_dir, onerror=remove_readonly)

    print(f"Cloning: {github_url}")
    git.Repo.clone_from(github_url, clone_dir)
    print("Clone complete.")

    return clone_dir

# ─────────────────────────────────────────────
# FUNCTION 2: Read useful files from the repo
# ─────────────────────────────────────────────

def get_useful_files(repo_path: str) -> list:
    """
    Walks through every folder in the cloned repo.
    Returns only the files we care about with their content.

    Each item in the returned list is a dictionary:
    {
        "file_name": "app.py",
        "relative_path": "src/app.py",
        "content": "import streamlit as st ..."
    }
    """
    useful_files = []

    for root, dirs, files in os.walk(repo_path):

        # Remove ignored folders from the search
        # dirs[:] modifies the list IN PLACE so os.walk skips those folders entirely
        dirs[:] = [d for d in dirs if d not in IGNORED_FOLDERS]

        for file in files:

            # Stop if we've already collected enough files
            if len(useful_files) >= MAX_FILES:
                break

            extension = os.path.splitext(file)[1].lower()

            # Only process allowed file types
            if extension not in ALLOWED_EXTENSIONS:
                continue

            full_path = os.path.join(root, file)
            relative_path = os.path.relpath(full_path, repo_path)

            # Skip files that are too large
            file_size_kb = os.path.getsize(full_path) / 1024
            if file_size_kb > MAX_FILE_SIZE_KB:
                print(f"Skipping large file: {relative_path} ({file_size_kb:.1f} KB)")
                continue

            try:
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # Skip empty files — nothing useful in them
                if not content.strip():
                    continue

                useful_files.append({
                    "file_name": file,
                    "relative_path": relative_path,
                    "content": content
                })

            except Exception as e:
                print(f"Could not read {file}: {e}")

    return useful_files

def detect_tech_stack(files: list) -> dict:
    """
    Looks at the file names and content to figure out
    what technologies the project uses.
    Returns a dictionary like:
    {
        "languages": ["Python"],
        "frameworks": ["Streamlit", "FastAPI"],
        "databases": ["SQLite"],
        "has_readme": True,
        "has_requirements": True,
        "has_tests": False
    }
    """

    languages = set()
    frameworks = set()
    databases = set()
    framework_keywords = {
        "streamlit": "Streamlit",
        "fastapi": "FastAPI",
        "flask": "Flask",
        "django": "Django",
        "react": "React",
        "express": "Express",
        "tensorflow": "TensorFlow",
        "torch": "PyTorch",
        "sklearn": "Scikit-learn",
        "pandas": "Pandas",
        "numpy": "NumPy",
        "opencv": "OpenCV",
        "langchain": "LangChain",
    }

    database_keywords = {
        "sqlite": "SQLite",
        "mysql": "MySQL",
        "postgresql": "PostgreSQL",
        "mongodb": "MongoDB",
        "firebase": "Firebase",
        "supabase": "Supabase",
        "chromadb": "ChromaDB",
    }

    has_readme = False
    has_requirements = False
    has_tests = False

    for file in files:
        name = file["file_name"].lower()
        content_lower = file["content"].lower()

        if name.endswith('.py'):
            languages.add("Python")
        elif name.endswith('.js'):
            languages.add("JavaScript")
        elif name.endswith('.html'):
            languages.add("HTML")
        elif name.endswith('.css'):
            languages.add("CSS")

        if name == "readme.md" or name == "readme.txt":
            has_readme = True
        if name in ("requirements.txt", "pyproject.toml", "package.json"):
            has_requirements = True
        if "test" in name:
            has_tests = True

        for keyword, framework_name in framework_keywords.items():
            if keyword in content_lower:
                frameworks.add(framework_name)
        
        for keyword, db_name in database_keywords.items():
            if keyword in content_lower:
                databases.add(db_name)

    return {
        "languages": sorted(list(languages)),
        "frameworks": sorted(list(frameworks)),
        "databases": sorted(list(databases)),
        "has_readme": has_readme,
        "has_requirements": has_requirements,
        "has_tests": has_tests,
    }