"""Conditional proof of the fixed captured238 query, never a runtime admission."""
from collections import deque
import hashlib
import re

SCHEMA='note10-v239-conditional-node-query-proof-v1'
TARGET_HEAD='ddeb90b4da7f5fb75a95ff44586f918bebc1a2d0'
TARGET_RUN=43389733142
C_NAMES=('__of_find_all_nodes','__of_find_property','_raw_spin_lock_irqsave','_raw_spin_unlock_irqrestore',
    'arch_find_n_match_cpu_physical_id','arch_match_cpu_phys_id','n233_capture_cpu_node_consistency','n233_clear_consistency',
    'of_find_node_by_type','of_find_property','of_get_cpu_node','of_get_parent','of_get_property','of_n_addr_cells','strcasecmp',
    'of_find_property_value_of_size','of_property_read_variable_u32_array')
OF_HELPERS=(0,1,2,4,5,7,9,12,13,15,18,22,23)
PROPERTY_HELPERS=(7,8,11)
LOCK='_raw_spin_lock_irqsave'
UNLOCK='_raw_spin_unlock_irqrestore'
SCHEDULE='preempt_schedule'
CONFIG={'ARM64':'y','PREEMPT':'y','PREEMPT_COUNT':'y','PREEMPT_TRACER':'n','DEBUG_PREEMPT':'n',
    'GENERIC_LOCKBREAK':'n','DEBUG_LOCK_ALLOC':'n','OF':'y','OF_DYNAMIC':'n','OF_OVERLAY':'n','SMP':'y','NR_CPUS':'8'}
SOURCE_HASHES={'include/linux/smp.h': '8d1094af3b3ddde955be5dd9e8d84349583883d40df3bf73832acb4d95ca0ff0', 'include/asm-generic/preempt.h': '7d7db96b2574f7a5765722965e963b1c2907c374c72a70ad63f3e68dfc2214dd', 'arch/arm64/include/asm/Kbuild': '7c57cf62e62210fa2084e7d38a6909f931475e9732692892b237a46398520ee8', 'arch/arm64/include/asm/thread_info.h': 'b000aad1bf2a1b622bc9307fe8ad30127a3c847307d5af0f90348b533d3baf9f', 'include/linux/preempt.h': '386da1a2be5458d2a6e172286987ce9fe6e8383d50377ad42a220c7026c228af', 'include/linux/spinlock_api_smp.h': 'e38b2efdb2b84888f2e204f524a30ccf4021e6561067c23c20da586511ab97f6', 'drivers/of/base.c': '99d93a76c7828a910ee8094c404ad4a3e2106f0affca18441572d1ef8400b4aa', 'include/linux/of.h': 'd9127c18db73393fe07ac50e801c8c1898b8d4b41366c5ca5d14c8244ef8bcdb', 'drivers/of/property.c': '2ce1a02d386d775368a9bfe1dd81eb47e1ba25a43afbcba03af6bf440dfac2ed'}
OUT_WIDTHS={'of_get_cpu_node':{1:4},'of_get_property':{2:4},'of_find_property':{2:4},
    'of_property_read_variable_u32_array':{2:4},'of_find_property_value_of_size':{4:8}}
CONDITIONAL_LIMITS=dict(runtime_hook_allowed=False,lookup_runtime_bound_proven=False,whole_OF_scheduler_bound_proven=False,
    outer_preemption_guard_compiled=False,outer_preemption_guard_runtime_observed=False,hardware_authorized=False,
    capture_plus_future_caller_chain_bound_proven=False,IRQ_NMI_whole_kernel_stack_bound_proven=False)


def require(ok,message):
    if not ok:raise ValueError(message)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def immediate(value):
    require(re.fullmatch(r'-?(?:0x[0-9a-f]+|[0-9]+)',value)is not None,'literal stack immediate required')
    sign=-1 if value.startswith('-')else 1;v=value.lstrip('-');return sign*int(v,16 if v.startswith('0x')else 10)


def normalized(text):return re.sub(r'\s+','',text.lower())


