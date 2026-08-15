# A3 Scoring Optimization Tracker

Last updated: 2026-08-14

This file is the source of truth for the current scoring review and frontend refinement work. Update it before and after every implementation batch.

## Status legend

- `[ ]` Not started
- `[~]` In progress
- `[x]` Complete and verified
- `[!]` Blocked or needs a product decision

## Safety and scope

- [x] Active repository identified as `94015785源码/嵌智学航源码` inside the current workspace.
- [x] Project-wide rules added in `AGENTS.md`.
- [x] Recursive deletion and all file/directory deletion are prohibited; obsolete items must be moved and recorded.
- [x] Existing untracked environment files identified and excluded from this work and future commits.
- [x] The former resource detail implementation was moved to `frontend/src/views/legacy/ResourceDetailView.legacy.vue`; no file was deleted.

## Scoring review

- [x] Extract the official scoring table, point weights, thresholds, and judge-visible evidence.
- [~] Map the rubric to current routes, APIs, agents, documentation, and demo evidence.
- [x] Record the initial high-risk evidence list in priority order.

### Official score structure and thresholds

| Priority | Scoring area | Points | Judge-visible threshold or evidence |
| --- | --- | ---: | --- |
| P0 | System completeness | 10 | A coherent, operable loop from collection and analysis through generation, verification, feedback, tutoring, assessment, and adjustment; capabilities must be presented as agents. |
| P0 | Dynamic learning profile | 8 | Dialogue-based construction, intelligent analysis, updates, and at least 6 visible dimensions using a real team member as a demonstrable learner. |
| P0 | Personalized multimodal resources | 10 | At least 5 actually generated resource types and at least 5 demonstrable cases; quality evaluation and hallucination controls must be visible. |
| P0 | Personalized path and recommendation | 3 | Profile-driven recommendations with high fit and 3-5 verifiable cases; show reasons, profile evidence, match, and adjustment. |
| P0 | Intelligent tutoring | 5 | Different and multimodal question types, accurate guided/Socratic answers, and at least 5 cases. |
| P0 | Effect assessment | 5 | Goal attainment, mastery, heatmap, radar, plan adjustment, and at least 3 cases. |
| P1 | Practicality and frontend experience | 10 | Complete and stable behavior, clear and novel interaction, low template/AI feel, multiple devices and roles, and cloud deployment. |
| P1 | Solution innovation | 15 | A visible closed loop, distinction from traditional learning, educational methods, and hallucination prevention. |
| P1 | Technical innovation | 10 | Real multimodal generation, deep multi-agent collaboration, multiple endpoints, and defensible technology choices. |
| P1 | Additional functional innovation | 5 | Extra agents or capabilities such as a digital human must connect to the main agent and learning flow. |
| P1 | Demo video and presentation | 10 | System operation is at least 60% of the video; slides include value, architecture, functions, stack, implementation, innovation, and hallucination controls. |
| P2 | Documentation | 10 | Development, test, deployment, AI implementation detail, source/data, diagrams, and a complete learner case with screenshots. |
| P2 | Bonus evidence | 10 | Existing Xunfei, private knowledge, external API, domestic stack, real-scene test, and AI Coding evidence should be made verifiable. |

The nominal 30-point technical-indicator subsection has child rows totaling 31 points. Intelligent tutoring and effect assessment are also labelled as bonus items while appearing in the required complete loop. Treat every child requirement as required and do not claim a calculated total beyond the official table.

### Initial evidence risks

1. Deep pages can look like independent tools unless they expose the responsible agent, profile basis, handoff, quality/source review, and the next closed-loop action.
2. A resource card or placeholder does not prove actual generation; generated detail pages need inspectable content and a learning-verification action.
3. Path recommendations need visible profile evidence and adjustment rationale, not only ordered tasks.
4. Loading, empty, error, and long-running states must preserve a judge-friendly route through the demo.
5. The required case counts need repeatable seeded/demo data and documentation, not last-minute live generation alone.

## Frontend route audit

- [x] Inventory primary, secondary, and deeper routes.
- [ ] Review shared page shell, breadcrumbs/back navigation, typography, spacing, responsive behavior, and state handling.
- [ ] Review learning-profile child pages.
- [ ] Review learning-path stage and task detail pages.
- [ ] Review personalized-resource generators and generated-resource detail pages.
- [ ] Review quiz generation, exam session, and result/history pages.
- [ ] Review knowledge, tutor, assessment, simulator, and interview detail flows.

## Planned implementation phases

