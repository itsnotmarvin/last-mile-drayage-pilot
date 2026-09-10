"""Build a portable, lossless public-evidence snapshot and offline explorer.

This exports the archive layer, including explicitly quarantined observations.
It does not activate rules or include the service's synthetic driver fixtures.
"""

import argparse
import copy
import json
import html
from pathlib import Path

import networkx as nx

from evidence_graph import EvidenceGraph
from graph_presentation import full_graph_svg
from organize_graph import connected_view


def snapshot(kg):
    checked = kg.verify_archives()
    nodes = []
    for node_id, attrs in sorted(kg.graph.nodes(data=True)):
        record = attrs["record"]
        display = record.get("properties", record)
        label = next((display[k] for k in ("name", "label", "title")
                      if isinstance(display.get(k), str)), "North Avenue historical traffic analysis" if attrs["kind"] == "historical_traffic_analysis" else node_id)
        nodes.append({"id": node_id, "label": label, **copy.deepcopy(attrs)})
    edges = [{"id": key, "source": start, "target": end, **copy.deepcopy(attrs)}
             for start, end, key, attrs in kg.graph.edges(keys=True, data=True)]
    edges.sort(key=lambda e: e["id"])
    return {"schema_version": "drayage-public-evidence-v1",
            "summary": kg.summary(), "input_hashes": dict(kg.input_hashes),
            "verified_archive_files": checked,
            "scope": kg.summary().get("graph_scope", "All records imported from the nine retained graph inputs; archived evidence, not current trip clearance."),
            "nodes": nodes, "edges": edges}


def render_html(data):
    template = (Path(__file__).parent / "kg" / "explorer.html").read_text()
    # A quoted source excerpt must never terminate the embedded JSON script.
    payload = json.dumps(data, ensure_ascii=False, allow_nan=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return template.replace("__GRAPH_DATA__", payload)



def render_full_graph(data, svg):
    template = (Path(__file__).parent / 'kg' / 'full_graph.html').read_text()
    payload = json.dumps(data, ensure_ascii=False, allow_nan=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    for variable, fallback in [('foreground', '#172f35'), ('border', '#a9b9b7'), ('background', '#f6f8f6'), ('viz-series-1', '#177867'), ('viz-series-2', '#b77724')]:
        svg = svg.replace(f'var(--{variable},{fallback})', f'var(--{variable})')
    return (template.replace('__FULL_SVG__', svg).replace('__GRAPH_DATA__', payload)
            .replace('__GRAPH_TITLE__', 'Connected drayage graph' if data.get('presentation') else 'Entire drayage knowledge graph')
            .replace('__NODE_COUNT__', str(len(data['nodes'])))
            .replace('__EDGE_COUNT__', str(len(data['edges'])))
            .replace('__ISOLATE_COUNT__', str(data['summary'].get('isolated_node_count', 34))))


def export(output):
    kg = EvidenceGraph()
    archive_data = snapshot(kg)
    archive_data["connectivity_audit"] = kg.audit()
    data = connected_view(archive_data)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "graph-archive.json").write_text(json.dumps(archive_data, indent=2, ensure_ascii=False) + "\n")
    inventory = "<!doctype html><html lang=\"en\"><meta charset=\"utf-8\"><title>Source inventory</title><body><h1>Archived source inventory</h1><p>The 2020 facilities map is retained here as an unlinked reference. It is excluded from the connected graph.</p><a href=\"index.html\">Connected graph</a>"
    for node in archive_data["nodes"]:
        if node["kind"] == "source_document":
            inventory += "<details><summary>" + html.escape(node["label"]) + "</summary><pre>" + html.escape(json.dumps(node["record"], indent=2)) + "</pre></details>"
    (output / "source-inventory.html").write_text(inventory + "</body></html>")
    (output / "connectivity-audit.json").write_text(json.dumps(kg.audit(), indent=2) + "\n")
    (output / "graph.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    # GraphML scalar attributes contain the complete nested records as JSON.
    portable = nx.MultiDiGraph(evidence_version=kg.evidence_version, operational_use=False)
    for node in data["nodes"]:
        portable.add_node(node["id"], label=node["label"], kind=node["kind"],
                          layer=node["layer"], record_json=json.dumps(node["record"], ensure_ascii=False))
    for edge in data["edges"]:
        portable.add_edge(edge["source"], edge["target"], key=edge["id"],
                          relationship=edge["relationship"],
                          record_json=json.dumps(edge["record"], ensure_ascii=False))
    nx.write_graphml(portable, output / "graph.graphml")
    (output / "explorer.html").write_text(render_html(data))
    svg = full_graph_svg(data)
    (output / 'entire-graph.svg').write_text(svg)
    fragment = render_full_graph(data, svg)
    (output / 'entire-graph.html').write_text(fragment)
    shell = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Entire drayage knowledge graph</title><style>:root{--background:#f6f8f6;--foreground:#172f35;--border:#a9b9b7;--viz-series-1:#177867;--viz-series-2:#b77724}body{margin:24px;font:15px/1.5 system-ui;color:var(--foreground);background:var(--background)}button,select{font:inherit;padding:8px 12px;margin:4px}a{color:#177867}.viz-controls{display:flex;flex-wrap:wrap;align-items:center;gap:8px}</style><body>'
    (output / 'index.html').write_text(shell + fragment + '<p><a href="explorer.html">Open neighborhood explorer</a> · <a href="entire-graph.svg">Full-resolution SVG</a> · <a href="connectivity-audit.json">Connection audit</a> · <a href="source-inventory.html">Source inventory</a> · <a href="graph-archive.json">Complete archive</a> · <a href="graph.json">Connected JSON</a> · <a href="graph.graphml">GraphML</a></p></body></html>')
    (output / "organized-graph.html").write_text((output / "index.html").read_text())
    (output / "readable-graph.html").write_text((output / "index.html").read_text())
    return data["summary"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "output" / "evidence-graph")
    print(json.dumps(export(parser.parse_args().output), indent=2))
