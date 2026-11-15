"""Three new boundary-alias predicates; old fixture entrypoints never run."""
import copy,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
if hashlib.sha256((HERE/'test_v272_watchdog_closure.py').read_bytes()).hexdigest()!='56b746911722c7b00a72010bbe27ef4b660e9effbb00f4eccf2b5c7f7d46bcdc':raise ValueError('immutable synthetic setup')
from test_v272_watchdog_closure import setup
CASES=('original-boundary-alias-closure','boundary-alias-extent-and-witness-rejection','boundary-alias-control-rejection')

def run(output,producer,parameters):
    p=producer;out=Path(output);done=[];serial=0;data=setup(p)
    data['table']['memcpy']=[dict(kind='W',address=0xa000,bytes=340,ordinal=100)]
    data['table']['__memcpy']=[dict(kind='T',address=0xa000,bytes=340,ordinal=101)]
    data['table']['__pi_memcpy']=[dict(kind='T',address=0xa000,bytes=340,ordinal=102)]
    data['bodies']['n269_begin']=data['body']('n269_begin',['bl a000','nop','nop','ret'])
    def exercise(changes=None,reject=False):
        nonlocal serial
        serial+=1;folder=out/('capture-'+str(serial));folder.mkdir();current=copy.deepcopy(data)
        if changes:changes(current)
        result=dict(source_head='a'*40,run_id=1,build_evidence_id='b'*32,source_sha256={'synthetic.c':'c'*64});bundle=p.capture_document(result,'synthetic aliases');p.save_capture(folder,bundle);captures=[]
        def capture(symbol):
            captures.append((symbol['address'],symbol['bytes']));return current['bodies'][symbol['symbol']]
        try:
            closure=p.scoped_closure(folder,bundle,current['context'],current['roots'],current['table'],capture)
            return not reject,closure,bundle,captures,current
        except ValueError as error:
            bundle.update(status='rejected',complete=False,rejection_reason=str(error));p.save_capture(folder,bundle);saved=json.loads((folder/'watchdog-capture.json').read_bytes())
            return reject and saved['status']=='rejected'and saved['complete']is False and bool(saved['rejection_reason']),{},saved,captures,current
    def check(predicate):
        if not predicate:raise ValueError('new274 predicate: '+CASES[len(done)])
        done.append(CASES[len(done)])
    try:
        ok,closure,bundle,captures,current=exercise();edge=closure['nodes']['0000000000001000:16']['proof']['external_transfers'][0];classified=p.classify_edge(edge,current['context'],current['roots'])
        namespace=p.scoped_closure.__globals__
        check(
            ok and
            classified['kind']=='boundary'and classified['names']==['memcpy']and classified['aliases']==['__memcpy','__pi_memcpy','memcpy']and classified['alias_records']==edge['resolved_records']and len(edge['resolved_records'])==3 and
            {r['kind']for r in edge['resolved_records']}=={'T','W'}and {r['ordinal']for r in edge['resolved_records']}=={100,101,102}and closure['selected_extents']==6 and
            closure['outlined_extents']==0 and
            closure['opaque_external_peaks_included']is False and
            len(captures)==len(set(captures))==6 and
            (0xa000,340)not in captures and
            namespace['classify_edge']is p.classify_edge and
            p.collect_binding.__globals__ is namespace and
            namespace['scoped_closure']is p.scoped_closure and
            namespace['capture_document']is p.capture_document and
            p.capture_document.__globals__ is namespace and
            p._ENV['collect_binding']is p.collect_binding and
            p.selected.classify_edge is not p.classify_edge and
            p.selected.scoped_closure.__globals__['classify_edge']is p.selected.classify_edge and
            bundle['schema']==p.CAPTURE_SCHEMA and
            len(p.BOUNDARIES)==9)
        rejected=[]
        def interior(d):d['bodies']['n269_begin']=d['body']('n269_begin',['bl a004','nop','nop','ret'])
        def mixed(d):d['table']['__pi_memcpy'][0]['bytes']=344
        def overlapping(d):d['table']['__pi_memcpy'][0].update(address=0x9ffc,bytes=344)
        def no_witness(d):d['table'].pop('memcpy')
        def over_cap(d):
            for i in range(30):d['table']['alias_'+str(i)]=[dict(kind='t',address=0xa000,bytes=340,ordinal=200+i)]
        for change in (interior,mixed,overlapping,no_witness,over_cap):rejected.append(exercise(change,True)[0])
        # A contradictory target in the retained record group is a new alias-path input.
        bad=copy.deepcopy(edge);bad['target']+=4
        try:p.classify_edge(bad,current['context'],current['roots'])
        except ValueError:rejected.append(True)
        else:rejected.append(False)
        check(all(rejected))
        rejected=[]
        for instruction in ('blr x0','cbz w0, a000'):
            rejected.append(exercise(lambda d,instruction=instruction:d['bodies'].__setitem__('n269_begin',d['body']('n269_begin',[instruction,'nop','nop','ret'])),True)[0])
        for mnemonic,unresolved in (('blr',False),('cbz',False),('bl',True)):
            bad=copy.deepcopy(edge);bad.update(mnemonic=mnemonic,unresolved=unresolved)
            try:p.classify_edge(bad,current['context'],current['roots'])
            except ValueError:rejected.append(True)
            else:rejected.append(False)
        check(all(rejected)and p.BOUNDARIES is p.selected.BOUNDARIES and closure['whole_kernel_stack_bound_proven']is False)
    except BaseException as error:
        error.fixture_progress=dict(groups=1,variants=3,assertions=len(done),planned_assertions=3,completed_variants=len(done),completed_assertions=len(done),case_names=done);raise
    return dict(groups=1,variants=3,assertions=3,completed_variants=3,completed_assertions=3,case_names=done,host_compile_attempts=0,host_fixture_process_attempts=0,old_tests_replayed=0)
