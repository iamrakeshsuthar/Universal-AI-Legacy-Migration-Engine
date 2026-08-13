"""
app.py - Version 2
Universal AI Legacy Policy Migration Engine with Multi-Format Ingestion,
Optional Relational Business Rules, and Interactive Reconciliation Workspace.
"""

import sys
import os
import json
import streamlit as st
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))

from modules.generic_source_parser import parse_legacy_source
from modules.rule_engine import validate_records
from modules.reconciler import update_record_field, resolve_anomaly
from modules.target_schema import DEFAULT_TARGET_SCHEMA
from modules.target_schema_upload import parse_uploaded_target_schema
from modules.mapping_router import get_ai_mapping
from modules.exporter import apply_mapping, to_json_string, flatten_for_csv

st.set_page_config(page_title="Universal Policy Migration Engine v2", layout="wide")

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "sample_data")

# Session state initialization
for key in ["canonical", "anomalies", "mapping_spec", "target_records", "target_schema", "source_records"]:
    if key not in st.session_state:
        st.session_state[key] = None

st.title("🔄 Universal AI Legacy Migration & Reconciliation Engine")
st.caption("Convert any legacy format (JSON, CSV, Excel, XML, COBOL/DAT) to Modern PAS with AI mapping, optional business rules, and live anomaly reconciliation.")

with st.sidebar:
    st.header("⚙️ Configuration")
    ai_provider = st.radio("AI provider for schema mapping", ["Claude", "Gemini"], horizontal=True)
    api_key_label = "Claude API key" if ai_provider == "Claude" else "Google Gemini API key"
    api_key = st.text_input(api_key_label, type="password")
    st.markdown("---")
    use_sample = st.checkbox("Use bundled sample legacy dataset", value=True)

# ---------------------------------------------------------------------------
# Step 1: Universal Legacy Intake
# ---------------------------------------------------------------------------
st.header("1️⃣ Legacy Source Intake")
source_records = []
source_meta = {}

if use_sample:
    col1, col2 = st.columns(2)
    sample_policies = os.path.join(SAMPLE_DIR, "POLICIES.DAT")
    sample_cpy = os.path.join(SAMPLE_DIR, "POLICYREC.cpy")

    if os.path.exists(sample_policies) and os.path.exists(sample_cpy):
        with open(sample_policies, "rb") as f_dat, open(sample_cpy, "rb") as f_cpy:
            source_records, source_meta = parse_legacy_source(
                f_dat.read(), "POLICIES.DAT", f_cpy.read(), "POLICYREC.cpy"
            )
        col1.success("Using bundled sample: POLICIES.DAT + POLICYREC.cpy")
        col2.info(f"Loaded {len(source_records)} records.")
else:
    col1, col2 = st.columns(2)
    with col1:
        src_file = st.file_uploader("Upload Legacy File (.json, .csv, .xlsx, .xml, .dat)", type=["json", "csv", "xlsx", "xls", "xml", "dat", "txt"], key="src_file")
    with col2:
        schema_file = st.file_uploader("Upload Copybook Schema (.cpy) — For DAT files", type=["cpy", "txt"], key="schema_file")

    if src_file:
        try:
            s_bytes = schema_file.read() if schema_file else None
            s_name = schema_file.name if schema_file else None
            source_records, source_meta = parse_legacy_source(src_file.read(), src_file.name, s_bytes, s_name)
            st.success(f"Parsed {len(source_records)} records!")
        except Exception as e:
            st.error(f"Error parsing file: {e}")

if source_records:
    with st.expander("🔍 Preview Ingested Records", expanded=False):
        st.dataframe(pd.DataFrame(source_records).head(15), use_container_width=True)

st.markdown("---")

# ---------------------------------------------------------------------------
# Step 2: Target Schema & Business Rules
# ---------------------------------------------------------------------------
st.header("2️⃣ Target Schema & Business Rules")
t_col, r_col = st.columns(2)

with t_col:
    st.subheader("Target PAS Schema")
    target_mode = st.radio("Choose target schema", ["Default modern PAS schema", "Upload custom schema (.json/.csv)"], horizontal=True)
    if target_mode.startswith("Default"):
        target_schema = DEFAULT_TARGET_SCHEMA
    else:
        target_schema_file = st.file_uploader("Upload custom target schema", type=["json", "csv"], key="t_file")
        target_schema = parse_uploaded_target_schema(target_schema_file.read(), target_schema_file.name) if target_schema_file else None

