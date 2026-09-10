"""Versioned evidence serialization shared by import and read-only runtime."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT.parents[1]
DATASET = "last-mile-drayage-pilot"
SCHEMA = "drayage-neo4j-release-v1"


class ArchiveError(ValueError):
    """Missing, changed, or inconsistent evidence; never an evaluation outcome."""


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def digest(value):
    return hashlib.sha256(encode(value).encode()).hexdigest()


def validate_release(release):
    body = {key: value for key, value in release.items() if key != "revision"}
    if release.get("revision") != digest(body):
        raise ArchiveError("Release content does not match its revision")
    if release.get("schema_version") != SCHEMA or release.get("dataset") != DATASET:
        raise ArchiveError("Unsupported evidence dataset or schema")
    nodes = release["nodes"]
    edges = release["edges"]
    ids = {n["id"] for n in nodes}
    if len(ids) != len(nodes) or len({e["id"] for e in edges}) != len(edges):
        raise ArchiveError("Duplicate record or relationship identity")
    if any(e["from"] not in ids or e["to"] not in ids for e in edges):
        raise ArchiveError("Relationship endpoint missing from release")
    if [n["ordinal"] for n in nodes] != list(range(len(nodes))):
        raise ArchiveError("Invalid record order")
    if [e["ordinal"] for e in edges] != list(range(len(edges))):
        raise ArchiveError("Invalid relationship order")
    return release


def verify_files(release, archive=ARCHIVE):
    """Verify actual source bytes, including originals referenced by the registry."""
    archive = archive.resolve()
    for relative, expected in release["file_hashes"].items():
        path = (archive / relative).resolve()
        if not path.is_relative_to(archive) or not path.is_file():
            raise ArchiveError("A required evidence file is unavailable")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ArchiveError("Evidence file changed; build and validate a new release")
