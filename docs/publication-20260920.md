# Repository publication — September 20, 2026 UTC

This publication makes the current local prototype, retained experiments and validation records available alongside the source evidence. It does not deploy a driver service, change the hosted graph, or run a new Claude experiment.

The published runtime is the final implementation recorded in the [evidence-answer audit](../prototype/knowledge_graph/audits/evidence-answer-generalization-20260920/README.md): `2119d669ea51edaf12253e8d9a2adf5ea4c3a18f73bbe5c98cf8c9c88576254a`. Its pinned Neo4j release remains `f5dffe0f7a32b5144920efb5a644f8c4dc9f20def76b4217c38b0cdbc454cf5c`.

Both public repositories contain the same current `prototype/knowledge_graph/` files, including the earlier synthetic SeaLink comparison recovered from the standalone checkout. The [implementation publication manifest](../implementation-publication.json) records their file hashes. The root evidence files remain unchanged. Unrelated Wave 2/3 analysis scripts and local runtime state were excluded from this publication.

Historical reports and captures retain their original bytes, including unfavorable results and statements such as “not published” or “no commit or push.” Those statements describe the checkpoint when each report was written. This publication record updates their publication status without rewriting sealed evidence. Paths to the original development machine in historical records are provenance, not portable setup commands.

Checks performed in clean publication checkouts:

- The full local suite passed **473 tests in each repository**. [Retained publication test log](publication-20260920-tests.log).
- All **50 standalone evidence files** matched their original evidence-snapshot hashes.
- The latest change audit retained all **188 artifact hashes** and its implementation hashes.
- The exact original-failure retest retained all **52 artifact hashes**.
- The earlier synthetic SeaLink comparison passed **24 artifact checks**, both frozen protocols, both event hashes and exact service replay.
- Every copied runtime file matched its source bytes. The two runtime trees match each other.

The front pages and research overview explain the current limits. The development score remains **11/12**, the latest Claude permit answer still omitted a supplied date, and there is no new controlled estimate of MCP benefit. Local tests establish implementation behavior; actual consumer responses remain separate evidence.

No GitHub Actions workflows are configured in either repository. Publication validation was performed locally. The database is hosted in Neo4j Aura; the assessment service and connector run locally. Credentials and private runtime databases are excluded.

The current code and new publication documents pass Git whitespace checks. A whole-publication whitespace check reports existing formatting in retained captures and generated SVGs (where included). Those bytes were preserved to keep the historical files and their recorded hashes intact.
