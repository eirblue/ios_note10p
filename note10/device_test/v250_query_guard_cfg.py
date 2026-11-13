"""Local compiled caller ownership only; external callees remain opaque."""
import json
import re

CALLER='n240_observe_current_cpu'
CAPTURES={'n231_capture_cpu_observation','n233_capture_cpu_node_consistency'}
SCHEDULER='preempt_schedule'
BASE_OPS={'stp','str','stur','mov','cbz','cbnz','mrs','ldr','cmp','tst','tbnz','bl','ret','ldp','add','adrp','subs','csel','b','b.ne','b.eq','b.hi'}


def require(ok,message):
    if not ok:raise ValueError(message)


def analyze(rows,edges,parser):
    require(0<len(rows)<=4096 and len({r[0]for r in rows})==len(rows),'bounded unique instruction rows')
    texts=[parser.normalized(op+' '+args)for _,op,args in rows]
    stores=[i for i,text in enumerate(texts)if re.match(r'st\w+.*\[x22,#(?:16|0x10)\]',text)]
    acquisitions=[];releases=[];interiors=set()
    for i in stores:
        require(texts[i]=='strw8,[x22,#16]','unrecognized counter write')
        if i>=4 and texts[i-4]=='ldrw8,[x22,#16]'and texts[i-3].startswith('adrpx23,')and texts[i-2]=='addx23,x23,#0x28'and texts[i-1]=='addw8,w8,#0x1':
            acquisitions.append(i);interiors.update(range(i-3,i+1))
        elif i>=2 and texts[i-2]=='ldrw8,[x22,#16]'and texts[i-1]=='subsw8,w8,#0x1':
            releases.append(i);interiors.update(range(i-1,i+1))
        else:raise ValueError('unrecognized counter write/sequence')
    require(len(acquisitions)==len(releases)==1,'one acquisition and one release required')
    require(texts.count('mrsx22,sp_el0')==1,'actual counter base witness required')
    acq=acquisitions[0];release=releases[0];addresses={row[0]:i for i,row in enumerate(rows)}
    require(set(edges)<=set(addresses),'external call must hit a body instruction')
    for i,(address,op,args)in enumerate(rows):
        if address in edges:require(op=='bl','only opaque ordinary external calls supported')
        elif op in ('b','bl','cbz','cbnz','tbz','tbnz')or op.startswith('b.'):
            require(parser.branch_target(args)in addresses and addresses[parser.branch_target(args)]not in interiors,'branch enters partial counter sequence')
    seen=set();pending=[(0,'not_acquired',False)];states={};calls={};returns=[];base_states={}
    while pending:
        index,state,base_valid=pending.pop()
        if (index,state,base_valid)in seen:continue
        seen.add((index,state,base_valid));require(len(seen)<=len(rows)*6,'bounded local state convergence')
        states.setdefault(index,set()).add(state);address,op,args=rows[index]
        require(op in BASE_OPS,'unsupported fixed-caller register-write semantics')
        base_states.setdefault(index,set()).add(base_valid)
        # Fixed-caller invariant, not a general alias analysis: reject local
        # copies/offset aliases or pointer spills while the witnessed base lives.
        prefix=args.split('[',1)[0];registers=re.findall(r'\b[xw](?:[0-9]+|zr)\b',prefix)
        writes=[]
        if op.startswith('ldp'):writes=registers[:2]
        elif op.startswith('ld')or op not in ('cmp','cmn','tst','ccmp','ccmn','ret','b','bl','cbz','cbnz','tbz','tbnz')and not op.startswith(('st','b.')):writes=registers[:1]
        reads=registers[len(writes):]
        if base_valid:require(not({'x22','w22'}&set(reads)),'unsupported local counter-base alias/read')
        if re.search(r'\[x22,\s*#(?:16|0x10)\]',args):require(base_valid,'counter base clobbered before access')
        if op=='mrs'and parser.normalized(args)=='x22,sp_el0':base_valid=True
        elif {'x22','w22'}&set(writes)or re.search(r'\[x22[^]]*\](?:!|,)',args):base_valid=False
        if index==acq:require(state=='not_acquired','second acquisition');state='owned'
        if index==release:require(state=='owned','release without ownership/second release');state='released'
        if address in edges:
            edge=edges[address];names=set(edge['names'])
            if names&CAPTURES:require(state=='owned','capture without caller ownership')
            if SCHEDULER in names:require(state=='released','scheduler before caller release')
            calls.setdefault(address,set()).add(state)
        if op=='ret':require(state!='owned','return before owned release');returns.append(dict(address=address,state=state))
        pending.extend((n,state,base_valid)for n in parser.successors(rows,index,edges))
    require(returns and acq in states and release in states,'reachable ownership and return paths required')
    named={name for address in calls for name in edges[address]['names']}
    require(CAPTURES|{SCHEDULER}<=named,'actual selected call boundaries required')
    return dict(local_guard_ownership_proven=True,captured_calls_inside_owned_interval=True,explicit_frontdoor_scheduler_after_release=True,
        acquisition_store=rows[acq][0],release_store=rows[release][0],instruction_states=[dict(address=rows[i][0],states=sorted(s))for i,s in sorted(states.items())],
        counter_base_valid_at_every_local_access=True,unsupported_local_counter_base_aliases_present=False,
        counter_base_states=[dict(address=rows[i][0],valid_states=sorted(s))for i,s in sorted(base_states.items())],
        call_sites=[dict(address=address,states=sorted(states),opaque=True,**edges[address])for address,states in sorted(calls.items())],returns=returns,
        external_callee_counter_preservation_proven=False,external_callee_register_preservation_proven=False,normal_callee_saved_ABI_assumed=True,
        whole_frontdoor_stack_bound_proven=False,conditional_runtime_admission_proven=False,
        whole_query_peak_proven=False,outer_put_scheduler_bound_proven=False,atomic_interval_duration_measured=False,runtime_CPU_observed=False,physical_ready=False)


