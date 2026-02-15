"""
Unit tests for candidate_folder_loader.py

Tests loading candidate profiles from folders.
"""

from pathlib import Path

import pytest

from jobflow.app.core.candidate_folder_loader import load_candidate_profile


def test_load_candidate_profile_anusha_fixture():
    """Test loading Anusha's candidate folder fixture."""
    fixture_path = Path(__file__).parent.parent / "fixtures" / "candidates" / "anusha"

    profile = load_candidate_profile(str(fixture_path))

    # Verify basic fields from application
    assert profile.full_name == "Anusha Kayam"
    assert profile.email == "anusha@example.com"
    assert profile.phone == "555-123-4567"
    assert profile.location == "Remote"

    # Verify desired titles parsed correctly
    assert len(profile.desired_titles) == 2
    assert "Power BI Developer" in profile.desired_titles
    assert "Data Analyst" in profile.desired_titles

    # Verify skills merged from application + resume
    assert len(profile.skills) > 0
    # Application skills
    assert any("power bi" in s.lower() or "powerbi" in s.lower() for s in profile.skills)
    assert any("sql" in s.lower() for s in profile.skills)
    assert any("dax" in s.lower() for s in profile.skills)

    # Verify years of experience
    assert profile.years_experience == 4.0

    # Verify sponsorship needed
    assert profile.sponsorship_needed is False

    # Verify remote preference
    assert profile.remote_ok is True  # Location is "Remote"

    # Verify resume text is present
    assert len(profile.resume_text) > 0
    assert "ANUSHA KAYAM" in profile.resume_text or "Anusha Kayam" in profile.resume_text


def test_load_candidate_profile_skills_merged():
    """Test that skills from application and resume are merged."""
    fixture_path = Path(__file__).parent.parent / "fixtures" / "candidates" / "anusha"

    profile = load_candidate_profile(str(fixture_path))

    # Application has: Power BI, SQL, DAX, Excel, Azure
    # Resume has many more: Tableau, Python, ETL, etc.

    # Should have application skills
    skills_lower = [s.lower() for s in profile.skills]

    # Check for resume-only skills (not in application)
    assert any("tableau" in s or "etl" in s or "python" in s for s in skills_lower)


def test_load_candidate_profile_skills_deduplicated():
    """Test that duplicate skills are removed."""
    fixture_path = Path(__file__).parent.parent / "fixtures" / "candidates" / "anusha"

    profile = load_candidate_profile(str(fixture_path))

    # Count occurrences of each skill (case-insensitive)
    skills_lower = [s.lower() for s in profile.skills]

    # No duplicates
    assert len(skills_lower) == len(set(skills_lower))


def test_load_candidate_profile_raw_metadata():
    """Test that raw metadata is included."""
    fixture_path = Path(__file__).parent.parent / "fixtures" / "candidates" / "anusha"

    profile = load_candidate_profile(str(fixture_path))

    assert "application_fields" in profile.raw
    assert "resume_path" in profile.raw
    assert "resume_text_excerpt" in profile.raw

    # Verify application fields preserved
    assert isinstance(profile.raw["application_fields"], dict)
    assert "Full Name" in profile.raw["application_fields"]

    # Verify resume path is a string
    assert isinstance(profile.raw["resume_path"], str)

    # Verify excerpt is truncated
    assert len(profile.raw["resume_text_excerpt"]) <= 500


