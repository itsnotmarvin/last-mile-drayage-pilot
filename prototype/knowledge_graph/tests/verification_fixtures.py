"""Deliberately synthetic operator-adapter fixtures, never production evidence."""
import copy

from neo4j_kg.verification_models import VERSION, PROVIDERS, case_fingerprint

AT='2026-09-13T14:00:00-04:00'
BEFORE='2026-09-13T12:00:00-04:00'
UNTIL='2026-09-13T16:00:00-04:00'
RELEASE='f5dffe0f7a32b5144920efb5a644f8c4dc9f20def76b4217c38b0cdbc454cf5c'

# Graph-resolved ordered segments for path_a_exit13a_to_apm (pinned release).
PATH_A_SEGMENTS=(
    'edge_a_exit13a_connector',
    'edge_shared_north_avenue',
    'edge_shared_mclester',
    'edge_shared_tripoli_gate',
)


def facts():
    return {'terminal_id':'facility_apm_elizabeth','subject_role':'truck_driver',
            'driver_id':'syn-driver-complete','current_sealink_id':'SYN-SL-A',
            'vehicle_id':'syn-vehicle-eval','trailer_id':'syn-trailer-eval','load_id':'syn-load-eval',
            'move_id':'syn-move-eval','move_type':'import_pickup','trip_at':AT,
            'route_id':'path_a_exit13a_to_apm','route_description':'Synthetic Interstate segment to APM',
            'port_street_in_route':False,
            'gross_weight':{'value':70000,'unit':'lb'},
            'axle_layout':{'axles':[{'position':{'value':p,'unit':'in'},'weight':{'value':w,'unit':'lb'}}
                                     for p,w in zip((0,144,192,576,624),(10000,15000,15000,15000,15000))]},
            'height':{'value':162,'unit':'in'},'width':{'value':102,'unit':'in'},
            'overall_length':{'value':840,'unit':'in'},'semitrailer_length':{'value':576,'unit':'in'},
            'permit_type':'nj_single_trip','container_sealed':True,'load_divisible':False,
            'engine_model_year':2015}


def receipts(case, suffix='a'):
    f={k:v['value'] for k,v in case['facts'].items()}
    equipment={k:f[k] for k in ('vehicle_id','trailer_id','load_id')}
    route={k:f[k] for k in ('route_id','route_description')}
    move={k:f[k] for k in ('move_id','move_type','terminal_id')}
    dims={k+'_inches':f[k] for k in ('height','width','overall_length','semitrailer_length')}
    limits={'gross_lb':90000,'single_axle_lb':22000,'tandem_lb':38000,**dims}
    payloads={
        'scale':{**equipment,'gross_weight_lb':f['gross_weight'],'axle_layout':f['axle_layout'],'weighing_method':'fixed_scale'},
        'dimensions':{**equipment,**dims,'kingpin_to_rear_axle_inches':None,'configuration':'standard_tractor_semitrailer'},
        'route':{**equipment,**route,'terminal_id':f['terminal_id'],'complete_sequence_verified':True,'exception_claimed':False,
                 'segments':[{'segment_id':sid,'authority':'nj_state','weight_regime':'federal_interstate',
                              'dimension_regime':'nj_102_network','local_direct_terminal_access_verified':False,
                              'long_semitrailer_access_verified':False,'access':'permitted','posted_limits':{}}
                             for sid in PATH_A_SEGMENTS]},
        'permit':{**equipment,**route,'permit_type':f['permit_type'],'permit_id':'syn-permit-eval','issuer':'nj_state','status':'valid',
                  'load_nondivisible':True,'sealed_ocean_borne_container':True,'conditions_satisfied':True,'authorized_limits':limits},
        'approval':{**equipment,**route,'authority':'nj_state','segment_ids':list(PATH_A_SEGMENTS),'status':'approved','conditions_satisfied':True},
        'conditions':{**equipment,**route,'segment_id':PATH_A_SEGMENTS[0],'authority':'nj_state',
                      'posting_checked':True,'closure_checked':True,'lane_and_detour_checked':True,'escort_checked':True,
                      'status':'open','conditions_satisfied':True,'posted_limits':{},
                      'source_reference':'Synthetic county operations desk, call reference OPS-1',
                      'evidence_sha256':'0'*64},
        'dtr':{'vehicle_id':f['vehicle_id'],'drayage_truck':True,'class_8':True,'registered':True,'active':True,
               'rfid_assigned':True,'rfid_mounted':True,'rfid_valid':True,'registered_at':'2026-08-01T00:00:00-04:00',
               'registration_changed_at':None,'registration_amended_at':None,'engine_model_year':2015,
               'meets_2014_emissions_standard':True,'registration_event':'existing_registration'},
        'twic':{'driver_id':f['driver_id'],'unescorted_secure_access':True,'exception_claimed':False,'status':'valid',
                'credential_expires_at':'2026-12-31T00:00:00-05:00','physically_present':True},
        'sealink':{'driver_id':f['driver_id'],'current_sealink_id':f['current_sealink_id'],'active':True,'twic_registered':True},
        'appointment':{**move,'vehicle_id':f['vehicle_id'],'status':'confirmed','slot_start':BEFORE,'slot_end':UNTIL},
        'transaction':{**move,'load_id':f['load_id'],'fully_available':True,'holds_complete':True,
                       'freight_hold':False,'customer_hold':False,'demurrage_hold':False,'customs_hold':False,'other_hold':False},
    }
    records=[{'schema_version':VERSION,'mode':'synthetic_only','id':'syn-verification-'+kind+'-'+suffix,
             'kind':kind,**PROVIDERS[kind],'graph_release':RELEASE,'trip_id':case['trip_id'],
             'trip_revision':case['revision'],'case_sha256':case_fingerprint(case),
             'observed_at':BEFORE,'valid_from':BEFORE,'valid_until':UNTIL,'payload':p} for kind,p in payloads.items()]
    base_conditions=next(r for r in records if r['kind']=='conditions')
    for position, segment_id in enumerate(PATH_A_SEGMENTS[1:], start=1):
        extra=copy.deepcopy(base_conditions)
        extra['id']='%s-%d' % (base_conditions['id'], position)
        extra['payload']={**extra['payload'],'segment_id':segment_id}
        records.append(extra)
    return records
