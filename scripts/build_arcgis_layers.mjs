#!/usr/bin/env node

import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const readJson = (path) => JSON.parse(readFileSync(resolve(root, path), "utf8"));
const writeJson = (path, value) =>
  writeFileSync(resolve(root, path), `${JSON.stringify(value, null, 2)}\n`);

const physicalNodes = readJson("data/processed/physical_nodes.geojson");
const physicalGraph = readJson("data/processed/physical_edges.json");
const regulatoryGraph = readJson("data/processed/regulatory_nodes.json");
const entityGraph = readJson("data/processed/entity_nodes.json");
const vehicleProfiles = readJson("data/processed/vehicle_profiles.json");
const couplingGraph = readJson("data/processed/coupling_edges.json");
const officialRoads = readJson(
  "data/raw/gis/official/njogis_apm_study_area_roads_2026_07_26.geojson",
);

const samePoint = (a, b) =>
  Array.isArray(a) &&
  Array.isArray(b) &&
  a.length === 2 &&
  b.length === 2 &&
  Math.abs(a[0] - b[0]) <= 1e-12 &&
  Math.abs(a[1] - b[1]) <= 1e-12;

const officialById = new Map(
  officialRoads.features.map((feature) => [feature.properties.OBJECTID, feature]),
);
const physicalNodeById = new Map(
  physicalNodes.features.map((feature) => [feature.properties.node_id, feature]),
);

const nearestPointOnSegment = (point, start, end) => {
  const latitudeRadians = (point[1] * Math.PI) / 180;
  const xScale = Math.cos(latitudeRadians);
  const ax = start[0] * xScale;
  const ay = start[1];
  const bx = end[0] * xScale;
  const by = end[1];
  const px = point[0] * xScale;
  const py = point[1];
  const dx = bx - ax;
  const dy = by - ay;
  const denominator = dx * dx + dy * dy;
  const t = denominator === 0 ? 0 : Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / denominator));
  const projected = [start[0] + t * (end[0] - start[0]), start[1] + t * (end[1] - start[1])];
  const distanceSquared =
    (projected[0] * xScale - px) ** 2 + (projected[1] - py) ** 2;
  return { distanceSquared, t };
};

const clipLineAtObservedPoint = (coordinates, observedPoint) => {
  let best = null;
  for (let index = 0; index < coordinates.length - 1; index += 1) {
    const candidate = nearestPointOnSegment(
      observedPoint,
      coordinates[index],
      coordinates[index + 1],
    );
    if (!best || candidate.distanceSquared < best.distanceSquared) {
      best = { ...candidate, index };
    }
  }
  if (!best) throw new Error("Cannot clip an empty roadway geometry");
  return [...coordinates.slice(0, best.index + 1), observedPoint];
};

const buildRoadGeometry = (edge) => {
  const coordinates = [];
  let current = edge.geometry_reference.start_coordinate;

  for (const featureId of edge.official_feature_ids) {
    const feature = officialById.get(featureId);
    if (!feature) throw new Error(`${edge.edge_id}: missing official feature ${featureId}`);
    if (feature.geometry.type !== "LineString") {
      throw new Error(`${edge.edge_id}: feature ${featureId} is not a LineString`);
    }

    let part = feature.geometry.coordinates.map((coordinate) => [...coordinate]);
    if (samePoint(current, part[0])) {
      // The official feature already follows the inbound traversal.
    } else if (samePoint(current, part.at(-1))) {
      part = part.reverse();
    } else {
      throw new Error(`${edge.edge_id}: feature chain disconnects at ${featureId}`);
    }

    coordinates.push(...(coordinates.length ? part.slice(1) : part));
    current = part.at(-1);
  }

  if (edge.geometry_reference.official_feature_coverage?.startsWith("partial_feature")) {
    return clipLineAtObservedPoint(coordinates, edge.geometry_reference.end_coordinate);
  }
  if (!samePoint(current, edge.geometry_reference.end_coordinate)) {
    throw new Error(`${edge.edge_id}: official feature chain does not reach the canonical end node`);
  }
  return coordinates;
};

