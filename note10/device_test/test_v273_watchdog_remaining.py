"""Only remaining272 case4 correction and unexecuted5/6; no old run or compiler."""
import copy,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
if hashlib.sha256((HERE/'test_v272_watchdog_closure.py').read_bytes()).hexdigest()!='56b746911722c7b00a72010bbe27ef4b660e9effbb00f4eccf2b5c7f7d46bcdc':raise ValueError('immutable272 synthetic setup source')
from test_v272_watchdog_closure import setup
CASES=('corrected-outlined-name-provenance-rejection','graph-cycle-and-cap-rejection','outlined-frame-and-persistence')

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
        if not predicate:raise ValueError('new273 predicate: '+name)
        done.append(name)
    try:
        data=setup(p)
        def closure(d):
            d['bodies']['n269_begin']=d['body']('n269_begin',['b 1600','nop','nop','ret'])
            d['bodies']['OUTLINED_FUNCTION_1']=d['body']('OUTLINED_FUNCTION_1',['b 1700'])
            d['bodies']['OUTLINED_FUNCTION_2']=d['body']('OUTLINED_FUNCTION_2',['b a000'])
        damaged=copy.deepcopy(data);damaged['table']['OUTLINED_FUNCTION_9']=[dict(kind='t',address=0xb000,bytes=4,ordinal=101)]
        ok,unused,saved,captured=exercise(damaged,lambda d:d['bodies'].__setitem__('n269_begin',d['body']('n269_begin',['bl b000 <OUTLINED_FUNCTION_9>','nop','nop','ret'])),True)
        edge=saved['current_edge']
        check(ok and saved['phase']=='frontier'and saved['rejection_reason']=='one actual driver ELF/nm/SU function: OUTLINED_FUNCTION_9'and edge['target']==0xb000 and edge['resolved_symbols']==['OUTLINED_FUNCTION_9']and len(captured)==1)
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
        error.fixture_progress=dict(groups=1,variants=3,assertions=len(done),planned_assertions=3,completed_variants=len(done),completed_assertions=len(done),case_names=done);raise
    return dict(groups=1,variants=3,assertions=3,completed_variants=3,completed_assertions=3,case_names=done,host_compile_attempts=0,host_fixture_process_attempts=0,old_tests_replayed=0)
