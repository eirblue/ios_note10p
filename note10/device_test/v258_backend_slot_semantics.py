"""Finite retained-backend slot effects under explicit abstract execution conditions."""
import hashlib
import re
import struct

CONDITIONS=('entry x0/x1 denote abstract prev/next; upstream values and actual linking are unproven','modeled prev/next context ranges are valid, disjoint, nonwrapping and suitably aligned; none is verified','required architectural state/privilege and fault-free noninterfered execution are assumed','loaded next SP/LR are uninterpreted saved values, not proven-valid task/stack/resume targets')


def require(ok,message):
    if not ok:raise ValueError(message)


def read_rows(text,provider,body_sha256):
    labels=list(re.finditer(r'^([0-9a-fA-F]+) <cpu_switch_to>:\s*$',text,re.M));require(len(labels)==1 and int(labels[0][1],16)==provider['value'],'one carried backend label');rows=[]
    for line in text[labels[0].end():].splitlines():
        if not line.strip():continue
        m=re.fullmatch(r'\s*([0-9a-fA-F]+):\s+([0-9a-fA-F]{8})\s+([a-z][a-z0-9.]*)\s*(.*?)\s*',line);require(m is not None,'complete instruction row required');address,word,mnemonic,operands=m.groups();require(int(address,16)==provider['value']+4*len(rows),'sequential selected rows');rows.append(dict(offset=4*len(rows),word=int(word,16),mnemonic=mnemonic,operands=operands.split('//',1)[0].strip()))
    require(len(rows)*4==provider['bytes']and 0<provider['bytes']<=32768 and hashlib.sha256(b''.join(struct.pack('<I',x['word'])for x in rows)).hexdigest()==body_sha256,'new semantic text boundary matches carried selected body');return rows


