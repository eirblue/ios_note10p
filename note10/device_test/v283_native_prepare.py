"""283 seals the exact existing 42-file evidence inventory."""
import json,stat,subprocess,zipfile
from pathlib import Path
from types import SimpleNamespace
import v282_native_prepare as retained

p,require,sha,bind=retained.p,retained.require,retained.sha,retained.bind
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
WORKFLOW='.github/workflows/note10-v283-native-prepare.yml';JOB='v283-native-prepare'
BUILD_SCHEMA='note10-v283-holder-carrier-build-v1'
CONTEXT_SCHEMA='note10-v283-holder-carrier-public-input-v1'
MANIFEST_SCHEMA='note10-v283-holder-carrier-sealed-members-v1'
SUCCESS_MEMBERS=retained.SUCCESS_MEMBERS
METADATA_TYPES={'name':str,'bytes':int,'regular':bool,'symlink':bool}
NEW_FILES=('v283_native_prepare.py','test_v283_seal_inventory.py')
CARRIED282=dict(passed=True,groups=1,variants=1,assertions=1,host_compile_attempts=0,host_fixture_process_attempts=0,result_sha256='158324797ca5e0607cfab2b276416839d6e4b44e6645f262890946a9a137213b',source_head='3577ddd78581d059934a4dad5a18c9ac003bed45',replayed=False)
stack_once=bind(retained.stack_once,{**retained.stack_once.__globals__,'_STACK':{}})
stream_candidate=SimpleNamespace(**{**vars(retained.stream_candidate),'verify_stack_evidence':stack_once})

def source_pins():
    pins=retained.source_pins();pins.pop(retained.WORKFLOW)
    pins.update({'note10/device_test/'+n:sha(p.ordinary(HERE/n))for n in NEW_FILES})
    pins[WORKFLOW]=sha(p.ordinary(ROOT/WORKFLOW));return pins

def public_context(head,passed):
    value=retained.public_context(head,passed)
    value.update(schema=CONTEXT_SCHEMA,source_sha256=source_pins(),carried282_fixture_PASS=CARRIED282)
    return value

def inventory_metadata(entries,passed):
    require(len(SUCCESS_MEMBERS)==len(set(SUCCESS_MEMBERS))==43 and 'members.json'in SUCCESS_MEMBERS,'fixed reviewed43-member schema; no implicit growth')
    allowed=set(SUCCESS_MEMBERS)-{'members.json'}
    require(len(allowed)==42 and type(passed)is bool and type(entries)is list and 0<len(entries)<=len(allowed),'bounded pre-manifest42 metadata')
    require(all(type(row)is dict and set(row)==set(METADATA_TYPES)and all(type(row[k])is kind for k,kind in METADATA_TYPES.items())for row in entries),'exact inventory metadata types')
    sizes={row['name']:row['bytes']for row in entries}
    require(len(sizes)==len(entries)and 'result.json'in sizes and set(sizes)<=allowed and(not passed or set(sizes)==allowed),'exact producer inventory; partial failures remain diagnostic only')
    require(all(row['regular']and not row['symlink']and 0<row['bytes']<=67108864 for row in entries)and sum(sizes.values())<=134217728,'bounded regular nonlink producer evidence')
    return sizes

def seal(out,head):
    files=sorted(out.iterdir())
    result=json.loads((out/'result.json').read_bytes())
    sizes=inventory_metadata([dict(name=x.name,bytes=x.stat().st_size,regular=stat.S_ISREG(x.stat().st_mode),symlink=x.is_symlink())for x in files],result['passed'])
    manifest=dict(schema=MANIFEST_SCHEMA,source_head=head,member_bytes=sizes,member_sha256={x.name:sha(p.ordinary(x,67108864))for x in files},manifest_self_excluded=True)
    p.save(out/'members.json',manifest)
    with zipfile.ZipFile(out.with_suffix('.zip'),'x',compression=zipfile.ZIP_DEFLATED)as bundle:
        for path in [*files,out/'members.json']:bundle.write(path,path.name)
    subprocess.run(['node',str(ROOT/'note10/device_test/sealed_affinity_artifact.cjs'),'seal',str(out.with_suffix('.zip')),str(out.with_suffix('.n10sealed')),head],check=True,timeout=120)

_VERIFY_ENV={**retained.verify_seal.__globals__,'stack_once':stack_once,'stream_candidate':stream_candidate}
verify_seal=retained._bind(retained.verify_seal,_VERIFY_ENV,{'note10-v282-seal-raw-v1':'note10-v283-seal-raw-v1','note10-v282-seal-target-v1':'note10-v283-seal-target-v1'})
_COLLECT_ENV={**retained.collect_binding.__globals__,'verify_seal':verify_seal,'stream_candidate':stream_candidate}
collect_binding=retained._bind(retained.collect_binding,_COLLECT_ENV,{'note10-v282-seal-raw-v1':'note10-v283-seal-raw-v1'})
_bind=retained._bind
_ENV={**retained._ENV,**{n:globals()[n]for n in ('WORKFLOW','JOB','BUILD_SCHEMA','CONTEXT_SCHEMA','MANIFEST_SCHEMA','SUCCESS_MEMBERS','source_pins','public_context','collect_binding','stream_candidate')}}
run_build=_bind(retained.run_build,_ENV,{'note10/private/v282-ci-native-prepare':'note10/private/v283-ci-native-prepare','v282':'v283','"-v282-contextual-edge-selection"':'"-v283-seal-inventory"'})
_ENV.update(run_build=run_build,seal=seal)
main=_bind(retained.main,_ENV,{})
if __name__=='__main__':main()
