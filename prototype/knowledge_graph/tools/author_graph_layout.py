"""Optional authoring tool: save coordinates using an existing Graphviz install.

The exporter reads these artifacts with stdlib; it does not invoke Graphviz.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evidence_graph import EvidenceGraph
from kg.graph import KnowledgeGraph, digest


def topology_key(nodes, edges):
    return digest({'nodes': sorted(nodes), 'pairs': sorted(set(tuple(sorted(e)) for e in edges))})


def author(kg):
    nodes = sorted(kg.graph)
    pairs = sorted(set(tuple(sorted((a, b))) for a, b in kg.graph.edges()))
    lines = ['strict graph G {', 'graph [overlap=prism, sep="+24", start=17, K=1.4, repulsiveforce=2, pack=36];',
             'node [shape=box, width=2.1, height=0.95, fixedsize=true, label=""];']
    lines.extend(json.dumps(n) + ';' for n in nodes)
    lines.extend(json.dumps(a) + ' -- ' + json.dumps(b) + ';' for a, b in pairs)
    lines.append('}')
    source = '\n'.join(lines)
    run = subprocess.run(['sfdp', '-Tjson'], input=source, text=True, capture_output=True, check=True)
    output = json.loads(run.stdout)
    positions = {n['name']: list(map(float, n['pos'].split(','))) for n in output['objects']}
    key = topology_key(nodes, pairs)
    result = {'topology_key': key, 'engine': 'Graphviz sfdp',
              'engine_version': subprocess.run(['sfdp', '-V'], text=True, capture_output=True, check=True).stderr.strip(),
              'authoring_options': 'overlap=prism, sep=+24, start=17, K=1.4, repulsiveforce=2, pack=36',
              'positions': positions}
    (ROOT / 'presentation' / (key + '.json')).write_text(json.dumps(result, indent=2) + '\n')
    (ROOT / 'presentation' / (key + '.dot')).write_text(source + '\n')
    print(key, len(positions), output['bb'])


if __name__ == '__main__':
    author(KnowledgeGraph())
    author(EvidenceGraph())
