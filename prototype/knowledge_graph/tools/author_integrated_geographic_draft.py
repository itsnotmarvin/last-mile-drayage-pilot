"""A review-only full-graph PNG source with geographic physical-node anchors."""
import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from graph_presentation import full_graph_svg, label_lines, label_width, PALETTE
from tools.author_geographic_preview import REPO, build_segments, xy

NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NS)

# Redundant abstractions hide in the picture but stay in the graph data.
# Route/approach dots repeat what the connected road geometry already shows;
# source dots become citations attached to the records that cite them.
HIDDEN = {
    'path_b_us1_9_to_apm', 'path_a_exit13a_to_apm',
    'approach_a_turnpike_sb', 'approach_a_turnpike_nb',
    'apm_directions', 'google_maps_route_observation_2026_07_31',
    'njogis_road_centerlines_2026_07_26',
}


def element(parent, tag, attrs=None, text=None):
    e = ET.SubElement(parent, '{'+NS+'}'+tag, {k:str(v) for k,v in (attrs or {}).items()})
    e.text = text
    return e


def split_line(points):
    lengths = [math.dist(a,b) for a,b in zip(points,points[1:])]
    remaining = sum(lengths)/2
    for i,length in enumerate(lengths):
        if remaining <= length and length:
            a,b=points[i:i+2];t=remaining/length
            midpoint=[a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1])]
            return midpoint, points[:i+1]+[midpoint], [midpoint]+points[i+1:]
        remaining-=length
    raise ValueError('Empty road geometry')


def path(points):
    return 'M'+' L'.join(f'{x:.3f},{y:.3f}' for x,y in points)


