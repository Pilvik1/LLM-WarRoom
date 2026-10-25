# Extended Council V0.2 Development Plan

## Objective

Turn the current LLM-WarRoom experiment into **Extended Council**: a local-first,
multi-model council where reasoning roles and model assignments are explicit,
configurable, inspectable, and reusable.

The product remains a hobby project. V0.2 should optimize for personal utility,
clarity, and reliability rather than commercial breadth or platform complexity.

The core promise is:

> Configure who should think about a problem, choose which model occupies each
> seat, run a structured deliberation, and receive a useful synthesis without
> hiding disagreement, failures, or fallbacks.

## Product principles

1. **Real model diversity.** Different seats can use different providers and
   models; diversity should not be simulated only through personas.
2. **Roles are separate from models.** A role describes how a seat should reason.
   A model assignment describes which provider/model fills that seat.
3. **Useful result first.** Recommendation, disagreement, assumptions, risks, and
   next action come before raw transcripts and technical metadata.
4. **Inspectability over mystique.** Show the stages, model assignments, failures,
   fallbacks, usage, and saved artifacts.
5. **Local-first by default.** Runs and configuration remain local. Prompts leave
   the machine only through providers explicitly configured by the user.
6. **Partial failure is a normal state.** One failed provider should be visible and
   recoverable; it should not silently poison or erase the entire run.
7. **Keep the architecture proportional.** JSON files remain the system of record
   for V0.2 unless measured use proves that a database is necessary.

## V0.2 product surface

### 1. Ask

Send one question to multiple independently configured seats, run anonymized
peer review, and synthesize a final answer. Ask should support follow-up messages
without making the composer disappear after the first turn.

### 2. Council

Assign reasoning roles to seats and pressure-test a question, decision, plan, or
artifact. The initial built-in roles are:

- Contrarian
- First Principles Thinker
- Expansionist
- Outsider
- Executor

Users can edit, remove, add, reorder, and save roles as presets.

### 3. Compare

Evaluate two or more named options against explicit criteria. The final result
must preserve material disagreement instead of reducing everything to a winner.

`evaluate`, `critique`, and deterministic `decide` remain engine capabilities.
They should not become top-level navigation items until a real personal workflow
requires them.

## Target user journey

1. Start a new run and select Ask, Council, or Compare.
2. Choose a saved preset or configure seats manually.
3. Inspect the role-to-model mapping and provider availability.
4. Enter the task, context, criteria, and optional candidate material.
5. Preview the run configuration and start it.
6. Follow a clear stage timeline while models respond, review, and synthesize.
7. Read the structured result first, then expand individual responses and
   technical evidence when useful.
8. Retry failed seats, rerun with a modified configuration, or export Markdown
   and JSON artifacts.
9. Reopen the run after an application restart.

## Target domain model

V0.2 should converge on one canonical `Run` model rather than maintaining
separate conversation and case concepts in the user-facing product.

```text
CouncilPreset
  id
  name
  workflow_type
  seats[]
  synthesizer_assignment
  review_policy

SeatDefinition
  id
  name
  role_prompt
  model_alias
  enabled

ModelAlias
  alias
  provider
  model
  display_name
  fallback_aliases[]

Run
  id
  workflow_type
  status
  input
  preset_snapshot
  stage_events[]
  outputs
  provider_metadata
  errors[]
  artifact_paths
  created_at
  completed_at
```

Every run stores a snapshot of its preset and model assignments. Later changes
to a preset must not rewrite the historical meaning of an earlier run.

## Target application structure

### Backend

- Keep FastAPI and the existing provider adapters.
- Introduce one orchestration service for run lifecycle and stage events.
- Keep role prompts and model aliases as separate configuration objects.
- Preserve anonymization during peer review.
- Persist status transitions before and after each fallible stage.
- Expose provider readiness without exposing API keys.
- Stream typed events with stable schemas and resumable final run state.
- Bind to loopback by default; wider network exposure must be explicit.

Target API surface:

```text
GET    /api/health
GET    /api/providers
GET    /api/presets
POST   /api/presets
PUT    /api/presets/{preset_id}
GET    /api/runs
POST   /api/runs
GET    /api/runs/{run_id}
GET    /api/runs/{run_id}/events
POST   /api/runs/{run_id}/cancel
POST   /api/runs/{run_id}/retry
```

