"""Conditional proof of captured241 query and guard predicates; never runtime permission."""
from collections import deque
import re
import json
import v239_query_admission as prior
require,sha=prior.require,prior.sha
SCHEMA='note10-v242-current-query-admission-proof-v1'
TARGET_HEAD='e07129664f1475b9576c45aa0ec44511ea6e9f53'
TARGET_RUN=43413072923
C_SOURCE_HASHES={'v240_guarded_query.c': '3d38df8db966827e2495701d803b15459dc2619e2c732687c2123e7ccf8eea88', 'v240_guarded_query.h': 'fd0f973e71ead7b4a62a8376237c27472c467416640ce20029f55dea09cce7f9', 'v231_cpu_observation.c': '8dee94d48b101b57ab27d1a68eaec085712170bded866f4ffd5e1257584d90c4', 'v231_cpu_observation.h': '407bcc677c59c1b6f8d7b4037df8a0bbdc876d77a5326775fabe2ab58e9389a1', 'v233_cpu_node_consistency.c': 'f539e615e24356867f8def9e7371f4c98e79e1948b698228745dc00986e07c2c', 'v233_cpu_node_consistency.h': '4a86e4308f443cf19e7c2f2f5478dd06de0af104116adc5aa866d021af2b06e4', 'native_source_stream.c': '0a25696f8d79d067868e1d119cfa4754e43747ae13890ab8658a12a3c29751d5', 'native_source_stream.h': '2207009c47adc326538e007702c2f3d1fd8248f0f2b3ac9c81832c4e24f07ebd'}
GUARD='n240_observe_current_cpu'
CAPTURE='n231_capture_cpu_observation'
ROOM='n240_room'
STACK_ROOM='n226_stack_room'
CONTROL=(GUARD,CAPTURE,ROOM,STACK_ROOM,'n240_clear_receipt','n240_invalidate_observations','n231_clear_observation')
SCHEDULE=prior.SCHEDULE


def target_gate(build):
    require(build['passed']is True and build['version']=='v241'and build['source_head']==TARGET_HEAD and build['run_id']==TARGET_RUN,'fixed authenticated241 target required; never relabel it242')
    require(all(build['effective_profile'].get(k,'n')==v for k,v in prior.CONFIG.items()),'actual current preemption/static OF config required')
    require(all(build['effective_profile'].get(k)=='y'for k in ('VMAP_STACK','THREAD_INFO_IN_TASK')),'actual VMAP/task-stack helper config required')
    require(build['guarded_query_target']['compiled_node_callers']==build['guarded_query_target']['compiled_capture_callers']==build['node_runtime_callers']==1 and
        build['guarded_query_target']['runtime_observed']is build['node_runtime_observed']is False,'current compiled caller1 required; legacy OF limit0 is not a premise')
    require({name:build['source_sha256']['note10/device_test/'+name]for name in C_SOURCE_HASHES}==C_SOURCE_HASHES,'exact compiled guard/provider sources required')
    require(build['guarded_query_target']['record_bytes']==56 and build['guarded_query_target']['pool_offset']==43608 and build['guarded_query_target']['new_pool_bytes']==0 and
        build['guarded_query_target']['ABS']==dict(n240_size_query=56,n240_align_query=8,n240_pre_room_offset=40),'actual exact56 receipt alias/type required')


