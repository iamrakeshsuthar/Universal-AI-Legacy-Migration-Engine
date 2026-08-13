"""
reconciler.py
Handles interactive reconciliation and record modifications.
"""

from typing import List, Dict, Any


def update_record_field(records: List[Dict[str, Any]], record_id: Any, field_name: str, new_value: Any):
    for r in records:
        if r.get("_record_id") == record_id or r.get("policy_number") == record_id:
            r[field_name] = new_value
            return True
    return False


def resolve_anomaly(anomalies_dict: Dict[Any, List[Dict]], record_id: Any, rule_code: str = None):
    if record_id in anomalies_dict:
        if rule_code:
            anomalies_dict[record_id] = [a for a in anomalies_dict[record_id] if a["rule"] != rule_code]
            if not anomalies_dict[record_id]:
                del anomalies_dict[record_id]
        else:
            del anomalies_dict[record_id]
