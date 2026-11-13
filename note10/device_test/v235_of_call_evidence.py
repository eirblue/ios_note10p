"""Fixed same-Image OF query evidence inventory; deliberately no lookup bound/hook."""
import hashlib
from pathlib import Path, PurePosixPath
import re
import shlex
import subprocess
import v226_source_stream as stream

SCHEMA='note10-v235-selected-OF-call-evidence-v1'
RAW_SCHEMA='note10-v235-selected-OF-call-raw-v1'
NEW_OBJECTS={
    'drivers/of/base.o':('of_get_cpu_node','of_find_node_by_type','of_n_addr_cells','of_find_property','of_get_property','of_get_parent','arch_find_n_match_cpu_physical_id','__of_find_all_nodes'),
    'arch/arm64/kernel/setup.o':('arch_match_cpu_phys_id',),
    'kernel/locking/spinlock.o':('_raw_spin_lock_irqsave','_raw_spin_unlock_irqrestore'),
}
REUSED_OBJECTS={'arch/arm64/mm/init.o':('n233_capture_cpu_node_consistency','n233_clear_consistency'),
    'lib/string.o':('strcasecmp',)}
OPTIONAL=('__of_find_property','__of_find_n_match_cpu_property')
MANDATORY=tuple(name for names in {**NEW_OBJECTS,**REUSED_OBJECTS}.values()for name in names)+('strcmp',)
SCHEDULER=('preempt_schedule','preempt_schedule_notrace')
MAX_FUNCTION_BYTES=8192
TEXT_CAP=2097152
BUNDLE_CAP=8388608
LIMITS=dict(whole_OF_scheduler_bound_proven=False,lookup_runtime_bound_proven=False,
    prelookup_guard_ready=False,runtime_hook_allowed=False,runtime_callers=0,hardware_authorized=False)
SOURCE_GUARDS={
    'include/linux/spinlock_api_smp.h':'e38b2efdb2b84888f2e204f524a30ccf4021e6561067c23c20da586511ab97f6',
    'include/linux/spinlock.h':'ea3a2447a9c005f9f05e20a12bfd5b0555f7298c3b386261fb980afe66b27d00',
    'kernel/locking/spinlock.c':'d4ce3d228f6fccdfd241dfe4ed23986c2ef94ffd9111341f25fb20502748214c',
    'include/linux/preempt.h':'386da1a2be5458d2a6e172286987ce9fe6e8383d50377ad42a220c7026c228af',
    'lib/string.c':'fc869eb46f5d63ce7c894f2a6b4ca3c996899a4241691373df81c5a0cf1a8ccb',
    'arch/arm64/include/asm/string.h':'b59fcb2650c3d683298c3c7543b98378a0f4f3bf8f77ccd1bc3e325c4050b748',
    'arch/arm64/lib/Makefile':'9e62504c654258403e7165e490e851cc4c5e1c74a44c66757da2aa8204950276',
}
CONFIG={'OF':'y','OF_DYNAMIC':'n','OF_OVERLAY':'n','ACPI':'n','SMP':'y','NR_CPUS':'8',
    'PREEMPT':'y','PREEMPT_COUNT':'y','DEBUG_PREEMPT':'n','UNINLINE_SPIN_UNLOCK':'y',
    'DEBUG_SPINLOCK':'n','DEBUG_LOCK_ALLOC':'n','PROVE_LOCKING':'n','DEBUG_ATOMIC_SLEEP':'y'}


def require(ok,message):
    if not ok:raise ValueError(message)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def translation_unit(command,target):
    usage=stream.compiler_stack_path(command,target)
    lines=command.decode().splitlines();key='source_'+target+' := '
    declarations=[line[len(key):]for line in lines if line.startswith(key)]
    require(len(declarations)==1,'one actual selected object source declaration required')
    source=declarations[0];path=PurePosixPath(source)
    require(path.is_absolute()and str(path)==source and '..'not in path.parts and
        source.endswith('/source/'+target[:-2]+'.c')and not any(c.isspace()for c in source),
        'literal canonical POSIX selected TU required')
    argv=shlex.split(lines[0][len('cmd_'+target+' := '):])
    require(argv[-1]==source and argv.count(source)==1,'source declaration and actual compile operand must agree')
    return dict(translation_unit=source,stack_relative=str(usage),command_sha256=sha(command))


