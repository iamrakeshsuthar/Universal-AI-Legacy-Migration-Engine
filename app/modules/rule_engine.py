"""
rule_engine.py
Dynamic & Optional Business Rules Validation Engine.
Executes custom rules if provided, or bypasses if none uploaded.
"""

from typing import List, Dict, Any, Optional


def validate_records(
    records: List[Dict[str, Any]], 
    rules_spec: Optional[List[Dict[str, Any]]] = None
) -> Dict[Any, List[Dict[str, str]]]:
    if not rules_spec:
        return {}

    anomalies: Dict[Any, List[Dict[str, str]]] = {}

    for rec in records:
        rec_id = rec.get("_record_id", rec.get("policy_number", id(rec)))
        rec_issues = []

        for rule in rules_spec:
            field = rule.get("field")
            condition = rule.get("condition")
            target_val = rule.get("value")
            rule_id = rule.get("rule_id", "CUSTOM_RULE")
            severity = rule.get("severity", "warning")
            message = rule.get("message", "Rule violation detected")

            val = rec.get(field)

            if condition == "not_null" and (val is None or val == ""):
                rec_issues.append({"rule": rule_id, "severity": severity, "message": message, "field": field})
            elif condition == "gt" and val is not None and val > target_val:
                rec_issues.append({"rule": rule_id, "severity": severity, "message": message, "field": field})
            elif condition == "lt" and val is not None and val < target_val:
                rec_issues.append({"rule": rule_id, "severity": severity, "message": message, "field": field})
            elif condition == "eq" and val is not None and val == target_val:
                rec_issues.append({"rule": rule_id, "severity": severity, "message": message, "field": field})

        if rec_issues:
            anomalies[rec_id] = rec_issues

    return anomalies
