# TASKS — Translation Evaluation & Analytics Suite

This document breaks the project into **main phases**, then **individual tasks**. It’s based on `OUTLINE.md` and is oriented around getting to an MVP quickly while keeping good architecture for later scale.

---

## Phase 0 — Project setup & decisions (foundation)

### 0.1 Confirm scope (MVP defaults)
- [ ] Decide execution model for MVP: **single-machine** only (yes/no)
- [ ] Decide evaluation mode requirement: **reference-based**, **reference-free**, or both for MVP
- [ ] Decide interfaces for MVP: **CLI only** vs CLI + local API
- [ ] Decide storage: **SQLite + artifact directory** vs other
- [ ] Decide first provider adapter (e.g., hosted API) and one baseline

### 0.2 Repository & workflow setup
- [ ] Create/confirm repo structure:
  - [ ] `app/`
  - [ ] `translation_engine/`
  - [ ] `comparison_engine/`
  - [ ] `analysis_engine/`
  - [ ] `schemas/`
  - [ ] `storage/`
  - [ ] `tests/`
- [ ] Add basic developer docs:
  - [ ] How to run a sample pipeline end-to-end
  - [ ] How to add a new provider adapter
  - [ ] How to add a new metric
- [ ] Set up formatting/linting/test runner conventions (language-specific)

### 0.3 Define “done” for MVP
- [ ] A single CLI command can execute: **ingest → translate → compare → analyze → export**
- [ ] Results are reproducible (config snapshot + dataset version + provenance stored)
- [ ] Outputs include at least:
  - [ ] translations per segment
  - [ ] 2–3 metrics per segment
  - [ ] aggregated leaderboard
  - [ ] at least one chart/report

---

## Phase 1 — Contracts & schemas (make components independent)

### 1.1 Define core schema objects (in `schemas/`)
- [ ] `Dataset`
  - [ ] fields: `dataset_id`, `version`, `segments[]`, optional `references[]`
  - [ ] segment fields: `segment_id`, `source_text`, `source_lang`, `target_lang`, `metadata`
- [ ] `Run`
  - [ ] fields: `run_id`, `created_at`, `config_snapshot`, `status`, `artifacts[]`
- [ ] `TranslationRequest` / `TranslationResult`
  - [ ] request includes config + segment info
  - [ ] result includes `translation_text` + `provenance`
- [ ] `ComparisonRequest` / `MetricResult`
  - [ ] metric name/value, tags, and linkage to `translation_id` and `segment_id`
- [ ] `AnalysisRequest` / `ReportArtifact`
  - [ ] dimensions, filters, report/viz spec, artifact pointers

### 1.2 Establish ID and hashing conventions
- [ ] Define how IDs are generated:
  - [ ] `run_id`
  - [ ] `translation_id`
  - [ ] `metric_result_id`
  - [ ] `artifact_id`
- [ ] Define deterministic hashing:
  - [ ] `config_hash`
  - [ ] `dataset_hash` (or dataset version strategy)
  - [ ] `request_hash` for caching translation calls

### 1.3 Error taxonomy (shared)
- [ ] Define a small set of error types/codes:
  - [ ] provider rate limit
  - [ ] provider invalid request
  - [ ] network failure / timeout
  - [ ] internal assertion / schema validation error
- [ ] Define retry policy rules per error type

---

## Phase 2 — Storage layer (runs, artifacts, metrics)

### 2.1 Artifact storage
- [ ] Define on-disk artifact layout (append-only preferred):
  - [ ] datasets
  - [ ] translations
  - [ ] metric outputs
  - [ ] reports/charts
- [ ] Implement `ArtifactRegistry` API:
  - [ ] write artifact (returns artifact pointer)
  - [ ] read artifact by pointer
  - [ ] list artifacts by run

### 2.2 Run persistence (Job & Run DB)
- [ ] Create run table(s):
  - [ ] run metadata, timestamps, status transitions
  - [ ] config snapshot location/hash
- [ ] Implement minimal `RunRepository`:
  - [ ] create run
  - [ ] update status
  - [ ] append event/log entry (optional but useful)
  - [ ] fetch run summary

### 2.3 Metrics persistence (Metrics/Results DB)
- [ ] Create tables for:
  - [ ] segment-level metric results
  - [ ] aggregates (run-level + pairwise)