def query_inventory(build,raw,guarded):
    target_gate(build);data=build['of_call_evidence'];selected=data['retained'];primary=selected['primary'];nodes={}
    C={**primary['object_provenance'],**data['property_input_section']['C_anchors']}
    require(set(C)==set(prior.C_NAMES),'exact current seventeen C functions required')
    def add(name,kind,proof,text,frame):
        symbol=proof['symbol'];key=(symbol['address'],symbol['bytes'])
        require(key not in nodes and type(frame)is int and 0<=frame<=8192,'one bounded static frame per actual extent required')
        nodes[key]=dict(name=name,kind=kind,frame=frame,proof=proof,rows=prior.parse_body(text,proof))
    for name,row in C.items():
        require(row['frame_kind']=='static','current dynamic C frame is unsupported')
        proof=primary['assembly'][name]if name in primary['assembly']else data['property_C_bodies'][name]
        text=raw['retained']['primary']['assembly'][name]if name in primary['assembly']else raw['assembly'][name]
        require(proof['symbol']['address']==row['linked_address']and proof['symbol']['bytes']==row['bytes'],'current C body/static extent join required')
        add(name,'C',proof,text,row['frame_bytes'])
    leaf=selected['strcmp_same_body_leaf'];require(leaf['zero_own_stack_proven']is True,'same actual strcmp body proof required')
    add('strcmp','asm',leaf,raw['retained']['primary']['assembly']['strcmp'],0)
    helpers=selected['outlined_input_section_join']['helpers']
    require({v['symbol']['symbol']for v in helpers}=={'OUTLINED_FUNCTION_'+str(i)for i in prior.OF_HELPERS}and len(helpers)==13,'exact current OF13 identities required')
    for row in helpers:add('of:'+row['symbol']['symbol'],'helper',selected['outlined_bodies'][row['identity']],raw['retained']['outlined_assembly'][row['identity']],0)
    local=data['property_local_joins'];require({v['name']for row in local.values()for v in row['records']}=={'OUTLINED_FUNCTION_'+str(i)for i in prior.PROPERTY_HELPERS}and len(local)==3,'exact current property3 identities required')
    for key,row in local.items():add('property:'+row['symbol']['symbol'],'helper',data['property_local_bodies'][key],raw['assembly'][key],0)
    reuse=selected['owner_reuse'];require(len(reuse)==1 and reuse[0]['caller']=='n233_capture_cpu_node_consistency','one exact current node-owner reuse required')
    row=reuse[0];key=row['guarded_body_key'];proof=selected['owner_reused_bodies'][key];symbol=proof['symbol'];record=row['nm_record']
    require(row['zero_own_stack_inferred_from_SU']is False and row['helper_static_frame_is_not_own_stack_proof']is True and
        row['guarded_raw_sha256']==sha((json.dumps(guarded,indent=2,sort_keys=True)+'\n').encode())and
        symbol==guarded['symbols'][key]and (record['address'],record['bytes'])==(symbol['address'],symbol['bytes'])and
        record['kind']=='t'and record['name']=='OUTLINED_FUNCTION_15'and row['owner_object']=='arch/arm64/mm/init.o',
        'exact current same-owner/ordinal/guarded extent reuse required')
    caller=primary['assembly'][row['caller']];matched=[edge for edge in caller['external_transfers']if edge['address']==row['call_site']and edge['mnemonic']=='bl'and edge['target']==record['address']]
    require(len(matched)==1 and any(all(v.get(k)==record[k]for k in ('name','kind','address','bytes','ordinal'))and v['offset']==0 for v in matched[0]['resolved_records']),
        'current node call site must retain exact owner ordinal/entry identity')
    require(row['translation_unit']==build['guarded_query_target']['owner_TU']['translation_unit']==primary['object_provenance'][row['caller']]['translation_unit'],
        'same current owner TU required at query/guard frontier')
    add('owner:'+record['name'],'helper',proof,guarded['assembly'][key],0)
    require(len(nodes)==35,'fixed35 current query extents required');return nodes


def analyze_query(nodes,edges,root,prune_key,prune_branch):
    require(len(nodes)==35 and root in nodes,'fixed35 query graph only');summaries={};visiting=set()
    def visit(key):
        if key in summaries:return
        require(key not in visiting,'recursive selected query is unsupported');visiting.add(key)
        for child in edges[key].values():
            if child!=SCHEDULE:visit(child)
        try:summaries[key]=prior.frame_body(nodes[key],edges[key],summaries,nodes,prune_branch if key==prune_key else None)
        except ValueError as error:raise ValueError(nodes[key]['name']+': '+str(error))from error
        visiting.remove(key)
    visit(root);require(set(summaries)==set(nodes),'unreachable or unproved fixed current body');return summaries


def normalized(rows):return [prior.normalized(op+' '+args)for _,op,args in rows]


def sequence(rows,wanted):
    text=normalized(rows);wanted=[prior.normalized(v)for v in wanted]
    found=[i for i in range(len(rows)-len(wanted)+1)if text[i:i+len(wanted)]==wanted]
    require(len(found)==1,'one exact compiled predicate sequence required: '+wanted[0]);return found[0]


