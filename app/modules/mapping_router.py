"""
mapping_router.py
Router that dispatches to Claude or Gemini mapper functions.
"""

from modules.claude_mapper import get_claude_mapping
from modules.gemini_mapper import get_gemini_mapping

PROVIDERS = {
    "Claude": get_claude_mapping,
    "Gemini": get_gemini_mapping,
}


def get_ai_mapping(provider: str, api_key: str, sample: dict, target_schema: list) -> list:
    if provider not in PROVIDERS:
        raise ValueError(f"Unknown AI provider: {provider}")
    return PROVIDERS[provider](api_key, sample, target_schema)