def prove(text,provider,body_sha256,prefix,relocations):
    require(provider['name']=='cpu_switch_to'and not relocations,'carried relocation-free backend');rows=read_rows(text,provider,body_sha256);add_at=prefix['ADD_x8_x0_x10_offset'];materialization=prefix['materialization']
    require(type(add_at)is int and add_at%4==0 and add_at>=4 and add_at+4<len(rows)*4 and len(materialization)*4==add_at,'bounded carried prefix seed')
    for i,row in enumerate(materialization):require(row['offset']==4*i and rows[i]['word']==int(row['word'],16),'carried prefix rows unchanged')
    require(prefix['generated_context_base_immediate_binding_proven']is True,'carried257 base binding');base=prefix['generated_THREAD_CPU_CONTEXT'];start=add_at//4+1
    # Prefix semantics are carried, not decoded/reproved here.
    regs={i:('entry_register',i)for i in range(31)};regs.update({0:('entry_prev',),1:('entry_next',),8:('prev_context',0),10:('carried_base',base)});sp=('entry_SP',);regs[30]=('entry_LR',);system=None;stores={};loads=[];trace=[];returned=None;phase='save'
    def address(rn,amount):
        pointer=regs.get(rn);require(pointer is not None and len(pointer)==2 and pointer[0]in ('prev_context','next_context'),'supported abstract context pointer');return pointer[0],pointer[1]+amount
    def write(where,value):
        require(where[0]=='prev_context'and phase=='save'and where not in stores,'unique previous-context save before loads');stores[where]=value
    def load(where):
        require(where[0]=='next_context'and phase=='load','next-context symbolic load only');loads.append(where);return ('next_slot',where[1])
    for index in range(start,len(rows)):
        row=rows[index];word=row['word'];rd=word&31;rn=(word>>5)&31;m=row['mnemonic'];event=dict(offset=row['offset'],mnemonic=m)
        if word&0xffe0fc00==0x8b000000:
            rm=(word>>16)&31;require(m=='add'and rd==8 and rn==1 and rm==10 and phase=='save'and regs[1]==('entry_next',)and regs[10]==('carried_base',base),'only next-context base ADD with intact next/base tokens supported');regs[8]=('next_context',0);phase='load';event['effect']='next_context_base'
        elif word&0xffc00000==0x91000000:
            immediate=(word>>10)&0xfff;require(immediate==0 and m=='mov','only observed SP register MOV alias supported')
            if rn==31 and rd!=31:regs[rd]=sp
            elif rd==31 and rn!=31:sp=regs[rn]
            else:raise ValueError('unsupported non-SP move alias')
            event.update(destination='SP'if rd==31 else 'x'+str(rd),value=sp if rd==31 else regs[rd])
        elif word&0xffc00000 in (0xa8800000,0xa8c00000):
            loading=bool(word&0x00400000);rt2=(word>>10)&31;imm=(word>>15)&127;imm=imm-128 if imm&64 else imm;stride=imm*8;require(m==('ldp'if loading else 'stp')and rn==8 and rd!=rn and rt2!=rn and rd!=31 and rt2!=31,'supported64-bit post-index pair without aliases');first=address(rn,0);second=address(rn,8)
            if loading:regs[rd]=load(first);regs[rt2]=load(second)
            else:write(first,regs[rd]);write(second,regs[rt2])
            regs[rn]=(first[0],first[1]+stride);event.update(registers=[rd,rt2],slots=[first,second],post_increment=stride)
        elif word&0xffc00000 in (0xf9000000,0xf9400000):
            loading=bool(word&0x00400000);amount=((word>>10)&0xfff)*8;require(m==('ldr'if loading else 'str')and rn==8 and rd!=31,'supported64-bit context scalar access');where=address(rn,amount)
            if loading:regs[rd]=load(where)
            else:write(where,regs[rd])
            event.update(register=rd,slot=where)
        elif word&0xffffffe0==0xd5184100:require(m=='msr'and rd!=31,'SP_EL0 source');system=regs[rd];event.update(system_register='SP_EL0',value=system)
        elif word&0xfffffc1f==0xd65f0000:
            require(m=='ret'and index==len(rows)-1 and rn==30,'one terminal RET x30');returned=regs[rn];event['target']=returned
        else:raise ValueError('unsupported suffix instruction at offset '+str(row['offset']))
        trace.append(event)
    expected=[('entry_register',i)for i in range(19,30)]+[('entry_SP',),('entry_LR',)];expected_stores={('prev_context',8*i):token for i,token in enumerate(expected)};require(stores==expected_stores,'complete nonoverlapping previous-context register/SP/LR slot saves')
    require(loads==[('next_context',8*i)for i in range(13)],'complete ordered next-context slot loads')
    require(all(regs[i]==('next_slot',(i-19)*8)for i in range(19,30))and sp==('next_slot',88)and regs[30]==returned==('next_slot',96)and system==('entry_next',)and regs[0]==('entry_prev',),'restored registers/SP/SP_EL0/LR/RET or x0 origin mismatch')
    span=max(where[1]for where in stores)+8-min(where[1]for where in stores)
    return dict(local_context_slot_effects_under_conditions=True,conditions=list(CONDITIONS),instruction_rows=len(rows),suffix_rows=len(trace),context_slot_span_bytes=span,save_slot_table=[dict(relative_offset=i*8,origin=token)for i,token in enumerate(expected)],load_slots=[dict(relative_offset=where[1],value=('next_slot',where[1]))for where in loads],SP_origin=sp,SP_EL0_origin=system,RET_target_origin=returned,x0_origin=regs[0],trace=trace,backend_save_load_semantics_proven=False,numeric_internal_context_layout_proven=False,task_stack_validity_proven=False,liveness_proven=False,switch_resume_contract_proven=False,cross_object_link_resolution_proven=False,original_Image_body_equivalent=False,historical_compiler_identity_inferred=False,local_SP_peak_proven=False,whole_scheduler_or_frontdoor_stack_bound_proven=False,compiler_static_SU_bytes=None,assembly_C_compiler_SU_claimed=False,runtime_observed=False,physical_ready=False)
