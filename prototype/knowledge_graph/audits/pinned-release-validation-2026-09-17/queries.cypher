// Read-only pinned-release validation queries for DrayageRelease f5dffe0f...
// Database: neo4j (Aura). Dataset: last-mile-drayage-pilot.
// Every query is MATCH-only with $dataset / $revision parameters. No writes.
// Run one at a time or via validate_pinned_release.py in this directory.

// C1: release identity (expect exactly 1 row)
MATCH (r:DrayageRelease {dataset: $dataset, revision: $revision})
RETURN r.dataset AS dataset, r.revision AS revision, r.manifest_json AS manifest;

// C1: node / relationship counts (expect 144 / 228)
MATCH (n:DrayageRecord {dataset: $dataset, revision: $revision})
RETURN count(*) AS drayage_nodes;
MATCH ()-[e]->() WHERE e.dataset = $dataset AND e.revision = $revision
RETURN count(*) AS drayage_relationships;

// C1: full release body for snapshot comparison
MATCH (n:DrayageRecord {dataset: $dataset, revision: $revision})
RETURN n{.id, .kind, .layer, .archive, .ordinal, .record_json} AS node ORDER BY n.ordinal;
MATCH (a:DrayageRecord {dataset: $dataset, revision: $revision})-[e]->
      (b:DrayageRecord {dataset: $dataset, revision: $revision})
WHERE e.dataset = $dataset AND e.revision = $revision
RETURN {id: e.id, from: a.id, to: b.id, relationship: type(e),
        archive: e.archive, ordinal: e.ordinal, record_json: e.record_json} AS edge
ORDER BY e.ordinal;

// C2: routes (expect 2 route_family + 2 route_approach)
MATCH (n:DrayageRecord {dataset: $dataset, revision: $revision})
WHERE n.kind IN ['route_family', 'route_approach']
RETURN n.id AS id, n.kind AS kind, n.record_json AS record ORDER BY n.id;

// C2: ordered segments per route (sequence is 1-based in e.record_json)
MATCH (r:DrayageRecord {dataset: $dataset, revision: $revision, id: $route_id})-[e:HAS_ORDERED_SEGMENT]->
      (s:DrayageRecord {dataset: $dataset, revision: $revision})
WHERE e.dataset = $dataset AND e.revision = $revision
RETURN s.id AS segment_id, e.record_json AS edge_record ORDER BY s.id;

// C2: segment endpoints (each road_segment expects 1 STARTS_AT + 1 ENDS_AT)
MATCH (s:DrayageRecord {dataset: $dataset, revision: $revision, id: $segment_id})-[e:STARTS_AT|ENDS_AT]->
      (p:DrayageRecord {dataset: $dataset, revision: $revision})
WHERE e.dataset = $dataset AND e.revision = $revision
RETURN type(e) AS rel, p.id AS place_id ORDER BY rel;

// C3: jurisdiction context per segment
MATCH (s:DrayageRecord {dataset: $dataset, revision: $revision, id: $segment_id})-[e:LOCATED_WITHIN]->
      (j:DrayageRecord {dataset: $dataset, revision: $revision})
WHERE e.dataset = $dataset AND e.revision = $revision
RETURN j.id AS jurisdiction_id, j.kind AS kind, e.record_json AS edge_record ORDER BY j.id;
MATCH (s:DrayageRecord {dataset: $dataset, revision: $revision, id: $segment_id})-[e:HAS_NJOGIS_JURISDICTION_CATEGORY]->
      (d:DrayageRecord {dataset: $dataset, revision: $revision})
WHERE e.dataset = $dataset AND e.revision = $revision
RETURN d.id AS domain_value_id ORDER BY d.id;

// C3/C4: clause-governed segments (applicability originates from source_clause only)
MATCH (c:DrayageRecord {dataset: $dataset, revision: $revision})-[e]->(s:DrayageRecord {dataset: $dataset, revision: $revision, id: $segment_id})
WHERE e.dataset = $dataset AND e.revision = $revision
  AND type(e) IN ['GOVERNS', 'OVERLAPS_PART_OF', 'STREET_NOT_LISTED_IN_RESTRICTION_TABLE',
                  'ROUTE_NUMBER_NOT_LISTED_IN_APPENDIX_C', 'TRUCK_ROUTE_SCHEDULE_RESERVED']
RETURN c.id AS clause_id, c.kind AS clause_kind, type(e) AS rel ORDER BY clause_id, rel;

