"""New-only synthetic local-frame/CFG/slot/conditional-preemption proof cases."""
from copy import deepcopy
import v239_query_admission as p

COUNTS=dict(groups=1,variants=38,assertions=38)


def run():
    cases=[]
    def accepted(name,call):cases.append((name,call,True))
    def rejected(name,call):cases.append((name,call,False))
    def body(name,ops,start=0x1000,frame=0,kind='C'):
        rows=[]
        for i,text in enumerate(ops):
            parts=text.split(None,1);rows.append((start+4*i,parts[0],parts[1]if len(parts)==2 else''))
        raw=format(start,'016x')+' <'+name+'>:\n'+''.join(' '+format(address,'x')+': d503201f '+op+(' '+args if args else'')+'\n'for address,op,args in rows)
        proof=dict(symbol=dict(symbol=name,address=start,bytes=len(ops)*4,aliases=[name]),disassembly_sha256=p.sha(raw.encode()),unknown_control_transfers=[],external_transfers=[])
        return (start,len(ops)*4),dict(name=name,kind=kind,frame=frame,rows=rows,proof=proof),raw
    ops=['stp x29, x30, [sp, #-16]!','mov x29, sp','ldp x29, x30, [sp], #16','ret']
    key,node,raw=body('root',ops,frame=16)
    def one(n=node,edges=None,summaries=None,others=None):return p.frame_body(n,{}if edges is None else edges,{}if summaries is None else summaries,{key:n}if others is None else others)
    accepted('balanced actual allocation matches static own frame',lambda:one()['observed_peak_bytes']==16)
    def changed(index,text,frame=16):
        modified=list(ops);modified[index]=text;return body('root',modified,frame=frame)[1]
    rejected('SP-changing reentry cannot acquire a second frame',lambda:one(changed(2,'b 1000')))
    rejected('dynamic SP arithmetic is unknown',lambda:one(changed(1,'sub sp, sp, x0')))
    rejected('unsupported SP move is unknown',lambda:one(changed(1,'mov sp, x0')))
    rejected('missing deallocation is not balanced return',lambda:one(changed(2,'nop')))
    rejected('actual peak cannot exceed static frame',lambda:one(changed(1,'mov x29, sp',8)))
    rejected('unknown FP cannot address an owned stack slot',lambda:one(changed(0,'ldr x0, [x29, #0]')))
    rejected('constant access beyond owned frame rejected',lambda:one(changed(1,'ldr x0, [sp, #16]')))
    rejected('dynamic SP index is not a fixed slot',lambda:one(changed(1,'ldr x0, [sp, x1]')))
    fork=['sub sp, sp, #16','cbz x0, 1010','mov x29, sp','b 1014','nop','add sp, sp, #16','ret']
    rejected('incompatible FP facts cannot merge',lambda:one(body('root',fork,frame=16)[1]))
    after=['stp x29, x30, [sp, #-16]!','mov x29, sp','cbz x0, 1014','ldp x29, x30, [sp], #16','ret','b 100c']
    accepted('success block after shared return is analyzed',lambda:one(body('root',after,frame=16)[1])['observed_peak_bytes']==16)
    rejected('internal BL is outside normal entry ABI',lambda:one(changed(1,'bl 100c')))
    rejected('indirect transfer cannot become a stack proof',lambda:one(changed(1,'br x0')))
    accepted('complete captured extent parser',lambda:len(p.parse_body(raw,node['proof']))==4)
    rejected('body hash must match evidence',lambda:p.parse_body(raw+'\n',node['proof']))
    bad=deepcopy(node['proof']);bad['symbol']['aliases']=['unbound']
    rejected('an arbitrary label is not an extent alias',lambda:p.parse_body(raw,bad))
    child_key,child,_=body('callee',['ret'],0x2000)
    root_key,root,_=body('root',['stp x29, x30, [sp, #-16]!','bl 2000','ldp x29, x30, [sp], #16','ret'],frame=16)
    graph={root_key:root,child_key:child};edges={root_key:{0x1004:child_key},child_key:{}}
    accepted('fixed acyclic call graph closes',lambda:len(p.analyze_graph(graph,edges,root_key))==2)
    recursive_key,recursive_node,_=body('callee',['stp x29, x30, [sp, #-16]!','bl 1000','ldp x29, x30, [sp], #16','ret'],0x2000,16)
    recursive={root_key:{0x1004:recursive_key},recursive_key:{0x2004:root_key}}
    rejected('recursive selected graph is not summed once',lambda:p.analyze_graph({root_key:root,recursive_key:recursive_node},recursive,root_key))
    rejected('unreachable inventory is not silently omitted',lambda:p.analyze_graph(graph,{root_key:{},child_key:{}},root_key))
    alias_node=deepcopy(root);alias_node['proof']['external_transfers']=[dict(address=0x1004,mnemonic='bl',target=0x2000,resolved_records=[dict(name='callee',address=child_key[0],bytes=child_key[1],offset=0),dict(name='callee_alias',address=child_key[0],bytes=child_key[1],offset=0)])]
    accepted('same-extent aliases produce one dependency',lambda:p.external_targets({root_key:alias_node,child_key:child})[root_key][0x1004]==child_key)
    wrong=deepcopy(alias_node);wrong['proof']['external_transfers'][0]['resolved_records'][0]['offset']=4
    rejected('interior callee offset is not an ABI entry',lambda:p.external_targets({root_key:wrong,child_key:child}))
    wrong=deepcopy(alias_node);wrong['proof']['external_transfers'][0]['resolved_records'][1]['address']=0x3000
    rejected('ambiguous linked extents fail closed',lambda:p.external_targets({root_key:wrong,child_key:child}))
    rejected('unlisted normal exit is not silently zero',lambda:p.external_targets({root_key:alias_node}))
    accepted('typed caller slot fits live frame',lambda:p.pointer_check('of_get_property',[None,None,-12,None,None,None,None,None],-16)[0]['width']==4)
    rejected('typed caller slot cannot cross entry SP',lambda:p.pointer_check('of_get_property',[None,None,-2,None,None,None,None,None],-16))
    rejected('unlisted outgoing stack-pointer ABI rejected',lambda:p.pointer_check('callee',[-8]+[None]*7,-16))
    helper_key,helper,_=body('property:OUTLINED_FUNCTION_7',['ldr x21, [sp, #16]','ret'],0x3000,kind='helper')
    helper_summary=p.frame_body(helper,{}, {},{helper_key:helper})
    accepted('borrowed helper records reads without own allocation',lambda:helper_summary['observed_peak_bytes']==0 and helper_summary['borrowed_intervals']==[(16,24)])
    root_key,root,_=body('root',['stp x29, x30, [sp, #-16]!','bl 3000','ldp x29, x30, [sp], #16','ret'],frame=16)
    rejected('helper read must fit actual caller allocation',lambda:p.frame_body(root,{0x1004:helper_key},{helper_key:helper_summary},{root_key:root,helper_key:helper}))
    key_fp,node_fp,_=body('of_n_addr_cells',['sub sp, sp, #48','add x29, sp, #16','sub x2, x29, #4','add sp, sp, #48','ret'],frame=48)
    accepted('fixed FP offset can differ from SP',lambda:p.frame_body(node_fp,{}, {},{key_fp:node_fp})['observed_peak_bytes']==48)
    forbidden_key,forbidden,_=body('property:OUTLINED_FUNCTION_8',['add x4, x29, #24','ret'],0x3000,kind='helper')
    rejected('unlisted helper cannot manufacture a slot adapter',lambda:p.frame_body(forbidden,{}, {},{forbidden_key:forbidden}))
    lock_key,lock,_=body(p.LOCK,['mrs x9, sp_el0','ldr w10, [x9, #16]','add w10, w10, #0x1','str w10, [x9, #16]','ret'],0x4000)
    unlock_ops=['stp x29, x30, [sp, #-16]!','mov x29, sp','mrs x8, sp_el0','ldr w9, [x8, #16]','subs w9, w9, #0x1','str w9, [x8, #16]','b.ne 5024','bl 6000','b 5024','ldp x29, x30, [sp], #16','ret']
    unlock_key,unlock,_=body(p.UNLOCK,unlock_ops,0x5000,16)
    primitives={lock_key:lock,unlock_key:unlock};primitive_edges={lock_key:{},unlock_key:{0x501c:p.SCHEDULE}}
    accepted('nonzero compiled count branch excludes scheduler',lambda:p.compiled_counter_predicate(primitives,primitive_edges)['pruned_branch']==0x5018)
    def balanced_counter():
        k,n,_=body('root',['stp x29, x30, [sp, #-16]!','bl 4000','bl 5000','ldp x29, x30, [sp], #16','ret'],0x7000,16)
        predicate=p.compiled_counter_predicate(primitives,primitive_edges)
        summaries=p.analyze_graph({**primitives,k:n},{**primitive_edges,k:{0x7004:lock_key,0x7008:unlock_key}},k,unlock_key,predicate['pruned_branch'])
        return summaries[k]['counter_effect']==0 and summaries[k]['required_lock_level']==0 and summaries[k]['max_lock_delta']==1
    accepted('balanced query lock calls retain outer count1',balanced_counter)
    def unmatched_unlock():
        k,n,_=body('root',['stp x29, x30, [sp, #-16]!','bl 5000','ldp x29, x30, [sp], #16','ret'],0x7000,16)
        predicate=p.compiled_counter_predicate(primitives,primitive_edges)
        return p.analyze_graph({unlock_key:unlock,k:n},{unlock_key:primitive_edges[unlock_key],k:{0x7004:unlock_key}},k,unlock_key,predicate['pruned_branch'])
    rejected('unmatched unlock cannot preserve outer invariant',unmatched_unlock)
    def wrong_predicate():
        changed=deepcopy(primitives);changed[unlock_key]['rows'][6]=(0x5018,'b.eq','5024');return p.compiled_counter_predicate(changed,primitive_edges)
    rejected('wrong zero/nonzero predicate cannot exclude scheduling',wrong_predicate)
    def reenter_count():
        changed=deepcopy(primitives);changed[lock_key]['rows'][4]=(0x4010,'b','4000');return p.compiled_counter_predicate(changed,primitive_edges)
    rejected('lock loop cannot repeat increment',reenter_count)
    def wrong_epilogue():
        changed=deepcopy(primitives);changed[unlock_key]['rows'][9]=(0x5024,'b','500c');return p.compiled_counter_predicate(changed,primitive_edges)
    rejected('nonzero branch cannot repeat decrement',wrong_epilogue)
    rejected('source bytes are part of conditional mechanism',lambda:p.preemption_predicate(primitives,primitive_edges,{}))
    invalid=dict(passed=True,source_head='0'*40,run_id=p.TARGET_RUN)
    rejected('analysis cannot relabel another target head',lambda:p.inventory(invalid,{}))
    for name,call,wanted in cases:
        try:actual=call()is not False
        except(ValueError,KeyError,TypeError):actual=False
        if actual is not wanted:raise AssertionError(name)
    if len(cases)!=COUNTS['variants']:raise AssertionError('new conditional proof case count')
    return dict(COUNTS)
