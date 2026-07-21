# Feature Specification: Contextual Knowledge Map

**Feature Branch**: `main`

**Created**: 2026-07-21

**Status**: Approved for implementation

**Input**: Return FrontierLens to its original product mission, sharpen its positioning and
core objective, and add evidence-backed knowledge graph capabilities without expanding into
a generic encyclopedia.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Understand a Release Through Connected Concepts (Priority: P1)

An AI product manager opens a model release and sees a small, contextual map of the technical
ideas required to understand that release. The map starts from the release's verified changes
and connects each concept to prerequisites, related techniques, capabilities, and evidence.

**Why this priority**: Isolated summaries do not build reusable technical intuition. This flow
turns the existing release brief into an explainable mental model while keeping the release as
the user's anchor.

**Independent Test**: Open a release that has a parsed Tech Report, inspect its knowledge map,
select one concept, and reach both a plain-language explanation and supporting report pages.

**Acceptance Scenarios**:

1. **Given** a release with a parsed Tech Report, **When** the user opens its release workspace,
   **Then** the user sees 3–6 relevant concepts grouped by their role in understanding the release.
2. **Given** a concept in the map, **When** the user selects it, **Then** the user sees what it is,
   why it exists, a useful analogy, its product impact, and its relationships.
3. **Given** a concept supported by a report, **When** the user views its evidence, **Then** the
   user can open the supporting report and see the cited page range when available.

---

### User Story 2 - Navigate From Report Language to Reusable Intuition (Priority: P2)

While reading a Tech Report, an AI product manager can select a highlighted term and open the
same canonical concept used in the release knowledge map. The concept is explained in the
current report's context rather than as an isolated dictionary entry.

**Why this priority**: The largest reading barrier appears at the moment a user meets unfamiliar
terminology. Reusing one concept object avoids contradictory explanations across releases.

**Independent Test**: Open a parsed report, choose a recognized term, and confirm the concept
drawer shows canonical content plus release-specific evidence.

**Acceptance Scenarios**:

1. **Given** a recognized report term, **When** the user opens its explanation, **Then** the same
   canonical concept and relationships appear as in the release map.
2. **Given** a term without evidence in the current release, **When** its explanation opens,
   **Then** it is labeled as general background and is not presented as a release claim.

---

### User Story 3 - Preserve Trust When Knowledge Is Incomplete (Priority: P3)

An AI product manager can distinguish supported relationships from general background and
unavailable evidence. Releases without parsed reports remain useful but do not receive fabricated
concept maps or page citations.

**Why this priority**: FrontierLens is only valuable if users can trust the boundary between
official facts and generated understanding.

**Independent Test**: Open a release with only an official blog and confirm the map uses honest
evidence states and never invents report pages.

**Acceptance Scenarios**:

1. **Given** a release without a parsed Tech Report, **When** the workspace loads, **Then** it shows
   a limited evidence-derived map or a clear pending state.
2. **Given** an inferred relationship, **When** it is displayed, **Then** it is visibly identified
   as background rather than official evidence.

### Edge Cases

- A release has several Tech Reports: evidence remains linked to the correct report and pages.
- A report is replaced or reparsed: the canonical concept remains, while its evidence association updates.
- A concept name has aliases or acronyms: aliases resolve to one canonical concept.
- No concepts are detected: the release workspace explains that concept indexing is pending.
- A cited report file is missing: the concept remains readable but the evidence link shows unavailable.
- The knowledge map is viewed on a small screen: it becomes a readable ordered list, not a clipped graph.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST maintain canonical concepts with aliases, plain-language intuition,
  motivation, analogy, product impact, and evidence state.
- **FR-002**: The system MUST maintain typed concept relationships including prerequisite,
  related, evolves-from, contrasts-with, and enables-capability.
- **FR-003**: The system MUST associate concepts with specific model releases and supporting reports.
- **FR-004**: Evidence associations MUST preserve report identity and page range when available.
- **FR-005**: The release workspace MUST present a contextual map containing no more than six
  primary concepts before optional expansion.
- **FR-006**: Selecting a concept MUST open a reusable concept explanation with its relationships,
  release context, and evidence links.
- **FR-007**: The Tech Report reading experience MUST resolve recognized terms to the same
  canonical concept objects used by the release map.
- **FR-008**: The system MUST distinguish supported release evidence, general background, inferred
  understanding, and unavailable evidence.
- **FR-009**: Releases without sufficient evidence MUST show an honest pending or limited state.
- **FR-010**: Knowledge-map interactions MUST support keyboard navigation and readable mobile fallback.
- **FR-011**: Existing release, document, and report identities MUST remain unchanged; knowledge
  indexing MUST augment rather than overwrite evidence.
- **FR-012**: Automated tests MUST cover concept alias resolution, relationship retrieval, release
  association, and report/page traceability.

### Evidence and Scope Boundaries

- **AI PM decision improved**: Determine what changed in a release, why the technical change matters,
  and which product assumption to validate next.
- **Official evidence path**: Every supported concept opens its source report and cited page range;
  unsupported background is labeled explicitly.
- **Out of scope**: Global force-directed graph exploration, community editing, personalized mastery
  tracking, animated concept labs, full courses, and autonomous graph generation from unverified sources.

### Key Entities

- **Concept**: A canonical technical idea with aliases and an explanation designed to build intuition.
- **Concept Relationship**: A typed, directed connection between two concepts or a concept and capability.
- **Release Concept**: The role and priority of a concept within one model release.
- **Concept Evidence**: A traceable association between a concept, release, report, and optional pages.
- **Model Release**: The existing event that groups brief, variants, documents, and the contextual map.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can move from a release highlight to a relevant concept and supporting report
  page in no more than three interactions.
- **SC-002**: Every supported concept shown in a release map has at least one accessible official
  evidence link; concepts without one are clearly labeled as background or pending.
- **SC-003**: The first release map contains 3–6 primary concepts and remains understandable without
  dragging, zooming, or learning graph controls.
- **SC-004**: In a five-person AI PM usability check, at least four participants can correctly explain
  one release change and its product implication after using the map for five minutes.
- **SC-005**: Existing report ingestion, release mapping, personalized feed, and AI-assisted reading
  tests continue to pass after knowledge-map integration.

## Assumptions

- The first implementation uses curated canonical concept content plus deterministic matching; fully
  autonomous ontology generation is deferred until evidence quality can be reviewed.
- Existing parsed reports and release briefs provide the initial release-to-concept signals.
- English concept names may coexist with Chinese explanations because source reports are primarily English.
- The current single-user/local production architecture remains in scope; team collaboration is deferred.