def call_edges(proof):
    result={}
    for edge in proof['external_transfers']:
        require(edge['mnemonic']=='bl'and edge['resolved_records']and all(v['offset']==0 for v in edge['resolved_records']),'fixed guard uses only bound direct calls')
        require(len({(v['address'],v['bytes'])for v in edge['resolved_records']})==1,'unambiguous guard callee extent required')
        result[edge['address']]=dict(names={v['name']for v in edge['resolved_records']},target=edge['target'])
    return result


def call_index(rows,edges,name):
    found=[i for i,(address,op,args)in enumerate(rows)if address in edges and name in edges[address]['names']and op=='bl'and prior.branch_target(args)==edges[address]['target']]
    require(len(found)==1,'one exact guard call required: '+name);return found[0]


def cfg(rows,edges,prune=None):return {i:prior.successors(rows,i,edges,prune)for i in range(len(rows))}


def reachable(graph,start,avoid=None):
    seen=set();pending=[start]
    while pending:
        i=pending.pop()
        if i==avoid or i in seen:continue
        require(i in graph,'CFG target outside fixed body');seen.add(i);pending.extend(graph[i])
    return seen


def dominates(graph,node,target):
    require(target in reachable(graph,0)and target not in reachable(graph,0,node),'compiled admission does not dominate protected call')


def branch_gate(rows,graph,index,protected,success_taken):
    _,op,args=rows[index];require(op in ('cbz','cbnz','tbz','tbnz')or op.startswith('b.'),'one predicate branch required')
    addresses={row[0]:i for i,row in enumerate(rows)};taken=addresses.get(prior.branch_target(args));fall=index+1
    require(taken is not None and fall in graph,'both predicate successors must be internal')
    good,bad=(taken,fall)if success_taken else(fall,taken)
    dominates(graph,index,protected)
    require(protected in reachable(graph,good)and protected not in reachable(graph,bad),'failed admission can reach protected call')


def local_frame(name,rows,edges,frame):
    """Own SP only: opaque calls return by normal ABI; their peaks stay unknown."""
    states={0:(0,None)};pending=deque([0]);calls={};samples=[];peak=0;returns=0;visits=0
    while pending:
        index=pending.popleft();visits+=1;require(visits<=len(rows)*32,'bounded fixed own-frame CFG convergence')
        sp,fp=states[index];address,op,args=rows[index];access=prior.memory(op,args)
        math=re.fullmatch(r'(sp|x29),\s*sp,\s*#(-?(?:0x[0-9a-f]+|\d+))',args)if op in ('add','sub')else None
        if access:
            if access['pre']:sp+=access['offset'];offset=0
            else:offset=access['offset']
            base=sp if access['base']=='sp'else fp;require(base is not None and sp<=base+offset<base+offset+access['width']<=0,'fixed own frame access outside live allocation')
            if access['load']and'x29'in access['regs']:fp=None
            sp+=access['post']
        elif math:
            value=prior.immediate(math[2])*(1 if op=='add'else-1)
            if math[1]=='sp':sp+=value
            else:fp=sp+value
        elif op=='mov'and prior.normalized(args)=='x29,sp':fp=sp
        elif name==ROOM and op=='mov'and prior.normalized(args)=='x2,sp':samples.append(dict(address=address,SP_offset=sp,scalar_SP_argument=2))
        else:require(not re.search(r'\b(?:sp|wsp|x29|fp)\b',args),'unsupported own SP/FP effect')
        require(-frame<=sp<=0,'own allocation exceeds actual static SU');peak=max(peak,-sp)
        if address in edges:
            require(op=='bl','only ordinary direct calls in fixed guard bodies');calls[address]=sp
        if op=='ret':require(sp==0,'unbalanced guard return');returns+=1
        for nxt in prior.successors(rows,index,edges):
            state=(sp,fp)
            if nxt in states:require(states[nxt]==state,'incompatible own SP/FP merge')
            else:states[nxt]=state;pending.append(nxt)
    require(returns and peak==frame,'actual own peak must equal measured static frame')
    return dict(own_peak_bytes=peak,call_SP_offsets=calls,scalar_samples=samples,normal_ABI_call_return_assumed=True,callee_peaks_included=False)


