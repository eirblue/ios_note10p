"""Fixed fresh caller argument flow, conditional on entry ABI and opaque-helper preservation."""
import hashlib
import re
import struct

TRACKED=(0,1,19,20)
ABI_CONDITIONS=('entry x0=prev and x1=next according to the provider interface; upstream caller values are unproven','ordinary returning pre-backend helpers preserve x19/x20 according to AAPCS64; their bodies/compliance are unverified')


def require(ok,message):
    if not ok:raise ValueError(message)


def signed(value,bits):return value-(1<<bits)if value&(1<<(bits-1))else value


def rows_from_text(text,proof):
    p=proof['provider'];start=p['value'];size=p['bytes'];require(p['name']=='__switch_to'and 0<size<=32768 and size%4==0,'carried complete provider extent')
    labels=list(re.finditer(r'^([0-9a-fA-F]+) <__switch_to>:\s*$',text,re.M));require(len(labels)==1 and int(labels[0][1],16)==start,'one exact disassembly function label');rows=[]
    for line in text[labels[0].end():].splitlines():
        if not line.strip():continue
        m=re.fullmatch(r'\s*([0-9a-fA-F]+):\s+([0-9a-fA-F]{8})\s+([a-z][a-z0-9.]*)\s*(.*?)\s*',line);require(m is not None,'unsupported/malformed selected disassembly row')
        address,word,mnemonic,operands=m.groups();address=int(address,16);require(address==start+4*len(rows)and address<start+size,'sequential complete selected rows');rows.append(dict(offset=address-start,word=int(word,16),mnemonic=mnemonic,operands=operands.split('//',1)[0].strip()))
    require(len(rows)*4==size and hashlib.sha256(b''.join(struct.pack('<I',r['word'])for r in rows)).hexdigest()==proof['body_sha256'],'new text semantic-input digest boundary')
    return rows


def decode(row):
    w=row['word'];at=row['offset'];m=row['mnemonic'];rd=w&31;rn=(w>>5)&31;effect=dict(kind='kill',destinations=[],mnemonic=m)
    if w&0x7c000000==0x14000000:
        call=bool(w&0x80000000);require(m==('bl'if call else 'b'),'branch mnemonic/word');target=at+(signed(w&0x03ffffff,26)<<2);effect.update(kind='call'if call else 'branch',target=target)
    elif w&0xff000010==0x54000000:
        conditions=('eq','ne','cs','cc','mi','pl','vs','vc','hi','ls','ge','lt','gt','le');require((w&15)<14 and m=='b.'+conditions[w&15],'conditional branch mnemonic/word');effect.update(kind='conditional',target=at+(signed((w>>5)&0x7ffff,19)<<2))
    elif w&0x7e000000 in (0x34000000,0x36000000):
        test=w&0x7e000000==0x36000000;nonzero=bool(w&0x01000000);require(m==('tbnz'if nonzero else 'tbz')if test else m==('cbnz'if nonzero else 'cbz'),'test branch mnemonic/word');bits=14 if test else 19;effect.update(kind='conditional',target=at+(signed((w>>5)&((1<<bits)-1),bits)<<2))
    elif w==0xd65f03c0:require(m=='ret','return mnemonic/word');effect['kind']='return'
    elif w&0x7fe0ffe0==0x2a0003e0:
        require(m=='mov','register move mnemonic/word');effect.update(kind='move',destination=rd,source=(w>>16)&31,width=64 if w&0x80000000 else 32)
    elif w&0x3a000000==0x28000000 and not w&0x04000000:
        load=bool(w&0x00400000);require((w>>30)&3 in (0,2)and m==('ldp'if load else 'stp'),'integer pair load/store');effect['destinations']=[rd,(w>>10)&31]if load else[]
        if (w>>23)&3 in (1,3):effect['destinations'].append(rn)
    elif w&0x3b000000 in (0x38000000,0x39000000)and not w&0x04000000:
        opcode=(w>>22)&3;require(opcode in (0,1)and m in (('ldr','ldrb','ldrh')if opcode else('str','strb','strh')),'supported scalar memory operation');effect['destinations']=[rd]if opcode else[]
        if w&0x3b000000==0x38000000 and not w&0x00200000 and (w>>10)&3 in (1,3):effect['destinations'].append(rn)
    elif w&0x1f800000==0x12800000:require(m in ('mov','movk','movn','movz'),'wide-immediate move');effect['destinations']=[rd]
    elif w&0x1f000000==0x11000000:require(m in ('add','sub','adds','subs','cmp','cmn','mov'),'add/sub immediate');effect['destinations']=[rd]
    elif w&0x1f800000==0x12000000:require(m in ('and','orr','eor','ands','tst','mov'),'logical immediate');effect['destinations']=[rd]
    elif w&0x1f000000==0x0a000000:require(m in ('and','orr','eor','ands','tst'),'logical register');effect['destinations']=[rd]
    elif w&0x1fe00000==0x1a800000:require(m=='csel','conditional select');effect['destinations']=[rd]
    elif w&0x1f000000==0x10000000:require(m in ('adr','adrp'),'PC-relative address');effect['destinations']=[rd]
    elif w&0xfff00000==0xd5300000:require(m=='mrs','system register read');effect['destinations']=[rd]
    elif w&0xfff00000==0xd5100000:require(m=='msr','system register write')
    elif w in (0xd503201f,0xd5033b9f):require(m==('nop'if w==0xd503201f else 'dsb'),'supported barrier/nop')
    else:raise ValueError('unsupported instruction at offset '+str(at))
    if effect['kind']in ('branch','conditional'):
        token=row['operands'].rsplit(',',1)[-1].strip().split()[0];require(re.fullmatch('[0-9a-fA-F]+',token)is not None,'numeric branch operand');effect['printed_target']=int(token,16)
    return effect


