"""One new six-predicate synthetic watchdog adapter batch; no subprocess/compiler."""
import copy,hashlib,json
from pathlib import Path
CASES=('scoped-intra-body-control-flow','duplicate-name-driver-local-closure','scope-and-provenance-rejection','transfer-frontier-rejection','graph-cycle-and-cap-rejection','outlined-frame-and-persistence')

def setup(p):
    target=p.TARGET;source='/synthetic/source/'+target[:-2]+'.c'
    command=('cmd_'+target+' := clang-14 -fstack-usage -fno-strict-aliasing -o '+target+' -c '+source+'\nsource_'+target+' := '+source+'\n').encode()
    names=[*p.ROOTS,'OUTLINED_FUNCTION_1','OUTLINED_FUNCTION_2'];sizes={n:4 for n in names};sizes['n269_begin']=16
    rows={n:dict(kind='t',address=0x1000+0x100*i,bytes=sizes[n],ordinal=i)for i,n in enumerate(names)}
    table={n:[v]for n,v in rows.items()};table['OUTLINED_FUNCTION_1'].append(dict(kind='t',address=0x9000,bytes=4,ordinal=99))
    table['memcpy']=[dict(kind='T',address=0xa000,bytes=4,ordinal=100)]
    nm=''.join(n+' t '+format(v['address']-0x1000,'x')+' '+format(v['bytes'],'x')+'\n'for n,v in rows.items())
    elf='  [ 1] .text PROGBITS 00000000 000040 001000 00 AX 0 0 4\n'+''.join(' '+str(i+1)+': '+format(v['address']-0x1000,'016x')+' '+str(v['bytes'])+' FUNC LOCAL DEFAULT 1 '+n+'\n'for i,(n,v)in enumerate(rows.items()))
    usage=''.join(source+':1:1:'+n+'\t0\tstatic\n'for n in names)
    context,roots=p.driver_provenance(command,usage,elf,nm,table)
    def body(n,instructions):
        start=rows[n]['address'];return format(start,'016x')+' <'+n+'>:\n'+''.join(' '+format(start+4*i,'x')+': d503201f '+text+'\n'for i,text in enumerate(instructions))
    bodies={n:body(n,['ret'])for n in names};bodies['n269_begin']=body('n269_begin',['cbz w0, 1008','b 1000','nop','ret'])
    return dict(context=context,roots=roots,table=table,bodies=bodies,body=body,rows=rows,command=command,usage=usage,elf=elf,nm=nm)

