"""
gemini_mapper.py
AI Field Mapper using Google Gemini API with self-healing 503 fallback.
"""

import json
import re
import time
from typing import List, Dict, Any

from google import genai

# A robust list of 4 free/flash-tier models to cycle through if one is overloaded (503)
# These are the latest, fastest baseline models available without billing.
MODELS_TO_TRY = [
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite"
]

MAPPING_SYSTEM_PROMPT = """You are a data migration mapping assistant for an insurance \
policy administration system (PAS) modernization project.

You will be given:
1. A list of canonical source fields (with example values) coming from a \
legacy mainframe system.
2. A target schema (field name, type, description) for a modern cloud-native PAS.

Your job: propose a mapping from each canonical source field to the best-fit \
target field. For nested/array target fields (like claims[].amount), map the \
corresponding canonical sub-field.

Respond with ONLY a JSON array, no prose, no markdown fences. Each element:
{
  "source_field": "<canonical field name>",
  "target_field": "<target field path>",
  "confidence": "high" | "medium" | "low",
  "notes": "<short note on transformation or ambiguity, or empty string>"
}

If a canonical field has no reasonable target match, still include it with \
target_field set to "UNMAPPED" and a note explaining why.
"""

def _build_user_prompt(canonical_sample: Dict[str, Any], target_schema: List[Dict[str, str]]) -> str:
    source_fields = []
    for key, value in canonical_sample.items():
        if key.startswith("_"): continue
        if key == "claims":
            if value:
                for ck, cv in value[0].items(): source_fields.append(f"claims.{ck} (example: {cv!r})")
            else:
                source_fields.append("claims.* (claim_number, accident_date, damage_description, amount, status)")
        else:
            source_fields.append(f"{key} (example: {value!r})")

    target_lines = [f"- {t['field']} ({t['type']}): {t['description']}" for t in target_schema]

    return (
        "CANONICAL SOURCE FIELDS:\n" + "\n".join(f"- {f}" for f in source_fields) +
        "\n\nTARGET SCHEMA:\n" + "\n".join(target_lines) +
        "\n\nProvide the mapping JSON array now."
    )

def _safe_extract_json(raw_text: str) -> List[Dict[str, Any]]:
    """Bulletproof JSON extractor that hunts for arrays and ignores conversational filler."""
    match = re.search(r'```(?:json)?\s*(.*?)\s*```', raw_text, flags=re.DOTALL | re.IGNORECASE)
    if match:
        clean_str = match.group(1).strip()
    else:
        start_idx, end_idx = raw_text.find('['), raw_text.rfind(']')
        clean_str = raw_text[start_idx:end_idx+1] if start_idx != -1 and end_idx != -1 else raw_text.strip()
    return json.loads(clean_str)

def get_gemini_mapping(api_key: str, canonical_sample: Dict[str, Any], target_schema: List[Dict[str, str]]) -> List[Dict[str, str]]:
    client = genai.Client(api_key=api_key)
    prompt = f"SYSTEM INSTRUCTIONS:\n{MAPPING_SYSTEM_PROMPT}\n\n{_build_user_prompt(canonical_sample, target_schema)}"
    
    last_error = None
    
    for model_name in MODELS_TO_TRY:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            
            if not response.text:
                raise ValueError("Empty response received from AI.")
                
            return _safe_extract_json(response.text)
            
        except Exception as e:
            last_error = str(e)
            # If 503 Unavailable / High Demand, pause briefly and pivot to the next model in the list
            if "503" in last_error or "UNAVAILABLE" in last_error.upper() or "demand" in last_error.lower():
                time.sleep(1) 
                continue
            continue

    raise RuntimeError(f"All 4 Gemini fallback models failed. Last error: {last_error}")
