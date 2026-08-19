# AI Development Log

**Deliverable 4: AI prompts, instructions, and configuration files used
during development.**

This project was built through an AI-assisted development workflow (Claude
acting as an in-IDE / Claude Code–style pair programmer). `CLAUDE.md`
captures the standing instructions given before development started. This
log captures the actual prompt sequence used at each subsequent stage —
scoping, feature builds, bug fixes, and UI changes — in the order they
happened, along with what Claude produced and how it was verified.

---

## Stage 0 — Problem scoping

**Prompt:**
> "Legacy policy systems and historical data block digital transformation
> and cloud modernization. Manual migration is slow, expensive,
> error-prone, and high risk for business continuity... This engine
> enables accelerated, error-free policy conversion, reduced migration
> cost, faster modernization cycles, and seamless transition to
> cloud-native PAS."

**Outcome:** Claude proposed narrowing the use case to a single concrete
slice — an **AI-powered Policy Record Mapper & Validator** — rather than
attempting full end-to-end PAS migration, and mapped the use case onto the
required 5-slide narrative structure (context, gaps, vision, solution,
business flow) before any code was written.

---

## Stage 1 — Architecture decision & constraint-driven stack selection

**Prompt:**
> "I want cloud based app, no need to install local dependencies during
> dev as this requires admin permission."

**Outcome:** Claude revised the stack to remove NeonDB and any local
setup step, settling on: Streamlit (frontend+backend in one file), Claude
API, no database for v1, Streamlit Community Cloud for hosting, deployed
via GitHub's web UI. This decision is recorded in `CLAUDE.md` and held for
the rest of the project.

**Clarifying questions asked back to the developer** (via structured
elicitation rather than assumptions):
- Persistence: NeonDB vs. in-session only? → **in-session only**
- Sample data: AI-generated vs. developer-supplied? → **developer-supplied**
- Target schema: fixed vs. user-uploadable? → **user-uploadable**

---

## Stage 2 — Legacy source inspection (before writing any parser code)

**Instruction:** Before generating a schema, Claude was pointed at the
developer's actual legacy codebase (a real COBOL/PL·I/JCL mainframe
export: copybooks, programs, and fixed-width data files) rather than
inventing a synthetic schema.

**Prompts (sequential, exploratory):**
> "view copybooks/POLICYREC.cpy"
> "view copybooks/CLAIMREC.cpy"
> "view cobol/POLCNCL.cbl"
> "view pli/POLVAL.pli"
> "view cobol/CLMPROC.cbl"
> "inspect POLICIES.DAT / CLAIMS.DAT line lengths and record counts"

**Outcome:** Claude extracted the real fixed-width record layout (90-byte
policy records, 91-byte claim records) and — critically — three genuine
embedded business rules that became the spec for the validation engine:
1. Claim amount cannot exceed policy coverage (`CLMPROC.cbl`)
2. A policy cannot be cancelled while it has a pending claim (`POLCNCL.cbl`)
3. High-risk vehicles / high coverage carry a premium surcharge
   (`POLVAL.pli`)

This turned "build a migration tool" into "build a tool that provably
preserves the legacy system's real business logic" — a stronger and more
auditable story than a generic field-renaming demo.

---

## Stage 3 — Schema Detector (copybook parser)

**Prompt:**
> "Build a copybook parser that reads a COBOL .cpy file and infers field
> name, PIC type (numeric / decimal with implied places / alphanumeric),
> length, and byte offset for each field, without hardcoding positions."

**Outcome:** `modules/copybook_parser.py` — regex-based PIC clause parser
producing a structured `CopybookSchema`.

**Verification prompt (same turn):**
> "Test this against the real POLICYREC.cpy and CLAIMREC.cpy files before
> moving on."

Claude ran the parser against both real copybooks and confirmed the
inferred byte offsets summed correctly (90 and 91 bytes respectively)
before proceeding — catching layout errors before they could propagate
into the data parser.

---

## Stage 4 — Fixed-width data decoder

**Prompt:**
> "Build a fixed-width file parser that decodes records using that
> inferred schema, correctly handling COBOL implied-decimal fields (e.g.
> 9(7)V99 stored as 9 raw digits with the decimal point implied 2 places
> from the right)."

