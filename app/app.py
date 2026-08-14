# ---------------------------------------------------------------------------
# Step 4: AI-Assisted Reconciliation Workspace (Side-by-Side Comparison)
# ---------------------------------------------------------------------------
if st.session_state.target_records:
    st.markdown("---")
    st.header("🛠️ AI-Assisted Reconciliation Workspace")
    
    anomalies = st.session_state.anomalies
    if anomalies:
        st.warning(f"⚠️ {len(anomalies)} record(s) flagged for review and quarantine.")
        rec_ids = list(anomalies.keys())
        selected_rec = st.selectbox("Select Quarantined Record ID to Inspect", rec_ids)
        
        if selected_rec is not None:
            active_rec = next((r for r in st.session_state.canonical if r.get("_record_id") == selected_rec or r.get("policy_number") == selected_rec), None)
            issues = anomalies[selected_rec]
            
            st.subheader("⚠️ Flagged Rule Violations for this Record")
            for iss in issues: 
                st.error(f"[{iss.get('severity', 'error').upper()}] **{iss.get('rule_id', 'RULE')}**: {iss['message']}")
            
            st.markdown("---")
            st.subheader("🔍 Side-by-Side Data Comparison & Reconciliation")
            st.caption("Review the original values versus current working values. You can update any field below or ask AI for a smart recommendation.")

            # Prepare comparison view data
            display_fields = [k for k in active_rec.keys() if not str(k).startswith("_")]
            
            # AI Suggestion Box integration
            if st.button("✨ Ask AI for Fix Suggestion"):
                with st.spinner(f"Asking {ai_provider} to analyze the record and rule violation..."):
                    suggestion = get_ai_fix_suggestion(active_rec, issues[0], ai_provider, api_key)
                    st.info(f"**🤖 AI Recommendation:** {suggestion}")

            # Build an interactive form for row-wide or field-by-field updates
            with st.form(key=f"reconcile_form_{selected_rec}"):
                updated_values = {}
                
                # Display headers for side-by-side comparison
                col_h1, col_h2, col_h3 = st.columns([2, 2, 3])
                col_h1.markdown("**Field Name**")
                col_h2.markdown("**Original Value (Legacy)**")
                col_h3.markdown("**Reconciled Value (Editable)**")
                
                for field in display_fields:
                    orig_val = active_rec.get(field)
                    c1, c2, c3 = st.columns([2, 2, 3])
                    c1.text(field)
                    c2.text(str(orig_val))
                    
                    # Render text input pre-filled with current value for editing
                    new_val_input = c3.text_input(f"edit_{field}", value=str(orig_val if orig_val is not None else ""), label_visibility="collapsed")
                    updated_values[field] = new_val_input

                st.markdown("---")
                col_btn1, col_btn2 = st.columns(2)
                submit_changes = col_btn1.form_submit_button("💾 Save Changes & Re-Validate Record", type="primary")
                approve_record = col_btn2.form_submit_button("✅ Force Approve Record (Clear Anomalies)")

                if submit_changes:
                    # Apply all modified fields back to the active record
                    for field, val in updated_values.items():
                        # Type coercion guard
                        parsed_val = val
                        if val.isdigit():
                            parsed_val = int(val)
                        else:
                            try:
                                parsed_val = float(val)
                            except ValueError:
                                pass
                        update_record_field(st.session_state.canonical, selected_rec, field, parsed_val)

                    # Re-run rule validation and mapping transformation
                    st.session_state.anomalies = validate_records(st.session_state.canonical, st.session_state.custom_rules)
                    st.session_state.target_records = apply_mapping(st.session_state.canonical, st.session_state.mapping_spec, st.session_state.anomalies)
                    st.success("✅ Record successfully updated and re-validated!")
                    st.rerun()

                if approve_record:
                    resolve_anomaly(st.session_state.anomalies, selected_rec)
                    st.session_state.target_records = apply_mapping(st.session_state.canonical, st.session_state.mapping_spec, st.session_state.anomalies)
                    st.success("✅ Record manually approved and moved to clean output.")
                    st.rerun()
    else:
        st.success("🎉 All records passed business validation perfectly! No quarantine items.")
