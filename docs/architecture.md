# FrontierLens ingestion architecture

## Scope of v0.2

The first backend slice turns official model-report indexes into traceable local evidence:

1. Load a version-controlled official source registry.
2. Poll each index with conditional HTTP requests.
3. Discover report candidates inside a domain and path allowlist.
4. Store report metadata and scan history in SQLite.
5. Archive original HTML or PDF files by SHA-256 content hash.
6. Extract PDF pages and top-level sections to stable JSON.
7. Expose monitoring and report data through local JSON APIs.
8. Persist user model/source preferences and generate a filtered release feed.
9. Group evidence under model families and releases instead of flattening every document.
10. Isolate device preferences with bearer tokens.
11. Run source monitoring in an independent worker process.
12. Provide grounded AI reading assistance from server-selected report text.
13. Maintain canonical concepts, typed relationships, and release-specific evidence associations.
14. Build a contextual knowledge payload on demand from parsed official reports and release briefs.

## Trust boundaries

- Only HTTPS URLs from configured domains are accepted.
- Redirect destinations are checked against the same allowlist.
- Qwen GitHub blob links are converted to their official raw file URLs.
- File downloads are size-limited.
- Source titles are escaped before the frontend renders them.
- Generated interpretation is not part of v0.1; this layer only stores evidence.
- User-added sources are stored as `pending_verification`; they do not enter the crawler allowlist automatically.

## Product hierarchy and document coexistence

The user-facing hierarchy is deliberately separate from the raw evidence table:

```text
Model family (Qwen)
  └─ Release (Qwen3)
      ├─ PM brief: changes and product impact
      ├─ Primary document: Technical Report
      └─ Supporting evidence: Blog / Benchmark / GitHub / Safety
```

`reports.url` remains unique, so a newly discovered document is inserted rather than overwriting an older file. `model_releases` and `release_documents` group multiple official documents under one release. A new document for Qwen3 creates another association under Qwen3; a new Qwen version creates a sibling release. Primary-evidence selection is metadata, not deletion: older reports remain traceable.

Knowledge augments this hierarchy:

```text
Release
  └─ Release concept (role + evidence state)
       ├─ Canonical concept ──typed relationship──> Canonical concept
       └─ Concept evidence ──> Report + optional page range
```

The first indexer is deterministic and curated. It matches concept aliases in parsed official
sections, stores the report and page range, and labels brief-only matches as inferred. It does not
use unverified web content or silently promote general background into a release claim.

## Stored artifacts

```text
data/
  frontierlens.db       Local metadata and scan history
  snapshots/            Versioned copies of monitored index pages
  raw/<provider>/       Original reports, named by SHA-256
  parsed/<hash>.json    Page text and section boundaries
```

The `data/` runtime artifacts are intentionally ignored by Git. Database schema, source configuration, parser logic, and tests are version-controlled.

## Local APIs

- `GET /api/health`
- `GET /api/sources`
- `GET /api/reports`
- `GET /api/reports/:id`
- `GET /api/reports/:id/original`
- `GET /api/reports/featured`
- `GET /api/releases`
- `GET /api/releases/:id/knowledge`
- `GET /api/concepts/:id?releaseId=:release_id`
- `POST /api/profiles`
- `GET /api/preferences/:profile_id`
- `PUT /api/preferences/:profile_id`
- `GET /api/feed/:profile_id`
- `GET /api/runs`
- `GET /api/monitor/summary`
- `POST /api/scan`
- `POST /api/ai/assist`
