"""282 selects the local restore by its source-owned caller edge."""
from pathlib import Path
from types import SimpleNamespace
import v281_native_prepare as retained

p,require,sha,bind=retained.p,retained.require,retained.sha,retained.bind
scoped=retained.scoped
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
WORKFLOW='.github/workflows/note10-v282-native-prepare.yml';JOB='v282-native-prepare'
BUILD_SCHEMA='note10-v282-holder-carrier-build-v1'
CONTEXT_SCHEMA='note10-v282-holder-carrier-public-input-v1'
MANIFEST_SCHEMA='note10-v282-holder-carrier-sealed-members-v1'
SUCCESS_MEMBERS=retained.SUCCESS_MEMBERS
NAMED,NAMED_CAP,OUTLINED_CAP,EXTENT_CAP=retained.NAMED,14,30,44
RESTORE,CALLER=retained.RESTORE,retained.CALLER
OWNER_TARGET,OWNER,VALIDATORS=retained.retained.OWNER_TARGET,retained.retained.OWNER,retained.retained.VALIDATORS
provenance=retained.retained.provenance
instruction_words,restore_shape=retained.instruction_words,retained.restore_shape
NEW_FILES=('v282_native_prepare.py','test_v282_contextual_selection.py')
CARRIED281=dict(passed=True,groups=1,variants=1,assertions=1,host_compile_attempts=0,host_fixture_process_attempts=0,result_sha256='bda75571a4c9d092c5a7885e506b8c3547e716494dcf3c42f4fef84933d5a0ae',source_head='3dfd78aa7226217fc4ae13695ae74c9cda70f6ec',replayed=False)
stack_once=bind(retained.stack_once,{**retained.stack_once.__globals__,'_STACK':{}})
stream_candidate=SimpleNamespace(**{**vars(retained.stream_candidate),'verify_stack_evidence':stack_once})

def source_pins():
    pins=retained.source_pins();pins.pop(retained.WORKFLOW)
    pins.update({'note10/device_test/'+n:sha(p.ordinary(HERE/n))for n in NEW_FILES})
    pins[WORKFLOW]=sha(p.ordinary(ROOT/WORKFLOW));return pins

def public_context(head,passed):
    value=retained.public_context(head,passed)
    value.update(schema=CONTEXT_SCHEMA,source_sha256=source_pins(),carried281_fixture_PASS=CARRIED281)
    return value

def restore_inputs(raw,table):
    def body(name,record=None):
        if record is None:
            require(name in table and len(table[name])==1,'unique exact contextual caller')
            record=dict(name=name,**table[name][0],offset=0)
        else:
            require(sum(record==dict(name=name,**row,offset=0)for row in table.get(name,()))==1,'exact edge-selected local record including ordinal')
        symbol=scoped.symbol_extent(table,name,record,name==RESTORE)
        text=raw['bodies'][format(symbol['address'],'016x')+':'+str(symbol['bytes'])]
        proof=scoped.scoped_transfers(text,symbol,table)
        return record,symbol,scoped.flow.parse_body(text,proof),instruction_words(text),proof
    caller,cs,cr,cw,cp=body(CALLER)
    require(len(cr)>=3,'complete caller suffix')
    edges=[edge for edge in cp['external_transfers']if edge['address']==cr[-3][0]]
    require(len(edges)==1,'one actual suffix transfer')
    edge=edges[0];records=edge['resolved_records']
    require(cr[-3][1]==edge['mnemonic']=='bl'and not edge['unresolved']and edge['resolved_symbols']==[RESTORE]and len(records)==1,'one unambiguous direct local restore target')
    helper=records[0]
    require(helper['name']==RESTORE and helper['kind']=='t'and helper['offset']==0 and helper['address']==edge['target']and helper['bytes']==12,'exact local restore entry/extent, no interior or alias fallback')
    helper,hs,hr,hw,hp=body(RESTORE,helper)
    require(cs['bytes']==260 and hs['bytes']==12 and not hp['external_transfers'],'one exact caller and full restore extent')
    item=raw['objects'][OWNER_TARGET]
    context,roots,reader=provenance(OWNER_TARGET,(OWNER,'n279_layout_witness',*VALIDATORS),item,table)
    joined=reader(context,helper,True)
    require(joined['object']==OWNER_TARGET and joined['binding']=='LOCAL'and joined['frame']['bytes']==0 and roots[CALLER]['frame']['bytes']==48 and joined['section_index']in context['deltas']and joined['object_address']+context['deltas'][joined['section_index']]==hs['address'],'same actual init.o source/ELF/staticSU/linked contextual join')
    external={e['address']:e['target']for e in cp['external_transfers']}
    incoming=[]
    for ident,text in raw['bodies'].items():
        address,size=ident.split(':');key=(int(address,16),int(size))
        names=[n for n,rows in table.items()for row in rows if(row['address'],row['bytes'])==key]
        require(names,'actual captured source extent')
        symbol=dict(symbol=names[0],address=key[0],bytes=key[1],aliases=names)
        proof=scoped.scoped_transfers(text,symbol,table)
        for transfer in proof['external_transfers']:
            if transfer['target']==hs['address']:
                require(names==[CALLER]and not transfer['unresolved']and len(transfer['resolved_records'])==1 and transfer['resolved_records'][0]['offset']==0,'exact unaliased contextual incoming entry')
                incoming.append((CALLER,transfer['address'],transfer['mnemonic']))
    call=restore_shape(cr,cw,hr,hw,external,hs['address'],incoming)
    words={}
    for text in raw['bodies'].values():
        for address,word in instruction_words(text).items():
            require(address not in words,'nonoverlapping selected body encodings')
            words[address]=word
    return dict(call=call,caller_rows=cr,helper_rows=hr,helper_address=hs['address'],words=words,provenance=joined)

_BCMP_ENV={**retained.bcmp_certificate.__globals__,'own_frame':retained.own_frame}
bcmp_certificate=bind(retained.bcmp_certificate,_BCMP_ENV)
_VERIFY_ENV={**retained.verify_seal.__globals__,'restore_inputs':restore_inputs,'stack_once':stack_once,'stream_candidate':stream_candidate,'bcmp_certificate':bcmp_certificate}
verify_seal=retained._bind(retained.verify_seal,_VERIFY_ENV,{'note10-v281-seal-raw-v1':'note10-v282-seal-raw-v1','note10-v281-seal-target-v1':'note10-v282-seal-target-v1'})
_COLLECT_ENV={**retained.collect_binding.__globals__,'verify_seal':verify_seal,'stream_candidate':stream_candidate}
collect_binding=retained._bind(retained.collect_binding,_COLLECT_ENV,{'note10-v281-seal-raw-v1':'note10-v282-seal-raw-v1'})
_bind=retained._bind
_ENV={**retained._ENV,**{n:globals()[n]for n in ('WORKFLOW','JOB','BUILD_SCHEMA','CONTEXT_SCHEMA','MANIFEST_SCHEMA','SUCCESS_MEMBERS','source_pins','public_context','collect_binding','stream_candidate')}}
run_build=_bind(retained.run_build,_ENV,{'note10/private/v281-ci-native-prepare':'note10/private/v282-ci-native-prepare','v281':'v282','"-v281-frame-forms"':'"-v282-contextual-edge-selection"'})
seal=_bind(retained.seal,_ENV,{})
_ENV.update(run_build=run_build,seal=seal)
main=_bind(retained.main,_ENV,{})
if __name__=='__main__':main()
