"""
copybook_parser.py
Parses a COBOL copybook (.cpy) and infers field offsets and PIC types.
"""

import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class CopybookField:
    name: str
    raw_name: str
    pic_clause: str
    data_type: str
    length: int
    decimal_places: int
    start: int
    end: int


@dataclass
class CopybookSchema:
    record_name: str
    fields: List[CopybookField] = field(default_factory=list)
    total_length: int = 0


_PIC_NUMERIC_DECIMAL = re.compile(r"PIC\s+9\((\d+)\)V9\((\d+)\)", re.IGNORECASE)
_PIC_NUMERIC_DECIMAL_SHORT = re.compile(r"PIC\s+9\((\d+)\)V(9+)", re.IGNORECASE)
_PIC_NUMERIC = re.compile(r"PIC\s+9\((\d+)\)", re.IGNORECASE)
_PIC_ALPHA = re.compile(r"PIC\s+X\((\d+)\)", re.IGNORECASE)
_FIELD_LINE = re.compile(r"^\s*(\d{2})\s+([A-Z0-9\-]+)\s+(PIC\s+.+?)\.\s*$", re.IGNORECASE)


def _normalize_name(raw_name: str) -> str:
    return raw_name.upper().replace("-", "_")


def _parse_pic(pic_clause: str):
    m = _PIC_NUMERIC_DECIMAL.search(pic_clause)
    if m:
        return "decimal", int(m.group(1)) + int(m.group(2)), int(m.group(2))
    m = _PIC_NUMERIC_DECIMAL_SHORT.search(pic_clause)
    if m:
        return "decimal", int(m.group(1)) + len(m.group(2)), len(m.group(2))
    m = _PIC_NUMERIC.search(pic_clause)
    if m:
        return "numeric", int(m.group(1)), 0
    m = _PIC_ALPHA.search(pic_clause)
    if m:
        return "alphanumeric", int(m.group(1)), 0
    raise ValueError(f"Unsupported PIC clause: {pic_clause}")


def parse_copybook(source_text: str) -> CopybookSchema:
    lines = source_text.splitlines()
    record_name = "RECORD"
    fields: List[CopybookField] = []
    offset = 0

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("*"):
            continue
        record_match = re.match(r"^\s*01\s+([A-Z0-9\-]+)\.?\s*$", stripped, re.IGNORECASE)
        if record_match:
            record_name = record_match.group(1)
            continue
        field_match = _FIELD_LINE.match(stripped)
        if field_match:
            _, raw_name, pic_clause = field_match.groups()
            data_type, length, decimals = _parse_pic(pic_clause)
            f = CopybookField(
                name=_normalize_name(raw_name), raw_name=raw_name, pic_clause=pic_clause.strip(),
                data_type=data_type, length=length, decimal_places=decimals, start=offset, end=offset + length
            )
            fields.append(f)
            offset += length

    return CopybookSchema(record_name=record_name, fields=fields, total_length=offset)