def run(output,producer,parameters):
    p=producer;out=Path(output);done=[];serial=0
    def exercise(data,changes=None,reject=False):
        nonlocal serial
        serial+=1;folder=out/('capture-'+str(serial));folder.mkdir();data=copy.deepcopy(data)if changes else data
        if changes:changes(data)
        result=dict(source_head='a'*40,run_id=1,build_evidence_id='b'*32,source_sha256={'synthetic.c':'c'*64})
        bundle=p.capture_document(result,'synthetic linked table');p.save_capture(folder,bundle);captured=[]
        def capture(symbol):
            key=(symbol['address'],symbol['bytes']);captured.append(key)
            return data['bodies'][symbol['symbol']]
        try:
            value=p.scoped_closure(folder,bundle,data['context'],data['roots'],data['table'],capture)
            if reject:return False,{},bundle,captured
            return True,value,bundle,captured
        except ValueError as error:
            bundle.update(status='rejected',complete=False,rejection_reason=str(error));p.save_capture(folder,bundle)
            saved=json.loads((folder/'watchdog-capture.json').read_bytes())
            return reject and saved['status']=='rejected'and saved['complete']is False and bool(saved['rejection_reason']),{},saved,captured
    def check(predicate):
        name=CASES[len(done)]
        if not predicate:raise ValueError('new272 predicate: '+name)
        done.append(name)
    try:
        data=setup(p);ok,value,bundle,captured=exercise(data)
        check(ok and value['frontier_closed']and value['acyclic']and value['nodes']['0000000000001000:16']['proof']['internal_branches']==2 and len(captured)==len(set(captured))==6)
        def closure(d):
            d['bodies']['n269_begin']=d['body']('n269_begin',['b 1600','nop','nop','ret'])
            d['bodies']['OUTLINED_FUNCTION_1']=d['body']('OUTLINED_FUNCTION_1',['b 1700'])
            d['bodies']['OUTLINED_FUNCTION_2']=d['body']('OUTLINED_FUNCTION_2',['b a000'])
        ok,value,bundle,captured=exercise(data,closure)
        check(ok and value['outlined_extents']==2 and len(captured)==len(set(captured))==8 and (0x9000,4)not in captured and value['selected_local_peak_bytes']==0)
        rejection=[]
        for raw in ('  0: R_AARCH64_CALL26 foreign\n','0000000000001000 <n269_begin>:\n 1000: d503201f ret\n',data['bodies']['n269_begin']+'000000000000a000 <memcpy>:\n a000: d503201f ret\n'):
            rejection.append(exercise(data,lambda d,raw=raw:d['bodies'].__setitem__('n269_begin',raw),True)[0])
        for field,value_ in (('source','/wrong.c'),('kind','dynamic'),('bytes',8)):
            damaged=copy.deepcopy(data);damaged['context']['frames']['OUTLINED_FUNCTION_1'][field]=value_
            def bad(d):closure(d)
            rejection.append(exercise(damaged,bad,True)[0])
        try:p.driver_provenance(data['command'],data['usage'],data['elf'].replace(' FUNC LOCAL DEFAULT 1 n269_begin',' FUNC GLOBAL DEFAULT 1 n269_begin'),data['nm'],data['table'])
        except ValueError:rejection.append(True)
        else:rejection.append(False)
        check(all(rejection))
        rejection=[]
        for ins in ('bl 1004','bl b000','blr x0','cbz w0, a000','bl a000 <OUTLINED_FUNCTION_9>'):
            if ins.endswith('<OUTLINED_FUNCTION_9>'):
                damaged=copy.deepcopy(data);damaged['table']['OUTLINED_FUNCTION_9']=[dict(kind='t',address=0xb000,bytes=4,ordinal=101)]
            else:damaged=data
            rejection.append(exercise(damaged,lambda d,ins=ins:d['bodies'].__setitem__('n269_begin',d['body']('n269_begin',[ins,'nop','nop','ret'])),True)[0])
        check(all(rejection)and len(p.BOUNDARIES)==9)
        rejection=[exercise(data,lambda d:d['bodies'].__setitem__('n269_begin',d['body']('n269_begin',['bl 1000','nop','nop','ret'])),True)[0]]
        oversized=copy.deepcopy(data);oversized['table']['n269_begin'][0]['bytes']=8196
        rejection.append(exercise(oversized,reject=True)[0])
        aliases=copy.deepcopy(data)
        for i in range(33):aliases['table']['alias'+str(i)]=[dict(kind='t',address=0x1000,bytes=16,ordinal=200+i)]
        rejection.append(exercise(aliases,reject=True)[0])
        frontier=copy.deepcopy(data);closure(frontier)
        for i in range(1,34):
            name='OUTLINED_FUNCTION_'+str(i);address=0x1500+0x100*i
            frontier['table'][name]=[dict(kind='t',address=address,bytes=4,ordinal=300+i)]
            frontier['context']['functions'][name]=[dict(address=address-0x1000,bytes=4,binding='LOCAL',section_index='1')]
            frontier['context']['object_rows'][name]=[[name,'t',format(address-0x1000,'x'),'4']]
            frontier['context']['frames'][name]=dict(source=frontier['context']['TU']['translation_unit'],bytes=0,kind='static')
            frontier['bodies'][name]=format(address,'016x')+' <'+name+'>:\n '+format(address,'x')+': d503201f b '+format(address+0x100,'x')+'\n'
        rejection.append(exercise(frontier,reject=True)[0]);check(all(rejection))
        rejection=[]
        for instructions in (['mov x0, sp'],['mov wsp, w0'],['mov x30, x0'],['mov w30, w0'],['bl a000'],['mov x29, x0'],['mov w29, w0'],['mov fp, x0'],['mov lr, x0'],['mrs x0, tpidr_el1']):
            def bad(d,instructions=instructions):closure(d);d['bodies']['OUTLINED_FUNCTION_1']=d['body']('OUTLINED_FUNCTION_1',instructions)
            rejection.append(exercise(data,bad,True)[0])
        missing=copy.deepcopy(data);missing['context']['frames'].pop('OUTLINED_FUNCTION_1')
        rejection.append(exercise(missing,closure,True)[0])
        # A failed later capture sees the prior successful frame already on disk.
        folder=out/'persistence';folder.mkdir();result=dict(source_head='a'*40,run_id=1,build_evidence_id='b'*32,source_sha256={});persisted=p.capture_document(result,'synthetic');calls=[]
        def stop_after_first(symbol):
            if calls:
                saved=json.loads((folder/'watchdog-capture.json').read_bytes());calls.append(any(v['frame_passed']for v in saved['helpers'].values()));raise ValueError('synthetic next tool stop')
            calls.append(symbol['symbol']);return data['bodies'][symbol['symbol']]
        try:p.scoped_closure(folder,persisted,data['context'],data['roots'],data['table'],stop_after_first)
        except ValueError:pass
        check(all(rejection)and len(calls)==2 and calls[1]is True)
    except BaseException as error:
        error.fixture_progress=dict(groups=1,variants=6,assertions=len(done),planned_assertions=6,completed_variants=len(done),completed_assertions=len(done),case_names=done);raise
    return dict(groups=1,variants=6,assertions=6,completed_variants=6,completed_assertions=6,case_names=done,host_compile_attempts=0,host_fixture_process_attempts=0,old_tests_replayed=0)
