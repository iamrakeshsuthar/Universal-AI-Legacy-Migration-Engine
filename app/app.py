"""
app.py - Ultimate Universal Migration Engine
Features: Backend Secrets, ZIP Workspaces, PDF/NLP Rules GenAI, Interactive AI Reconciliation, Granular Exports.
"""

import sys
import os
import json
import streamlit as st
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))

from modules.generic_source_parser import parse_legacy_source
from modules.rule_engine import extract_rules_from_document, validate_records
from modules.reconciler import update_record_field, resolve_anomaly, get_ai_fix_suggestion
from modules.target_schema import SCHEMA_TEMPLATES
from modules.target_schema_upload import parse_uploaded_target_schema
from modules.mapping_router import get_ai_mapping
from modules.exporter import apply_mapping, to_json_string, flatten_for_csv, generate_migration_report, create_export_zip

st.set_page_config(page_title="Ultimate Migration Engine", layout="wide")

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "sample_data")

# ---------------------------------------------------------------------------
# Backend AI Configuration (Hidden from UI)
# ---------------------------------------------------------------------------
try:
    ai_provider = st.secrets.get("AI_PROVIDER", "Claude")
    if ai_provider == "Claude":
        api_key = st.secrets["ANTHROPIC_API_KEY"]
    else:
        api_key = st.secrets["GOOGLE_API_KEY"]
except KeyError:
    st.error("⚠️ Developer Notice: API Key or Provider not found. Please configure `.streamlit/secrets.toml`.")
    st.stop()

# Initialize Session State
for key in ["canonical", "anomalies", "mapping_spec", "target_records", "custom_rules", "raw_file_bytes"]:
    if key not in st.session_state:
        st.session_state[key] = None

st.title("🔄 Ultimate AI Legacy Migration & Reconciliation Engine")
st.caption("Universal Ingestion (ZIP, COBOL, JSON, CSV, PDF Rules) ➔ AI Mapping ➔ Interactive AI Reconciliation ➔ Granular Batch Export.")

with st.sidebar:
    st.header("⚙️ Configuration")
    use_sample = st.checkbox("Use bundled sample legacy dataset", value=False)
    st.markdown("---")
    st.caption(f"🔒 Authenticated via backend secrets. Active Provider: **{ai_provider}**.")

# ---------------------------------------------------------------------------
# Step 1: Universal Source Intake & Pre-flight Review
# ---------------------------------------------------------------------------
st.header("1️⃣ Universal Source Intake")

if use_sample:
    col1, col2 = st.columns(2)
    sample_policies = os.path.join(SAMPLE_DIR, "POLICIES.DAT")
    sample_cpy = os.path.join(SAMPLE_DIR, "POLICYREC.cpy")
    
    if os.path.exists(sample_policies) and os.path.exists(sample_cpy):
        with open(sample_policies, "rb") as f_dat, open(sample_cpy, "rb") as f_cpy:
            st.session_state.raw_file_bytes = f_dat.read()
            records, meta, extracted_rules_bytes = parse_legacy_source(
                st.session_state.raw_file_bytes, "POLICIES.DAT", f_cpy.read(), ai_provider, api_key
            )
            st.session_state.canonical = records
        col1.success("✅ Using bundled sample: POLICIES.DAT + POLICYREC.cpy")
        col2.info(f"Loaded {len(records)} records.")
        
        st.markdown("### 🔍 Pre-flight Data Review")
        tab1, tab2 = st.tabs(["📊 Parsed Structured Data", "📄 Raw File Content"])
        with tab1:
            st.dataframe(pd.DataFrame(records).head(50), use_container_width=True)
        with tab2:
            st.code(st.session_state.raw_file_bytes.decode('utf-8', errors='ignore')[:2000] + "\n\n...[TRUNCATED]")
