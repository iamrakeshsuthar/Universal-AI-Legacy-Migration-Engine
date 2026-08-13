"""
exporter.py
Applies mapping specifications deterministically to all records.
"""

import json
import copy
from typing import List, Dict, Any


def _set_nested(target: Dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    cur = target
    for i, part in enumerate(parts):
        if i == len(parts) - 1:
            cur[part] = value
        else:
            if part not in cur or not isinstance(cur[part], dict):
                cur[part] = {}
            cur = cur[part]


def apply_mapping(
    source_records: List[Dict[str, Any]],
    mapping_spec: List[Dict[str, str]],
    anomalies_by_record: Dict[Any, List[Dict[str, str]]],
) -> List[Dict[str, Any]]:
    valid_mappings = [m for m in mapping_spec if m.get("target_field") != "UNMAPPED"]
    results = []

    for rec in source_records:
        target: Dict[str, Any] = {}
        for m in valid_mappings:
            src, tgt = m["source_field"], m["target_field"]
            if src.startswith("claims."):
                continue
            val = rec.get(src)
            if val is not None:
                _set_nested(target, tgt, val)

        rec_id = rec.get("_record_id", rec.get("policy_number"))
        rec_anomalies = anomalies_by_record.get(rec_id, [])
        _set_nested(target, "metadata.sourceSystem", "LEGACY-SYSTEM")
        _set_nested(target, "metadata.anomalyFlags", [a["rule"] for a in rec_anomalies])
        results.append(target)

    return results


def to_json_string(records: List[Dict[str, Any]]) -> str:
    return json.dumps(records, indent=2, default=str)


def flatten_for_csv(records: List[Dict[str, Any]]):
    import pandas as pd
    flat_rows = []
    for rec in records:
        row = {}
        def _flatten(prefix, obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    _flatten(f"{prefix}.{k}" if prefix else k, v)
            elif isinstance(obj, list):
                row[f"{prefix}_count"] = len(obj)
            else:
                row[prefix] = obj
        _flatten("", copy.deepcopy(rec))
        flat_rows.append(row)
    return pd.DataFrame(flat_rows)
