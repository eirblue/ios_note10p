"""Finite real-object projection/relocation and component-only stack proof."""
import re
import struct
from relocation_trial_aarch64_model import require,digest

ENTRY='n10_kernel_trial_adapter'
FUNCTIONS=frozenset('''n10_kernel_trial_adapter n10_rt_trial n10_rt_plan n10_rt_validate_adt
span intersects copy zero_bytes copy_bytes add64 overlap pointer_overlap pointer_span same le32
name_byte gic_name take adt_node command_ok'''.split())
DATA_SECTIONS={'.rodata.n10_component','.n10_abi','.n10_stack'}
ROOT_SECTIONS={'.text.'+ENTRY,'.n10_abi','.n10_stack'}

def parse_elf(raw,kind):
    require(len(raw)>=64 and raw[:6]==b'\x7fELF\x02\x01' and struct.unpack_from('<HH',raw,16)==(kind,183),'bounded actual AArch64 ELF type')
    at=struct.unpack_from('<Q',raw,40)[0];stride,count,names=struct.unpack_from('<HHH',raw,58)
    require(stride==64 and 0<count<4096 and names<count and at+count*64<=len(raw),'ELF section table')
    headers=[struct.unpack_from('<IIQQQQIIQQ',raw,at+i*64) for i in range(count)]
    def data(s):
        require(s[5]<=256*1024*1024 and (s[1]==8 or s[4]+s[5]<=len(raw)),'section bytes extent')
        return b'\0'*s[5] if s[1]==8 else raw[s[4]:s[4]+s[5]]
    def string(table,index):
        end=table.find(b'\0',index);require(index<len(table) and end>=0,'bounded ELF string');return table[index:end].decode('ascii')
    strings=data(headers[names]);sections=[]
    for index,s in enumerate(headers):sections.append({'index':index,'name':string(strings,s[0]),'type':s[1],'flags':s[2],'address':s[3],'bytes':data(s),'link':s[6],'info':s[7],'stride':s[9]})
    tables={};symbols=[]
    for s in sections:
        if s['type']!=2:continue
        require(s['stride']==24 and len(s['bytes'])%24==0 and s['link']<count,'ELF symbol table')
        table=[];strings=sections[s['link']]['bytes']
        for off in range(0,len(s['bytes']),24):
            name,info,other,index,value,size=struct.unpack_from('<IBBHQQ',s['bytes'],off)
            symbol={'name':string(strings,name),'info':info,'section':index,'value':value,'size':size}
            table.append(symbol);symbols.append(symbol)
        tables[s['index']]=table
    relocations=[]
    for s in sections:
        require(s['type']!=9,'REL without explicit addend rejected')
        if s['type']!=4:continue
        require(s['stride']==24 and len(s['bytes'])%24==0 and s['link'] in tables and s['info']<count,'RELA table')
        target=sections[s['info']]
        for off in range(0,len(s['bytes']),24):
            address,info,addend=struct.unpack_from('<QQq',s['bytes'],off);symbol_index=info>>32
            require(symbol_index<len(tables[s['link']]),'RELA symbol index')
            relative=address-target['address'] if kind==2 else address
            require(0<=relative<len(target['bytes']),'RELA source extent')
            relocations.append({'section':target['index'],'offset':relative,'type':info&0xffffffff,'addend':addend,'symbol':tables[s['link']][symbol_index]})
    return {'kind':kind,'sections':sections,'symbols':symbols,'relocations':relocations,'sha256':digest(raw)}

def section_map(obj):
    result={}
    for s in obj['sections']:
        if not s['flags']&2 or not s['bytes']:continue
        require(s['name'] not in result,'duplicate allocated section name');result[s['name']]=s
    return result

