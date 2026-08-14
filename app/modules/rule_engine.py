"""
rule_engine.py
Dynamic Business Rules Validation Engine with Natural Language / PDF ingestion.
"""

import json
import io
import PyPDF2
from typing import List, Dict, Any, Optional

import anthropic
from google import genai
from google.genai import types
from modules.claude_mapper import MODEL as CLAUDE_MODEL
from modules.gemini_mapper import MODEL as GEMINI_MODEL

def extract_rules_from_document(file_bytes: bytes, file_name: str, ai_provider: str, api_key: str) -> List[Dict[str, Any]]:
    """Reads PDF/TXT/MD and uses GenAI to convert natural language to JSON rules."""
    ext = file_name.split(".")[-1].lower()
    text_content = ""
    
    if ext == "pdf":
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        for page in reader.pages: text_content += page.extract_text() + "\n"
    else:
        text_content = file_bytes.decode("utf-8", errors="ignore")

    prompt = f"""
    Read the following business policy document and extract the validation rules.
    Output ONLY a JSON array of objects with this exact structure:
    [ {{"rule_id": "MOCK_ID", "field": "relevant_field_name", "condition": "gt" | "lt" | "eq" | "not_null" | "ne", "value": <numeric or string limit>, "message": "Why it failed", "severity": "error" | "warning"}} ]
    
    POLICY TEXT:
    {text_content[:8000]}
    """

    if ai_provider == "Claude":
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=CLAUDE_MODEL, max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        text = "".join([b.text for b in response.content if getattr(b, "type", None) == "text"])
        import re
        return json.loads(re.sub(r"^```(json)?|```$", "", text.strip()).strip())
    else:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=GEMINI_MODEL, contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        return json.loads(response.text)

def validate_records(records: List[Dict[str, Any]], rules_spec: Optional[List[Dict[str, Any]]] = None) -> Dict[Any, List[Dict[str, str]]]:
    if not rules_spec: return {}
    anomalies: Dict[Any, List[Dict[str, str]]] = {}

    for rec in records:
        rec_id = rec.get("_record_id", rec.get("policy_number", id(rec)))
        rec_issues = []

        for rule in rules_spec:
            field, condition, target_val = rule.get("field"), rule.get("condition"), rule.get("value")
            val = rec.get(field)

            if condition == "not_null" and (val is None or val == ""):
                rec_issues.append(rule)
            elif condition == "gt" and val is not None and isinstance(val, (int, float)) and val > float(target_val):
                rec_issues.append(rule)
            elif condition == "lt" and val is not None and isinstance(val, (int, float)) and val < float(target_val):
                rec_issues.append(rule)
            elif condition == "eq" and val is not None and str(val) == str(target_val):
                rec_issues.append(rule)

        if rec_issues: anomalies[rec_id] = rec_issues
    return anomalies
