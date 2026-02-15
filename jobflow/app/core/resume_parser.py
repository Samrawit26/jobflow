"""
Resume parser with stdlib-only text extraction.

Extracts text and skills from resume files (.txt, .md, .docx).
"""

import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


# Built-in skill keywords for deterministic extraction
SKILL_KEYWORDS = {
    "python", "java", "javascript", "typescript", "c++", "c#", "ruby", "go", "rust",
    "sql", "nosql", "postgresql", "mysql", "mongodb", "redis", "cassandra",
    "aws", "azure", "gcp", "cloud", "docker", "kubernetes", "terraform",
    "power bi", "powerbi", "tableau", "looker", "qlik", "excel", "vba",
    "spark", "hadoop", "kafka", "airflow", "dbt", "snowflake", "redshift", "bigquery",
    "etl", "elt", "data warehouse", "data lake", "data pipeline",
    "fastapi", "django", "flask", "spring", "react", "angular", "vue", "node.js", "nodejs",
    "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch", "keras",
    "git", "github", "gitlab", "bitbucket", "jira", "confluence",
    "rest api", "graphql", "microservices", "api", "ci/cd", "devops",
    "machine learning", "ml", "ai", "deep learning", "nlp", "computer vision",
    "data science", "data analysis", "analytics", "bi", "business intelligence",
    "agile", "scrum", "kanban", "sdlc", "tdd", "bdd",
    "html", "css", "sass", "less", "bootstrap", "tailwind",
    "linux", "unix", "bash", "shell", "powershell",
    "dax", "mdx", "ssrs", "ssis", "ssas", "power query",
}


def extract_text_from_resume(path: str) -> str:
    """
    Extract text from resume file.

    Supports .txt, .md, .docx formats. .doc is NOT supported.

    Args:
        path: Path to resume file

    Returns:
        Extracted text as string

    Raises:
        ValueError: If file format is .doc or unsupported
        FileNotFoundError: If file doesn't exist
    """
    path_obj = Path(path)

    if not path_obj.exists():
        raise FileNotFoundError(f"Resume file not found: {path}")

    suffix = path_obj.suffix.lower()

    # .doc is explicitly not supported
    if suffix == ".doc":
        raise ValueError(
            "Legacy .doc format is not supported. "
            "Please convert to .docx or .txt format."
        )

    # Handle .txt and .md
    if suffix in {".txt", ".md"}:
        return _read_text_file(path)

    # Handle .docx
    if suffix == ".docx":
        return _extract_text_from_docx(path)

    # Unsupported format
    raise ValueError(
        f"Unsupported resume format: {suffix}. "
        f"Supported formats: .txt, .md, .docx"
    )


def _read_text_file(path: str) -> str:
    """Read text file with UTF-8 encoding, ignoring errors."""
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def _extract_text_from_docx(path: str) -> str:
    """
    Extract text from .docx file using stdlib only.

    .docx is a ZIP archive containing XML files. This extracts text
    from word/document.xml.

    Args:
        path: Path to .docx file

    Returns:
        Extracted text with paragraphs separated by newlines
    """
    try:
        with zipfile.ZipFile(path, "r") as docx_zip:
            # Read the main document XML
            try:
                xml_content = docx_zip.read("word/document.xml")
            except KeyError:
                # Some docx files might have different structure
                return ""

            # Parse XML
            root = ET.fromstring(xml_content)

            # Define namespace
            namespaces = {
                "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
            }

            # Extract text from all text nodes
            paragraphs = []
            for paragraph in root.findall(".//w:p", namespaces):
                texts = []
                for text_node in paragraph.findall(".//w:t", namespaces):
                    if text_node.text:
                        texts.append(text_node.text)
                if texts:
                    paragraphs.append("".join(texts))

            return "\n".join(paragraphs)

    except zipfile.BadZipFile:
        raise ValueError(f"Invalid .docx file: {path}")
    except ET.ParseError:
        raise ValueError(f"Cannot parse .docx XML: {path}")


def extract_skills_from_text(text: str) -> list[str]:
    """
    Extract skills from text using deterministic keyword matching.

    Uses built-in SKILL_KEYWORDS set plus pattern matching for:
    - Technical acronyms (2-5 uppercase letters)
    - Capitalized tech terms

    Args:
        text: Resume or description text

    Returns:
        List of extracted skills (lowercase, deduplicated, stable order)
    """
    if not text:
        return []

    text_lower = text.lower()
    found_skills = []
    seen = set()

    # 1. Match known skill keywords (case-insensitive, whole words)
    for skill in SKILL_KEYWORDS:
        # Use word boundaries for single-word skills
        if " " not in skill:
            pattern = rf"\b{re.escape(skill)}\b"
        else:
            # Multi-word skills need more careful matching
            pattern = re.escape(skill)

        if re.search(pattern, text_lower):
            if skill not in seen:
                found_skills.append(skill)
                seen.add(skill)

    # 2. Extract acronyms (2-5 uppercase letters)
    acronyms = re.findall(r"\b[A-Z]{2,5}\b", text)
    for acronym in acronyms:
        acronym_lower = acronym.lower()
        if acronym_lower not in seen:
            found_skills.append(acronym_lower)
            seen.add(acronym_lower)

    # 3. Extract capitalized tech terms (CamelCase or standalone)
    # Match words like "PowerBI", "Node.js", "C#", etc.
    tech_terms = re.findall(r"\b[A-Z][a-z]*(?:[A-Z][a-z]*)*(?:[.#][a-z]+)?\b", text)
    for term in tech_terms:
        # Skip common words
        if term.lower() in {"the", "a", "an", "and", "or", "but", "in", "on", "at"}:
            continue
        # Only include if 2+ chars
        if len(term) >= 2:
            term_lower = term.lower()
            if term_lower not in seen:
                found_skills.append(term_lower)
                seen.add(term_lower)

    return found_skills
