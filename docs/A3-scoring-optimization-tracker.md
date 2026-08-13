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

- [ ] Prioritize after Phase 1 evidence review.

### Phase 3 - Demo evidence and documentation consistency

- [ ] Reconcile UI labels, README claims, scoring evidence, and repeatable verification steps.

## Completed changes

| Date | Phase | Change | Verification | Commit |
| --- | --- | --- | --- | --- |
| 2026-08-14 | Governance | Added repository rules and this living tracker. | Reviewed and committed with Phase 1. | Phase 1 commit |
| 2026-08-14 | Phase 1 | Restored task-backed resource deep links, exposed profile/orchestration/quality/source evidence, isolated generated content, added honest history states, and separated per-resource learning feedback with closed-loop next actions. | Frontend non-clean build; resource detail unit tests 5/5; synthetic Playwright contract and visual review at 1440x900 and 390x844; backend 79 tests and 25 subtests; `git diff --check`. | This Phase 1 commit |

## Remaining work

- Complete the remaining rubric-to-route and shared-shell audits.
- Phase 2: fix scoring-critical deep-page recovery, beginning with the empty exam session and authenticated deep-link restoration.
- Phase 2: make learning-path generation failures distinguishable from genuinely personalized paths.
- Phase 3: reconcile README claims, missing delivery documents, admin packaging, and repeatable scoring evidence.

## Decision log

| Date | Decision | Reason |
| --- | --- | --- |
| 2026-08-14 | Treat the Git-backed source tree in the current workspace as the only editable project. | It is the only complete repository under the user-authorized workspace. |
| 2026-08-14 | Never delete files or directories, including generated artifacts. | Explicit user safety constraint; move items when organization is required. |
| 2026-08-14 | Use the generated-resource detail flow for Phase 1. | It joins five high-value rubric signals in one judge-visible deep page: real generation, profile dependence, agent collaboration, hallucination review, and learning feedback. |
