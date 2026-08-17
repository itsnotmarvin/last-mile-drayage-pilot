#!/usr/bin/env node

import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const readJson = (path) => JSON.parse(readFileSync(resolve(root, path), "utf8"));

const metadata = readJson("data/metadata.json");
const physicalNodes = readJson("data/processed/physical_nodes.geojson");
const physicalEdges = readJson("data/processed/physical_edges.json");
const couplingEdges = readJson("data/processed/coupling_edges.json");
const regulatoryNodes = readJson("data/processed/regulatory_nodes.json");
const entityNodes = readJson("data/processed/entity_nodes.json");
const vehicleProfiles = readJson("data/processed/vehicle_profiles.json");
const officialRoads = readJson(
  "data/raw/gis/official/njogis_apm_study_area_roads_2026_07_26.geojson",
);

const errors = [];
const check = (condition, message) => {
  if (!condition) errors.push(message);
};
const unique = (values) => new Set(values).size === values.length;
const equalCoordinate = (a, b) =>
  Array.isArray(a) &&
  Array.isArray(b) &&
  a.length === 2 &&
  b.length === 2 &&
  Math.abs(a[0] - b[0]) <= 1e-12 &&
  Math.abs(a[1] - b[1]) <= 1e-12;

const nodes = physicalNodes.features.map((feature) => ({
  ...feature.properties,
  coordinate: feature.geometry.coordinates,
}));
const edges = physicalEdges.edges;
const paths = physicalEdges.paths;
const approaches = physicalEdges.approaches;

const nodeById = new Map(nodes.map((node) => [node.node_id, node]));
const edgeById = new Map(edges.map((edge) => [edge.edge_id, edge]));
const pathById = new Map(paths.map((path) => [path.path_id, path]));
const approachById = new Map(
  approaches.map((approach) => [approach.approach_id, approach]),
);
const sourceIds = new Set(metadata.sources.map((source) => source.source_id));
const regulatoryIds = new Set(regulatoryNodes.rules.map((rule) => rule.rule_id));
const entityIds = new Set(entityNodes.entities.map((entity) => entity.entity_id));
const profileIds = new Set(vehicleProfiles.profiles.map((profile) => profile.profile_id));
const officialRoadById = new Map(
  officialRoads.features.map((feature) => [feature.properties.OBJECTID, feature]),
);

check(physicalNodes.feature_count === nodes.length, "physical node feature_count mismatch");
check(physicalEdges.edge_count === edges.length, "physical edge_count mismatch");
check(couplingEdges.edge_count === couplingEdges.edges.length, "coupling edge_count mismatch");
check(metadata.source_count === metadata.sources.length, "metadata source_count mismatch");

check(unique(nodes.map((node) => node.node_id)), "duplicate physical node_id");
check(unique(edges.map((edge) => edge.edge_id)), "duplicate physical edge_id");
check(unique(paths.map((path) => path.path_id)), "duplicate path_id");
check(unique(approaches.map((approach) => approach.approach_id)), "duplicate approach_id");
check(unique(couplingEdges.edges.map((edge) => edge.edge_id)), "duplicate coupling edge_id");
check(unique(metadata.sources.map((source) => source.source_id)), "duplicate source_id");

for (const source of metadata.sources) {
  for (const archivedFile of source.archived_files ?? []) {
    const archivedPath = resolve(root, archivedFile.path);
    check(existsSync(archivedPath), `${source.source_id}: archived file is missing: ${archivedFile.path}`);
    if (existsSync(archivedPath) && archivedFile.sha256) {
      const actualHash = createHash("sha256")
        .update(readFileSync(archivedPath))
        .digest("hex");
      check(
        actualHash === archivedFile.sha256,
        `${source.source_id}: SHA-256 mismatch for ${archivedFile.path}`,
      );
    }
  }
}

