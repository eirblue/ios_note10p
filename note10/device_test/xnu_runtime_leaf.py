"""Exact fixed-leaf proof for both pinned sequential diagnostic callers."""
import re
import struct
from prepare_xnu_runtime_observation import sha

PREFIX='arch/arm64/mm/'
SOURCE_PINS={
 PREFIX+'note10_xnu_runtime_scratch.c':'3775f48d09fff787e921d3962aa5cf30fcce60524c5188f06b8f2b0f65934fe6',
 PREFIX+'runtime_relocation.c':'dc51d22fce4c8e0d566d6158f53aa3d512a65954541e4ea4201c5878cb17e448',
 PREFIX+'runtime_relocation.h':'2956336fbec371636acb62a4fc51aae451e74a65bdf4595b12e80c3be8ca9037',
 PREFIX+'init.c':'5d52b5883ba502909294cefb6a97b19df3fe7b749eb404b677b90fc15fd233e2',
 PREFIX+'note10_xnu_runtime_plan.c':'82009f2f6355726556a83fe4040ca117557ae5d2c8456290ae72753d6c42fd7e',
 PREFIX+'note10_xnu_runtime_observation.c':'a8d99bf3747a4e7a7064b95beaac67ae05346a2008f4a2497d4c973672323004'}
RESERVE=PREFIX+'note10_xnu_reserve.c'
RESERVE_BODY_SHA='9da5f31aab5fe6ea0072e8c20ace8a19bbd54248d64d0808e87b3f098d869a4e'
SYMBOLS=('n10_scratch_tree','n10_xnu_runtime_plan_check.synthetic_tree')
LEAF=struct.pack('<II32sI12s',1,0,b'name',12,b'device-tree\0')
LEAF_SHA='37154617c91027ac8e52fea9924579df6f135b0c1179892aad1fe77fb0936d80'
REPORTERS=('n10_observe_runtime_plan','n10_runtime_plan_report','n10_scratch_report')

def _sections(raw):
    if len(raw)<64 or raw[:6]!=b'\x7fELF\x02\x01' or struct.unpack_from('<HH',raw,16)!=(1,183):raise ValueError('leaf proof requires AArch64 ELF64 ET_REL')
    at=struct.unpack_from('<Q',raw,40)[0];stride,count,names=struct.unpack_from('<HHH',raw,58)
    if stride!=64 or not 1<=count<=4096 or names>=count or at>len(raw) or count*stride>len(raw)-at:raise ValueError('leaf ELF section table invalid')
    sections=[struct.unpack_from('<IIQQQQIIQQ',raw,at+i*stride) for i in range(count)]
    if sections[names][1]!=3 or sum(s[1]==2 for s in sections)!=1 or any(s[1]==11 for s in sections):raise ValueError('leaf ELF canonical section/symbol tables required')
    if any(s[1]!=8 and (s[4]>len(raw) or s[5]>len(raw)-s[4]) for s in sections):raise ValueError('leaf ELF section truncated')
    def data(section):
        if section[1]==8 or section[4]>len(raw) or section[5]>len(raw)-section[4]:raise ValueError('leaf ELF section data invalid')
        return raw[section[4]:section[4]+section[5]]
    def string(table,index):
        if index>=len(table):raise ValueError('leaf ELF string offset invalid')
        end=table.find(b'\0',index)
        if end<0:raise ValueError('leaf ELF string unterminated')
        try:return table[index:end].decode('ascii')
        except UnicodeError as error:raise ValueError('leaf ELF string invalid') from error
    return sections,data,string,data(sections[names])

def leaf_symbols(raw):
    sections,data,string,section_names=_sections(raw);found={n:[] for n in SYMBOLS}
    for table in sections:
        if table[1]!=2:continue
        if table[9]!=24 or table[5]%24 or table[6]>=len(sections) or sections[table[6]][1]!=3:raise ValueError('leaf ELF symbol table invalid')
        symbols=data(table);strings=data(sections[table[6]])
        for at in range(0,len(symbols),24):
            name,info,visibility,index,value,size=struct.unpack_from('<IBBHQQ',symbols,at)
            name=string(strings,name)
            if name not in found:continue
            if info!=1 or visibility!=0 or not 0<index<len(sections) or size!=56:raise ValueError('leaf symbol must be exact LOCAL STT_OBJECT size56')
            section=sections[index]
            if section[1]!=1 or not section[2]&2 or section[2]&5:raise ValueError('leaf symbol section must be allocated readonly nonexecutable')
            blob=data(section)
            if value>len(blob) or size>len(blob)-value:raise ValueError('leaf symbol exceeds section')
            leaf=blob[value:value+size]
            if leaf!=LEAF or sha(leaf)!=LEAF_SHA:raise ValueError('compiled leaf bytes differ')
            found[name].append(dict(symbol=name,binding='LOCAL',type='STT_OBJECT',section=string(section_names,section[0]),
              section_flags=section[2],offset=value,size=size,sha256=sha(leaf),root_properties=1,root_children=0))
    if any(len(rows)!=1 for rows in found.values()):raise ValueError('both exact unique compiled leaf symbols required')
    return [found[n][0] for n in SYMBOLS]

