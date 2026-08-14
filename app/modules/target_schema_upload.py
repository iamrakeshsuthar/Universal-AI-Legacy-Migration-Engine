"""
target_schema_upload.py
Parses custom JSON or CSV uploaded target schemas with robust error handling.
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
            
        # If the user uploaded a dictionary (e.g., {"fields": [...]}), auto-extract the inner list
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, list):
                    data = value
                    break
            else:
                raise ValueError("Could not find an array of fields in the uploaded JSON object.")
        
        # Ensure we are now working with a list
        if not isinstance(data, list):
            raise ValueError("Target schema JSON must be a list (array) of {field, type, description} objects.")
            
        normalized = []
        for e in data:
            # Prevent AttributeError by ensuring 'e' is actually a dictionary
            if not isinstance(e, dict):
                raise ValueError(f"Expected a dictionary object in JSON array, but got a {type(e).__name__}.")
            
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
