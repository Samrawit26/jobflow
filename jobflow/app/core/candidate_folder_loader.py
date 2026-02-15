"""
Candidate folder loader.

Loads candidate profile from a folder containing application info and resume.
"""

import re
from pathlib import Path

from jobflow.app.core.candidate_profile import CandidateProfile
from jobflow.app.core.resume_parser import extract_text_from_resume, extract_skills_from_text
from jobflow.app.core.xlsx_kv_reader import read_xlsx_key_value_pairs


def load_candidate_profile(folder_path: str) -> CandidateProfile:
    """
    Load candidate profile from folder.

    Expects folder to contain:
    - One .xlsx file with application info (key-value pairs)
    - One resume file (.txt, .md, or .docx)

    Args:
        folder_path: Path to candidate folder

    Returns:
        CandidateProfile instance

    Raises:
        FileNotFoundError: If folder, xlsx, or resume not found
        ValueError: If resume format is unsupported
    """
    folder = Path(folder_path)

    if not folder.exists() or not folder.is_dir():
        raise FileNotFoundError(f"Candidate folder not found: {folder_path}")

    # Find application info XLSX
    xlsx_file = _find_application_xlsx(folder)
    if xlsx_file is None:
        raise FileNotFoundError(f"No .xlsx application file found in {folder_path}")

    # Find resume file
    resume_file = _find_resume_file(folder)
    if resume_file is None:
        raise FileNotFoundError(f"No resume file found in {folder_path}")

    # Load application key-value pairs
    application_fields = read_xlsx_key_value_pairs(str(xlsx_file))

    # Extract resume text and skills
    resume_text = extract_text_from_resume(str(resume_file))
    resume_skills = extract_skills_from_text(resume_text)

    # Merge into candidate profile
    profile_dict = _build_profile_dict(application_fields, resume_text, resume_skills)

    # Add metadata that will be included in raw by from_dict
    # from_dict will copy profile_dict to raw field
    profile_dict["application_fields"] = application_fields
    profile_dict["resume_path"] = str(resume_file)
    profile_dict["resume_text_excerpt"] = resume_text[:500] if resume_text else ""

    return CandidateProfile.from_dict(profile_dict)


def _find_application_xlsx(folder: Path) -> Path | None:
    """
    Find application info XLSX file in folder.

    Prefers files with "application" in name, else returns first .xlsx.

    Args:
        folder: Folder Path

    Returns:
        Path to XLSX file, or None if not found
    """
    xlsx_files = list(folder.glob("*.xlsx"))

    if not xlsx_files:
        return None

    # Prefer files with "application" in name (case-insensitive)
    for xlsx_file in xlsx_files:
        if "application" in xlsx_file.name.lower():
            return xlsx_file

    # Otherwise return first
    return xlsx_files[0]


def _find_resume_file(folder: Path) -> Path | None:
    """
    Find resume file in folder.

    Prefers .docx, then .txt, then .md.

    Args:
        folder: Folder Path

    Returns:
        Path to resume file, or None if not found
    """
    # Try .docx first
    docx_files = list(folder.glob("*.docx"))
    if docx_files:
        return docx_files[0]

    # Try .txt
    txt_files = list(folder.glob("*.txt"))
    if txt_files:
        return txt_files[0]

    # Try .md
    md_files = list(folder.glob("*.md"))
    if md_files:
        return md_files[0]

    return None


