# Tasks: Contextual Knowledge Map

**Input**: Design documents from `/specs/001-contextual-knowledge-map/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

## Phase 1: Setup

- [x] T001 Verify existing ignore rules cover Python, local data, and environment secrets in `.gitignore`

## Phase 2: Foundational

- [x] T002 Add canonical concept, relationship, release-concept, and evidence schema in `backend/frontierlens/database.py`
- [x] T003 Add curated concept registry and deterministic evidence indexer in `backend/frontierlens/knowledge.py`

## Phase 3: User Story 1 - Understand a Release Through Connected Concepts (P1)

**Goal**: Show a release-centered map with evidence-backed concept explanations.

**Independent Test**: A parsed release returns 3–6 primary concepts and report evidence.

- [x] T004 [P] [US1] Add knowledge indexing and traceability tests in `tests/test_pipeline.py`
- [x] T005 [US1] Add release knowledge payload and concept lookup methods in `backend/frontierlens/database.py` and `backend/frontierlens/knowledge.py`
- [x] T006 [US1] Expose release and concept knowledge endpoints in `backend/frontierlens/server.py`
- [x] T007 [US1] Add contextual knowledge-map section and concept drawer integration in `app.js`
- [x] T008 [US1] Add readable, keyboard-visible, responsive map styling in `styles.css`

## Phase 4: User Story 2 - Navigate From Report Language to Reusable Intuition (P2)

**Goal**: Reuse canonical concepts from the report reader.

**Independent Test**: A recognized report term resolves to the same canonical concept payload.

- [x] T009 [P] [US2] Add alias-resolution tests in `tests/test_pipeline.py`
- [x] T010 [US2] Connect report concept interactions to canonical concept lookup in `app.js`

## Phase 5: User Story 3 - Preserve Trust When Knowledge Is Incomplete (P3)

**Goal**: Make supported, background, inferred, pending, and unavailable states explicit.

**Independent Test**: A release lacking parsed evidence shows no fabricated citations.

- [x] T011 [P] [US3] Add incomplete-evidence and multiple-report tests in `tests/test_pipeline.py`
- [x] T012 [US3] Add honest pending/limited states to knowledge payloads and UI in `backend/frontierlens/knowledge.py` and `app.js`

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T013 [P] Document positioning, knowledge flow, and API in `README.md`, `docs/product-experience.md`, and `docs/architecture.md`
- [x] T014 Validate AI PM decision journey and official evidence traceability using `specs/001-contextual-knowledge-map/quickstart.md`
- [x] T015 Run all automated tests and mark completed tasks in `specs/001-contextual-knowledge-map/tasks.md`

## Dependencies & Execution Order

- T001 precedes implementation verification.
- T002 and T003 block all user-story work.
- US1 is the MVP and precedes report-reader reuse in US2.
- US3 may be validated independently after the foundational schema exists.
- Documentation and full validation follow all desired user stories.

## Parallel Opportunities

- T004, T009, and T011 can be prepared independently once the data contract is stable.
- T008 can proceed after the generated markup contract in T007 is known.
- T013 can proceed alongside final UI validation.

## Implementation Strategy

Deliver US1 first: one release-centered map, canonical concept drawer, and traceable report links.
Then reuse the same concept objects in the reader and add strict incomplete-evidence states.
