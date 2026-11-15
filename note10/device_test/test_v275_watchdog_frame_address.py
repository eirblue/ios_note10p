"""Three new own-frame address predicates; no compiler or old fixture entrypoint."""
import json
from pathlib import Path
CASES=('named-C-live-frame-address','named-C-address-bounds-and-merge-rejection','outlined-address-neutrality-preserved')

def run(output,producer,parameters):
    p=producer;out=Path(output);done=[];serial=0
    def rows(texts):
        return[(0x1000+4*i,*((text.split(None,1)+[''])[:2]))for i,text in enumerate(texts)]
    def evaluate(texts,frame=16,outlined=False,name='n269_publish',external=None,reject=False):
        nonlocal serial
        serial+=1;path=out/('frame-'+str(serial)+'.json');body=rows(texts);edges=external or{}
        raw=dict(name=name,rows=body,frame=frame,outlined=outlined,external=edges,passed=False)
        path.write_text(json.dumps(raw,sort_keys=True)+'\n',encoding='utf-8')
        try:
            certificate=p.own_frame(name,body,edges,frame,outlined);raw.update(passed=True,certificate=certificate)
            return not reject,certificate
        except ValueError as error:
            raw.update(rejection_reason=str(error));return reject and bool(raw['rejection_reason']),{}
        finally:path.write_text(json.dumps(raw,sort_keys=True)+'\n',encoding='utf-8')
    def check(predicate):
        if not predicate:raise ValueError('new275 predicate: '+CASES[len(done)])
        done.append(CASES[len(done)])
    try:
        body=['sub sp, sp, #0x50','stp x29, x30, [sp, #0x30]','add x29, sp, #0x30','add x0, sp, #0x8','bl 2000','add x1, sp, #0x8','mov x2, #0x28','bl 3000','ldp x29, x30, [sp, #0x30]','add sp, sp, #0x50','ret']
        ok,certificate=evaluate(body,80,external={0x1010:'named-n269_empty',0x101c:'opaque-memcpy'})
        samples=certificate['SP_address_samples'];namespace=p.scoped_closure.__globals__
        check(ok and certificate['own_peak_bytes']==80 and certificate['call_SP_offsets']=={0x1010:-80,0x101c:-80} and [s['register']for s in samples]==['x0','x1'] and all(s['SP_offset']==-80 and s['literal_offset']==8 and s['formed_entry_SP_offset']==-72 and s['live_frame_interval']==[-80,0]for s in samples) and certificate['callee_peaks_included']is False and namespace['own_frame']is p.own_frame and p.collect_binding.__globals__ is namespace and namespace['scoped_closure']is p.scoped_closure and namespace['capture_document']is p.capture_document and p._ENV['collect_binding']is p.collect_binding and namespace['classify_edge']is p.retained.classify_edge and p.retained._WATCHDOG['own_frame']is p.retained.selected.own_frame and p.retained._WATCHDOG['own_frame']is not p.own_frame)
        rejected=[]
        for instruction in ('add x0, sp, #-1','add x0, sp, #0x10','add x0, sp, #0x14','add w0, sp, #8','add x30, sp, #8','add x0, sp, #8, lsl #12'):
            rejected.append(evaluate(['sub sp, sp, #16',instruction,'add sp, sp, #16','ret'],reject=True)[0])
        rejected.append(evaluate(['add x0, sp, #0','ret'],0,reject=True)[0])
        rejected.append(evaluate(['sub sp, sp, #16','add x0, sp, #8','add sp, sp, #16','ret'],name='foreign_C',reject=True)[0])
        rejected.append(evaluate(['sub sp, sp, #16','cbz w0, 1010','sub sp, sp, #16','b 1014','nop','add x0, sp, #8','add sp, sp, #16','ret'],32,reject=True)[0])
        rejected.append(evaluate(['sub sp, sp, #16','add x0, sp, #8','ret'],reject=True)[0])
        rejected.append(evaluate(['sub sp, sp, #16','add x0, sp, #8','add sp, sp, #16','ret'],32,reject=True)[0])
        check(all(rejected))
        rejected=[]
        for instruction in ('add x0, sp, #8','add x1, sp, #0','add x29, sp, #8','add x30, sp, #8'):
            rejected.append(evaluate([instruction,'ret'],0,True,name='OUTLINED_FUNCTION_1',reject=True)[0])
        check(all(rejected)and p.BOUNDARIES is p.retained.BOUNDARIES)
    except BaseException as error:
        error.fixture_progress=dict(groups=1,variants=3,assertions=len(done),planned_assertions=3,completed_variants=len(done),completed_assertions=len(done),case_names=done);raise
    return dict(groups=1,variants=3,assertions=3,completed_variants=3,completed_assertions=3,case_names=done,host_compile_attempts=0,host_fixture_process_attempts=0,old_tests_replayed=0)
