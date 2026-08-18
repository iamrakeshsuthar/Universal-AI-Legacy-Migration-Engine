"""
app.py - Ultimate Universal Migration Engine
Features: Backend Secrets, ZIP Workspaces, PDF/NLP Rules GenAI, Interactive AI Reconciliation, Granular Exports.
"""

import sys
import os
import json
import re
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
# Helper Functions
# ---------------------------------------------------------------------------
def sanitize_error(error_obj):
    """Scrubs specific provider names from error strings to anonymize the AI."""
    msg = str(error_obj)
    terms_to_hide = ["Gemini", "Claude", "Anthropic", "Google", "genai"]
    for term in terms_to_hide:
        msg = re.sub(term, "AI Engine", msg, flags=re.IGNORECASE)
    return msg

# ---------------------------------------------------------------------------
# Backend AI Configuration (Hidden from UI)
# ---------------------------------------------------------------------------
try:
    ai_provider = st.secrets.get("AI_PROVIDER", "Claude")
    if ai_provider == "Claude":
        api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
    else:
        api_key = st.secrets.get("GOOGLE_API_KEY", "")
except KeyError:
    st.error("⚠️ Developer Notice: API Key or Provider not found. Please configure `.streamlit/secrets.toml`.")
    st.stop()

# ---------------------------------------------------------------------------
# State Management Initialization
# ---------------------------------------------------------------------------
state_keys = ["canonical", "anomalies", "mapping_spec", "target_records", "custom_rules", "raw_file_bytes", "target_schema", "schema_choice"]
for key in state_keys:
    if key not in st.session_state:
        st.session_state[key] = None

# Stepper variables
if "current_step" not in st.session_state:
    st.session_state.current_step = 1
if "highest_step_reached" not in st.session_state:
    st.session_state.highest_step_reached = 1

# Navigation Callbacks
def go_next():
    st.session_state.current_step += 1
    st.session_state.highest_step_reached = max(st.session_state.highest_step_reached, st.session_state.current_step)

def go_prev():
    st.session_state.current_step -= 1

def jump_to(step):
    st.session_state.current_step = step

# ---------------------------------------------------------------------------
# Sidebar & Header UI
# ---------------------------------------------------------------------------
st.title("🔄 AI Legacy Migration Workbench")
st.caption("A working prototype: AI-assisted field mapping, automated anomaly detection, and human-in-the-loop exception review.")

with st.sidebar:
    st.header("⚙️ Configuration")
    use_sample = st.checkbox("Use bundled sample legacy dataset", value=False)
    st.markdown("---")
    # Anonymized sidebar status
    st.caption("🔒 Authenticated via backend secrets. AI Engine: **Active**.")

# ---------------------------------------------------------------------------
# Milestone Visual Stepper
# ---------------------------------------------------------------------------
steps = ["1️⃣ Load Data", "2️⃣ Configuration", "3️⃣ AI Engine", "4️⃣ Reconciliation", "5️⃣ Export"]
cols = st.columns(len(steps))