def parse_body(raw,proof):
    require(sha(raw.encode())==proof['disassembly_sha256'],'captured body SHA required')
    symbol=proof['symbol'];rows=[];labels=[]
    for line in raw.splitlines():
        label=re.fullmatch(r'\s*([0-9a-fA-F]+) <([^>]+)>:\s*',line)
        if label:labels.append((int(label[1],16),label[2]))
        if re.match(r'^\s*[0-9a-fA-F]+:',line):
            row=re.fullmatch(r'\s*([0-9a-fA-F]+):\s+[0-9a-fA-F]{8}\s+(.+)',line)
            require(row is not None,'every fixed body instruction must decode')
            text=row[2].lower().split('//',1)[0].strip();parts=text.split(None,1)
            rows.append((int(row[1],16),parts[0],parts[1]if len(parts)==2 else''))
    require(0<len(rows)<=4096 and len(rows)*4==symbol['bytes']and
        all(address==symbol['address']+4*i for i,(address,_,_)in enumerate(rows))and
        len(labels)==1 and labels[0][0]==symbol['address']and labels[0][1]in symbol['aliases'],
        'one complete fixed same-extent body and alias required')
    require(not proof['unknown_control_transfers']and not any(edge['unresolved']for edge in proof['external_transfers']),
        'unresolved or indirect captured transfer remains unknown')
    return rows


def inventory(build,raw):
    require(build['passed']is True and build['source_head']==TARGET_HEAD and build['run_id']==TARGET_RUN,
        'analysis is bound to the existing238 target, never an Image239')
    require(all(build['effective_profile'].get(key,'n')==value for key,value in CONFIG.items()),'exact target preemption/static OF config required')
    data=build['of_call_evidence'];old=data['retained'];primary=old['primary'];body={}
    C={**primary['object_provenance'],**data['property_input_section']['C_anchors']}
    require(set(C)==set(C_NAMES),'fixed seventeen C functions required')
    def add(name,kind,proof,text,frame):
        symbol=proof['symbol'];key=(symbol['address'],symbol['bytes'])
        require(key not in body,'aliases must identify one body, never duplicate frames')
        require(type(frame)is int and 0<=frame<=8192,'static frame bytes required')
        body[key]=dict(name=name,kind=kind,frame=frame,proof=proof,rows=parse_body(text,proof))
    for name,row in C.items():
        require(row['frame_kind']=='static','dynamic C frame is unknown')
        proof=primary['assembly'][name]if name in primary['assembly']else data['property_C_bodies'][name]
        text=raw['retained']['primary']['assembly'][name]if name in primary['assembly']else raw['assembly'][name]
        require(proof['symbol']['address']==row['linked_address']and proof['symbol']['bytes']==row['bytes'],'C frame/body extent join required')
        add(name,'C',proof,text,row['frame_bytes'])
    strcmp=old['strcmp_same_body_leaf'];require(strcmp['zero_own_stack_proven']is True,'same-body strcmp own-stack proof required')
    add('strcmp','asm',strcmp,raw['retained']['primary']['assembly']['strcmp'],0)
    of_rows={row['identity']:row for row in old['outlined_input_section_join']['helpers']}
    require({row['symbol']['symbol']for row in of_rows.values()}=={'OUTLINED_FUNCTION_'+str(n)for n in OF_HELPERS},'fixed OF helper inventory required')
    for identity,row in of_rows.items():add('of:'+row['symbol']['symbol'],'helper',old['outlined_bodies'][identity],raw['retained']['outlined_assembly'][identity],0)
    prop=data['property_local_joins'];require({record['name']for row in prop.values()for record in row['records']}=={'OUTLINED_FUNCTION_'+str(n)for n in PROPERTY_HELPERS},'fixed property helper inventory required')
    for identity,row in prop.items():add('property:'+row['symbol']['symbol'],'helper',data['property_local_bodies'][identity],raw['assembly'][identity],0)
    require(len(body)==34,'fixed34 same-extent bodies required');return body


def external_targets(body):
    result={}
    for key,node in body.items():
        edges={}
        for edge in node['proof']['external_transfers']:
            require(edge['mnemonic']in ('bl','b'),'external conditional/indirect exit is unknown')
            instruction=[row for row in node['rows']if row[0]==edge['address']]
            require(len(instruction)==1 and instruction[0][1]==edge['mnemonic']and branch_target(instruction[0][2])==edge['target'],
                'external metadata must match the captured actual instruction')
            records=edge['resolved_records'];require(records and all(r['offset']==0 for r in records),'only exact external entries allowed')
            require(all(r['address']+r['offset']==edge['target']for r in records),'resolved record must match the branch target')
            extents={(r['address'],r['bytes'])for r in records};require(len(extents)==1,'ambiguous external extents are unknown')
            target=next(iter(extents));names={r['name']for r in records}
            if target not in body:require(node['name']==UNLOCK and names=={SCHEDULE},'unlisted selected-query exit')
            edges[edge['address']]=target if target in body else SCHEDULE
        result[key]=edges
    return result


