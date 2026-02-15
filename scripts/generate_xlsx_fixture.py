"""
Generate XLSX fixture for candidate folder tests.

Creates a minimal valid XLSX file with key-value pairs using stdlib only.
"""

import zipfile
from pathlib import Path


def generate_application_xlsx(output_path: str, data: dict[str, str]):
    """
    Generate minimal XLSX with key-value pairs.

    Creates an XLSX file with Column A = keys, Column B = values.

    Args:
        output_path: Path where XLSX should be saved
        data: Dict of key-value pairs to write
    """
    # Create output directory if needed
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Prepare shared strings and sheet data
    shared_strings = []
    string_map = {}  # value -> index
    rows = []

    row_num = 1
    for key, value in data.items():
        # Add key to shared strings
        if key not in string_map:
            string_map[key] = len(shared_strings)
            shared_strings.append(key)

        # Add value to shared strings (if string)
        value_ref = ""
        value_type = ""
        if isinstance(value, (int, float)):
            # Numeric value
            value_ref = str(value)
            value_type = ""
        else:
            # String value
            if value not in string_map:
                string_map[value] = len(shared_strings)
                shared_strings.append(value)
            value_ref = str(string_map[value])
            value_type = ' t="s"'

        rows.append((row_num, string_map[key], value_ref, value_type))
        row_num += 1

    # Generate XML content
    content_types_xml = _generate_content_types()
    rels_xml = _generate_rels()
    workbook_xml = _generate_workbook()
    workbook_rels_xml = _generate_workbook_rels()
    shared_strings_xml = _generate_shared_strings(shared_strings)
    sheet1_xml = _generate_sheet(rows)

    # Create XLSX as ZIP
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as xlsx:
        xlsx.writestr("[Content_Types].xml", content_types_xml)
        xlsx.writestr("_rels/.rels", rels_xml)
        xlsx.writestr("xl/workbook.xml", workbook_xml)
        xlsx.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
        xlsx.writestr("xl/sharedStrings.xml", shared_strings_xml)
        xlsx.writestr("xl/worksheets/sheet1.xml", sheet1_xml)


def _generate_content_types() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>
</Types>"""


def _generate_rels() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""


def _generate_workbook() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Sheet1" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>"""


def _generate_workbook_rels() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>
</Relationships>"""


def _generate_shared_strings(strings: list[str]) -> str:
    xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="{count}" uniqueCount="{count}">
""".format(count=len(strings))

    for s in strings:
        # Escape XML special characters
        escaped = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
        xml += f"  <si><t>{escaped}</t></si>\n"

    xml += "</sst>"
    return xml


def _generate_sheet(rows: list[tuple]) -> str:
    xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
"""

    for row_num, key_idx, value_ref, value_type in rows:
        xml += f'    <row r="{row_num}">\n'
        # Column A (key)
        xml += f'      <c r="A{row_num}" t="s"><v>{key_idx}</v></c>\n'
        # Column B (value)
        xml += f'      <c r="B{row_num}"{value_type}><v>{value_ref}</v></c>\n'
        xml += "    </row>\n"

    xml += """  </sheetData>
</worksheet>"""
    return xml


if __name__ == "__main__":
    # Generate fixture for Anusha
    anusha_data = {
        "Full Name": "Anusha Kayam",
        "Email": "anusha@example.com",
        "Phone": "555-123-4567",
        "Location": "Remote",
        "Desired Titles": "Power BI Developer; Data Analyst",
        "Skills": "Power BI, SQL, DAX, Excel, Azure",
        "Years of Experience": "4",
        "Sponsorship Needed": "No",
    }

    output_path = "tests/fixtures/candidates/anusha/application_info.xlsx"
    generate_application_xlsx(output_path, anusha_data)
    print(f"Generated: {output_path}")