with r_col:
    st.subheader("Optional Business Rules")
    enable_rules = st.checkbox("Enable / Upload Relational Business Rules", value=use_sample)
    custom_rules = None
    if enable_rules:
        sample_rules_path = os.path.join(SAMPLE_DIR, "sample_rules.json")
        if use_sample and os.path.exists(sample_rules_path):
            with open(sample_rules_path, "r") as rf:
                custom_rules = json.load(rf)
            st.info(f"Loaded {len(custom_rules)} sample business validation rules.")
        else:
            rules_file = st.file_uploader("Upload Business Rules Specification (.json)", type=["json"], key="r_file")
            if rules_file:
                custom_rules = json.loads(rules_file.read().decode("utf-8"))

st.markdown("---")

# ---------------------------------------------------------------------------
# Step 3: Run Engine
# ---------------------------------------------------------------------------
st.header("3️⃣ Run Migration Engine")
run_disabled = not (source_records and target_schema and api_key)

if st.button("🚀 Run Migration Engine", disabled=run_disabled, type="primary"):
    st.session_state.canonical = source_records

    with st.spinner("Evaluating business validation rules..."):
        anomalies = validate_records(source_records, custom_rules)
        st.session_state.anomalies = anomalies

    with st.spinner("Requesting AI schema mapping..."):
        try:
            mapping_spec = get_ai_mapping(ai_provider, api_key, source_records[0], target_schema)
            st.session_state.mapping_spec = mapping_spec
        except Exception as e:
            st.error(f"AI Mapping failed: {e}")

    if st.session_state.mapping_spec:
        with st.spinner("Applying target mapping..."):
            target_records = apply_mapping(source_records, st.session_state.mapping_spec, anomalies)
            st.session_state.target_records = target_records
        st.success("Migration complete!")

# ---------------------------------------------------------------------------
# Step 4: Reconciliation Workspace & Output
# ---------------------------------------------------------------------------
if st.session_state.canonical and st.session_state.target_records:
    canonical = st.session_state.canonical
    anomalies = st.session_state.anomalies
    target_records = st.session_state.target_records

    st.markdown("---")
    st.header("🛠️ Anomaly Reconciliation Workspace")
    if anomalies:
        rows = [{"record_id": rec_id, **issue} for rec_id, issues in anomalies.items() for issue in issues]
        st.dataframe(pd.DataFrame(rows), use_container_width=True)

        selected_rec = st.selectbox("Select Record ID to Reconcile", list(anomalies.keys()))
        if selected_rec is not None:
            active_rec = next((r for r in canonical if r.get("_record_id") == selected_rec or r.get("policy_number") == selected_rec), None)
            if active_rec:
                st.json(active_rec)
                c_field, c_val = st.columns(2)
                field_to_edit = c_field.selectbox("Select Field to Fix", [k for k in active_rec.keys() if not k.startswith("_")])
                new_val = c_val.text_input(f"New Value for {field_to_edit}", value=str(active_rec.get(field_to_edit, "")))

                c_act1, c_act2 = st.columns(2)
                if c_act1.button("Apply Field Override & Re-run Transformation"):
                    parsed_val = int(new_val) if new_val.isdigit() else new_val
                    update_record_field(canonical, selected_rec, field_to_edit, parsed_val)
                    st.session_state.anomalies = validate_records(canonical, custom_rules)
                    st.session_state.target_records = apply_mapping(canonical, st.session_state.mapping_spec, st.session_state.anomalies)
                    st.success("Updated field successfully!")
                    st.rerun()

                if c_act2.button("Force Approve / Clear Anomalies"):
                    resolve_anomaly(st.session_state.anomalies, selected_rec)
                    st.session_state.target_records = apply_mapping(canonical, st.session_state.mapping_spec, st.session_state.anomalies)
                    st.success("Record approved.")
                    st.rerun()
    else:
        st.success("🎉 All records are 100% clean!")

    st.markdown("---")
    st.header("📤 Export Target Output")
    e1, e2 = st.columns(2)
    with e1:
        st.download_button("Download Converted JSON", data=to_json_string(target_records), file_name="migrated_policies.json", mime="application/json")
    with e2:
        df_csv = flatten_for_csv(target_records)
        st.download_button("Download Flattened CSV", data=df_csv.to_csv(index=False), file_name="migrated_policies.csv", mime="text/csv")