const approachById = new Map(
  physicalGraph.approaches.map((approach) => [approach.approach_id, approach]),
);
const edgeFeatures = physicalGraph.edges.map((edge) => {
  const supportStatuses = [
    ...new Set(edge.approach_ids.map((id) => approachById.get(id).verification_status)),
  ];
  const relatedRuleIds = [
    ...new Set(
      couplingGraph.edges
        .filter(
          (coupling) =>
            (coupling.from_node === edge.edge_id && coupling.to_node.startsWith("reg_")) ||
            (coupling.to_node === edge.edge_id && coupling.from_node.startsWith("reg_")),
        )
        .map((coupling) =>
          coupling.from_node.startsWith("reg_") ? coupling.from_node : coupling.to_node,
        ),
    ),
  ];
  return {
    type: "Feature",
    properties: {
      edge_id: edge.edge_id,
      name: edge.name,
      from_node: edge.from_node,
      to_node: edge.to_node,
      paths: edge.path_ids.join(" | "),
      approaches: edge.approach_ids.join(" | "),
      approach_count: edge.approach_ids.length,
      verification: supportStatuses.join(" | "),
      jurisdiction: edge.jurisdiction_label,
      official_ids: edge.official_feature_ids.join(","),
      sri_ids: edge.official_sri_ids.join(" | "),
      njogis_feature_count: edge.official_feature_ids.length,
      rule_count: relatedRuleIds.length,
      rules: relatedRuleIds.join(" | "),
    },
    geometry: {
      type: "LineString",
      coordinates: buildRoadGeometry(edge),
    },
  };
});

const displayEdges = {
  type: "FeatureCollection",
  name: "APM drayage inbound physical edge display layer",
  schema_version: "1.0",
  feature_count: edgeFeatures.length,
  features: edgeFeatures,
};

const physicalEdgeIds = new Set(physicalGraph.edges.map((edge) => edge.edge_id));
const physicalNodeIds = new Set(
  physicalNodes.features.map((feature) => feature.properties.node_id),
);
const nonPhysicalIds = [
  ...new Set(
    couplingGraph.edges
      .flatMap((edge) => [edge.from_node, edge.to_node])
      .filter((id) => !physicalEdgeIds.has(id) && !physicalNodeIds.has(id)),
  ),
];

const ruleById = new Map(regulatoryGraph.rules.map((rule) => [rule.rule_id, rule]));
const entityById = new Map(entityGraph.entities.map((entity) => [entity.entity_id, entity]));
const profileById = new Map(
  vehicleProfiles.profiles.map((profile) => [profile.profile_id, profile]),
);
const authorityLevel = (authorityId) => {
  if (["authority_fmcsa", "authority_fhwa", "authority_uscg"].includes(authorityId)) {
    return "Federal";
  }
  if (authorityId === "authority_njdot") return "State";
  if (authorityId === "authority_elizabeth_city") return "Municipal";
  if (authorityId === "authority_panynj") return "Port Authority";
  if (authorityId === "operator_apm_terminals") return "Terminal Operator";
  return "Graph context";
};
const orderedRuleIds = regulatoryGraph.rules
  .map((rule) => rule.rule_id)
  .filter((id) => nonPhysicalIds.includes(id));
const orderedContextIds = nonPhysicalIds
  .filter((id) => !ruleById.has(id))
  .sort((a, b) => a.localeCompare(b));

const displayPositionById = new Map();
orderedRuleIds.forEach((id, index) => {
  const column = Math.floor(index / 9);
  const row = index % 9;
  displayPositionById.set(id, [-74.151 + column * 0.0045, 40.691 - row * 0.004]);
});
orderedContextIds.forEach((id, index) => {
  const column = Math.floor(index / 5);
  const row = index % 5;
  displayPositionById.set(id, [-74.142 + column * 0.004, 40.688 - row * 0.006]);
});

const displayRegulatoryFeatures = nonPhysicalIds.map((id) => {
  const rule = ruleById.get(id);
  const entity = entityById.get(id);
  const profile = profileById.get(id);
  const nodeClass = rule ? "regulatory_rule" : entity ? "entity_or_jurisdiction" : "vehicle_profile";
  const label =
    rule?.label ??
    entity?.label ??
    entity?.name ??
    (profile
      ? "Scoped 80,000 lb five-axle nonhazardous inbound drayage vehicle"
      : id);
  const ruleAuthority = rule ? entityById.get(rule.authority_entity_id) : null;
  const authority = rule
    ? ruleAuthority?.label ?? ruleAuthority?.name ?? rule.authority_entity_id
    : entity?.label ?? entity?.name ?? label;
  const level = rule
    ? authorityLevel(rule.authority_entity_id)
    : id.startsWith("jurisdiction_")
      ? "Jurisdiction"
      : id.startsWith("road_authority_category_")
        ? "Road authority category"
        : profile
          ? "Scoped vehicle"
          : "Graph context";
  const sourceText = Array.isArray(rule?.source_text)
    ? rule.source_text.join(" ")
    : rule?.source_text ?? "";
  return {
    type: "Feature",
    properties: {
      node_id: id,
      rule_id: id,
      label,
      node_class: nodeClass,
      source_id: rule?.source_id ?? "",
      connection_count: couplingGraph.edges.filter(
        (edge) => edge.from_node === id || edge.to_node === id,
      ).length,
      authority_level: level,
      authority,
      placement: nodeClass,
      source_locator: rule?.source_locator ?? "",
      source_text: sourceText,
      governs_count: couplingGraph.edges.filter((edge) => edge.from_node === id).length,
    },
    geometry: {
      type: "Point",
      coordinates: displayPositionById.get(id),
    },
  };
});