// C4: check-definition applicability wiring (expect 1 APPLIES_AT + 1 REQUIRES_PROGRAM + 2 incoming SUPPORTS)
MATCH (c:DrayageRecord {dataset: $dataset, revision: $revision, id: 'check_apm_induction_v1'})-[e:APPLIES_AT]->
      (t:DrayageRecord {dataset: $dataset, revision: $revision})
WHERE e.dataset = $dataset AND e.revision = $revision
RETURN t.id AS terminal_id;
MATCH (c:DrayageRecord {dataset: $dataset, revision: $revision, id: 'check_apm_induction_v1'})-[e:REQUIRES_PROGRAM]->
      (p:DrayageRecord {dataset: $dataset, revision: $revision})
WHERE e.dataset = $dataset AND e.revision = $revision
RETURN p.id AS program_id;
MATCH (c:DrayageRecord {dataset: $dataset, revision: $revision})<-[e:SUPPORTS]-
      (s:DrayageRecord {dataset: $dataset, revision: $revision})
WHERE e.dataset = $dataset AND e.revision = $revision
RETURN s.id AS supporting_clause_id ORDER BY s.id;

// C5: clause provenance (every source_clause needs exactly one incoming CONTAINS_CLAUSE)
MATCH (n:DrayageRecord {dataset: $dataset, revision: $revision, kind: 'source_clause'})
OPTIONAL MATCH (d:DrayageRecord {dataset: $dataset, revision: $revision})-[e:CONTAINS_CLAUSE]->(n)
WHERE e.dataset = $dataset AND e.revision = $revision
RETURN n.id AS clause_id, count(e) AS incoming_contains, collect(d.id) AS source_ids ORDER BY n.id;

// C6: mutable observations stay quarantined (expect 5, layer quarantined_observation)
MATCH (n:DrayageRecord {dataset: $dataset, revision: $revision, kind: 'mutable_observation'})
RETURN n.id AS id, n.layer AS layer, n.archive AS archive ORDER BY n.id;

// C6: mutable observations never act as clauses (expect 0 rows)
MATCH (m:DrayageRecord {dataset: $dataset, revision: $revision, kind: 'mutable_observation'})-[e:SUPPORTS|APPLIES_AT|REQUIRES_PROGRAM|CONTAINS_CLAUSE]-()
WHERE e.dataset = $dataset AND e.revision = $revision
RETURN m.id AS id, type(e) AS rel LIMIT 10;

// C8: MCP evaluator bounded reads — single node lookup
MATCH (n:DrayageRecord {dataset: $dataset, revision: $revision, id: $node_id})
RETURN n.kind AS kind, n.layer AS layer, n.archive AS archive, n.record_json AS record;

// C8: MCP evaluator bounded reads — neighbors
MATCH (n:DrayageRecord {dataset: $dataset, revision: $revision, id: $node_id})-[e]->(o:DrayageRecord)
WHERE o.dataset = $dataset AND o.revision = $revision
  AND e.dataset = $dataset AND e.revision = $revision AND type(e) = $relationship
RETURN o.id AS id ORDER BY id;

// C8: MCP evaluator bounded reads — records by kind (archive only)
MATCH (n:DrayageRecord {dataset: $dataset, revision: $revision})
WHERE n.kind IN $kinds AND n.archive = true
RETURN n.record_json AS record ORDER BY n.ordinal;

// C8: MCP evaluator bounded reads — summary
MATCH (n:DrayageRecord {dataset: $dataset, revision: $revision})
WHERE n.archive = true
RETURN n.kind AS kind, count(*) AS count ORDER BY kind;

// C9: Wave-4 isolation — no cross-label nodes (expect 0)
MATCH (n) WHERE (n:DrayageRecord AND n:Wave4Entity)
RETURN count(*) AS cross_label_nodes;

// C9: Wave-4 isolation — no cross-graph relationships in either direction (expect 0)
MATCH (a:DrayageRecord)-[e]->(b:Wave4Entity) RETURN count(*) AS drayage_to_wave4;
MATCH (a:Wave4Entity)-[e]->(b:DrayageRecord) RETURN count(*) AS wave4_to_drayage;

// C9: co-resident graph sizes (observed, not asserted)
MATCH (n:Wave4Entity) RETURN count(*) AS wave4_nodes;
MATCH (:Wave4Entity)-[e]->(:Wave4Entity) RETURN count(*) AS wave4_relationships;
MATCH (r:DrayageRelease) RETURN r.dataset AS dataset, r.revision AS revision ORDER BY r.revision;
