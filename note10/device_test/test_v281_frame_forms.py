"""One new conjunction for the two demonstrated compiler frame forms."""
import copy
import v281_native_prepare as p

def refused(fn,*args):
    try:fn(*args)
    except (ValueError,KeyError):return True
    return False

def predicate():
    for name,register,size in [('n209_decode_payload',23,144),(p.retained.OWNER,2,96)]:
        rows=[(4096,'sub',f'sp, sp, #{size}'),(4100,'mov',f'x{register}, sp'),(4104,'add',f'sp, sp, #{size}'),(4108,'ret','')]
        words={4100:0x910003e0+register}
        accepted=p.own_frame(name,rows,{},size,False,words)
        assert accepted['own_peak_bytes']==size and accepted['SP_address_samples']==[dict(address=4100,register=f'x{register}',SP_offset=-size,literal_offset=0,formed_entry_SP_offset=-size,live_frame_interval=[-size,0])]
        assert refused(p.own_frame,name,rows,{},size,False,{4100:0xaa0003e0+register})
        assert refused(p.own_frame,name,rows,{},size-16,False,words)
        assert refused(p.own_frame,'OUTLINED_FUNCTION_2',rows,{},size,True,words)
        assert refused(p.own_frame,name,rows[1:],{},size,False,words)
        for args in ('sp, x0','wsp, w0','fp, x0','w29, w0','x30, sp','w30, wsp','w2, wsp'):
            bad=list(rows);bad[1]=(4100,'mov',args)
            assert refused(p.own_frame,name,bad,{},size,False,words)
        merge=[(4096,'sub',f'sp, sp, #{size}'),(4100,'cbz','x0, 100c'),(4104,'add','sp, sp, #16'),(4108,'mov',f'x{register}, sp'),(4112,'add',f'sp, sp, #{size}'),(4116,'ret','')]
        assert refused(p.own_frame,name,merge,{},size,False,{4108:0x910003e0+register})
    caller=[(4096,'stp','x29, x30, [sp, #-48]!'),(4100,'stp','x22, x21, [sp, #16]'),(4104,'mov','x29, sp'),(4108,'stp','x20, x19, [sp, #32]'),(4112,'cbz','x0, 1018'),(4116,'nop',''),(4120,'bl','2000 <OUTLINED_FUNCTION_22>'),(4124,'ldp','x29, x30, [sp], #48'),(4128,'ret','')]
    helper=[(8192,'ldp','x20, x19, [sp, #32]'),(8196,'ldp','x22, x21, [sp, #16]'),(8200,'ret','')]
    cw={4096:0xa9bd7bfd,4100:0xa90157f6,4104:0x910003fd,4108:0xa9024ff4,4120:0x94000000+((8192-4120)//4),4124:0xa8c37bfd,4128:0xd65f03c0}
    hw=dict(zip((8192,8196,8200),p.RESTORE_WORDS));external={4120:8192};incoming=[(p.CALLER,4120,'bl')]
    def shape(cr=caller,words=cw,hr=helper,hwords=hw,edges=external,ins=incoming):return p.restore_shape(cr,words,hr,hwords,edges,8192,ins)
    call=shape();cert=p.own_frame(p.CALLER,caller,external,48,False,cw)
    result=p.borrowed_certificate(cert,call,helper,0)
    assert result['contextual_caller_frame_read']is True and result['neutral_outlined']is result['standalone_leaf']is False and result['borrowed_entry_SP_intervals']==[[-16,0],[-32,-16]]and cert['call_SP_offsets'][call]==-48
    assert refused(p.own_frame,p.RESTORE,helper,{},0,True,hw)
    for index,args in ((0,'x20, x19, [sp, #48]'),(1,'x22, x21, [sp, #16]!'),(0,'x22, x21, [sp, #32]')):
        bad=list(helper);bad[index]=(bad[index][0],'ldp',args);assert refused(shape,caller,cw,bad)
    assert refused(shape,caller,cw,helper+[(8204,'nop','')])
    bad=dict(hw);bad[8192]^=1;assert refused(shape,caller,cw,helper,bad)
    for index,row in ((1,(4100,'stp','x22, x21, [sp, #32]')),(5,(4116,'str','x0, [x1]')),(4,(4112,'cbz','x0, 101c')),(7,(4124,'ldp','x29, x30, [sp], #32'))):
        bad=list(caller);bad[index]=row;assert refused(shape,bad)
    assert refused(shape,caller,cw,helper,hw,external,incoming+[(p.retained.OWNER,12288,'bl')])
    assert refused(shape,caller,cw,helper,hw,{4120:8196})
    assert refused(shape,caller,cw,helper,hw,external,[])
    bad=dict(cw);bad[4120]^=1;assert refused(shape,caller,bad)
    for key,value in [('own_peak_bytes',16),('own_peak_bytes',32),('call_SP_offsets',{4120:0}),('call_SP_offsets',{4120:-32})]:
        bad=copy.deepcopy(cert);bad[key]=value;assert refused(p.borrowed_certificate,bad,call,helper,0)
    assert refused(p.borrowed_certificate,cert,call,helper,16)
    assert (p.NAMED_CAP,p.OUTLINED_CAP,p.EXTENT_CAP)==(14,30,44)
    return dict(passed=True,groups=1,variants=1,assertions=1)
