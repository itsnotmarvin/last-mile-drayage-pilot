"""Small-node whole-graph rendering from saved graph-layout coordinates.

Presentation aliases and colors do not change evidence records or topology.
"""
import html
import json
import math
import textwrap
from pathlib import Path
from kg.graph import digest

PRESENTATION = Path(__file__).parent / 'presentation'
PALETTE = {
    'Sources': ('#b8a2e1', '#7656ab'),
    'Rules': ('#58b5dd', '#237fa7'),
    'Authorities & places': ('#53c5b0', '#248775'),
    'Roads & routes': ('#8ba5ed', '#526fba'),
    'Credentials & profiles': ('#e4a7d9', '#a65b99'),
    'Dated observations & analysis': ('#f1a071', '#b86836'),
}


def category(node):
    kind = node['kind']
    if kind == 'source_document': return 'Sources'
    if kind == 'source_clause': return 'Rules'
    if kind in ('physical_location', 'road_segment', 'route_family', 'route_approach'): return 'Roads & routes'
    if kind in ('mutable_observation', 'historical_traffic_analysis'): return 'Dated observations & analysis'
    if kind in ('credential', 'registration', 'operational_system', 'training', 'project_profile_not_live_vehicle'): return 'Credentials & profiles'
    return 'Authorities & places'


def topology_key(data):
    return digest({'nodes': sorted(n['id'] for n in data['nodes']),
                   'pairs': sorted(set(tuple(sorted((e['source'], e['target']))) for e in data['edges']))})


def layout(data):
    key = topology_key(data)
    path = PRESENTATION / (key + '.json')
    if path.exists():
        saved = json.loads(path.read_text())
        positions = saved['positions']
        if saved['topology_key'] != key or set(positions) != {n['id'] for n in data['nodes']}:
            raise ValueError('Layout artifact does not match graph topology')
        if any(len(p) != 2 or not all(isinstance(x, (int, float)) and math.isfinite(x) for x in p) for p in positions.values()):
            raise ValueError('Invalid layout coordinates')
        # The saved authoring boxes include breathing room for labels below dots.
        positions = {n: [x*.62, -y*.62] for n, (x, y) in positions.items()}
        engine = saved['engine']
    else:
        # Honest fallback for unseen topologies; no external executable required.
        ids = sorted(n['id'] for n in data['nodes'])
        r = max(180, len(ids)*30)
        positions = {n: [r*math.cos(i*2*math.pi/max(1,len(ids))), r*math.sin(i*2*math.pi/max(1,len(ids)))] for i,n in enumerate(ids)}
        engine = 'circular fallback; no matching saved layout'
    minx = min((p[0] for p in positions.values()), default=0)
    miny = min((p[1] for p in positions.values()), default=0)
    positions = {n: [x-minx+115, y-miny+65] for n, (x, y) in positions.items()}
    width = max((p[0] for p in positions.values()), default=0)+115
    height = max((p[1] for p in positions.values()), default=0)+110
    return positions, width, height, engine



def label_lines(node, aliases):
    short = aliases.get(node['id'], node['label'].replace('_', ' '))
    lines = textwrap.wrap(short, 24)
    if len(lines) > 3:
        lines = lines[:2] + [textwrap.shorten(' '.join(lines[2:]), 24, placeholder='…')]
    return lines


def label_width(text):
    # Conservative Arial 14px estimate, including white text halo.
    narrow, wide = " ilI.,:;!'|", 'MWmw@%'
    return sum(4 if c in narrow else 12 if c in wide else 8 for c in text) + 12


