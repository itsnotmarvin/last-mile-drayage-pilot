"""Read-only archive import into a directed, attributed multigraph.

Archive relationships retain their original meaning and are not executable
policy. New checking definitions live in a separate prototype layer.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import networkx as nx


ARCHIVE = Path(__file__).resolve().parents[3]
INPUTS = (
    "data/metadata.json",
    "data/processed/entity_nodes.json",
    "data/processed/regulatory_nodes.json",
    "data/processed/regulatory_edges.json",
    "data/processed/physical_nodes.geojson",
    "data/processed/physical_edges.json",
    "data/processed/coupling_edges.json",
    "data/processed/vehicle_profiles.json",
    "data/processed/mutable_conditions.json",
)


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


class ArchiveError(ValueError):
    """The archive cannot be imported without losing evidence integrity."""


class KnowledgeGraph:
    def __init__(self, archive: Path = ARCHIVE):
        self.archive = archive.resolve()
        self.graph = nx.MultiDiGraph()
        self.input_hashes: dict[str, str] = {}
        self.documents: dict[str, dict] = {}
        for relative in INPUTS:
            raw = self._path(relative).read_bytes()
            self.input_hashes[relative] = hashlib.sha256(raw).hexdigest()
            self.documents[relative] = json.loads(raw)
        self.evidence_version = digest(self.input_hashes)
        self._import()
        nx.freeze(self.graph)

    def _path(self, relative: str) -> Path:
        path = (self.archive / relative).resolve()
        if not path.is_relative_to(self.archive):
            raise ArchiveError(f"Archive path escapes its root: {relative}")
        return path

    def _node(self, node_id: str, kind: str, record: dict, layer: str = "archive"):
        if node_id in self.graph:
            raise ArchiveError(f"Duplicate node: {node_id}")
        self.graph.add_node(node_id, kind=kind, layer=layer, record=copy.deepcopy(record))

    def _edge(self, edge_id: str, start: str, relation: str, end: str, record: dict):
        if start not in self.graph or end not in self.graph:
            raise ArchiveError(f"Dangling relationship: {edge_id}: {start} -> {end}")
        if any(edge_id == k for _, _, k in self.graph.edges(keys=True)):
            raise ArchiveError(f"Duplicate edge: {edge_id}")
        self.graph.add_edge(start, end, key=edge_id, relationship=relation,
                            record=copy.deepcopy(record))

    def _import(self):
        for source in self.documents[INPUTS[0]]["sources"]:
            self._node(source["source_id"], "source_document", source)
        for entity in self.documents[INPUTS[1]]["entities"]:
            self._node(entity["entity_id"], entity["entity_type"], entity)
        for rule in self.documents[INPUTS[2]]["rules"]:
            self._node(rule["rule_id"], "source_clause", rule)
            self._edge("contains:" + rule["rule_id"], rule["source_id"], "CONTAINS_CLAUSE",
                       rule["rule_id"], {"derived_from": INPUTS[2]})
        for feature in self.documents[INPUTS[4]]["features"]:
            self._node(feature["properties"]["node_id"], "physical_location", feature)
        physical = self.documents[INPUTS[5]]
        for segment in physical["edges"]:
            self._node(segment["edge_id"], "road_segment", segment)
            self._edge("starts:" + segment["edge_id"], segment["edge_id"], "STARTS_AT",
                       segment["from_node"], {})
            self._edge("ends:" + segment["edge_id"], segment["edge_id"], "ENDS_AT",
                       segment["to_node"], {})
        for key, id_key, kind in (("paths", "path_id", "route_family"),
                                  ("approaches", "approach_id", "route_approach")):
            for route in physical[key]:
                self._node(route[id_key], kind, route)
                for sequence, segment_id in enumerate(route["ordered_edge_ids"], 1):
                    self._edge(f"segment:{route[id_key]}:{sequence}", route[id_key],
                               "HAS_ORDERED_SEGMENT", segment_id, {"sequence": sequence})
        for profile in self.documents[INPUTS[7]]["profiles"]:
            self._node(profile["profile_id"], "project_profile_not_live_vehicle", profile)
        for relative in (INPUTS[3], INPUTS[6]):
            for edge in self.documents[relative]["edges"]:
                self._edge(edge["edge_id"], edge["from_node"], edge["relationship"],
                           edge["to_node"], edge)
        conditions = self.documents[INPUTS[8]]
        for condition in conditions["conditions"]:
            record = {"archive_context": {k: v for k, v in conditions.items()
                                           if k != "conditions"}, **condition}
            self._node(condition["condition_id"], "mutable_observation", record,
                       layer="quarantined_observation")

    def record(self, node_id: str) -> dict:
        return copy.deepcopy(self.graph.nodes[node_id]["record"])

    def related(self, node_id: str, relationship: str | None = None) -> list[dict]:
        if node_id not in self.graph:
            raise KeyError(node_id)
        return sorted([
            {"from": start, "to": end, "edge_id": key,
             "relationship": data["relationship"], "record": copy.deepcopy(data["record"])}
            for start, end, key, data in self.graph.out_edges(node_id, keys=True, data=True)
            if relationship is None or data["relationship"] == relationship
        ], key=lambda edge: edge["edge_id"])

    def citation(self, clause_id: str) -> dict:
        if self.graph.nodes[clause_id]["kind"] != "source_clause":
            raise ArchiveError(f"Not a clause: {clause_id}")
        clause = self.record(clause_id)
        source = self.record(clause["source_id"])
        return {"clause_id": clause_id, "source_id": source["source_id"],
                "publisher": source["publisher"], "title": source["title"],
                "url": source["url"], "locator": clause["source_locator"],
                "source_text": clause["source_text"],
                "publication_date": source.get("publication_date"),
                "accessed_date": source.get("accessed_date"),
                "archived_files": source.get("archived_files", []),
                "currentness": "archived_evidence_only_not_verified_for_this_trip"}

    def verify_archives(self) -> list[str]:
        checked = []
        for source in self.documents[INPUTS[0]]["sources"]:
            for archived in source.get("archived_files", []):
                path = self._path(archived["path"])
                actual = hashlib.sha256(path.read_bytes()).hexdigest()
                if actual != archived["sha256"]:
                    raise ArchiveError(f"Archive checksum mismatch: {archived['path']}")
                checked.append(archived["path"])
        return sorted(set(checked))

    def summary(self) -> dict:
        kinds: dict[str, int] = {}
        for _, data in self.graph.nodes(data=True):
            kinds[data["kind"]] = kinds.get(data["kind"], 0) + 1
        return {"engine": "NetworkX 3.6.1 in-memory MultiDiGraph; not a database server",
                "evidence_version": self.evidence_version,
                "node_count": self.graph.number_of_nodes(),
                "edge_count": self.graph.number_of_edges(), "node_kinds": kinds,
                "operational_use": False}

