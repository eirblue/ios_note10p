"""Bind the complete v45 source composition to immutable v44 and inspect hooks."""
import argparse,hashlib,json,shutil
from pathlib import Path
from prepare_ehld_lock_audit import prepare,snapshot,CHANGED,FILES

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--v44-source',required=True,type=Path);p.add_argument('--v44-composition',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
 base,prior,out=a.v44_source,a.v44_composition,a.output
 if out.exists():raise ValueError('output exists')
 prior_map=json.loads(prior.read_text(encoding='utf8'))['snapshot_sha256']
 actual={x.relative_to(base).as_posix() for x in base.rglob('*') if x.is_file()}
 if actual!=set(prior_map):raise ValueError('v44 baseline file allowlist differs')
 if any(sha(base/n)!=d for n,d in prior_map.items()):raise ValueError('v44 source snapshot hash differs')
 out.mkdir(parents=True);source=out/'source';shutil.copytree(base,source)
 report=prepare(source,{'rcu_context_snapshot_sha256':prior_map})
 report['rcu_context_snapshot_sha256']=prior_map
 snapshot_dir=out/'snapshot';snapshot_map=snapshot(source,snapshot_dir,report)
 expected=set(prior_map)|set(FILES)
 if set(snapshot_map)!=expected or len(snapshot_map)!=len(prior_map)+len(FILES):raise ValueError('final full-source snapshot count differs')
 if any((source/n).read_bytes()!=(snapshot_dir/n).read_bytes() for n in expected):raise ValueError('full-source bytes differ')
 chain=(source/'kernel/note10_pm_pre_chain.c').read_text(encoding='utf8')
 capture=(source/'kernel/power/note10_pm_pre_capture.c').read_text(encoding='utf8')
 worker=(source/'arch/arm64/mm/note10_pm_timer_roundtrip.c').read_text(encoding='utf8')
 getter=(source/'drivers/soc/samsung/debug/note10_ehld_lock_getter.c').read_text(encoding='utf8')
 checks={
  'collector-once':chain.count('n10_ehld_lock_collect(n,out,out->count-1,generation)')==1,
  'final-chain-check':chain.count('n10_ehld_lock_complete(out,generation)')==1,
  'check-before-unlock':chain.index('n10_ehld_lock_complete(out,generation)')<chain.index('spin_unlock_irqrestore(&cpu_pm_notifier_chain.lock,flags);'),
  'lifecycle-hooks':capture.count('n10_ehld_lock_begin(generation)')==1 and capture.count('n10_ehld_lock_finish(s->error)')==1 and capture.count('n10_ehld_lock_invalidate()')>=2,
  'worker-ifdef':worker.count('#ifdef CONFIG_NOTE10_EHLD_LOCK_AUDIT')>=3 and worker.count('n10_report_ehld_lock(pm.qgeneration,0)')==1,
  'getter-no-event-pmu':all(x not in getter for x in ('->event','perf_event','PMU','rb_node','attr')),
  'config-default-off':'config NOTE10_EHLD_LOCK_AUDIT' in (source/'kernel/power/Kconfig').read_text(encoding='utf8') and '\tdefault n' in (source/'kernel/power/Kconfig').read_text(encoding='utf8').split('config NOTE10_EHLD_LOCK_AUDIT',1)[1],
 }
 if not all(checks.values()):raise ValueError('composition hook proof failed: '+repr(checks))
 result={'passed':True,'hardware_verified':False,'baseline_files':len(prior_map),'final_files':len(snapshot_map),'prepared_sha256':report['ehld_lock_prepared_sha256'],'snapshot_sha256':snapshot_map,'checks':checks,'harness_sha256':sha(Path(__file__))}
 (out/'composition-proof.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
 print('v45 composed full snapshot: 73 baseline + 5 helpers verified')
if __name__=='__main__':main()