def count_update(rows,base,temp,operation):
    text=normalized(rows);load=prior.normalized('ldr '+temp+', ['+base+', #16]');arithmetic=prior.normalized(operation+' '+temp+', '+temp+', #0x1');store=prior.normalized('str '+temp+', ['+base+', #16]')
    found=[]
    for i,value in enumerate(text):
        if value!=load:continue
        for j in range(i+1,min(i+5,len(rows)-1)):
            if text[j]==arithmetic and text[j+1]==store:
                between=rows[i+1:j]
                require(all(not(op in ('bl','b','ret','cbz','cbnz','tbz','tbnz')or op.startswith('b.'))and args.split(',',1)[0].strip()not in(temp,'x'+temp[1:],base)for _,op,args in between),'count value/base changed before update')
                found.append((i,j,j+1))
    require(len(found)==1,'one exact inline count update required');return found[0]


def balanced_region(rows,graph,increment,decrement):
    returns={i for i,(_,op,_)in enumerate(rows)if op=='ret'}
    require(not(returns&reachable(graph,increment,decrement)),'owned increment can return without its decrement')
    require(all(increment not in reachable(graph,nxt)for nxt in graph[increment]),'count increment can be repeated')


def capture_predicate(rows,edges):
    graph=cfg(rows,edges);increment=count_update(rows,'x8','w9','add');decrement=count_update(rows,'x8','w10','subs')
    sequence(rows,['mrs x8, sp_el0','ldr w9, [x8, #16]'])
    require(decrement[1]==decrement[0]+1 and rows[decrement[2]+1][1]=='b.ne','one capture nonzero decrement bypass required')
    branch=decrement[2]+1;pruned=cfg(rows,edges,rows[branch][0]);schedule=call_index(rows,edges,SCHEDULE)
    require(schedule not in reachable(pruned,0),'capture scheduler reachable despite held outer count')
    balanced_region(rows,graph,increment[2],decrement[2])
    writes=[i for i,v in enumerate(normalized(rows))if re.fullmatch(r'(?:str|stur)[wx][0-9]+,\[x8,#(?:16|0x10)\]',v)]
    require(writes==[increment[2],decrement[2]],'unlisted capture count write')
    require(increment[2]<decrement[0]and rows[branch][1]=='b.ne','ordered nested capture hold required')
    return dict(increment=rows[increment[2]][0],decrement=rows[decrement[2]][0],pruned_nonzero_branch=rows[branch][0],scheduler_call=rows[schedule][0],incoming_outer_count_min=1,nested_peak_count_min=2,counter_effect=0,scheduler_unreachable_only_under_outer_premise=True)


def room_certificate(rows,edges,own):
    wanted=['stp x29, x30, [sp, #-16]!','mov x29, sp','mrs x8, sp_el0','mov x2, sp','ldr x8, [x8, #32]',
        'mov w3, #0x2000','mov w4, #0x1000','add x1, x8, #0x4, lsl #12','add x8, x8, #0x8',
        'cmp x2, x1','sub x9, x2, x8','ccmp x2, x8, #0x0, ls','csel x9, xzr, x9, cc','str x9, [x0]','mov x0, x8']
    require(sequence(rows,wanted)==0 and len(rows)==18,'exact VMAP-aware scalar room-call shape required')
    call=call_index(rows,edges,STACK_ROOM);require(call==15 and normalized(rows)[16:]==[prior.normalized(v)for v in('ldp x29, x30, [sp], #16','ret')],'room must return straight after stack guard')
    require(own['own_peak_bytes']==16 and len(own['scalar_samples'])==1,'one actual SP sample inside room frame required')
    return dict(cap=8192,guard=4096,scalar_SP_sample=own['scalar_samples'][0],call=rows[call][0],frame_bytes=16,task_floor_top_source_contract_assumed=True,SP_bitmask_inference=False,runtime_headroom_observed=False)


