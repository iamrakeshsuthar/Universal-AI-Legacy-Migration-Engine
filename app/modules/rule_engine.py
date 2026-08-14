"""
rule_engine.py
Dynamic Business Rules Validation Engine with Natural Language / PDF ingestion.
"""

import json
import io
import re
import PyPDF2
from typing import List, Dict, Any, Optional

import anthropic
from google import genai

def extract_rules_from_document(file_bytes: bytes, file_name: str, ai_provider: str, api_key: str) -> List[Dict[str, Any]]:
    """Reads PDF/TXT/MD and uses GenAI to convert natural language to JSON rules."""
    ext = file_name.split(".")[-1].lower()
    text_content = ""
    
    if ext == "pdf":
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        for page in reader.pages: 
            text_content += page.extract_text() + "\n"
    else:
        text_content = file_bytes.decode("utf-8", errors="ignore")

    prompt = f"""
    Read the following business policy document and extract the validation rules.
    Output ONLY a JSON array of objects with this exact structure:
    [ {{"rule_id": "MOCK_ID", "field": "relevant_field_name", "condition": "gt" | "lt" | "eq" | "not_null" | "ne", "value": 100, "message": "Why it failed", "severity": "error" | "warning"}} ]
    
    POLICY TEXT:
    {text_content[:8000]}
    """

    if ai_provider == "Claude":
        from modules.claude_mapper import MODEL as CLAUDE_MODEL
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=CLAUDE_MODEL, max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        text = "".join([b.text for b in response.content if getattr(b, "type", None) == "text"])
        cleaned = re.sub(r"^```(json)?|```$", "", text.strip()).strip()
        return json.loads(cleaned)
    else:
        client = genai.Client(api_key=api_key)
        
        # Fallback chain to ensure stability across Google's model alias updates
        models = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.0-flash"]
        last_error = None
        
        for model_name in models:
            try:
                # Dropped response_mime_type to prevent strict API server crashes
                response = client.models.generate_content(
                    model=model_name, 
                    contents=prompt
                )
                
                # Manually strip markdown fences and parse safely
                cleaned = re.sub(r"^```(json)?|```$", "", response.text.strip(), flags=re.MULTILINE | re.IGNORECASE).strip()
                return json.loads(cleaned)
                
            except Exception as e:
                last_error = e
                continue
                
        raise RuntimeError(f"Gemini API failed to extract rules. Last error: {last_error}")

def validate_records(records: List[Dict[str, Any]], rules_spec: Optional[List[Dict[str, Any]]] = None) -> Dict[Any, List[Dict[str, str]]]:
    if not rules_spec: return {}
    anomalies: Dict[Any, List[Dict[str, str]]] = {}

    for rec in records:
        rec_id = rec.get("_record_id", rec.get("policy_number", id(rec)))
        rec_issues = []

        for rule in rules_spec:
            field = rule.get("field")
            condition = rule.get("condition")
            target_val = rule.get("value")
            
            val = rec.get(field)

            if condition == "not_null" and (val is None or val == ""):
                rec_issues.append(rule)
            elif condition == "gt" and val is not None and isinstance(val, (int, float)) and val > float(target_val):
                rec_issues.append(rule)
            elif condition == "lt" and val is not None and isinstance(val, (int, float)) and val < float(target_val):
                rec_issues.append(rule)
            elif condition == "eq" and val is not None and str(val) == str(target_val):
                rec_issues.append(rule)

        if rec_issues: 
            anomalies[rec_id] = rec_issues
            
    return anomalies