- [ ] Implement `MetricsRepository` APIs:
  - [ ] write metric results batch
  - [ ] query metrics by run/config/metric
  - [ ] obtain aggregates

---

## Phase 3 — Application Orchestrator (pipeline, concurrency, reliability)

### 3.1 Job lifecycle / state machine
- [ ] Implement run state machine:
  - [ ] `Created → Translating → Comparing → Analyzing → Completed`
  - [ ] `Failed → Retrying → {stage}`
- [ ] Persist state transitions and stage start/end timestamps

### 3.2 Scheduler + worker pools
- [ ] Implement a basic scheduler:
  - [ ] stage-by-stage dispatch (simple first)
  - [ ] bounded queues between stages
- [ ] Implement concurrency primitives:
  - [ ] worker pool per stage
  - [ ] configurable max concurrency
- [ ] Add rate limiting hooks for translation providers (even if no-op initially)

### 3.3 Reliability / observability
- [ ] Add structured logging:
  - [ ] run_id, stage, segment_id, config_id
- [ ] Implement retry/backoff for translation calls:
  - [ ] exponential backoff + max retries
- [ ] Add cancellation / graceful shutdown behavior
- [ ] Emit simple run summary at end (counts, failures, duration)

### 3.4 CLI interface (MVP)
- [ ] `run` command:
  - [ ] dataset input path
  - [ ] translation configs (one or multiple)
  - [ ] metrics set selection
  - [ ] output directory / run name
- [ ] `inspect` command:
  - [ ] show run status
  - [ ] show high-level metrics summary
- [ ] `export` command (optional in MVP if analysis already generates)
  - [ ] export CSV/JSON for a given run

---

## Phase 4 — Ingest (dataset loading & validation)

### 4.1 Dataset loader(s)
- [ ] Define supported input formats for MVP:
  - [ ] JSONL or CSV with columns: segment_id/source/target(optional reference)/metadata(optional)
- [ ] Implement loader:
  - [ ] parse
  - [ ] validate required fields
  - [ ] normalize segmentation (one row = one segment for MVP)

### 4.2 Dataset versioning/provenance
- [ ] Compute dataset hash/version identifier
- [ ] Store dataset artifact with metadata:
  - [ ] source file info
  - [ ] counts, languages, domain tags if present

### 4.3 Basic dataset quality checks
- [ ] empty or very short segments detection
- [ ] language code validation
- [ ] duplicate segment_id detection

---

## Phase 5 — Translation Engine (adapters, caching, batching)

### 5.1 Core translation engine interface
- [ ] Define `translate_batch(requests[]) -> results[]`
- [ ] Ensure return type includes provenance:
  - [ ] model/provider id
  - [ ] decoding params
  - [ ] latency
  - [ ] token usage / estimated cost (if available)
  - [ ] request hash

### 5.2 Provider adapter #1 (MVP)
- [ ] Implement one real provider adapter OR a local model adapter
- [ ] Implement one baseline adapter:
  - [ ] identity (copy source) OR simple dictionary-based transform
  - [ ] ensures pipeline works without external dependencies

### 5.3 Caching
- [ ] Implement deterministic cache key:
  - [ ] hash(source_text + config + segmentation strategy)
- [ ] Add cache storage:
  - [ ] in artifacts store and/or DB
- [ ] Add “cache hit” logging + provenance flag

### 5.4 Batching
- [ ] Implement batching rules (simple first):
  - [ ] max batch size by provider
  - [ ] max tokens/characters per batch if needed
- [ ] Ensure batching preserves segment order and IDs

---

## Phase 6 — Comparison Engine (metrics + aggregation)

### 6.1 Metric registry framework
- [ ] Implement `Metric` interface:
  - [ ] `name`
  - [ ] `requires_reference` (bool)
  - [ ] `score(segment, translation, reference?) -> value`
- [ ] Implement metric selection by name / config

### 6.2 MVP metrics (2–3)
Pick a minimal set that is cheap and robust:
- [ ] Metric: **length ratio**
- [ ] Metric: **chrF** (reference-based; only if references exist)
- [ ] Metric: **embedding cosine similarity** (reference-based or ref-free depending on design)

### 6.3 Segment-level outputs
- [ ] Produce `MetricResult` per segment per metric
- [ ] Attach tags for obvious failures:
  - [ ] empty translation
  - [ ] identical-to-source (if that’s undesirable)
  - [ ] extreme length ratio

