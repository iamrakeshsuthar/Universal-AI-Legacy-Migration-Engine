"""
gemini_mapper.py
AI Field Mapper using Google Gemini API.
"""

import json
from google import genai
from google.genai import types

MODEL = "gemini-flash-latest"
SYSTEM_PROMPT = """You are a data migration mapping assistant. Respond with ONLY a JSON array mapping canonical source_field to target_field.
[{ "source_field": "...", "target_field": "...", "confidence": "high", "notes": "" }]"""


def get_gemini_mapping(api_key: str, sample_rec: dict, target_schema: list) -> list:
    client = genai.Client(api_key=api_key)
    prompt = f"SOURCE SAMPLE:\n{json.dumps(sample_rec, indent=2)}\n\nTARGET SCHEMA:\n{json.dumps(target_schema, indent=2)}"
    response = client.models.generate_content(
        model=MODEL, contents=prompt,
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, response_mime_type="application/json")
    )
    return json.loads(response.text)
