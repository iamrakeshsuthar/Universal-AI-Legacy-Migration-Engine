"""
claude_mapper.py
AI Field Mapper using Anthropic Claude API.
"""

import json
import re
import anthropic

MODEL = "claude-sonnet-4-5"
SYSTEM_PROMPT = """You are a data migration mapping assistant. Respond with ONLY a JSON array mapping canonical source_field to target_field.
[{ "source_field": "...", "target_field": "...", "confidence": "high", "notes": "" }]"""


def get_claude_mapping(api_key: str, sample_rec: dict, target_schema: list) -> list:
    client = anthropic.Anthropic(api_key=api_key)
    prompt = f"SOURCE SAMPLE:\n{json.dumps(sample_rec, indent=2)}\n\nTARGET SCHEMA:\n{json.dumps(target_schema, indent=2)}"
    response = client.messages.create(
        model=MODEL, max_tokens=2000, system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}]
    )
    text = "".join([b.text for b in response.content if getattr(b, "type", None) == "text"])
    cleaned = re.sub(r"^```(json)?|```$", "", text.strip()).strip()
    return json.loads(cleaned)
