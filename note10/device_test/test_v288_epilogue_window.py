"""One fresh post-RET-block conjunction, with two direct window/bypass negatives."""
from copy import deepcopy
import v288_native_prepare as producer


def predicate():
    p=producer
    helper=dict(address=0x3000,bytes=20)
    helper_rows=[(0x3000+4*i,w,'ret' if w==0xd65f03c0 else 'nop','') for i,w in enumerate(p.INIT_WORDS)]
    def provenance(frame):return dict(TU=p.OWNER_TARGET,object_sha256='a'*64,section=1,delta=0,static_SU_bytes=frame)
    prefix=(0xa9bb7bfd,0xf9000bf9,0x910003fd,0xa9025ff8,0xa90357f6,0xa9044ff4)
    decoded=(('stp','x29,x30,[sp,#-80]!'),('str','x25,[sp,#16]'),('mov','x29,sp'),
        ('stp','x24,x23,[sp,#32]'),('stp','x22,x21,[sp,#48]'),('stp','x20,x19,[sp,#64]'))
    callers=[];incoming=[]
    for name,address in [('n285_readback_pages',0x4000),('n217_page_io',0x5000)]:
        rows=[(address+4*i,w,*decoded[i]) for i,w in enumerate(prefix)]
        call=address+28
        rows += [(address+24,0x34000080,'cbz','w0,'+format(address+40,'x')),
            (call,0x94000000|(((helper['address']-call)//4)&0x3ffffff),'bl',format(helper['address'],'x')),
            (address+32,0xa8c57bfd,'ldp','x29,x30,[sp],#80'),(address+36,0xd65f03c0,'ret',''),
            (address+40,0xd503201f,'nop',''),(address+44,0x17fffffc,'b',format(call,'x'))]
        callers.append(dict(name=name,frame=80,rows=rows,provenance=provenance(80)));incoming.append((name,call,'bl'))
    positive=p.init_restore(helper,helper_rows,callers,incoming,provenance(0))
    def refused(changed):
        try:p.init_restore(helper,helper_rows,changed,incoming,provenance(0))
        except ValueError:return True
        return False
    word_bad=deepcopy(callers);a,w,op,args=word_bad[0]['rows'][8];word_bad[0]['rows'][8]=(a,w^1,op,args)
    bypass=deepcopy(callers);a,_,op,_=bypass[0]['rows'][11];target=bypass[0]['rows'][8][0]
    bypass[0]['rows'][11]=(a,0x14000000|(((target-a)//4)&0x3ffffff),op,format(target,'x'))
    assert positive['neutral_outlined'] is positive['standalone_leaf'] is False and refused(word_bad) and refused(bypass)
    return dict(passed=True,groups=1,variants=1,assertions=1)
