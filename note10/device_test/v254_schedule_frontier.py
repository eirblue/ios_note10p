"""Fresh-object selected scheduler provenance and opaque switch-call boundary."""
import hashlib
import re
import struct


def require(ok,message):
    if not ok:raise ValueError(message)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def metadata(text):
    sections={};symbols={};relocations=[];unsupported=[];current=None;symtabs=0
    for line in text.splitlines():
        section=re.fullmatch(r'\s*\[\s*(\d+)\]\s+(\S+)\s+(\S+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+([A-Z]*)\s+(\d+)\s+(\d+)\s+(\d+)\s*',line)
        if section:
            i,name,kind,address,offset,size,entry,flags,link,info,align=section.groups();i=int(i);require(i not in sections,'unique ELF text section');sections[i]=dict(name=name,type=kind,address=int(address,16),offset=int(offset,16),bytes=int(size,16),flags=flags,alignment=int(align))
        if line.startswith("Symbol table '"):
            require(line.startswith("Symbol table '.symtab'"),'only static symbol table supported');symtabs+=1;current=None
        symbol=re.fullmatch(r'\s*(\d+):\s+([0-9a-fA-F]+)\s+(\d+|0x[0-9a-fA-F]+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s*(.*?)\s*',line)
        if symbol:
            i,value,size,kind,binding,visibility,index,name=symbol.groups();i=int(i);require(i not in symbols,'unique symbol index');symbols[i]=dict(index=i,value=int(value,16),bytes=int(size,16 if size.startswith('0x')else 10),type=kind,binding=binding,visibility=visibility,section=int(index)if index.isdecimal()else index,name=name)
        heading=re.match(r"Relocation section '([^']+)'",line)
        if heading:current=heading[1]
        row=re.fullmatch(r'\s*([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+(R_AARCH64_\S+)\s+([0-9a-fA-F]+)\s+(.*?)\s+([+-])\s+([0-9a-fA-F]+)\s*',line)
        if row and current=='.rela.sched.text':
            offset,info,kind,value,name,sign,addend=row.groups();info=int(info,16);relocations.append(dict(relocation_section=current,offset=int(offset,16),info=info,symbol_index=info>>32,type_id=info&0xffffffff,type=kind,symbol_value=int(value,16),symbol_name=name,addend=int(addend,16)*(-1 if sign=='-'else 1)))
        elif current=='.rela.sched.text'and re.match(r'^\s*[0-9a-fA-F]+\s+[0-9a-fA-F]+\s+R_',line):unsupported.append(line)
    require(symtabs==1 and sections and symbols,'complete authenticated static ELF text required');return dict(sections=sections,symbols=symbols,relocations=relocations,unsupported_relocations=unsupported)


def extract(raw,text,expected):
    require(len(raw)>=64 and raw[:7]==b'\x7fELF\x02\x01\x01'and struct.unpack_from('<HH',raw,16)==(1,183),'ELF64 little-endian AArch64 object required')
    info=metadata(text);symbols=info['symbols'];rows=[row for row in symbols.values()if row['name']=='__schedule'and row['type']=='FUNC'];require(len(rows)==1,'unique selected __schedule FUNC');symbol=rows[0]
    require(all(symbol[k]==expected[k]for k in ('index','value','bytes','section'))and symbol['binding']=='LOCAL'and symbol['visibility']=='DEFAULT'and symbol['bytes']>0 and symbol['value']%4==symbol['bytes']%4==0,'exact selected function identity')
    section=info['sections'].get(symbol['section']);require(section and section['name']=='.sched.text'and section['type']=='PROGBITS'and 'A'in section['flags']and 'X'in section['flags']and 'W'not in section['flags'],'non-init allocated executable scheduler section')
    offset=struct.unpack_from('<Q',raw,40)[0];entry,count=struct.unpack_from('<HH',raw,58);index=symbol['section'];require(entry==64 and 0<index<count<=4096 and offset+count*64<=len(raw),'bounded native section headers')
    actual=struct.unpack_from('<IIQQQQIIQQ',raw,offset+index*64);require(actual[1]==1 and actual[2]&6==6 and not actual[2]&1 and (actual[3],actual[4],actual[5],actual[8])==(section['address'],section['offset'],section['bytes'],section['alignment']),'actual object section must match authenticated readelf text')
    start=section['offset']+symbol['value'];end=start+symbol['bytes'];require(symbol['value']+symbol['bytes']<=section['bytes']and end<=len(raw),'complete selected function extent')
    return raw[start:end],dict(symbol=symbol,section=section,symbols=symbols,relocations=info['relocations'],unsupported_relocations=info['unsupported_relocations'],body_file_offset=start)


def static_frame(usage,tu,line):
    found=[]
    for row in usage.splitlines():
        parts=row.split('\t')
        if len(parts)!=3 or parts[0].rsplit(':',1)[-1]!='__schedule':continue
        location,amount,kind=parts;require(location.startswith(tu+':'),'same declared TU SU row');suffix=location[len(tu)+1:].split(':');require(len(suffix)in (2,3)and all(x.isdecimal()for x in suffix[:-1])and int(suffix[0])==line and amount.isdecimal(),'actual selected compiler SU location');found.append(dict(bytes=int(amount),kind=kind,line=line,translation_unit=tu))
    require(len(found)==1 and found[0]['kind']=='static','one static selected SU row');return found[0]


