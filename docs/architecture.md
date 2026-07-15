# FrontierLens ingestion architecture

## Scope of v0.1

The first backend slice turns official model-report indexes into traceable local evidence:

1. Load a version-controlled official source registry.
2. Poll each index with conditional HTTP requests.
3. Discover report candidates inside a domain and path allowlist.
4. Store report metadata and scan history in SQLite.
5. Archive original HTML or PDF files by SHA-256 content hash.
6. Extract PDF pages and top-level sections to stable JSON.
7. Expose monitoring and report data through local JSON APIs.

## Trust boundaries

- Only HTTPS URLs from configured domains are accepted.
- Redirect destinations are checked against the same allowlist.
- Qwen GitHub blob links are converted to their official raw file URLs.
- File downloads are size-limited.
- Source titles are escaped before the frontend renders them.
- Generated interpretation is not part of v0.1; this layer only stores evidence.

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
- `GET /api/runs`
- `GET /api/monitor/summary`
- `POST /api/scan`
