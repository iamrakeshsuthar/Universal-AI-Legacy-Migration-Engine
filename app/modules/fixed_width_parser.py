"""
fixed_width_parser.py
Parses fixed-width files according to CopybookSchema.
"""

from typing import List, Dict, Any
from modules.copybook_parser import CopybookSchema


def decode_field(raw_value: str, cf) -> Any:
    raw_value = raw_value.rstrip()
    if cf.data_type == "alphanumeric":
        return raw_value.strip()
    if cf.data_type in ("numeric", "decimal"):
        digits = raw_value.strip()
        if digits == "":
            return None
        if not digits.lstrip("-").isdigit():
            return {"__raw_invalid__": raw_value}
        value = int(digits)
        if cf.decimal_places > 0:
            value = value / (10 ** cf.decimal_places)
        return value
    return raw_value


def parse_fixed_width_file(file_text: str, schema: CopybookSchema) -> List[Dict[str, Any]]:
    records = []
    for line_num, line in enumerate(file_text.splitlines(), start=1):
        if not line.strip():
            continue
        record: Dict[str, Any] = {"_source_line": line_num, "_raw_line": line}
        for cf in schema.fields:
            raw_value = line[cf.start:cf.end] if len(line) >= cf.end else line[cf.start:]
            record[cf.name] = decode_field(raw_value, cf)
        records.append(record)
    return records
