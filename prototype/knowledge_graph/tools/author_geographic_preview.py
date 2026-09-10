"""Map existing physical records using their archived NJOGIS geometry.

No graph records are changed. Run from any directory; render the resulting
SVG with the already installed rsvg-convert to obtain the companion PNG.
"""
import hashlib
import html
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
OUT = ROOT / 'output/geographic-preview'
COS = math.cos(math.radians(40.672))
M = 6371008.8 * math.pi / 180


def xy(p):
    return (p[0] * M * COS, p[1] * M)


def clip_at_gate(coords, gate):
    """End the road on the centerline nearest the separately observed gate."""
    gx, gy = xy(gate)
    best = None
    for i, (a, b) in enumerate(zip(coords, coords[1:])):
        ax, ay = xy(a)
        bx, by = xy(b)
        dx, dy = bx-ax, by-ay
        t = max(0, min(1, ((gx-ax)*dx + (gy-ay)*dy)/(dx*dx+dy*dy)))
        point = [a[0]+t*(b[0]-a[0]), a[1]+t*(b[1]-a[1])]
        distance = math.hypot(gx-(ax+t*dx), gy-(ay+t*dy))
        if best is None or distance < best[0]:
            best = (distance, i, point)
    distance, i, point = best
    if distance > 1:
        raise ValueError('Observed gate is more than one metre from Tripoli centerline')
    return coords[:i+1]+[point], distance


def build_segments(roads, records, locations):
    features = {f['properties']['OBJECTID']: f for f in roads['features']}
    points = {f['properties']['node_id']: f['geometry']['coordinates'] for f in locations['features']}
    result = []
    for record in records['edges']:
        start = points[record['from_node']]
        end = points[record['to_node']]
        if start != record['geometry_reference']['start_coordinate'] or end != record['geometry_reference']['end_coordinate']:
            raise ValueError('Graph endpoints disagree with geometry reference')
        coords = [start]
        for feature_id in record['official_feature_ids']:
            line = features[feature_id]['geometry']['coordinates']
            if line[0] == coords[-1]:
                oriented = line
            elif line[-1] == coords[-1]:
                oriented = list(reversed(line))
            else:
                raise ValueError(f'Disconnected GIS feature: {feature_id}')
            oneway = features[feature_id]['properties'].get('ONEWAY')
            if (oneway == 'FT' and oriented != line) or (oneway == 'TF' and oriented == line):
                raise ValueError(f'GIS one-way direction conflict: {feature_id}')
            coords += oriented[1:]
        gap = 0
        if record['edge_id'] == 'edge_shared_tripoli_gate':
            coords, gap = clip_at_gate(coords, end)
        elif coords[-1] != end:
            raise ValueError(f'Incorrect end of segment: {record["edge_id"]}')
        result.append({'type':'Feature', 'geometry':{'type':'LineString','coordinates':coords},
                       'properties':{**record, 'gate_centerline_offset_metres':gap}})
    return result


