"""Bind included231 functions to the actual owner TU, static SU and ELF/nm."""
from pathlib import PurePosixPath
import re
import shlex
import v231_native_prepare as retained
require,sha=retained.require,retained.sha
TARGET='arch/arm64/mm/init.o'
FUNCTIONS=('n231_capture_cpu_observation','n231_clear_observation','n231_layout_witness')


def owner_tu(command):
    usage=retained.stream_candidate.compiler_stack_path(command,TARGET)
    lines=command.decode().splitlines();key='source_'+TARGET+' := '
    declarations=[line[len(key):]for line in lines if line.startswith(key)]
    require(len(declarations)==1,'one actual owner source declaration required')
    source=declarations[0];path=PurePosixPath(source)
    require(path.is_absolute()and str(path)==source and '..'not in path.parts and
        source.endswith('/source/arch/arm64/mm/init.c')and not any(c.isspace()for c in source),
        'canonical literal remote owner TU required')
    argv=shlex.split(lines[0][len('cmd_'+TARGET+' := '):])
    require(argv[-1]==source and argv.count(source)==1,'owner source declaration/compile operand must agree')
    return dict(translation_unit=source,stack_relative=str(usage),command_sha256=sha(command))


def observation_target(symbols,usage,sections,command):
    require(type(symbols)is type(usage)is type(sections)is str and type(command)is bytes,'typed same-owner evidence required')
    tu=owner_tu(command);rows=[line.split()for line in symbols.splitlines()if line.strip()]
    def one(name):
        found=[row for row in rows if row[0]==name];require(len(found)==1,'one actual231 symbol required: '+name);return found[0]
    values={}
    for name,wanted in retained.OBSERVATION_ABS.items():
        row=one(name);require(len(row)==3 and row[1]=='A'and int(row[2],16)==wanted,'computed231 ABS type required');values[name]=wanted
    pool,slot,body=one('n226_source_pool'),one('n231_observation_storage'),one('n231_capture_cpu_observation')
    require(len(pool)==len(slot)==len(body)==4 and pool[1]in('b','B')and slot[1]=='B'and body[1]=='T'and
        int(pool[3],16)==49152 and int(slot[3],16)==32 and int(slot[2],16)==int(pool[2],16)+43544 and int(body[3],16)>0,
        'actual32 alias must stay inside existing pool')
    parsed=retained.stream_candidate.frames(usage)
    require({name for name in parsed if name.startswith('n231_')}==set(FUNCTIONS),'exact known231 frame set required')
    selected={name:parsed[name]for name in FUNCTIONS}
    require(all(row['source']==tu['translation_unit']and row['kind']=='static'for row in selected.values()),
        'known231 static rows must belong to the declared owner TU')
    require({row[0]for row in rows if len(row)==4 and row[0].startswith('n231_')and row[1]in('T','t')}==set(FUNCTIONS),
        'exact known231 nm function set required')
    elf=[]
    for line in sections.splitlines():
        match=re.match(r'^\s*\d+:\s+([0-9a-fA-F]+)\s+(\d+|0x[0-9a-fA-F]+)\s+FUNC\s+(LOCAL|GLOBAL)\s+DEFAULT\s+(\d+)\s+(\S+)\s*$',line)
        if match and match[5]in FUNCTIONS:elf.append(match.groups())
    provenance={}
    for name in FUNCTIONS:
        nm=one(name);expected='GLOBAL'if name=='n231_capture_cpu_observation'else'LOCAL'
        found=[row for row in elf if row[4]==name]
        require(len(found)==1 and len(nm)==4 and nm[1]==('T'if expected=='GLOBAL'else't'),'one same-owner nm/ELF function required')
        address,size,binding,index,_=found[0];size=int(size,16 if size.startswith('0x')else 10)
        require(binding==expected and int(address,16)==int(nm[2],16)and size==int(nm[3],16)>0,
            'same-owner nm/ELF address/size/binding must agree')
        provenance[name]=dict(address=int(address,16),bytes=size,binding=binding,section_index=int(index))
    noninit=retained.stream_candidate.noninit_functions(sections,set(FUNCTIONS))
    return dict(schema='note10-v232-cpu-observation-target-v1',ABS=values,pool_offset=43544,record_bytes=32,new_pool_bytes=0,
        capture_static_frames=selected,noninit_functions=noninit,capture_scheduler_chain_bound=False,decoder_bound_includes_capture=False,
        runtime_observed=False,FDT_bound=False,handoff_cpu_selected=False,post_shutdown=False,
        owner_TU_provenance=dict(schema='note10-v232-owner-TU-stack-provenance-v1',**tu,symbol_provenance=provenance,
            nm_text_sha256=sha(symbols.encode()),ELF_text_sha256=sha(sections.encode()),SU_text_sha256=sha(usage.encode())))