for i, step_label in enumerate(steps):
    step_num = i + 1
    
    # Determine styling based on milestone state
    if step_num == st.session_state.current_step:
        # Active Step - Light Blue
        bg_color = "#e0f7fa"
        border = "2px solid #00838f"
        text_color = "#00838f"
        font_weight = "bold"
    elif step_num <= st.session_state.highest_step_reached:
        # Completed Step - Light Green
        bg_color = "#d4edda"
        border = "1px solid #c3e6cb"
        text_color = "#155724"
        font_weight = "normal"
    else:
        # Locked Future Step - Gray
        bg_color = "transparent"
        border = "1px dashed #e0e0e0"
        text_color = "#bdbdbd"
        font_weight = "normal"

    # Render a uniform Flexbox container for perfect alignment
    with cols[i]:
        st.markdown(f"""
        <div style='
            height: 42px; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            background-color: {bg_color}; 
            border: {border}; 
            border-radius: 6px; 
            color: {text_color}; 
            font-weight: {font_weight};
            font-size: 14px;
            margin-bottom: 5px;
        '>
            {step_label}
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# ===========================================================================
# STEP 1: SOURCE INTAKE
# ===========================================================================
if st.session_state.current_step == 1:
    st.header("Step 1 — Load Legacy Policy Data")
    st.markdown("Load a synthetic batch (including deliberately dirty records) or upload your own structured files.")
    
    if st.session_state.canonical is not None:
        st.success(f"✅ Data loaded successfully! ({len(st.session_state.canonical)} records ready for processing).")
        
        tab1, tab2 = st.tabs(["📊 Parsed Structured Data", "📄 Raw File Content"])
        with tab1:
            st.dataframe(pd.DataFrame(st.session_state.canonical).head(50), use_container_width=True)
        with tab2:
            try:
                st.code(st.session_state.raw_file_bytes.decode('utf-8')[:2000] + "\n\n...[TRUNCATED]")
            except:
                st.info("Raw binary file uploaded. Preview available in Parsed Data tab.")
                
        if st.button("🗑️ Clear and Upload New Data"):
            st.session_state.canonical = None
            st.session_state.raw_file_bytes = None
            st.session_state.highest_step_reached = 1
            st.rerun()
            
    else:
        if use_sample:
            sample_policies = os.path.join(SAMPLE_DIR, "POLICIES.DAT")
            sample_cpy = os.path.join(SAMPLE_DIR, "POLICYREC.cpy")
            
            if os.path.exists(sample_policies) and os.path.exists(sample_cpy):
                with open(sample_policies, "rb") as f_dat, open(sample_cpy, "rb") as f_cpy:
                    st.session_state.raw_file_bytes = f_dat.read()
                    records, meta, ext_rules = parse_legacy_source(st.session_state.raw_file_bytes, "POLICIES.DAT", f_cpy.read(), ai_provider, api_key)
                    st.session_state.canonical = records
                st.rerun()
        else:
            col1, col2 = st.columns(2)
            with col1:
                src_file = st.file_uploader("Upload Workspace (.zip) or Data (.json, .csv, .dat)", key="src_file")
            with col2:
                schema_file = st.file_uploader("Upload Schema (.cpy) (Only if DAT uploaded)", key="schema_file")

            if src_file:
                ext = src_file.name.split('.')[-1].lower()
                if ext in ['dat', 'txt'] and not schema_file:
                    st.info("ℹ️ Fixed-width file detected. Please upload the matching Copybook schema (.cpy) in the second box to continue.")
                else:
                    try:
                        s_bytes = schema_file.read() if schema_file else None
                        st.session_state.raw_file_bytes = src_file.getvalue()
                        records, meta, extracted_rules_bytes = parse_legacy_source(st.session_state.raw_file_bytes, src_file.name, s_bytes, ai_provider, api_key)
                        st.session_state.canonical = records
                        
                        if extracted_rules_bytes:
                            st.session_state.custom_rules = extract_rules_from_document(extracted_rules_bytes, "rule.txt", ai_provider, api_key)
                        st.rerun()
                    except Exception as e:
                        # Anonymized error
                        st.error(f"Ingestion Error: {sanitize_error(e)}")

    st.markdown("---")
    _, right_col = st.columns([8, 2])
    if st.session_state.canonical:
        st.session_state.highest_step_reached = max(st.session_state.highest_step_reached, 2)
        with right_col:
            st.button("Next: Configuration ➡️", on_click=go_next, type="primary", use_container_width=True)

# ===========================================================================
# STEP 2: CONFIGURATION (SCHEMA & RULES)
# ===========================================================================
elif st.session_state.current_step == 2:
    st.header("Step 2 — Schema Hub & Business Rules")
    t_col, r_col = st.columns(2)

    with t_col:
        st.subheader("Target PAS Schema")
        
        # Persist dropdown selection
        schema_options = list(SCHEMA_TEMPLATES.keys()) + ["Upload Custom Schema"]
        current_index = schema_options.index(st.session_state.schema_choice) if st.session_state.schema_choice in schema_options else 0
        
        schema_choice = st.selectbox("Select Target Schema Template", schema_options, index=current_index)
        st.session_state.schema_choice = schema_choice
        
        if schema_choice == "Upload Custom Schema":
            t_file = st.file_uploader("Upload Target Schema (.json, .csv)", key="t_file")
            if t_file:
                st.session_state.target_schema = parse_uploaded_target_schema(t_file.read(), t_file.name)
        else:
            st.session_state.target_schema = SCHEMA_TEMPLATES[schema_choice]
            with st.expander("Preview Target Template Structure"):
                st.dataframe(pd.DataFrame(st.session_state.target_schema))

    with r_col:
        st.subheader("Business Rules (NLP / PDF Support)")
        
        if st.session_state.custom_rules:
            st.success(f"Loaded {len(st.session_state.custom_rules)} active business validation rules.")
            with st.expander("View Active Rules"):
                st.json(st.session_state.custom_rules)
            if st.button("🗑️ Clear Rules"):
                st.session_state.custom_rules = None
                st.rerun()
        else:
            if use_sample:
                sample_rules_path = os.path.join(SAMPLE_DIR, "sample_rules.json")
                if os.path.exists(sample_rules_path):
                    if st.button("Load Sample Rules"):
                        with open(sample_rules_path, "r") as rf:
                            st.session_state.custom_rules = json.load(rf)
                        st.rerun()
            else:
                rule_file = st.file_uploader("Upload Rules Manual (.pdf, .txt, .json)", key="r_file")
                if rule_file:
                    with st.spinner("🤖 The AI Engine is reading your policy document to extract JSON rules..."):
                        try:
                            if rule_file.name.endswith(".json"):
                                st.session_state.custom_rules = json.loads(rule_file.read().decode('utf-8'))
                            else:
                                st.session_state.custom_rules = extract_rules_from_document(rule_file.read(), rule_file.name, ai_provider, api_key)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Rule Extraction Error: {sanitize_error(e)}")

    st.markdown("---")
    left_col, _, right_col = st.columns([2, 6, 2])
    with left_col:
        st.button("⬅️ Back", on_click=go_prev, use_container_width=True)
    
    if st.session_state.target_schema:
        st.session_state.highest_step_reached = max(st.session_state.highest_step_reached, 3)
        with right_col:
            st.button("Next: AI Engine ➡️", on_click=go_next, type="primary", use_container_width=True)

# ===========================================================================
# STEP 3: RUN ENGINE
# ===========================================================================
elif st.session_state.current_step == 3:
    st.header("Step 3 — Execute AI Migration Engine")
    st.markdown("Map the canonical source to the target PAS schema and validate records against business rules.")
    
    run_ready = st.session_state.canonical and st.session_state.target_schema and api_key

    if st.button("🚀 Run Complete Migration", disabled=not run_ready, type="primary"):
        with st.spinner("Validating records against business rules..."):
            st.session_state.anomalies = validate_records(st.session_state.canonical, st.session_state.custom_rules)

        with st.spinner("The AI Engine is mapping the canonical source to the target PAS schema..."):
            try:
                st.session_state.mapping_spec = get_ai_mapping(ai_provider, api_key, st.session_state.canonical[0], st.session_state.target_schema)
                
                with st.spinner("Applying schema transformation deterministically..."):
                    st.session_state.target_records = apply_mapping(st.session_state.canonical, st.session_state.mapping_spec, st.session_state.anomalies)
                    
                    st.session_state.highest_step_reached = max(st.session_state.highest_step_reached, 4)
                    st.session_state.current_step = 4
                    st.rerun()
            except Exception as e:
                st.error(f"AI Mapping failed: {sanitize_error(e)}")
                
    if st.session_state.target_records:
        st.success("✅ Migration engine has run successfully! You can proceed to Review & Reconciliation.")

    st.markdown("---")
    left_col, _, right_col = st.columns([2, 6, 2])
    with left_col:
        st.button("⬅️ Back", on_click=go_prev, use_container_width=True)
    if st.session_state.target_records:
        with right_col:
            st.button("Next: Reconciliation ➡️", on_click=go_next, type="primary", use_container_width=True)

# ===========================================================================
# STEP 4: RECONCILIATION
# ===========================================================================
elif st.session_state.current_step == 4:
    st.header("Step 4 — AI-Assisted Reconciliation Workspace")
    
    if st.session_state.target_records:
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
                
                if st.button("✨ Ask AI for Fix Suggestion"):
                    with st.spinner("Asking the AI Engine to analyze the violation(s)..."):
                        try:
                            suggestion = get_ai_fix_suggestion(active_rec, issues, ai_provider, api_key)
                            st.info(f"**AI Suggestion:** {sanitize_error(suggestion)}")
                        except Exception as e:
                            st.error(f"Failed to generate suggestion: {sanitize_error(e)}")

                st.write("**Edit Record Data (Entire Row):**")
                editable_data = {k: v for k, v in active_rec.items() if not str(k).startswith("_")}
                edited_json_str = st.text_area("Update JSON to fix the record", value=json.dumps(editable_data, indent=2, default=str), height=300)

                c_act1, c_act2 = st.columns(2)
                if c_act1.button("💾 Apply Fix & Re-Validate"):
                    try:
                        updated_data = json.loads(edited_json_str)
                        for r in st.session_state.canonical:
                            if r.get("_record_id") == selected_rec or r.get("policy_number") == selected_rec:
                                for k, v in updated_data.items(): r[k] = v
                                break
                        st.session_state.anomalies = validate_records(st.session_state.canonical, st.session_state.custom_rules)
                        st.session_state.target_records = apply_mapping(st.session_state.canonical, st.session_state.mapping_spec, st.session_state.anomalies)
                        st.rerun()
                    except json.JSONDecodeError:
                        st.error("⚠️ Invalid JSON format. Please ensure your edits maintain valid JSON structure before applying.")

                if c_act2.button("✅ Force Approve (Ignore Rule)"):
                    resolve_anomaly(st.session_state.anomalies, selected_rec)
                    st.session_state.target_records = apply_mapping(st.session_state.canonical, st.session_state.mapping_spec, st.session_state.anomalies)
                    st.rerun()
        else:
            st.success("🎉 All records passed business validation perfectly! No quarantine items.")

    st.markdown("---")
    left_col, _, right_col = st.columns([2, 6, 2])
    with left_col:
        st.button("⬅️ Back", on_click=go_prev, use_container_width=True)
    
    st.session_state.highest_step_reached = max(st.session_state.highest_step_reached, 5)
    with right_col:
        st.button("Next: Export ➡️", on_click=go_next, type="primary", use_container_width=True)

# ===========================================================================
# STEP 5: EXPORT
# ===========================================================================
elif st.session_state.current_step == 5:
    st.header("Step 5 — Granular Batch Exports & Reporting")
    
    if st.session_state.target_records:
        total = len(st.session_state.target_records)
        flagged = len(st.session_state.anomalies)
        clean = total - flagged
        
        clean_recs = [r for r in st.session_state.target_records if not r.get("metadata", {}).get("anomalyFlags")]
        quarantine_recs = [r for r in st.session_state.target_records if r.get("metadata", {}).get("anomalyFlags")]
        report_md = generate_migration_report(total, clean, flagged, st.session_state.mapping_spec)
        
        st.markdown("### Migration Summary")
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Records", total)
        c2.metric("Clean Records ✅", clean)
        c3.metric("Quarantined ⚠️", flagged)

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
    else:
        st.info("No data available to export. Please run the migration engine first.")

    st.markdown("---")
    left_col, _, _ = st.columns([2, 6, 2])
    with left_col:
        st.button("⬅️ Back", on_click=go_prev, use_container_width=True)