### 6.4 Aggregation
- [ ] Compute run-level aggregates:
  - [ ] mean/median per metric
  - [ ] percentile summary (p50/p90) if easy
- [ ] Pairwise comparison (optional in MVP):
  - [ ] win-rate per segment between two translation configs
  - [ ] delta distributions

---

## Phase 7 — Analysis Engine (analytics, reports, visualizations)

### 7.1 Query + grouping layer
- [ ] Implement basic group-by queries:
  - [ ] by model/provider/config
  - [ ] by language pair
  - [ ] by dataset version
- [ ] Add filtering:
  - [ ] include/exclude tags
  - [ ] segment length buckets

### 7.2 MVP reports
- [ ] Leaderboard table:
  - [ ] rows: translation config
  - [ ] columns: metric aggregates, latency/cost summaries if available
- [ ] “Worst segments” report:
  - [ ] list lowest scoring segments per metric + translation text

### 7.3 MVP visualizations (at least one)
- [ ] Choose one chart:
  - [ ] box plot of metric distribution per config OR
  - [ ] scatter plot of quality vs latency/cost
- [ ] Emit artifact(s):
  - [ ] image or HTML
  - [ ] link referenced from run summary

### 7.4 Export formats
- [ ] CSV export for aggregates
- [ ] JSON export for segment-level metrics (or Parquet later)

---

## Phase 8 — End-to-end integration (pipeline wiring)

### 8.1 Wire stages: ingest → translate → compare → analyze
- [ ] Ensure outputs from each stage are stored and referenced by stable IDs
- [ ] Ensure partial reruns are possible (optional but recommended):
  - [ ] rerun compare/analyze without re-translating

### 8.2 Reproducibility verification
- [ ] Confirm that re-running with same dataset + config yields:
  - [ ] same cache hits
  - [ ] consistent artifact paths/IDs (where applicable)
- [ ] Record environment info:
  - [ ] app version, git hash, dependency versions

### 8.3 Acceptance test scenario (MVP)
- [ ] Add a small fixture dataset (10–50 segments)
- [ ] Add a golden workflow test:
  - [ ] completes successfully
  - [ ] produces translations, metrics, report artifacts
  - [ ] sanity checks on output shapes (counts match)

---

## Phase 9 — Testing & quality (baseline confidence)

### 9.1 Unit tests
- [ ] Schema validation tests
- [ ] Translation caching key determinism test
- [ ] Metric correctness smoke tests on known examples

### 9.2 Integration tests
- [ ] End-to-end pipeline with baseline adapter (no external calls)
- [ ] Optional: provider adapter mocked “record/replay” tests

### 9.3 Performance & robustness checks (lightweight)
- [ ] Run a medium dataset (e.g., 1k segments) to validate:
  - [ ] batching effectiveness
  - [ ] memory usage does not blow up
  - [ ] bounded queues/backpressure operate as expected

---

## Phase 10 — Extensions (post-MVP, prioritized backlog)

### 10.1 More translation adapters
- [ ] Add additional provider adapters
- [ ] Add local model support (if not in MVP)
- [ ] Add glossary/constraints support where providers allow

### 10.2 More metrics
- [ ] BLEU, TER, additional semantic metrics
- [ ] Model-based evaluation (COMET/BLEURT-style) if desired
- [ ] Terminology adherence and named-entity consistency scoring

### 10.3 Advanced analysis
- [ ] Bootstrap confidence intervals
- [ ] Significance testing between configs
- [ ] Pareto frontier computation for quality vs cost/latency

### 10.4 UI / API service
- [ ] Local API to query runs and metrics
- [ ] Web dashboard for interactive slicing/drill-down

### 10.5 Distributed execution
- [ ] Move worker pools to distributed task queue
- [ ] Use Postgres + object storage
- [ ] Multi-node orchestration

---

## Quick “critical path” checklist (recommendation)

If you want the fastest route to a useful system, the critical path is:

- [ ] Phase 1 (schemas) minimum viable
- [ ] Phase 2 (storage) minimum viable
- [ ] Phase 3 (CLI orchestrator) minimum viable
- [ ] Phase 4 (ingest) + Phase 5 (baseline + 1 adapter)
- [ ] Phase 6 (2–3 metrics) + Phase 7 (leaderboard + 1 chart)
- [ ] Phase 8 (end-to-end test fixture)

---