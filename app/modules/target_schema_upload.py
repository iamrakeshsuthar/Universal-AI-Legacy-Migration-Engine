"""
target_schema_upload.py
Parses custom JSON or CSV uploaded target schemas with robust error handling
and auto-conversion for various JSON structures.
"""

import json
import io
import csv
from typing import List, Dict

def parse_uploaded_target_schema(file_bytes: bytes, filename: str) -> List[Dict[str, str]]:
    text = file_bytes.decode("utf-8", errors="replace")
    
    # ---------------------------------------------------------
    # JSON Parsing Logic
    # ---------------------------------------------------------
    if filename.lower().endswith(".json"):
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON file uploaded. Please check the file formatting.")
            
        # If the user uploaded a dictionary (starts with {...})
        if isinstance(data, dict):
            # Case A: Dictionary of dictionaries (e.g., {"field1": {"type": "string", "description": "..."}})
            if data and all(isinstance(v, dict) for v in data.values()):
                return [
                    {
                        "field": str(k),
                        "type": str(v.get("type", "string")),
                        "description": str(v.get("description", ""))
                    }
                    for k, v in data.items()
                ]
            
            # Case B: Flat dictionary of key:type pairs (e.g., {"field1": "string", "field2": "integer"})
            if data and all(isinstance(v, str) for v in data.values()):
                return [
                    {
                        "field": str(k),
                        "type": str(v),
                        "description": ""
                    }
                    for k, v in data.items()
                ]

            # Case C: Dictionary containing a list (e.g., {"schema": [{"field": "f1"...}]})
            for key, value in data.items():
                if isinstance(value, list):
                    data = value
                    break
            else:
                raise ValueError("JSON structure not recognized. Please use an array of objects [{\"field\": \"...\"}] or a key-value dictionary.")
        
        # Ensure we are now working with a list (for standard array formats)
        if not isinstance(data, list):
            raise ValueError("Target schema JSON must be a list (array) or a valid dictionary object.")
            
        normalized = []
        for e in data:
            if not isinstance(e, dict):
                raise ValueError(f"Expected a dictionary object in JSON array, but got {type(e).__name__}.")
            
            normalized.append({
                "field": str(e.get("field") or e.get("name") or ""),
                "type": str(e.get("type", "string")),
                "description": str(e.get("description", ""))
            })
            
        return normalized

    # ---------------------------------------------------------
    # CSV Parsing Logic
    # ---------------------------------------------------------
    if filename.lower().endswith(".csv"):
        reader = csv.DictReader(io.StringIO(text))
        normalized = []
        for row in reader:
            normalized.append({
                "field": str(row.get("field") or row.get("name") or ""),
                "type": str(row.get("type", "string")),
                "description": str(row.get("description", ""))
            })
        return normalized

    raise ValueError("Unsupported target schema file type. Please upload a .json or .csv file.")
