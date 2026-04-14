# Phase 0 — Project setup & decisions log

This log captures **decisions made** and **actions performed** during **Phase 0** (foundation) for the *Translation Evaluation & Analytics Suite*.

References:
- `TASKS.md` → Phase 0 checklist and MVP definition
- `OUTLINE.md` → overall architecture and guiding non-goals/principles

---

## Status

- Phase: **0 — Project setup & decisions**
- Log created: 2026-04-04
- Owner: project team

---

## 0.1 Confirm scope (MVP defaults)

### Decision: Execution model for MVP
- Decision: **Single-machine only**
- Rationale:
  - Aligns with `OUTLINE.md` non-goal: no distributed compute initially
  - Simplifies orchestration, storage, and reproducibility for MVP
- Implications:
  - Concurrency implemented via local worker pools/threads/async only
  - Storage targets local filesystem + local DB

### Decision: Evaluation mode requirement for MVP
- Decision: **Both reference-based and reference-free (where possible)**
- Rationale:
  - `OUTLINE.md` explicitly supports both modes; MVP should not assume references exist
  - Enables evaluating datasets with and without reference translations
- Implications:
  - Metrics must declare `requires_reference`
  - Pipeline must explicitly handle missing references without failing

### Decision: Interfaces for MVP
- Decision: **CLI only**
- Rationale:
  - `OUTLINE.md` suggests CLI first and “optionally add a local API service later”
  - MVP focus is repeatable evaluation runs, not interactive service
- Implications:
  - All run orchestration is driven by a CLI command
  - Future API can wrap CLI/core modules once contracts stabilize

### Decision: Storage for MVP
- Decision: **SQLite + artifact directory**
- Rationale:
  - Matches `TASKS.md` recommended storage strategy
  - Provides enough durability and query capability for run summaries/metrics
- Implications:
  - Define artifact layout early (append-only preferred)
  - Store config snapshots + dataset version identifiers for reproducibility

### Decision: First provider adapter + baseline
- Decision: **Baseline adapter first** (local, no external dependency) + **Provider adapter TBD**
- Rationale:
  - Critical path: ensure end-to-end pipeline works without API keys/network
  - Provider choice depends on desired vendors (OpenAI/DeepL/Google/etc.) and key availability
- Notes / Follow-ups:
  - Provider adapter selection is pending until preferences and credentials are confirmed
  - Baseline translation behavior should be deterministic (e.g., identity copy)

---

## 0.2 Repository & workflow setup

### Repo structure
- Target structure (from `TASKS.md`):
  - `app/`
  - `translation_engine/`
  - `comparison_engine/`
  - `analysis_engine/`
  - `schemas/`
  - `storage/`
  - `tests/`

#### Action taken
- Action: **Verified repository root and existing `logs/` directory**
- Action: **Created this log file**: `logs/PHASE-0.md`

#### Pending actions
- Create/confirm the full repo structure listed above
- Add developer docs:
  - how to run a sample pipeline end-to-end
  - how to add a provider adapter
  - how to add a metric
- Decide and enforce formatting/lint/test conventions once primary language/tooling is confirmed

---

## 0.3 Define “done” for MVP

### MVP “done” criteria (recorded)
MVP is considered done when:

1. A single CLI command can execute the full flow:
   - **ingest → translate → compare → analyze → export**

2. Results are reproducible:
   - config snapshot stored
   - dataset version/hash captured
   - provenance stored with translations/metrics

3. Outputs include at least:
   - translations per segment
   - 2–3 metrics per segment
   - aggregated leaderboard
   - at least one chart/report artifact

#### Notes
- These criteria match `TASKS.md` Phase 0.3 and align with `OUTLINE.md` workflow.

---

## Open questions (not decided yet)

These are explicitly called out in `OUTLINE.md` and remain pending unless/ until confirmed:

- Which hosted provider is adapter #1 for MVP (OpenAI vs DeepL vs Google vs other)?
- Primary implementation language / runtime (affects linting/testing choices)
- Default metric set for MVP (beyond “length ratio” and one semantic metric)

---

## Next steps (Phase 0 completion checklist)

- [ ] Create the repository directory skeleton (`app/`, `schemas/`, etc.)
- [ ] Add developer “how-to” docs (minimal, but runnable)
- [ ] Choose language-specific tooling for format/lint/test
- [ ] Decide provider adapter #1 (and capture it here)
- [ ] Confirm MVP metric list (2–3) and whether references exist in initial datasets

---

## Change log

- 2026-04-04:
  - Added `logs/PHASE-0.md`
  - Recorded initial Phase 0 decisions (execution model, evaluation modes, interface, storage, baseline-first)