def captured(receive,build,raw,of_raw,parser):
    require(receive['authenticated']is receive['passed']is build['passed']is True and receive['source_head']==build['source_head']and receive['run_id']==build['run_id'],'authenticated same target required')
    graph=build['guarded_query_graph'];proof=graph['named_bodies'][CALLER];symbol=proof['symbol'];text=raw['assembly'][CALLER]
    require(raw['target']==build['guarded_query_target']and raw['symbols'][CALLER]==symbol and graph['raw_sha256']==parser.sha((json.dumps(raw,indent=2,sort_keys=True)+'\n').encode()),'original raw/result binding required')
    require(symbol['bytes']==500 and symbol['symbol']==CALLER and proof['disassembly_sha256']==parser.sha(text.encode()),'fixed complete caller identity required')
    rows=parser.parse_body(text,proof);edges={}
    node_proof=build['of_call_evidence']['retained']['primary']['assembly']['n233_capture_cpu_node_consistency'];node=node_proof['symbol']
    require(node_proof['disassembly_sha256']==parser.sha(of_raw['retained']['primary']['assembly']['n233_capture_cpu_node_consistency'].encode()),'existing node raw proof binding required')
    for edge in proof['external_transfers']:
        require(edge['mnemonic']=='bl'and not edge['unresolved']and edge['resolved_records'],'resolved ordinary external boundary required')
        records=edge['resolved_records'];require(all(r['offset']==0 and r['address']==edge['target']and type(r['ordinal'])is int and r['bytes']>0 for r in records)and len({(r['address'],r['bytes'])for r in records})==1,'exact source-bound entry extent/ordinal required')
        names={r['name']for r in records}
        for name in names&CAPTURES:
            target=raw['symbols'][name]if name in raw['symbols']else node
            require(target['address']==records[0]['address']and target['bytes']==records[0]['bytes'],'selected captured callee extent differs')
            aliases=graph['named_bodies'][name]['alias_records']if name in graph['named_bodies']else node_proof['alias_records']
            require(all(any(all(alias[k]==record[k]for k in ('name','address','bytes','kind','ordinal'))for alias in aliases)for record in records),'selected callee nm ordinal differs')
        instruction=next((r for r in rows if r[0]==edge['address']),None)
        require(instruction and instruction[1]=='bl'and parser.branch_target(instruction[2])==edge['target'],'actual caller call instruction differs')
        edges[edge['address']]=dict(names=sorted(names),target=edge['target'],resolved_records=records)
    result=analyze(rows,edges,parser);result.update(schema='note10-v250-local-query-guard-proof-v1',target_source_head=receive['source_head'],target_run=receive['run_id'],caller_symbol=symbol,caller_disassembly_sha256=proof['disassembly_sha256'],scheduler_body_captured=False)
    return result
