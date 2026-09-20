"""Apply reversible display-only properties to the pinned prototype release."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from neo4j_kg.config import connect
from neo4j_kg.store import read_release
from neo4j_kg.common import DATASET
REV='f5dffe0f7a32b5144920efb5a644f8c4dc9f20def76b4217c38b0cdbc454cf5c'
def main():
    driver,db=connect(Path.home()/'.config/drayage-mcp/neo4j.env')
    try:
        with driver.session(database=db) as s:
            before=s.execute_read(lambda tx:read_release(tx,REV))
            layout=json.loads((ROOT/'presentation/organized-layout.json').read_text())
            labels=json.loads((ROOT/'presentation/labels.json').read_text())
            pos={n:[x,-(y+650 if y>=1550 else y)] for n,(x,y) in layout['positions'].items()}
            topics={n:r['title'] for r in layout['regions'] for n in r['nodes']}
            extras=[n for n in before['nodes'] if n['id'] not in pos]
            for i,n in enumerate(extras):
                pos[n['id']]=[2940+(i%4)*275,-(1190+(i//4)*150)]
                topics[n['id']]='3 · Terminal entry'
            rows=[]
            for n in before['nodes']:
                record=json.loads(n['record_json']); d=record.get('properties',record)
                caption=labels.get(n['id']) or d.get('name') or d.get('label') or d.get('title') or n['id'].replace('_',' ')
                k=n['kind']; category='Authorities & places'
                if k=='source_document':category='Sources'
                elif k=='source_clause':category='Rules'
                elif k in ('physical_location','road_segment','route_family','route_approach'):category='Roads & routes'
                elif k in ('mutable_observation','historical_traffic_analysis'):category='Dated observations & analysis'
                elif k in ('credential','registration','operational_system','training','project_profile_not_live_vehicle') or k.startswith('synthetic_'):category='Credentials & profiles'
                rows.append(dict(id=n['id'],x=pos[n['id']][0],y=pos[n['id']][1],caption=str(caption),topic=topics[n['id']],category=category))
            def write(tx):
                result=tx.run('UNWIND $rows AS r MATCH (n:DrayageRecord {dataset:$dataset,revision:$revision,id:r.id}) SET n.viz_x=r.x,n.viz_y=r.y,n.viz_caption=r.caption,n.viz_topic=r.topic,n.viz_category=r.category RETURN count(n) AS count',rows=rows,dataset=DATASET,revision=REV).single()['count']
                if result!=144:raise ValueError('Unexpected display-property update count')
                return result
            count=s.execute_write(write)
            after=s.execute_read(lambda tx:read_release(tx,REV))
            assert before==after, 'Evidence release changed'
            print(json.dumps({'styled_nodes':count,'evidence_release_unchanged':True}))
    finally:driver.close()
if __name__=='__main__':main()
