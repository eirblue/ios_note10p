"""Reject GIC guard source, config, metadata and evidence mutations."""
import argparse,hashlib,json,shutil,tempfile
from pathlib import Path
from gic_priority_binding import validate_core
CASES=('source-map-omitted','snapshot-map-omitted','version-omitted','prior-source-changed','final-source-changed','generated-source-changed','coherent-generated-change','case-omitted','config-disabled','image-marker-missing','unsupported-max-gic','nonbanked','package-map-missing')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--artifact',required=True);ap.add_argument('--output',required=True);a=ap.parse_args();artifact=Path(a.artifact);out=Path(a.output);out.mkdir(parents=True,exist_ok=False);base=json.loads((artifact/'build-result.json').read_text(encoding='utf8'))
 with tempfile.TemporaryDirectory() as t:
  root=Path(t)
  for n in ('pm-preconditions-prepared','pm-branch-prepared','pmu-failure-prepared','pmu-failure-model','pmu-failure-binding-model','pmu-failure-package-flow-model','gic-priority-prepared','gic-priority-model'):shutil.copytree(artifact/n,root/n)
  for n in ('Image','handoff.config'):shutil.copyfile(artifact/n,root/n)
  validate_core(root,base)
  for case in CASES:
   b=dict(base);changes=[]
   if case in ('source-map-omitted','snapshot-map-omitted','version-omitted','package-map-missing'):
    b.pop({'source-map-omitted':'gic_priority_sources_sha256','snapshot-map-omitted':'gic_priority_snapshot_sha256','version-omitted':'gic_priority_restore_version','package-map-missing':'gic_priority_package_sources_sha256'}[case])
   else:
    p=root/{'prior-source-changed':'pm-preconditions-prepared/drivers/irqchip/irq-gic.c','final-source-changed':'gic-priority-prepared/drivers/irqchip/irq-gic.c','generated-source-changed':'gic-priority-model/on.c','coherent-generated-change':'gic-priority-model/on.c','case-omitted':'gic-priority-model/result.json','config-disabled':'handoff.config','image-marker-missing':'Image','unsupported-max-gic':'handoff.config','nonbanked':'handoff.config'}[case];raw=p.read_bytes();changes.append((p,raw))
    if case=='case-omitted':m=json.loads(raw);m['cases']['on'].pop();p.write_text(json.dumps(m),encoding='utf8')
    elif case=='config-disabled':p.write_bytes(raw.replace(b'CONFIG_NOTE10_GIC_PRIORITY_RESTORE=y',b'# CONFIG_NOTE10_GIC_PRIORITY_RESTORE is not set'))
    elif case=='image-marker-missing':p.write_bytes(raw.replace(b'N10GIPR1: missing GIC priority snapshot',b'N10GIPRx: missing GIC priority snapshot'))
    elif case=='unsupported-max-gic':p.write_bytes(raw.replace(b'CONFIG_ARM_GIC_MAX_NR=1',b'CONFIG_ARM_GIC_MAX_NR=2'))
    elif case=='nonbanked':p.write_bytes(raw+b'\nCONFIG_GIC_NON_BANKED=y\n')
    else:
     p.write_bytes(raw+b'\nmutation\n')
     if case=='coherent-generated-change':
      q=root/'gic-priority-model/result.json';old=q.read_bytes();changes.append((q,old));m=json.loads(old);m['generated_sha256']['on.c']=hashlib.sha256(p.read_bytes()).hexdigest();q.write_text(json.dumps(m),encoding='utf8')
   try:validate_core(root,b)
   except (ValueError,KeyError,FileNotFoundError):pass
   else:raise RuntimeError('accepted mutation: '+case)
   finally:
    for p,raw in changes:p.write_bytes(raw)
 result={'passed':True,'cases':list(CASES),'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()};(out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
if __name__=='__main__':main()
