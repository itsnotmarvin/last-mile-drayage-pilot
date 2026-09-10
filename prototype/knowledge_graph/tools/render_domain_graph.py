"""Render the drayage situation using actual roads and compact authority nodes."""
import html
import json
import math
import sys
import textwrap
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from domain_graph import domain_view
from tools.author_geographic_preview import REPO, build_segments, xy
from tools.author_integrated_geographic_draft import split_line

OUT=ROOT/'output/domain-graph'

# Captions summarize topics and retain legal distinctions; full text is attached.
CAPTIONS={
 'reg_nj_height_limit': ('Height limits', 'NJ size & weight guide §2.1.2'),
 'reg_nj_width_limit': ('Width depends on road-network status', '§2.1.1 · 96 / 102-inch distinction'),
 'reg_nj_semitrailer_length': ('Trailer length and terminal-access conditions', '§2.1.3.6 · route conditions matter'),
 'reg_nj_tandem_gross_bridge': ('Axle-group, gross weight and bridge formula', '§2.2.2 · gross weight alone is insufficient'),
 'reg_nj_noninterstate_single_axle': ('Single-axle limits on non-Interstate roads', '§2.2.1'),
 'reg_nj_terminal_access_102_inch_standard_truck': ('Reasonable terminal access', 'Scope limited to 102-inch standard trucks'),
 'reg_nj_access_network_600_series': ('CR 624 absent from access-network list', 'Absence is not a permission finding'),
 'reg_nj_truck_access_local_rule_preservation': ('Local restrictions remain relevant', 'NJ truck access code · 16:32'),
 'reg_nj_single_trip_osow_permit': ('Single-trip oversize / overweight permit', 'Applicability needs vehicle and load facts'),
 'reg_nj_ocean_container_permit': ('Annual ocean-container permit', 'Applicability needs vehicle and load facts'),
 'reg_federal_interstate_weight': ('Interstate axle, gross and bridge-formula limits', '23 CFR 658.17 · recorded Interstate scope'),
 'reg_njta_roadway_use_limitations': ('Turnpike roadway and vehicle limitations', 'N.J.A.C. 19:9-1.9'),
 'reg_federal_cdl': ('Commercial driver license requirement', '49 CFR 383.23'),
 'reg_federal_group_a_cmv': ('Group A combination-vehicle definition', 'Defines the scope of the CDL requirement'),
 'reg_apm_appointment': ('Gate appointment through TERMPoint', 'APM truckers guide · printed page 18'),
 'reg_apm_safety_induction': ('Mandatory safety induction video / quiz', 'APM truckers guide · printed page 18'),
 'reg_panynj_dtr': ('Drayage Truck Registry registration', 'PA-10 §34-1100'),
 'reg_panynj_dtr_engine': ('Engine provisions for DTR registration', 'PA-10 §34-1101 · registration scope'),
 'reg_panynj_rfid': ('RFID and its DTR registration connection', 'Port truck information · RFID section'),
 'reg_panynj_sealink_twic': ('SeaLink and TWIC access requirements', 'Port truck information · SeaLink / TWIC'),
 'reg_panynj_terminal_traffic': ('Traffic rules on port terminal highways', 'PA-10 §34-290'),
 'reg_panynj_terminal_weight_dimensions': ('Terminal oversize / overweight provisions', 'PA-10 §34-046'),
 'reg_panynj_drayage_truck_deadline_34_1140': ('Drayage deadline text — unresolved', '§34-1140 / §34-1101 interpretation tension'),
 'reg_federal_twic': ('TWIC for unescorted secure-area access', '33 CFR 101.514'),
 'reg_elizabeth_north_avenue_east_zone': ('80,000 lb zone overlaps part of North Avenue', 'Geographic overlap only · §10.16.050'),
 'reg_elizabeth_four_ton_limit_streets': ('Mapped streets absent from four-ton table', '§10.16.010 · absence does not grant permission'),
 'reg_elizabeth_five_ton_limit_streets': ('Mapped streets absent from five-ton table', '§10.16.040 · absence does not grant permission'),
 'reg_union_county_truck_routes_reserved': ('County truck-route schedule is reserved', 'No designation established by that schedule'),
 'reg_nj_osow_permit_requirement_13_18_portal_copy': ('Oversize / overweight permit requirement', '13:18-1.2 · current force not fully verified'),
 'reg_nj_single_trip_route_review_13_18_portal_copy': ('Single-trip route review', '13:18-1.5 · current force not fully verified'),
 'reg_nj_toll_authority_approval_13_18_portal_copy': ('Separate toll-authority approval', '13:18-1.9 · current force not fully verified'),
}


