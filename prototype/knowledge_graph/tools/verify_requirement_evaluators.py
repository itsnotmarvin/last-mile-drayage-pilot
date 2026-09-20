"""Capture eleven bounded evaluators through live Neo4j stdio and local HTTP.

No model prompts or browser acceptance. The operator seeds synthetic receipts
outside client endpoints; MCP/application callers cannot write verifications.
"""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
from http.cookiejar import CookieJar
import importlib.util
import json
import os
from pathlib import Path
import selectors
import sqlite3
import subprocess
import sys
import tempfile
import time
from urllib.request import build_opener, HTTPCookieProcessor, ProxyHandler, Request
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from verification_fixtures import facts, receipts, RELEASE
from neo4j_kg.verification import REQUIRED_KINDS
from neo4j_kg.verification_store import VerificationStore
from neo4j_kg.trip_state import TripStore
from neo4j_kg.release_readiness import runtime_hashes
from neo4j_kg.decision_brief import render_trip_report
from trip_app.operations import private_write, read_secret
from trip_app.store import Workspace, secret_hash
from trip_app.mcp_server import Client


def semantics(a):
    return [(r['requirement_id'],r['status'],r['reason_codes'],r.get('checks')) for r in a['findings']]


def row(a,rid):return next(r for r in a['findings'] if r['requirement_id']==rid)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--credentials-file',type=Path,required=True)
    p.add_argument('--private-directory',type=Path,required=True)
    p.add_argument('--origin',default='http://127.0.0.1:8765')
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();Client(args.origin,'origin-validation-only')
    out=args.output;out.mkdir(parents=True,mode=0o700,exist_ok=False)
    before=runtime_hashes();script_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    def save(name,obj):private_write(out/name,json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
    transcript=[];assessments=[];operator_events=[]
    entry='''import sys
from pathlib import Path
from neo4j_kg.service import CheckingService
from neo4j_kg.assessment import TripService
from neo4j_kg.trip_state import TripStore
from neo4j_kg.verification_store import VerificationStore
from neo4j_kg.mcp_server import Session,serve
service=CheckingService()
try:serve(sys.stdin.buffer,sys.stdout,Session(service,trip_service=TripService(service.store,TripStore(Path(sys.argv[1])),VerificationStore(Path(sys.argv[2])))))
finally:service.close()
'''
    env=os.environ|{'NEO4J_CREDENTIALS_FILE':str(args.credentials_file.resolve()),'DRAYAGE_NEO4J_REVISION':RELEASE}
    with tempfile.TemporaryDirectory(dir=ROOT/'.runtime',prefix='eleven-live-') as temp, (out/'stdio-stderr.txt').open('w') as err:
        state_path=Path(temp)/'trips.sqlite3';store=VerificationStore(Path(temp)/'verifications.sqlite3')
        proc=subprocess.Popen([sys.executable,'-c',entry,str(state_path),str(store.path)],cwd=ROOT,env=env,
                              stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=err,text=True,bufsize=1)
        selector=selectors.DefaultSelector();selector.register(proc.stdout,selectors.EVENT_READ)
        def request(method,params,notify=False):
            req={'jsonrpc':'2.0','method':method,'params':params}
            if not notify:req['id']=len(transcript)+1
            proc.stdin.write(json.dumps(req)+'\n');proc.stdin.flush()
            if notify:return
            if not selector.select(55):raise RuntimeError('MCP response timed out')
            res=json.loads(proc.stdout.readline());transcript.append({'request':req,'response':res})
            assert res.get('id')==req['id'] and 'error' not in res
            return res['result']
        def call(name,arguments,rejected=False):
            result=request('tools/call',{'name':name,'arguments':arguments})
            assert result['isError'] is rejected
            if rejected:return
            a=result['structuredContent'];assert json.loads(result['content'][-1]['text'])==a
            if a.get('schema_version')=='drayage-trip-assessment-v1':
                assert a['service_status']=='available'
                assert a['decision_brief']['operational_permission']=='not_issued'
                assessments.append(a)
            return a
        def create(role='driver',raw=None):
            return call('assess_trip',{'facts':facts() if raw is None else raw,'source_message':'Synthetic structured evaluator fixture.',
                        'request_key':uuid.uuid4().hex,'requester_role':role,'question_scope':'trip_dispatch'})
        def seed(a,mutate=None):
            case=TripStore(state_path).get(a['case']['trip_id']);rs=receipts(case,uuid.uuid4().hex)
            if mutate:mutate(rs)
            snapshot=store.put(rs,case,RELEASE)
            operator_events.append({'operation':'synthetic_operator_seed','trip_id':case['trip_id'],'receipts':rs,'snapshot_version':snapshot['version']})
            return call('assess_trip',{'trip_id':case['trip_id']})
        try:
            request('initialize',{'protocolVersion':'2025-11-25','capabilities':{},'clientInfo':{'name':'eleven-evaluator-verifier','version':'1'}})
            request('notifications/initialized',{},True)
            save('tools.json',request('tools/list',{}))
            positives=[]
            for role in ('driver','dispatcher'):
                a=create(role);assert a['coverage']['executed_requirements']==['apm_induction']
                a=seed(a);positives.append(a)
                for rid in REQUIRED_KINDS:
                    assert row(a,rid)['execution_state']=='evaluated'
                    assert row(a,rid)['status']==('unresolved' if rid=='dtr_engine_policy' else 'met'),rid
            assert semantics(positives[0])==semantics(positives[1])
            cases=[('axle_weight_evidence','scale','weight'),('dimensions_and_route','dimensions','height'),
                   ('permit_eligibility','permit',{'status':'revoked'}),('cross_authority_coverage','approval',{'status':'denied'}),
                   ('current_route_conditions','conditions',{'status':'closed'}),('dtr_registration_and_rfid','dtr',{'rfid_valid':False}),
                   ('dtr_engine_policy','dtr',{'meets_2014_emissions_standard':False}),('driver_twic','twic',{'status':'revoked'}),
                   ('sealink_registration','sealink',{'active':False}),('apm_appointment','appointment',{'status':'cancelled'}),
                   ('transaction_release','transaction',{'fully_available':False,'customs_hold':True})]
            for rid,kind,changes in cases:
                raw=facts()
                if changes=='weight':
                    raw['axle_layout']['axles'][0]['weight']['value']=22000;raw['gross_weight']['value']=82000
                if changes=='height':raw['height']['value']=163
                a=create(raw=raw)
                def mutate(rs):
                    if isinstance(changes,dict):next(r for r in rs if r['kind']==kind)['payload'].update(changes)
                a=seed(a,mutate)
                assert row(a,rid)['status']==('unresolved' if rid=='dtr_engine_policy' else 'not_met'),(rid,row(a,rid))
            a=positives[0]
            twic_id=next(r['id'] for r in a['verification_evidence']['accepted_receipts'] if r['kind']=='twic')
            store.revoke(twic_id,'Synthetic audit revocation')
            operator_events.append({'operation':'synthetic_operator_revoke','id':twic_id})
            revoked=call('assess_trip',{'trip_id':a['case']['trip_id']})
            assert row(revoked,'driver_twic')['status']=='unresolved' and a['assessment_id']!=revoked['assessment_id']
            updated=call('update_trip_facts',{'trip_id':a['case']['trip_id'],'expected_revision':1,'facts':{'load_id':'syn-load-new'},
                'replace_conflicts':True,'source_message':'Explicit synthetic load reassignment.','request_key':uuid.uuid4().hex,
                'requester_role':'driver','question_scope':'trip_dispatch'})
            assert not updated['verification_evidence']['accepted_receipts']
            assert updated['verification_evidence']['rejected_receipts']
            call('assess_trip',{'facts':{'verification_receipts':[]},'source_message':'Attempted caller verification.',
                              'request_key':uuid.uuid4().hex},rejected=True)
            save('transaction-evidence.json',call('get_requirement_evidence',{'requirement_id':'transaction_release'}))
            private_write(out/'sample-trip-report.html',render_trip_report(positives[0]))
        finally:
            proc.stdin.close()
            try:proc.wait(timeout=10)
            except subprocess.TimeoutExpired:proc.kill();proc.wait()
            proc.stdout.close();selector.close()
    assert proc.returncode==0
    save('mcp-transcript.json',transcript);save('operator-fixture-events-stdio.json',operator_events)

    http=[];http_assessments=[];http_positives=[];renewals=[]
    dbpath=(args.private_directory/'app.sqlite3').resolve()
    for role,user in (('driver','syn-user-driver'),('dispatch','syn-user-dispatch')):
        key=read_secret(args.private_directory/(role+'.key'))
        with sqlite3.connect(dbpath.as_uri()+'?mode=ro',uri=True) as db:
            valid=db.execute('SELECT 1 FROM app_access WHERE hash=? AND expires>?',(secret_hash(key),time.time())).fetchone()
        if not valid:
            key=Workspace(dbpath).issue_access(user)
            private_write(args.private_directory/(role+'-eleven-'+uuid.uuid4().hex+'.key'),key)
            renewals.append(user)
        client=build_opener(ProxyHandler({}),HTTPCookieProcessor(CookieJar()));csrf=''
        def http_call(path,body=None,record=True):
            req=Request(args.origin+path,data=json.dumps(body).encode() if body is not None else None,
                headers={'Origin':args.origin,'Content-Type':'application/json','X-CSRF-Token':csrf})
            with client.open(req,timeout=55) as res:
                assert res.status==200;value=json.load(res)
            if record:http.append({'role':role,'path':path,'body':body,'status':200,'response':value})
            if value.get('assessment'):
                a=value['assessment'];assert a['service_status']=='available';http_assessments.append(a)
            return value
        csrf=http_call('/api/login',{'key':key},record=False)['csrf']
        cid=http_call('/api/conversations',{})['id'];path='/api/conversations/'+cid
        view=http_call(path+'/message',{'version':0,'statement':'Synthetic structured evaluator acceptance fixture.','request_key':uuid.uuid4().hex})
        assert view['assessment'] is None
        view=http_call(path+'/confirm',{'version':1,'proposal_id':view['proposals'][0]['id'],'facts':facts(),'scope':'trip_dispatch'})
        assert view['assessment']['coverage']['executed_requirements']==['apm_induction']
        case=Workspace(dbpath).trips.get(view['case']['trip_id'])
        rs=receipts(case,'http-'+uuid.uuid4().hex);opstore=VerificationStore();snap=opstore.put(rs,case,RELEASE)
        operator_events.append({'operation':'http_synthetic_operator_seed','trip_id':case['trip_id'],'receipts':rs,'snapshot_version':snap['version']})
        view=http_call(path);a=view['assessment'];http_positives.append(a)
        for rid in REQUIRED_KINDS:assert row(a,rid)['status']==('unresolved' if rid=='dtr_engine_policy' else 'met')
        twic=next(r for r in rs if r['kind']=='twic');opstore.revoke(twic['id'],'Synthetic HTTP audit revocation')
        operator_events.append({'operation':'http_synthetic_operator_revoke','id':twic['id']})
        view=http_call(path)
        assert row(view['assessment'],'driver_twic')['status']=='unresolved'
        assert view['assessment']['assessment_id']!=a['assessment_id']
    assert semantics(http_positives[0])==semantics(http_positives[1])
    assert http_positives[0]['case']['trip_id']!=http_positives[1]['case']['trip_id']
    with build_opener(ProxyHandler({})).open(args.origin+'/app.js',timeout=10) as res:served=res.read()
    assert hashlib.sha256(served).hexdigest()==before['trip_app/static/app.js']
    save('http-transcript.json',http);save('operator-fixture-events.json',operator_events)
    assert runtime_hashes()==before,'Runtime changed during verification'
    assert script_sha==hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    save('assessments.json',assessments+http_assessments)
    save('summary.json',{'at':datetime.now(timezone.utc).isoformat(),'graph_release':RELEASE,
        'runtime_sha256':before,'verifier_sha256':script_sha,
        'surface':'local_stdio_and_http_live_neo4j_no_model_no_browser',
        'stdio_assessments':len(assessments),'http_assessments':len(http_assessments),
        'implemented_evaluators_exercised':list(REQUIRED_KINDS),'matching_driver_dispatch_predicates':True,
        'revocation_rechecked_stdio_and_http':True,'reassignment_rejects_old_receipts':True,
        'caller_verification_injection_rejected':True,'served_javascript_matches_runtime':True,
        'networkx_present_in_runtime':bool(importlib.util.find_spec('networkx')),
        'temporary_synthetic_access_renewals':renewals,'operational_permission':'not_issued',
        'browser_acceptance':'not_run_prior_ERR_BLOCKED_BY_CLIENT_unresolved',
        'model_acceptance':'not_run','new_proposal_bridge':'unattached'})
    print(f'Captured {len(assessments)} stdio and {len(http_assessments)} HTTP assessments against live Neo4j.')


if __name__=='__main__':main()
