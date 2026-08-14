"""
reconciler.py
Handles interactive reconciliation, manual overrides, and AI-suggested fixes.
"""

from typing import List, Dict, Any
import anthropic
from google import genai
from modules.claude_mapper import MODEL as CLAUDE_MODEL
from modules.gemini_mapper import MODEL as GEMINI_MODEL

def update_record_field(records: List[Dict[str, Any]], record_id: Any, field_name: str, new_value: Any):
    for r in records:
        if r.get("_record_id") == record_id or r.get("policy_number") == record_id:
            r[field_name] = new_value
            return True
    return False

def resolve_anomaly(anomalies_dict: Dict[Any, List[Dict]], record_id: Any):
    if record_id in anomalies_dict:
        del anomalies_dict[record_id]

def get_ai_fix_suggestion(record: Dict, anomaly: Dict, ai_provider: str, api_key: str) -> str:
    """Asks the LLM to suggest a fix for a specific rule violation."""
    prompt = f"The following record violated this business rule:\nRule: {anomaly['message']}\nRecord:\n{record}\n\nSuggest a brief, specific fix for the user. Example: 'Change coverage_amount to 50000'."
    
    if ai_provider == "Claude":
        client = anthropic.Anthropic(api_key=api_key)
        res = client.messages.create(model=CLAUDE_MODEL, max_tokens=100, messages=[{"role": "user", "content": prompt}])
        return "".join([b.text for b in res.content if getattr(b, "type", None) == "text"])
    else:
        client = genai.Client(api_key=api_key)
        res = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        return res.text