def prove(text,proof,source):
    require(re.search(r'\b__switch_to\s*\(\s*struct\s+task_struct\s*\*\s*prev\s*,\s*struct\s+task_struct\s*\*\s*next\s*\)',source)is not None,'pinned provider two-pointer interface')
    rows=rows_from_text(text,proof);p=proof['provider'];boundary=proof['backend_boundary'];end=boundary['offset'];require(boundary['type']==283 and boundary['mnemonic']=='bl'and boundary['target']['name']=='cpu_switch_to'and boundary['addend']==0 and 0<end<p['bytes']and end%4==0,'carried cpu_switch_to BL boundary')
    relocations={}
    for rel in proof['selected_relocations']:
        require(rel['offset']not in relocations,'unique carried relocation');relocations[rel['offset']]=rel
    require(end in relocations and all(relocations[end][k]==boundary[k]for k in ('type','symbol_index','target','addend')),'exact carried backend relocation')
    effects={};edges={};colors={};order=[];helpers=[]
    def visit(at):
        require(type(at)is int and at%4==0 and 0<=at<=end,'unsupported CFG transfer outside pre-backend slice')
        require(colors.get(at)!=1,'cyclic CFG unsupported')
        if colors.get(at)==2:return
        colors[at]=1;effect=decode(rows[at//4]);effects[at]=effect
        if at==end:require(effect['kind']=='call','backend instruction is BL');successors=[]
        elif effect['kind']=='call':
            rel=relocations.get(at);require(rel is not None and rel['type']==283 and rel['addend']==0 and rel['target']['name']!='cpu_switch_to','opaque ordinary helper must have carried CALL26');helpers.append(dict(offset=at,target=rel['target']['name'],preservation_assumed=True));successors=[at+4]
        elif effect['kind']in ('branch','conditional'):
            require(at not in relocations,'relocated CFG branch unsupported; encoded target is not final')
            require(effect['printed_target']==p['value']+effect['target'],'branch encoded/printed target agreement');successors=[effect['target']]+([at+4]if effect['kind']=='conditional'else[])
        else:require(effect['kind']!='return','return before backend unsupported');successors=[at+4]
        edges[at]=list(dict.fromkeys(successors))
        for target in edges[at]:visit(target)
        colors[at]=2;order.append(at)
    visit(0);require(end in colors,'backend locally reachable');order.reverse();incoming={0:('prev','next',None,None)};trace=[]
    for at in order:
        state=dict(zip(TRACKED,incoming[at]));before=dict(state);effect=effects[at]
        if at!=end:
            if effect['kind']=='call':state[0]=state[1]=None
            elif effect['kind']=='move':
                if effect['destination']in state:state[effect['destination']]=state.get(effect['source'])if effect['width']==64 else None
            else:
                for register in effect['destinations']:
                    if register in state:state[register]=None
        after=tuple(state[x]for x in TRACKED);trace.append(dict(offset=at,before={str(k):v for k,v in before.items()},after={str(k):v for k,v in state.items()},effect=effect,successors=edges[at]))
        for target in edges[at]:
            if target not in incoming:incoming[target]=after
            else:incoming[target]=tuple(a if a==b else None for a,b in zip(incoming[target],after))
    state=dict(zip(TRACKED,incoming[end]));require(state[0]=='prev'and state[1]=='next','outgoing arguments are not proved on every supported incoming path')
    return dict(argument_mapping_at_backend_call_under_ABI_contract=True,conditional_on=list(ABI_CONDITIONS),backend_offset=end,outgoing_arguments={'x0':'entry-prev','x1':'entry-next'},opaque_helper_contracts=sorted(helpers,key=lambda r:r['offset']),instruction_rows=len(rows),reachable_pre_backend_rows=len(order),trace=trace,machine_argument_register_flow_proven=False,upstream_caller_values_proven=False,ordinary_helper_ABI_compliance_verified=False,compiled_backend_body_captured=False,cross_object_link_resolution_proven=False,switch_resume_contract_proven=False,local_SP_peak_proven=False,whole_scheduler_or_frontdoor_stack_bound_proven=False,original_Image_body_equivalent=False,historical_compiler_identity_inferred=False,runtime_observed=False,physical_ready=False)
