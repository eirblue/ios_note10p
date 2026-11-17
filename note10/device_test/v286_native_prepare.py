"""286 PC-only bounded contextual verifier; no hardware-ready claim."""
import json
import re
import subprocess
from collections import deque
from pathlib import Path
from types import SimpleNamespace
import v283_native_prepare as retained
import v279_native_prepare as seal_base
import v277_native_prepare as watchdog
import v275_native_prepare as frame_core
import v281_native_prepare as frame_forms

p,require,sha,bind=retained.p,retained.require,retained.sha,retained.bind
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
WORKFLOW='.github/workflows/note10-v286-native-prepare.yml';JOB='v286-native-prepare'
BUILD_SCHEMA='note10-v286-CPU-metadata-PC-build-v1'
CONTEXT_SCHEMA='note10-v286-CPU-metadata-PC-public-input-v1'
MANIFEST_SCHEMA='note10-v286-CPU-metadata-PC-sealed-members-v1'
CAPTURE_SCHEMA,TARGET_SCHEMA=watchdog.CAPTURE_SCHEMA,watchdog.TARGET_SCHEMA
decode_binding=watchdog.decode_binding
NEW_FILES=('v285_current_cpu_metadata.h','v285_current_cpu_metadata.c','v285_current_cpu_metadata.inc',
           'v285_current_cpu_metadata_fixture.c','v286_native_prepare.py','test_v286_contextual_validator.py')
ADDED_MEMBERS=('cpu-metadata-evidence.json','cpu-metadata-object.o','cpu-metadata-object.cmd',
               'cpu-metadata-object.su','cpu-metadata-object-elf.log')
SUCCESS_MEMBERS=(*retained.SUCCESS_MEMBERS,*ADDED_MEMBERS)
METADATA_TYPES=retained.METADATA_TYPES
NEW_NAMES=('n285_snapshot_of_locked','n285_find_property_locked','n285_prepare_metadata','n285_encode_cpu_adt',
           'n285_put_property','n285_write_pages','n285_readback_pages','n285_layout_witness')
OLD_NAMES=('n226_ingest_prepared_locked','n278_seal_once','n279_layout_witness','n210_request_valid',
           'n210_receipt_matches','n209_decode_payload','n209_layout_bounds','little','magic','nonzero','equal','hex32','extent','bcmp')
PROJECTION_NAMES=('n230_project_metadata','n230_span','n230_overlap','n230_copy','n10_rt_validate_adt',
                  'n10_rt_serialize_boot_args','n10_rt_serialize_record')
RT_NAMES=('zero_bytes','copy_bytes','add64','overlap','pointer_overlap','pointer_span','same','le32','put16',
          'put32','put64','name_byte','gic_name','take','adt_node','command_ok')
IO_NAMES=('n217_owner','n217_page_io','n217_write_destination','n217_read_destination')
NAMED=(*NEW_NAMES,*OLD_NAMES,*PROJECTION_NAMES,*RT_NAMES,*IO_NAMES)
NAMED_CAP,OUTLINED_CAP,EXTENT_CAP=49,30,79
OWNER_TARGET='arch/arm64/mm/init.o';NEW_TARGET='arch/arm64/mm/v285_current_cpu_metadata.o'
TARGETS={OWNER_TARGET:(seal_base.OWNER,'n279_layout_witness'),NEW_TARGET:('n285_prepare_metadata','n285_layout_witness'),
         seal_base.SEAL_TARGET:('n278_seal_once',),'arch/arm64/mm/v230_boot_metadata.o':('n230_project_metadata',),
         'arch/arm64/mm/v230_runtime_relocation.o':('n10_rt_validate_adt','n10_rt_serialize_boot_args','n10_rt_serialize_record'),
         'lib/string.o':('bcmp',)}
BOUNDARY_CALLERS={'n226_ingest_prepared_locked','n285_snapshot_of_locked','n217_owner','n217_page_io','n278_seal_once'}
ABI={'n285_size_workspace':24576,'n285_align_workspace':8,'n285_offset_snapshot':18208,'n285_offset_readback':20480}
DONE=b' done:\n'
AFTER_END=b'''    if(!error){
        memset(n226_source_pool,0,N226_WORKSPACE_BYTES);
        error=n285_snapshot_of_locked(&((struct n285_workspace *)n226_source_pool)->snapshot,
            (const struct n231_cpu_observation *)(n226_source_pool+N231_POOL_OFFSET),
            (const struct n233_cpu_node_consistency *)(n226_source_pool+N233_POOL_OFFSET),
            (const struct n240_query_receipt *)(n226_source_pool+N240_POOL_OFFSET));
        if(!error)error=n285_prepare_metadata(prepared,&n210_destination,context,ctx,
            (struct n285_workspace *)n226_source_pool,N226_WORKSPACE_BYTES);
        if(!error)error=n278_seal_once(N279_SEAL,prepared,&n210_destination,context,
            n210_result.descriptor_sha256,&n210_result,n210_spent,&n217_kernel_state);
    }
    if(error&&N279_SEAL->phase==N278_EMPTY)N279_SEAL->phase=N278_REFUSED;
'''