for (const node of nodes) {
  check(node.incident_edge_ids.length > 0, `${node.node_id}: isolated node`);
  for (const edgeId of node.incident_edge_ids) {
    const edge = edgeById.get(edgeId);
    check(Boolean(edge), `${node.node_id}: unknown incident edge ${edgeId}`);
    if (edge) {
      check(
        edge.from_node === node.node_id || edge.to_node === node.node_id,
        `${node.node_id}: incident edge ${edgeId} does not touch node`,
      );
    }
  }
  for (const pathId of node.path_ids) {
    check(pathById.has(pathId), `${node.node_id}: unknown path ${pathId}`);
  }
  for (const approachId of node.approach_ids) {
    check(approachById.has(approachId), `${node.node_id}: unknown approach ${approachId}`);
  }
  for (const sourceId of node.source_ids ?? []) {
    check(sourceIds.has(sourceId), `${node.node_id}: unregistered source ${sourceId}`);
  }
}

for (const edge of edges) {
  const from = nodeById.get(edge.from_node);
  const to = nodeById.get(edge.to_node);
  check(Boolean(from), `${edge.edge_id}: unknown from_node ${edge.from_node}`);
  check(Boolean(to), `${edge.edge_id}: unknown to_node ${edge.to_node}`);
  if (from) {
    check(from.incident_edge_ids.includes(edge.edge_id), `${edge.edge_id}: missing from-node incident link`);
    check(
      equalCoordinate(edge.geometry_reference.start_coordinate, from.coordinate),
      `${edge.edge_id}: start coordinate differs from from_node`,
    );
  }
  if (to) {
    check(to.incident_edge_ids.includes(edge.edge_id), `${edge.edge_id}: missing to-node incident link`);
    check(
      equalCoordinate(edge.geometry_reference.end_coordinate, to.coordinate),
      `${edge.edge_id}: end coordinate differs from to_node`,
    );
  }
  for (const pathId of edge.path_ids) {
    check(pathById.has(pathId), `${edge.edge_id}: unknown path ${pathId}`);
  }
  for (const approachId of edge.approach_ids) {
    check(approachById.has(approachId), `${edge.edge_id}: unknown approach ${approachId}`);
    check(
      Number.isInteger(edge.sequence_by_approach[approachId]),
      `${edge.edge_id}: missing sequence for ${approachId}`,
    );
  }
  check(
    Object.keys(edge.sequence_by_approach).length === edge.approach_ids.length,
    `${edge.edge_id}: sequence_by_approach and approach_ids differ`,
  );
  for (const sourceId of [
    edge.geometry_source_id,
    edge.gate_observation_source_id,
    edge.official_nhs_designations?.fhwa_nhs_2025?.source_id,
  ].filter(Boolean)) {
    check(sourceIds.has(sourceId), `${edge.edge_id}: unregistered source ${sourceId}`);
  }

  let chainCoordinate = edge.geometry_reference.start_coordinate;
  for (const featureId of edge.official_feature_ids) {
    const feature = officialRoadById.get(featureId);
    check(Boolean(feature), `${edge.edge_id}: official feature ${featureId} is absent from archive`);
    if (!feature) continue;
    check(
      feature.properties.JURISDICTN === edge.jurisdiction_code_raw,
      `${edge.edge_id}: feature ${featureId} jurisdiction differs from edge`,
    );
    const coordinates = feature.geometry.coordinates;
    const featureStart = coordinates[0];
    const featureEnd = coordinates.at(-1);
    if (equalCoordinate(chainCoordinate, featureStart)) {
      check(
        feature.properties.ONEWAY !== "TF",
        `${edge.edge_id}: feature ${featureId} is traversed against TF direction`,
      );
      chainCoordinate = featureEnd;
    } else if (equalCoordinate(chainCoordinate, featureEnd)) {
      check(
        feature.properties.ONEWAY !== "FT",
        `${edge.edge_id}: feature ${featureId} is traversed against FT direction`,
      );
      chainCoordinate = featureStart;
    } else {
      check(false, `${edge.edge_id}: official feature chain disconnects at ${featureId}`);
    }
  }
  if (edge.geometry_reference.official_feature_coverage?.startsWith("partial_feature")) {
    check(
      edge.geometry_reference.gate_coordinate_distance_from_official_centerline_meters <= 1,
      `${edge.edge_id}: partial-feature gate is not sufficiently close to official centerline`,
    );
  } else {
    check(
      equalCoordinate(chainCoordinate, edge.geometry_reference.end_coordinate),
      `${edge.edge_id}: official feature chain does not reach edge end`,
    );
  }
}

