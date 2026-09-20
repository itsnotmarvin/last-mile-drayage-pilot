"""Inventory repository files and screen retained PDF quotations at their locators."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import unicodedata

ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parents[1]
OUT=ROOT/'audits/evidence-2026-09-10'

def normal(text):
    return re.sub(r'[^a-z0-9]','',unicodedata.normalize('NFKC',text).lower())

def leaves(value):
    if isinstance(value,str):return [value]
    if isinstance(value,list):return [s for v in value for s in leaves(v)]
    if isinstance(value,dict):return [s for v in value.values() for s in leaves(v)]
    return []

def main():
    r=json.loads((ROOT/'data/neo4j_release.json').read_text())
    records={n['id']:json.loads(n['record_json']) for n in r['nodes']}
    linked={}
    for n in r['nodes']:
        for f in records[n['id']].get('archived_files',[]):linked.setdefault(f['path'],[]).append(n['id'])
    # Respect .gitignore: don't read credential stores, environments, .runtime,
    # or .git internals. Include both tracked and ordinary untracked repo files.
    names=subprocess.check_output(['rg','--files','--hidden','-g','!.git','-g','!prototype/knowledge_graph/audits'],cwd=REPO,text=True).splitlines()
    names=sorted(set(names)|set(r['file_hashes']))
    inventory=[]
    for name in names:
        p=REPO/name
        if not p.is_file():continue
        category='pinned_release_input' if name in r['file_hashes'] else 'source_linked' if name in linked else 'not_linked_to_pinned_release'
        if name.startswith('prototype/') and name not in r['file_hashes']:purpose='prototype_code_tests_or_artifacts'
        elif name.startswith('data/raw/'):purpose='raw_evidence_candidate'
        elif name.startswith('data/processed/'):purpose='processed_evidence'
        elif name.startswith('docs/'):purpose='documentation'
        else:purpose='repository_support_or_artifact'
        h=hashlib.sha256()
        with p.open('rb') as f:
            while chunk:=f.read(1024*1024):h.update(chunk)
        inventory.append({'path':name,'bytes':p.stat().st_size,'sha256':h.hexdigest(),'status':category,'purpose':purpose,'linked_source_ids':linked.get(name,[])})
    extracts=OUT/'source-extracts';extracts.mkdir(exist_ok=True)
    pages={};screens=[]
    for n in r['nodes']:
        if n['kind']!='source_clause':continue
        c=records[n['id']];source=records[c['source_id']]
        pdfs=[f['path'] for f in source.get('archived_files',[]) if f['path'].endswith('.pdf')]
        row={'clause_id':n['id'],'source_id':c['source_id'],'locator':c['source_locator'],'declared_verbatim':c.get('source_text_verbatim'),'screen':'not_pdf_source','quotes':[]}
        if pdfs:
            file=pdfs[0]
            if file not in pages:
                text=subprocess.check_output(['pdftotext','-layout',str(REPO/file),'-'],text=True)
                pages[file]=text.split('\f');(extracts/(Path(file).stem+'.txt')).write_text(text)
            matches=list(re.finditer(r'PDF pages? (\d+)(?:[-–](\d+))?',c['source_locator']))
            wanted=sorted({i for m in matches for i in range(int(m[1]),int(m[2] or m[1])+1)})
            selected='\n'.join(pages[file][i-1] for i in wanted if 0<i<=len(pages[file]))
            for quote in leaves(c['source_text']):
                q=normal(quote)
                if not q:continue
                row['quotes'].append({'quote':quote,'matches_locator_pages':bool(wanted) and q in normal(selected),
                                      'matches_any_page':q in normal('\n'.join(pages[file]))})
            row.update(pdf=file,locator_pdf_pages=wanted,screen='normalized_text_screen_not_semantic_validation')
        screens.append(row)
    counts={}
    for f in inventory:counts[f['status']]=counts.get(f['status'],0)+1
    report={'scope':'Non-ignored repository files excluding this generated audit directory, plus all pinned inputs. Runtime databases, .git and environments are excluded. Inventory is not proof every file should be ingested.',
            'file_counts':counts,'release_input_count':len(r['file_hashes']),
            'unlinked_raw_candidates':[f['path'] for f in inventory if f['purpose']=='raw_evidence_candidate' and f['status']=='not_linked_to_pinned_release'],
            'pdf_clauses_screened':sum(bool(s['quotes']) for s in screens),
            'pdf_quote_flags':[{'clause_id':s['clause_id'],'locator':s['locator'],'quote':q['quote'],'found_elsewhere':q['matches_any_page']} for s in screens for q in s['quotes'] if not q['matches_locator_pages']],
            'limits':['Normalized text search is a triage screen, not legal/scope validation','Non-PDF quotations require separate source review','Human review is needed for table interpretation and unresolved text mismatches']}
    for name,data in [('repository-inventory.json',inventory),('pdf-quote-screen.json',screens),('source-coverage.json',report)]:
        (OUT/name).write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