def branch_target(args):
    literal=re.sub(r'<[^>]+>','',args).split(',')[-1].strip()
    require(re.fullmatch(r'(?:0x)?[0-9a-f]+',literal)is not None,'literal branch target required');return int(literal,16)


def successors(rows,index,external,prune=None):
    address,op,args=rows[index];addresses={row[0]:i for i,row in enumerate(rows)}
    if op=='ret':require(args in ('','x30'),'ordinary return required');return []
    conditional=op in ('cbz','cbnz','tbz','tbnz')or re.fullmatch(r'b\.(eq|ne|cs|cc|hs|lo|mi|pl|vs|vc|hi|ls|ge|lt|gt|le|al|nv)',op)
    if op in ('b','bl')or conditional:
        target=branch_target(args)
        if address in external:
            require(op in ('bl','b'),'external conditional exit unknown')
            if op=='b':return []
        elif op=='bl':raise ValueError('internal BL/recursion is outside fixed ABI')
        else:
            require(target in addresses,'internal branch must hit an instruction')
            if op=='b'or address==prune:return [addresses[target]]
            require(index+1<len(rows),'conditional fallthrough outside body');return [addresses[target],index+1]
    else:
        require(op not in ('br','blr','eret','eretaa','eretab','drps','svc','hvc','smc','brk','hlt','udf','dcps1','dcps2','dcps3')and
            not op.startswith(('.','ret','b.','cb','tb'))and(not op.startswith('b')or op in ('bic','bics','bfi','bfxil')),
            'unsupported control instruction')
    require(index+1<len(rows),'unclosed function fallthrough');return [index+1]


def preemption_predicate(body,edges,sources):
    require(set(sources)==set(SOURCE_HASHES)and all(sha(text.encode())==SOURCE_HASHES[name]for name,text in sources.items()),'exact pinned source mechanism required')
    return compiled_counter_predicate(body,edges)


def compiled_counter_predicate(body,edges):
    byname={node['name']:key for key,node in body.items()};lock=body[byname[LOCK]]['rows'];unlock=body[byname[UNLOCK]]['rows']
    def find(rows,sequence):
        texts=[normalized(op+' '+args)for _,op,args in rows];wanted=[normalized(x)for x in sequence]
        found=[i for i in range(len(rows)-len(sequence)+1)if texts[i:i+len(wanted)]==wanted]
        require(len(found)==1,'one actual compiled count update sequence required');return found[0]
    increment=find(lock,['mrs x9, sp_el0','ldr w10, [x9, #16]','add w10, w10, #0x1','str w10, [x9, #16]'])
    decrement=find(unlock,['ldr w9, [x8, #16]','subs w9, w9, #0x1','str w9, [x8, #16]'])
    require(unlock[decrement+3][1]=='b.ne','nonzero post-decrement must bypass scheduler')
    branch=unlock[decrement+3][0]
    require(any(target==SCHEDULE for target in edges[byname[UNLOCK]].values()),'explicit scheduler boundary required')
    # No call/branch may skip or re-enter the lock increment prefix.
    require(all(op not in ('b','bl','ret','cbz','cbnz','tbz','tbnz')and not op.startswith('b.')for _,op,_ in lock[:increment+4]),'lock increment must dominate the wait/return path')
    for _,op,args in lock[increment+4:]:
        if op in ('b','cbz','cbnz','tbz','tbnz')or op.startswith('b.'):
            require(branch_target(args)>lock[increment+3][0],'lock wait must not repeat the count increment')
    require(all(op not in ('b','bl','ret','cbz','cbnz','tbz','tbnz')and not op.startswith('b.')for _,op,_ in unlock[:decrement+3]),'unlock decrement must occur once before its predicate')
    bypass=branch_target(unlock[decrement+3][2]);out=next((i for i,row in enumerate(unlock)if row[0]==bypass),None)
    require(out is not None and out+1<len(unlock)and normalized(unlock[out][1]+' '+unlock[out][2])==normalized('ldp x29, x30, [sp], #16')and
        unlock[out+1][1]=='ret'and unlock[out+1][2]in ('','x30'),'nonzero branch must go straight to the balanced epilogue')
    seen=set();pending=[0]
    while pending:
        index=pending.pop()
        if index in seen:continue
        seen.add(index);require(edges[byname[UNLOCK]].get(unlock[index][0])!=SCHEDULE,'scheduler remains reachable under nonzero invariant')
        pending.extend(successors(unlock,index,edges[byname[UNLOCK]],branch))
    return dict(unlock_key=byname[UNLOCK],pruned_branch=branch,outer_preempt_count_min=1,unlock_input_lock_level_required=1,
        scheduler_not_analyzed=True,guard_is_hypothetical_not_compiled=True)


