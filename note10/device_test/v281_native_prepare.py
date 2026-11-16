"""281 recognizes two bounded compiler frame forms in the seal closure only."""
import re
from pathlib import Path
from types import SimpleNamespace
import v280_native_prepare as retained

p,require,sha,bind=retained.p,retained.require,retained.sha,retained.bind
scoped=retained.scoped
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
WORKFLOW='.github/workflows/note10-v281-native-prepare.yml';JOB='v281-native-prepare'
BUILD_SCHEMA='note10-v281-holder-carrier-build-v1'
CONTEXT_SCHEMA='note10-v281-holder-carrier-public-input-v1'
MANIFEST_SCHEMA='note10-v281-holder-carrier-sealed-members-v1'
SUCCESS_MEMBERS=retained.SUCCESS_MEMBERS
NAMED,NAMED_CAP,OUTLINED_CAP,EXTENT_CAP=retained.NAMED,14,30,44
RESTORE='OUTLINED_FUNCTION_22';CALLER='n210_receipt_matches'
RESTORE_WORDS=(0xa9424ff4,0xa94157f6,0xd65f03c0)
RESTORE_ROWS=(('ldp','x20,x19,[sp,#32]'),('ldp','x22,x21,[sp,#16]'),('ret',''))
NEW_FILES=('v281_native_prepare.py','test_v281_frame_forms.py')
CARRIED279=retained.CARRIED279
CARRIED280=dict(passed=True,groups=1,variants=1,assertions=1,host_compile_attempts=0,host_fixture_process_attempts=0,result_sha256='d4fb5941f70eddf67c2fc318209694a4eca20234111258a3f7f3f2e85260579e',source_head='5225bc1bcd34117a5445ddc6824baecbcb0e734c',replayed=False)
stack_once=bind(retained.stack_once,{**retained.stack_once.__globals__,'_STACK':{}})
stream_candidate=SimpleNamespace(**{**vars(retained.stream_candidate),'verify_stack_evidence':stack_once})

def source_pins():
    pins=retained.source_pins();pins.pop(retained.WORKFLOW)
    pins.update({'note10/device_test/'+n:sha(p.ordinary(HERE/n))for n in NEW_FILES})
    pins[WORKFLOW]=sha(p.ordinary(ROOT/WORKFLOW));return pins

def public_context(head,passed):
    value=retained.public_context(head,passed)
    value.update(schema=CONTEXT_SCHEMA,source_sha256=source_pins(),carried280_fixture_PASS=CARRIED280)
    return value

def instruction_words(text):
    words={}
    for line in text.splitlines():
        m=re.match(r'^\s*([0-9a-f]+):\s+([0-9a-f]{8})\s+',line)
        if m:
            address=int(m[1],16);require(address not in words,'one actual instruction encoding')
            words[address]=int(m[2],16)
    return words

def own_frame(name,rows,external,frame,outlined,words=None):
    normalized=[]
    for address,op,args in rows:
        alias=re.fullmatch(r'x([0-9]|1[0-9]|2[0-8]),sp',scoped.flow.normalized(args))if op=='mov'else None
        if alias:
            require(not outlined and name in NAMED and words is not None and words.get(address)==0x910003e0+int(alias[1]),'actual ADD-immediate-zero SP read alias in fixed named C domain')
            normalized.append((address,'add','x'+alias[1]+', sp, #0'))
        else:normalized.append((address,op,args))
    return retained.own_frame(name,normalized,external,frame,outlined)

