# Universal AI Legacy Policy Migration Engine (v2)

**Quantum Shift AI Practitioner+ Capstone Project**

Converts legacy insurance policy records across ANY source format (COBOL `.DAT`, JSON, CSV, XML, Excel) into a modern cloud-native PAS (Policy Administration System) JSON schema—using Claude or Gemini for field mapping, an optional relational business rule engine, and an interactive anomaly reconciliation workspace.

## Features
1. **Universal Source Support**: Parse COBOL copybooks, CSVs, JSON, XML, or Excel spreadsheets.
2. **Optional Relational Business Rules**: Upload custom JSON rules or bypass rules for 100% clean auto-conversion.
3. **AI Field Mapping**: Claude or Gemini proposes structural mapping decisions once per batch.
4. **Interactive Anomaly Reconciliation**: Live Streamlit workspace to view flagged anomalies, override field values, and manually resolve warnings before export.

> This is a one-week capstone prototype, not a production system — see
> `CLAUDE.md` for the scope/design constraints and `AI_DEVELOPMENT_LOG.md`
> for the stage-by-stage build history and known limitations.

## Run it (Streamlit Community Cloud — no local install)

1. Push this repo to GitHub (via the GitHub web UI — see
   `GITHUB_PUSH_INSTRUCTIONS.md` if you're starting from the zip export).
2. On [share.streamlit.io](https://share.streamlit.io), create a new app
   pointing at this repo, branch `main`, main file path `app/app.py`.
3. In the app's **Settings → Secrets**, paste in:
   ```toml
   AI_PROVIDER = "Gemini"        # or "Claude"
   GOOGLE_API_KEY = "..."        # required if AI_PROVIDER = "Gemini"
   ANTHROPIC_API_KEY = "sk-ant-..."  # required if AI_PROVIDER = "Claude"
   ```
   (see `.streamlit/secrets.toml.example` for the full template). Secrets
   are entered directly in the Streamlit Cloud app manager — never commit
   a real `secrets.toml` file.
4. Deploy. Dependencies are installed automatically from
   `app/requirements.txt`.

To try it without uploading your own files, check **"Use bundled sample
legacy dataset"** in the sidebar once the app is running — this loads the
COBOL fixed-width sample data under `app/sample_data/`.

### Run in GitHub Codespaces

Opening this repo in a Codespace uses `.devcontainer/devcontainer.json`,
which installs `app/requirements.txt` and runs
`streamlit run app/app.py` automatically — useful for testing in-browser
before deploying to Streamlit Community Cloud.