def linked_symbols(raw):
    result={}
    for line in raw.splitlines():
        row=line.split()
        if len(row)!=4 or row[1]not in ('T','t','W','w'):continue
        require(row[0]not in result,'unique linked text symbol required')
        address,size=int(row[2],16),int(row[3],16)
        result[row[0]]=dict(kind=row[1],address=address,bytes=size)
    require(result,'actual same-vmlinux nm text required');return result


def extent(table,name):
    require(name in table,'missing selected linked function: '+name)
    row=table[name];start,size=row['address'],row['bytes']
    require(0<start<1<<64 and 0<size<=MAX_FUNCTION_BYTES and start%4==size%4==0 and start+size<1<<64,
        'bounded aligned same-ELF selected function required')
    aliases=sorted(n for n,r in table.items()if r['address']==start and r['bytes']==size)
    require(name in aliases and len(aliases)<=32,'bounded same-extent aliases required')
    return dict(symbol=name,address=start,bytes=size,aliases=aliases)


def command(vmlinux,symbol):
    image=str(vmlinux);path=PurePosixPath(image)
    require(path.is_absolute()and str(path)==image and '..'not in path.parts and path.name=='vmlinux',
        'canonical absolute same-vmlinux path required')
    require(type(symbol)is dict and set(symbol)=={'symbol','address','bytes','aliases'}and
        symbol['symbol']in (*MANDATORY,*OPTIONAL),'only fixed selected inventory may be disassembled')
    checked=extent({n:dict(address=symbol['address'],bytes=symbol['bytes'])for n in symbol['aliases']},symbol['symbol'])
    require(checked==symbol,'exact selected alias/extent record required')
    return ['aarch64-linux-gnu-objdump','-d','--disassemble-zeroes','--start-address='+hex(symbol['address']),
        '--stop-address='+hex(symbol['address']+symbol['bytes']),image]


def object_proof(target,item,names,table):
    require(set(item)=={'command','command_sha256','stack_usage','stack_sha256','stack_relative','elf_sections_and_symbols','elf_evidence_sha256'},
        'exact object text fields required')
    cmd=item['command'].encode();usage=item['stack_usage'];elf=item['elf_sections_and_symbols']
    require(sha(cmd)==item['command_sha256']and sha(usage.encode())==item['stack_sha256']and
        sha(elf.encode())==item['elf_evidence_sha256'],'selected object text hashes required')
    tu=translation_unit(cmd,target);require(tu['stack_relative']==item['stack_relative'],'actual compiler-derived SU required')
    frames=stream.frames(usage);sections={};functions={}
    for line in elf.splitlines():
        section=re.match(r'^\s*\[\s*(\d+)\]\s+(\S+)\s+\S+\s+[0-9a-fA-F]+\s+[0-9a-fA-F]+\s+[0-9a-fA-F]+\s+[0-9a-fA-F]+\s+([A-Z]+)\s+',line)
        if section:sections[section[1]]=(section[2],section[3])
        row=re.match(r'^\s*\d+:\s+([0-9a-fA-F]+)\s+(\d+|0x[0-9a-fA-F]+)\s+FUNC\s+(LOCAL|GLOBAL|WEAK)\s+DEFAULT\s+(\d+)\s+(\S+)\s*$',line)
        if row and row[5]in names:
            require(row[5]not in functions,'one selected object ELF function required');functions[row[5]]=row.groups()
    result={}
    for name in names:
        require(name in frames and name in functions,'actual selected SU/ELF function required: '+name)
        frame=frames[name];address,size,binding,index,_=functions[name]
        size=int(size,16 if size.startswith('0x')else 10)
        require(frame['source']==tu['translation_unit']and frame['kind']=='static'and 0<=frame['bytes']<=8192,
            'selected frame must be static in its declared TU: '+name)
        require(index in sections,'selected function section required');section,flags=sections[index]
        require(not section.startswith(('.init','.exit'))and'A'in flags and'X'in flags and'W'not in flags,
            'selected function must be non-init executable code')
        expected='WEAK'if name=='arch_find_n_match_cpu_physical_id'else'LOCAL'if table[name]['kind']=='t'else'GLOBAL'
        require(binding==expected and table[name]['bytes']==size>0,'object/linked size and source binding must agree: '+name)
        require(name!='arch_match_cpu_phys_id'or(target=='arch/arm64/kernel/setup.o'and binding=='GLOBAL'and table[name]['kind']=='T'),
            'ARM64 strong setup match body required; weak OF fallback is not selected')
        result[name]=dict(object=target,translation_unit=tu['translation_unit'],object_address=int(address,16),
            linked_address=table[name]['address'],bytes=size,binding=binding,section=section,frame_bytes=frame['bytes'],frame_kind='static')
    return result