### Phase 1 - Highest-impact deep-page polish

- [x] Select generated-resource history and detail as the first route group.
- [x] Mark affected scoring items and acceptance criteria.
- [x] Implement the smallest coherent page group.
- [x] Distinguish resource-history loading, partial-source failure, full failure, and true empty states with retry actions.
- [x] Verify build without cleaning output directories.
- [x] Verify desktop and mobile routes with synthetic task data and no production-database writes.
- [x] Resolve final review findings for Markdown mind maps, collision-safe feedback-key normalization, and HTML PPT network isolation.
- [x] Update this tracker and commit the verified phase.

Acceptance criteria for this batch:

- A task-backed resource detail can be restored from its URL after refresh through the authenticated task API, while legacy local cache remains an explicitly labelled fallback.
- Loading, unavailable/error, retry, populated, and feedback-complete states provide a clear next action and do not silently redirect.
- Model-produced Markdown is HTML-escaped before limited rendering; HTML PPT output is isolated in a sandboxed iframe; Mermaid uses the installed package with strict security.
- The page exposes only returned profile, planning, responsible-agent, orchestration, quality-review, verification, and knowledge-source evidence, with honest unavailable labels.
- Learners can record either completion or a need for reinforcement and then continue to effect assessment or learning-path adjustment.

### Phase 2 - Remaining scoring-critical page states

- [x] Prioritize the highest-risk remaining states after Phase 1 evidence review.
- [x] Preserve and validate authenticated desktop deep links through both router-guard and runtime-401 login flows.
- [x] Harden exam-session payload normalization, zero-question recovery, persistence guards, timing, exit controls, and responsive layout.
- [x] Ensure embedded-assistant learning-path candidates are persisted only after agent review succeeds; never let degraded fallback output overwrite an accepted path.
- [x] Distinguish learning-path loading/generation failures from a genuine no-profile or not-generated state and provide retry/recovery actions.
- [~] Add focused regression tests, run backend/frontend checks and non-clean builds, then verify applicable routes at 1440x900 and 390x844.

Acceptance criteria for this batch:

- A protected URL preserves its path, query, and hash through login; only same-origin internal targets are accepted, and login loops or external/protocol-relative targets fall back safely.
- An exam payload with valid top-level questions renders normally; a genuinely empty exam never starts timing, exposes completion, writes history, or submits assessment evidence, and offers a clear return route.
- Exam timing is derived from elapsed wall-clock time, the active session has a deliberate exit path, and the page does not horizontally overflow on a 390px viewport.
- Embedded-assistant path and stage tasks treat generated paths as candidates until orchestration review passes; rejected or degraded output leaves the previously accepted profile-scoped configuration unchanged.
- Existing degraded paths are visibly non-personalized and cannot prepare resources; network/load failures never masquerade as “no profile” or a successfully personalized path.

### Deep-page wrapper polish

- [x] Fit the 1920x1080 digital-twin scene to desktop and mobile viewports while preserving an inspectable architecture canvas and explicit loading/error recovery.
- [x] Add an explicit return path, preflight failure state, and retry action to the navbar-free PPT workbench wrapper without changing the embedded OhMyPPT engine.
- [~] Add focused tests, run a non-clean frontend build, and visually verify both routes at 1440x900 and 390x844.

Acceptance criteria for this batch:

- The digital-twin route does not require horizontal scrolling at either target viewport and keeps its loading/error state centered in the available frame.
- The PPT workbench never traps the learner in a blank full-screen iframe: it provides return, loading, unavailable, and retry controls, and successful preflight still fills the remaining viewport.

### Repository integrity - Admin log route

- [x] Scope the admin ignore rule to the runtime root `admin/logs/` directory so `admin/src/views/logs/index.vue` is included in source control.
- [x] Verify the tracked route from an isolated clean source copy: frozen-lockfile install, typecheck, and production build with `--emptyOutDir=false` all pass without copying environment files.

### Production performance and capacity

- [x] Measure the live origin, static assets, application services, and host capacity before changing production.
- [x] Stop only application services proven unrelated to `lzhan.xyz` and the three QR item routes, then reverify every retained endpoint.
- [x] Restore effective immutable caching for fingerprinted assets while keeping SPA HTML uncached.
- [x] Split learner routes into page-level chunks so secondary-page code and CSS are loaded on demand.
- [x] Replace oversized always-on animation media and defer below-the-fold landing media without removing source assets.
- [~] Run focused deployment tests, a non-clean frontend build, bundle-size comparison, and user-led desktop/mobile checks before phased production deployment.