### Frontend

Use a three-part workbench:

- **Left rail:** new run, run history, saved presets.
- **Main canvas:** task input, live stage timeline, structured result.
- **Inspector:** seats, models, provider status, latency, usage, fallbacks, and
  artifact paths.

The interface should have explicit empty, loading, partial-success, error,
cancelled, restored, and no-provider-configured states. Desktop and narrow mobile
layouts are both release gates.

## Milestone 0 — Stabilize the inherited application

**Goal:** make the existing baseline reliable enough to change safely.

### Work

- Keep the Ask composer available after the first response.
- Buffer incomplete SSE frames across network chunks.
- Surface stream and provider failures in the UI.
- Clear or recover stale selected-run state after a backend `404`.
- Move the frontend API base URL to environment configuration.
- Bind the backend to `127.0.0.1` by default.
- Fix current ESLint failures.
- Resolve the production dependency advisory.
- Document `uv` as a setup prerequisite and make the setup path reproducible.
- Add backend unit tests for storage, ranking parsing, fallbacks, and run
  persistence.
- Add frontend tests for the composer, stream parsing, error recovery, and mode
  switching.
- Add a minimal CI workflow for backend tests plus frontend lint and build.

### Exit gates

- A fresh clone can follow the documented setup without hidden prerequisites.
- Backend tests pass.
- Frontend tests, lint, and production build pass independently.
- A user can ask two consecutive questions in one conversation.
- A split SSE event is parsed correctly.
- A missing or failed provider produces a visible recovery path.

## Milestone 1 — Make role-to-model councils first-class

**Goal:** represent the actual product idea in the domain and API.

### Work

- Add `CouncilPreset`, `SeatDefinition`, and preset snapshots on runs.
- Allow each seat to select a different model alias.
- Add explicit synthesizer and reviewer assignments.
- Add provider readiness and model availability endpoints.
- Record requested and actual provider/model identity for every stage.
- Preserve attempted aliases, fallback reason, latency, and usage when available.
- Normalize Ask, Council, and Compare around the canonical `Run` lifecycle.
- Keep legacy conversation JSON readable during migration; do not silently
  rewrite or delete existing local artifacts.

### Exit gates

- One run can use at least three different role/model assignments.
- Swapping a model does not require changing the role prompt.
- Swapping a role does not require changing provider configuration.
- A run restored from disk shows the exact preset snapshot originally used.
- A fallback is visible in both the API response and persisted artifact.

## Milestone 2 — Rebuild the workbench UI

**Goal:** replace the inherited admin-style interface with a coherent council
workflow.

### Work

- Define visual tokens for typography, spacing, color, surfaces, focus, and
  motion.
- Build the left rail, main canvas, and inspector shell.
- Create a useful empty state with workflow and preset selection.
- Add a seat editor for role prompts and model assignments.
- Add a pre-run summary showing seats, providers, fallbacks, and workflow stages.
- Replace stacked raw output panels with a live stage timeline.
- Lead the result page with:
  - recommendation or synthesis;
  - strongest reasons;
  - disagreement map;
  - assumptions and missing information;
  - risks and reversal conditions;
  - one concrete next action.
- Put individual responses, peer reviews, raw metadata, and artifacts in
  expandable evidence panels.
- Add responsive navigation and mobile layouts.
- Add reduced-motion and keyboard-focus behavior.

### Exit gates

- The primary workflow is understandable without reading the README.
- A complete run can be configured and inspected on desktop and mobile.
- The final recommendation is visible before raw model output.
- Partial failures and fallbacks are obvious without opening developer tools.
- No destructive action relies only on an unlabeled icon or browser alert.

## Milestone 3 — Complete the useful hobby-product loop

**Goal:** make repeated personal use fast and trustworthy.

### Work

- Ship editable built-in presets:
  - General Council
  - Decision Review
  - Code Review
  - Investment Case
  - Red Team
- Add save, duplicate, and reset actions for presets.
- Add run cancellation and retry for failed seats.
- Add run history, search, reopen, and rerun-with-changes.
- Show per-stage latency and provider-reported token usage.
- Show estimated cost only when pricing data is explicit and current; otherwise
  label cost as unavailable rather than inventing precision.
- Export a concise Markdown result and the canonical JSON artifact.
- Allow a completed Ask run to continue as a follow-up while retaining the model
  configuration used by the thread.