def transfers(raw,symbol,table):
    labels=[];instructions=[]
    for line in raw.splitlines():
        label=re.fullmatch(r'\s*([0-9a-fA-F]+) <([^>]+)>:\s*',line)
        if label:labels.append((int(label[1],16),label[2]))
        if re.match(r'^\s*[0-9a-fA-F]+:',line):
            row=re.fullmatch(r'\s*([0-9a-fA-F]+):\s+[0-9a-fA-F]{8}\s+(.+)',line)
            require(row is not None,'every selected instruction must decode');instructions.append((int(row[1],16),row[2].lower()))
    require(len(labels)==1 and labels[0][0]==symbol['address']and labels[0][1]in symbol['aliases']and
        len(instructions)*4==symbol['bytes']and all(a==symbol['address']+4*i for i,(a,_)in enumerate(instructions)),
        'complete contiguous actual function extent and bound alias required')
    addresses={a for a,_ in instructions};edges=[];unknown=[];internal=0
    for address,text in instructions:
        text=text.split('//',1)[0].strip();parts=text.split(None,1);op=parts[0];operands=parts[1]if len(parts)==2 else''
        if op=='ret':
            if operands not in ('','x30'):unknown.append(dict(address=address,instruction=text))
            continue
        direct=op in ('bl','b','cbz','cbnz','tbz','tbnz')or re.fullmatch(r'b\.(eq|ne|cs|cc|hs|lo|mi|pl|vs|vc|hi|ls|ge|lt|gt|le|al|nv)',op)
        if direct:
            literal=re.sub(r'<[^>]+>','',operands).split(',')[-1].strip()
            require(re.fullmatch(r'(?:0x)?[0-9a-f]+',literal)is not None,'literal direct branch address required')
            target=int(literal,16)
            require(not(symbol['address']<=target<symbol['address']+symbol['bytes'])or target in addresses,
                'in-function branch target must be an actual instruction address')
            if target in addresses and op!='bl':internal+=1;continue
            resolved=sorted(n for n,r in table.items()if r['address']<=target<r['address']+r['bytes'])
            edges.append(dict(address=address,mnemonic=op,target=target,resolved_symbols=resolved,
                selected_target=any(n in (*MANDATORY,*OPTIONAL)for n in resolved),scheduler_boundary=any(n in SCHEDULER for n in resolved),
                unresolved=not bool(resolved)))
        elif op in ('br','blr','braa','brab','braaz','brabz','blraa','blrab','blraaz','blrabz','eret','eretaa','eretab','drps','svc','hvc','smc','brk','hlt','udf','dcps1','dcps2','dcps3')or op.startswith(('.','ret','b.','cb','tb'))or(op.startswith('b')and op not in ('bic','bics','bfi','bfxil')):
            unknown.append(dict(address=address,instruction=text))
    if instructions[-1][1].split(None,1)[0]not in ('ret','b','br'):unknown.append(dict(address=instructions[-1][0],instruction='extent fallthrough not closed'))
    return dict(symbol=symbol,instructions=len(instructions),internal_branches=internal,external_transfers=edges,
        unknown_control_transfers=unknown,disassembly_sha256=sha(raw.encode()),chain_bound_proven=False)