def readable_positions(data):
    if data.get("presentation"):
        from organize_graph import topic_layout
        saved = topic_layout(data)
        return saved["positions"], saved["width"], saved["height"], saved["engine"], {}
    positions, _, _, engine = layout(data)
    aliases = json.loads((PRESENTATION / 'labels.json').read_text())
    degree = {n['id']: 0 for n in data['nodes']}
    for edge in data['edges']:
        degree[edge['source']] += 1
        degree[edge['target']] += 1
    boxes = {}
    for node in data['nodes']:
        lines = label_lines(node, aliases)
        status = 'Dated · quarantined' if node['layer'] == 'quarantined_observation' else 'No supported connection' if degree[node['id']] == 0 else ''
        box_lines = lines + ([status] if status else [])
        boxes[node['id']] = (max([46] + [label_width(t) for t in box_lines]), 47 + len(box_lines)*16)
    # Reserve the node and its external label together. Move only overlapping
    # rectangles, retaining the Graphviz neighborhood structure.
    ids = sorted(positions)
    for _ in range(400):
        moved = False
        for i, a in enumerate(ids):
            for b in ids[i+1:]:
                ax,ay = positions[a]; bx,by = positions[b]
                wa,ha = boxes[a]; wb,hb = boxes[b]
                dx = bx-ax
                dy = (by+hb/2-18)-(ay+ha/2-18)
                ox = (wa+wb)/2+12-abs(dx)
                oy = (ha+hb)/2+10-abs(dy)
                if ox > .05 and oy > .05:
                    if ox < oy:
                        shift = (ox+.1)/2 * (1 if dx >= 0 else -1)
                        positions[a][0] -= shift; positions[b][0] += shift
                    else:
                        shift = (oy+.1)/2 * (1 if dy >= 0 else -1)
                        positions[a][1] -= shift; positions[b][1] += shift
                    moved = True
        if not moved:
            break
    minx = min((p[0]-boxes[n][0]/2 for n,p in positions.items()), default=0)
    miny = min((p[1]-18 for p in positions.values()), default=0)
    positions = {n: [x-minx+30, y-miny+30] for n,(x,y) in positions.items()}
    width = max((p[0]+boxes[n][0]/2 for n,p in positions.items()), default=0)+30
    height = max((p[1]-18+boxes[n][1] for n,p in positions.items()), default=0)+30
    return positions, width, height, engine, boxes