### Exit gates

- A saved preset can be reused after restart.
- A cancelled run remains inspectable and can be retried.
- A completed run can be reopened and exported after restart.
- Missing usage or pricing data is represented honestly.
- Presets change prompts and model assignments without code edits.

## Milestone 4 — Rename, document, and cut V0.2

**Goal:** make the repository accurately explain and demonstrate the product.

### Work

- Confirm **Extended Council** as the product name.
- Rename repository/package/UI identifiers together rather than leaving mixed
  WarRoom, twosome, and council terminology.
- Introduce neutral environment variable names and document any temporary
  backward-compatible aliases.
- Replace the military header image with a real product screenshot or a sober
  workflow illustration.
- Rewrite the README using the same standard as Flyt:
  - hero visual and concise value proposition;
  - honest status callout;
  - why the project exists;
  - five-minute setup;
  - core workflows;
  - what works today;
  - architecture;
  - privacy and provider boundaries;
  - development commands and validation gates;
  - limitations and roadmap;
  - acknowledgements and license.
- Credit Andrej Karpathy's LLM Council and the Claude Council skill as the
  project's conceptual starting points.
- Add `LICENSE`, `PRIVACY.md`, `SECURITY.md`, and contribution guidance suitable
  for a hobby project.
- Tag V0.2 only after the documented setup and smoke path are verified from a
  fresh clone.

### Exit gates

- Product, repository, package, configuration, and documentation terminology
  agree.
- The README describes only behavior that is currently implemented.
- A fresh user can configure providers and complete one run from the README.
- Privacy language clearly distinguishes local storage from remote model calls.

## Planned implementation sequence

Keep changes small and reviewable:

1. `fix/foundation-reliability`
   - inherited bugs, setup, tests, lint, dependency advisory, CI.
2. `feat/run-domain`
   - canonical run lifecycle and legacy artifact compatibility.
3. `feat/council-presets`
   - roles, seats, model assignments, provider readiness, preset persistence.
4. `feat/workbench-shell`
   - new layout, navigation, empty states, responsive foundation.
5. `feat/live-run-experience`
   - stage timeline, cancellation, retry, errors, restoration.
6. `feat/structured-results`
   - verdict-first result, disagreement, evidence panels, export.
7. `feat/preset-library`
   - built-in presets, editing, duplication, history, rerun.
8. `docs/extended-council-v0.2`
   - final naming migration, screenshots, README, privacy, security, release.

Each branch must leave backend tests, frontend tests, lint, and build green before
the next dependent branch starts.

## V0.2 definition of done

V0.2 is complete when all of the following are true:

- A fresh clone reaches a working local application through documented commands.
- The application explains how to configure missing providers without crashing.
- A user can assign different models to different roles without editing code.
- Ask, Council, and Compare complete through one canonical run lifecycle.
- Peer review remains anonymous.
- The result leads with useful synthesis and preserves material disagreement.
- Provider failure, fallback, latency, and available usage are visible.
- Runs and presets restore after process restart.
- Runs can be cancelled, retried, rerun, and exported.
- Desktop and mobile acceptance paths pass.
- Backend tests, frontend tests, lint, build, and dependency audit pass.
- README, privacy notes, and screenshots match the shipped application.

## Explicit non-goals for V0.2

- Hosted SaaS deployment
- User accounts, teams, billing, or cloud synchronization
- Calibrated confidence claims without evaluation evidence
- Autonomous tool execution or agentic code modification
- Web search, retrieval pipelines, or automatic workspace scanning
- Plugin marketplaces
- Replacing JSON storage without evidence that it is a bottleneck
- Optimizing for competitor feature parity

## Decision log

- **2026-10-25 — Product direction:** Treat the project as a personal extension
  of the LLM Council pattern, not a commercial category play.
- **2026-10-25 — Working name:** Use Extended Council as the target name;
  coordinate the actual rename in Milestone 4.
- **2026-10-25 — Core differentiator:** Make role-to-model assignment and real
  model diversity first-class.
- **2026-10-25 — Architecture boundary:** Keep local JSON artifacts as the V0.2
  source of truth unless usage proves a database is necessary.
- **2026-10-25 — UI strategy:** Replace the inherited frontend around council
  runs instead of polishing the existing stage dump incrementally.