**Outcome:** `modules/fixed_width_parser.py`, tested against the real
`POLICIES.DAT` (114 records) and `CLAIMS.DAT` (50 records) — confirmed
correct decoding of a sample record before continuing (e.g.
`0040746000` → `40746.00`).

---

## Stage 5 — Deterministic business-rule validator

**Prompt:**
> "From the legacy COBOL/PL·I source (POLCNCL.cbl, CLMPROC.cbl,
> POLVAL.pli), extract the real business rules and implement them as a
> deterministic validation engine — not hardcoded synthetic rules."

**Outcome:** `modules/validator.py`, implementing the three rules found
in Stage 2 as explicit, named, testable functions (`CLAIM_EXCEEDS_COVERAGE`,
`CANCELLED_WITH_PENDING_CLAIM`, `SURCHARGE_APPLICABLE`), each tagged with
its legacy source file in the docstring for auditability.

**Verification prompt:**
> "Run the validator against the real canonical policy set and show me
> actual anomaly counts, not placeholder numbers."

Result: 8 real cancellation-rule violations and 88 real surcharge flags
found in the sample data — used later as the metrics on the presentation
slides.

---

## Stage 6 — AI field-mapping module (the one place the LLM touches data decisions)

**System prompt** (used verbatim at runtime, in both the Claude and later
the Gemini implementation):

```
You are a data migration mapping assistant for an insurance policy
administration system (PAS) modernization project.

You will be given:
1. A list of canonical source fields (with example values) coming from a
legacy mainframe system.
2. A target schema (field name, type, description) for a modern
cloud-native PAS.

Your job: propose a mapping from each canonical source field to the
best-fit target field. For nested/array target fields (like
claims[].amount), map the corresponding canonical sub-field.

Respond with ONLY a JSON array, no prose, no markdown fences. Each
element:
{
  "source_field": "<canonical field name>",
  "target_field": "<target field path>",
  "confidence": "high" | "medium" | "low",
  "notes": "<short note on transformation or ambiguity, or empty string>"
}

If a canonical field has no reasonable target match, still include it
with target_field set to "UNMAPPED" and a note explaining why. If a
target field has no clear canonical source, do not invent a mapping
for it.
```

**Development prompt:**
> "Build an AI mapping module that asks Claude for a structured JSON
> mapping from canonical fields to an arbitrary target schema, so it
> works whether the target schema is the built-in default or a
> user-uploaded one. Apply that mapping deterministically to every record
> — the LLM proposes the mapping once, code applies it to all records, so
> no hallucination risk touches actual policy values."

**Outcome:** `modules/ai_mapper.py` (later split into `claude_mapper.py`
+ `gemini_mapper.py` + `mapping_router.py`, see Stage 8) and
`modules/exporter.py`, which applies the mapping deterministically —
enforcing the "AI suggests, code validates" principle from `CLAUDE.md`.

---

## Stage 7 — Streamlit UI assembly

**Prompt:**
> "Tie the modules together into a Streamlit app: upload legacy source →
> choose/upload target schema → run migration → show metrics dashboard →
> show the AI-proposed mapping table → show an anomaly report → raw-vs-
> converted side-by-side comparison → JSON/CSV export."

**Outcome:** `app.py`, built as a single-page wizard rather than a
multi-file Streamlit app (kept deploy simple: no routing/multipage
config needed). Session state used to persist results between the "Run"
button and the results/export sections.

**Follow-up UI refinement prompts:**
> "Add a bundled-sample toggle in the sidebar so the demo doesn't require
> the user to have files ready."
> "Add severity filtering to the anomaly table so error/warning/info can
> be viewed separately."

---

## Stage 8 — Feature addition: multi-provider AI support (Claude ↔ Gemini)

**Prompt:**
> "I have a Google GenAI API key, not a Claude API key — can we have
> another option?"

**Outcome:** Refactored `ai_mapper.py` into `claude_mapper.py` +
`gemini_mapper.py` + a `mapping_router.py` dispatcher, added a provider
radio button to the sidebar, and used `response_mime_type="application/
json"` on the Gemini call for structured output.

---

## Stage 9 — Bug fix: Gemini model deprecation

**Bug report (from the developer, verbatim error message):**
> "AI mapping failed: 404 NOT_FOUND ... 'This model models/gemini-2.5-flash
> is no longer available to new users...'"