def restore_shape(caller_rows,caller_words,helper_rows,helper_words,external,helper_address,incoming):
    """Check one source-owned borrowed-frame read, never a standalone leaf."""
    norm=lambda rows:tuple((op,scoped.flow.normalized(args))for _,op,args in rows)
    require(len(helper_rows)==3 and norm(helper_rows)==RESTORE_ROWS and tuple(helper_words.get(a)for a,_,_ in helper_rows)==RESTORE_WORDS,'exact two fixed-offset GPR loads and RET; no helper SP write/pop')
    require(len(caller_rows)>=7 and norm(caller_rows[:4])==(('stp','x29,x30,[sp,#-48]!'),('stp','x22,x21,[sp,#16]'),('mov','x29,sp'),('stp','x20,x19,[sp,#32]')),'exact caller48 saved FP/LR and GPR slots')
    require(tuple(caller_words.get(a)for a,_,_ in caller_rows[:4])==(0xa9bd7bfd,0xa90157f6,0x910003fd,0xa9024ff4),'actual caller save encodings')
    call=caller_rows[-3][0]
    require(caller_rows[-3][1]=='bl'and call in external and external[call]==helper_address and norm(caller_rows[-2:])==(('ldp','x29,x30,[sp],#48'),('ret',''))and tuple(caller_words.get(a)for a,_,_ in caller_rows[-2:])==(0xa8c37bfd,0xd65f03c0),'caller exact helper return then FP/LR restore/pop48/terminal return')
    word=caller_words.get(call,0);displacement=word&0x3ffffff
    if displacement&0x2000000:displacement-=0x4000000
    require(word&0xfc000000==0x94000000 and call+4*displacement==helper_address,'actual direct BL encoding joins the restore entry')
    require(incoming==[(CALLER,call,'bl')],'one selected source-owned direct caller, no extra incoming edge')
    require(all(op!='ret'for _,op,_ in caller_rows[:-1]),'all caller returns use joined suffix')
    # No arbitrary pointer-store interpretation: there are no stores after saves.
    for index,(address,op,args)in enumerate(caller_rows):
        if index>=4:
            require(not op.startswith(('st','cas','swp','ldadd','ldclr','ldeor','ldset')),'no intervening saved-slot store or atomic write')
            if re.search(r'\b(?:sp|wsp|x29|w29|fp)\b',args):require(index==len(caller_rows)-2,'no unaccounted caller SP/FP operation')
        nexts=scoped.flow.successors(caller_rows,index,external)
        for target in nexts:
            if target>=len(caller_rows)-2:require(target==index+1,'no branch bypass of restore call/pop/return')
            if index>=4:require(target>=4,'no branch reentering caller saves')
    return call

def borrowed_certificate(caller_certificate,call,helper_rows,frame):
    require(frame==0 and caller_certificate['own_peak_bytes']==48 and caller_certificate['call_SP_offsets'].get(call)==-48,'actual caller per-call depth48 and actual helper SU0')
    intervals=[]
    for _,op,args in helper_rows[:2]:
        access=scoped.flow.memory(op,args)
        require(access and access['load']and access['base']=='sp'and not access['pre']and access['post']==0 and access['width']==16,'fixed caller-SP reads without writeback')
        start=-48+access['offset'];end=start+access['width']
        require(-32<=start<end<=0,'borrowed reads inside matching saved GPR slots, excluding FP/LR')
        intervals.append([start,end])
    require(intervals==[[-16,0],[-32,-16]],'exact joined caller-owned read ranges')
    return dict(own_peak_bytes=0,call_SP_offsets={},neutral_outlined=False,normal_ABI_call_return_assumed=True,callee_peaks_included=False,SP_address_samples=[],contextual_caller_frame_read=True,standalone_leaf=False,caller=CALLER,caller_call=call,caller_SP_offset=-48,caller_live_frame_bytes=48,borrowed_entry_SP_intervals=intervals,helper_SP_change=0,original_FP_LR_restored_by_caller=True)

