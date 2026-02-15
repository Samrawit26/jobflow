"""
Unit tests for xlsx_kv_reader.py

Tests XLSX key-value pair reading with stdlib only.
"""

from pathlib import Path

import pytest

from jobflow.app.core.xlsx_kv_reader import read_xlsx_key_value_pairs


def test_read_xlsx_anusha_fixture():
    """Test reading Anusha's application_info.xlsx fixture."""
    fixture_path = Path(__file__).parent.parent / "fixtures" / "candidates" / "anusha" / "application_info.xlsx"

    result = read_xlsx_key_value_pairs(str(fixture_path))

    # Verify expected fields
    assert "Full Name" in result
    assert result["Full Name"] == "Anusha Kayam"

    assert "Email" in result
    assert result["Email"] == "anusha@example.com"

    assert "Phone" in result
    assert result["Phone"] == "555-123-4567"

    assert "Location" in result
    assert result["Location"] == "Remote"

    assert "Desired Titles" in result
    assert result["Desired Titles"] == "Power BI Developer; Data Analyst"

    assert "Skills" in result
    assert result["Skills"] == "Power BI, SQL, DAX, Excel, Azure"

    assert "Years of Experience" in result
    assert result["Years of Experience"] == "4"

    assert "Sponsorship Needed" in result
    assert result["Sponsorship Needed"] == "No"


def test_read_xlsx_missing_file():
    """Test that missing file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        read_xlsx_key_value_pairs("nonexistent.xlsx")


def test_read_xlsx_invalid_file(tmp_path):
    """Test that invalid XLSX raises ValueError."""
    invalid_file = tmp_path / "invalid.xlsx"
    invalid_file.write_text("not an xlsx file")

    with pytest.raises(ValueError, match="Invalid XLSX"):
        read_xlsx_key_value_pairs(str(invalid_file))


def test_read_xlsx_missing_sheet():
    """Test that requesting non-existent sheet raises ValueError."""
    fixture_path = Path(__file__).parent.parent / "fixtures" / "candidates" / "anusha" / "application_info.xlsx"

    with pytest.raises(ValueError, match="Sheet .* not found"):
        read_xlsx_key_value_pairs(str(fixture_path), sheet_index=99)


def test_read_xlsx_returns_dict():
    """Test that result is a dict."""
    fixture_path = Path(__file__).parent.parent / "fixtures" / "candidates" / "anusha" / "application_info.xlsx"

    result = read_xlsx_key_value_pairs(str(fixture_path))

    assert isinstance(result, dict)
    assert len(result) > 0


def test_read_xlsx_all_values_are_strings():
    """Test that all values are returned as strings."""
    fixture_path = Path(__file__).parent.parent / "fixtures" / "candidates" / "anusha" / "application_info.xlsx"

    result = read_xlsx_key_value_pairs(str(fixture_path))

    for key, value in result.items():
        assert isinstance(key, str)
        assert isinstance(value, str)


def test_read_xlsx_preserves_order():
    """Test that key-value pairs maintain order."""
    fixture_path = Path(__file__).parent.parent / "fixtures" / "candidates" / "anusha" / "application_info.xlsx"

    result = read_xlsx_key_value_pairs(str(fixture_path))

    keys = list(result.keys())

    # Full Name should be first
    assert keys[0] == "Full Name"

    # Email should be second
    assert keys[1] == "Email"
