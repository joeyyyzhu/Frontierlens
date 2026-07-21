# Implementation Plan: Contextual Knowledge Map

**Branch**: `001-contextual-knowledge-map` | **Date**: 2026-07-21 | **Spec**: [spec.md](spec.md)

## Summary

Add a small, evidence-backed cognitive map to every model release workspace. Canonical concepts
and typed relationships are stored independently from reports; release associations and page-level
evidence connect them to the existing release/document model. A deterministic indexer seeds trusted
concept content and matches report/brief text. The UI presents a layered map and reuses the existing
concept drawer, with a clear pending state when evidence is insufficient.

## Technical Context

**Language/Version**: Python 3.11+, browser-native JavaScript, HTML, CSS

**Primary Dependencies**: Python standard library, SQLite, pypdf 6.x

**Storage**: Existing SQLite database plus existing parsed-report JSON files

**Testing**: unittest through the project test runner

**Target Platform**: Single-host Linux/macOS web service and modern desktop/mobile browsers

**Project Type**: Web application with Python API/backend and static browser frontend

**Performance Goals**: Knowledge payload visible within one second for a local release workspace;
no graph layout work on the main thread beyond a maximum of six primary concepts

**Constraints**: No new runtime dependency; preserve existing report/release identities; no
unverified source may create supported evidence; readable mobile and keyboard fallback required

**Scale/Scope**: Hundreds of releases, dozens of canonical concepts in v1, and no more than six
primary concepts per release view

## Constitution Check

- **AI PM decision**: Helps decide what changed, why it matters, and which product hypothesis to validate.
- **Evidence path**: Every supported release concept retains report ID and optional page range.
- **Release integrity**: Concepts augment existing releases and documents without replacing either.
- **Progressive depth**: Release map shows 3–6 concepts before deeper relationships and background.
- **Auditability**: Supported, inferred, background, pending, and unavailable states remain explicit.

All gates pass before research and remain satisfied after design.

## Project Structure

### Documentation (this feature)

```text
specs/001-contextual-knowledge-map/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── knowledge-api.md
└── tasks.md
```

### Source Code (repository root)

```text
backend/frontierlens/
├── database.py          # persistent concept, relationship, release, and evidence records
├── knowledge.py         # curated registry, matching, indexing, payload assembly
└── server.py            # knowledge API and feed integration

app.js                   # contextual map, concept drawer, report-term integration
styles.css               # accessible map and drawer presentation
tests/test_pipeline.py   # indexing and traceability tests
docs/product-experience.md
docs/architecture.md
```

**Structure Decision**: Extend the existing single-service application. Knowledge construction is
isolated in one backend module while persistence remains in the established database boundary.

## Complexity Tracking

No constitution violations or additional infrastructure are required.
