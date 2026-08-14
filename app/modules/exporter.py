"""
exporter.py
Handles deterministic data mapping, JSON/CSV exports, Migration Report generation,
and in-memory ZIP creation for Granular Batch Exports.
"""

import json
import io
import copy
import zipfile
import pandas as pd
from typing import List, Dict, Any

def _set_nested(target: Dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    cur = target
    for i, part in enumerate(parts):
        is_last = i == len(parts) - 1
        if is_last:
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
            if src.startswith("claims."): continue
            val = rec.get(src)
            if val is not None: _set_nested(target, tgt, val)

        rec_id = rec.get("_record_id", rec.get("policy_number", id(rec)))
        rec_anomalies = anomalies_by_record.get(rec_id, [])
        _set_nested(target, "metadata.sourceSystem", "LEGACY-SYSTEM")
        _set_nested(target, "metadata.anomalyFlags", [a["rule_id"] for a in rec_anomalies])
        
        # Keep internal ID for routing
        target["_record_id"] = rec_id
        results.append(target)

    return results

def to_json_string(records: List[Dict[str, Any]]) -> str:
    clean_recs = [{k: v for k, v in r.items() if not k.startswith("_")} for r in records]
    return json.dumps(clean_recs, indent=2, default=str)

def flatten_for_csv(records: List[Dict[str, Any]]) -> pd.DataFrame:
    flat_rows = []
    for rec in records:
        row = {}
        def _flatten(prefix, obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if not k.startswith("_"): _flatten(f"{prefix}.{k}" if prefix else k, v)
            elif isinstance(obj, list):
                row[f"{prefix}_count"] = len(obj)
            else:
                row[prefix] = obj
        _flatten("", copy.deepcopy(rec))
        flat_rows.append(row)
    return pd.DataFrame(flat_rows)

def generate_migration_report(total: int, clean: int, flagged: int, mapping: list) -> str:
    """Generates a comprehensive Markdown report of the migration batch."""
    report = f"""# AI Migration Batch Report
    
## 📊 Migration Metrics
* **Total Records Processed:** {total}
* **Clean (Auto-Converted):** {clean}
* **Quarantined (Rule Violations):** {flagged}
* **Success Rate:** {round((clean/total)*100, 1) if total > 0 else 0}%

## 🧭 Applied AI Mapping Specification
The following mappings were proposed by the AI and applied to the target PAS schema:

| Source Field | Target Field | Confidence | Notes |
|---|---|---|---|
"""
    for m in mapping:
        report += f"| {m.get('source_field','')} | {m.get('target_field','')} | {m.get('confidence','')} | {m.get('notes','')} |\n"
    
    return report

def create_export_zip(clean_records: list, quarantined_records: list, report_md: str) -> bytes:
    """Packages separate JSON files and a Markdown report into a single ZIP byte stream."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as z:
        if clean_records:
            z.writestr("clean_records.json", to_json_string(clean_records))
        if quarantined_records:
            z.writestr("quarantined_records.json", to_json_string(quarantined_records))
        z.writestr("migration_report.md", report_md)
    return zip_buffer.getvalue()