def component_closure(obj,enabled=True):
    symbols=obj['symbols'];adapter=[s for s in symbols if s['name']==ENTRY]
    component=[s for s in symbols if s['name'].startswith('n10_rt_') or s['name'] in (ENTRY,'n10_trial_abi','n10_kernel_stack_oracle')]
    if not enabled:
        require(not component,'disabled object exposes component');return {'selected_sections':[],'functions':[],'call_edges':[],'adapter_uninvoked':True}
    sections=obj['sections'];named=section_map(obj)
    require(len(adapter)==1 and adapter[0]['info']==18 and ROOT_SECTIONS<=set(named),'unique global adapter and readonly oracles')
    adapter_index=named['.text.'+ENTRY]['index'];require(adapter[0]['section']==adapter_index,'adapter isolated from shared init text')
    require(not any(('ksymtab' in s['name'] or 'kstrtab' in s['name']) and any(n in s['name'] for n in ('n10_rt_','n10_kernel_trial','n10_trial_abi')) for s in symbols),'component not exported')
    for rel in obj['relocations']:
        if sections[rel['section']]['flags']&2 and rel['symbol']['section']==adapter_index:
            require(rel['section']==adapter_index,'kernel boot/initcall/registration references adapter')
    selected={named[n]['index'] for n in ROOT_SECTIONS};pending=list(selected);edges=set()
    while pending:
        index=pending.pop();s=sections[index];name=s['name']
        require(not s['flags']&1 and (name in DATA_SECTIONS or name.startswith('.text.') and name[6:] in FUNCTIONS),'unexpected/writable retained component section: '+name)
        for rel in obj['relocations']:
            if rel['section']!=index:continue
            symbol=rel['symbol'];target=symbol['section'];require(0<target<len(sections),'component has external OS/provider/absolute relocation')
            if rel['type'] in (282,283):
                callee=sections[target]['name'];require(callee.startswith('.text.') and callee[6:] in FUNCTIONS and symbol['value']+rel['addend']==0,'call to nonentry/noncomponent provider')
                edges.add((name[6:],callee[6:]))
            if target not in selected:selected.add(target);pending.append(target)
    functions=[]
    for symbol in symbols:
        if symbol['section'] in selected and symbol['info']&15==2:
            require(symbol['name'] in FUNCTIONS and symbol['size']>0,'unknown retained function/outline')
            functions.append(symbol['name'])
    require({ENTRY,'n10_rt_trial','n10_rt_plan','adt_node'}<=set(functions),'required closed component function symbols')
    graph={n:set() for n in functions}
    for caller,callee in edges:
        if caller==callee:require(caller=='adt_node','unexpected recursive component function')
        else:graph[caller].add(callee)
    def acyclic(node,path):
        require(node not in path,'unexpected mutually recursive component call graph')
        for child in graph[node]:acyclic(child,path|{node})
    for name in functions:acyclic(name,set())
    return {'selected_sections':sorted(sections[i]['name'] for i in selected),'functions':sorted(set(functions)),
      'call_edges':[list(e) for e in sorted(edges)],'adapter_uninvoked':True,'external_OS_calls':0}

def relocate(raw,offset,kind,symbol,addend,place):
    data=bytearray(raw);target=symbol+addend;width=8 if kind==257 else 4
    require(offset>=0 and offset+width<=len(data),'relocation field extent')
    if kind==257:struct.pack_into('<Q',data,offset,target);return bytes(data)
    word=struct.unpack_from('<I',data,offset)[0]
    if kind in (282,283):
        delta=target-place;require(delta%4==0 and -(1<<27)<=delta<(1<<27),'branch relocation range');word=(word&~0x3ffffff)|((delta>>2)&0x3ffffff)
    elif kind in (274,275):
        delta=target-place if kind==274 else (target>>12)-(place>>12)
        require(-(1<<20)<=delta<(1<<20),'ADR relocation range');imm=delta&0x1fffff
        word=(word&~0x60ffffe0)|((imm&3)<<29)|((imm>>2)<<5)
    elif kind in (277,278,284,285,286):
        scale={277:0,278:0,284:1,285:2,286:3}[kind];low=target&4095
        require(low%(1<<scale)==0,'load/store relocation alignment');word=(word&~0x003ffc00)|((low>>scale)<<10)
    else:raise ValueError('unreviewed component relocation kind: '+str(kind))
    struct.pack_into('<I',data,offset,word);return bytes(data)

def validate_linked_relocation(original,linked,expected_section,expected_value):
    require(linked['offset']==original['offset'] and linked['type']==original['type'] and
      linked['symbol']['section']==expected_section and linked['symbol']['value']==expected_value and
      linked['addend']==original['addend'],'exact linked relocation section/location/addend identity')