def render():
    archive=json.loads((ROOT/'output/evidence-graph/graph.json').read_text())
    data=domain_view(archive);nodes={n['id']:n for n in data['nodes']}
    aliases=json.loads((ROOT/'presentation/labels.json').read_text())
    locations=json.loads((REPO/'data/processed/physical_nodes.geojson').read_text())
    records=json.loads((REPO/'data/processed/physical_edges.json').read_text())
    roads=json.loads((REPO/'data/raw/gis/official/njogis_apm_study_area_roads_2026_07_26.geojson').read_text())
    segments=build_segments(roads,records,locations)
    W,H=3300,2400
    mx,my,mw,mh=690,260,1710,1160
    xmin,ymin=xy([-74.201,40.660]);xmax,ymax=xy([-74.1525,40.683])
    scale=min(mw/(xmax-xmin),mh/(ymax-ymin))
    def project(p):
        x,y=xy(p)
        return [mx+(mw-(xmax-xmin)*scale)/2+(x-xmin)*scale,my+(mh-(ymax-ymin)*scale)/2+(ymax-y)*scale]
    pos={f['properties']['node_id']:project(f['geometry']['coordinates']) for f in locations['features']}
    geometry={}
    for f in segments:
        nid=f['properties']['edge_id'];line=list(map(project,f['geometry']['coordinates']))
        pos[nid]=split_line(line)[0];geometry[nid]=line
    # Authority cards are actual graph nodes; their rule lists are attributes.
    cards={
      'authority_njdot':(45,260,570,900,'NJDOT','State road rules and permit provisions'),
      'authority_fhwa':(45,1240,570,240,'FHWA','Federal Interstate weight rules'),
      'authority_njta':(45,1540,570,210,'NJ Turnpike Authority','Turnpike roadway rules'),
      'authority_fmcsa':(45,1840,570,350,'FMCSA','Driver qualification · general scope'),
      'operator_apm_terminals':(2510,330,740,280,'APM Terminals','Operator requirements'),
      'authority_panynj':(2510,750,740,645,'Port Authority','Port access and terminal requirements'),
      'authority_uscg':(2510,1540,740,225,'US Coast Guard','Secure-area access'),
      'authority_elizabeth_city':(720,1580,790,400,'City of Elizabeth','Local road rules'),
      'authority_union_county':(1620,1580,780,230,'Union County','County route designation'),
      'authority_njmvc':(1620,1920,780,355,'NJ Motor Vehicle Commission','Permit provisions'),
    }
    for nid,(x,y,w,h,_,_) in cards.items():
        pos[nid]=[x+w-27,y+36] if x<650 else [x+27,y+36]
    pos['facility_apm_elizabeth']=[2390,650]
    pos['credential_cdl']=[310,2140]
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
         '<style>text{font-family:Arial,sans-serif;fill:#233642}.halo{paint-order:stroke;stroke:#f7faf8;stroke-width:6;stroke-linejoin:round}</style>',
         '<rect width="100%" height="100%" fill="#fff"/>',
         '<defs><marker id="scope-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M0 0 L10 5 L0 10z" fill="#7992a1"/></marker>',
         f'<clipPath id="map"><rect x="{mx}" y="{my}" width="{mw}" height="{mh}"/></clipPath></defs>']
    esc=lambda t:html.escape(str(t),quote=True)
    def text(x,y,t,size=22,color=None,extra=''):
        out.append(f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" {extra}'+(f' style="fill:{color}"' if color else '')+'>'+esc(t)+'</text>')
    def path(points,attrs=''):
        d='M'+' L'.join(f'{x:.2f},{y:.2f}' for x,y in points)
        out.append(f'<path d="{d}" fill="none" {attrs}/>')
    text(55,75,'Last-mile drayage · roads, requirements and responsibilities',43,extra='font-weight="700"')
    text(55,120,'APM Elizabeth inbound approaches — a knowledge graph grounded in the actual road network',25,'#5c7180')
    text(55,169,'Roads and junctions',21,'#496eb3');text(355,169,'Authorities and terminal',21,'#248c7b')
    text(730,169,'Rules appear within their authority nodes; citations stay attached to the records.',21,'#5c7180')
    text(mx,my-35,'PHYSICAL NETWORK',23,'#58716c',extra='font-weight="700"')
    out.append(f'<rect x="{mx}" y="{my}" width="{mw}" height="{mh}" rx="24" fill="#f7faf8"/>')
    out.append('<g clip-path="url(#map)">')
    for f in roads['features']:
        if f['geometry']['type']=='LineString':path(list(map(project,f['geometry']['coordinates'])),'stroke="#e0e8e2" stroke-width="1.7"')
    out.append('</g>')
    # Every visible authority-to-road connection expands to exact archived clauses.
    for e in data['edges']:
        if e['relationship'] in {'STARTS_AT','ENDS_AT'}:continue
        a,b=pos[e['source']],pos[e['target']]
        records=e.get('record',{}).get('scope_records',[])
        uncertain=records and all(r['scope_relation'] in {'STREET_NOT_LISTED_IN_RESTRICTION_TABLE','ROUTE_NUMBER_NOT_LISTED_IN_APPENDIX_C','TRUCK_ROUTE_SCHEDULE_RESERVED'} for r in records)
        color='#b38d55' if uncertain else '#7994a4'
        dx=b[0]-a[0];dy=b[1]-a[1]
        # Curves distribute nearby connections while preserving exact endpoints.
        cx=a[0]+dx*.45;cy=a[1]+dy*.55
        out.append(f'<path data-edge-id="{esc(e["id"])}" d="M{a[0]},{a[1]} Q{cx},{cy} {b[0]},{b[1]}" stroke="{color}" stroke-width="1.9" opacity=".46" fill="none" marker-end="url(#scope-arrow)"'+(' stroke-dasharray="7 7"' if uncertain else '')+f'><title>{esc(e["relationship"])}: {esc([r.get("rule_id") for r in records])}</title></path>')
    for f in segments:
        nid=f['properties']['edge_id'];candidate=nid in {'edge_a_nb_turnpike_exit','edge_a_nb_state_ramps_to_north_ave'}
        color='#bd8b3e' if candidate else '#608acf'
        # A segment is one real object with two endpoint relations, not a route-summary node.
        _,start,end=split_line(geometry[nid])
        path(list(reversed(start)),f'data-edge-id="starts:{nid}" stroke="{color}" stroke-width="6" stroke-linecap="round"'+(' stroke-dasharray="10 8"' if candidate else ''))
        path(end,f'data-edge-id="ends:{nid}" stroke="{color}" stroke-width="6" stroke-linecap="round"'+(' stroke-dasharray="10 8"' if candidate else ''))
        # Direction chevron follows the actual directed segment.
        mid,_,tail=split_line(geometry[nid]);b=tail[1];ang=math.degrees(math.atan2(b[1]-mid[1],b[0]-mid[0]))
        out.append(f'<path d="M-10,-7 L1,0 L-10,7" fill="none" stroke="{color}" stroke-width="3" transform="translate({mid[0]+18*math.cos(math.radians(ang))},{mid[1]+18*math.sin(math.radians(ang))}) rotate({ang})"/>')
    # Keep geographic anchors fixed and move only the names around them.
    geo_ids={f['properties']['node_id'] for f in locations['features']}|set(geometry)
    labels={};boxes=[]
    obstacles=[(pos[n][0]-16,pos[n][1]-16,pos[n][0]+16,pos[n][1]+16) for n in geo_ids]
    def overlaps(a,b):return min(a[2],b[2])>max(a[0],b[0]) and min(a[3],b[3])>max(a[1],b[1])
    short={
      'node_path_b_us1_south_access':'US 1 / 9 approach start','edge_b_us1_south':'US 1 / 9 segment',
      'node_path_b_north_avenue_entry':'US 1 / 9 → North Avenue','edge_b_north_avenue_to_merge':'North Avenue East',
      'edge_shared_north_avenue':'North Avenue · shared section', 'edge_shared_mclester':'McLester Street',
      'edge_shared_tripoli_gate':'Tripoli Street','node_paths_merge_north_avenue':'Approaches join',
      'edge_ab_shared_north_ave_to_all_merge':'North Avenue · between merges',
    }
    for nid in sorted(geo_ids,key=lambda n:pos[n][0]):
        x,y=pos[nid];lines=textwrap.wrap(short.get(nid,aliases[nid]),25)
        w=max(len(t) for t in lines)*11+20;h=len(lines)*23+12
        found=None
        for radius in [45,75,110,150,200,260,330,410]:
            for degrees in [-90,90,0,180,-45,45,135,-135]:
                r=math.radians(degrees);lx=x+radius*math.cos(r);ly=y+radius*math.sin(r)
                box=(lx-w/2,ly-20,lx+w/2,ly-20+h)
                if box[0]<mx+15 or box[2]>mx+mw-15 or box[1]<my+70 or box[3]>my+mh-100:continue
                if not any(overlaps(box,b) for b in boxes+obstacles):found=(lx,ly,box);break
            if found:break
        if not found:raise ValueError(f'Cannot place road label {nid}')
        lx,ly,box=found;boxes.append(box);labels[nid]=[lx,ly]
        out.append(f'<g data-node-id="{nid}">')
        path([[x,y],[lx,ly-9]],'stroke="#84969b" stroke-width="1.2"')
        fill='#2d9d87' if nid=='node_apm_inbound_gate' else '#83a1dc'
        out.append(f'<circle cx="{x}" cy="{y}" r="10" fill="{fill}" stroke="white" stroke-width="2"/>')
        for i,t in enumerate(lines):text(lx,ly+i*23,t,21,extra='class="halo" text-anchor="middle"')
        out.append('</g>')
    # An actual terminal object remains distinct from its gate.
    x,y=pos['facility_apm_elizabeth'];out.append('<g data-node-id="facility_apm_elizabeth">')
    out.append(f'<circle cx="{x}" cy="{y}" r="12" fill="#42b49c" stroke="#238b77" stroke-width="2"/>')
    text(x,y+36,'APM Elizabeth',25,extra='font-weight="700" text-anchor="middle"')
    text(x,y+64,'terminal',21,extra='text-anchor="middle"');out.append('</g>')
    # No source or rule dots: those records are written inside their authority node.
    rule_ids=set()
    for nid,(x,y,w,h,title,subtitle) in cards.items():
        out.append(f'<g data-node-id="{nid}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="20" fill="#fff" stroke="#cddfd9" stroke-width="2"/>')
        px,py=pos[nid];out.append(f'<circle cx="{px}" cy="{py}" r="10" fill="#43b59e" stroke="#288b78" stroke-width="2"/>')
        tx=x+25 if x<650 else x+52
        text(tx,y+44,title,28,extra='font-weight="700"');text(x+25,y+79,subtitle,19,'#637981')
        yy=y+123
        ordered=sorted(nodes[nid]['requirements'],key=lambda n:list(CAPTIONS).index(n['id']))
        for rule in ordered:
            rid=rule['id'];rule_ids.add(rid);caption,note=CAPTIONS[rid]
            limit=47 if w<650 else 61
            lines=textwrap.wrap(caption,limit)
            color='#9c6b2c' if 'unresolved' in caption else '#263d49'
            for line in lines:text(x+25,yy,line,21,color);yy+=25
            for line in textwrap.wrap(note,limit+5):text(x+25,yy,line,17,'#6e8087');yy+=21
            yy+=17
        if yy>y+h-8:raise ValueError(f'Authority text overflows {nid}: {yy} > {y+h}')
        out.append('</g>')
    x,y=pos['credential_cdl'];out.append('<g data-node-id="credential_cdl">')
    path([pos['authority_fmcsa'],[x,y]],'stroke="#bd94b4" stroke-width="1.5"')
    out.append(f'<circle cx="{x}" cy="{y}" r="10" fill="#d797c8"/>');text(x+22,y+7,'CDL qualification',21);out.append('</g>')
    text(mx+25,my+40,'Real GIS centerlines · recorded location coordinates',21,'#637c70')
    text(mx+mw-85,my+44,'N ↑',27,'#3e6257',extra='font-weight="700"')
    bar=500*scale;path([[mx+28,my+mh-65],[mx+28,my+mh-55],[mx+28+bar,my+mh-55],[mx+28+bar,my+mh-65]],'stroke="#5a716b" stroke-width="2.5"')
    text(mx+28,my+mh-25,'500 m',18,'#61766e')
    text(mx+300,my+mh-57,'Amber dashed ramps: candidate northbound approach; truck use not verified.',19,'#94703d')
    text(mx+300,my+mh-25,'Thin arrows: recorded rule scope. Dashed links: listing gaps / reserved schedules.',19,'#617580')
    text(720,1480,'Exact road shapes; no separate Route A / Route B nodes.',22,'#4e6873')
    text(720,1517,'Sources and detailed clauses remain attached as evidence.',22,'#4e6873')
    text(720,2070,'Scope matters',27,extra='font-weight="700"')
    for i,t in enumerate(['A rule connection records what the archive says.', 'It does not establish that a specific truck can enter.',
                           'Missing listings are not permissions.', 'Driver and permit facts still need checking.']):
        text(720,2110+i*34,t,22,'#657882')
    text(55,2320,'Geometry: NJOGIS snapshot, July 26, 2026; gate observation, July 31, 2026. Rule quotations and source locators are preserved.',20,'#6b7f88')
    text(55,2360,f'{data["summary"]["node_count"]} domain nodes · {data["summary"]["retained_rule_records"]} rule records attached · archived evidence, not current trip clearance',20,'#6b7f88')
    out.append('</svg>')
    if rule_ids!={n['id'] for n in archive['nodes'] if n['kind']=='source_clause'}:raise ValueError('Not every rule is represented')
    data['presentation']={'positions':pos,'geographic_labels':labels,'rule_caption_ids':sorted(rule_ids)}
    return '\n'.join(out),data


if __name__=='__main__':
    svg,data=render();OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'knowledge-graph.svg').write_text(svg)
    (OUT/'graph.json').write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps(data['summary']))