def guarded_certificate(build,guarded,query_bound):
    target_gate(build);target=build['guarded_query_target'];proofs=build['guarded_query_graph']['named_bodies'];bodies={};own={};edges={}
    for name in CONTROL:
        proof=proofs[name];rows=prior.parse_body(guarded['assembly'][name],proof);body_edges=call_edges(proof);bodies[name]=rows;edges[name]=body_edges
        require(target['frames'][name]['kind']=='static','actual separate static guard/capture frames required')
        own[name]=local_frame(name,rows,body_edges,target['frames'][name]['bytes'])
    room=room_certificate(bodies[ROOM],edges[ROOM],own[ROOM]);capture=capture_predicate(bodies[CAPTURE],edges[CAPTURE])
    rows=bodies[GUARD];calls=edges[GUARD];graph=cfg(rows,calls)
    increment=count_update(rows,'x22','w8','add');decrement=count_update(rows,'x22','w8','subs')
    sequence(rows,['mrs x22, sp_el0','ldr w8, [x22, #16]','str w8, [x19, #24]'])
    cap_call=call_index(rows,calls,CAPTURE);query_call=call_index(rows,calls,'n233_capture_cpu_node_consistency')
    admission=sequence(rows,['ldr w8, [x19, #24]'])+1
    require(rows[admission][1]=='cbz'and prior.normalized(rows[admission][2].split(',')[0])=='w8','count0 entry branch required')
    branch_gate(rows,graph,admission,increment[2],True)
    pid=sequence(rows,['ldr w8, [x22, #1488]','cmp w8, #0x1'])+2
    process=sequence(rows,['ldr w8, [x22, #16]','tst w8, #0x1fff00'])+2
    irq=sequence(rows,['mrs x8, daif'])+1
    require(rows[pid][1]==rows[process][1]=='b.ne'and rows[irq][1]=='tbnz'and prior.normalized(rows[irq][2].rsplit(',',1)[0])=='w8,#7','PID1/process/IRQ entry admission shape required')
    for gate in(pid,process,irq):branch_gate(rows,graph,gate,increment[2],False)
    initial=sequence(rows,['ldr w8, [x22, #16]','cmp w8, #0x1'])+2
    require(rows[initial][1]=='b.ne','held count1 before capture required');branch_gate(rows,graph,initial,cap_call,False)
    before_query=sequence(rows,['str w8, [x19, #28]'])+1
    require(rows[before_query][1]=='cbnz'and prior.normalized(rows[before_query][2].split(',')[0])=='w0','capture failure must block node call');branch_gate(rows,graph,before_query,query_call,False)
    held=before_query+1
    require(normalized(rows)[held]==prior.normalized('cmp w8, #0x1')and rows[held+1][1]=='b.ne','count1 capture-return predicate required');branch_gate(rows,graph,held+1,query_call,False)
    status=sequence(rows,['ldr w8, [x21, #24]','cmp w8, #0x1'])+2
    require(rows[status][1]=='b.ne','capture valid status gate required');branch_gate(rows,graph,status,query_call,False)
    cpu=sequence(rows,['ldr w8, [x21, #16]','ldr w9, [x19, #12]','cmp w8, w9'])+3
    require(rows[cpu][1]=='b.ne','matching held/sample CPU gate required');branch_gate(rows,graph,cpu,query_call,False)
    get_cpu=sequence(rows,['cmp w8, #0x7','str w8, [x19, #12]'])+2
    require(rows[get_cpu][1]=='b.hi','CPU<8 admission required');branch_gate(rows,graph,get_cpu,cap_call,False)
    release=sequence(rows,['str w8, [x19, #20]'])-1
    node_status=sequence(rows,['ldr w8, [x20, #28]','cmp w8, #0x1'])+2
    node_cpu=sequence(rows,['ldr w8, [x20, #16]','ldr w9, [x21, #16]','cmp w8, w9'])+3
    failure=next((i for i,row in enumerate(rows)if row[0]==prior.branch_target(rows[node_status][2])),None)
    require(failure is not None and normalized(rows)[failure]==prior.normalized('mov w0, #0xffffffb9'),'node mismatch must set exact negative error')
    query_error=query_call+1
    require(rows[query_error][1]=='cbnz'and prior.normalized(rows[query_error][2].split(',')[0])=='w0'and prior.branch_target(rows[query_error][2])==rows[release][0],'node failure must preserve error into common release')
    require(all(rows[i][1]=='b.ne'and prior.branch_target(rows[i][2])==rows[failure][0]for i in(node_status,node_cpu)),'node status/CPU mismatch must select negative error')
    require(normalized(rows)[failure-2]==prior.normalized('mov w0, wzr')and rows[failure-1][1]=='b'and prior.branch_target(rows[failure-1][2])==rows[release][0],'only valid node branch selects zero error')
    require(failure+1==release,'negative node error must fall into common release')
    release_count=sequence(rows,['ldr w9, [x22, #16]','cmp w9, #0x1','str w9, [x19, #32]'])+3
    release_failure=decrement[0]-1
    require(normalized(rows)[release_failure]==prior.normalized('mov w0, #0xffffffb9')and rows[release_count][1]=='b.ne'and prior.branch_target(rows[release_count][2])==rows[release_failure][0],'release count mismatch must select error before one owned decrement')
    require(normalized(rows)[release_count+1:release_count+3]==[prior.normalized(v)for v in('ldr w9, [x19, #12]','cmp w8, w9')]and rows[release_count+3][1]=='b.eq'and prior.branch_target(rows[release_count+3][2])==rows[decrement[0]][0]and release_count+4==release_failure,'held CPU match/error release edge required')
    balanced_region(rows,graph,increment[2],decrement[2]);dominates(graph,increment[2],query_call)
    writes=[i for i,v in enumerate(normalized(rows))if re.fullmatch(r'(?:str|stur)[wx][0-9]+,\[x22,#(?:16|0x10)\]',v)]
    require(writes==[increment[2],decrement[2]],'one owned guard increment/decrement only')
    require(rows[decrement[2]+1][1]=='b.ne','outer release zero/nonzero scheduling predicate required')
    scheduler=call_index(rows,calls,SCHEDULE);require(scheduler in reachable(graph,increment[2]),'outer release scheduler edge must remain reachable/unbounded')
    room_calls=[i for i,(address,_,_)in enumerate(rows)if address in calls and ROOM in calls[address]['names']]
    require(len(room_calls)==2 and room_calls[0]<increment[0]<cap_call<query_call<decrement[0]<room_calls[1],'pre-room/capture/query/release/post-room order required')
    for i in room_calls:
        require(rows[i+1][1]=='cbz'and prior.normalized(rows[i+1][2].split(',')[0])=='w0','room Boolean return must block success');
    require(all(normalized(rows)[index-1]==prior.normalized('add x0, x19, #'+offset)for index,offset in zip(room_calls,('0x28','0x30'))),'pre/post headroom outputs must use exact receipt slots40/48')
    dominates(graph,room_calls[0],increment[2])
    branch_gate(rows,graph,room_calls[0]+1,increment[2],False)
    final=sequence(rows,['cmp w8, #0x0','str w8, [x19, #36]','csel w22, w0, w9, eq'])+3
    require(rows[final][1]=='cbnz'and prior.normalized(rows[final][2].split(',')[0])=='w22','release count/error must block success')
    success=sequence(rows,['mov w8, #0x1','mov w22, wzr','stur x8, [x19, #4]'])
    branch_gate(rows,graph,final,success,False);branch_gate(rows,graph,room_calls[1]+1,success,False)
    require(own[GUARD]['own_peak_bytes']==64 and own[GUARD]['call_SP_offsets'][rows[query_call][0]]==-64 and
        own[GUARD]['call_SP_offsets'][rows[room_calls[0]][0]]==-64,'query and pre-room calls must share stable live guard frame')
    helper_calls=[(address,edge)for address,edge in calls.items()if 'OUTLINED_FUNCTION_0'in edge['names']]
    require(len(helper_calls)==2,'same exact CPU helper at enter/release required')
    for address,edge in helper_calls:
        matches=[key for key,symbol in guarded['symbols'].items()if symbol['address']==edge['target']and symbol['bytes']==12]
        require(len(matches)==1,'one bound CPU helper extent required');key=matches[0]
        proof=build['guarded_query_graph']['direct_owner_local_bodies'][key];helper_rows=prior.parse_body(guarded['assembly'][key],proof)
        require(normalized(helper_rows)==[prior.normalized(v)for v in('mrs x8, tpidr_el1','ldr w8, [x8, x23]','ret')],'fixed CPU helper scalar/no-SP contract required')
    clear=normalized(bodies['n240_invalidate_observations'])
    require(clear.count(prior.normalized('cmp x8, #0x20'))==2 and prior.normalized('stp wzr, w8, [x2, #4]')in clear,'both-record32 clearing and receipt-invalid store required')
    require(query_bound<=8192 and own[CAPTURE]['own_peak_bytes']<=8192 and all(own[n]['own_peak_bytes']==0 for n in('n240_clear_receipt','n240_invalidate_observations','n231_clear_observation',STACK_ROOM)),
        'selected pre-release byte budget exceeds existing cap')
    return dict(compiled_node_callers=1,compiled_outer_span_predicate=True,normal_context_and_valid_argument_assumptions=True,error_value_propagation_source_and_fixed_register_contract=True,
        query_call=rows[query_call][0],query_call_SP_offset=-64,pre_room=room,capture=capture,
        owned_increment=rows[increment[2]][0],owned_decrement=rows[decrement[2]][0],outer_release_scheduler_call=rows[scheduler][0],
        outer_release_scheduler_reachable=True,outer_release_scheduler_stack_bound=None,atomic_duration_measured=False,
        own_frames=own,conditional_admission_cut='successful pre-room sample to before outer release only',
        conditional_query_bytes=query_bound,capture_static_bytes=own[CAPTURE]['own_peak_bytes'],cap=8192,guard=4096,
        caller_frames_already_live_at_sample=True,whole_guarded_caller_stack_proven=False,CPU_value_semantics_source_assumed=True,runtime_headroom_observed=False)


