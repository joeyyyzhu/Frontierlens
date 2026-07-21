<!--
Sync Impact Report
- Version change: template -> 1.0.0
- Added principles: AI PM First; Evidence Before Interpretation; Release-Centric Understanding;
  Progressive Cognitive Depth; Current, Complete, and Auditable
- Added sections: Product Mission and Scope; Delivery and Quality Gates
- Removed sections: none (template placeholders replaced)
- Templates requiring updates:
  - ✅ .specify/templates/plan-template.md
  - ✅ .specify/templates/spec-template.md
  - ✅ .specify/templates/tasks-template.md
- Runtime guidance:
  - ✅ README.md
  - ✅ docs/product-experience.md
  - ✅ docs/architecture.md
- Follow-up TODOs: none
-->
# FrontierLens Constitution

## Core Principles

### I. AI PM First

FrontierLens MUST optimize its primary journey for AI product managers who need to make a
product decision after a model release. Every primary screen MUST help answer at least one
of four questions: what changed, why it matters, what should I validate, and where is the
official evidence. Research depth MAY unfold progressively, but it MUST NOT displace this
decision journey.

### II. Evidence Before Interpretation

Facts MUST come from traceable official evidence. Tech Reports are the highest-priority and
most complete source; Official Blogs, Benchmarks, GitHub, Model/System Cards, and Safety
Reports supplement them according to the question being answered. AI-generated summaries,
concept explanations, relationships, and product implications MUST be visibly distinguishable
from source facts and MUST link back to supporting evidence when available.

### III. Release-Centric Understanding

The primary product object MUST be a model release, not a document and not an isolated model
variant. A release MAY contain multiple coexisting documents and variants. A new document
MUST augment its release without overwriting history; a new model generation MUST create a
new release node. Concepts and relationships MUST be reusable across releases while preserving
the release-specific context in which they were asserted.

### IV. Progressive Cognitive Depth

FrontierLens MUST provide just enough understanding first, then allow deeper exploration in
the sequence `release change -> concept -> relationship -> evolution -> original evidence`.
Knowledge maps MUST serve comprehension and navigation; decorative graphs, disconnected
encyclopedic pages, and exhaustive taxonomies are out of scope unless they shorten the core
decision journey. Concept explanations MUST cover intuition, why the concept exists, related
ideas, and product impact before optional mathematical depth.

### V. Current, Complete, and Auditable

Official-source monitoring MUST preserve source URL, discovery time, publication date basis,
original content, and parsing status. The product MUST NOT label an item as the latest release
without an official, auditable date basis. Missing, undated, superseded, or partially parsed
evidence MUST remain visible with an honest status rather than being silently discarded or
presented as verified chronology.

## Product Mission and Scope

FrontierLens is an AI Frontier Intelligence Platform. Its mission is to help an AI product
manager understand a frontier model release in 15 minutes and confidently explain its core
changes, product implications, and evidence.

The core experience consists of:

1. Personalized discovery of official model releases.
2. A release workspace that explains what changed and why it matters.
3. Complete, AI-assisted Tech Report reading with page-level evidence.
4. A contextual knowledge map connecting concepts, prerequisites, evolution, capabilities,
   and evidence.
5. Question-first retrieval across official source types.

Community discussion, generic AI news, courses, and graph exploration without release context
are outside the core product scope until the primary 15-minute journey is validated.

## Delivery and Quality Gates

- Every feature specification MUST name the AI PM decision it improves and its evidence path.
- Every generated factual claim MUST have an evidence state: supported, inferred, or unavailable.
- Tests MUST cover release/document coexistence, model/report mapping, and knowledge-evidence
  traceability when those areas change.
- UI changes MUST preserve keyboard access, readable text sizing, explicit loading/empty/error
  states, and a single primary question per screen.
- Production changes MUST retain source monitoring observability and must not expose service keys
  to the browser.

## Governance

This constitution governs product specifications, implementation plans, and review decisions.
Amendments require a documented rationale, a migration impact note, and semantic versioning:
MAJOR for incompatible principle changes, MINOR for materially expanded guidance, and PATCH for
clarifications. Every feature review MUST check compliance before planning and again before
completion. Exceptions MUST be explicit in the feature plan and include why a simpler compliant
alternative is insufficient.

**Version**: 1.0.0 | **Ratified**: 2026-07-21 | **Last Amended**: 2026-07-21
