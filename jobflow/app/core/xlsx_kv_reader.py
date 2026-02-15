"""
XLSX key-value pair reader using stdlib only.

Reads key-value pairs from XLSX files (column A = key, column B = value).
"""

import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


def read_xlsx_key_value_pairs(path: str, sheet_index: int = 0) -> dict[str, str]:
    """
    Read key-value pairs from XLSX file.

    Expects:
    - Column A: keys (field names)
    - Column B: values (field values)

    Args:
        path: Path to .xlsx file
        sheet_index: Sheet index to read (default 0 = first sheet)

    Returns:
        Dict mapping keys to values (all as strings)

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file is not valid XLSX
    """
    path_obj = Path(path)

    if not path_obj.exists():
        raise FileNotFoundError(f"XLSX file not found: {path}")

    try:
        with zipfile.ZipFile(path, "r") as xlsx_zip:
            # Read shared strings (string pool)
            shared_strings = _read_shared_strings(xlsx_zip)

            # Read the sheet
            sheet_name = f"xl/worksheets/sheet{sheet_index + 1}.xml"
            try:
                sheet_xml = xlsx_zip.read(sheet_name)
            except KeyError:
                raise ValueError(f"Sheet {sheet_index} not found in XLSX")

            # Parse sheet XML and extract key-value pairs
            return _extract_key_value_pairs(sheet_xml, shared_strings)

    except zipfile.BadZipFile:
        raise ValueError(f"Invalid XLSX file: {path}")


def _read_shared_strings(xlsx_zip: zipfile.ZipFile) -> list[str]:
    """
    Read shared strings table from XLSX.

    Shared strings are stored in xl/sharedStrings.xml.

    Args:
        xlsx_zip: Open XLSX ZipFile

    Returns:
        List of strings indexed by their position
    """
    try:
        shared_strings_xml = xlsx_zip.read("xl/sharedStrings.xml")
    except KeyError:
        # No shared strings (all values are inline or numeric)
        return []

    try:
        root = ET.fromstring(shared_strings_xml)
    except ET.ParseError:
        return []

    # Namespace
    ns = {"": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

    strings = []
    for si in root.findall("si", ns):
        # Text can be in <t> or <r><t> (rich text)
        text_parts = []
        for t in si.findall(".//t", ns):
            if t.text:
                text_parts.append(t.text)
        strings.append("".join(text_parts))

    return strings


def _extract_key_value_pairs(
    sheet_xml: bytes, shared_strings: list[str]
) -> dict[str, str]:
    """
    Extract key-value pairs from sheet XML.

    Expects column A = keys, column B = values.

    Args:
        sheet_xml: Sheet XML content
        shared_strings: Shared strings lookup table

    Returns:
        Dict of key -> value pairs
    """
    try:
        root = ET.fromstring(sheet_xml)
    except ET.ParseError:
        return {}

    # Namespace
    ns = {"": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

    # Find all rows with data
    rows = root.findall(".//row", ns)

    key_value_pairs = {}

    for row in rows:
        cells = row.findall("c", ns)
        if len(cells) < 2:
            continue  # Need at least 2 cells

        # Get cells A and B
        cell_a = None
        cell_b = None

        for cell in cells:
            cell_ref = cell.get("r", "")
            col = _get_column_from_ref(cell_ref)

            if col == "A":
                cell_a = cell
            elif col == "B":
                cell_b = cell

        if cell_a is None or cell_b is None:
            continue

        # Extract key from column A
        key = _get_cell_value(cell_a, shared_strings, ns)
        if not key or not key.strip():
            continue

        # Extract value from column B
        value = _get_cell_value(cell_b, shared_strings, ns)

        key_value_pairs[key.strip()] = value

    return key_value_pairs


def _get_column_from_ref(cell_ref: str) -> str:
    """
    Extract column letter from cell reference.

    Examples:
        A1 -> A
        B10 -> B
        AA5 -> AA

    Args:
        cell_ref: Cell reference like "A1", "B2", etc.

    Returns:
        Column letter(s)
    """
    # Extract letters from the beginning
    match = re.match(r"^([A-Z]+)", cell_ref)
    if match:
        return match.group(1)
    return ""


def _get_cell_value(cell, shared_strings: list[str], ns: dict) -> str:
    """
    Get value from cell element.

    Handles:
    - Shared strings (type="s")
    - Inline strings (type="inlineStr")
    - Numbers (no type or type="n")
    - Booleans (type="b")

    Args:
        cell: Cell XML element
        shared_strings: Shared strings lookup
        ns: XML namespace dict

    Returns:
        Cell value as string
    """
    cell_type = cell.get("t", "")

    # Find value element
    value_elem = cell.find("v", ns)
    if value_elem is None or value_elem.text is None:
        # Try inline string
        inline_str = cell.find("is", ns)
        if inline_str is not None:
            text_parts = []
            for t in inline_str.findall(".//t", ns):
                if t.text:
                    text_parts.append(t.text)
            return "".join(text_parts)
        return ""

    value = value_elem.text

    # Shared string reference
    if cell_type == "s":
        try:
            index = int(value)
            if 0 <= index < len(shared_strings):
                return shared_strings[index]
        except (ValueError, IndexError):
            pass
        return ""

    # Boolean
    if cell_type == "b":
        return "True" if value == "1" else "False"

    # Number or plain text
    return value