**Fix prompt / process:**
> Searched current Gemini model availability, then updated
> `gemini_mapper.py` to use `gemini-flash-latest` as the primary model
> (an alias Google maintains to always point at their current Flash
> model) with an explicit fallback chain (`gemini-3.6-flash` →
> `gemini-3.5-flash-lite` → `gemini-2.5-flash`), so a 404 on one model
> automatically retries the next rather than failing the whole migration
> run. Non-404 errors (bad key, quota) still fail fast rather than being
> masked.

This directly reflects `CLAUDE.md` principle #3 ("every AI provider call
must degrade gracefully").

---

## Stage 10 — Major feature expansion: Universal source support

**Prompt (three requirements in one):**
> "Let's create a different version in which: (1) user can upload any
> legacy schema, not fixed ones like COBOL, (2) user can optionally add
> relational policy business rules, or just not upload them and let the
> AI decide its mapping, (3) add a reconciliation option for anomaly/
> business-rule errors and warnings flagged data."

**Outcome — broken into three build prompts:**

1. **Universal schema detection:**
   > "Auto-detect file format (CSV/JSON/Excel are self-describing; fixed-
   > width needs either a COBOL copybook, a generic field-layout file, or
   > AI-assisted boundary inference as a last resort) and produce a
   > common canonical record shape regardless of source format."
   → `modules/schema_detector.py`, `generic_schema_upload.py`,
   `ai_schema_inference.py`.

   **Verification prompt:**
   > "Prove this works on something that isn't COBOL — build a synthetic
   > CSV sample and confirm the same pipeline parses it correctly,
   > including null handling."
   → Caught and fixed a real bug during this step: pandas was leaving
   `NaN` instead of `None` for missing CSV values due to dtype coercion;
   fixed by casting to `object` dtype before the null-replacement step.

2. **Generalized canonical join:**
   > "Generalize the policy/claims join so it's not hardcoded to those
   > field names — accept any primary + optional related dataset with a
   > user-specified (or heuristically suggested) join key."
   → `modules/canonical.py` (v2), with `suggest_join_keys()` as a
   best-effort heuristic, always deferring to the user's final choice.

3. **Optional AI-assisted business rules + reconciliation workspace**
   (see the reviewed build for the shipped implementation details).

---

## Stage 11 — Code review / QA pass on a separately AI-built version

**Prompt:**
> "I have built the app, first look into it, then I will assign you some
> tasks."

**Process:** Rather than assuming the uploaded build was correct, Claude
was instructed to read every module, compile-check the whole project, and
then **execute the actual pipeline logic against the real sample data**
(not just review code by eye) to confirm claimed features actually work
end-to-end.

**Outcome:** This surfaced three critical, demo-breaking issues before
the showcase rather than during it:
- Claims/nested array data was silently dropped in the exporter
- The policy↔claims relational join was never wired into the app
  (`canonical.py` was dead code, never imported)
- The "relational business rules" engine only supported field-vs-literal
  comparisons, not true relational conditions

...plus one confirmed runtime bug (an argument-shape mismatch that would
crash the "Ask AI for Fix Suggestion" button).

This stage is included in the log because **AI-assisted code review**
was as much a part of the development lifecycle as AI-assisted code
generation — the same "test against real data, don't trust that code
looks right" principle from `CLAUDE.md` applied to auditing a build, not
just producing one.

---

## Configuration files used during development

| File | Purpose |
|---|---|
| `CLAUDE.md` | Standing project instructions read before every development task |
| `requirements.txt` | `streamlit`, `anthropic`, `google-genai`, `pandas` (+ `openpyxl`, `xmltodict`, `PyPDF2` in the Universal version for Excel/XML/PDF ingestion) |
| `.streamlit/secrets.toml.example` | Template for API key configuration on Streamlit Community Cloud (real keys never committed) |
| `prompts.md` | Runtime system prompts used by the AI mapping module, kept in sync with the actual code |

## Design principle enforced throughout every stage

**"AI suggests, code validates."** At no stage was the LLM asked to
transform actual record data or execute arbitrary logic — only to
propose a mapping, interpret a free-text rule, or suggest a fix, always
subject to deterministic code applying (and the user reviewing) the
result before it touches real data.
