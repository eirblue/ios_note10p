"""Exercise fail-closed Image/config/metadata scope decisions."""
import argparse,hashlib,json,tempfile
from pathlib import Path
from pm_callbacks_binding import assert_scope,verify_snapshot,MARKERS,REQUIRED

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);o=Path(p.parse_args().output);o.mkdir(parents=True,exist_ok=True);rows=[]
 with tempfile.TemporaryDirectory(dir=o) as d:
  root=Path(d); config=[b'CONFIG_NOTE10_PM_CALLBACK_INVENTORY=y',*REQUIRED]; image=b'\0'.join(MARKERS);build={'pm_callbacks_diagnostic':True,'pm_callbacks_evidence_version':1}
  cases=[('enabled',config,image,build,True),('metadata_omitted',config,image,{},False),('version_omitted',config,image,{'pm_callbacks_diagnostic':True},False),('marker_missing',config,image.replace(MARKERS[0],b'X'),build,False),('config_omitted',config[1:],image,build,False),('debug_enabled',config+[b'CONFIG_DEBUG_SNAPSHOT_SPINLOCK=y'],image,build,False),('logbuf_wrong',[x for x in config if x!=b'CONFIG_LOG_BUF_SHIFT=21']+[b'CONFIG_LOG_BUF_SHIFT=20'],image,build,False),('off',[],b'',{},True),('off_marker',[],image,{},False)]
  for name,cfg,img,meta,accepted in cases:
   (root/'handoff.config').write_bytes(b'\n'.join(cfg));(root/'Image').write_bytes(img)
   try:assert_scope(root,meta);ok=True
   except ValueError:ok=False
   if ok!=accepted:raise AssertionError(name)
   rows.append({'case':name,'passed':True,'accepted':ok})
  snap=root/'pm-callbacks-prepared';(snap/'a').mkdir(parents=True);f=snap/'a/file.c';f.write_bytes(b'prepared'); expected={'a/file.c':hashlib.sha256(b'prepared').hexdigest()}
  for name,action,accepted in (('snapshot_good',lambda:None,True),('snapshot_corrupt',lambda:f.write_bytes(b'bad'),False),('snapshot_missing',lambda:f.unlink(),False),('snapshot_extra',lambda:(f.write_bytes(b'prepared'),(snap/'extra').write_bytes(b'x')),False),('snapshot_extra_dir',lambda:((snap/'extra').unlink(),(snap/'unlisted').mkdir()),False)):
   action()
   try:verify_snapshot(root,expected,set(expected));ok=True
   except ValueError:ok=False
   if ok!=accepted:raise AssertionError(name)
   rows.append({'case':name,'passed':True,'accepted':ok})
 (o/'result.json').write_text(json.dumps({'passed':True,'outcomes':rows,'cases':len(rows),'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'binding_sha256':hashlib.sha256((Path(__file__).parent/'pm_callbacks_binding.py').read_bytes()).hexdigest()},indent=2)+'\n',encoding='utf-8');print('callback scope cases:',len(rows))
if __name__=='__main__':main()
