"""Fresh property-symbol fixture repair and exact per-case failure progress."""
import json
import test_v242_query_admission as retained
p=retained.p
body=retained.body
base_build=retained.base_build
guard_fixture=retained.guard_fixture
COUNTS=dict(groups=1,variants=31,assertions=31)


def check_case(index,name,call,wanted):
    cause=None;actual=None
    try:actual=call()is not False
    except Exception as error:
        if not wanted and isinstance(error,(ValueError,KeyError,TypeError,StopIteration)):return
        cause=error
    if cause is None and actual is wanted:return
    message='case '+str(index)+' '+name+': '+(type(cause).__name__+': '+str(cause)if cause is not None else'expected '+str(wanted)+', actual '+str(actual))
    failure=AssertionError(message)
    failure.fixture_case=dict(planned_variants=COUNTS['variants'],planned_assertions=COUNTS['assertions'],attempted_variants=index,completed_variants=index-1,completed_assertions=index-1,
        failing_case_index=index,failing_case_name=name,original_exception_type=type(cause).__name__ if cause is not None else None,original_exception_message=str(cause)if cause is not None else None)
    if cause is not None:raise failure from cause
    raise failure


def inventory_fixture():
    build=base_build();primary=dict(object_provenance={},assembly={});selected=dict(primary=primary,outlined_input_section_join=dict(helpers=[]),outlined_bodies={},strcmp_same_body_leaf=None,owner_reuse=[],owner_reused_bodies={})
    data=dict(retained=selected,property_input_section=dict(C_anchors={}),property_C_bodies={},property_local_joins={},property_local_bodies={});raw=dict(retained=dict(primary=dict(assembly={}),outlined_assembly={}),assembly={});guarded=dict(assembly={},symbols={})
    address=0x10000
    def add(name):
        nonlocal address
        _,proof,text=body(name,['ret'],address);address+=0x100;return proof,text
    for name in p.prior.C_NAMES:
        proof,text=add(name);row=dict(frame_kind='static',frame_bytes=0,linked_address=proof['symbol']['address'],bytes=proof['symbol']['bytes'],translation_unit='/ci/work/source/arch/arm64/mm/init.c')
        primary['object_provenance'][name]=row;primary['assembly'][name]=proof;raw['retained']['primary']['assembly'][name]=text
    proof,text=add('strcmp');proof['zero_own_stack_proven']=True;selected['strcmp_same_body_leaf']=proof;raw['retained']['primary']['assembly']['strcmp']=text
    for number in p.prior.OF_HELPERS:
        name='OUTLINED_FUNCTION_'+str(number);proof,text=add(name);identity='of'+str(number);selected['outlined_input_section_join']['helpers'].append(dict(identity=identity,symbol=proof['symbol']));selected['outlined_bodies'][identity]=proof;raw['retained']['outlined_assembly'][identity]=text
    for number in p.prior.PROPERTY_HELPERS:
        name='OUTLINED_FUNCTION_'+str(number);proof,text=add(name);identity='property'+str(number);data['property_local_joins'][identity]=dict(symbol=proof['symbol'],records=[dict(name=name)]);data['property_local_bodies'][identity]=proof;raw['assembly'][identity]=text
    proof,text=add('OUTLINED_FUNCTION_15');key='owner15';guarded['assembly'][key]=text;guarded['symbols'][key]=proof['symbol'];selected['owner_reused_bodies'][key]=proof
    caller='n233_capture_cpu_node_consistency';node_address=primary['assembly'][caller]['symbol']['address'];_,node_proof,node_text=body(caller,['bl '+format(proof['symbol']['address'],'x'),'ret'],node_address,{'OUTLINED_FUNCTION_15':proof['symbol']['address']})
    node_proof['external_transfers'][0]['resolved_records'][0].update(kind='t',ordinal=99)
    primary['assembly'][caller]=node_proof;primary['object_provenance'][caller]['bytes']=8;raw['retained']['primary']['assembly'][caller]=node_text
    selected['owner_reuse']=[dict(call_site=node_address,translation_unit='/ci/work/source/arch/arm64/mm/init.c',caller='n233_capture_cpu_node_consistency',guarded_body_key=key,zero_own_stack_inferred_from_SU=False,helper_static_frame_is_not_own_stack_proof=True,
        guarded_raw_sha256=p.sha((json.dumps(guarded,indent=2,sort_keys=True)+'\n').encode()),nm_record=dict(name='OUTLINED_FUNCTION_15',kind='t',address=proof['symbol']['address'],bytes=proof['symbol']['bytes'],ordinal=99),owner_object='arch/arm64/mm/init.o')]
    build['of_call_evidence']=data;return build,raw,guarded


