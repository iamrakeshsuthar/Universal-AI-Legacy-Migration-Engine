"""
target_schema_upload.py
Parses custom JSON or CSV uploaded target schemas.
"""

import json
import io
import csv
from typing import List, Dict


def parse_uploaded_target_schema(file_bytes: bytes, filename: str) -> List[Dict[str, str]]:
    text = file_bytes.decode("utf-8", errors="replace")
    if filename.lower().endswith(".json"):
        data = json.loads(text)
        return [{"field": e.get("field") or e.get("name") or "", "type": e.get("type", "string"), "description": e.get("description", "")} for e in data]
    if filename.lower().endswith(".csv"):
        reader = csv.DictReader(io.StringIO(text))
        return [{"field": row.get("field") or row.get("name") or "", "type": row.get("type", "string"), "description": row.get("description", "")} for row in reader]
    raise ValueError("Upload .json or .csv target schema.")