Acceptance criteria for this batch:

- `/`, `/api/health`, `/ppt-api/health`, and `/api/item/{a1,b7,c4}` remain available after unrelated services stop.
- Fingerprinted `/assets/` responses are cacheable for one year and immutable; `index.html` and SPA history fallbacks remain explicitly uncached.
- Loading one learner route does not eagerly include every other learner view in the entry bundle.
- The floating assistant no longer requires a 10 MB GIF download, and below-the-fold landing images do not block initial rendering.
- Production changes are deployed in small verified batches with an immediate configuration rollback path.

### Seedream 4.5 image-generation migration

- [x] Verify the APIMart Seedream 4.5 submission, authentication, parameter, and task-polling contract against the provider documentation.
- [x] Route learning-profile portraits, learning-video first frames, and PPT illustration generation through `seedream-4-5`.
- [x] Add mocked contract tests for the model ID, 2K minimum resolution, Bearer authentication, asynchronous polling, result parsing, and failure handling.
- [x] Update environment examples and root README claims without storing credentials in Git.
- [x] Run focused backend and PPT checks, commit only migration files, then deploy the backend configuration and code in small verified batches.
- [x] Add a lightweight generated default learner portrait for loading, missing, and failed report states; replace it only after the report-specific database portrait is ready.

Acceptance criteria for this batch:

- Every tracked runtime image-generation path submits `seedream-4-5` to APIMart's `/v1/images/generations`; legacy provider selections cannot silently fall back to a previous image model.
- Seedream requests use supported aspect-ratio values and `2K` or `4K` resolution, never the unsupported `1K` value.
- API credentials remain in ignored local/server environment configuration and never appear in source, logs, tests, commits, or user-facing responses.
- Asynchronous tasks are polled through `/v1/tasks/{task_id}`, temporary result URLs are downloaded promptly, and empty, failed, cancelled, timed-out, or malformed responses produce explicit errors.

### Phase 3 - Demo evidence and documentation consistency

- [~] Reconcile UI labels, README claims, scoring evidence, and repeatable verification steps.
- [x] Make the real Harness E2E run five distinct `learning.tutor.answer` cases while preserving one registry probe per Skill.
- [x] Make the scoring summary resolve those tutoring tasks directly from the E2E report and redacted raw-artifact directory; retain the former manually collected directory as a compatibility fallback.
- [x] Replace the machine-specific scoring command with a repository-relative, two-stage real-E2E and evidence-summary workflow.
- [ ] Run the five tutoring calls against the final review account and archive the redacted evidence package; unit tests prove the pipeline contract but are not presented as real model evidence.

## Completed changes