def _build_profile_dict(
    application_fields: dict[str, str],
    resume_text: str,
    resume_skills: list[str]
) -> dict:
    """
    Build profile dict from application fields and resume data.

    Args:
        application_fields: Key-value pairs from application xlsx
        resume_text: Full resume text
        resume_skills: Skills extracted from resume

    Returns:
        Dict suitable for CandidateProfile.from_dict()
    """
    profile = {}

    # Basic fields from application (with flexible key names)
    profile["full_name"] = _get_field(
        application_fields, ["Full Name", "Name", "Candidate Name"]
    )
    profile["email"] = _get_field(
        application_fields, ["Email", "Email Address", "E-mail"]
    )
    profile["phone"] = _get_field(
        application_fields, ["Phone", "Phone Number", "Mobile", "Contact"]
    )
    profile["location"] = _get_field(
        application_fields, ["Location", "City", "State", "Address"]
    )

    # Desired titles - split by semicolons, commas, or newlines
    desired_titles_raw = _get_field(
        application_fields, ["Desired Titles", "Target Roles", "Job Titles", "Roles"]
    )
    profile["desired_titles"] = _split_list(desired_titles_raw)

    # Skills - from application + resume (merged and deduplicated)
    app_skills_raw = _get_field(
        application_fields, ["Skills", "Primary Skills", "Technical Skills"]
    )
    app_skills = _split_list(app_skills_raw)

    # Merge skills: application skills first, then resume skills
    all_skills = []
    seen_lower = set()

    for skill in app_skills:
        skill_lower = skill.lower()
        if skill_lower not in seen_lower:
            all_skills.append(skill)
            seen_lower.add(skill_lower)

    for skill in resume_skills:
        skill_lower = skill.lower()
        if skill_lower not in seen_lower:
            all_skills.append(skill)
            seen_lower.add(skill_lower)

    profile["skills"] = all_skills

    # Years of experience - parse to int/float
    years_exp_raw = _get_field(
        application_fields, ["Years of Experience", "Experience", "Years"]
    )
    profile["years_experience"] = _parse_years_experience(years_exp_raw)

    # Work authorization
    work_auth_raw = _get_field(
        application_fields, ["Work Authorization", "Visa Status", "Authorization"]
    )
    profile["work_authorization"] = work_auth_raw

    # Preferred locations
    pref_loc_raw = _get_field(
        application_fields,
        ["Preferred Locations", "Desired Locations", "Location Preference"]
    )
    profile["preferred_locations"] = _split_list(pref_loc_raw)

    # Remote preference - check if location or pref includes "remote"
    remote_raw = _get_field(
        application_fields, ["Remote", "Remote OK", "Remote Work", "Remote Preference"]
    )
    profile["remote_ok"] = _parse_remote_preference(
        remote_raw, profile.get("location", ""), profile.get("preferred_locations", [])
    )

    # Sponsorship needed
    sponsorship_raw = _get_field(
        application_fields,
        ["Sponsorship Needed", "Needs Sponsorship", "Visa Sponsorship", "Requires Sponsorship"]
    )
    profile["sponsorship_needed"] = _parse_bool(sponsorship_raw)

    # Resume text
    profile["resume_text"] = resume_text

    return profile


def _get_field(fields: dict[str, str], possible_keys: list[str]) -> str:
    """
    Get field value from dict using flexible key matching.

    Args:
        fields: Dict with field values
        possible_keys: List of possible key names (case-insensitive)

    Returns:
        Field value, or empty string if not found
    """
    # Create case-insensitive lookup
    fields_lower = {k.lower(): v for k, v in fields.items()}

    for key in possible_keys:
        key_lower = key.lower()
        if key_lower in fields_lower:
            return fields_lower[key_lower]

    return ""


def _split_list(value: str) -> list[str]:
    """
    Split string into list by semicolons, commas, or newlines.

    Args:
        value: String to split

    Returns:
        List of non-empty trimmed strings
    """
    if not value:
        return []

    # Split by semicolons, commas, or newlines
    items = re.split(r"[;,\n]+", value)

    # Strip and filter empty
    return [item.strip() for item in items if item.strip()]


def _parse_years_experience(value: str) -> float | None:
    """
    Parse years of experience to float.

    Args:
        value: String value

    Returns:
        Float value or None if invalid
    """
    if not value:
        return None

    # Try to extract number
    match = re.search(r"(\d+(?:\.\d+)?)", value)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass

    return None


def _parse_remote_preference(
    remote_field: str,
    location: str,
    preferred_locations: list[str]
) -> bool | None:
    """
    Parse remote preference from various sources.

    Args:
        remote_field: Direct remote field value
        location: Current location
        preferred_locations: List of preferred locations

    Returns:
        True if remote preferred, False if not, None if unknown
    """
    # Check direct remote field
    if remote_field:
        remote_lower = remote_field.lower()
        if remote_lower in {"yes", "true", "1", "remote"}:
            return True
        if remote_lower in {"no", "false", "0", "onsite", "on-site"}:
            return False

    # Check if "remote" appears in location or preferred locations
    all_locations = [location] + preferred_locations
    for loc in all_locations:
        if "remote" in loc.lower():
            return True

    return None


def _parse_bool(value: str) -> bool | None:
    """
    Parse boolean value from string.

    Args:
        value: String value

    Returns:
        True, False, or None if cannot determine
    """
    if not value:
        return None

    value_lower = value.lower()

    if value_lower in {"yes", "true", "1", "y"}:
        return True
    if value_lower in {"no", "false", "0", "n"}:
        return False

    return None