def verify(raw,stack_data):
    require(type(raw)is dict and set(raw)=={'schema','objects','linked_nm_sha256','assembly','tools'}and raw['schema']==RAW_SCHEMA,
        'exact selected raw bundle required')
    require(set(raw['objects'])==set(NEW_OBJECTS)and set(stack_data['objects'])>=set(REUSED_OBJECTS),'fixed object inventory required')
    nm=stack_data['linked_nm'];require(sha(nm.encode())==raw['linked_nm_sha256'],'same-vmlinux nm binding required')
    table=linked_symbols(nm);optional=[name for name in OPTIONAL if name in table]
    names=(*MANDATORY,*optional);require(set(raw['assembly'])==set(names),'exact mandatory/actually-linked optional inventory required')
    tools=raw['tools'];require(type(tools)is list and len(tools)==len(NEW_OBJECTS)+len(names),'fixed bounded tool inventory required')
    root=None
    for index,target in enumerate(NEW_OBJECTS):
        tool=tools[index];argv=tool.get('argv',[])
        require(len(argv)==5 and argv[:4]==['aarch64-linux-gnu-readelf','--wide','--sections','--symbols']and
            argv[-1].endswith('/'+target),'same-Image object tool argv required')
        candidate=argv[-1][:-len(target)-1];path=PurePosixPath(candidate)
        require(path.is_absolute()and str(path)==candidate and '..'not in path.parts and(root is None or candidate==root),'one canonical objects root required');root=candidate
        require(set(tool)=={'argv','returncode','stdout_sha256','stderr'}and tool['returncode']==0 and type(tool['stderr'])is str and
            tool['stdout_sha256']==sha(raw['objects'][target]['elf_sections_and_symbols'].encode()),'actual successful object stdout binding required')
    for index,name in enumerate(names,len(NEW_OBJECTS)):
        tool=tools[index]
        require(set(tool)=={'argv','returncode','stdout_sha256','stderr'}and tool['returncode']==0 and type(tool['stderr'])is str and
            tool['argv']==command(root+'/vmlinux',extent(table,name))and tool['stdout_sha256']==sha(raw['assembly'][name].encode()),
            'actual successful selected disassembly argv/stdout binding required')
    proofs={}
    for target,selected in {**NEW_OBJECTS,**REUSED_OBJECTS}.items():
        if target=='drivers/of/base.o':selected=(*selected,*optional)
        item=raw['objects'][target]if target in NEW_OBJECTS else stack_data['objects'][target]
        proofs.update(object_proof(target,item,selected,table))
    assembly={name:transfers(raw['assembly'][name],extent(table,name),table)for name in names}
    return dict(schema=SCHEMA,selected_function_count=len(names),object_provenance=proofs,assembly=assembly,
        optional_functions={name:('present'if name in optional else'absent_or_inlined_no_zero_frame_claim')for name in OPTIONAL},
        unexpanded_scheduler_boundaries=list(SCHEDULER),unexpanded_other_targets=sorted({n for row in assembly.values()for edge in row['external_transfers']for n in edge['resolved_symbols']if n not in names}),
        selected_frames_are_not_a_chain_sum=True,strcmp_frame_proven=False,**LIMITS)


def collect(objects,stack_data,nm,save):
    """Called once after Image; save raw evidence before any interpretation/gate."""
    objects=Path(objects);raw=dict(schema=RAW_SCHEMA,objects={},linked_nm_sha256=sha(nm.encode()),assembly={},tools=[])
    def capture(argv):
        done=subprocess.run(list(map(str,argv)),stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False,timeout=120)
        require(len(done.stdout)<=TEXT_CAP and len(done.stderr)<=65536,'bounded selected tool text required')
        row=dict(argv=list(map(str,argv)),returncode=done.returncode,stdout_sha256=sha(done.stdout),stderr=done.stderr.decode(errors='replace'))
        raw['tools'].append(row);save(raw)
        require(done.returncode==0,'selected evidence tool failed');return done.stdout.decode()
    save(raw)
    for target in NEW_OBJECTS:
        path=PurePosixPath(target);cmd=(objects/str(path.with_name('.'+path.name+'.cmd'))).read_bytes()
        require(len(cmd)<=TEXT_CAP,'bounded selected command required')
        raw['objects'][target]=dict(command=cmd.decode(),command_sha256=sha(cmd));save(raw)
        # Derive the actual compiler-output SU before reading it; no basename fallback.
        usage_relative=stream.compiler_stack_path(cmd,target);usage=(objects/usage_relative).read_text()
        require(len(usage.encode())<=TEXT_CAP,'bounded selected SU required')
        elf=capture(['aarch64-linux-gnu-readelf','--wide','--sections','--symbols',objects/target])
        raw['objects'][target]=dict(command=cmd.decode(),command_sha256=sha(cmd),stack_usage=usage,stack_sha256=sha(usage.encode()),
            stack_relative=str(usage_relative),elf_sections_and_symbols=elf,elf_evidence_sha256=sha(elf.encode()));save(raw)
    table=linked_symbols(nm)
    for name in (*MANDATORY,*(n for n in OPTIONAL if n in table)):
        raw['assembly'][name]=capture(command(objects/'vmlinux',extent(table,name)));save(raw)
    return verify(raw,dict(objects=stack_data['objects'],linked_nm=nm))