def source_pins():
    value=retained.source_pins();value.pop(retained.WORKFLOW)
    value.update({'note10/device_test/'+n:sha(p.ordinary(HERE/n))for n in NEW_FILES})
    value[WORKFLOW]=sha(p.ordinary(ROOT/WORKFLOW));return value

def public_context(head,passed):
    p.hexid(head,40)
    require(set(passed)=={'passed','groups','variants','assertions','result_sha256'} and passed['passed']is True and
            tuple(passed[k]for k in ('groups','variants','assertions'))==(1,1,1),'new286 contextual conjunction only')
    p.hexid(passed['result_sha256'])
    return dict(schema=CONTEXT_SCHEMA,source_head=head,source_sha256=source_pins(),new_fixture_PASS=passed,
                old_tests_replayed=False,PC_only=True,hardware_ready=False)

def owner_overlay(raw):
    require(raw.count(seal_base.CALL)==1 and raw.count(DONE)==1 and
            raw.count(b'n226_codec_end(ctx);')==1 and b'n285_'not in raw,'exact old success/end seams')
    guard=b'    if(n217_kernel_state.spent)return -EALREADY;'
    clear=b'    memset(n226_source_pool,0,sizeof(n226_source_pool));'
    require(raw.count(guard)==raw.count(clear)==1 and raw.index(guard)<raw.index(clear)<raw.index(seal_base.CALL),
            'shared spent precedes clear')
    changed=raw.replace(b'#include "v279_current_owner_seal.inc"\n',
                        b'#include "v279_current_owner_seal.inc"\n#include "v285_current_cpu_metadata.inc"\n',1)
    require(changed!=raw,'one owner-local snapshot include')
    changed=changed.replace(seal_base.CALL,b'',1).replace(b'n226_codec_end(ctx);',b'',1)
    changed=changed.replace(DONE,DONE+b'    n226_codec_end(ctx);\n'+AFTER_END,1)
    require(changed.count(b'n278_seal_once(')==1 and changed.count(b'n226_codec_end(ctx);')==1 and
            changed.index(b'n226_codec_end(ctx);')<changed.index(b'error=n285_prepare_metadata(')<
            changed.index(b'error=n278_seal_once(')<changed.index(b'stats->error='), 'final seal before pure cleanup')
    return changed

def install_binding(source,buffers):
    value=seal_base.install_binding(source,buffers)
    owner=source/'arch/arm64/mm/v226_source_stream_kernel.c';before=p.ordinary(owner);after=owner_overlay(before)
    owner.write_bytes(after)
    value['compiler_inputs']['arch/arm64/mm/v226_source_stream_kernel.c']['after_sha256']=sha(after)
    value['current_owner_seal']['owner_after_sha256']=sha(after)
    copied={}
    for name in NEW_FILES[:3]:
        target=source/'arch/arm64/mm'/name;require(not target.exists(),'fresh285 source input')
        target.write_bytes(buffers['note10/device_test/'+name]);copied[str(target.relative_to(source))]=sha(p.ordinary(target))
    make=source/'arch/arm64/mm/Makefile';old=p.ordinary(make)
    line=b'obj-$(CONFIG_NOTE10_V210_NATIVE_PREPARE) += v285_current_cpu_metadata.o\n'
    require(b'v285_current_cpu_metadata'not in old and old.endswith(b'\n'),'one new readonly metadata TU')
    make.write_bytes(old+line);value['current_owner_seal']['Kbuild_after_sha256']=sha(old+line)
    value['current_cpu_metadata']=dict(owner_path=str(owner.relative_to(source)),owner_after_sha256=sha(after),
        copied=copied,Kbuild_after_sha256=sha(old+line),seal_after_readback=True,new_BSS_bytes=0,new_pool_bytes=0,
        scratch_interval=[0,24576],freed_workspace_interval=[0,42312],adapter_record_installed=False)
    return value

def inventory_metadata(entries,passed):
    require(len(SUCCESS_MEMBERS)==len(set(SUCCESS_MEMBERS))==48 and 'members.json'in SUCCESS_MEMBERS,'fixed48 post schema')
    allowed=set(SUCCESS_MEMBERS)-{'members.json'}
    require(len(allowed)==47 and type(passed)is bool and type(entries)is list and 0<len(entries)<=47,'bounded47 pre schema')
    require(all(type(row)is dict and set(row)==set(METADATA_TYPES)and
            all(type(row[k])is kind for k,kind in METADATA_TYPES.items())for row in entries),'exact metadata row types')
    sizes={row['name']:row['bytes']for row in entries}
    require(len(sizes)==len(entries)and 'result.json'in sizes and set(sizes)<=allowed and
            (not passed or set(sizes)==allowed),'closed success/diagnostic inventory')
    require(all(row['regular']and not row['symlink']and 0<row['bytes']<=67108864 for row in entries)and
            sum(sizes.values())<=134217728,'unchanged file/total bounds')
    return sizes

stack_once=bind(retained.stack_once,{**retained.stack_once.__globals__,'_STACK':{}})
stream_candidate=SimpleNamespace(**{**vars(retained.stream_candidate),'verify_stack_evidence':stack_once})
_base_frame=bind(frame_core.own_frame,{**frame_core.own_frame.__globals__,'ROOTS':NAMED})
_frame_env={**frame_forms.own_frame.__globals__,'NAMED':NAMED,'retained':SimpleNamespace(own_frame=_base_frame)}
own_frame=bind(frame_forms.own_frame,_frame_env)

