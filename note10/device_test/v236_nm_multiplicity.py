"""236 preserve unselected nm multiplicity, keep selected provenance unambiguous."""
from pathlib import Path, PurePosixPath
import re
import subprocess
import v235_of_call_evidence as retained
require,sha=retained.require,retained.sha
stream=retained.stream
NEW_OBJECTS,REUSED_OBJECTS=retained.NEW_OBJECTS,retained.REUSED_OBJECTS
OPTIONAL,MANDATORY,SCHEDULER=retained.OPTIONAL,retained.MANDATORY,retained.SCHEDULER
MAX_FUNCTION_BYTES,TEXT_CAP,BUNDLE_CAP=retained.MAX_FUNCTION_BYTES,retained.TEXT_CAP,retained.BUNDLE_CAP
LIMITS,SOURCE_GUARDS,CONFIG=retained.LIMITS,retained.SOURCE_GUARDS,retained.CONFIG
translation_unit,command,object_proof=retained.translation_unit,retained.command,retained.object_proof
SCHEMA='note10-v236-selected-OF-call-evidence-v1'
RAW_SCHEMA='note10-v236-selected-OF-call-raw-v1'


def linked_symbols(raw):
    result={}
    for ordinal,line in enumerate(raw.splitlines()):
        row=line.split()
        if len(row)!=4 or row[1]not in ('T','t','W','w'):continue
        address,size=int(row[2],16),int(row[3],16)
        result.setdefault(row[0],[]).append(dict(kind=row[1],address=address,bytes=size,ordinal=ordinal))
    require(result,'actual same-vmlinux nm text required');return result


def selected_symbol(table,name):
    require(name in (*MANDATORY,*OPTIONAL)and name in table and len(table[name])==1,
        'exactly one selected linked definition required: '+name)
    return table[name][0]


def extent(table,name):
    row=selected_symbol(table,name);start,size=row['address'],row['bytes']
    require(0<start<1<<64 and 0<size<=MAX_FUNCTION_BYTES and start%4==size%4==0 and start+size<1<<64,
        'bounded aligned same-ELF selected function required')
    aliases=sorted({n for n,rows in table.items()for r in rows if r['address']==start and r['bytes']==size})
    require(name in aliases and len(aliases)<=32,'bounded same-extent aliases required')
    return dict(symbol=name,address=start,bytes=size,aliases=aliases)


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
            records=[dict(name=n,**r,offset=target-r['address'])for n,rows in table.items()for r in rows if r['address']<=target<r['address']+r['bytes']]
            resolved=sorted({r['name']for r in records})
            edges.append(dict(address=address,mnemonic=op,target=target,resolved_symbols=resolved,resolved_records=records,
                selected_target=any(n in (*MANDATORY,*OPTIONAL)for n in resolved),scheduler_boundary=any(n in SCHEDULER for n in resolved),
                unresolved=not bool(resolved)))
        elif op in ('br','blr','braa','brab','braaz','brabz','blraa','blrab','blraaz','blrabz','eret','eretaa','eretab','drps','svc','hvc','smc','brk','hlt','udf','dcps1','dcps2','dcps3')or op.startswith(('.','ret','b.','cb','tb'))or(op.startswith('b')and op not in ('bic','bics','bfi','bfxil')):
            unknown.append(dict(address=address,instruction=text))
    if instructions[-1][1].split(None,1)[0]not in ('ret','b','br'):unknown.append(dict(address=instructions[-1][0],instruction='extent fallthrough not closed'))
    aliases=[dict(name=n,**r)for n,rows in table.items()for r in rows if r['address']==symbol['address']and r['bytes']==symbol['bytes']]
    return dict(symbol=symbol,alias_records=aliases,instructions=len(instructions),internal_branches=internal,external_transfers=edges,
        unknown_control_transfers=unknown,disassembly_sha256=sha(raw.encode()),chain_bound_proven=False)


def verify(raw,stack_data):
    require(type(raw)is dict and set(raw)=={'schema','objects','linked_nm_sha256','assembly','tools'}and raw['schema']==RAW_SCHEMA,
        'exact selected raw bundle required')
    require(set(raw['objects'])==set(NEW_OBJECTS)and set(stack_data['objects'])>=set(REUSED_OBJECTS),'fixed object inventory required')
    nm=stack_data['linked_nm'];require(sha(nm.encode())==raw['linked_nm_sha256'],'same-vmlinux nm binding required')
    table=linked_symbols(nm);optional=[name for name in OPTIONAL if name in table]
    names=(*MANDATORY,*optional);selected_table={name:selected_symbol(table,name)for name in names}
    require(set(raw['assembly'])==set(names),'exact mandatory/actually-linked optional inventory required')
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
        proofs.update(object_proof(target,item,selected,selected_table))
    assembly={name:transfers(raw['assembly'][name],extent(table,name),table)for name in names}
    return dict(schema=SCHEMA,selected_function_count=len(names),object_provenance=proofs,assembly=assembly,
        optional_functions={name:('present'if name in optional else'absent_or_inlined_no_zero_frame_claim')for name in OPTIONAL},
        unexpanded_scheduler_boundaries=list(SCHEDULER),unexpanded_other_targets=sorted({n for row in assembly.values()for edge in row['external_transfers']for n in edge['resolved_symbols']if n not in names}),
        selected_frames_are_not_a_chain_sum=True,strcmp_frame_proven=False,selected_names_unique=True,
        linked_nm_text_rows=sum(len(rows)for rows in table.values()),unselected_duplicate_name_count=sum(len(rows)>1 for name,rows in table.items()if name not in names),**LIMITS)


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

