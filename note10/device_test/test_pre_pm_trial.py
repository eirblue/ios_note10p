"""Only new pure data/source/flag gates; never execute the kernel wrapper."""
import argparse,json,os,shutil,subprocess
from pathlib import Path
from test_pre_pm_object import run_cases as object_cases,CASES as OBJECT_CASES
from prepare_pre_pm_trial import ROOT,BASE,render,sources,KCONFIG,config_settings,OPTION,require
POLICY_CASES=('layout-full','layout-overflow','page-size','unaligned-size','zero-size','span-overflow','span-alias','span-adjacent','pfn-outside','pfn-overlap','pfn-overflow','pfn-unique','pfn-duplicate','pfn-unsorted','guard-full','guard-last-byte')
SOURCE_CASES=('source-overlay62','default-off','new-hook-guard','epoch-before-arm','stage-cache-hook-PM','positive-only-call','unchanged-provider-bytes','crypto-preallocated','flags-valid','flags-inline-reject','flags-LTO-reject','flags-outliner-reject')
CASE_INVENTORY=POLICY_CASES+SOURCE_CASES+OBJECT_CASES
def run_source_cases():
 from build_pre_pm_trial import validate_flags,INSTRUMENTATION
 result=[]
 def check(name,ok):require(ok,name);result.append({'name':name,'passed':True})
 baseline=sources();transformed=render('1234567890abcdef1234567890abcdef');body=transformed['arch/arm64/mm/note10_xnu_reserve.c']
 check('source-overlay62',len(baseline)==62)
 check('default-off',b'\tdefault n\n' in KCONFIG and config_settings(False)[OPTION]=='n' and config_settings(True)[OPTION]=='y')
 check('new-hook-guard',b'#ifdef CONFIG_NOTE10_PRE_PM_TRIAL\n    if (n10_pre_pm_trial' in body)
 check('epoch-before-arm',body.index(b'unsigned long n10_pre_pm_epoch = jiffies;')<body.index(b'if (n10_arm_auto_return())'))
 check('stage-cache-hook-PM',body.index(b'if (n10_stage_xnu_payload')<body.index(b'if (n10_test_cpu_cache')<body.index(b'if (n10_pre_pm_trial')<body.index(b'    n10_start_pm_timer();'))
 wrapper=(ROOT/'note10/device_test/pre_pm_trial_wrapper.c').read_bytes()
 check('positive-only-call',wrapper.count(b'trial_rc=n10_rt_trial(')==1 and b'N10_TRIAL_FIXTURE' not in wrapper)
 check('unchanged-provider-bytes',all(transformed[n]==raw for n,raw in baseline.items() if n not in ('arch/arm64/mm/note10_xnu_reserve.c','arch/arm64/Kconfig')))
 check('crypto-preallocated',wrapper.index(b'crypto_alloc_shash(')<wrapper.index(b'trial_rc=n10_rt_trial(') and wrapper.index(b'kmalloc(')<wrapper.index(b'trial_rc=n10_rt_trial('))
 args=['-mlittle-endian','-fno-common','-march=armv8-a+lse','-fno-PIE','-mno-implicit-float','-fno-pic','-Oz','-fno-stack-protector','-mno-global-merge',*INSTRUMENTATION.split()];validate_flags(args);check('flags-valid',True)
 for name,extra in [('flags-inline-reject',['-finline-functions']),('flags-LTO-reject',['-flto=thin']),('flags-outliner-reject',['-mllvm','-enable-machine-outliner=always'])]:
  try:validate_flags(args+extra)
  except ValueError:check(name,True)
  else:raise AssertionError('mutation accepted: '+name)
 return result
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--cc',default='gcc');ap.add_argument('--source-only',action='store_true');a=ap.parse_args()
 out=a.output.resolve();require(not out.exists() and out.is_relative_to(ROOT/'note10/private'),'fresh private fixture output');out.mkdir(parents=True)
 cases=[];commands=[]
 if not a.source_only:
  executable=out/('policy.exe' if os.name=='nt' else 'policy');cmd=[a.cc,'-std=c11','-Wall','-Wextra','-Werror','-I'+str(ROOT/'note10/xnu26'),'-I'+str(ROOT/'note10/device_test'),str(ROOT/'note10/device_test/pre_pm_trial_policy_fixture.c'),'-o',str(executable)]
  commands.append(cmd);p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(out/'compile.log').write_bytes(p.stdout);require(p.returncode==0,'pure policy C fixture compile')
  p=subprocess.run([str(executable)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(out/'policy.log').write_bytes(p.stdout);require(p.returncode==0,'new pure data fixtures');names=[line[5:] for line in p.stdout.decode().splitlines() if line.startswith('CASE|')];require(tuple(names)==POLICY_CASES,'canonical pure data inventory');cases.extend({'name':n,'passed':True} for n in names)
 cases+=run_source_cases()+object_cases();require([x['name'] for x in cases]==list(SOURCE_CASES+OBJECT_CASES if a.source_only else CASE_INVENTORY),'selected fixture inventory')
 (out/'result.json').write_text(json.dumps({'passed':True,'fixture_only':True,'synthetic_only':True,'kernel_wrapper_executed':False,'physical_memory_or_hardware_accessed':False,'selected_cases':cases,'canonical_case_count':len(CASE_INVENTORY),'partial':a.source_only,'commands':commands},indent=2)+'\n',newline='\n')
if __name__=='__main__':main()