for (const path of paths) {
  check(path.movement === "inbound", `${path.path_id}: movement must remain inbound`);
  check(path.definition_level === "corridor_route_family", `${path.path_id}: not a corridor family`);
  check(nodeById.has(path.destination_node), `${path.path_id}: unknown destination node`);
  for (const approachId of path.approach_ids) {
    const approach = approachById.get(approachId);
    check(Boolean(approach), `${path.path_id}: unknown approach ${approachId}`);
    if (approach) {
      check(approach.path_id === path.path_id, `${approachId}: assigned to the wrong path`);
    }
  }
}

for (const approach of approaches) {
  check(pathById.has(approach.path_id), `${approach.approach_id}: unknown path`);
  check(approach.movement === "inbound", `${approach.approach_id}: movement must remain inbound`);
  check(nodeById.has(approach.origin_node), `${approach.approach_id}: unknown origin node`);
  check(nodeById.has(approach.destination_node), `${approach.approach_id}: unknown destination node`);

  let expectedNode = approach.origin_node;
  approach.ordered_edge_ids.forEach((edgeId, index) => {
    const edge = edgeById.get(edgeId);
    check(Boolean(edge), `${approach.approach_id}: unknown edge ${edgeId}`);
    if (!edge) return;
    check(edge.from_node === expectedNode, `${approach.approach_id}: disconnected before ${edgeId}`);
    check(edge.approach_ids.includes(approach.approach_id), `${edgeId}: missing ${approach.approach_id}`);
    check(
      edge.sequence_by_approach[approach.approach_id] === index + 1,
      `${edgeId}: incorrect ${approach.approach_id} sequence`,
    );
    expectedNode = edge.to_node;
  });
  check(
    expectedNode === approach.destination_node,
    `${approach.approach_id}: traversal does not end at destination`,
  );
  for (const sourceId of approach.sequence_source_ids ?? []) {
    check(sourceIds.has(sourceId), `${approach.approach_id}: unregistered source ${sourceId}`);
  }
}

for (const coupling of couplingEdges.edges) {
  for (const endpoint of [coupling.from_node, coupling.to_node]) {
    const endpointExists =
      edgeById.has(endpoint) ||
      nodeById.has(endpoint) ||
      regulatoryIds.has(endpoint) ||
      entityIds.has(endpoint) ||
      profileIds.has(endpoint);
    check(endpointExists, `${coupling.edge_id}: unknown endpoint ${endpoint}`);
  }
  for (const sourceId of coupling.source_ids ?? []) {
    check(sourceIds.has(sourceId), `${coupling.edge_id}: unregistered source ${sourceId}`);
  }
}

check(
  JSON.stringify(couplingEdges.path_ids) === JSON.stringify(physicalEdges.active_path_ids),
  "coupling path IDs differ from active physical path IDs",
);
check(
  JSON.stringify(couplingEdges.approach_ids) === JSON.stringify(physicalEdges.active_approach_ids),
  "coupling approach IDs differ from active physical approach IDs",
);

const governedTargets = (ruleId) =>
  new Set(
    couplingEdges.edges
      .filter((edge) => edge.from_node === ruleId && edge.relationship === "GOVERNS")
      .map((edge) => edge.to_node),
  );