def reporter_identity(raw,expected_id):
    """Bind ID to actual reporter references, not an unrelated string literal."""
    sections,data,string,names=_sections(raw)
    table_index=next(i for i,s in enumerate(sections) if s[1]==2)
    table=sections[table_index]
    if table[9]!=24 or table[5]%24 or table[6]>=len(sections):raise ValueError('reporter symbol table malformed')
    symbols=[struct.unpack_from('<IBBHQQ',data(table),at) for at in range(0,table[5],24)]
    strings=data(sections[table[6]]);functions={n:[] for n in REPORTERS}
    for symbol in symbols:
        name,info,other,index,value,size=symbol;name=string(strings,name)
        if name not in functions:continue
        if info!=2 or other!=0 or not 0<index<len(sections) or not size:raise ValueError('reporter must be exact LOCAL STT_FUNC')
        section=sections[index]
        if section[1]!=1 or section[2]&7!=6 or value>section[5] or size>section[5]-value:raise ValueError('reporter executable section/range invalid')
        functions[name].append((index,value,size))
    if any(len(rows)!=1 for rows in functions.values()):raise ValueError('unique actual reporter functions required')
    references={n:[] for n in REPORTERS}
    for relocation in sections:
        if relocation[1]!=4:continue
        if relocation[6]!=table_index or relocation[9]!=24 or relocation[5]%24 or relocation[7]>=len(sections):raise ValueError('reporter relocation table malformed')
        relocations=data(relocation)
        for at in range(0,len(relocations),24):
            offset,info,addend=struct.unpack_from('<QQq',relocations,at);kind=info&0xffffffff
            if kind not in (275,277):continue
            sym=info>>32
            if sym>=len(symbols):raise ValueError('reporter relocation symbol invalid')
            _,target_info,_,index,value,_=symbols[sym]
            if not 0<index<len(sections):continue
            target=sections[index];position=value+addend
            if target[1]!=1 or not target[2]&2 or target[2]&5 or target_info>>4!=0:continue
            blob=data(target)
            if position<0 or position>len(blob) or 33>len(blob)-position or blob[position:position+33]!=expected_id.encode()+b'\0':continue
            for name,rows in functions.items():
                function_section,start,size=rows[0]
                if function_section==relocation[7] and start<=offset<start+size:
                    references[name].append({'relocation_type':kind,'target_section':index,'target_offset':position})
    for name,refs in references.items():
        if sorted(r['relocation_type'] for r in refs)!=[275,277] or len({(r['target_section'],r['target_offset']) for r in refs})!=1:
            raise ValueError('both exact reporter build-ID address relocations required: '+name)
    return references

def prove(raw,sources,expected_id):
    if not isinstance(sources,dict) or not isinstance(expected_id,str) or re.fullmatch('[0-9a-f]{32}',expected_id) is None:
        raise ValueError('leaf proof actual source/build ID binding missing')
    for name,digest in SOURCE_PINS.items():
        if not isinstance(sources.get(name),bytes) or sha(sources[name])!=digest:raise ValueError('fixed leaf caller/runtime source differs: '+name)
    reserve=sources.get(RESERVE)
    if not isinstance(reserve,bytes):raise ValueError('fixed leaf reserve call closure missing')
    first,separator,body=reserve.partition(b'\n')
    match=re.fullmatch(rb'#define N10_RESERVE_BUILD_ID "([0-9a-f]{32})"',first)
    if not separator or not match or match[1].decode()!=expected_id or sha(body)!=RESERVE_BODY_SHA:
        raise ValueError('reserve exact build-ID/body/sequential call closure differs')
    sections,data,string,names=_sections(raw)
    readonly=[data(s) for s in sections if s[1]==1 and s[2]&2 and not s[2]&5]
    if sum(blob.count(expected_id.encode()+b'\0') for blob in readonly)!=1:raise ValueError('same-object build ID missing/ambiguous')
    symbols=leaf_symbols(raw)
    identity_relocations=reporter_identity(raw,expected_id)
    return dict(proven=True,adt_levels=1,scope='both sequential pinned diagnostic callers only',
      depth_reason='both canonical root nodes have children0; pinned parser recurses only in child loop',
      build_evidence_id=expected_id,object_sha256=sha(raw),symbols=symbols,reporter_id_relocations=identity_relocations,
      source_sha256={n:sha(sources[n]) for n in (*SOURCE_PINS,RESERVE)},
      reserve_body_sha256=sha(body),build_id_normalization='only remove exact first define line',
      call_paths=['planner observer -> planner check -> plan -> validate_adt -> root',
        'scratch observer -> scratch build -> rt_build -> plan -> validate_adt -> root'],
      sequential_call_order_from_pinned_source=True,physical_stack_safety_proven=False)