def memory(op,args):
    names=('ldr','str','ldur','stur','ldrb','strb','ldurb','sturb','ldrh','strh','ldurh','sturh','ldrsw','ldursw','ldp','stp')
    if op not in names:return None
    m=re.fullmatch(r'([xw](?:[0-9]|[12][0-9]|30|zr))(?:,\s*([xw](?:[0-9]|[12][0-9]|30|zr)))?,\s*\[(sp|x29)(?:,\s*#(-?(?:0x[0-9a-f]+|\d+)))?\](!)?(?:,\s*#(-?(?:0x[0-9a-f]+|\d+)))?',args)
    if not m:return None
    pair=op in ('ldp','stp');require(pair==(m[2]is not None),'typed stack load/store operands required')
    width=1 if op.endswith('b')else 2 if op.endswith('h')else 4 if op.endswith('sw')or m[1].startswith('w')else 8
    if pair:require(m[1][0]==m[2][0],'matching stack pair widths required');width*=2
    require(not(m[5]and m[6])and(m[3]=='sp'or not(m[5]or m[6])),'only SP immediate writeback supported')
    return dict(regs=[m[1]]+([m[2]]if m[2]else[]),base=m[3],offset=immediate(m[4]or'0'),pre=bool(m[5]),post=immediate(m[6])if m[6]else 0,width=width,load=op.startswith('ld'))


def pointer_check(name,args,sp):
    slots=[]
    for index,value in enumerate(args):
        if value is None:continue
        require(index in OUT_WIDTHS.get(name,{}),'unlisted stack-pointer argument ABI')
        width=OUT_WIDTHS[name][index];require(sp<=value and value+width<=0,'outgoing typed slot outside caller frame')
        slots.append(dict(callee=name,argument=index,entry_SP_interval=[value,value+width],width=width))
    return slots


def slot_signatures(nodes):
    """Fixed typed adapters, not a generic variable-array ABI width assumption."""
    names={row['name']:row for row in nodes.values()}
    def exact(name,wanted):
        rows=names[name]['rows'];texts=[normalized(op+' '+args)for _,op,args in rows]
        require(texts[:-1]==[normalized(text)for text in wanted]and rows[-1][1]=='b','exact reviewed typed tail adapter required')
    exact('of:OUTLINED_FUNCTION_5',['cmp x8, #0x0','sub x2, x29, #0x4','csel x19, x19, x8, eq','mov x1, x20','mov x0, x19','mov w3, #0x1','mov x4, xzr'])
    exact('property:OUTLINED_FUNCTION_11',['add x4, x29, #0x18'])
    setup=[normalized(op+' '+args)for _,op,args in names['property:OUTLINED_FUNCTION_8']['rows']]
    require(setup==[normalized(text)for text in ('mov x21, x4','mov x20, x3','mov x19, x2','ret')],'actual min/max/output register setup required')
    public=names['of_property_read_variable_u32_array']['rows'];text=[normalized(op+' '+args)for _,op,args in public]
    for wanted in ('cmp x21, #0x0','csel x8, x20, x8, eq','str w10, [x19, x9, lsl #2]','add x9, x9, #0x1'):
        require(text.count(normalized(wanted))==1,'one actual min1/max0 four-byte array loop required')
    static=[normalized(op+' '+args)for _,op,args in names['of_find_property_value_of_size']['rows']]
    require(static.count(normalized('mov x19, x4'))==static.count(normalized('str x9, [x19]'))==1,'actual eight-byte saved length output required')


