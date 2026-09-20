"""Read the pinned Neo4j release and render an offline six-topic SVG/HTML."""
import html
import json
import sys
import textwrap
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from neo4j_kg.config import connect
from neo4j_kg.store import read_release
REVISION = 'f5dffe0f7a32b5144920efb5a644f8c4dc9f20def76b4217c38b0cdbc454cf5c'

def main():
    driver, database = connect(Path.home()/'.config/drayage-mcp/neo4j.env')
    try:
        with driver.session(database=database, default_access_mode='READ') as session:
            data = session.execute_read(lambda tx: read_release(tx, REVISION))
    finally:
        driver.close()
    layout = json.loads((ROOT/'presentation/organized-layout.json').read_text())
    aliases = json.loads((ROOT/'presentation/labels.json').read_text())
    positions = {k:[x,y+650 if y>=1550 else y] for k,(x,y) in layout['positions'].items()}
    nodes = data['nodes']; edges = data['edges']
    topics = {n:r['id'] for r in layout['regions'] for n in r['nodes']}
    extras = [n for n in nodes if n['id'] not in positions]
    for i,n in enumerate(extras):
        positions[n['id']] = [2940+(i%4)*275, 1190+(i//4)*150]
        topics[n['id']] = 'terminal'
    esc = lambda x: html.escape(str(x), quote=True)
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="4074" height="3500" viewBox="0 0 4074 3500">', '<rect width="100%" height="100%" fill="white"/>', '<style>text{font-family:Arial,sans-serif;fill:#344454}.label{font-size:14px;paint-order:stroke;stroke:white;stroke-width:4px;stroke-linejoin:round}.node:hover circle{stroke:#172f35;stroke-width:5}.edge{fill:none;stroke:#b7c0c8;stroke-width:1.2}</style>']
    svg.append('<defs><marker id="arrow" viewBox="0 0 10 10" refX="17" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M0 0 L10 5 L0 10z" fill="#b7c0c8"/></marker></defs>')
    for e in edges:
        a,b=e['from'],e['to']; x,y=positions[a]; u,v=positions[b]
        opacity='.18' if topics[a]!=topics[b] else '.65'
        svg.append(f'<path class="edge" marker-end="url(#arrow)" data-edge-id="{esc(e["id"])}" d="M{x},{y} L{u},{v}" opacity="{opacity}"><title>{esc(a)} → {esc(e["relationship"])} → {esc(b)}</title></path>')
    for r in layout['regions']:
        x,y=r['x'],r['y']+(650 if r['y']>=1550 else 0)
        svg.append(f'<rect x="{x}" y="{y}" width="{r["width"]}" height="92" fill="white"/><text x="{x+20}" y="{y+32}" font-size="30" font-weight="bold">{esc(r["title"])}</text><text x="{x+20}" y="{y+66}" font-size="19" fill="#667788">{esc(r["question"])}</text>')
    if extras:
        svg.append('<text x="2900" y="1110" font-size="20">Additional terminal records · includes synthetic fixtures</text>')
    for n in nodes:
        nid=n['id']; record=json.loads(n['record_json']); display=record.get('properties',record)
        label=aliases.get(nid) or display.get('name') or display.get('label') or display.get('title') or nid.replace('_',' ')
        kind=n['kind']; color='#53c5b0'
        if kind=='source_document': color='#b8a2e1'
        elif kind=='source_clause': color='#58b5dd'
        elif kind in ('physical_location','road_segment','route_family','route_approach'): color='#8ba5ed'
        elif kind in ('mutable_observation','historical_traffic_analysis'): color='#f1a071'
        elif kind in ('credential','registration','operational_system','training','project_profile_not_live_vehicle') or nid in {v['id'] for v in extras}: color='#e4a7d9'
        x,y=positions[nid]
        svg.append(f'<g class="node" data-node-id="{esc(nid)}"><title>{esc(label)}\n{esc(kind)}\n{esc(json.dumps(record,ensure_ascii=False,indent=2))}</title><circle cx="{x}" cy="{y}" r="12" fill="{color}" stroke="{color}" stroke-width="3"/>')
        lines = textwrap.wrap(str(label),27)
        if len(lines)>3: lines=lines[:2]+[textwrap.shorten(' '.join(lines[2:]),27,placeholder='…')]
        if n['layer']=='quarantined_observation': lines.append('Dated · quarantined')
        for j,line in enumerate(lines):
            svg.append(f'<text class="label" x="{x}" y="{y+29+j*17}" text-anchor="middle">{esc(line)}</text>')
        svg.append('</g>')
    svg.append('</svg>'); content='\n'.join(svg)
    out=ROOT/'output/knowledge-graph-visual'; out.mkdir(exist_ok=True)
    (out/'knowledge-graph.svg').write_text(content)
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Trucker & Dispatch · Knowledge Graph</title><style>body{margin:0;background:white;color:#344454;font:14px Arial}header{position:sticky;top:0;background:#ffffffed;padding:16px 24px;border-bottom:1px solid #e7ebef;z-index:1}h1{font-size:20px;margin:0 0 8px}button,a{margin-right:12px;color:#344454}main{overflow:auto;height:calc(100vh - 110px)}svg{width:100%;height:auto;display:block}p{margin:8px 0}</style><header><h1>Trucker & Dispatch · Knowledge Graph</h1><p>144 records · 228 relationships · Neo4j snapshot · September 10, 2026</p><button onclick="zoom(1.3)">Zoom +</button><button onclick="zoom(1/1.3)">Zoom −</button><button onclick="scale=1;draw()">Fit width</button><a href="knowledge-graph.svg">Open full-resolution SVG</a><span>Hover over a node for its record. Prototype evidence is not trip clearance.</span></header><main>'''+content+'''</main><script>let scale=1;function draw(){document.querySelector('svg').style.width=(scale*100)+'%'}function zoom(f){scale=Math.max(.5,Math.min(6,scale*f));draw()}</script></html>'''
    (out/'index.html').write_text(page)
    (out/'snapshot.json').write_text(json.dumps(data,indent=2))
    assert content.count('class="node"')==len(nodes)==144
    assert content.count('class="edge"')==len(edges)==228
    print(json.dumps({'nodes':len(nodes),'relationships':len(edges),'additional_records':len(extras),'output':str(out)}))
if __name__=='__main__': main()
