"""PC-only execution and independent bounded-data verification of production A64.

Unicorn imports are confined to execute_case. ELF/ABI/blob/checker helpers do
not execute target instructions and can be used by an independent artifact reader.
"""
import argparse
from email.parser import BytesParser
from email import policy
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import struct
import zlib

from relocation_trial_instructions import classify, ROW

ROOT=Path(__file__).resolve().parents[2]
PAGE=4096
IMAGE=19578880
OFFSET=0x1004000
AFFECTED=0x22b0000
MAX_DECODED=AFFECTED+PAGE
PAYLOAD_SHA='7a573eb6d2f5efc87bd5c85af130ea854eb4bad8370d17a4247e54f9593a836a'
WINDOW=0x40000000
BACKUP=0x50000000
REQUEST=0x30000000
ADT=0x30002000
RESULT=0x30004000
STACK=0x60000000
STACK_SIZE=0x20000
SP=STACK+STACK_SIZE-0x100
RETURN=0x70000000
COUNT_LIMIT=2_000_000_000
TIMEOUT_SECONDS=180
CASES=('actual-payload-success','actual-payload-transient-mismatch','insufficient-backup-capacity','window-backup-alias')
REQUEST_FIELDS=('physical_base','window_size','image_virtual','image_size','entry_virtual','adt','adt_length','synthetic_adt','command_line','command_length','reserved','occupied','reserved_count','occupied_count')
RESULT_FIELDS=('kernel_offset','image_size','affected_size','transient_compared','restored_compared','backward','reserved')
LEAF=struct.pack('<II32sI12s',1,0,b'name',12,b'device-tree\0')

def require(ok,message):
    if not ok:raise ValueError(message)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def sha(path):return digest(path.read_bytes())
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
def private_path(path):
    path=path.resolve();require(path.is_relative_to((ROOT/'note10/private').resolve()),'private output required');return path

def wheel_metadata(raw):
    """Parse RFC headers, accepting LF/CRLF without ambiguous duplicate fields."""
    message=BytesParser(policy=policy.default).parsebytes(raw,headersonly=True)
    require(not message.defects,'malformed wheel metadata headers')
    values={}
    for key,expected in (('Name','unicorn'),('Version','2.1.4')):
        headers=message.get_all(key,[])
        require(len(headers)==1 and not getattr(headers[0],'defects',()) and str(headers[0])==expected,'unique exact wheel metadata '+key)
        values[key]=str(headers[0])
    return values

def argument_values(name,abi):
    return [REQUEST,abi['request_size'],len(LEAF),0,0,0,WINDOW,AFFECTED,
      WINDOW if name==CASES[3] else BACKUP,AFFECTED-1 if name==CASES[2] else AFFECTED,RESULT,abi['result_size']]

def callee_seed():
    return {**{'x'+str(i):0x1937000000000000+i for i in range(19,30)},
      **{'d'+str(i):0x8837000000000000+i for i in range(8,16)}}

def entry_contract(symbols,entry,expected_entry='n10_rt_trial'):
    require(expected_entry in ('n10_rt_trial','n10_kernel_trial_adapter'),'caller-pinned supported entry required')
    require(expected_entry in symbols and symbols[expected_entry]['info']==18 and symbols[expected_entry]['flags']&4 and
      symbols[expected_entry]['size']>0 and entry==symbols[expected_entry]['value'],'ELF entry must match caller-pinned production symbol')

def report_entry_contract(report,expected_entry='n10_rt_trial'):
    require(expected_entry in ('n10_rt_trial','n10_kernel_trial_adapter') and
      report.get('entry_symbol','n10_rt_trial')==expected_entry,'report cannot select a different entry')