def restore_inputs(raw,table):
    def body(name):
        require(name in table and len(table[name])==1,'unique exact contextual function')
        record=dict(name=name,**table[name][0],offset=0)
        symbol=scoped.symbol_extent(table,name,record,name==RESTORE)
        text=raw['bodies'][format(symbol['address'],'016x')+':'+str(symbol['bytes'])]
        proof=scoped.scoped_transfers(text,symbol,table)
        return record,symbol,scoped.flow.parse_body(text,proof),instruction_words(text),proof
    caller,cs,cr,cw,cp=body(CALLER);helper,hs,hr,hw,hp=body(RESTORE)
    require(cs['bytes']==260 and hs['bytes']==12 and not hp['external_transfers'],'one exact caller and full restore extent')
    item=raw['objects'][retained.OWNER_TARGET]
    context,roots,reader=retained.provenance(retained.OWNER_TARGET,(retained.OWNER,'n279_layout_witness',*retained.VALIDATORS),item,table)
    joined=reader(context,helper,True)
    require(joined['object']==retained.OWNER_TARGET and joined['binding']=='LOCAL'and joined['frame']['bytes']==0 and roots[CALLER]['frame']['bytes']==48 and joined['section_index']in context['deltas']and joined['object_address']+context['deltas'][joined['section_index']]==hs['address'],'same actual init.o source/ELF/staticSU/linked contextual join')
    external={e['address']:e['target']for e in cp['external_transfers']}
    incoming=[]
    for ident,text in raw['bodies'].items():
        address,size=ident.split(':');key=(int(address,16),int(size))
        names=[n for n,records in table.items()for record in records if(record['address'],record['bytes'])==key]
        require(names,'actual captured source extent')
        symbol=dict(symbol=names[0],address=key[0],bytes=key[1],aliases=names)
        proof=scoped.scoped_transfers(text,symbol,table)
        for edge in proof['external_transfers']:
            if edge['target']==hs['address']:
                require(names==[CALLER]and not edge['unresolved']and len(edge['resolved_records'])==1 and edge['resolved_records'][0]['offset']==0,'exact unaliased contextual incoming entry')
                incoming.append((CALLER,edge['address'],edge['mnemonic']))
    call=restore_shape(cr,cw,hr,hw,external,hs['address'],incoming)
    words={}
    for text in raw['bodies'].values():
        for address,word in instruction_words(text).items():
            require(address not in words,'nonoverlapping selected body encodings')
            words[address]=word
    return dict(call=call,caller_rows=cr,helper_rows=hr,helper_address=hs['address'],words=words,provenance=joined)

def verify_seal(raw,linked,stack_data,profile,binding):
    context=restore_inputs(raw,scoped.reader.linked_symbols(linked));state={}
    def frame(name,rows,external,actual_frame,outlined):
        if name==RESTORE:
            require(outlined and rows==context['helper_rows']and not external and 'caller'in state and 'restore'not in state,'joined restore only after actual caller frame proof')
            state['restore']=borrowed_certificate(state['caller'],context['call'],rows,actual_frame)
            return state['restore']
        certificate=own_frame(name,rows,external,actual_frame,outlined,context['words'])
        if name==CALLER:
            require(rows==context['caller_rows']and actual_frame==48 and not outlined,'actual joined caller body/frame')
            state['caller']=certificate
        return certificate
    env={**retained.verify_seal.__globals__,'own_frame':frame,'bcmp_certificate':bcmp_certificate,'stack_once':stack_once,'stream_candidate':stream_candidate}
    verify=retained._bind(retained.verify_seal,env,{'note10-v280-seal-raw-v1':'note10-v281-seal-raw-v1','note10-v280-seal-target-v1':'note10-v281-seal-target-v1'})
    value=verify(raw,linked,stack_data,profile,binding)
    require('restore'in state,'actual contextual restore reached in closed selected graph')
    value['contextual_restore']=dict(certificate=state['restore'],provenance=context['provenance'],selected_extent_count=1)
    return value

_BCMP_ENV={**retained.bcmp_certificate.__globals__,'own_frame':own_frame}
bcmp_certificate=bind(retained.bcmp_certificate,_BCMP_ENV)
_COLLECT_ENV={**retained.collect_binding.__globals__,'verify_seal':verify_seal,'stream_candidate':stream_candidate}
collect_binding=retained._bind(retained.collect_binding,_COLLECT_ENV,{'note10-v280-seal-raw-v1':'note10-v281-seal-raw-v1'})
_bind=retained._bind
_ENV={**retained._ENV,**{n:globals()[n]for n in ('WORKFLOW','JOB','BUILD_SCHEMA','CONTEXT_SCHEMA','MANIFEST_SCHEMA','SUCCESS_MEMBERS','source_pins','public_context','collect_binding','stream_candidate')}}
run_build=_bind(retained.run_build,_ENV,{'note10/private/v280-ci-native-prepare':'note10/private/v281-ci-native-prepare','v280':'v281','"-v280-bcmp-bridge"':'"-v281-frame-forms"'})
seal=_bind(retained.seal,_ENV,{})
_ENV.update(run_build=run_build,seal=seal)
main=_bind(retained.main,_ENV,{})
if __name__=='__main__':main()
