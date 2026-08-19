# CLAUDE.md — Project Instructions

This file was provided to Claude at the start of development (the standing
context an AI coding assistant reads before every task, similar to a
`CLAUDE.md` in Claude Code or a Cowork project brief). It captures the
constraints and design principles that shaped every subsequent prompt.

## Project

**AI-Assisted Legacy Policy Migration Engine** — a capstone PoC for the
Quantum Shift AI Practitioner+ program.

**Business problem:** Legacy policy systems and historical data block
digital transformation and cloud modernization. Manual migration is slow,
expensive, error-prone, and high risk for business continuity. Carriers
need faster platform upgrades, book consolidations, M&A portfolio
transfers, and modernization of distribution models.

**What we're building:** A working prototype that demonstrates AI-assisted,
error-reduced, auditable policy record migration from legacy source
systems into a modern cloud-native PAS schema.

## Hard constraints

- **No local installs during development.** The developer's machine does
  not have admin rights. All development, testing, and iteration happens
  in a cloud sandbox; the deliverable is a **cloud-hosted app** (Streamlit
  Community Cloud), deployed via GitHub's web UI — no local Python, no
  local git CLI, no local package installs required at any point.
- **Capstone scope, not production scope.** This is a PoC/MVP. Prefer
  simplicity and a demonstrable business story over completeness. Cut
  scope aggressively rather than letting any one feature block delivery.
- **Timeline:** one week, single developer, AI-assisted throughout.

## Design principles (apply to every feature)

1. **"AI suggests, code validates."** The LLM (Claude or Gemini) is used
   only for judgment calls that benefit from language understanding —
   proposing a field mapping, interpreting a free-text business rule,
   suggesting a fix. It is **never** used to transform actual record data
   or to execute arbitrary logic. All parsing, validation, business-rule
   evaluation, and record transformation are deterministic Python, so the
   pipeline is auditable and hallucination-proof where it matters most.
2. **Test against real data, not assumptions.** Whenever a legacy file
   format, business rule, or data quirk is introduced, verify the parser/
   validator against actual sample data before wiring it into the UI.
   Don't trust that code "looks right" — run it.
3. **Every AI provider call must degrade gracefully.** Model names get
   deprecated. Any LLM call should have a fallback path and a clear error
   message, never a silent failure or a raw stack trace shown to the user.
4. **Keep the AI/deterministic boundary visible in the UI.** The person
   using the app should always be able to see what the AI proposed versus
   what the code decided, and be able to override either.

## Tech stack

- Frontend + backend: Streamlit (single Python app, no separate build step)
- AI: Claude API and Google Gemini API (interchangeable, user's choice)
- Storage: none required for v1 — in-session state is sufficient for a
  demo; do not add a database unless the demo genuinely needs persistence
- Hosting: Streamlit Community Cloud, deployed from a GitHub repo created
  via the browser (no local git)

## Definition of done for any feature

- Code compiles cleanly (`python3 -m py_compile`)
- Core logic tested against real sample data, not synthetic placeholder
  data, wherever real data is available
- Any new AI-facing prompt is documented in `AI_DEVELOPMENT_LOG.md`
- README and `prompts.md` updated to reflect any new capability
