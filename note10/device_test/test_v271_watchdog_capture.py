"""Two new synthetic persist-before-reject cases; no external command."""
import hashlib,json
from pathlib import Path
CASES=('unknown-relocation-persisted','indirect-branch-persisted')
def run(output,producer,parameters):
    out=Path(output);done=[]
    try:
        for name,body,unknown,indirect in (
            (CASES[0],'00000000 <n269_begin>:\n  0: R_AARCH64_CALL26 foreign_symbol\n',['foreign_symbol'],False),
            (CASES[1],'00000000 <n269_begin>:\n  4: d63f0000 blr x0\n',[],True)):
            folder=out/name;folder.mkdir()
            result=dict(source_head='a'*40,run_id=1,build_evidence_id='b'*32,source_sha256={'synthetic.c':'c'*64})
            required={'n269_begin'};allowed=set();argv=['synthetic-objdump','-dr','--disassemble=n269_begin','synthetic.o']
            bundle=producer.capture_document(result,'synthetic.o',b'synthetic clang-14 command',required,allowed)
            try:producer.guard_binding_body(folder,bundle,'n269_begin',argv,body,{'kind':'static','bytes':0},required,allowed)
            except ValueError as error:
                if str(error)!='no new269 indirect/hardware/external callback':raise
            else:raise ValueError('new271 rejection missing')
            saved=json.loads((folder/'watchdog-capture.json').read_bytes());entry=saved['helpers']['n269_begin']
            if not(saved['schema']==producer.CAPTURE_SCHEMA and saved['source_head']==result['source_head']and saved['run_id']==result['run_id']and saved['build_evidence_id']==result['build_evidence_id']and saved['source_sha256']==result['source_sha256']and saved['complete']is False and saved['status']=='rejected'and saved['rejected_helper']=='n269_begin'and entry['argv']==argv and entry['raw_objdump']==body and entry['raw_objdump_bytes']==len(body.encode())and entry['raw_objdump_sha256']==hashlib.sha256(body.encode()).hexdigest()and entry['calls']==unknown and entry['unknown_edges']==unknown and entry['indirect_blr']is indirect and entry['guard_passed']is False):raise ValueError('new271 persisted rejection fields')
            done.append(name)
    except BaseException as error:
        error.fixture_progress=dict(groups=1,variants=2,assertions=len(done),planned_assertions=2,completed_variants=len(done),completed_assertions=len(done),case_names=done);raise
    return dict(groups=1,variants=2,assertions=2,completed_variants=2,completed_assertions=2,case_names=done,host_compile_attempts=0,host_fixture_process_attempts=0,old_tests_replayed=0)