def run():
    cases=[]
    def accepted(name,call):cases.append((name,call,True))
    def rejected(name,call):cases.append((name,call,False))
    accepted('current35 includes distinct owner and OF names',lambda:len(p.query_inventory(*inventory_fixture()))==35)
    def wrong_target():
        build,raw,guarded=inventory_fixture();build['source_head']='0'*40;return p.query_inventory(build,raw,guarded)
    rejected('old or different target cannot be normalized',wrong_target)
    def caller_zero():
        build,raw,guarded=inventory_fixture();build['guarded_query_target']['compiled_node_callers']=0;return p.query_inventory(build,raw,guarded)
    rejected('current compiled caller must be one',caller_zero)
    def missing_owner():
        build,raw,guarded=inventory_fixture();build['of_call_evidence']['retained']['owner_reuse']=[];return p.query_inventory(build,raw,guarded)
    rejected('35th owner body cannot be omitted',missing_owner)
    def wrong_reuse():
        build,raw,guarded=inventory_fixture();build['of_call_evidence']['retained']['owner_reuse'][0]['nm_record']['address']+=4;return p.query_inventory(build,raw,guarded)
    rejected('same-named owner extent must match reused body',wrong_reuse)
    def graph(recursive=False):
        nodes={};edges={};keys=[]
        for i in range(35):
            start=0x40000+i*0x100;last=i==34;ops=['ret']if last else['stp x29, x30, [sp, #-16]!','bl '+format(start+0x100,'x'),'ldp x29, x30, [sp], #16','ret']
            rows,proof,_=body('synthetic'+str(i),ops,start);key=(start,4*len(rows));keys.append(key);nodes[key]=dict(name='synthetic'+str(i),kind='C',frame=0 if last else 16,rows=rows,proof=proof)
        for i,key in enumerate(keys):edges[key]={}if i==34 else{key[0]+4:keys[i+1]}
        if recursive:edges[keys[34]]={keys[34][0]:keys[0]}
        return p.analyze_query(nodes,edges,keys[0],None,None)
    accepted('bounded35 acyclic analysis wrapper closes all nodes',lambda:len(graph())==35)
    rejected('new35 wrapper rejects recursion',lambda:graph(True))
    def coverage(size):
        k=(0x30000,16);rows,proof,_=body('owner:OUTLINED_FUNCTION_15',['ldp x20, x19, [sp, #64]','ldp x22, x21, [sp, #48]','ldp x24, x23, [sp, #32]','ret'],k[0]);node=dict(name='owner:OUTLINED_FUNCTION_15',kind='helper',frame=0,rows=rows,proof=proof);summary=p.prior.frame_body(node,{}, {},{k:node})
        ops=['sub sp, sp, #'+str(size),'bl 30000','add sp, sp, #'+str(size),'ret'];rows,proof,_=body('node',ops,0x20000);root=(0x20000,16);return p.prior.frame_body(dict(name='node',kind='C',frame=size,rows=rows,proof=proof),{0x20004:k},{k:summary},{root:dict(name='node'),k:node})
    accepted('new owner paired loads fit actual80-byte caller slots',lambda:coverage(80)['observed_peak_bytes']==80)
    rejected('SU0 never permits owner read beyond live caller slots',lambda:coverage(64))
    def certificate(change=None):return p.guarded_certificate(*guard_fixture(change),128)
    accepted('complete guarded predicate is conditional and scheduler remains unbounded',lambda:certificate()['outer_release_scheduler_reachable']is True and certificate()['whole_guarded_caller_stack_proven']is False)
    def replace(name,before,after,occurrence=0):
        def change(ops):
            index=[i for i,value in enumerate(ops[name])if value==before][occurrence];ops[name][index]=after
        return change
    rejected('count0 admission cannot become count-nonzero',lambda:certificate(replace(p.GUARD,'cbz w8, $pre_room','cbnz w8, $pre_room')))
    rejected('PID1 admission cannot be removed',lambda:certificate(replace(p.GUARD,'ldr w8, [x22, #1488]','ldr w8, [x22, #1492]')))
    rejected('IRQ bit gate must be exact',lambda:certificate(replace(p.GUARD,'tbnz w8, #7, $failed','tbnz w8, #6, $failed')))
    rejected('held count before capture must equal one',lambda:certificate(replace(p.GUARD,'cmp w8, #0x1','cmp w8, #0x2',1)))
    rejected('capture decrement must bypass scheduler on nonzero',lambda:certificate(replace(p.CAPTURE,'b.ne $done','b.eq $done')))
    rejected('capture must own a matched decrement',lambda:certificate(replace(p.CAPTURE,'subs w10, w10, #0x1','subs w10, w10, #0x2')))
    rejected('room cap is8192 not a fabricated answer',lambda:certificate(replace(p.ROOM,'mov w3, #0x2000','mov w3, #0x2400')))
    rejected('room guard remains4096',lambda:certificate(replace(p.ROOM,'mov w4, #0x1000','mov w4, #0x800')))
    rejected('room SP is scalar argument2 only',lambda:certificate(replace(p.ROOM,'mov x2, sp','mov x3, sp')))
    rejected('guard cannot skip own SP deallocation',lambda:certificate(replace(p.GUARD,'ldp x29, x30, [sp], #64','ldp x29, x30, [sp], #32')))
    rejected('capture status gate must remain',lambda:certificate(replace(p.GUARD,'ldr w8, [x21, #24]','ldr w8, [x21, #28]')))
    rejected('node mismatch must set negative error',lambda:certificate(replace(p.GUARD,'mov w0, #0xffffffb9','mov w0, wzr')))
    rejected('outer release decrement cannot change width',lambda:certificate(replace(p.GUARD,'subs w8, w8, #0x1','subs w8, w8, #0x2')))
    rejected('release count error selection cannot invert',lambda:certificate(replace(p.GUARD,'csel w22, w0, w9, eq','csel w22, w0, w9, ne')))
    rejected('CPU helper is a fixed source-backed no-SP shape',lambda:certificate(replace('OUTLINED_FUNCTION_0','mrs x8, tpidr_el1','mrs x8, mpidr_el1')))
    rejected('post-room false result must block success',lambda:certificate(replace(p.GUARD,'cbz w0, $failed','nop',1)))
    def incompatible():
        rows,proof,text=body('own',['sub sp, sp, #16','cbz x0, $no_fp','mov x29, sp','b $join','no_fp:','nop','join:','add sp, sp, #16','ret'],0x50000)
        return p.local_frame('own',rows,{},16)
    rejected('new own-frame reader rejects incompatible FP merge',incompatible)
    rejected('post-room must branch on the Boolean return register',lambda:certificate(replace(p.GUARD,'cbz w0, $failed','cbz w1, $failed',1)))
    def wrong_ABI():
        build,guarded=guard_fixture();build['guarded_query_target']['record_bytes']=48;return p.guarded_certificate(build,guarded,128)
    rejected('receipt offset semantics require actual56-byte type',wrong_ABI)
    def without_source():
        build,guarded=guard_fixture();build['source_sha256']['note10/device_test/v240_guarded_query.c']='0'*64;return p.guarded_certificate(build,guarded,128)
    rejected('compiled source hash cannot be replaced',without_source)
    def diagnostic():
        def missing_symbol():raise KeyError('symbol')
        try:check_case(4,'synthetic missing property symbol',missing_symbol,True)
        except AssertionError as error:
            info=error.fixture_case
            return info==dict(planned_variants=31,planned_assertions=31,attempted_variants=4,completed_variants=3,completed_assertions=3,
                failing_case_index=4,failing_case_name='synthetic missing property symbol',original_exception_type='KeyError',original_exception_message="'symbol'")and isinstance(error.__cause__,KeyError)and 'case 4'in str(error)
        return False
    accepted('unexpected positive failure retains case progress and original cause',diagnostic)
    progress=dict(planned_variants=COUNTS['variants'],planned_assertions=COUNTS['assertions'],attempted_variants=0,completed_variants=0,completed_assertions=0,
        failing_case_index=None,failing_case_name=None,original_exception_type=None,original_exception_message=None)
    try:
        p.require(len(cases)==COUNTS['variants'],'exact fresh243 registry count')
        for index,(name,call,wanted)in enumerate(cases,1):
            progress.update(attempted_variants=index,failing_case_index=index,failing_case_name=name)
            check_case(index,name,call,wanted)
            progress.update(completed_variants=index,completed_assertions=index,failing_case_index=None,failing_case_name=None)
    except BaseException as error:
        progress.update(original_exception_type=type(error).__name__,original_exception_message=str(error))
        progress.update(getattr(error,'fixture_case',{}));error.fixture_progress=dict(progress);raise
    return dict(COUNTS,**progress)
