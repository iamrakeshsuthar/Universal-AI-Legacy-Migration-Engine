"""
generic_source_parser.py
Universal legacy source file ingestion engine.
Handles ZIP, COBOL, JSON, CSV, Excel, XML, and uses self-healing GenAI for unknown formats.
"""

import json
import csv
import io
import zipfile
import time
import pandas as pd
import xmltodict
from typing import List, Dict, Any, Tuple

import anthropic
from google import genai
from google.genai import types
from modules.copybook_parser import parse_copybook
from modules.fixed_width_parser import parse_fixed_width_file

# Robust fallback list of active free/flash-tier models
GEMINI_MODELS = [
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite"
]

def _ai_fallback_parse(file_text: str, ai_provider: str, api_key: str) -> List[Dict[str, Any]]:
    """Uses GenAI to parse unstructured text into a JSON array of records."""
    prompt = f"Extract the following raw legacy data into a structured JSON array of flat dictionary records. Only output valid JSON.\n\nRAW DATA:\n{file_text[:5000]}"
    
    if ai_provider == "Claude":
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-3-5-sonnet-latest", max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )
        text = "".join([b.text for b in response.content if getattr(b, "type", None) == "text"])
        import re
        cleaned = re.sub(r"^```(json)?|```$", "", text.strip()).strip()
        return json.loads(cleaned)
    else:
        client = genai.Client(api_key=api_key)
        last_error = None
        
        for model_name in GEMINI_MODELS:
            try:
                response = client.models.generate_content(
                    model=model_name, contents=prompt,
                    config=types.GenerateContentConfig(response_mime_type="application/json")
                )
                return json.loads(response.text)
            except Exception as e:
                last_error = str(e)
                # Intercept 503 Overload and 404 Deprecated models, then pivot
                if "503" in last_error or "UNAVAILABLE" in last_error.upper() or "demand" in last_error.lower():
                    time.sleep(1)
                    continue
                if "404" in last_error or "NOT_FOUND" in last_error.upper():
                    continue
                continue
                
        raise RuntimeError(f"All Gemini fallback models failed in AI Parser. Last error: {last_error}")

def parse_legacy_source(
    file_bytes: bytes, file_name: str, schema_bytes: bytes = None, 
    ai_provider: str = None, api_key: str = None
) -> Tuple[List[Dict[str, Any]], Dict[str, Any], bytes]:
    """Parses any file, including extracting from ZIPs."""
    ext = file_name.split(".")[-1].lower()
    records: List[Dict[str, Any]] = []
    extracted_rules = None

    # Handle ZIP Workspace
    if ext == "zip":
        with zipfile.ZipFile(io.BytesIO(file_bytes), "r") as z:
            data_file, rules_file = None, None
            for name in z.namelist():
                if "rule" in name.lower(): rules_file = name
                elif name.endswith(('.csv', '.json', '.dat', '.txt', '.xml', '.xlsx')): data_file = name
            
            if rules_file:
                extracted_rules = z.read(rules_file)
            if data_file:
                file_bytes = z.read(data_file)
                file_name = data_file
                ext = file_name.split(".")[-1].lower()

    try:
        if ext == "json":
            data = json.loads(file_bytes.decode("utf-8", errors="replace"))
            records = data if isinstance(data, list) else [data]
        elif ext == "csv":
            records = pd.read_csv(io.BytesIO(file_bytes)).to_dict(orient="records")
        elif ext in ["xlsx", "xls"]:
            records = pd.read_excel(io.BytesIO(file_bytes)).to_dict(orient="records")
        elif ext == "xml":
            parsed = xmltodict.parse(file_bytes.decode("utf-8", errors="replace"))
            root_key = list(parsed.keys())[0]
            content = parsed[root_key]
            records = content if isinstance(content, list) else [content]
        elif ext in ["dat", "cpy"] and schema_bytes:
            schema = parse_copybook(schema_bytes.decode("utf-8", errors="replace"))
            records = parse_fixed_width_file(file_bytes.decode("utf-8", errors="replace"), schema)
        else:
            # AI Fallback for unknown text files
            if api_key:
                records = _ai_fallback_parse(file_bytes.decode("utf-8", errors="replace"), ai_provider, api_key)
            else:
                raise ValueError("Unsupported format and no API key provided for AI parsing.")
    except Exception as e:
        if api_key: # Try AI if deterministic fails
            records = _ai_fallback_parse(file_bytes.decode("utf-8", errors="replace"), ai_provider, api_key)
        else:
            raise e

    for idx, r in enumerate(records):
        r["_record_id"] = idx + 1
    
    schema_meta = {k: type(v).__name__ for k, v in records[0].items() if not str(k).startswith("_")} if records else {}
    return records, schema_meta, extracted_rules