const njTandemTargets = governedTargets("reg_nj_tandem_gross_bridge");
for (const edge of edges) {
  check(njTandemTargets.has(edge.edge_id), `${edge.edge_id}: missing NJ tandem/gross/bridge coupling`);
}
const njNonInterstateTargets = governedTargets("reg_nj_noninterstate_single_axle");
for (const edge of edges.filter((item) => item.jurisdiction_code_raw !== "HA")) {
  check(
    njNonInterstateTargets.has(edge.edge_id),
    `${edge.edge_id}: missing NJ non-Interstate single-axle coupling`,
  );
}
const federalInterstateTargets = governedTargets("reg_federal_interstate_weight");
for (const edge of edges.filter((item) => item.jurisdiction_code_raw === "HA")) {
  check(
    federalInterstateTargets.has(edge.edge_id),
    `${edge.edge_id}: missing federal Interstate/reasonable-access weight coupling`,
  );
}

for (const ruleId of ["reg_nj_width_limit", "reg_nj_height_limit", "reg_nj_semitrailer_length"]) {
  const targets = governedTargets(ruleId);
  for (const edge of edges) {
    check(targets.has(edge.edge_id), `${edge.edge_id}: missing ${ruleId} coupling`);
  }
}

const relationshipTargets = (ruleId, relationship) =>
  new Set(
    couplingEdges.edges
      .filter((edge) => edge.from_node === ruleId && edge.relationship === relationship)
      .map((edge) => edge.to_node),
  );
const namedStreetEdges = edges.filter((edge) => (edge.official_list_names ?? []).length > 0);
for (const ruleId of [
  "reg_elizabeth_four_ton_limit_streets",
  "reg_elizabeth_five_ton_limit_streets",
]) {
  const targets = relationshipTargets(ruleId, "STREET_NOT_LISTED_IN_RESTRICTION_TABLE");
  for (const edge of namedStreetEdges) {
    check(targets.has(edge.edge_id), `${edge.edge_id}: missing ${ruleId} street-table coupling`);
  }
}
const unionCountyTargets = relationshipTargets(
  "reg_union_county_truck_routes_reserved",
  "TRUCK_ROUTE_SCHEDULE_RESERVED",
);
for (const edge of edges.filter((item) => item.jurisdiction_code_raw === "C")) {
  check(unionCountyTargets.has(edge.edge_id), `${edge.edge_id}: missing Union County schedule coupling`);
}
const njtaTargets = governedTargets("reg_njta_roadway_use_limitations");
for (const edge of edges.filter((item) => item.jurisdiction_code_raw === "HA")) {
  check(njtaTargets.has(edge.edge_id), `${edge.edge_id}: missing NJTA roadway-use coupling`);
}

const profile = vehicleProfiles.profiles.find(
  (item) => item.profile_id === physicalEdges.vehicle_profile_id,
);
check(Boolean(profile), "physical graph vehicle profile is missing");
if (profile) {
  check(profile.supplied_facts.movement_direction === "inbound", "vehicle movement is not inbound");
  check(profile.supplied_facts.outbound_movement_in_scope === false, "outbound movement entered scope");
  check(
    JSON.stringify(profile.classifications.path_ids) === JSON.stringify(physicalEdges.active_path_ids),
    "vehicle path IDs differ from active physical path IDs",
  );
  check(
    JSON.stringify(profile.classifications.approach_ids) ===
      JSON.stringify(physicalEdges.active_approach_ids),
    "vehicle approach IDs differ from active physical approach IDs",
  );
}

if (errors.length) {
  console.error(`Graph validation failed with ${errors.length} error(s):`);
  for (const error of errors) console.error(`- ${error}`);
  process.exitCode = 1;
} else {
  console.log(
    `Graph validation passed: ${paths.length} paths, ${approaches.length} approaches, ${nodes.length} nodes, ${edges.length} physical edges, ${couplingEdges.edges.length} coupling edges, ${metadata.sources.length} sources.`,
  );
}