def frame_body(node,external,summaries,nodes,prune=None):
    rows=node['rows'];states={0:(0,None,0,(None,)*8)};pending=deque([0]);required=0;peak=0;max_level=0;returns=set();borrowed=[];pointers={};arg_writes=set();calls=[];slots=[];visits=0
    while pending:
        index=pending.popleft();visits+=1;require(visits<=len(rows)*32,'bounded local dataflow convergence required')
        sp,fp,level,args=states[index];args=list(args);address,op,text=rows[index];original_sp=sp
        m=memory(op,text)
        stack_math=re.fullmatch(r'(sp|x29),\s*sp,\s*#(-?(?:0x[0-9a-f]+|\d+))',text)if op in ('add','sub')else None
        ptr=re.fullmatch(r'x([0-7]),\s*(sp|x29),\s*#(-?(?:0x[0-9a-f]+|\d+))',text)if op in ('add','sub')else None
        dest=text.split(',',1)[0].strip()
        if m:
            if m['pre']:sp+=m['offset'];offset=0
            else:offset=m['offset']
            base=sp if m['base']=='sp'else fp;require(base is not None,'unknown FP stack reference')
            start=base+offset;end=start+m['width']
            if node['kind']=='helper':
                require(m['base']=='sp'and not m['pre']and not m['post']and m['load']and not{'x29','x30'}&set(m['regs']),
                    'helper must only borrow constant SP loads without FP/LR changes')
                borrowed.append([start,end])
            else:require(sp<=start<end<=0,'stack access outside current owned frame')
            if m['load']:
                if 'x29'in m['regs']:fp=None
                for reg in m['regs']:
                    if re.fullmatch(r'[xw][0-7]',reg):args[int(reg[1:])]=None;arg_writes.add(int(reg[1:]))
            sp+=m['post']
        elif stack_math:
            value=immediate(stack_math[2])*(1 if op=='add'else-1)
            if stack_math[1]=='sp':sp+=value
            else:require(node['kind']!='helper','helper FP write unsupported');fp=sp+value
        elif op=='mov'and normalized(text)=='x29,sp':require(node['kind']!='helper','helper FP write unsupported');fp=sp
        elif ptr:
            register=int(ptr[1]);offset=immediate(ptr[3])*(1 if op=='add'else-1);base=sp if ptr[2]=='sp'else fp
            if node['kind']=='helper':
                expected={'of:OUTLINED_FUNCTION_5':(2,'x29',-4),'property:OUTLINED_FUNCTION_11':(4,'x29',24)}
                require(expected.get(node['name'])==(register,ptr[2],offset),'only the two reviewed typed helper outputs allowed')
                value=('fp'if ptr[2]=='x29'else'sp',offset)
                require(register not in pointers or pointers[register]==value,'incompatible helper slot output')
                pointers[register]=value;args[register]=None
            else:require(base is not None,'unknown FP argument base');args[register]=base+offset
            arg_writes.add(register)
        else:
            require(not re.search(r'\b(?:sp|wsp|x29|fp)\b',text),'unsupported SP/FP instruction or alias')
            if node['kind']=='helper':require(dest not in ('x30','w30','lr'),'helper return-link write unsupported')
            if re.fullmatch(r'[xw][0-7]',dest)and op not in ('cbz','cbnz','tbz','tbnz','ret','msr')and not op.startswith(('st','cmp','cmn','tst','ccmp','ccmn')):
                r=int(dest[1:]);source=re.fullmatch(r'x([0-7]),\s*x([0-7])',text)if op=='mov'else None
                require(node['kind']!='helper'or r not in pointers,'helper output pointer overwritten')
                args[r]=args[int(source[2])]if source else None;arg_writes.add(r)
            if op=='ldp':
                second=text.split(',')[1].strip()
                if re.fullmatch(r'[xw][0-7]',second):args[int(second[1:])]=None;arg_writes.add(int(second[1:]))
        require(-8192<=sp<=0,'unsupported allocation, reentry or SP above entry');peak=max(peak,-sp)
        if address in external:
            target=external[address];require(target!=SCHEDULE,'unguarded scheduler call reached')
            child=summaries[target];child_node=nodes[target]
            required=max(required,child['required_lock_level']-level);max_level=max(max_level,level+child['max_lock_delta']);level+=child['counter_effect']
            if child_node['kind']=='helper':
                for lo,hi in child['borrowed_intervals']:require(sp<=sp+lo<sp+hi<=0,'borrowed helper load exceeds live caller frame')
                for register in child['arg_writes']:args[register]=None
                for register,(base,offset)in child['pointer_outputs'].items():
                    value=sp if base=='sp'else fp;require(value is not None,'unknown caller FP for helper output');args[register]=value+offset
                tail=child['tail_target']
                if tail is not None:slots.extend(pointer_check(nodes[tail]['name'],args,sp));args=[None]*8
            else:slots.extend(pointer_check(child_node['name'],args,sp));args=[None]*8
            calls.append(dict(address=address,target=child_node['name'],SP_offset=sp,FP_offset=fp,lock_delta_before=level-child['counter_effect']))
        if op=='ret'or(op=='b'and address in external):
            require(sp==0,'unbalanced return/tail SP');returns.add(level)
        for nxt in successors(rows,index,external,prune):
            state=(sp,fp,level,tuple(args))
            if nxt in states:
                previous=states[nxt];require(previous[:3]==state[:3],'incompatible SP/FP/preemption CFG merge')
                merged=previous[:3]+(tuple(a if a==b else None for a,b in zip(previous[3],state[3])),)
                if merged!=previous:states[nxt]=merged;pending.append(nxt)
            else:states[nxt]=state;pending.append(nxt)
    require(len(returns)==1,'one balanced local counter effect required')
    effect=next(iter(returns));name=node['name']
    if name==LOCK:effect=1;max_level=1
    elif name==UNLOCK:effect=-1;required=max(required,1)
    elif node['kind']!='helper':require(effect==0,'C function leaves an unbalanced query lock level')
    require(peak<=node['frame']if node['kind']!='helper'else peak==0,'actual SP peak exceeds static C frame or helper-neutral scope')
    tails=[target for address,target in external.items()if any(row[0]==address and row[1]=='b'for row in rows)]
    require(node['kind']!='helper'or len(tails)<=1,'only one fixed helper tail allowed')
    return dict(frame_bytes=node['frame'],observed_peak_bytes=peak,counter_effect=effect,required_lock_level=max(0,required),max_lock_delta=max_level,
        borrowed_intervals=sorted({tuple(x)for x in borrowed}),pointer_outputs=pointers,arg_writes=sorted(arg_writes),tail_target=tails[0]if tails else None,
        calls=calls,typed_caller_slots=slots,reachable_instructions=len(states),normal_ABI_SP_return_assumed=True)


