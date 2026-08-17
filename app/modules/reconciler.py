"""
reconciler.py
Handles interactive reconciliation, manual overrides, and AI-suggested holistic row fixes.
"""

from typing import List, Dict, Any
import time

import anthropic
from google import genai

# Robust fallback list using active models
MODELS_TO_TRY = [
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash"
]

def update_record_field(records: List[Dict[str, Any]], record_id: Any, field_name: str, new_value: Any):
    for r in records:
        if r.get("_record_id") == record_id or r.get("policy_number") == record_id:
            r[field_name] = new_value
            return True
    return False

def resolve_anomaly(anomalies_dict: Dict[Any, List[Dict]], record_id: Any):
    if record_id in anomalies_dict:
        del anomalies_dict[record_id]

def get_ai_fix_suggestion(record: Dict, anomalies: List[Dict], ai_provider: str, api_key: str) -> str:
    """Asks the LLM to suggest holistic fixes for a record based on all its rule violations."""
    
    issues_text = "\n".join([f"- {a.get('rule_id', 'RULE')}: {a['message']}" for a in anomalies])
    
    prompt = f"""
The following record has rule violations that need to be fixed.

RULE VIOLATIONS:
{issues_text}

CURRENT RECORD DATA:
{record}

Analyze the entire row. Suggest specific fixes for any fields that need updating to resolve ALL violations. 
Keep it concise. Example: 'Change coverage_amount to 50000 and update status to Active.'
"""
    
    if ai_provider == "Claude":
        from modules.claude_mapper import MODEL as CLAUDE_MODEL
        client = anthropic.Anthropic(api_key=api_key)
        res = client.messages.create(model=CLAUDE_MODEL, max_tokens=200, messages=[{"role": "user", "content": prompt}])
        return "".join([b.text for b in res.content if getattr(b, "type", None) == "text"])
    else:
        client = genai.Client(api_key=api_key)
        last_error = None
        
        for model_name in MODELS_TO_TRY:
            try:
                res = client.models.generate_content(
                    model=model_name, 
                    contents=prompt
                )
                if not res.text:
                    raise ValueError("Empty response received from AI.")
                return res.text
            except Exception as e:
                last_error = str(e)
                # Intercept 503 Overload Errors and quietly cycle to the next model
                if "503" in last_error or "UNAVAILABLE" in last_error.upper() or "demand" in last_error.lower():
                    time.sleep(1)
                    continue
                continue
                
        return f"AI Suggestion failed after trying {len(MODELS_TO_TRY)} fallback models. Last error: {last_error}"