def full_graph_svg(data):
    esc = lambda value: html.escape(str(value), quote=True)
    aliases = json.loads((PRESENTATION / 'labels.json').read_text())
    positions, width, height, engine, _ = readable_positions(data)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" data-layout-engine="{esc(engine)}" role="img" aria-label="All {len(data["nodes"])} retained nodes and {len(data["edges"])} directed relationships">',
        '<style>text{font-family:Arial,sans-serif;fill:#263442}.edge{stroke:#b7c0c8;stroke-width:1.15;fill:none;opacity:.8}.edge.provenance{stroke:#c0c8cf;opacity:.72}.edge.cross-topic{opacity:.18}.edge.cross-topic.selected{opacity:1}.edge-label{font-size:11px;fill:#52606b;paint-order:stroke;stroke:white;stroke-width:4;stroke-linejoin:round;visibility:hidden}.all-edge-labels .edge-label,.edge-label.selected{visibility:visible}.node-circle{stroke-width:2}.node.selected .node-circle{stroke:#152434;stroke-width:4}.edge.selected{stroke:#596d80;stroke-width:2;opacity:1}.edge-label.selected{fill:#172f45}.node-label{font-size:14px;paint-order:stroke;stroke:#fff;stroke-width:4;stroke-linejoin:round}.node.selected .node-label{font-weight:bold}.node text{pointer-events:none}.node-hit{fill:transparent;stroke:none}</style>',
        '<rect width="100%" height="100%" fill="white"/>',
        '<defs><marker id="full-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0 L10 5 L0 10z" fill="#a3b0ba"/></marker></defs>']
    topic_by_node = {}
    headings = []
    if data.get('presentation'):
        from organize_graph import topic_layout
        for region in topic_layout(data)['regions']:
            x,y,w,h = region['x'],region['y'],region['width'],region['height']
            headings.append(f'<g class="topic-heading" data-topic-id="{esc(region["id"])}" data-x="{x}" data-y="{y}" data-width="{w}" data-height="{h}"><rect x="{x}" y="{y}" width="{w}" height="92" fill="white"/><text x="{x+20}" y="{y+32}" style="font-size:30px;font-weight:bold">{esc(region["title"])}</text><text x="{x+20}" y="{y+66}" style="font-size:19px;fill:#536677">{esc(region["question"])}</text></g>')
            topic_by_node.update({n: region['id'] for n in region['nodes']})
    pair_groups = {}
    for edge in data['edges']:
        pair = tuple(sorted((edge['source'], edge['target'])))
        pair_groups.setdefault(pair, []).append(edge['id'])
    degree = {n['id']: 0 for n in data['nodes']}
    labels = []
    for edge in data['edges']:
        degree[edge['source']] += 1; degree[edge['target']] += 1
        a, b = positions[edge['source']], positions[edge['target']]
        dx, dy = b[0]-a[0], b[1]-a[1]
        distance = math.hypot(dx,dy) or 1
        pair = tuple(sorted((edge['source'], edge['target'])))
        group = pair_groups[pair]
        # Canonical normal separates reciprocal as well as parallel edges.
        offset = (group.index(edge['id'])-(len(group)-1)/2)*20
        direction = 1 if edge['source'] == pair[0] else -1
        cx, cy = (a[0]+b[0])/2-dy/distance*offset*direction, (a[1]+b[1])/2+dx/distance*offset*direction
        d1 = math.hypot(cx-a[0],cy-a[1]) or 1
        d2 = math.hypot(b[0]-cx,b[1]-cy) or 1
        x1,y1 = a[0]+(cx-a[0])/d1*14, a[1]+(cy-a[1])/d1*14
        x2,y2 = b[0]-(b[0]-cx)/d2*17, b[1]-(b[1]-cy)/d2*17
        eid, source, target, relation = map(esc,(edge['id'],edge['source'],edge['target'],edge['relationship']))
        provenance = edge['relationship'] in ('CITES_SOURCE','CONTAINS_CLAUSE','OBSERVED_IN_SOURCE','ATTRIBUTED_TO_AUTHORITY')
        cls = 'edge provenance' if provenance else 'edge'
        if topic_by_node and topic_by_node[edge['source']] != topic_by_node[edge['target']]:
            cls += ' cross-topic'
        out.append(f'<path class="{cls}" data-edge-id="{eid}" data-source="{source}" data-target="{target}" d="M{x1:.2f},{y1:.2f} Q{cx:.2f},{cy:.2f} {x2:.2f},{y2:.2f}" marker-end="url(#full-arrow)"><title>{relation}</title></path>')
        lx,ly = .25*x1+.5*cx+.25*x2, .25*y1+.5*cy+.25*y2
        angle = math.degrees(math.atan2(dy,dx))
        if angle>90:angle-=180
        if angle< -90:angle+=180
        labels.append(f'<text class="edge-label" data-edge-label="{eid}" data-source="{source}" data-target="{target}" x="{lx:.2f}" y="{ly-5:.2f}" transform="rotate({angle:.2f} {lx:.2f} {ly:.2f})" text-anchor="middle">{relation}</text>')
    out.extend(labels)
    out.extend(headings)
    for node in data['nodes']:
        x,y = positions[node['id']]
        nid, label = esc(node['id']), esc(node['label'])
        group = category(node)
        fill, stroke = PALETTE[group]
        quarantine = node['layer'] == 'quarantined_observation'
        dash = ' stroke-dasharray="3 2"' if quarantine else ''
        lines = label_lines(node, aliases)
        out.append(f'<g class="node{" quarantine" if quarantine else ""}" data-node-id="{nid}" data-x="{x:.2f}" data-y="{y:.2f}" data-category="{esc(group)}" role="button" tabindex="0" aria-label="{label}"><title>{label} · {esc(node["kind"])}{" · quarantined" if quarantine else ""}</title><circle class="node-hit" cx="{x:.2f}" cy="{y:.2f}" r="23"/><circle class="node-circle" cx="{x:.2f}" cy="{y:.2f}" r="12" fill="{fill}" stroke="{stroke}"{dash}/>')
        for i,line in enumerate(lines):
            out.append(f'<text class="node-label" x="{x:.2f}" y="{y+29+i*16:.2f}" text-anchor="middle">{esc(line)}</text>')
        status = 'Dated · quarantined' if quarantine else 'No supported connection' if degree[node['id']]==0 else ''
        if status:out.append(f'<text class="node-label" x="{x:.2f}" y="{y+29+len(lines)*16:.2f}" text-anchor="middle" style="font-size:11px;fill:#795037">{status}</text>')
        out.append('</g>')
    out.append('</svg>')
    return '\n'.join(out)