else:
    col1, col2 = st.columns(2)
    with col1:
        src_file = st.file_uploader("Upload Workspace (.zip) or Data (.json, .csv, .dat, .txt, .xml, .xlsx)", key="src_file")
    with col2:
        schema_file = st.file_uploader("Upload Schema (.cpy) (Only if DAT uploaded)", key="schema_file")

    if src_file:
        ext = src_file.name.split('.')[-1].lower()
        
        # Wait for Copybook schema if a DAT file is uploaded to prevent errors
        if ext in ['dat', 'txt'] and not schema_file:
            st.info("ℹ️ Fixed-width file detected. Please upload the matching Copybook schema (.cpy) in the second box to continue.")
        else:
            try:
                s_bytes = schema_file.read() if schema_file else None
                st.session_state.raw_file_bytes = src_file.getvalue()
                
                records, meta, extracted_rules_bytes = parse_legacy_source(
                    st.session_state.raw_file_bytes, src_file.name, s_bytes, ai_provider, api_key
                )
                st.session_state.canonical = records
                
                if extracted_rules_bytes:
                    st.session_state.custom_rules = extract_rules_from_document(extracted_rules_bytes, "rule.txt", ai_provider, api_key)
                    st.success("✅ Extracted Data AND Business Rules from ZIP Workspace!")
                else:
                    st.success(f"✅ Parsed {len(records)} records from {src_file.name}!")
                    
                st.markdown("### 🔍 Pre-flight Data Review")
                tab1, tab2 = st.tabs(["📊 Parsed Structured Data", "📄 Raw File Content"])
                with tab1:
                    st.dataframe(pd.DataFrame(records).head(50), use_container_width=True)
                with tab2:
                    # For zips or excel, raw bytes text preview might not be readable, so we wrap in a try-except
                    try:
                        st.code(st.session_state.raw_file_bytes.decode('utf-8')[:2000] + "\n\n...[TRUNCATED]")
                    except UnicodeDecodeError:
                        st.info("Raw binary file uploaded (e.g. ZIP or XLSX). Preview available in Parsed Data tab.")
                    
            except Exception as e:
                st.error(f"Ingestion Error: {str(e)}")

st.markdown("---")

# ---------------------------------------------------------------------------
# Step 2: Target Schema Hub & NLP Rule Extraction
# ---------------------------------------------------------------------------
st.header("2️⃣ Schema Hub & Business Rules")
t_col, r_col = st.columns(2)

with t_col:
    st.subheader("Target PAS Schema")
    schema_choice = st.selectbox("Select Target Schema Template", list(SCHEMA_TEMPLATES.keys()) + ["Upload Custom Schema"])
    
    if schema_choice == "Upload Custom Schema":
        t_file = st.file_uploader("Upload Target Schema (.json, .csv)", key="t_file")
        target_schema = parse_uploaded_target_schema(t_file.read(), t_file.name) if t_file else None
    else:
        target_schema = SCHEMA_TEMPLATES[schema_choice]
        with st.expander("Preview Target Template Structure"):
            st.dataframe(pd.DataFrame(target_schema))

with r_col:
    st.subheader("Business Rules (NLP / PDF Support)")
    
    if use_sample:
        sample_rules_path = os.path.join(SAMPLE_DIR, "sample_rules.json")
        if os.path.exists(sample_rules_path):
            with open(sample_rules_path, "r") as rf:
                st.session_state.custom_rules = json.load(rf)
            st.success(f"Loaded {len(st.session_state.custom_rules)} sample business rules.")
    else:
        rule_file = st.file_uploader("Upload Rules Manual (.pdf, .txt, .md, .json)", key="r_file")
        
        if rule_file and not st.session_state.custom_rules:
            with st.spinner("🤖 AI is reading your policy document to extract JSON rules..."):
                if rule_file.name.endswith(".json"):
                    st.session_state.custom_rules = json.loads(rule_file.read().decode('utf-8'))
                else:
                    st.session_state.custom_rules = extract_rules_from_document(rule_file.read(), rule_file.name, ai_provider, api_key)
        
    if st.session_state.custom_rules:
        st.success(f"Loaded {len(st.session_state.custom_rules)} active business validation rules.")
        with st.expander("View Active Rules"):
            st.json(st.session_state.custom_rules)

st.markdown("---")

# ---------------------------------------------------------------------------
# Step 3: Run Engine
# ---------------------------------------------------------------------------
st.header("3️⃣ Execute AI Migration Engine")
run_ready = st.session_state.canonical and target_schema and api_key

if st.button("🚀 Run Complete Migration", disabled=not run_ready, type="primary"):
    with st.spinner("Validating records against business rules..."):
        st.session_state.anomalies = validate_records(st.session_state.canonical, st.session_state.custom_rules)

    with st.spinner(f"{ai_provider} is mapping canonical source to target PAS schema..."):
        try:
            st.session_state.mapping_spec = get_ai_mapping(ai_provider, api_key, st.session_state.canonical[0], target_schema)
            
            with st.spinner("Applying schema transformation deterministically..."):
                st.session_state.target_records = apply_mapping(st.session_state.canonical, st.session_state.mapping_spec, st.session_state.anomalies)
                st.success("✅ AI Mapping and Data Transformation Complete!")
                
        except Exception as e:
            st.error(f"AI Mapping failed: {str(e)}")

