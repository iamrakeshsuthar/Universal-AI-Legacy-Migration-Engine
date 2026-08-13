"""
generic_source_parser.py
Universal legacy source file ingestion engine.
Handles COBOL (.cpy + .DAT), JSON, CSV, Excel (.xlsx), and XML formats.
"""

import json
import csv
import io
import pandas as pd
import xmltodict
from typing import List, Dict, Any, Tuple
from modules.copybook_parser import parse_copybook
from modules.fixed_width_parser import parse_fixed_width_file

def parse_legacy_source(
    file_bytes: bytes, 
    file_name: str, 
    schema_bytes: bytes = None, 
    schema_name: str = None
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Parses any input legacy file into a list of generic canonical records 
    and returns (records, extracted_schema_info).
    """
    ext = file_name.split(".")[-1].lower()
    records: List[Dict[str, Any]] = []

    if ext == "json":
        data = json.loads(file_bytes.decode("utf-8", errors="replace"))
        records = data if isinstance(data, list) else [data]

    elif ext == "csv":
        df = pd.read_csv(io.BytesIO(file_bytes))
        records = df.to_dict(orient="records")

    elif ext in ["xlsx", "xls"]:
        df = pd.read_excel(io.BytesIO(file_bytes))
        records = df.to_dict(orient="records")

    elif ext == "xml":
        parsed = xmltodict.parse(file_bytes.decode("utf-8", errors="replace"))
        root_key = list(parsed.keys())[0]
        content = parsed[root_key]
        if isinstance(content, list):
            records = content
        elif isinstance(content, dict):
            sub_lists = [v for k, v in content.items() if isinstance(v, list)]
            records = sub_lists[0] if sub_lists else [content]

    elif ext in ["dat", "txt", "cpy"]:
        if schema_bytes:
            cpy_text = schema_bytes.decode("utf-8", errors="replace")
            dat_text = file_bytes.decode("utf-8", errors="replace")
            schema = parse_copybook(cpy_text)
            records = parse_fixed_width_file(dat_text, schema)
        else:
            raise ValueError("For COBOL/Fixed-width files, please provide a matching Copybook schema (.cpy).")
            
    else:
        raise ValueError(f"Unsupported legacy file extension: .{ext}")

    for idx, r in enumerate(records):
        r["_record_id"] = idx + 1

    schema_meta = {}
    if records:
        schema_meta = {k: type(v).__name__ for k, v in records[0].items() if not k.startswith("_")}

    return records, schema_meta