def prove(build,raw,guarded,sources):
    nodes=query_inventory(build,raw,guarded);external=prior.external_targets(nodes);prior.slot_signatures(nodes);predicate=prior.preemption_predicate(nodes,external,sources)
    root=next(key for key,node in nodes.items()if node['name']=='n233_capture_cpu_node_consistency')
    summaries=analyze_query(nodes,external,root,predicate['unlock_key'],predicate['pruned_branch'])
    require(summaries[root]['counter_effect']==summaries[root]['required_lock_level']==0,'current query must preserve incoming outer count1')
    bound=sum(node['frame']for node in nodes.values()if node['kind']=='C');require(0<bound<=8192,'fresh conditional query bound exceeds cap')
    guard=guarded_certificate(build,guarded,bound)
    return dict(schema=SCHEMA,passed=True,target_version='v241',target_source_head=TARGET_HEAD,target_CI_run=TARGET_RUN,
        conditional_node_query_bound_bytes=bound,query_body_count=35,bound_kind='current fixed acyclic C-frame conservative sum under stated outer count1/normal ABI premises',
        query_functions={nodes[key]['name']:dict(frame_bytes=node['frame_bytes'],observed_peak_bytes=node['observed_peak_bytes'],counter_effect=node['counter_effect'],required_lock_level=node['required_lock_level'],borrowed_intervals=[list(v)for v in node['borrowed_intervals']],calls=node['calls'])for key,node in summaries.items()},
        preemption_invariant={**{k:v for k,v in predicate.items()if k not in('unlock_key','guard_is_hypothetical_not_compiled')},'compiled_guard_supplies_premise_under_normal_ABI':True,'runtime_guard_observed':False},compiled_guard_certificate=guard,source_sha256=prior.SOURCE_HASHES,kernel_source_sha256=C_SOURCE_HASHES,
        current_compiled_node_callers=1,legacy_OF_runtime_callers_not_used_as_premise=True,normal_ABI_and_valid_argument_assumptions=True,
        runtime_hook_allowed=False,runtime_admission=False,runtime_observed=False,physical_ready=False,hardware_authorized=False,
        whole_guarded_caller_stack_proven=False,whole_kernel_scheduler_stack_bound=False,atomic_interval_duration_measured=False,IRQ_NMI_bound_proven=False)
