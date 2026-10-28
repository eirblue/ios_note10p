"""Exercise the complete callback binding against actual model artifacts."""
import argparse,copy,hashlib,json,shutil,tempfile
from pathlib import Path
from pm_callbacks_binding import _validate_core,MARKERS

def main():
 p=argparse.ArgumentParser();p.add_argument('--artifact',required=True);p.add_argument('--output',required=True);a=p.parse_args();artifact=Path(a.artifact);o=Path(a.output);o.mkdir(parents=True,exist_ok=True);build=json.loads((artifact/'pm-callbacks-binding-input.json').read_text());rows=[]
 with tempfile.TemporaryDirectory(dir=o) as temp:
  work=Path(temp)
  for n in ('handoff.config','Image','pm-callbacks-prepared-binding.json') :shutil.copyfile(artifact/n,work/n)
  for n in ('prepared','prepared-binding-model','lock-model','dispatcher-model','families-model','producer-model','integration-model','decoder-model','binding-model'):
   shutil.copytree(artifact/('pm-callbacks-'+n),work/('pm-callbacks-'+n))
  for n in ('cpu-pm-failure-guard-model','pm-build-concurrency-model'):shutil.copytree(artifact/n,work/n)
  if not _validate_core(work,build):raise AssertionError('baseline disabled')
  rows.append({'case':'baseline','passed':True})
  def reject(name,change,restore):
   change()
   try:_validate_core(work,build)
   except (ValueError,FileNotFoundError,KeyError):rows.append({'case':name,'passed':True})
   else:raise AssertionError(name+' accepted')
   finally:restore()
  old=build.pop('pm_callbacks_diagnostic');reject('metadata_omitted',lambda:None,lambda:build.update(pm_callbacks_diagnostic=old))
  img=work/'Image';raw=img.read_bytes();reject('image_marker',lambda:img.write_bytes(raw.replace(MARKERS[0],b'XXXXXXXX')),lambda:img.write_bytes(raw))
  source=work/'pm-callbacks-prepared/kernel/cpu_pm.c';raw=source.read_bytes();reject('snapshot_corrupt',lambda:source.write_bytes(raw+b'x'),lambda:source.write_bytes(raw))
  extra=work/'pm-callbacks-prepared/unlisted';reject('snapshot_extra',lambda:extra.write_bytes(b'x'),lambda:extra.unlink())
  old=copy.deepcopy(build['pm_callbacks_intermediate_sha256']);reject('intermediate_mismatch',lambda:build['pm_callbacks_intermediate_sha256'].__setitem__('kernel/power/suspend.c','0'*64),lambda:build.update(pm_callbacks_intermediate_sha256=old))
  log=work/'pm-callbacks-producer-model/mode-0.log';raw=log.read_bytes();reject('producer_log',lambda:log.write_bytes(raw+b'x'),lambda:log.write_bytes(raw))
  model=work/'pm-callbacks-dispatcher-model/result.json';raw=model.read_bytes();alter=json.loads(raw);alter['source_sha256']['pm_callbacks_backend.c']='0'*64;reject('source_model',lambda:model.write_text(json.dumps(alter),encoding='utf-8'),lambda:model.write_bytes(raw))
  cfg=work/'handoff.config';origcfg=cfg.read_bytes();img=work/'Image';origimg=img.read_bytes();oldmeta=build['pm_callbacks_diagnostic']
  def omit_inventory():
   cfg.write_bytes(origcfg.replace(b'CONFIG_NOTE10_PM_CALLBACK_INVENTORY=y',b'# CONFIG_NOTE10_PM_CALLBACK_INVENTORY is not set'))
   data=origimg
   for marker in MARKERS:data=data.replace(marker,b'X'*len(marker))
   img.write_bytes(data);build['pm_callbacks_diagnostic']=False
  def restore_inventory():cfg.write_bytes(origcfg);img.write_bytes(origimg);build['pm_callbacks_diagnostic']=oldmeta
  reject('guard_scope',omit_inventory,restore_inventory)
  guard=work/'cpu-pm-failure-guard-model/result.json';raw=guard.read_bytes();reject('guard_missing',lambda:guard.unlink(),lambda:guard.write_bytes(raw))
  alter=json.loads(raw);alter['source_sha256']['kernel/cpu_pm.c']='0'*64;reject('guard_source',lambda:guard.write_text(json.dumps(alter),encoding='utf-8'),lambda:guard.write_bytes(raw))
  log=work/'cpu-pm-failure-guard-model/case-0.log';raw=log.read_bytes();reject('guard_log',lambda:log.write_bytes(raw+b'x'),lambda:log.write_bytes(raw))
 model_dirs=('prepared-binding','lock','dispatcher','families','producer','decoder','binding','integration')
 manifest={};cases={}
 for name in model_dirs:
  directory=artifact/('pm-callbacks-'+name+'-model');report=json.loads((directory/'result.json').read_text(encoding='utf-8'));cases[name]=report.get('outcomes',[])
  for f in sorted(directory.iterdir()):
   if f.is_file() and f.suffix in ('.json','.c','.log'):manifest[f.relative_to(artifact).as_posix()]=hashlib.sha256(f.read_bytes()).hexdigest()
 result={'manifest':manifest,'model_outcomes':cases,'passed':True,'cases':len(rows),'outcomes':rows,'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'binding_sha256':hashlib.sha256((Path(__file__).parent/'pm_callbacks_binding.py').read_bytes()).hexdigest(),'binding_input_sha256':hashlib.sha256((artifact/'pm-callbacks-binding-input.json').read_bytes()).hexdigest()};(o/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print('full callback binding cases:',len(rows))
if __name__=='__main__':main()