const displayRegulatoryNodes = {
  type: "FeatureCollection",
  name: "APM drayage regulatory and context node display layer",
  schema_version: "1.0",
  feature_count: displayRegulatoryFeatures.length,
  layout_note:
    "Nonphysical nodes use a deterministic two-column display layout east of the roadway corridor; their coordinates are diagram positions, not real-world locations.",
  features: displayRegulatoryFeatures,
};

const edgeFeatureById = new Map(
  edgeFeatures.map((feature) => [feature.properties.edge_id, feature]),
);
const regulatoryFeatureById = new Map(
  displayRegulatoryFeatures.map((feature) => [feature.properties.node_id, feature]),
);

const midpointAlongLine = (coordinates) => {
  const segments = [];
  let total = 0;
  for (let index = 0; index < coordinates.length - 1; index += 1) {
    const start = coordinates[index];
    const end = coordinates[index + 1];
    const latitudeRadians = (((start[1] + end[1]) / 2) * Math.PI) / 180;
    const dx = (end[0] - start[0]) * Math.cos(latitudeRadians);
    const dy = end[1] - start[1];
    const length = Math.hypot(dx, dy);
    segments.push({ start, end, length });
    total += length;
  }
  let remaining = total / 2;
  for (const segment of segments) {
    if (remaining <= segment.length) {
      const ratio = segment.length === 0 ? 0 : remaining / segment.length;
      return [
        segment.start[0] + ratio * (segment.end[0] - segment.start[0]),
        segment.start[1] + ratio * (segment.end[1] - segment.start[1]),
      ];
    }
    remaining -= segment.length;
  }
  return [...coordinates.at(-1)];
};

const displayCoordinate = (id) => {
  if (physicalNodeById.has(id)) return physicalNodeById.get(id).geometry.coordinates;
  if (edgeFeatureById.has(id)) {
    return midpointAlongLine(edgeFeatureById.get(id).geometry.coordinates);
  }
  if (regulatoryFeatureById.has(id)) {
    return regulatoryFeatureById.get(id).geometry.coordinates;
  }
  throw new Error(`No display coordinate for coupling endpoint ${id}`);
};

const couplingAuthorityLevel = (edge) => {
  const ruleId = edge.from_node.startsWith("reg_")
    ? edge.from_node
    : edge.to_node.startsWith("reg_")
      ? edge.to_node
      : null;
  if (ruleId) return authorityLevel(ruleById.get(ruleId)?.authority_entity_id);
  if (edge.relationship === "LOCATED_WITHIN") return "Jurisdiction";
  if (edge.relationship === "HAS_NJOGIS_JURISDICTION_CATEGORY") {
    return "Road authority category";
  }
  return "Graph relation";
};

const couplingFeatures = couplingGraph.edges.map((edge) => ({
  type: "Feature",
  properties: {
    coupling_id: edge.edge_id,
    rule_id: edge.from_node,
    authority_level: couplingAuthorityLevel(edge),
    placement: edge.relationship,
    from_node: edge.from_node,
    relationship: edge.relationship,
    to_node: edge.to_node,
    source_ids: (edge.source_ids ?? []).join(" | "),
    applicability: edge.applicability_status ?? "",
  },
  geometry: {
    type: "LineString",
    coordinates: [displayCoordinate(edge.from_node), displayCoordinate(edge.to_node)],
  },
}));

const displayCouplings = {
  type: "FeatureCollection",
  name: "APM drayage regulatory coupling display layer",
  schema_version: "1.0",
  feature_count: couplingFeatures.length,
  features: couplingFeatures,
};

writeJson("data/processed/apm_drayage_edges.geojson", displayEdges);
writeJson("data/processed/apm_regulatory_nodes.geojson", displayRegulatoryNodes);
writeJson("data/processed/apm_regulatory_couplings.geojson", displayCouplings);

console.log(
  `Built ArcGIS display layers: ${edgeFeatures.length} physical edges, ${displayRegulatoryFeatures.length} regulatory/context nodes, ${couplingFeatures.length} couplings.`,
);
