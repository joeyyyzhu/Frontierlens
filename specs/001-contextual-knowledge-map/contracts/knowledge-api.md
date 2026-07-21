# Knowledge API Contract

## GET `/api/releases/{release_id}/knowledge`

Returns the contextual map for one existing release.

Successful response:

```json
{
  "releaseId": 12,
  "releaseSlug": "qwen3",
  "status": "ready",
  "primaryConcepts": [
    {
      "id": "mixture-of-experts",
      "name": "Mixture-of-Experts",
      "role": "mechanism",
      "evidenceState": "supported",
      "contextSummary": "...",
      "oneLiner": "...",
      "relationships": [],
      "evidence": [
        {"reportId": 7, "title": "Qwen3 Technical Report", "firstPage": 4, "lastPage": 5}
      ]
    }
  ]
}
```

`status` is `ready`, `limited`, or `pending`. Unknown release IDs return `404`. Concepts without
report support never include fabricated page numbers.

## GET `/api/concepts/{concept_id}`

Returns one canonical concept, all aliases, typed relationships, and release occurrences. Unknown
concept IDs or aliases return `404`. Alias requests resolve to the canonical `id`.
