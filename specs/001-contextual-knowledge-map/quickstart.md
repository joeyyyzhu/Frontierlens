# Quickstart Validation: Contextual Knowledge Map

## Prerequisites

- FrontierLens initialized with at least one parsed Tech Report associated with a release.
- The normal local service is running.

## Validate the backend

1. Run the complete automated test suite.
2. Request `/api/releases`, choose a release ID with a readable Tech Report, and request
   `/api/releases/{id}/knowledge`.
3. Expect 3–6 primary concepts when recognized evidence exists.
4. For every concept marked `supported`, expect at least one report ID and no invented page value.
5. Request `/api/concepts/{id}` and confirm aliases and typed relationships resolve consistently.

## Validate the user journey

1. Open the personalized feed and enter a model release workspace.
2. Find “Technical Intuition Map” after the release changes summary.
3. Open a concept with keyboard and pointer input.
4. Confirm the drawer explains intuition, motivation, analogy, product impact, and relationships.
5. Follow its evidence action into the correct Tech Report; confirm the report identity is unchanged.
6. Open a release without a parsed report and confirm it shows a limited or pending state.

## Expected outcome

An AI product manager reaches a release concept and its evidence within three interactions, while
unsupported background remains visibly distinct from official release evidence.