def verify(body,info,usage,tu,source,expected):
    symbol=info['symbol'];require(len(body)==symbol['bytes'],'complete selected body retained');require(not info['unsupported_relocations'],'unsupported relocation text; body retained, no record skipped');frame=static_frame(usage,tu,expected['source_line']);require(frame['bytes']==expected['frame_bytes'],'exact fresh compiler SU')
    lines=source.splitlines();require(0<frame['line']<=len(lines)and re.search(r'\b__schedule\s*\(',lines[frame['line']-1]),'selected SU declaration in authenticated source')
    mappings={}
    for row in info['symbols'].values():
        match=re.fullmatch(r'\$([xd])(?:\..*)?',row['name'])
        if row['section']==symbol['section']and match:mappings.setdefault(row['value'],set()).add(match[1])
    require(mappings and all(len(kinds)==1 for kinds in mappings.values()),'unambiguous AArch64 mapping symbols');prior=[at for at in mappings if at<=symbol['value']]
    require(prior and mappings[max(prior)]=={'x'}and not any(kinds!={'x'}for at,kinds in mappings.items()if symbol['value']<=at<symbol['value']+len(body)),'selected extent must be code without data mappings')
    selected=[];direct=[];occupied=set();rel_section='.rela'+info['section']['name']
    for row in info['relocations']:
        if row['relocation_section']!=rel_section or not symbol['value']<=row['offset']<symbol['value']+len(body):continue
        record=info['symbols'].get(row['symbol_index']);require(record and record['name']==row['symbol_name']and record['value']==row['symbol_value'],'actual relocation symbol index/name/value join')
        local=row['offset']-symbol['value'];require(local%4==0 and local+4<=len(body),'selected relocation instruction extent');item=dict(**row,offset_in_function=local,symbol_record=record);selected.append(item);occupied.add(local)
        if row['type']in ('R_AARCH64_CALL26','R_AARCH64_JUMP26'):
            opcode=0x94000000 if row['type']=='R_AARCH64_CALL26'else 0x14000000;kind=283 if opcode==0x94000000 else 282
            require(row['type_id']==kind and struct.unpack_from('<I',body,local)[0]&0xfc000000==opcode,'actual instruction opcode must match CALL26/JUMP26')
            direct.append(dict(offset_in_function=local,object_site=row['offset'],mnemonic='bl'if kind==283 else'b',relocation=item,target_status='undefined-external'if record['section']=='UND'else'same-section'if record['section']==symbol['section']else'cross-section',opaque=True))
    switch=[row for row in selected if row['offset_in_function']==expected['switch_offset']]
    require(len(switch)==1,'one selected context-switch relocation');switch=switch[0];switch_target=switch['symbol_record']
    require(switch['type']=='R_AARCH64_CALL26'and switch['type_id']==283 and switch['symbol_index']==expected['switch_symbol_index']and switch['addend']==0 and switch_target['name']=='__switch_to'and switch_target['binding']=='GLOBAL'and switch_target['type']=='NOTYPE'and switch_target['visibility']=='DEFAULT'and switch_target['section']=='UND'and switch_target['bytes']==switch_target['value']==0,'exact global undefined __switch_to boundary; no callee frame inferred')
    for offset in range(0,len(body),4):
        word=struct.unpack_from('<I',body,offset)[0]
        if offset in occupied:continue
        if word&0x7c000000==0x14000000:
            immediate=word&0x03ffffff;immediate-=1<<26 if immediate&(1<<25)else 0;target=symbol['value']+offset+(immediate<<2)
            records=[row for row in info['symbols'].values()if row['type']=='FUNC'and row['section']==symbol['section']and row['value']==target]
            direct.append(dict(offset_in_function=offset,object_site=symbol['value']+offset,mnemonic='bl'if word&0x80000000 else'b',relocation=None,target_object_offset=target,target_records=records,internal=symbol['value']<=target<symbol['value']+len(body),opaque=True))
        elif word&0xfffffc1f in (0xd61f0000,0xd63f0000):direct.append(dict(offset_in_function=offset,object_site=symbol['value']+offset,mnemonic='blr'if word&0xfffffc1f==0xd63f0000 else'br',target_register=(word>>5)&31,unresolved=True,opaque=True))
    return dict(schema='note10-v254-fresh-schedule-context-proof-v1',fresh_object_schedule_provenance=True,context_switch_CALL26_boundary_proven=True,selected_symbol=symbol,selected_body_sha256=sha(body),selected_body_bytes=len(body),fresh_object_compiler_SU=frame,all_selected_relocations=selected,direct_transfer_frontier=direct,context_switch=switch,
        original_Image_schedule_body_equivalent=False,historical_compiler_identity_inferred=False,local_SP_peak_proven=False,complete_control_flow_proven=False,external_switch_implementation_captured=False,whole_scheduler_stack_bound_proven=False,whole_frontdoor_stack_bound_proven=False,runtime_observed=False,physical_ready=False)
