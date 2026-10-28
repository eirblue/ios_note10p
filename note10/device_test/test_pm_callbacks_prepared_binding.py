"""Mutate the actual prepared snapshot and reject composition corruption."""
import argparse,hashlib,json,shutil,tempfile
from pathlib import Path
from pm_callbacks_binding import verify_snapshot,verify_composition

def main():
 p=argparse.ArgumentParser();p.add_argument('--artifact',required=True);p.add_argument('--output',required=True);a=p.parse_args();artifact=Path(a.artifact);o=Path(a.output);o.mkdir(parents=True,exist_ok=True);meta=json.loads((artifact/'pm-callbacks-prepared-binding.json').read_text());final=meta['final'];intermediate=meta['intermediate'];paths=set(final);rows=[]
 with tempfile.TemporaryDirectory(dir=o) as d:
  work=Path(d);shutil.copytree(artifact/'pm-callbacks-prepared',work/'pm-callbacks-prepared');verify_snapshot(work,final,paths);verify_composition(work,intermediate);rows.append({'case':'baseline','passed':True})
  for name,target in (('cpu_hook','kernel/power/note10_pm_cpus.c'),('worker_hook','arch/arm64/mm/note10_pm_timer_roundtrip.c'),('dma_hook','drivers/base/power/note10_dma_pm.c'),('noirq_hook','kernel/power/note10_pm_noirq.c'),('kconfig','kernel/power/Kconfig'),('upstream_tu','kernel/cpu_pm.c')):
   f=work/'pm-callbacks-prepared'/target;original=f.read_bytes();f.write_bytes(original+b'\n/* unexpected */\n');altered=dict(final);altered[target]=hashlib.sha256(f.read_bytes()).hexdigest()
   try:verify_snapshot(work,altered,paths);verify_composition(work,intermediate)
   except ValueError:rows.append({'case':name,'passed':True})
   else:raise AssertionError(name+' accepted')
   f.write_bytes(original)
 result={'passed':True,'cases':len(rows),'outcomes':rows,'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'binding_sha256':hashlib.sha256((Path(__file__).parent/'pm_callbacks_binding.py').read_bytes()).hexdigest(),'prepared_map_sha256':hashlib.sha256((artifact/'pm-callbacks-prepared-binding.json').read_bytes()).hexdigest()};(o/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print('prepared composition cases:',len(rows))
if __name__=='__main__':main()