def test_load_candidate_profile_missing_folder():
    """Test that missing folder raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError, match="Candidate folder not found"):
        load_candidate_profile("nonexistent_folder")


def test_load_candidate_profile_missing_xlsx(tmp_path):
    """Test that missing XLSX raises FileNotFoundError."""
    # Create folder with only resume
    candidate_folder = tmp_path / "candidate"
    candidate_folder.mkdir()

    resume_file = candidate_folder / "resume.txt"
    resume_file.write_text("Some resume text")

    with pytest.raises(FileNotFoundError, match="No .xlsx application file found"):
        load_candidate_profile(str(candidate_folder))


def test_load_candidate_profile_missing_resume(tmp_path):
    """Test that missing resume raises FileNotFoundError."""
    # Create folder with only XLSX
    candidate_folder = tmp_path / "candidate"
    candidate_folder.mkdir()

    # Copy fixture XLSX
    from scripts.generate_xlsx_fixture import generate_application_xlsx

    xlsx_path = candidate_folder / "application.xlsx"
    generate_application_xlsx(str(xlsx_path), {"Name": "Test"})

    with pytest.raises(FileNotFoundError, match="No resume file found"):
        load_candidate_profile(str(candidate_folder))


def test_load_candidate_profile_doc_resume_not_found(tmp_path):
    """Test that .doc resume is not recognized (raises FileNotFoundError)."""
    # Create folder with XLSX and .doc resume
    candidate_folder = tmp_path / "candidate"
    candidate_folder.mkdir()

    # Create XLSX
    from scripts.generate_xlsx_fixture import generate_application_xlsx

    xlsx_path = candidate_folder / "application.xlsx"
    generate_application_xlsx(str(xlsx_path), {"Name": "Test", "Email": "test@example.com", "Phone": "555-0000", "Location": "NYC"})

    # Create .doc file
    doc_file = candidate_folder / "resume.doc"
    doc_file.write_text("fake doc")

    # .doc files are not supported and not even looked for
    # Should raise FileNotFoundError (no supported resume found)
    with pytest.raises(FileNotFoundError, match="No resume file found"):
        load_candidate_profile(str(candidate_folder))


def test_load_candidate_profile_prefers_application_in_name(tmp_path):
    """Test that XLSX with 'application' in name is preferred."""
    candidate_folder = tmp_path / "candidate"
    candidate_folder.mkdir()

    # Create two XLSX files
    from scripts.generate_xlsx_fixture import generate_application_xlsx

    # First file (no "application" in name)
    xlsx1 = candidate_folder / "info.xlsx"
    generate_application_xlsx(str(xlsx1), {"Name": "Wrong"})

    # Second file (has "application" in name)
    xlsx2 = candidate_folder / "application_info.xlsx"
    generate_application_xlsx(str(xlsx2), {"Name": "Correct", "Email": "test@example.com", "Phone": "555-0000", "Location": "NYC"})

    # Create resume
    resume = candidate_folder / "resume.txt"
    resume.write_text("Test resume")

    profile = load_candidate_profile(str(candidate_folder))

    # Should use the "application" file
    assert profile.full_name == "Correct"


def test_load_candidate_profile_prefers_docx_resume(tmp_path):
    """Test that .docx resume is preferred over .txt."""
    import zipfile

    candidate_folder = tmp_path / "candidate"
    candidate_folder.mkdir()

    # Create XLSX
    from scripts.generate_xlsx_fixture import generate_application_xlsx

    xlsx_path = candidate_folder / "application.xlsx"
    generate_application_xlsx(str(xlsx_path), {"Name": "Test", "Email": "test@example.com", "Phone": "555-0000", "Location": "NYC"})

    # Create .txt resume
    txt_resume = candidate_folder / "resume.txt"
    txt_resume.write_text("TXT resume")

    # Create .docx resume
    docx_resume = candidate_folder / "resume.docx"
    document_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>DOCX resume content</w:t></w:r></w:p>
  </w:body>
</w:document>"""
    with zipfile.ZipFile(docx_resume, "w") as docx:
        docx.writestr("word/document.xml", document_xml)

    profile = load_candidate_profile(str(candidate_folder))

    # Should use DOCX
    assert "DOCX resume content" in profile.resume_text


def test_load_candidate_profile_returns_candidate_profile():
    """Test that result is CandidateProfile instance."""
    from jobflow.app.core.candidate_profile import CandidateProfile

    fixture_path = Path(__file__).parent.parent / "fixtures" / "candidates" / "anusha"

    profile = load_candidate_profile(str(fixture_path))

    assert isinstance(profile, CandidateProfile)


def test_load_candidate_profile_handles_missing_optional_fields(tmp_path):
    """Test loading with minimal application fields."""
    from scripts.generate_xlsx_fixture import generate_application_xlsx

    candidate_folder = tmp_path / "candidate"
    candidate_folder.mkdir()

    # Create minimal XLSX
    xlsx_path = candidate_folder / "application.xlsx"
    generate_application_xlsx(
        str(xlsx_path),
        {
            "Name": "Test User",
            "Email": "test@example.com",
            "Phone": "555-0000",
            "Location": "NYC",
        }
    )

    # Create resume
    resume = candidate_folder / "resume.txt"
    resume.write_text("Basic resume with Python and SQL")

    profile = load_candidate_profile(str(candidate_folder))

    # Should have basic fields
    assert profile.full_name == "Test User"
    assert profile.email == "test@example.com"

    # Optional fields should have defaults
    assert profile.desired_titles == []
    assert profile.years_experience is None
    assert profile.sponsorship_needed is None
