"""Author topic-local Graphviz layouts; no new nodes/edges enter the graph."""
import json
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from evidence_graph import EvidenceGraph
from export_graph import snapshot
from organize_graph import connected_view
from graph_presentation import topology_key, label_lines, label_width

data=connected_view(snapshot(EvidenceGraph()))
aliases=json.loads((ROOT/'presentation/labels.json').read_text())
nodes={n['id']:n for n in data['nodes']}
positions={};regions=[]
for i,topic in enumerate(data['presentation']['topics']):
    # Explicit topical placement is separate from graph connectivity.
    # Graphviz arranges actual relationships within each topic.
    lines=['strict graph G {','graph [overlap=prism, sep="+24", start=17, K=1.1, pack=20];','node [shape=box, width=2.4, height=1.25, fixedsize=true, label=""];']
    for n in topic['nodes']:lines.append(json.dumps(n)+';')
    for e in data['edges']:
        if e['source'] in topic['nodes'] and e['target'] in topic['nodes']:
            lines.append(json.dumps(e['source'])+' -- '+json.dumps(e['target'])+';')
    lines.append('}')
    r=subprocess.run(['sfdp','-Tjson'],input='\n'.join(lines),text=True,capture_output=True,check=True)
    objects=json.loads(r.stdout)['objects']
    raw={n['name']:list(map(float,n['pos'].split(','))) for n in objects}
    xmin=min(p[0] for p in raw.values());xmax=max(p[0] for p in raw.values())
    ymin=min(p[1] for p in raw.values());ymax=max(p[1] for p in raw.values())
    local={n:[120+(x-xmin)/(xmax-xmin or 1)*900,160+(ymax-y)/(ymax-ymin or 1)*640] for n,(x,y) in raw.items()}
    if topic['id']=='roads':
        # A schematic of the stored approach/segment sequence. Coordinates
        # organize existing nodes; they add no road or permission relationship.
        local={
          'path_a_exit13a_to_apm':[100,100], 'approach_a_turnpike_sb':[330,100], 'approach_a_turnpike_nb':[560,100],
          'node_path_a_turnpike_sb_exit13a':[330,270], 'edge_a_exit13a_connector':[610,270],
          'node_a_nb_turnpike_exit13a':[100,450], 'edge_a_nb_turnpike_exit':[330,450],
          'node_a_nb_turnpike_state_ramp_transition':[560,450], 'edge_a_nb_state_ramps_to_north_ave':[560,620],
          'node_a_nb_joins_north_ave':[790,620], 'edge_ab_shared_north_ave_to_all_merge':[1010,620],
          'path_b_us1_9_to_apm':[100,790], 'node_path_b_us1_south_access':[100,950],
          'edge_b_us1_south':[330,950], 'node_path_b_north_avenue_entry':[560,950], 'edge_b_north_avenue_to_merge':[790,950],
          'node_paths_merge_north_avenue':[1280,230], 'edge_shared_north_avenue':[1280,390],
          'node_north_avenue_mclester':[1280,550], 'edge_shared_mclester':[1280,710],
          'node_mclester_tripoli':[1280,870], 'edge_shared_tripoli_gate':[1280,1030],
          'apm_directions':[330,1160], 'google_maps_route_observation_2026_07_31':[640,1160],
          'njogis_road_centerlines_2026_07_26':[950,1160],
        }
        assert set(local)==set(topic['nodes'])
    boxes={n:(max(label_width(t) for t in label_lines(nodes[n],aliases)), 100 if nodes[n]['layer']=='quarantined_observation' else 80) for n in local}
    ids=sorted(local)
    for _ in range(600):
        moved=False
        for j,a in enumerate(ids):
            for b in ids[j+1:]:
                dx=local[b][0]-local[a][0];dy=local[b][1]-local[a][1]
                ox=(boxes[a][0]+boxes[b][0])/2+18-abs(dx);oy=(boxes[a][1]+boxes[b][1])/2+14-abs(dy)
                if ox>0 and oy>0:
                    axis=0 if ox<oy else 1;amount=((ox if axis==0 else oy)+.1)/2*(1 if (dx if axis==0 else dy)>=0 else -1)
                    local[a][axis]-=amount;local[b][axis]+=amount;moved=True
        if not moved:break
    minx=min(p[0]-boxes[n][0]/2 for n,p in local.items());miny=min(p[1] for p in local.values())
    local={n:[x-minx+35,y-miny+160] for n,(x,y) in local.items()}
    width=max(p[0]+boxes[n][0]/2 for n,p in local.items())+35
    height=max(p[1]+boxes[n][1] for n,p in local.items())+45
    regions.append({**topic,'local_positions':local,'width':width,'height':height})
column_widths=[max(regions[c]['width'],regions[c+3]['width']) for c in range(3)]
row_heights=[max(r['height'] for r in regions[:3]),max(r['height'] for r in regions[3:])]
for i,region in enumerate(regions):
    col=i%3;row=i//3
    x=sum(column_widths[:col])+col*110+45;y=sum(row_heights[:row])+row*150+55
    region['x']=x;region['y']=y
    positions.update({n:[x+px,y+py] for n,(px,py) in region.pop('local_positions').items()})
result={'topology_key':topology_key(data),'engine':'Authored route schematic and Graphviz topic layouts','positions':positions,'regions':regions,'width':sum(column_widths)+330,'height':sum(row_heights)+260}
(ROOT/'presentation/organized-layout.json').write_text(json.dumps(result,indent=2)+'\n')
print('Saved',len(positions),'nodes;',result['width'],result['height'])
