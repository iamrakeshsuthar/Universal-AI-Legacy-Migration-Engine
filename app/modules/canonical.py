"""
canonical.py
Builds canonical records joined with nested claim structures.
"""

from typing import List, Dict, Any
from datetime import datetime


def _parse_cobol_date(raw: Any):
    if raw is None:
        return None
    s = str(int(raw)) if isinstance(raw, (int, float)) else str(raw)
    s = s.strip()
    if len(s) != 8 or not s.isdigit():
        return None
    try:
        return datetime.strptime(s, "%Y%m%d").date().isoformat()
    except ValueError:
        return None


def build_canonical_policies(policy_records: List[Dict], claim_records: List[Dict]) -> List[Dict[str, Any]]:
    claims_by_policy: Dict[int, List[Dict]] = {}
    for c in claim_records:
        pol_num = c.get("CLM_POLICY_NUMBER")
        claims_by_policy.setdefault(pol_num, []).append(c)

    canonical = []
    for p in policy_records:
        pol_num = p.get("POL_POLICY_NUMBER")
        related_claims = claims_by_policy.get(pol_num, [])

        canonical_claims = []
        for c in related_claims:
            canonical_claims.append({
                "claim_number": c.get("CLM_CLAIM_NUMBER"),
                "accident_date": _parse_cobol_date(c.get("CLM_ACCIDENT_DATE")),
                "damage_description": c.get("CLM_DAMAGE_DESC"),
                "amount": c.get("CLM_AMOUNT"),
                "status": c.get("CLM_STATUS"),
            })

        base_record = {
            "policy_number": pol_num,
            "customer_name": p.get("POL_CUSTOMER_NAME"),
            "vehicle_model": p.get("POL_VEHICLE_MODEL"),
            "coverage_amount": p.get("POL_COVERAGE_AMOUNT"),
            "premium_amount": p.get("POL_PREMIUM_AMOUNT"),
            "status": p.get("POL_POLICY_STATUS"),
            "expiration_date": _parse_cobol_date(p.get("POL_EXPIRATION_DATE")),
            "claims": canonical_claims,
            "_source_line": p.get("_source_line"),
        }
        canonical.append(base_record)

    return canonical