def analyze_graph(nodes,edges,root,prune_key=None,prune_branch=None):
    require(0<len(nodes)<=34 and root in nodes,'bounded fixed query graph required');summaries={};visiting=set()
    def visit(key):
        if key in summaries:return
        require(key not in visiting,'recursive selected query graph is unknown');visiting.add(key)
        for target in edges[key].values():
            if target!=SCHEDULE:visit(target)
        node=nodes[key];prune=prune_branch if key==prune_key else None
        try:summaries[key]=frame_body(node,edges[key],summaries,nodes,prune)
        except ValueError as error:raise ValueError(node['name']+': '+str(error))from error
        visiting.remove(key)
    visit(root)
    require(set(summaries)==set(nodes),'fixed query inventory has unreachable/unproved bodies')
    return summaries


def prove(build,raw,sources):
    nodes=inventory(build,raw);edges=external_targets(nodes);slot_signatures(nodes);predicate=preemption_predicate(nodes,edges,sources)
    root=next(key for key,node in nodes.items()if node['name']=='n233_capture_cpu_node_consistency')
    summaries=analyze_graph(nodes,edges,root,predicate['unlock_key'],predicate['pruned_branch'])
    require(summaries[root]['counter_effect']==summaries[root]['required_lock_level']==0,'root must balance lock nesting under outer count1')
    bound=sum(node['frame']for node in nodes.values()if node['kind']=='C');require(0<bound<=8192,'conditional selected-frame cap exceeded')
    serial={}
    for key,row in summaries.items():
        serial[nodes[key]['name']]={**row,'borrowed_intervals':[list(interval)for interval in row['borrowed_intervals']],
            'pointer_outputs':{'x'+str(register):dict(base=value[0],offset=value[1])for register,value in row['pointer_outputs'].items()},
            'arg_writes':['x'+str(register)for register in row['arg_writes']],
            'tail_target':nodes[row['tail_target']]['name']if row['tail_target']is not None else None}
    return dict(schema=SCHEMA,passed=True,analysis_kind='conditional-existing238-query-proof',target_version='v238',target_source_head=TARGET_HEAD,target_CI_run=TARGET_RUN,
        target_Image_bytes=build['Image_bytes'],target_linked_bytes=build['linked_extent'],conditional_node_query_bound_bytes=bound,
        bound_kind='conservative sum of fixed acyclic C frames under stated outer-preemption invariant',normal_C_ABI_and_valid_argument_assumptions=True,
        functions=serial,preemption_invariant={k:v for k,v in predicate.items()if k!='unlock_key'},
        source_sha256=SOURCE_HASHES,current_C_capture32_not_a_proven_future_chain=True,atomic_interval_duration_unmeasured=True,
        previous238_records_unchanged=True,**CONDITIONAL_LIMITS)
