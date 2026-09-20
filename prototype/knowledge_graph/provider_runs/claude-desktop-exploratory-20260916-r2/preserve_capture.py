"""Preserve this bounded experiment's existing UI and MCP logs; sends no prompts."""
from pathlib import Path
import json, base64, hashlib
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
LOG = Path('/Users/marbin/.t3/userdata/logs/provider/events.db2f55fe-c183-42b0-874a-f41de3d4e9b4.log')
START = '2026-09-17T00:48:00Z'
END = '2026-09-17T00:56:15Z'
def save(name, value):
    (OUT/name).write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n')
ui=OUT/'ui'; ui.mkdir(exist_ok=True)
seen=set(); index=[]
for line in LOG.read_text().splitlines():
    try: x=json.loads(line[line.index('{'):])
    except (ValueError, KeyError): continue
    raw=x.get('raw',{}); item=raw.get('payload',{}).get('item',{})
    if raw.get('method')!='item/completed' or item.get('pluginId')!='unified-computer-use@openai-bundled' or not START<=x.get('createdAt','')<=END: continue
    ident=item['id']
    if ident in seen: continue
    seen.add(ident)
    stem='ui/'+x['createdAt'].replace(':','-')+'-'+ident
    meta={'recorded_at':x['createdAt'],'tool_call_id':ident,'arguments':item.get('arguments'),'source_thread':'db2f55fe-c183-42b0-874a-f41de3d4e9b4','provenance':'Exact completed CUA result recovered from local provider event log. Accessibility text can truncate individual elements; screenshots and streaming observations supplement it.'}
    save(stem+'.json',meta)
    index.append({'title':item.get('arguments',{}).get('title'),'metadata':stem+'.json'})
    for i,c in enumerate(item.get('result',{}).get('content',[])):
        if c.get('type')=='text': (OUT/(stem+f'.{i}.txt')).write_text(c['text'])
        elif c.get('type')=='image': (OUT/(stem+f'.{i}.png')).write_bytes(base64.b64decode(c['data']))
save('ui-index.json',index)
b=json.loads((OUT/'baseline.json').read_text()); events=[]; origins=[]
for p in ROOT.glob('.runtime/mcp-session-*.jsonl'):
    offset=b['audit_offsets'].get(str(p.relative_to(ROOT)),0)
    with p.open('rb') as f: f.seek(offset); data=f.read()
    for line in data.splitlines():
        e=json.loads(line)
        if not START<=e['recorded_at']<=END: continue
        events.append(e); origins.append({'file':str(p.relative_to(ROOT)),'baseline_offset':offset,'event_hash':e['event_hash'],'sequence':e['sequence']})
events.sort(key=lambda e:e['recorded_at'])
save('mcp-events.json',events);save('mcp-origins.json',origins)
print(json.dumps({'ui_calls':len(index),'mcp_events':len(events)}))
