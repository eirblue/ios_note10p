"""Default-off owned RAM attach/start consumer, retained but never invoked."""
import json
from pathlib import Path
import re
import current_native_kernel as native

ROOT=Path(__file__).resolve().parents[2]
KEY='owned_ram_factory'
UNIT='@port/note10_owned_ram_nub.cpp'
SOURCE='note10/xnu26/note10_owned_ram_nub.cpp'
PINS={SOURCE:'4dde1c336eb0ce597e83949880f25456838a2d241e204fc459191e8c9ddf8780',
      'note10/xnu26/note10_owned_ram_nub.h':'333b7997d59afbeb32ba2ed2bbb82d95bcc33d682a342d4bf39ae150368d9c39',
      'note10/xnu26/note10_readonly_ram_block_device.h':'14ef1309e063789911190f6c7d4c7cdaa3b6ac9843ac195b9e4092c91be0ecbe'}


def require(ok,message):
    if not ok:raise ValueError(message)


def mode(value,storage,memdev,fetch,nub):
    require(all(type(x)is bool for x in (value,storage,memdev,fetch,nub))and(not value or all((storage,memdev,fetch,nub))),'closed factory storage/fetch/nub mode')
    return value


def profile():return dict(schema='note10-v262-owned-ram-attach-start-link-profile-v1',source_sha256=PINS,unit=UNIT,owner='iokit',factory_returns_unstarted=True,consumer='note10_attach_owned_readonly_ram_nub',consumer_invoked=False)


def enabled(current):
    producer,bindings=current['producer'],current['bindings']
    if KEY not in producer and KEY not in bindings:return False
    require(producer.get(KEY)==profile()and bindings.get(KEY)==native.digest(profile())and 'readonly_ram_nub'in producer and 'user_exception_fetch'in producer,'exact factory link opt-in binding')
    expected=current['dependencies'].get(UNIT)
    require(expected==dict(path=str(ROOT/SOURCE),source_sha256=PINS[SOURCE]),'one fixed factory dependency')
    return True


