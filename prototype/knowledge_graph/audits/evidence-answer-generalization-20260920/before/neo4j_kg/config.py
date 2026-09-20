"""Credentials stay outside the repository, receipts, and MCP responses."""
from __future__ import annotations

import os
from pathlib import Path

from .common import ArchiveError


def connect(credentials_file=None):
    config = dict(os.environ)
    path = credentials_file or config.get("NEO4J_CREDENTIALS_FILE")
    if path:
        for line in Path(path).read_text().splitlines():
            if line.strip() and not line.lstrip().startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()
    if not config.get("NEO4J_URI", "").startswith("neo4j+s://"):
        raise ArchiveError("Configure a certificate-verified Neo4j TLS connection")
    if not all(config.get(key) for key in ("NEO4J_USERNAME", "NEO4J_PASSWORD")):
        raise ArchiveError("Neo4j credentials are unavailable")
    import truststore
    truststore.inject_into_ssl()
    from neo4j import GraphDatabase
    driver = GraphDatabase.driver(
        config["NEO4J_URI"], auth=(config["NEO4J_USERNAME"], config["NEO4J_PASSWORD"]),
        connection_timeout=10, connection_acquisition_timeout=15,
        max_transaction_retry_time=10, max_connection_pool_size=4)
    return driver, config.get("NEO4J_DATABASE", "neo4j")
