"""One new production-context conjunction; no historical capture or fixture."""
from copy import deepcopy
import v286_native_prepare as producer


def predicate():
    p=producer
    def rows(address,words):
        return [(address+4*i,w,'ret' if w==0xd65f03c0 else 'nop','') for i,w in enumerate(words)]
    def call(address,target):return (address,0x94000000|(((target-address)//4)&0x3ffffff),'bl',format(target,'x'))
    def provenance(target,frame):return dict(TU=target,object_sha256='a'*64,section=1,delta=0,static_SU_bytes=frame)
    def refused(action):
        try:action()
        except ValueError:return True
        return False
    fp=(0x1000,0xd10013a1,'sub','x1,x29,#4')
    fp_ok=p.fp_address(fp,-144,-96)['formed_entry_SP_offset']==-100
    helper=dict(address=0x3000,bytes=20)
    init_provenance=provenance(p.OWNER_TARGET,0)
    prefix=(0xa9bb7bfd,0xf9000bf9,0x910003fd,0xa9025ff8,0xa90357f6,0xa9044ff4)
    decoded=(('stp','x29,x30,[sp,#-80]!'),('str','x25,[sp,#16]'),('mov','x29,sp'),
        ('stp','x24,x23,[sp,#32]'),('stp','x22,x21,[sp,#48]'),('stp','x20,x19,[sp,#64]'))
    callers=[];incoming=[]
    for name,address in [('n285_readback_pages',0x4000),('n217_page_io',0x5000)]:
        rr=[(address+4*i,w,*decoded[i]) for i,w in enumerate(prefix)]
        rr += [call(address+24,helper['address']),(address+28,0xa8c57bfd,'ldp','x29,x30,[sp],#80'),(address+32,0xd65f03c0,'ret','')]
        callers.append(dict(name=name,frame=80,rows=rr,provenance=provenance(p.OWNER_TARGET,80)));incoming.append((name,address+24,'bl'))
    init_ok=p.init_restore(helper,rows(0x3000,p.INIT_WORDS),callers,incoming,init_provenance)['neutral_outlined'] is False
    target='arch/arm64/mm/v230_runtime_relocation.o'
    save=dict(record=dict(address=0x7000),rows=rows(0x7000,p.SAVE_WORDS))
    restore=dict(record=dict(address=0x7100),rows=rows(0x7100,p.RESTORE_WORDS))
    rr=[(0x6000,0xa9ba7bfd,'stp','x29,x30,[sp,#-96]!'),call(0x6004,0x7000),
        (0x6008,0xd106c3ff,'sub','sp,sp,#432'),(0x600c,0xd503201f,'nop',''),
        (0x6010,0x9106c3ff,'add','sp,sp,#432'),call(0x6014,0x7100),
        (0x6018,0xa8c67bfd,'ldp','x29,x30,[sp],#96'),(0x601c,0xd65f03c0,'ret','')]
    caller=dict(name='adt_node',frame=528,rows=rr,provenance=provenance(target,528))
    edges=dict(save=[('adt_node',0x6004,'bl')],restore=[('adt_node',0x6014,'bl')])
    sources=dict(save=provenance(target,0),restore=provenance(target,0))
    pair=p.validator_pair(caller,save,restore,edges,sources)
    bad_save=deepcopy(save);a,w,op,args=bad_save['rows'][1];bad_save['rows'][1]=(a,w^1,op,args)
    bad_caller=deepcopy(caller);a,w,op,args=bad_caller['rows'][-2];bad_caller['rows'][-2]=(a,w^1,op,args)
    bad_sources=deepcopy(sources);bad_sources['save']['delta']=4
    negatives=[refused(lambda:p.fp_address((fp[0],fp[1]^1,fp[2],fp[3]),-144,-96)),
        refused(lambda:p.init_restore(helper,rows(0x3000,p.INIT_WORDS),callers,incoming+[('third',0x9000,'bl')],init_provenance)),
        refused(lambda:p.validator_pair(caller,bad_save,restore,edges,sources)),
        refused(lambda:p.validator_pair(bad_caller,save,restore,edges,sources)),
        refused(lambda:p.validator_pair(caller,save,restore,edges,bad_sources))]
    assert fp_ok and init_ok and set(pair)=={'save','restore'} and all(v['neutral_outlined'] is v['standalone_leaf'] is False for v in pair.values()) and len(negatives)==5 and all(negatives)
    return dict(passed=True,groups=1,variants=1,assertions=1)
