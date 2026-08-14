"""
app.py - Ultimate Universal Migration Engine
Features: ZIP Workspaces, PDF/NLP Rules GenAI, Interactive AI Reconciliation, Granular Exports.
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
    use_sample = st.checkbox("Use bundled sample legacy dataset", value=True)
    st.markdown("---")
    st.caption("🔒 AI Engine and Authentication are managed securely via backend configurations.")

# ---------------------------------------------------------------------------
# Step 1: Universal Source Intake & Pre-flight Review
# ---------------------------------------------------------------------------
# ... [The rest of your app.py code remains exactly the same from this point down] ...