# ---------------------------------------------------------------------------
# Step 4: AI-Assisted Reconciliation Workspace
# ---------------------------------------------------------------------------
if st.session_state.target_records:
    st.markdown("---")
    st.header("🛠️ AI-Assisted Reconciliation Workspace")
    
    anomalies = st.session_state.anomalies
    if anomalies:
        st.warning(f"⚠️ {len(anomalies)} record(s) flagged for review.")
        rec_ids = list(anomalies.keys())
        selected_rec = st.selectbox("Select Quarantined Record to Inspect", rec_ids)
        
        if selected_rec is not None:
            active_rec = next((r for r in st.session_state.canonical if r.get("_record_id") == selected_rec or r.get("policy_number") == selected_rec), None)
            issues = anomalies[selected_rec]
            
            st.write("**Flagged Rule Violations:**")
            for iss in issues: 
                st.error(f"[{iss['severity'].upper()}] {iss.get('rule_id', 'RULE')}: {iss['message']}")
            
            # Ask AI for Suggestion Feature
            if st.button("✨ Ask AI for Fix Suggestion"):
                with st.spinner(f"Asking {ai_provider} to analyze the violation..."):
                    suggestion = get_ai_fix_suggestion(active_rec, issues[0], ai_provider, api_key)
                    st.info(f"**AI Suggestion:** {suggestion}")

            st.write("**Edit Record Data:**")
            c_f, c_v = st.columns(2)
            field_edit = c_f.selectbox("Field to Override", [k for k in active_rec.keys() if not str(k).startswith("_")])
            new_val = c_v.text_input("New Value", value=str(active_rec.get(field_edit, "")))

            c_act1, c_act2 = st.columns(2)
            if c_act1.button("💾 Apply Fix & Re-Validate"):
                # Attempt to preserve numbers as int/float
                val_to_save = new_val
                if new_val.isdigit():
                    val_to_save = int(new_val)
                else:
                    try: val_to_save = float(new_val)
                    except ValueError: pass

                update_record_field(st.session_state.canonical, selected_rec, field_edit, val_to_save)
                
                # Re-validate and remap
                st.session_state.anomalies = validate_records(st.session_state.canonical, st.session_state.custom_rules)
                st.session_state.target_records = apply_mapping(st.session_state.canonical, st.session_state.mapping_spec, st.session_state.anomalies)
                st.rerun()

            if c_act2.button("✅ Force Approve (Ignore Rule)"):
                resolve_anomaly(st.session_state.anomalies, selected_rec)
                st.session_state.target_records = apply_mapping(st.session_state.canonical, st.session_state.mapping_spec, st.session_state.anomalies)
                st.rerun()
    else:
        st.success("🎉 All records passed business validation perfectly! No quarantine items.")

# ---------------------------------------------------------------------------
# Step 5: Granular Batch Exports & Reporting
# ---------------------------------------------------------------------------
    st.markdown("---")
    st.header("📤 Granular Batch Exports & Reporting")
    
    total = len(st.session_state.target_records)
    flagged = len(st.session_state.anomalies)
    clean = total - flagged
    
    # Split records into clean and quarantined
    clean_recs = [r for r in st.session_state.target_records if not r.get("metadata", {}).get("anomalyFlags")]
    quarantine_recs = [r for r in st.session_state.target_records if r.get("metadata", {}).get("anomalyFlags")]
    
    # Generate Report
    report_md = generate_migration_report(total, clean, flagged, st.session_state.mapping_spec)
    
    st.markdown("### Migration Summary")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Records", total)
    c2.metric("Clean Records ✅", clean)
    c3.metric("Quarantined ⚠️", flagged)

    # Download Buttons
    st.markdown("### Download Assets")
    btn1, btn2, btn3, btn4 = st.columns(4)
    
    with btn1:
        st.download_button("📦 Export ALL (JSON)", to_json_string(st.session_state.target_records), "all_records.json")
    with btn2:
        st.download_button("✅ Export Clean Only", to_json_string(clean_recs), "clean_records.json", disabled=not clean_recs)
    with btn3:
        st.download_button("⚠️ Export Quarantined", to_json_string(quarantine_recs), "quarantined_records.json", disabled=not quarantine_recs)
    with btn4:
        zip_bytes = create_export_zip(clean_recs, quarantine_recs, report_md)
        st.download_button("🗂️ Download Full Batch ZIP", zip_bytes, "migration_batch_export.zip", mime="application/zip")