def main():
    paths = ['data/processed/physical_nodes.geojson', 'data/processed/physical_edges.json',
             'data/raw/gis/official/njogis_apm_study_area_roads_2026_07_26.geojson']
    locations, records, roads = [json.loads((REPO/p).read_text()) for p in paths]
    segments = build_segments(roads, records, locations)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'physical-network.geojson').write_text(json.dumps({'type':'FeatureCollection',
        'features':locations['features']+segments}, indent=2)+'\n')
    audit = {'location_nodes':len(locations['features']), 'road_segments':len(segments),
             'geometry_basis':'Archived NJOGIS centerlines, July 26 2026; gate observation July 31 2026',
             'projection':'Local equirectangular, standard parallel 40.672 degrees north',
             'graph_records_changed':False,
             'source_sha256':{p:hashlib.sha256((REPO/p).read_bytes()).hexdigest() for p in paths},
             'gate_centerline_offset_metres':segments[-1]['properties']['gate_centerline_offset_metres']}
    (OUT/'geometry-audit.json').write_text(json.dumps(audit, indent=2)+'\n')
    # Equal metres per pixel in both axes. North stays up; no node is displaced.
    west, south, east, north = -74.2005, 40.6615, -74.1545, 40.682
    xmin,ymin=xy([west,south]);xmax,ymax=xy([east,north])
    left,top,width,height=48,170,1250,950
    scale=min(width/(xmax-xmin),height/(ymax-ymin))
    def project(p):
        x,y=xy(p)
        return left+(width-(xmax-xmin)*scale)/2+(x-xmin)*scale, top+(height-(ymax-ymin)*scale)/2+(ymax-y)*scale
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1800" height="1300" viewBox="0 0 1800 1300">',
         '<rect width="1800" height="1300" fill="#fafbf9"/>',
         '<style>text{font-family:Arial,sans-serif;fill:#20333e}.halo{paint-order:stroke;stroke:#fafbf9;stroke-width:7;stroke-linejoin:round}</style>',
         f'<defs><clipPath id="map"><rect x="{left}" y="{top}" width="{width}" height="{height}"/></clipPath></defs>']
    def text(x,y,value,size=20,fill=None,extra=''):
        svg.append(f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" {extra}'+(f' style="fill:{fill}"' if fill else '')+'>'+html.escape(str(value))+'</text>')
    def line(coords,color,stroke=2,dash=''):
        pts=' '.join(f'{x:.2f},{y:.2f}' for x,y in map(project,coords))
        svg.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round"'+(f' stroke-dasharray="{dash}"' if dash else '')+'/>')
    text(48,67,'The roads behind the knowledge graph',40,extra='font-weight="700"')
    text(48,108,'APM Elizabeth approaches · actual road geometry and recorded location coordinates',23)
    text(48,142,'Geographic companion to the full graph — 10 physical locations and 9 directed road segments',19,'#62747c')
    svg.append(f'<rect x="{left}" y="{top}" width="{width}" height="{height}" rx="12" fill="#f0f3ef"/>')
    svg.append('<g clip-path="url(#map)">')
    for f in roads['features']:
        if f['geometry']['type']=='LineString':line(f['geometry']['coordinates'],'#cdd4ce',1.6)
    colors={}
    for f in segments:
        eid=f['properties']['edge_id']
        candidate=eid in {'edge_a_nb_turnpike_exit','edge_a_nb_state_ramps_to_north_ave'}
        shared=eid.startswith('edge_shared_')
        color='#b87819' if candidate else '#235ac0' if shared else '#168879'
        colors[eid]=color
        line(f['geometry']['coordinates'],'#ffffff',10)
        line(f['geometry']['coordinates'],color,5.5,'9 7' if candidate else '')
        # Arrow at 60% of the actual directed polyline length.
        pts=list(map(project,f['geometry']['coordinates']))
        lengths=[math.dist(a,b) for a,b in zip(pts,pts[1:])]
        remain=sum(lengths)*.60
        for (a,b),length in zip(zip(pts,pts[1:]),lengths):
            if remain<=length and length:
                t=remain/length;x=a[0]+t*(b[0]-a[0]);y=a[1]+t*(b[1]-a[1])
                angle=math.degrees(math.atan2(b[1]-a[1],b[0]-a[0]))
                svg.append(f'<path d="M -8,-6 L 5,0 L -8,6" fill="none" stroke="{color}" stroke-width="3" transform="translate({x},{y}) rotate({angle})"/>')
                break
            remain-=length
    # Road labels are annotations; only their text offsets are chosen for legibility.
    labels=[([-74.196,40.6797],'US 1 & 9',0),([-74.1898,40.6739],'North Avenue East',22),
            ([-74.1755,40.6675],'North Avenue East',23),([-74.1640,40.6704],'McLester Street',-59),
            ([-74.1585,40.6742],'Tripoli Street',24),([-74.184,40.665],'NJ Turnpike',-62)]
    for p,label,angle in labels:
        x,y=project(p);text(x,y,label,19,extra=f'class="halo" transform="rotate({angle},{x},{y})"')
    offsets={1:(-26,-28),2:(-24,28),3:(28,23),4:(-25,-26),5:(24,-25),6:(-22,27),7:(24,26),8:(12,30),9:(-23,-25),10:(35,12)}
    for i,f in enumerate(locations['features'],1):
        x,y=project(f['geometry']['coordinates']);dx,dy=offsets[i]
        svg.append(f'<circle cx="{x}" cy="{y}" r="6" fill="#20333e" stroke="white" stroke-width="2"/>')
        svg.append(f'<path d="M{x},{y} L{x+dx},{y+dy}" stroke="#697b82" fill="none"/>')
        svg.append(f'<circle cx="{x+dx}" cy="{y+dy}" r="15" fill="white" stroke="#20333e" stroke-width="1.5"/>')
        text(x+dx,y+dy+6,i,16,extra='text-anchor="middle" font-weight="700"')
    svg.append('</g>')
    text(1250,220,'N',22,extra='text-anchor="middle" font-weight="700"')
    svg.append('<path d="M1250 236 L1250 286 M1242 249 L1250 236 L1258 249" fill="none" stroke="#20333e" stroke-width="3"/>')
    bar=500*scale
    svg.append(f'<path d="M85 1070 v10 h{bar} v-10" fill="none" stroke="#20333e" stroke-width="3"/>')
    text(85,1108,'0',17);text(85+bar,1108,'500 m',17,extra='text-anchor="end"')
    text(1340,207,'Recorded locations',25,extra='font-weight="700"')
    names=['Turnpike southbound exit','Turnpike northbound exit','Authority / state ramp transition',
           'Northbound approach joins North Ave','US 1 & 9 approach start','US 1 & 9 / North Avenue entry',
           'Shared North Avenue merge','North Avenue / McLester','McLester / Tripoli','Observed APM gate location']
    for i,name in enumerate(names,1):
        y=244+(i-1)*47
        text(1340,y,f'{i:02}',18,'#62747c');text(1376,y,name,17)
    text(1340,759,'Road connections',24,extra='font-weight="700"')
    legends=[('#168879','Operator-published approaches'),('#235ac0','Shared approach to APM'),('#b87819','Candidate northbound ramps')]
    for i,(color,label) in enumerate(legends):
        y=800+i*43
        svg.append(f'<path d="M1340 {y-6} h35" stroke="{color}" stroke-width="5"'+(' stroke-dasharray="8 5"' if i==2 else '')+'/>')
        text(1388,y,label,18)
    for i,s in enumerate(['Dots stay at recorded coordinates.', 'Number badges are offset for clarity.',
                           'Road bends come from GIS features.', 'Crossing lines do not create junctions.',
                           'Rules and documents stay in the full graph.']):
        text(1340,950+i*31,s,17,'#62747c')
    text(48,1170,'Sources: NJOGIS Road Centerlines / ArcGIS snapshot, July 26, 2026; archived APM directions;',19)
    text(48,1200,'Google Maps gate observation, July 31, 2026. Background roads are context only.',19)
    text(48,1243,'Geography shows physical connections. It does not verify truck legality, current closures, or gate access.',20,'#775015')
    svg.append('</svg>')
    (OUT/'geographic-roads.svg').write_text('\n'.join(svg))
    print(json.dumps(audit,indent=2))


if __name__ == '__main__':
    main()
