# Data Model: Contextual Knowledge Map

## Concept

- `id`: canonical slug, unique and stable
- `name`: canonical display name
- `aliases`: normalized alternative terms and acronyms
- `one_liner`: concise intuition
- `why_it_exists`: motivation and problem addressed
- `analogy`: plain-language analogy
- `product_impact`: implication for AI product decisions
- `created_at`, `updated_at`: audit timestamps

Aliases are case-insensitive during matching and MUST resolve to exactly one concept.

## Concept Relationship

- `source_concept_id`: origin concept
- `target_concept_id`: destination concept
- `relationship_type`: `prerequisite`, `related`, `evolves_from`, `contrasts_with`, or
  `enables_capability`
- `explanation`: short reason for the edge
- `evidence_state`: `background` or `inferred`

The source, target, and type form a unique relationship.

## Release Concept

- `release_id`: existing model release
- `concept_id`: canonical concept
- `role`: `core_change`, `mechanism`, `prerequisite`, or `capability`
- `priority`: lower values appear first
- `evidence_state`: `supported`, `inferred`, `background`, `pending`, or `unavailable`
- `context_summary`: how the concept matters in this release

A release and concept pair is unique. At most six entries with roles `core_change` or `mechanism`
are returned as primary map nodes.

## Concept Evidence

- `release_id`: release in which the evidence applies
- `concept_id`: concept supported by the evidence
- `report_id`: existing report
- `first_page`, `last_page`: optional one-based page range
- `quote_hint`: short non-verbatim locator or section title
- `evidence_state`: normally `supported`; `unavailable` when the file is missing

The release, concept, and report form a unique evidence association. Report deletion cascades only
the association, not the canonical concept.

## State Transitions

1. New release without parsed evidence: map state `pending`.
2. Deterministic match in a parsed official report: release concept becomes `supported` and gains evidence.
3. Match in official non-report evidence only: release concept may be `inferred` with no report page.
4. Report reparsed: evidence page locator is rebuilt; canonical concept remains unchanged.
5. Report file unavailable: association becomes `unavailable` and retains its report identity.
