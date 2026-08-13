"""
validator.py
Legacy built-in business rules validator helper.
"""


def calculate_expected_premium(policy: dict) -> dict:
    base = policy.get("premium_amount") or 0.0
    return {"surcharge_amount": 0.0, "adjusted_premium": base}


def validate_all(policies: list) -> dict:
    return {}