def signed(value, bits):
    return value-(1 << bits) if value & (1 << (bits-1)) else value

def instructions(text, record):
    rows = []
    for line in text.splitlines():
        match = re.fullmatch(r'\s*([0-9a-f]+):\s+([0-9a-f]{8})\s+([a-z0-9.]+)\s*(.*?)\s*', line)
        if match:
            rows.append((int(match[1], 16), int(match[2], 16), match[3], re.sub(r'\s+', '', match[4].split('//')[0])))
    require(rows and [r[0] for r in rows] == list(range(record['address'], record['address']+record['bytes'], 4)), 'complete exact instruction extent')
    return rows

def successors(rows, index):
    address, word, op, args = rows[index]
    end = rows[0][0]+4*len(rows)
    if op == 'ret':
        require(word == 0xd65f03c0 and args in ('', 'x30'), 'ordinary terminal RET')
        return []
    if op == 'bl':
        require(word & 0xfc000000 == 0x94000000, 'direct BL encoding')
        target = address+4*signed(word & 0x3ffffff, 26)
        require(args.split('<')[0] == format(target, 'x'), 'BL text/encoding target')
        targets = [address+4]
    elif op == 'b' or op.startswith('b.') or op in ('cbz', 'cbnz', 'tbz', 'tbnz'):
        if op == 'b':
            require(word & 0xfc000000 == 0x14000000, 'direct B encoding')
            target = address+4*signed(word & 0x3ffffff, 26)
        elif op.startswith('b.'):
            require(word & 0xff000010 == 0x54000000, 'conditional branch encoding')
            target = address+4*signed((word >> 5) & 0x7ffff, 19)
        elif op in ('cbz', 'cbnz'):
            require(word & 0x7e000000 == 0x34000000, 'compare branch encoding')
            target = address+4*signed((word >> 5) & 0x7ffff, 19)
        else:
            require(word & 0x7e000000 == 0x36000000, 'test branch encoding')
            target = address+4*signed((word >> 5) & 0x3fff, 14)
        require(args.rsplit(',', 1)[-1].split('<')[0] == format(target, 'x'), 'branch text/encoding target')
        targets = [target] if op == 'b' else [address+4, target]
    else:
        require(op not in ('br', 'blr', 'eret', 'drps'), 'unknown control transfer remains unclosed')
        targets = [address+4]
    require(all(rows[0][0] <= a < end and a % 4 == 0 for a in targets), 'selected local CFG targets only')
    return [(a-rows[0][0])//4 for a in targets]

def merge(states, index, state, pending):
    if index in states:
        require(states[index] == state, 'compatible current SP/FP state merge')
    else:
        states[index] = state
        pending.append(index)

def fp_address(row, sp, fp):
    address, word, op, args = row
    match = re.fullmatch(r'x([0-9]|1[0-9]|2[0-8]),x29,#(0x[0-9a-f]+|[0-9]+)', args)
    require(op == 'sub' and match is not None, 'only selected 64-bit GPR SUB from FP')
    destination, amount = int(match[1]), int(match[2], 0)
    require(amount in (4, 20) and word == 0xd1000000 | (amount << 10) | (29 << 5) | destination,
            'exact unshifted64 SUB opcode/immediate/destination')
    require(type(sp) is type(fp) is int and -144 <= sp < 0 and sp <= fp-amount < 0, 'known FP/result inside live own frame')
    return dict(address=address, register='x'+str(destination), immediate=amount, SP_offset=sp, FP_offset=fp,
                formed_entry_SP_offset=fp-amount, live_frame_interval=[sp, 0])

def frame_states(rows, frame, *, selected_fp=False):
    states = {0: (0, None)}
    pending = deque([0])
    samples = {}
    peak = returns = 0
    while pending:
        index = pending.popleft()
        sp, fp = states[index]
        address, word, op, args = rows[index]
        math = re.fullmatch(r'(sp|x29),sp,#(0x[0-9a-f]+|[0-9]+)', args) if op in ('add', 'sub') else None
        access = re.fullmatch(r'(.+),\[(sp|x29)(?:,#(-?(?:0x[0-9a-f]+|[0-9]+)))?\](!)?(?:,#(-?(?:0x[0-9a-f]+|[0-9]+)))?', args)
        if math:
            amount = int(math[2], 0)
            destination = 31 if math[1] == 'sp' else 29
            require(amount <= 4095 and word == (0x91000000 if op == 'add' else 0xd1000000) | (amount << 10) | (31 << 5) | destination,
                    'exact SP/FP allocation encoding')
            if destination == 31:
                sp += amount if op == 'add' else -amount
            else:
                fp = sp+(amount if op == 'add' else -amount)
        elif op == 'mov' and args == 'x29,sp':
            require(word == 0x910003fd, 'exact FP establishment')
            fp = sp
        elif selected_fp and op == 'sub' and ',x29,' in args:
            samples[address] = fp_address(rows[index], sp, fp)
        elif access:
            require(op in ('ldp', 'stp', 'ldr', 'str', 'ldur', 'stur'), 'known bounded stack access form')
            registers = access[1].split(',')
            require(all(re.fullmatch(r'[xw](?:[0-9]|[12][0-9]|30|zr)', reg) for reg in registers), 'stack access GPR width')
            width = sum(8 if reg.startswith('x') else 4 for reg in registers)
            offset = int(access[3], 0) if access[3] else 0
            if access[4]:
                sp += offset
                offset = 0
            origin = sp if access[2] == 'sp' else fp
            require(origin is not None and sp <= origin+offset < origin+offset+width <= 0, 'stack access inside current allocation')
            if op.startswith('ld') and 'x29' in registers:
                fp = None
            sp += int(access[5], 0) if access[5] else 0
        elif op == 'add' and re.fullmatch(r'x(?:[0-9]|1[0-9]|2[0-8]),sp,#(?:0x[0-9a-f]+|[0-9]+)', args):
            destination, _, immediate = args.split(',')
            amount = int(immediate[1:], 0)
            require(word == 0x91000000 | (amount << 10) | (31 << 5) | int(destination[1:]) and 0 <= amount < -sp,
                    'ordinary existing SP address inside allocation')
        else:
            require(not re.search(r'\b(?:sp|wsp|x29|w29|fp)\b', args), 'unrecognized SP/FP effect remains refused')
        require(-frame <= sp <= 0, 'current static frame bound')
        peak = max(peak, -sp)
        if op == 'ret':
            require(sp == 0, 'balanced caller return')
            returns += 1
        for target in successors(rows, index):
            merge(states, target, (sp, fp), pending)
    require(returns > 0 and peak == frame, 'actual frame peak and reachable return')
    return states, [samples[k] for k in sorted(samples)]

def object_join(raw, record, target, frame):
    item = raw['objects'][target]
    rows = re.findall(r'^\s*\d+:\s+([0-9a-f]+)\s+(\d+)\s+FUNC\s+(LOCAL|GLOBAL)\s+DEFAULT\s+(\d+)\s+(\S+)\s*$', item['elf'], re.M)
    matches = [(int(a, 16), int(size), binding, int(section)) for a, size, binding, section, name in rows if name == record['name']]
    require(len(matches) == 1 and matches[0][1] == record['bytes'] and
            matches[0][2] == ('LOCAL' if record['kind'] == 't' else 'GLOBAL'), 'exact TU local/global ELF extent')
    usage = re.findall(r'^(.+):\d+:'+re.escape(record['name'])+r'\t(\d+)\tstatic\s*$', item['usage'], re.M)
    require(len(usage) == 1 and int(usage[0][1]) == frame and target.replace('.o', '.c') in usage[0][0] and
            target in item['command'] and target.replace('.o', '.c') in item['command'], 'same compiler TU and actual static usage')
    return dict(TU=target, object_sha256=item['object_sha256'], section=matches[0][3], object_address=matches[0][0],
                delta=record['address']-matches[0][0], static_SU_bytes=frame, linked_ordinal=record['ordinal'])


INIT_WORDS=(0xa9444ff4,0xa94357f6,0xa9425ff8,0xf9400bf9,0xd65f03c0)
SAVE_WORDS=(0xa9016ffc,0x910003fd,0xa90267fa,0xa9035ff8,0xa90457f6,0xa9054ff4,0xd65f03c0)
RESTORE_WORDS=(0xa9454ff4,0xa94457f6,0xa9435ff8,0xa94267fa,0xa9416ffc,0xd65f03c0)

def same_context(provenance, callers, target, frame):
    require(provenance['TU']==target and provenance['static_SU_bytes']==0 and callers and
        all(c['provenance']['TU']==target and c['provenance']['object_sha256']==provenance['object_sha256'] and
            c['provenance']['section']==provenance['section'] and c['provenance']['delta']==provenance['delta'] and
            c['provenance']['static_SU_bytes']==c['frame']==frame for c in callers),'fresh contextual TU/section/delta/SU/object join')

def direct_call(row, target):
    address,word,op,args=row
    require(op=='bl' and word&0xfc000000==0x94000000 and
        address+4*signed(word&0x3ffffff,26)==target and args.split('<')[0]==format(target,'x'),'exact fresh contextual BL')

def init_restore(helper, helper_rows, callers, incoming, provenance):
    require(tuple(w for _,w,_,_ in helper_rows)==INIT_WORDS and helper['bytes']==20,'fixed init saved-slot reads and RET')
    same_context(provenance,callers,OWNER_TARGET,80)
    require(sorted(c['name'] for c in callers)==['n217_page_io','n285_readback_pages'] and len(incoming)==2 and
        sorted(n for n,_,op in incoming if op=='bl')==['n217_page_io','n285_readback_pages'],'only both selected init incoming contexts')
    prefix=(0xa9bb7bfd,0xf9000bf9,0x910003fd,0xa9025ff8,0xa90357f6,0xa9044ff4)
    for caller in callers:
        rows=caller['rows'];call=next(a for n,a,_ in incoming if n==caller['name']);at=next(i for i,row in enumerate(rows) if row[0]==call)
        require(tuple(w for _,w,_,_ in rows[:6])==prefix and tuple(w for _,w,_,_ in rows[at+1:])==(0xa8c57bfd,0xd65f03c0),'actual save80 and FP/LR pop80 suffix')
        direct_call(rows[at],helper['address'])
        require([i for i,row in enumerate(rows) if row[2]=='ret']==[at+2] and
            all(not row[2].startswith(('st','cas','swp','ldadd','ldclr','ldeor','ldset')) for row in rows[6:]),'sole init return and no saved-slot overwrite')
        states,_=frame_states(rows,80);require(states[at]==(-80,-80),'actual live init caller80')
        for i in states:
            for target in successors(rows,i):
                require(target not in (at+1,at+2) or target==i+1,'no init restore bypass')
                require(i<6 or target>=6,'no reentry into init saves')
    return dict(own_peak_bytes=0,neutral_outlined=False,standalone_leaf=False,contextual_caller_frame=True,
        helper_SP_change=0,caller_frame_bytes=80,saved_SP_intervals=[[16,24],[32,48],[48,64],[64,80]],
        original_FP_LR_restored_by_caller=True,selected_incoming=incoming,provenance=provenance,
        normal_ABI_call_return_assumed=True,callee_peaks_included=False)

def validator_pair(caller, save, restore, incoming, provenance):
    same_context(provenance['save'],[caller],'arch/arm64/mm/v230_runtime_relocation.o',528)
    same_context(provenance['restore'],[caller],'arch/arm64/mm/v230_runtime_relocation.o',528)
    require(tuple(w for _,w,_,_ in save['rows'])==SAVE_WORDS and
        tuple(w for _,w,_,_ in restore['rows'])==RESTORE_WORDS,'exact contextual save/FP-set and restore words')
    rows=caller['rows'];require(caller['name']=='adt_node' and rows[0][1]==0xa9ba7bfd and rows[2][1]==0xd106c3ff,'caller save96 and local432')
    require(len(incoming['save'])==len(incoming['restore'])==1 and
        incoming['save'][0]==('adt_node',rows[1][0],'bl'),'only selected adt save incoming edge')
    at=next(i for i,row in enumerate(rows) if row[0]==incoming['restore'][0][1])
    require(incoming['restore']==[('adt_node',rows[at][0],'bl')] and
        rows[at-1][1]==0x9106c3ff and tuple(w for _,w,_,_ in rows[at+1:at+3])==(0xa8c67bfd,0xd65f03c0),'dealloc432 and final FP/LR pop96')
    direct_call(rows[1],save['record']['address']);direct_call(rows[at],restore['record']['address'])
    states={0:(0,None)};pending=deque([0]);returns=0
    while pending:
        i=pending.popleft();sp,fp=states[i];address,word,op,args=rows[i]
        if i==0:sp=-96
        elif i==1:require(sp==-96 and fp is None,'save helper entry caller96');fp=-96
        elif i==2:require(sp==fp==-96,'local allocation follows save helper');sp-=432
        elif i==at-1:require(sp==-528 and fp==-96,'live local432 before restore');sp+=432
        elif i==at:require(sp==fp==-96,'restore helper entry caller96')
        elif i==at+1:require(sp==-96,'pop96 live caller');sp=0;fp=None
        else:
            require(not (op in ('add','sub','mov') and args.split(',')[0] in ('sp','wsp','x29','w29')) and
                not ('[sp' in args and ('!' in args or '],#' in args)),'no unaccounted adt SP/FP mutation')
        if op=='ret':require(i==at+2 and sp==0,'only joined adt return');returns+=1
        for target in successors(rows,i):
            require((target not in (1,2,at,at+1,at+2) or target==i+1) and (i<3 or target>=3),'no context reentry or restore bypass')
            merge(states,target,(sp,fp),pending)
    require(returns==1,'reachable joined adt return')
    # Ordinary pointer stores and recursion remain outside this helper-access certificate.
    return {role:dict(own_peak_bytes=0,neutral_outlined=False,standalone_leaf=False,contextual_caller_frame=True,
        helper_SP_change=0,caller='adt_node',caller_frame_bytes=528,caller_SP_offset=-96,
        helper_FP_effect='set-caller-SP' if role=='save' else 'unchanged',
        saved_SP_intervals=[[16,32],[32,48],[48,64],[64,80],[80,96]],
        selected_incoming=incoming[role],provenance=provenance[role],normal_ABI_call_return_assumed=True,
        saved_slot_integrity_proven=False,recursive_validator_closed=False,callee_peaks_included=False) for role in ('save','restore')}

def context_inputs(raw):
    bodies={k:instructions(raw['bodies'][k],record) for k,record in raw['records'].items()}
    def named(name,target,frame):
        found=[(k,v) for k,v in raw['records'].items() if v['name']==name];require(len(found)==1,'unique named contextual caller')
        key,record=found[0]
        return dict(name=name,frame=frame,rows=bodies[key],provenance=object_join(raw,record,target,frame))
    def helper(words,target):
        found=[(k,v) for k,v in raw['records'].items() if re.fullmatch(r'OUTLINED_FUNCTION_\d+',v['name']) and tuple(row[1] for row in bodies[k])==words]
        require(len(found)==1,'unique fresh exact helper shape');key,record=found[0]
        joined=object_join(raw,record,target,0);incoming=[]
        for ident,rows in bodies.items():
            for address,word,op,args in rows:
                if op in ('bl','b') and word&0x7c000000==0x14000000 and address+4*signed(word&0x3ffffff,26)==record['address']:
                    direct_call((address,word,op,args),record['address']);incoming.append((raw['records'][ident]['name'],address,op))
        return key,dict(record=record,rows=bodies[key]),joined,incoming
    init,ih,ip,ii=helper(INIT_WORDS,OWNER_TARGET)
    callers=[named(n,OWNER_TARGET,80) for n in ('n285_readback_pages','n217_page_io')]
    certificates={init:init_restore(ih['record'],ih['rows'],callers,ii,ip)}
    save,sh,sp,si=helper(SAVE_WORDS,'arch/arm64/mm/v230_runtime_relocation.o')
    restore,rh,rp,ri=helper(RESTORE_WORDS,'arch/arm64/mm/v230_runtime_relocation.o')
    pair=validator_pair(named('adt_node','arch/arm64/mm/v230_runtime_relocation.o',528),sh,rh,
        dict(save=si,restore=ri),dict(save=sp,restore=rp))
    certificates.update({save:pair['save'],restore:pair['restore']});return certificates

def metadata_frame(name,rows,external,frame,outlined,words):
    if name!='n285_prepare_metadata':return own_frame(name,rows,external,frame,outlined,words)
    require(not outlined and frame==144,'selected production metadata frame144')
    exact=[(a,words[a],op,re.sub(r'\s+','',args)) for a,op,args in rows]
    states,samples=frame_states(exact,144,selected_fp=True)
    require(samples and {s['immediate'] for s in samples}=={4,20} and
        all((s['SP_offset'],s['FP_offset'])==(-144,-96) for s in samples),'only declared production FP forms')
    by_address={s['address']:s for s in samples};normalized=[]
    for address,op,args in rows:
        if address in by_address:
            sample=by_address[address];args=sample['register']+', sp, #'+str(sample['formed_entry_SP_offset']-sample['SP_offset']);op='add'
        normalized.append((address,op,args))
    value=own_frame(name,normalized,external,frame,outlined,words);value['FP_address_samples']=samples;return value


def verify_metadata(raw,linked):
    require(raw['schema']=='note10-v286-CPU-metadata-raw-v1'and raw['complete']is True,'complete new metadata capture')
    require(raw['profile'].get('LTO_NONE')=='y'and raw['profile'].get('LTO','n')=='n','actual LTO_NONE')
    table=seal_base.scoped.reader.linked_symbols(linked)
    require(raw['linked_nm_sha256']==sha(linked.encode())and len(NAMED)==len(set(NAMED))==49,'exact linked input/domain')
    require(set(raw['objects'])==set(TARGETS)and set(raw['records'])==set(raw['bodies'])and
            0<len(raw['bodies'])<=79,'bounded object/body inventory')
    contexts={}
    for target,roots in TARGETS.items():
        item=raw['objects'][target]
        contexts[target]=seal_base.provenance(target,roots,item,table)
    item=raw['objects'][NEW_TARGET]
    abi=seal_base.scoped.object_symbols(item['nm'])
    require(all(len(abi[n])==1 and abi[n][0][1]=='A'and int(abi[n][0][2],16)==v for n,v in ABI.items()),'actual workspace ABI')
    obj=retained._ENV['metadata_object_evidence'](item['elf'],item['usage'])
    require(obj['writable_section_bytes']==0,'new metadata TU writable0')
    contexts_by_extent=context_inputs(raw)
    frames={};frontiers=[];outlined=0;core_sum=0;metadata_callers=seal_callers=0
    for ident,body in raw['bodies'].items():
        record=raw['records'][ident];name=record['name'];outline=bool(re.fullmatch(r'OUTLINED_FUNCTION_\d+',name))
        require(name in NAMED or outline,'fixed named/outline domain')
        require(sum(record==dict(name=name,**row,offset=0)for row in table.get(name,()))==1,
                'exact linked record including local ordinal and zero offset')
        symbol=seal_base.scoped.symbol_extent(table,name,record,outline)
        require(ident==format(symbol['address'],'016x')+':'+str(symbol['bytes']),'exact selected extent')
        joined=[]
        for target,(context,roots,reader)in contexts.items():
            try:
                item=reader(context,record,outline);index=item['section_index']
                require(index in context['deltas']and item['object_address']+context['deltas'][index]==record['address'],
                        'same actual source section/linked entry')
                joined.append(item)
            except ValueError:pass
        require(len(joined)==1,'unique source/TU/ELF/SU provenance')
        proof=seal_base.scoped.scoped_transfers(body,symbol,table)
        require(not proof['unknown_control_transfers']or name in BOUNDARY_CALLERS,'no unknown new-core transfers')
        if proof['unknown_control_transfers']:
            frontiers.append(dict(caller=name,unknown_control_transfers=proof['unknown_control_transfers'],peak_bytes=None))
        certificate=None
        # New core only. Lock/owner/old recursive validator frontiers stay unknown.
        if name in NEW_NAMES and name!='n285_snapshot_of_locked':
            rows=seal_base.scoped.flow.parse_body(body,proof)
            external={e['address']:'captured-callee-boundary'for e in proof['external_transfers']}
            certificate=metadata_frame(name,rows,external,joined[0]['frame']['bytes'],outline,
                                  frame_forms.instruction_words(body))
            core_sum+=certificate['own_peak_bytes']
        if outline:
            outlined+=1
            require(outlined<=30,'strict neutral outline cap')
            if ident in contexts_by_extent:
                certificate=contexts_by_extent[ident]
                require(certificate['neutral_outlined'] is False and certificate['standalone_leaf'] is False,
                    'contextual helpers remain non-neutral borrowed-frame certificates')
            else:
                neutral=seal_base.scoped.own_frame(name,seal_base.scoped.flow.parse_body(body,proof),
                    {e['address']:'exact-boundary'for e in proof['external_transfers']},0,True)
                require(neutral['neutral_outlined'] is True,'other selected helpers strictly neutral')
        for edge in proof['external_transfers']:
            records=edge['resolved_records']
            require(edge['mnemonic']in('bl','b')and not edge['unresolved']and records and
                    all(r['offset']==0 for r in records),'direct exact selected edge')
            targets={(r['address'],r['bytes'])for r in records}
            require(len(targets)==1,'unambiguous edge extent')
            if name=='n226_ingest_prepared_locked':
                if any(r['name']=='n285_prepare_metadata'for r in records):metadata_callers+=1
                if any(r['name']=='n278_seal_once'for r in records):seal_callers+=1
            target=next(iter(targets));key=format(target[0],'016x')+':'+str(target[1])
            if key not in raw['bodies']:
                require(name in BOUNDARY_CALLERS or all(r['name']in('memcpy','__memcpy','__pi_memcpy',
                    'memset','__memset','__pi_memset','memcmp','__pi_memcmp')for r in records),'declared source-owned boundary')
                frontiers.append(dict(caller=name,edge=edge,peak_bytes=None))
        frames[ident]=dict(name=name,source=joined[0],frame_certificate=certificate,edges=proof['external_transfers'])
    require(0<core_sum<=8192 and outlined<=30 and metadata_callers==seal_callers==1,
            'new core frames and exact actual owner callsites')
    value=dict(schema='note10-v286-CPU-metadata-target-v1',**{k:raw[k]for k in ('source_head','run_id','build_evidence_id','source_sha256')},
        ABI=ABI,named_cap=49,outlined_cap=30,aggregate_cap=79,selected_extents=len(frames),outlined_extents=outlined,
        selected_metadata_core_frame_proven=True,selected_metadata_core_static_sum=core_sum,frames=frames,
        uncertified_new_boundary_functions=['n285_snapshot_of_locked'],
        explicit_unclosed_boundaries=frontiers,contextual_helpers=contexts_by_extent,recursive_validator_closed=False,
        caller_qualified=False,independent_return_qualified=False,frontdoor_whole_stack_closed=False,whole_stack_bound_proven=False,
        seal_after_readback=True,adapter_record_installed=False,new_BSS_bytes=0,new_pool_bytes=0,
        same_boot_FDT_verified=False,observed_running_at_sample_only=True,complete_boot_tree=False,handoff_ready=False,
        actual_mandatory_metadata_callers=metadata_callers,actual_final_seal_callers=seal_callers,
        authoritative_ADT=False,hardware_ready=False,physical_ready=False,XNU=False)
    return json.loads(json.dumps(value))  # JSON report keys have the same type on reception.

def collect_binding(objects,out,result,run,linked):
    value=watchdog.collect_binding(objects,out,result,run,linked)
    binding=result['preparation']['watchdog_binding']['current_cpu_metadata']
    raw=dict(schema='note10-v286-CPU-metadata-raw-v1',**{k:result[k]for k in ('source_head','run_id','build_evidence_id','source_sha256')},
        complete=False,linked_nm_sha256=sha(linked.encode()),compiler_input_binding=binding,
        profile=result['effective_profile'],objects={},bodies={},records={},tools=[])
    def persist():
        require(len(json.dumps(raw).encode())<=16777216,'bounded metadata evidence');p.save(out/'cpu-metadata-evidence.json',raw)
    def capture(argv):
        done=subprocess.run(list(map(str,argv)),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=120)
        raw['tools'].append(dict(argv=list(map(str,argv)),returncode=done.returncode,stdout_sha256=sha(done.stdout)));persist()
        require(done.returncode==0 and 0<len(done.stdout)<=8388608 and len(done.stderr)<=65536,'bounded metadata tool')
        return done.stdout.decode()
    try:
        table=seal_base.scoped.reader.linked_symbols(linked);contexts={}
        for target,roots in TARGETS.items():
            rel=Path(target);command=p.ordinary(objects/rel.with_name('.'+rel.name+'.cmd'))
            usage=p.ordinary(objects/stream_candidate.compiler_stack_path(command,target)).decode()
            item=dict(command=command.decode(),command_sha256=sha(command),usage=usage,usage_sha256=sha(usage.encode()),
                nm=capture(['aarch64-linux-gnu-nm','--format=posix','--print-size',objects/target]),
                elf=capture(['aarch64-linux-gnu-readelf','--wide','--sections','--symbols',objects/target]),
                object_sha256=sha(p.ordinary(objects/target,67108864)))
            raw['objects'][target]=item;contexts[target]=seal_base.provenance(target,roots,item,table)
            if target in (NEW_TARGET,seal_base.SEAL_TARGET):
                stem='cpu-metadata-object'if target==NEW_TARGET else'seal-object'
                (out/(stem+'.o')).write_bytes(p.ordinary(objects/target,67108864))
                (out/(stem+'.cmd')).write_bytes(command);(out/(stem+'.su')).write_text(usage)
                (out/(stem+'-elf.log')).write_text(item['elf'])
        source=Path(contexts[OWNER_TARGET][0]['TU']['translation_unit']).parent
        require(sha(p.ordinary(source/'v226_source_stream_kernel.c'))==binding['owner_after_sha256']and
                sha(p.ordinary(source/'Makefile'))==binding['Kbuild_after_sha256'],'actual metadata owner/Kbuild source')
        for path,digest in binding['copied'].items():require(sha(p.ordinary(source/Path(path).name))==digest,'actual new compiler input')
        pending=deque()
        for name in ('n226_ingest_prepared_locked','n279_layout_witness','n285_prepare_metadata','n285_layout_witness'):
            require(name in table and len(table[name])==1,'unique public proof root')
            pending.append(dict(name=name,**table[name][0],offset=0))
        while pending:
            record=pending.popleft();name=record['name'];key=(record['address'],record['bytes']);ident=format(key[0],'016x')+':'+str(key[1])
            if ident in raw['bodies']:continue
            require(len(raw['bodies'])<79,'fixed aggregate capture79')
            symbol=seal_base.scoped.symbol_extent(table,name,record,bool(re.fullmatch(r'OUTLINED_FUNCTION_\d+',name)))
            text=capture(['aarch64-linux-gnu-objdump','-d','--disassemble-zeroes','--start-address='+hex(key[0]),'--stop-address='+hex(sum(key)),objects/'vmlinux'])
            raw['bodies'][ident]=text;raw['records'][ident]=record;persist()
            proof=seal_base.scoped.scoped_transfers(text,symbol,table)
            for edge in proof['external_transfers']:
                records=edge['resolved_records']
                if records and len({(r['address'],r['bytes'])for r in records})==1:
                    selected=[r for r in records if r['name']in NAMED or re.fullmatch(r'OUTLINED_FUNCTION_\d+',r['name'])]
                    if name=='n278_seal_once':continue  # Retained validator frontier, not an old proof replay.
                    if name=='n226_ingest_prepared_locked':selected=[r for r in selected if r['name']in
                        ('n285_snapshot_of_locked','n285_prepare_metadata','n278_seal_once')]
                    if selected:pending.append(selected[0])
        raw['complete']=True;persist()
        proof=verify_metadata(raw,linked);result['current_cpu_metadata_target']=proof
        result.update(metadata_runtime_callers=1,metadata_destination_writes=True,metadata_physical_authority=False,
            metadata_projection_revision='v285',frontdoor_whole_stack_closed=False,hardware_ready=False,physical_ready=False)
        result['metadata_projection_compile'].update(runtime_callers=1,destination_writes=True,
            synthetic_metadata_only=False,live_owner_verified=False)
        # Preserve the established member inventory with honest current source data,
        # not an old seal proof replay or a counterfeit closed-frontier certificate.
        p.save(out/'seal-evidence.json',dict(schema='note10-v286-seal-frontier-v1',**{k:raw[k]for k in
            ('source_head','run_id','build_evidence_id','source_sha256')},complete=True,frontier_closed=False,
            metadata_evidence_sha256=sha(p.ordinary(out/'cpu-metadata-evidence.json',16777216)),hardware_ready=False))
        result['current_owner_seal_target']=dict(schema='note10-v286-seal-order-PC-target-v1',seal_after_readback=True,
            source_coupled_N226_success=True,frontier_closed=False,whole_stack_bound_proven=False,hardware_ready=False)
        return value
    except BaseException as error:
        raw.update(complete=False,rejection=str(error)[:2048]);persist();raise

_ENV={**retained._ENV,**{n:globals()[n]for n in ('WORKFLOW','JOB','BUILD_SCHEMA','CONTEXT_SCHEMA','MANIFEST_SCHEMA',
    'SUCCESS_MEMBERS','source_pins','public_context','install_binding','collect_binding','stream_candidate')}}
run_build=retained._bind(retained.run_build,_ENV,{'note10/private/v283-ci-native-prepare':'note10/private/v286-ci-native-prepare',
    'v283':'v286','"-v283-seal-inventory"':'"-v286-contextual-validator"'})
_SEAL_ENV={**retained.seal.__globals__,**_ENV,'inventory_metadata':inventory_metadata}
seal=bind(retained.seal,_SEAL_ENV)
_ENV.update(run_build=run_build,seal=seal)
main=bind(retained.main,_ENV)

def audit_api():
    require(CAPTURE_SCHEMA==watchdog.CAPTURE_SCHEMA and TARGET_SCHEMA==watchdog.TARGET_SCHEMA and
            callable(source_pins)and callable(public_context)and callable(decode_binding),'actual retained consumer exports')
    require(run_build.__globals__['install_binding']is install_binding and
            run_build.__globals__['collect_binding']is collect_binding and
            main.__globals__['seal']is seal and seal.__globals__['inventory_metadata']is inventory_metadata,
            'actual fresh callback namespaces')

if __name__=='__main__':main()
