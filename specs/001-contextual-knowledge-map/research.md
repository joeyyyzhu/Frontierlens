# Research: Contextual Knowledge Map

## Decision: Use a contextual layered map, not a force-directed canvas

**Rationale**: AI product managers need a fast explanation path, not graph controls. A layered list
of release changes, concepts, prerequisites, and evidence is readable, keyboard accessible, and
predictable on small screens.

**Alternatives considered**: Force-directed SVG/canvas graph; global ontology explorer. Both add
interaction cost and encourage browsing without improving the 15-minute release task.

## Decision: Start with curated concepts plus deterministic evidence matching

**Rationale**: The product's trust promise requires stable explanations and auditable associations.
Curated concept records prevent contradictory definitions, while deterministic alias matching can
index parsed reports and release briefs without an external model dependency.

**Alternatives considered**: Fully AI-generated ontology; manual per-release authoring. The former
is difficult to audit and the latter does not scale across the existing report corpus.

## Decision: Keep graph data relational and augment existing release entities

**Rationale**: Current scope is modest and SQLite already provides transactions, indexes, and joins.
Typed edge tables express the required graph while preserving report and release identity.

**Alternatives considered**: A graph database or JSON blobs. A graph database is operationally
premature; JSON blobs make alias resolution, evidence joins, and integrity checks harder.

## Decision: Label knowledge by evidence state

**Rationale**: A canonical concept may be useful background even when a particular release does not
claim it. Separating supported, inferred, background, pending, and unavailable prevents the UI from
turning general knowledge into a false release claim.

**Alternatives considered**: Hide all unsupported concepts; show everything without labels. The
first harms learning, while the second violates the evidence-first product promise.