def elf_image(path,expected_entry='n10_rt_trial'):
    raw=path.read_bytes()
    require(len(raw)>=64 and raw[:6]==b'\x7fELF\x02\x01' and struct.unpack_from('<HH',raw,16)==(2,183),'closed AArch64 ET_EXEC required')
    entry,phoff,shoff=struct.unpack_from('<QQQ',raw,24)
    eh,phstride,phcount,shstride,shcount,shnames=struct.unpack_from('<HHHHHH',raw,52)
    require(eh==64 and phstride==56 and 0<phcount<32 and phoff+phstride*phcount<=len(raw) and
      shstride==64 and 0<shcount<4096 and shoff+shstride*shcount<=len(raw) and shnames<shcount,'ELF bounded tables')
    sections=[struct.unpack_from('<IIQQQQIIQQ',raw,shoff+i*64) for i in range(shcount)]
    def data(s):
        require(s[1]!=8 and s[4]+s[5]<=len(raw),'ELF section bytes bounds')
        return raw[s[4]:s[4]+s[5]]
    def string(table,at):
        end=table.find(b'\0',at);require(at<len(table) and end>=0,'ELF string bounds')
        return table[at:end].decode('ascii')
    require(sections[shnames][1]==3,'ELF section string table')
    symbols={};undefined=[]
    for section in sections:
        require(not (section[2]&1 and section[5]),'nonempty writable ELF state rejected')
        require(section[1] not in (6,11) and not (section[1] in (4,9) and section[5]),'dynamic/remaining relocation ELF rejected')
        if section[1]!=2:continue
        require(section[9]==24 and section[5]%24==0 and section[6]<shcount and sections[section[6]][1]==3,'ELF symbol table')
        strings=data(sections[section[6]])
        for at in range(0,section[5],24):
            name,info,visibility,index,value,size=struct.unpack_from('<IBBHQQ',data(section),at)
            name=string(strings,name)
            if not name:continue
            require('fixture' not in name.lower() and 'observe' not in name.lower(),'fixture hook symbol rejected')
            if index==0:undefined.append(name)
            if info&15 in (1,2):
                require(name not in symbols and 0<index<shcount,'unique defined object/function symbols required')
                s=sections[index];require(s[2]&2 and value>=s[3] and value+size<=s[3]+s[5],'symbol allocated section extent')
                symbols[name]={'value':value,'size':size,'info':info,'flags':s[2],
                  'bytes':data(s)[value-s[3]:value-s[3]+size]}
    require(not undefined,'no undefined target symbols')
    for name in ('n10_rt_trial','n10_rt_plan'):
        require(name in symbols and symbols[name]['info']==18 and symbols[name]['flags']&4 and symbols[name]['size']>0,'exact production function symbols')
    entry_contract(symbols,entry,expected_entry)
    segments=[];page_ranges=[]
    for i in range(phcount):
        kind,flags,offset,va,pa,filesz,memsz,align=struct.unpack_from('<IIQQQQQQ',raw,phoff+i*56)
        require(kind in (0,1),'only static load program headers supported')
        if kind!=1:continue
        require(flags in (4,5) and filesz<=memsz and memsz>0 and offset+filesz<=len(raw) and
          0x10000000<=va and va+memsz<=0x11000000 and align==PAGE and va%PAGE==offset%PAGE,'fixed separated readonly/RX ELF segment')
        start=va&~(PAGE-1);end=(va+memsz+PAGE-1)&~(PAGE-1)
        require(all(not(start<e and s<end) for s,e in page_ranges),'segment page permissions overlap')
        page_ranges.append((start,end));segments.append({'address':va,'start':start,'mapped_size':end-start,'filesz':filesz,'memsz':memsz,'flags':flags,'bytes':raw[offset:offset+filesz]})
    require(segments and any(s['flags']==5 and s['address']<=entry<s['address']+s['memsz'] for s in segments),'entry in RX load segment')
    for section in sections:
        if not section[2]&2 or not section[5]:continue
        owners=[s for s in segments if s['address']<=section[3] and section[3]+section[5]<=s['address']+s['filesz']]
        require(len(owners)==1,'allocated section must belong to one file-backed load segment')
        owner=owners[0];offset=section[3]-owner['address']
        require(data(section)==owner['bytes'][offset:offset+section[5]] and bool(section[2]&4)==bool(owner['flags']&1),'section/load bytes and RX versus NX permissions agree')
    oracle=symbols.get('n10_trial_abi')
    require(oracle and oracle['info']==17 and oracle['flags']&2 and not oracle['flags']&5,'readonly exact ABI oracle object')
    require(oracle['size']==(9+2*(len(REQUEST_FIELDS)+len(RESULT_FIELDS)))*8,'ABI oracle length')
    words=struct.unpack('<'+'Q'*(oracle['size']//8),oracle['bytes'])
    require(words[:2]==(0x4e31304142493031,1) and words[4:6]==(8,4),'target pointer/int ABI')
    require(words[6:9]==(0,(1<<64)-1,(1<<64)-5),'target signed status constants')
    abi={'request_size':words[2],'result_size':words[3],'pointer_size':words[4],'int_size':words[5],
      'status':{'OK':0,'INVALID':-1,'BUFFER':-5},'request':{},'result':{},'oracle_sha256':digest(oracle['bytes'])}
    at=9
    for group,names in (('request',REQUEST_FIELDS),('result',RESULT_FIELDS)):
        occupied=[]
        for name in names:
            offset,size=words[at:at+2];at+=2
            expected=4 if name in ('adt_length','synthetic_adt','command_length','reserved_count','occupied_count','backward','reserved') else 8
            # Request reserved is a pointer; result reserved is uint32_t.
            if group=='request' and name=='reserved':expected=8
            require(size==expected and offset+size<=abi[group+'_size'] and all(not(offset<e and s<offset+size) for s,e in occupied),'ABI field widths/extent/disjointness')
            occupied.append((offset,offset+size));abi[group][name]={'offset':offset,'size':size}
    require(0<abi['request_size']<=PAGE and 0<abi['result_size']<=PAGE,'bounded target structures')
    return {'entry':entry,'segments':segments,'symbols':symbols,'abi':abi,'sha256':digest(raw)}

def baseline(payload):
    require(len(payload)==IMAGE and digest(payload)==PAYLOAD_SHA,'exact real payload')
    return payload+b'\x69'*(AFFECTED-IMAGE)+b'\xa7'*PAGE

def put_field(raw,fields,name,value):
    field=fields[name];raw[field['offset']:field['offset']+field['size']]=int(value).to_bytes(field['size'],'little')

def blob_store(directory,raw):
    require(len(raw)<=MAX_DECODED,'observation maximum decoded size')
    h=digest(raw);packed=zlib.compress(raw,9);directory.mkdir(parents=True,exist_ok=True)
    name=h+'.zlib';path=directory/name
    if path.exists():require(path.read_bytes()==packed,'content-addressed observation collision')
    else:path.write_bytes(packed)
    return {'file':'blobs/'+name,'raw_size':len(raw),'raw_sha256':h,'packed_size':len(packed),'packed_sha256':digest(packed)}

def blob_read(root,description):
    require(set(description)=={'file','raw_size','raw_sha256','packed_size','packed_sha256'},'exact compressed observation schema')
    name=description['file'];h=description['raw_sha256'];size=description['raw_size']
    require(re.fullmatch('[0-9a-f]{64}',h) and name=='blobs/'+h+'.zlib' and type(size) is int and 0<=size<=MAX_DECODED,'bounded content-addressed observation')
    packed=(root/name).read_bytes()
    require(len(packed)==description['packed_size'] and len(packed)<=MAX_DECODED+1024*1024 and digest(packed)==description['packed_sha256'],'compressed observation bytes')
    decoder=zlib.decompressobj();raw=decoder.decompress(packed,MAX_DECODED+1)
    require(len(raw)==size and decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail and digest(raw)==h,'bounded exact zlib stream; trailing/unused bytes rejected')
    return raw

def verify_case(root,report,payload,abi):
    name=report['case'];require(name in CASES,'canonical case name')
    before=baseline(payload);admitted=name in CASES[:2];injected=name==CASES[1]
    initial_backup=b'\xa5'*AFFECTED+b'\xa7'*PAGE
    expected_observations={'window_before':before,'window_after':before,'backup_before':initial_backup,
      'backup_after':before if admitted else initial_backup,'result_before':b'\x5a'*PAGE}
    if name==CASES[3]:expected_observations.update({'alias_backup_argument_before':before,'alias_backup_argument_after':before})
    result=bytearray(b'\x5a'*PAGE)
    if name==CASES[0]:
        values={'kernel_offset':OFFSET,'image_size':IMAGE,'affected_size':AFFECTED,'transient_compared':IMAGE,'restored_compared':AFFECTED,'backward':1,'reserved':0}
        for key,value in values.items():put_field(result,abi['result'],key,value)
    expected_observations['result_after']=bytes(result)
    if admitted:
        expected_observations.update({'backup_first_tail_write':before,'backup_restore_start':before,
          'transient_before_injection':payload,'transient_restore_start':payload[:-1]+bytes([payload[-1]^0x80]) if injected else payload})
    require(set(report['observations'])==set(expected_observations),'exact required observation inventory')
    for key,expected in expected_observations.items():require(blob_read(root,report['observations'][key])==expected,'independent complete observed-byte comparison: '+key)
    expected_status=0 if name==CASES[0] else -1 if injected else -5
    require(report['status_signed_w0']==expected_status and report['return_pc']==RETURN and report['sp_after']==SP and
      report['callee_saved_before']==callee_seed() and report['callee_saved_after']==callee_seed() and
      report['arguments']==argument_values(name,abi) and report['sp_before']==SP,'target return/status/SP/callee-saved ABI')
    require(report['budget']=={'instruction_ceiling':COUNT_LIMIT,'timeout_seconds':TIMEOUT_SECONDS,'executed_instruction_count':None},'configured bounds only')
    state=report['observer']
    if admitted:
        require(state['transitions']==['first-tail-write','first-tail-read','restore-start'] and state['first_tail_write_address']==WINDOW+AFFECTED-1 and
          state['first_tail_write_size']==1 and state['tail_writes_before_restore']==64 and state['tail_reads_before_restore']==64 and
          state['restore_base_writes']==1 and state['injections']==int(injected),'selective hook ordering/actual negative return')
        spans=state['tail_read_spans'];tail=WINDOW+AFFECTED-64
        require(state['tail_read_events_before_restore']==len(spans) and 0<len(spans)<=64 and sum(size for address,size in spans)==64,'comparison tail byte/event accounting')
        seen=[]
        for address,size in spans:
            require(type(address) is int and type(size) is int and size>0 and tail<=address and address+size<=tail+64 and
              all(not(address<end and start<address+size) for start,end in seen),'unique in-range comparison tail read spans')
            seen.append((address,address+size))
    else:require(state['transitions']==[] and state['restore_base_writes']==0 and state['injections']==0 and
      state['tail_reads_before_restore']==0 and state['tail_read_events_before_restore']==0 and state['tail_read_spans']==[],
      'pre-admission case no mutation observer transitions')
    require(report['metadata_unchanged'] is True and report['invalid_accesses']==[] and report['hardware_verified'] is False,'readonly input and mapped-memory scope')
    return {d['file'] for d in report['observations'].values()}

def verify_report(root,report,payload,image,expected_profile=None,expected_entry='n10_rt_trial'):
    require(report['elf_sha256']==image['sha256'] and report['abi']==image['abi'],'actual executed ELF and ABI binding')
    entry_contract(image['symbols'],image['entry'],expected_entry)
    report_entry_contract(report,expected_entry)
    expected=[[s['start'],s['start']+s['mapped_size'],5 if s['flags']&1 else 1] for s in image['segments']]
    expected += [[REQUEST,REQUEST+PAGE,1],[ADT,ADT+PAGE,1],[WINDOW,WINDOW+MAX_DECODED,3],
      [BACKUP,BACKUP+MAX_DECODED,3],[RESULT,RESULT+PAGE,3],[STACK,STACK+STACK_SIZE,3],[RETURN,RETURN+PAGE,5]]
    require(report['model_mappings']==expected,'exact separated RX/RO/RW model mappings and guard extents')
    alias=report['case']==CASES[3]
    require(report['backup_mapping_role']==('unused-separate-mapping-sentinel' if alias else 'actual-backup-argument-mapping') and
      report['backup_argument']=={'address':WINDOW if alias else BACKUP,'role':'aliases-window' if alias else 'separate-backup'},'actual passed backup pointer and separate mapping evidence role')
    emulator=report['emulator']
    require(emulator['distribution']=='2.1.4' and emulator['runtime']=='2.1.4' and emulator['api'][:2]==[2,1] and emulator['libraries_sha256'],'pinned model dependency/API/library identity')
    if expected_profile is None:
        require(emulator['fp_advsimd_setting']=={'register':'CPACR_EL1','value':3<<20,'model_assumption_only':True} and
          'codegen_profile' not in report,'strict default v59 FP-enabled profile')
    else:
        from relocation_trial_kernel_profile import verify_profile_report
        verify_profile_report(report,expected_profile)
    require(report['production_aarch64_model_executed'] is True and report['physical_memory_or_hardware_accessed'] is False and
      report['xnu_executed'] is False and report['whole_ci_accepted'] is False,'PC-model execution scope')
    return verify_case(root,report,payload,image['abi'])

def execute_case(elf_path,payload_path,name,out,blob_directory,profile=None,entry_symbol='n10_rt_trial'):
    import unicorn as u
    from unicorn import arm64_const as arm
    require(importlib.metadata.version('unicorn')=='2.1.4' and u.__version__=='2.1.4' and tuple(u.uc_version()[:2])==(2,1),'pinned Unicorn distribution/runtime/API')
    require(not os.environ.get('UNICORN_LIB_PATH'),'custom Unicorn engine search path rejected')
    image=elf_image(elf_path,expected_entry=entry_symbol);abi=image['abi'];payload=payload_path.read_bytes();before=baseline(payload)
    uc=u.Uc(u.UC_ARCH_ARM64,u.UC_MODE_ARM)
    settings=None
    if profile is None:
        uc.reg_write(arm.UC_ARM64_REG_CPACR_EL1,3<<20)
    else:
        from relocation_trial_kernel_profile import kernel_profile
        settings=kernel_profile(profile)
        uc.reg_write(arm.UC_ARM64_REG_CPACR_EL1,0)
        cpacr_before=uc.reg_read(arm.UC_ARM64_REG_CPACR_EL1)
        require(cpacr_before==0,'actual FP-disabled model setup readback')
    mappings=[];mapping_permissions=[]
    def map_bytes(address,raw,size,permissions):
        require(address%PAGE==0 and size%PAGE==0 and len(raw)<=size,'model page mapping')
        require(not(address<0x90000000 and 0x80000000<address+size),'claimed physical range must remain unmapped')
        require(all(not(address<end and start<address+size) for start,end in mappings),'model mappings disjoint')
        uc.mem_map(address,size,u.UC_PROT_READ|u.UC_PROT_WRITE);uc.mem_write(address,raw);uc.mem_protect(address,size,permissions)
        mappings.append((address,address+size))
        mapping_permissions.append([address,address+size,permissions])
    for segment in image['segments']:
        prefix=b'\0'*(segment['address']-segment['start'])
        map_bytes(segment['start'],prefix+segment['bytes'],segment['mapped_size'],u.UC_PROT_READ|(u.UC_PROT_EXEC if segment['flags']&1 else 0))
    request=bytearray(PAGE)
    values={'physical_base':0x80000000,'window_size':0x10000000,'image_virtual':0xfffffff007004000,'image_size':IMAGE,
      'entry_virtual':0xfffffff007340490,'adt':ADT,'adt_length':len(LEAF),'synthetic_adt':1,
      'command_line':0,'command_length':0,'reserved':0,'occupied':0,'reserved_count':0,'occupied_count':0}
    for key,value in values.items():put_field(request,abi['request'],key,value)
    map_bytes(REQUEST,bytes(request),PAGE,u.UC_PROT_READ)
    map_bytes(ADT,LEAF,PAGE,u.UC_PROT_READ)
    map_bytes(WINDOW,before,len(before),u.UC_PROT_READ|u.UC_PROT_WRITE)
    initial_backup=b'\xa5'*AFFECTED+b'\xa7'*PAGE
    map_bytes(BACKUP,initial_backup,len(initial_backup),u.UC_PROT_READ|u.UC_PROT_WRITE)
    map_bytes(RESULT,b'\x5a'*PAGE,PAGE,u.UC_PROT_READ|u.UC_PROT_WRITE)
    map_bytes(STACK,b'\xcc'*STACK_SIZE,STACK_SIZE,u.UC_PROT_READ|u.UC_PROT_WRITE)
    map_bytes(RETURN,b'\0'*PAGE,PAGE,u.UC_PROT_READ|u.UC_PROT_EXEC)
    args=argument_values(name,abi)
    observations={};state={'transitions':[],'tail_writes_before_restore':0,'tail_reads_before_restore':0,
      'tail_read_events_before_restore':0,'tail_read_spans':[],
      'restore_base_writes':0,'injections':0,'ignored_unarmed_tail_reads':0,'ignored_restoration_tail_events':0}
    def observe(key,raw):
        require(key not in observations,'duplicate observation boundary');observations[key]=blob_store(blob_directory,raw)
    observe('window_before',before);observe('backup_before',initial_backup);observe('result_before',b'\x5a'*PAGE)
    if name==CASES[3]:observe('alias_backup_argument_before',bytes(uc.mem_read(args[8],MAX_DECODED)))
    errors=[];invalid=[]
    def guarded(fn):
        def callback(*args):
            try:return fn(*args)
            except Exception as error:errors.append(str(error));uc.emu_stop();return False
        return callback
    @guarded
    def tail_write(engine,access,address,size,value,user):
        if 'restore-start' in state['transitions']:state['ignored_restoration_tail_events']+=1;return
        require(not state['tail_reads_before_restore'],'tail write after transient comparison')
        if not state['tail_writes_before_restore']:
            require(address==WINDOW+AFFECTED-1 and size==1,'first backward target store must be final byte')
            backup=bytes(engine.mem_read(BACKUP,MAX_DECODED));require(backup==before,'full backup before first relocation store')
            observe('backup_first_tail_write',backup);state['first_tail_write_address']=address;state['first_tail_write_size']=size
            state['first_tail_write_pc']=engine.reg_read(arm.UC_ARM64_REG_PC)
            state['transitions'].append('first-tail-write')
        state['tail_writes_before_restore']+=size
    @guarded
    def tail_read(engine,access,address,size,value,user):
        if 'restore-start' in state['transitions']:state['ignored_restoration_tail_events']+=1;return
        if not state['tail_writes_before_restore']:state['ignored_unarmed_tail_reads']+=1;return
        tail=WINDOW+AFFECTED-64
        require(size>0 and tail<=address and address+size<=tail+64 and state['tail_reads_before_restore']+size<=64 and
          all(not(address<prior+count and prior<address+size) for prior,count in state['tail_read_spans']),'nonrepeated in-range comparison tail byte span')
        if not state['tail_reads_before_restore']:
            require(state['tail_writes_before_restore']==64,'complete high tail written before comparison')
            raw=bytes(engine.mem_read(WINDOW+OFFSET,IMAGE));require(raw==payload,'independent complete transient before injection')
            observe('transient_before_injection',raw);state['transitions'].append('first-tail-read')
            state['first_tail_read_pc']=engine.reg_read(arm.UC_ARM64_REG_PC)
            if name==CASES[1]:
                engine.mem_write(WINDOW+AFFECTED-1,bytes([payload[-1]^0x80]));state['injections']+=1
        state['tail_read_spans'].append([address,size]);state['tail_reads_before_restore']+=size
        state['tail_read_events_before_restore']+=1
    @guarded
    def restore_start(engine,access,address,size,value,user):
        require(address==WINDOW and state['transitions']==['first-tail-write','first-tail-read'],'unique common restoration boundary')
        require(state['tail_reads_before_restore']==64,'all 64 comparison tail bytes observed before restoration')
        state['restore_base_writes']+=1;require(state['restore_base_writes']==1,'duplicate restore boundary')
        state['restore_start_pc']=engine.reg_read(arm.UC_ARM64_REG_PC)
        backup=bytes(engine.mem_read(BACKUP,MAX_DECODED));require(backup==before,'backup complete before common restoration')
        transient=bytes(engine.mem_read(WINDOW+OFFSET,IMAGE))
        expected=payload[:-1]+bytes([payload[-1]^0x80]) if name==CASES[1] else payload
        require(transient==expected,'full transient at restoration start')
        observe('backup_restore_start',backup);observe('transient_restore_start',transient)
        state['transitions'].append('restore-start')
    def invalid_access(engine,access,address,size,value,user):
        invalid.append({'access':access,'address':address,'size':size});return False
    uc.hook_add(u.UC_HOOK_MEM_WRITE,tail_write,begin=WINDOW+AFFECTED-64,end=WINDOW+AFFECTED-1)
    uc.hook_add(u.UC_HOOK_MEM_READ,tail_read,begin=WINDOW+AFFECTED-64,end=WINDOW+AFFECTED-1)
    uc.hook_add(u.UC_HOOK_MEM_WRITE,restore_start,begin=WINDOW,end=WINDOW)
    uc.hook_add(u.UC_HOOK_MEM_INVALID,invalid_access)
    callee={}
    for i in range(19,30):
        value=0x1937000000000000+i;uc.reg_write(getattr(arm,'UC_ARM64_REG_X'+str(i)),value);callee['x'+str(i)]=value
    for i in range(8,16):
        value=0x8837000000000000+i;uc.reg_write(getattr(arm,'UC_ARM64_REG_D'+str(i)),value);callee['d'+str(i)]=value
    for i in range(8):uc.reg_write(getattr(arm,'UC_ARM64_REG_X'+str(i)),args[i])
    uc.mem_write(SP,struct.pack('<4Q',*args[8:]));uc.reg_write(arm.UC_ARM64_REG_SP,SP);uc.reg_write(arm.UC_ARM64_REG_LR,RETURN)
    partial={'case':name,'observer':state,'observations':observations,'configured_instruction_ceiling':COUNT_LIMIT,'configured_timeout_seconds':TIMEOUT_SECONDS,'accepted':False}
    try:uc.emu_start(image['entry'],RETURN,timeout=TIMEOUT_SECONDS*1_000_000,count=COUNT_LIMIT)
    except Exception as error:
        partial['error']=str(error);partial['invalid_accesses']=invalid;write(out/'failure.json',partial);raise
    if errors or invalid or uc.reg_read(arm.UC_ARM64_REG_PC)!=RETURN:
        partial['errors']=errors;partial['invalid_accesses']=invalid;partial['pc']=uc.reg_read(arm.UC_ARM64_REG_PC);write(out/'failure.json',partial)
        raise ValueError('target did not complete clean sentinel return within configured bounds')
    observe('window_after',bytes(uc.mem_read(WINDOW,MAX_DECODED)));observe('backup_after',bytes(uc.mem_read(BACKUP,MAX_DECODED)))
    observe('result_after',bytes(uc.mem_read(RESULT,PAGE)))
    if name==CASES[3]:observe('alias_backup_argument_after',bytes(uc.mem_read(args[8],MAX_DECODED)))
    after={key:uc.reg_read(getattr(arm,'UC_ARM64_REG_'+key.upper())) for key in callee}
    low=uc.reg_read(arm.UC_ARM64_REG_X0)&0xffffffff;status=low-(1<<32) if low&(1<<31) else low
    dist=importlib.metadata.distribution('unicorn')
    libraries={str(f):sha(Path(dist.locate_file(f))) for f in dist.files or [] if str(f).endswith(('.dll','.so','.dylib','.so.2'))}
    report={'schema':1,'case':name,'observations':observations,'observer':state,'status_signed_w0':status,
      'return_pc':uc.reg_read(arm.UC_ARM64_REG_PC),'sp_before':SP,'sp_after':uc.reg_read(arm.UC_ARM64_REG_SP),'arguments':args,
      'backup_mapping_role':'unused-separate-mapping-sentinel' if name==CASES[3] else 'actual-backup-argument-mapping',
      'backup_argument':{'address':args[8],'role':'aliases-window' if name==CASES[3] else 'separate-backup'},
      'callee_saved_before':callee,'callee_saved_after':after,'invalid_accesses':invalid,
      'metadata_unchanged':bytes(uc.mem_read(REQUEST,PAGE))==bytes(request) and bytes(uc.mem_read(ADT,len(LEAF)))==LEAF,
      'budget':{'instruction_ceiling':COUNT_LIMIT,'timeout_seconds':TIMEOUT_SECONDS,'executed_instruction_count':None},
      'emulator':{'distribution':importlib.metadata.version('unicorn'),'runtime':u.__version__,'api':list(u.uc_version()),'libraries_sha256':libraries,
        'fp_advsimd_setting':{'register':'CPACR_EL1','value':(3<<20) if settings is None else cpacr_before,'model_assumption_only':True}},
      'model_mappings':mapping_permissions,'hardware_verified':False,'physical_memory_or_hardware_accessed':False,'xnu_executed':False,'whole_ci_accepted':False,
      'production_aarch64_model_executed':True,'model_memory_only':True,'synthetic_adt':True,
      'observations_codec':{'format':'zlib','compression_level':9,'maximum_decoded_size':MAX_DECODED,'runtime_version':zlib.ZLIB_RUNTIME_VERSION},
      'elf_sha256':image['sha256'],'abi':abi}
    # Independent byte verification uses full observed blobs, not returned counts.
    if settings is not None:
        report['codegen_profile']=settings
        report['emulator']['cpacr_before']=cpacr_before
        report['emulator']['cpacr_after']=uc.reg_read(arm.UC_ARM64_REG_CPACR_EL1)
    if entry_symbol!='n10_rt_trial':report['entry_symbol']=entry_symbol
    write(out/'observed.json',report)
    verify_report(blob_directory.parent,report,payload,image,expected_profile=profile,expected_entry=entry_symbol);write(out/'result.json',report)
    return report

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--elf',type=Path,required=True);ap.add_argument('--payload',type=Path,required=True)
    ap.add_argument('--case',choices=CASES,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--blobs',type=Path,required=True)
    ap.add_argument('--profile',choices=['kernel-init-subset-v1'],default=None,help='Explicit kernel-option subset model; omitted preserves v59 FP-enabled contract')
    ap.add_argument('--entry-symbol',choices=['n10_rt_trial','n10_kernel_trial_adapter'],default='n10_rt_trial',help='Explicit caller-owned adapter entry; omitted preserves trial entry')
    a=ap.parse_args();out=private_path(a.output);blobs=private_path(a.blobs)
    require(blobs.parent==out.parent.parent,'shared blobs must belong to this model evidence root')
    out.mkdir(parents=True,exist_ok=False);execute_case(a.elf,a.payload,a.case,out,blobs,profile=a.profile,entry_symbol=a.entry_symbol)
