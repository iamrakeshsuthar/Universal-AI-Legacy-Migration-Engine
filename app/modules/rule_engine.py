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

def _safe_extract_json(raw_text: str) -> List[Dict[str, Any]]:
    """Bulletproof JSON extractor that hunts for arrays and ignores conversational filler."""
    if not raw_text or not raw_text.strip():
        raise ValueError("Received empty text from AI. This may be due to AI safety filters blocking the content.")
        
    # 1. Try to find a markdown code block first
    match = re.search(r'```(?:json)?\s*(.*?)\s*```', raw_text, flags=re.DOTALL | re.IGNORECASE)
    if match:
        clean_str = match.group(1).strip()
    else:
        # 2. If no markdown, hunt for the first '[' and last ']'
        start_idx = raw_text.find('[')
        end_idx = raw_text.rfind(']')
        if start_idx != -1 and end_idx != -1:
            clean_str = raw_text[start_idx:end_idx+1]
        else:
            # 3. Fallback to just stripping whitespace
            clean_str = raw_text.strip()
            
    return json.loads(clean_str)

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
        return _safe_extract_json(text)
        
    else:
        client = genai.Client(api_key=api_key)
        
        # 'gemini-flash-latest' is the most universally accessible alias across all Google API tiers
        models = ["gemini-flash-latest", "gemini-1.5-flash", "gemini-2.5-flash"]
        error_logs = []
        
        for model_name in models:
            response = None
            try:
                response = client.models.generate_content(
                    model=model_name, 
                    contents=prompt
                )
                
                if not response.text:
                    raise ValueError("Empty response received. Google Safety Filters may have blocked the document extraction.")
                    
                return _safe_extract_json(response.text)
                
            except Exception as e:
                # Capture the exact error for this specific model attempt
                err_msg = f"[{model_name}] {type(e).__name__}: {str(e)}"
                if response and hasattr(response, 'text') and response.text:
                    err_msg += f" | Raw Output: {response.text[:200]}"
                error_logs.append(err_msg)
                continue
                
        # If we reach here, all models failed. Print the exact errors so we can see what Google is complaining about.
        formatted_errors = "\n".join(error_logs)
        raise RuntimeError(f"Gemini API failed to extract rules after trying multiple models.\nDetails:\n{formatted_errors}")

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