def compile_provider(current,source,private,apple):
    import phase1_owned_ram_factory_object as retained
    require(enabled(current)and all(native.file_sha(ROOT/n)==h for n,h in PINS.items()),'unchanged owned factory sources')
    tool=current['producer']['toolchain']
    fixed=retained.profile_for(tool['compiler'],tool['sdk'],source,apple,current['producer']['source_commit'],current['producer']['ci_context'])
    report=retained.compiler_recipe.main(owned_ram_factory_profile=fixed)
    require(len(report['units'])==1 and report['units'][0]['passed']is True,'one current factory compile')
    row=report['units'][0]
    row.update(factory_profile_producer_id=row['producer_id'],factory_profile_input_binding=row['input_binding'])
    native.stamp(current,row,'port')
    report.update(units=[row],current_producer_id=current['producer_id'],current_input_binding=current['input_binding'])
    (Path(private)/'current-owned-ram-factory-result.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def bind_origins(current,rows,defined,references,aliases,observation):
    require(enabled(current),'factory profile required')
    own=[row for row in rows if row['source']==UNIT]
    require(len(own)==1,'one factory current row');row=own[0]
    require(row['category']=='port'and row['source_sha256']==PINS[SOURCE]and row['passed']is True and row['producer_id']==current['producer_id']and row['input_binding']==current['input_binding'],'current factory row identity')
    def entry(fragment):
        names=[name for name,owners in defined.items()if row['object_path']in owners and fragment in name]
        require(len(names)==1,'one compiler-emitted definition: '+fragment);name=names[0]
        require(re.fullmatch(r'[_A-Za-z][_A-Za-z0-9$]{0,383}',name)and defined[name]==[row['object_path']]and name not in aliases,'unique genuine definition, no alias')
        return name
    symbol=entry('note10_create_owned_readonly_ram_nub');consumer=entry('note10_attach_owned_readonly_ram_nub')
    require(not references.get(consumer)and all(p==row['object_path']for p in references.get(symbol,[])),'consumer uncalled externally; factory edge may be internal or inlined')
    by_path={item['object_path']:item for item in rows};providers={}
    for name,owners in references.items():
        if row['object_path']not in owners or name in (symbol,consumer):continue
        target=aliases.get(name,name);paths=defined.get(target,[])
        require(len(paths)==1 and paths[0]in by_path and paths[0]!=row['object_path'],'factory import must resolve to real current provider')
        actual=by_path[paths[0]];require(actual['category']in ('native','storage')and actual['passed']is True,'no substitute factory provider')
        providers[name]=dict(symbol=target,source=actual['source'],source_sha256=actual['source_sha256'],object_sha256=actual['object_sha256'])
    require(providers,'factory genuine imports required')
    observation.update(profile=profile(),producer_id=current['producer_id'],input_binding=current['input_binding'],row={k:row[k]for k in ('source','category','source_sha256','object_path','object_sha256')},symbol=symbol,consumer_symbol=consumer,providers=providers,object_provenance_verified=True,local_factory_source_consumer='note10_attach_owned_readonly_ram_nub',local_factory_source_calls=1,external_consumer_callers=0,factory_same_object_reference_observed=bool(references.get(symbol)),consumer_invoked=False,factory_invoked=False,provider_started=False,provider_registered=False,native_activation=False,physical_ready=False)
    current['owned_ram_factory_link']=dict(observation)


def link_root(current):
    if not enabled(current):return []
    proof=current['owned_ram_factory_link']
    require(proof['object_provenance_verified']is True and proof['profile']==profile()and proof['producer_id']==current['producer_id']and proof['input_binding']==current['input_binding']and proof['external_consumer_callers']==0 and proof['consumer_invoked']is False and re.fullmatch(r'[_A-Za-z][_A-Za-z0-9$]{0,383}',proof['symbol']),'bound factory retention root')
    require(re.fullmatch(r'[_A-Za-z][_A-Za-z0-9$]{0,383}',proof['consumer_symbol'])and proof['consumer_symbol']!=proof['symbol'],'separate consumer retention root')
    return ['-Wl,-u,'+proof[name]for name in ('symbol','consumer_symbol')]


def final_symbols(text,linked,current,observation):
    require(enabled(current)and linked['link_succeeded']is True and linked['object_count']==native.expected_objects(current,storage=True)==1079,'complete current factory link')
    names=[p[-1]for line in text.splitlines()if len(p:=line.split())>=3 and re.fullmatch('[0-9a-fA-F]+',p[0])and p[-2].isupper()]
    require(observation['object_provenance_verified']is True and names.count(observation['symbol'])==names.count(observation['consumer_symbol'])==1,'factory definition retained once')
    observation.update(passed=True,final_symbols_verified=True,native_kernel_contains_factory=True,consumer_retained=True,linked_objects=1079)


def verify_profile(current,rows,state,producer,link):
    require(enabled(current),'closed factory profile');proof=state[KEY]
    own=[row for row in rows if row['source']==UNIT]
    require(len(own)==1 and proof==producer[KEY]and proof['profile']==profile()and proof['producer_id']==current['producer_id']and proof['input_binding']==current['input_binding']and proof['passed']is proof['object_provenance_verified']is proof['final_symbols_verified']is proof['native_kernel_contains_factory']is True and proof['linked_objects']==link['object_count']==1079,'retained current factory provenance')
    require(proof['row']=={k:own[0][k]for k in ('source','category','source_sha256','object_path','object_sha256')}and proof['external_consumer_callers']==0 and proof['consumer_invoked']is False and proof['consumer_retained']is True and proof['local_factory_source_consumer']=='note10_attach_owned_readonly_ram_nub'and proof['local_factory_source_calls']==1 and all(proof[k]is False for k in ('consumer_invoked','factory_invoked','provider_started','provider_registered','native_activation','physical_ready')),'unstarted exact factory row')
