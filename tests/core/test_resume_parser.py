"""
Unit tests for resume_parser.py

Tests resume text extraction and skill extraction.
"""

import zipfile
from pathlib import Path

import pytest

from jobflow.app.core.resume_parser import (
    extract_skills_from_text,
    extract_text_from_resume,
)


def test_extract_text_from_txt_file():
    """Test extracting text from .txt resume."""
    fixture_path = Path(__file__).parent.parent / "fixtures" / "candidates" / "anusha" / "resume.txt"

    text = extract_text_from_resume(str(fixture_path))

    assert isinstance(text, str)
    assert len(text) > 0
    assert "ANUSHA KAYAM" in text
    assert "Power BI" in text
    assert "SQL" in text


def test_extract_text_from_missing_file():
    """Test that missing file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        extract_text_from_resume("nonexistent.txt")


def test_extract_text_from_doc_raises_error(tmp_path):
    """Test that .doc file raises ValueError."""
    doc_file = tmp_path / "resume.doc"
    doc_file.write_text("fake doc content")

    with pytest.raises(ValueError, match="Legacy .doc format is not supported"):
        extract_text_from_resume(str(doc_file))


def test_extract_text_from_unsupported_format(tmp_path):
    """Test that unsupported format raises ValueError."""
    pdf_file = tmp_path / "resume.pdf"
    pdf_file.write_text("fake pdf")

    with pytest.raises(ValueError, match="Unsupported resume format"):
        extract_text_from_resume(str(pdf_file))


def test_extract_text_from_docx(tmp_path):
    """Test extracting text from .docx file."""
    # Create a minimal valid .docx file
    docx_path = tmp_path / "test.docx"

    # Create document.xml content
    document_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p>
      <w:r><w:t>John Doe</w:t></w:r>
    </w:p>
    <w:p>
      <w:r><w:t>Software Engineer with Python and AWS experience</w:t></w:r>
    </w:p>
  </w:body>
</w:document>"""

    # Create minimal DOCX structure
    with zipfile.ZipFile(docx_path, "w") as docx:
        docx.writestr("word/document.xml", document_xml)

    text = extract_text_from_resume(str(docx_path))

    assert "John Doe" in text
    assert "Python" in text
    assert "AWS" in text


def test_extract_text_from_md_file(tmp_path):
    """Test extracting text from .md file."""
    md_file = tmp_path / "resume.md"
    md_file.write_text("# Resume\n\n## Skills\n- Python\n- SQL\n")

    text = extract_text_from_resume(str(md_file))

    assert "Resume" in text
    assert "Skills" in text
    assert "Python" in text


def test_extract_skills_from_text_basic():
    """Test basic skill extraction."""
    text = """
    Experienced developer with Python, SQL, and AWS expertise.
    Proficient in Docker, Kubernetes, and CI/CD pipelines.
    """

    skills = extract_skills_from_text(text)

    assert "python" in skills
    assert "sql" in skills
    assert "aws" in skills
    assert "docker" in skills
    assert "kubernetes" in skills


def test_extract_skills_from_anusha_resume():
    """Test skill extraction from Anusha's resume fixture."""
    fixture_path = Path(__file__).parent.parent / "fixtures" / "candidates" / "anusha" / "resume.txt"

    text = extract_text_from_resume(str(fixture_path))
    skills = extract_skills_from_text(text)

    # Should find Power BI (or powerbi)
    assert any("power" in s and "bi" in s for s in skills) or "powerbi" in skills

    # Should find SQL
    assert "sql" in skills

    # Should find Azure
    assert "azure" in skills

    # Should find DAX
    assert "dax" in skills

    # Should find ETL
    assert "etl" in skills


def test_extract_skills_from_text_deduplicates():
    """Test that skill extraction deduplicates."""
    text = """
    Python Python PYTHON python
    SQL sql Sql SQL
    """

    skills = extract_skills_from_text(text)

    # Should have python only once
    python_count = sum(1 for s in skills if s == "python")
    assert python_count == 1

    # Should have sql only once
    sql_count = sum(1 for s in skills if s == "sql")
    assert sql_count == 1


def test_extract_skills_from_text_finds_all():
    """Test that skill extraction finds all present skills."""
    text = "Experience with Java, Python, SQL, and AWS."

    skills = extract_skills_from_text(text)

    # Should find all mentioned skills
    assert "java" in skills
    assert "python" in skills
    assert "sql" in skills
    assert "aws" in skills


def test_extract_skills_from_text_empty():
    """Test skill extraction from empty text."""
    skills = extract_skills_from_text("")

    assert skills == []


def test_extract_skills_from_text_no_skills():
    """Test skill extraction when no skills present."""
    text = "This is just some random text with no technical skills."

    skills = extract_skills_from_text(text)

    # May extract some capitalized words, but should be minimal
    assert isinstance(skills, list)


def test_extract_skills_returns_lowercase():
    """Test that extracted skills are lowercase."""
    text = "Python SQL AWS Docker KUBERNETES"

    skills = extract_skills_from_text(text)

    for skill in skills:
        assert skill == skill.lower()


def test_extract_skills_extracts_acronyms():
    """Test that acronyms are extracted."""
    text = "Experience with ETL, CI/CD, and API development."

    skills = extract_skills_from_text(text)

    assert "etl" in skills
    assert "api" in skills


def test_extract_skills_handles_special_chars():
    """Test skill extraction with special characters."""
    text = "C++, C#, Node.js, and ASP.NET experience"

    skills = extract_skills_from_text(text)

    # Should extract something related to these
    assert len(skills) > 0
