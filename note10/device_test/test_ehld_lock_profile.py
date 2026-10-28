"""Reject unsupported profile results and changed pinned Kconfig inputs."""
import argparse,hashlib,json,tempfile
from pathlib import Path
import ehld_lock_profile as profile

def valid_config():
 return ('\n'.join('# CONFIG_'+x+' is not set' for x in profile.DISABLE)+'\n'+
         '\n'.join('CONFIG_'+x+'=y' for x in profile.PRESERVE)+
         '\nCONFIG_NOTE10_EHLD_LOCK_AUDIT=y\nCONFIG_NOTE10_RCU_CONTEXT_AUDIT=y\n')

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
 cases=[];raw=valid_config();profile.verify_config(raw.encode());cases.append('valid-profile')
 for name in profile.DISABLE:
  for value in ('y','m','garbage'):
   bad=raw.replace('# CONFIG_'+name+' is not set','CONFIG_'+name+'='+value)
   try:profile.verify_config(bad.encode())
   except ValueError:cases.append('reject-'+name+'-'+value)
   else:raise AssertionError('accepted enabled '+name+'='+value)
 for name in profile.PRESERVE:
  bad=raw.replace('CONFIG_'+name+'=y','# CONFIG_'+name+' is not set')
  try:profile.verify_config(bad.encode())
  except ValueError:cases.append('reject-missing-'+name)
  else:raise AssertionError('accepted missing preserve '+name)
 for name in ('NOTE10_EHLD_LOCK_AUDIT','NOTE10_RCU_CONTEXT_AUDIT'):
  bad=raw.replace('CONFIG_'+name+'=y','# CONFIG_'+name+' is not set')
  try:profile.verify_config(bad.encode())
  except ValueError:cases.append('reject-disabled-'+name)
  else:raise AssertionError('accepted disabled feature '+name)
 try:profile.verify_config((raw+'CONFIG_KPROBES=m\n').encode())
 except ValueError:cases.append('reject-duplicate')
 else:raise AssertionError('accepted duplicate config symbol')
 if a.source:
  actual=profile.verify_pins(a.source)
  if actual!=profile.PINS:raise AssertionError('profile pin map differs')
  cases.append('pinned-source-map')
 result={'passed':True,'hardware_verified':False,'cases':cases,'disable':list(profile.DISABLE),'preserve':list(profile.PRESERVE),'pins':profile.PINS,'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'profile_sha256':hashlib.sha256(Path(profile.__file__).read_bytes()).hexdigest()}
 if a.output:
  a.output.mkdir(parents=True,exist_ok=False);(a.output/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
 print(json.dumps({'passed':True,'cases':len(cases)}))
if __name__=='__main__':main()