def render():
    data=json.loads((ROOT/'output/evidence-graph/graph.json').read_text())
    saved=json.loads((ROOT/'presentation/organized-layout.json').read_text())
    aliases=json.loads((ROOT/'presentation/labels.json').read_text())
    nodes={n['id']:n for n in data['nodes']}
    locations=json.loads((REPO/'data/processed/physical_nodes.geojson').read_text())
    records=json.loads((REPO/'data/processed/physical_edges.json').read_text())
    roads=json.loads((REPO/'data/raw/gis/official/njogis_apm_study_area_roads_2026_07_26.geojson').read_text())
    segments=build_segments(roads,records,locations)
    positions={k:list(v) for k,v in saved['positions'].items()}
    # A single metre-based projection for every physical anchor.
    west,south,east,north=-74.2005,40.6610,-74.1535,40.6825
    xmin,ymin=xy([west,south]);xmax,ymax=xy([east,north])
    mx,my,mw,mh=1324,175,1406,1020
    scale=min(mw/(xmax-xmin),mh/(ymax-ymin))
    def project(p):
        x,y=xy(p)
        return [mx+(mw-(xmax-xmin)*scale)/2+(x-xmin)*scale,
                my+(mh-(ymax-ymin)*scale)/2+(ymax-y)*scale]
    geo_ids=set()
    for feature in locations['features']:
        nid=feature['properties']['node_id'];geo_ids.add(nid)
        positions[nid]=project(feature['geometry']['coordinates'])
    polylines={};halves={}
    for feature in segments:
        nid=feature['properties']['edge_id'];geo_ids.add(nid)
        coords=list(map(project,feature['geometry']['coordinates']))
        midpoint,first,last=split_line(coords)
        positions[nid]=midpoint;polylines[nid]=coords;halves[nid]=(first,last)
    # The nonspatial route and source records remain part of this same graph.
    route_ids=['path_b_us1_9_to_apm','path_a_exit13a_to_apm','approach_a_turnpike_sb','approach_a_turnpike_nb']
    source_ids=['apm_directions','google_maps_route_observation_2026_07_31','njogis_road_centerlines_2026_07_26']
    for i,nid in enumerate(route_ids):positions[nid]=[1430+i*380,1270]
    for i,nid in enumerate(source_ids):positions[nid]=[1510+i*505,1400]
    # Section 3 follows the trucker's real-life order in three stage lanes.
    # This staging is an arranged reading order, not an APM-published sequence.
    # The gate itself stays geographic on the map; everything else lanes up here.
    STAGES = [
        ('1 · Before anything', [
            'credential_twic', 'credential_sealink', 'credential_rfid', 'registration_dtr',
            'training_apm_safety_induction', 'reg_apm_safety_induction', 'reg_federal_twic',
            'reg_panynj_dtr', 'reg_panynj_dtr_engine', 'reg_panynj_sealink_twic', 'reg_panynj_rfid',
            'ecfr_twic_1572', 'ecfr_33_cfr_101_514_2026_07_29', 'authority_uscg',
        ]),
        ('2 · Before arrival', [
            'system_termpoint', 'apm_appointment_system', 'apm_hours_ops',
            'reg_apm_appointment', 'operator_apm_terminals', 'porttruckpass_tips',
        ]),
        ('3 · At the gate', [
            'facility_apm_elizabeth', 'authority_panynj', 'jurisdiction_panynj_terminal',
            'reg_panynj_terminal_traffic', 'reg_panynj_terminal_weight_dimensions',
            'reg_panynj_drayage_truck_deadline_34_1140', 'panynj_truck_info',
            'panynj_truckers_guide', 'panynj_marine_terminal_tariff',
        ]),
    ]
    STAGE_X = [3140, 3435, 3730]
    STAGE_TOP, STAGE_BOTTOM, STAGE_HEADER_Y = 330, 1500, 290
    stage_of = {}
    for lane, (header, members) in enumerate(STAGES):
        for nid in members:
            stage_of[nid] = lane
    for lane, (header, members) in enumerate(STAGES):
        pitch = (STAGE_BOTTOM-STAGE_TOP)/max(1, len(members)-1)
        for i, nid in enumerate(members):
            positions[nid] = [STAGE_X[lane], STAGE_TOP+i*pitch]
    # Section 1: the truck left, the driver right. Section 4: the permit
    # path, then the fenced-off dated notices. Same arranged-order idea.
    SEC1 = [
        ('The truck', [
            'scoped_80000lb_5axle_nonhaz_inbound_apm', 'representative_older_engine_drayage',
            'representative_osow_ocean_container', 'reg_federal_interstate_weight',
            'ecfr_23_cfr_658_17_2026_07_29', 'authority_fhwa',
        ]),
        ('The driver', [
            'reg_federal_cdl', 'reg_federal_group_a_cmv', 'credential_cdl',
            'ecfr_49_cfr_383_2026_07_29', 'authority_fmcsa',
        ]),
    ]
    SEC4 = [
        ('Permit path', [
            'reg_nj_osow_permit_requirement_13_18_portal_copy', 'reg_nj_single_trip_osow_permit',
            'reg_nj_ocean_container_permit', 'reg_nj_single_trip_route_review_13_18_portal_copy',
            'reg_nj_toll_authority_approval_13_18_portal_copy', 'njac_13_18_osow_portal_copy_2026_08_24',
            'authority_njmvc',
        ]),
        ('Dated notices: recheck', [
            'njpass_home_2026_08_24', 'njpass_connecting_local_routes_application_comments',
            'njpass_nonstate_permit_authorities', 'njpass_port_st_oversize_restrictions_2026_08_03',
            'njpass_route_survey_threshold', 'njpass_state_routes_only_system_scope',
        ]),
    ]
    for lanes, xs, top, bottom in ((SEC1, [420, 800], 340, 800), (SEC4, [430, 820], 1880, 2320)):
        for lane, (header, members) in enumerate(lanes):
            pitch = (bottom-top)/max(1, len(members)-1)
            for i, nid in enumerate(members):
                positions[nid] = [xs[lane], top+i*pitch]
    # Section 5: one lane per road owner, plus the map-zone references.
    SEC5 = [
        ('State rules', [
            'authority_njdot', 'reg_nj_height_limit', 'reg_nj_width_limit',
            'reg_nj_semitrailer_length', 'reg_nj_noninterstate_single_axle',
            'reg_nj_tandem_gross_bridge', 'reg_nj_access_network_600_series',
            'reg_nj_terminal_access_102_inch_standard_truck',
            'reg_nj_truck_access_local_rule_preservation',
        ]),
        ('State sources', [
            'nj_size_weight_guidebook', 'nj_large_truck_map',
            'njac_16_32_truck_access_current_2023', 'njac_16_32_readoption_njr_2023_01_03',
            'njdot_truck_routing_regulations_2026_08_24',
        ]),
        ('Turnpike & county', [
            'authority_njta', 'reg_njta_roadway_use_limitations',
            'njac_19_9_1_9_cornell_2026_08_07', 'njta_rules_readoption_2024',
            'authority_union_county', 'reg_union_county_truck_routes_reserved',
            'union_county_laws_2026',
        ]),
        ('City streets', [
            'authority_elizabeth_city', 'reg_elizabeth_five_ton_limit_streets',
            'reg_elizabeth_four_ton_limit_streets', 'reg_elizabeth_north_avenue_east_zone',
            'elizabeth_code_10_16_050_2025_11_11',
        ]),
        ('Map zones', [
            'jurisdiction_new_jersey', 'jurisdiction_union_county', 'jurisdiction_elizabeth',
            'road_authority_category_state', 'road_authority_category_county',
            'road_authority_category_municipal', 'road_authority_category_highway_authority',
            'njogis_county_boundaries_2026_07_26', 'njogis_municipal_boundaries_2026_07_26',
        ]),
    ]
    SEC5_X = [1510, 1695, 1880, 2065, 2250]
    for lane, (header, members) in enumerate(SEC5):
        pitch = (2600-1880)/max(1, len(members)-1)
        for i, nid in enumerate(members):
            positions[nid] = [SEC5_X[lane], 1880+i*pitch]
    # Section 6: counts left, context right, the analysis hub between them,
    # and the verdict as plain strip text below (presentation, not new nodes).
    SEC6_COUNTS = [
        'njdot_traffic_counts_c74r_6c8d_route624_2018',
        'njdot_traffic_counts_c74r_6c8d_station_3_3_024_2020_2022',
        'njdot_traffic_count_2024_station_3_3_024',
    ]
    SEC6_CONTEXT = [
        'elizabeth_kapkowski_corridor_concept_report_2022',
        'union_county_truck_mobility_study_2021',
        'fhwa_nhs_shapefile_2025_08_08',
    ]
    for i, nid in enumerate(SEC6_COUNTS):
        positions[nid] = [3150, 1900+i*200]
    for i, nid in enumerate(SEC6_CONTEXT):
        positions[nid] = [3710, 1900+i*200]
    positions['historical_north_avenue_traffic_analysis'] = [3430, 2100]
    FINDINGS = [
        'North Ave funnels about twice the approach traffic into the merge (2018 counts),',
        'and its key intersections run with zero slack at rush hour —',
        'but nobody has measured the full merged flow since.',
    ]
    svg=ET.fromstring(full_graph_svg(data))
    # Hide redundant dots and their incident arrows from the picture.
    # The records and their evidence stay in graph.json unchanged.
    hidden_edges={e['id'] for e in data['edges'] if e['source'] in HIDDEN or e['target'] in HIDDEN}
    for parent in svg.iter():
        for child in list(parent):
            if child.get('data-node-id') in HIDDEN or child.get('data-edge-id') in hidden_edges:
                parent.remove(child)
    width=saved['width'];height=saved['height']+245
    svg.set('height',str(height));svg.set('viewBox',f'0 0 {width} {height}')
    svg.set('aria-label','Draft knowledge graph with 114 drawn nodes, 281 drawn relationships and actual road geometry; 121 nodes and 345 relationships in the archived graph')
    # Move the old contents down together to leave room for the draft title.
    contents=element(svg,'g',{'transform':'translate(0 165)'})
    for child in list(svg):
        if child is not contents:
            svg.remove(child);contents.append(child)
    svg.insert(0,ET.Element('{'+NS+'}rect',{'width':'100%','height':'100%','fill':'white'}))
    map_group=ET.Element('{'+NS+'}g',{'data-geographic-basemap':'true'})
    # Insert above the original white background and below relationship lines.
    contents.insert(3,map_group)
    element(map_group,'rect',{'x':mx,'y':my,'width':mw,'height':mh,'rx':24,'fill':'#f5f8f6'})
    defs=element(map_group,'defs');clip=element(defs,'clipPath',{'id':'geographic-clip'})
    element(clip,'rect',{'x':mx,'y':my,'width':mw,'height':mh})
    background=element(map_group,'g',{'clip-path':'url(#geographic-clip)'})
    for f in roads['features']:
        if f['geometry']['type']=='LineString':
            element(background,'path',{'d':path(list(map(project,f['geometry']['coordinates']))),
                                      'fill':'none','stroke':'#dce4de','stroke-width':1.4})
    road_layer=ET.Element('{'+NS+'}g',{'data-road-geometry':'true'})
    # Actual geographic lines are distinct from graph relationship arrows.
    for f in segments:
        nid=f['properties']['edge_id'];candidate=nid in {'edge_a_nb_turnpike_exit','edge_a_nb_state_ramps_to_north_ave'}
        attrs={'d':path(polylines[nid]),'fill':'none','stroke':'#bf8b3c' if candidate else '#6d91d6',
               'stroke-width':5,'stroke-linecap':'round','stroke-linejoin':'round','data-road-id':nid}
        if candidate:attrs['stroke-dasharray']='10 8'
        element(road_layer,'path',attrs)
    # Keep every relationship arrow above the geographic road underlay.
    contents.insert(list(contents).index(map_group)+1,road_layer)
    labels={};boxes=[]
    # Labels may move; geographic dots may not. Keep all dots clear of labels.
    obstacles=[(positions[n][0]-16,positions[n][1]-16,positions[n][0]+16,positions[n][1]+16) for n in geo_ids]
    def overlap(a,b):return min(a[2],b[2])>max(a[0],b[0]) and min(a[3],b[3])>max(a[1],b[1])
    for nid in sorted(geo_ids,key=lambda n:positions[n][0]):
        x,y=positions[nid];lines=label_lines(nodes[nid],aliases)
        w=max(label_width(t) for t in lines)+10;h=len(lines)*17+10
        found=None
        for radius in [45,70,100,135,175,220,280,340]:
            for angle in [-90,90,0,180,-45,45,135,-135]:
                a=math.radians(angle);lx=x+radius*math.cos(a);ly=y+radius*math.sin(a)
                box=(lx-w/2,ly-15,lx+w/2,ly-15+h)
                if box[0]<mx+8 or box[2]>mx+mw-8 or box[1]<my+55 or box[3]>my+mh-8:continue
                if not any(overlap(box,b) for b in boxes+obstacles):found=(lx,ly,box);break
            if found:break
        if not found:raise ValueError(f'Cannot place geographic label: {nid}')
        lx,ly,box=found;boxes.append(box);labels[nid]=[lx,ly]
    pair_groups={}
    for e in data['edges']:pair_groups.setdefault(tuple(sorted([e['source'],e['target']])),[]).append(e['id'])
    edges={e['id']:e for e in data['edges']}
    for el in contents.iter():
        if 'data-edge-id' in el.attrib:
            e=edges[el.get('data-edge-id')];a=positions[e['source']];b=positions[e['target']]
            if e['relationship'] in {'STARTS_AT','ENDS_AT'} and e['source'] in halves:
                first,last=halves[e['source']]
                points=list(reversed(first)) if e['relationship']=='STARTS_AT' else last
                el.set('d',path(points));el.set('style','stroke:#516f9c;opacity:.65;stroke-width:1.4')
            else:
                dx,dy=b[0]-a[0],b[1]-a[1];distance=math.hypot(dx,dy) or 1
                pair=tuple(sorted([e['source'],e['target']]));group=pair_groups[pair]
                offset=(group.index(e['id'])-(len(group)-1)/2)*20
                direction=1 if e['source']==pair[0] else -1
                cx=(a[0]+b[0])/2-dy/distance*offset*direction;cy=(a[1]+b[1])/2+dx/distance*offset*direction
                d1=math.dist(a,[cx,cy]) or 1;d2=math.dist(b,[cx,cy]) or 1
                x1=a[0]+(cx-a[0])/d1*14;y1=a[1]+(cy-a[1])/d1*14
                x2=b[0]-(b[0]-cx)/d2*17;y2=b[1]-(b[1]-cy)/d2*17
                el.set('d',f'M{x1},{y1} Q{cx},{cy} {x2},{y2}')
                if e['source'] in geo_ids or e['target'] in geo_ids:
                    gate='node_apm_inbound_gate' in (e['source'],e['target'])
                    el.set('style','stroke:#5f86ad;stroke-width:1.8;opacity:.48' if gate else 'stroke:#b1bbc3;stroke-width:1.1;opacity:.24')
        elif 'data-edge-label' in el.attrib:
            # Static preview: full semantic labels remain in titles and export.
            el.set('display','none')
    for group in contents:
        nid=group.get('data-node-id')
        if not nid:continue
        old=saved['positions'][nid];x,y=positions[nid]
        group.set('data-x',str(x));group.set('data-y',str(y))
        for child in group:
            if child.tag.endswith('circle'):
                child.set('cx',str(x));child.set('cy',str(y))
                if nid in geo_ids and child.get('class')=='node-circle':child.set('r','9')
            elif child.tag.endswith('text'):
                if nid in geo_ids:
                    lx,ly=labels[nid]
                    offset=float(child.get('y'))-old[1]-29
                    child.set('x',str(lx));child.set('y',str(ly+offset))
                    child.set('style','font-size:15px')
                else:
                    child.set('x',str(float(child.get('x'))+x-old[0]))
                    child.set('y',str(float(child.get('y'))+y-old[1]))
        if nid in geo_ids:
            lx,ly=labels[nid]
            lead=ET.Element('{'+NS+'}path',{'d':f'M{x},{y} L{lx},{ly-8}', 'fill':'none','stroke':'#94a1a6','stroke-width':'1', 'data-label-leader':nid})
            group.insert(1,lead)
    # Keep topics recognizable while moving the real gate into the physical map.
    for el in contents.iter():
        if el.get('data-topic-id')=='roads':
            texts=[e for e in el if e.tag.endswith('text')]
            texts[0].text='2 · Approaches & roads — geographic view'
            texts[1].text='Actual road geometry, with the graph connected directly to it'
    annotation=element(contents,'g')
    for lanes, xs, hy in ((STAGES, STAGE_X, STAGE_HEADER_Y), (SEC1, [420, 800], 300), (SEC4, [430, 820], 1840),
                          (SEC5, SEC5_X, 1840), ([('Counts', SEC6_COUNTS), ('Context', SEC6_CONTEXT)],
                          [3150, 3710], 1840)):
        for lane, (header, _members) in enumerate(lanes):
            element(annotation,'text',{'x':xs[lane],'y':hy,'text-anchor':'middle',
                                       'style':'font-size:19px;font-weight:bold;fill:#3e5a66'},header)
    for i, line in enumerate(FINDINGS):
        element(annotation,'text',{'x':3430,'y':2415+i*34,'text-anchor':'middle',
                                   'style':'font-size:17px;fill:#3e5a66'},line)
        for lane, (header, _members) in enumerate(lanes):
            element(annotation,'text',{'x':xs[lane],'y':hy,'text-anchor':'middle',
                                       'style':'font-size:19px;font-weight:bold;fill:#3e5a66'},header)
    # The honesty note lives in section 3's own heading, clear of every lane.
    for el in contents.iter():
        if el.get('data-topic-id')=='terminal':
            texts=[e for e in el if e.tag.endswith('text')]
            texts[1].text='What needs checking at APM? Follow 1 → 2 → 3: an arranged reading order'
        elif el.get('data-topic-id')=='vehicle':
            texts=[e for e in el if e.tag.endswith('text')]
            texts[1].text='What vehicle and driver facts matter? Truck left, driver right'
        elif el.get('data-topic-id')=='permits':
            texts=[e for e in el if e.tag.endswith('text')]
            texts[1].text='Which permit questions remain? Path left, dated notices right: recheck'
        elif el.get('data-topic-id')=='road_rules':
            texts=[e for e in el if e.tag.endswith('text')]
            texts[1].text='Which road rules and authorities are recorded? One lane per road owner'
        elif el.get('data-topic-id')=='traffic':
            texts=[e for e in el if e.tag.endswith('text')]
            texts[1].text='What does the traffic evidence actually tell us? Counts, context, verdict'
    element(annotation,'text',{'x':mx+22,'y':my+35,'style':'font-size:18px;fill:#627970'},'NJOGIS centerlines · recorded coordinates · north up')
    element(annotation,'text',{'x':mx+mw-38,'y':my+38,'style':'font-size:23px;font-weight:bold'},'N ↑')
    length=500*scale
    element(annotation,'path',{'d':f'M{mx+25},{my+mh-35} v8 h{length} v-8','stroke':'#5d706b','stroke-width':2,'fill':'none'})
    element(annotation,'text',{'x':mx+25,'y':my+mh-9,'style':'font-size:15px;fill:#627970'},'500 m')
    element(annotation,'text',{'x':mx+260,'y':my+mh-13,'style':'font-size:16px;fill:#7f6033'},'Dashed amber: candidate northbound ramps, not truck verified')
    element(svg,'text',{'x':65,'y':62,'style':'font-size:39px;font-weight:bold'},'Drayage knowledge graph · geographic integration draft')
    element(svg,'text',{'x':65,'y':104,'style':'font-size:23px;fill:#526572'},'114 nodes · 281 relationships drawn · 121 nodes · 345 relationships in the archived graph')
    for i,(name,(fill,stroke)) in enumerate(PALETTE.items()):
        x=65+i*475
        element(svg,'circle',{'cx':x,'cy':140,'r':8,'fill':fill,'stroke':stroke})
        element(svg,'text',{'x':x+20,'y':147,'style':'font-size:18px'},name)
    element(svg,'text',{'x':65,'y':height-28,'style':'font-size:19px;fill:#65747e'},
            'Draft for comparison · heavy lines = GIS roads; thin arrows = graph relationships · route order and source citations live in the graph data · archived July 2026 geography, not current trip clearance')
    element(svg,'text',{'x':1430,'y':1300,'style':'font-size:19px;fill:#65747e'},
            'Routes follow the road geometry above; their sequences and source citations are retained in the graph data.')
    drawn_nodes={e.get('data-node-id') for e in svg.iter() if 'data-node-id' in e.attrib}
    drawn_edges={e.get('data-edge-id') for e in svg.iter() if 'data-edge-id' in e.attrib}
    if drawn_nodes!=set(nodes)-HIDDEN or drawn_edges!=set(edges)-hidden_edges:raise ValueError('Graph membership changed')
    audit={'nodes':len(drawn_nodes),'relationships':len(drawn_edges),'geographic_locations':10,'geographic_segments':9,
           'projection':'Local equirectangular; north up; same metre scale in x/y',
           'positions':positions,'geographic_ids':sorted(geo_ids),'label_positions':labels,
           'hidden_nodes':sorted(HIDDEN),'hidden_relationships':len(hidden_edges),
           'archive_nodes':len(nodes),'archive_relationships':len(edges),
           'graph_records_changed':False,'canonical_png_replaced':False}
    return ET.tostring(svg,encoding='unicode'),audit


if __name__=='__main__':
    svg,audit=render()
    out=ROOT/'output/integrated-geographic-draft';out.mkdir(parents=True,exist_ok=True)
    (out/'knowledge-graph-geographic-draft.svg').write_text(svg)
    (out/'draft-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    print(f'Draft saved: {audit["nodes"]} nodes, {audit["relationships"]} relationships')