def projection_proof(original,linked,final):
    closure=component_closure(original);names=set(closure['selected_sections']);a=section_map(original);b=section_map(linked);c=section_map(final)
    require(set(b)==names==set(c),'projection retained unexpected/unreviewed sections')
    require(not final['relocations'],'runtime projection still has relocations')
    evidence={}
    for name in sorted(names):
        source=a[name];destination=b[name];require(destination['bytes']==c[name]['bytes'] and destination['address']==c[name]['address'],'relocation-metadata stripping changed executable bytes')
        expected=source['bytes'];rels=[rel for rel in original['relocations'] if rel['section']==source['index']]
        linked_rels=[rel for rel in linked['relocations'] if rel['section']==destination['index']]
        require(len(rels)==len(linked_rels),'emitted original relocation inventory differs')
        used=set()
        for rel in rels:
            target_section=original['sections'][rel['symbol']['section']]['name'];require(target_section in b,'relocation escapes selected sections')
            target=b[target_section]['address']+rel['symbol']['value'];place=destination['address']+rel['offset']
            matches=[(i,x) for i,x in enumerate(linked_rels) if i not in used and x['offset']==rel['offset'] and x['type']==rel['type']]
            require(len(matches)==1,'linked relocation offset/type collision');i,other=matches[0];used.add(i)
            validate_linked_relocation(rel,other,b[target_section]['index'],target)
            expected=relocate(expected,rel['offset'],rel['type'],target,rel['addend'],place)
        require(expected==destination['bytes'],'projection bytes differ from original plus exact finite relocations')
        evidence[name]={'original_sha256':digest(source['bytes']),'projected_sha256':digest(expected),'address':destination['address'],'relocation_count':len(rels)}
    for symbol in final['symbols']:
        if symbol['section'] and symbol['info']&15==2:require(symbol['name'] in closure['functions'],'unexpected final provider/function')
    return {'closure':closure,'sections':evidence,'original_object_sha256':original['sha256'],'linked_relocation_proof_sha256':linked['sha256'],'final_ELF_sha256':final['sha256'],'bytes_and_relocations_recomputed':True,'standalone_recompile_substitute':False}

def usage_frames(text):
    result={}
    for line in text.splitlines():
        parts=line.split('\t');require(len(parts)==3,'actual .su row syntax')
        name=parts[0].rsplit(':',1)[-1];require(name not in result and parts[1].isdecimal(),'duplicate/malformed stack usage row')
        result[name]=int(parts[1]) if parts[2]=='static' else None
    return result

def stack_estimate(frames,functions,thread_size):
    require({'adt_node',ENTRY,'n10_rt_trial','n10_rt_plan'}<=set(functions) and all(n in frames and type(frames[n]) is int for n in functions),'missing/dynamic retained actual frame; never infer zero')
    base=sum(frames[n] for n in functions);leaf=32+base;generic=32+base+9*frames['adt_node']
    require(thread_size>=8192 and leaf<=8192 and thread_size-leaf>=8192,'component-only leaf stack budget/margin')
    return {'component_frames':{n:frames[n] for n in sorted(functions)},'sum_retained_frames':base,'adapter_incoming_stack_argument_bytes':32,
      'modeled_leaf_depth':1,'modeled_component_bound':leaf,'THREAD_SIZE':thread_size,'modeled_margin':thread_size-leaf,
      'generic_ADT_frames_including_rejecting_depth9':10,'generic_component_bound':generic,'generic_budget_passed':generic<=8192 and thread_size-generic>=8192,
      'external_OS_reservation_assumption':None,'physical_or_whole_OS_IRQ_stack_safety_proven':False}

def linker_script():
    text='ENTRY('+ENTRY+')\nPHDRS { code PT_LOAD FLAGS(5); ro PT_LOAD FLAGS(4); }\nSECTIONS {\n . = 0x10000000;\n'
    for name in sorted(FUNCTIONS,key=lambda n:(n!=ENTRY,n)):text+=' .text.'+name+' : { *(.text.'+name+') } :code\n'
    text+=' . = ALIGN(0x1000);\n .rodata.n10_component : { *(.rodata.n10_component) } :ro\n'
    text+=' .n10_abi : { KEEP(*(.n10_abi)) } :ro\n .n10_stack : { KEEP(*(.n10_stack)) } :ro\n'
    return text+' /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) *(.llvm_addrsig) }\n}\n'