| Date | Phase | Change | Verification | Commit |
| --- | --- | --- | --- | --- |
| 2026-08-14 | Governance | Added repository rules and this living tracker. | Reviewed and committed with Phase 1. | Phase 1 commit |
| 2026-08-14 | Phase 1 | Restored task-backed resource deep links, exposed profile/orchestration/quality/source evidence, isolated generated content, added honest history states, and separated per-resource learning feedback with closed-loop next actions. | Frontend non-clean build; resource detail unit tests 5/5; synthetic Playwright contract and visual review at 1440x900 and 390x844; backend 79 tests and 25 subtests; `git diff --check`. | This Phase 1 commit |
| 2026-08-14 | Repository integrity | Narrowed the admin runtime-log ignore rule and restored the router-referenced server-monitor page to source control. | Isolated frozen-lockfile install; admin typecheck; admin production build with `--emptyOutDir=false`; runtime `admin/logs/` remains ignored. | Admin integrity commit |
| 2026-08-15 | Production performance batches 1-3 | Stopped unrelated application services, restored desktop SPA deployment, fixed static caching, split learner views into route-level chunks, and replaced oversized initial media with WebP plus original fallbacks. | Retained live endpoints all 200; server-local homepage 17 ms and application endpoints 2-6 ms; available host memory about 1.0 GiB; deployment tests 6/6; media tests 2/2; clean non-destructive build reduced entry JS from 1.45 MB to 236.5 KB (94.4 KB transferred with gzip), entry CSS from 868 KB to 197 KB, five landing images from 10.7 MB to 0.55 MB, and the floating animation from 10.6 MB to 193 KB. | `616269e`, `f0adc6e`, `4ff47ea`; deployed and HTTP-verified |
| 2026-08-15 | Seedream 4.5 migration | Fixed all tracked image-generation paths to APIMart `seedream-4-5`, migrated legacy PPT provider selections at runtime, and stored credentials only in ignored local/server environment files. | Backend focused tests 33/33; PPT typecheck; Seedream adapter tests 3/3; APIMart credential check HTTP 200; production backend active and public health HTTP 200. Full backend suite: 285 passed and 1 unrelated dirty-worktree learning-path test failed. | `eeffc64` plus PPT follow-up commit; backend deployed |
| 2026-08-15 | Default profile portrait | Generated a clean non-identifying Seedream 4.5 learner illustration, compressed it to a 640px WebP, and kept loading/missing/failure labels plus retry actions visible until a report-specific portrait is ready. | Default-avatar contract test 1/1; non-clean frontend build; generated source and compressed WebP visually inspected. | This default-avatar commit |
| 2026-08-15 | Phase 3 scoring evidence pipeline | Extended the real Harness run from one to five distinct intelligent-tutoring cases, linked summary generation directly to redacted E2E task artifacts, and documented a repository-relative reproduction flow. | Python compile checks; `tests.test_harness_real_e2e` and `tests.test_scoring_evidence_suite`, 13/13 passed without model calls. Formal real-model evidence remains pending. | This Phase 3 evidence commit |
| 2026-08-15 | Phase 2 auth and exam recovery | Preserved protected deep links across login and runtime 401 redirects; normalized exam payloads, blocked empty-exam timing/history/evidence writes, used wall-clock timing, and added deliberate exit plus mobile layout. | Frontend contract tests 8/8; Playwright deep-link and exam fixtures passed; non-clean production build passed. | `3f1d48f` |
| 2026-08-15 | Phase 2 learning-path integrity | Delayed embedded-assistant path persistence until Harness review, rejected degraded stage baselines, separated load/generation errors from empty profile state, and blocked resource dispatch from degraded paths in both metadata and the backend executor. | Learning-profile/path API 61/61 plus 7 subtests; Harness/MCP 32/32 plus 42 subtests; non-clean frontend build passed. Desktop/mobile visual review remains pending. | This learning-path integrity commit |
| 2026-08-15 | Deep-page wrappers | Fitted the 1920x1080 digital-twin scene into the available viewport and added return, preflight, unavailable and retry states to the OhMyPPT wrapper. | Wrapper source contracts 2/2; non-clean production build passed; route chunks remain 2.11 KB and 2.81 KB before gzip. Desktop/mobile visual review remains pending. | This wrapper-page commit |

## Remaining work

- Complete the remaining rubric-to-route and shared-shell audits.
- Phase 2: visually verify the learning-path load, generation failure, degraded-path and retry states at desktop/mobile widths.
- Phase 3: replace or create the seven README-declared `docs/*.md` deliverables, `SCORING_MATRIX.md`, and the referenced test report; none currently exists in the Git tree.
- Phase 3: run the final real Harness E2E with the review account so the five tutoring cases and scoring summary are backed by archived redacted Xunfei outputs.
- Deep-page polish: make the 1920x1080 digital-twin scene fit desktop/mobile viewports without requiring horizontal scrolling.
- Deep-page polish: add a judge-visible return path and load-failure recovery to the navbar-free PPT workbench iframe.
- Admin evidence integrity: label the nationwide region heatmap as deterministic demo allocation data until real region evidence is collected; all other dashboard metrics remain database-derived.

## Decision log

| Date | Decision | Reason |
| --- | --- | --- |
| 2026-08-14 | Treat the Git-backed source tree in the current workspace as the only editable project. | It is the only complete repository under the user-authorized workspace. |
| 2026-08-14 | Never delete files or directories, including generated artifacts. | Explicit user safety constraint; move items when organization is required. |
| 2026-08-14 | Use the generated-resource detail flow for Phase 1. | It joins five high-value rubric signals in one judge-visible deep page: real generation, profile dependence, agent collaboration, hallucination review, and learning feedback. |
| 2026-08-14 | Treat the Manifest counts of 22 implemented roles and 18 registered Skills as verified, but do not treat missing documentation files as delivered evidence. | The counts match `backend/agent_manifests/xiaozhi_agents.json`; the README-declared documentation paths do not exist in the current Git tree. |
| 2026-08-14 | Keep the admin heatmap but label it as demo allocation data. | `/api/admin/dashboard` derives global metrics from SQLite but builds province values through `_admin_region_demo`; presenting those values as observed regional data would overclaim evidence. |
