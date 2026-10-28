"""Independently challenge actual IRQ producer output and cross-lane bindings."""
import argparse,hashlib,json,re
from pathlib import Path
from decode_pm_irq import decode
from decode_reservation import checksum
from run_probe import ROOT
HERE=Path(__file__).resolve().parent
ID='0123456789abcdef0123456789abcdef'
def run(output,native):
 out=Path(output).resolve();native=Path(native)
 if out.exists() or not out.is_relative_to((ROOT/'note10/private').resolve()):raise ValueError('fresh private model directory required')
 out.mkdir(parents=True);base=(native/'mode-0.log').read_text();wrap=(native/'mode-19.log').read_text()
 baseline={'cpus':{0:{'snapshot':{'mpidr':0x80000000,'sctlr':0x1005,'tcr':0x11,'ttbr1':0x1234000012345000,'mair':0xff}}}}
 timers={'cpus':{0:{'after':0xb6,'freq':26000000}}}
 def edit(tag,old,new,phase=None,both=True):
  lines=base.splitlines();changed=0
  for i,line in enumerate(lines):
   if not line.startswith(tag+' ') or (phase is not None and ('phase='+str(phase)+' ') not in line):continue
   t,rest=line.split(' ',1);body,digest=rest.rsplit(' checksum=',1)
   if old not in body:raise ValueError('Missing mutation '+old)
   body=body.replace(old,new,1);lines[i]=t+' '+body+' checksum='+format(checksum(body.encode()),'08x');changed+=1
   if not both:break
  if not changed:raise ValueError('Missing mutation row')
  return '\n'.join(lines)+'\n'
 def drop(tag):
  lines=base.splitlines();i=next(i for i,x in enumerate(lines) if x.startswith(tag+' '));lines.pop(i);return '\n'.join(lines)+'\n'
 def corrupt(tag):
  lines=base.splitlines();i=next(i for i,x in enumerate(lines) if x.startswith(tag+' '));lines[i]=lines[i][:-8]+'00000000';return '\n'.join(lines)+'\n'
 cases=[('baseline',base,2,baseline,timers,True),('wrap',wrap,1,baseline,timers,True),
  ('actual_failure',(native/'mode-11.log').read_text(),2,baseline,timers,False),
  ('missing_arch',drop('N10IAR1'),2,baseline,timers,False),('missing_timer',drop('N10ITR1'),2,baseline,timers,False),
  ('missing_gic',drop('N10IGR1'),2,baseline,timers,False),('missing_summary',drop('N10IQR1'),2,baseline,timers,False),
  ('corrupt_checksum',corrupt('N10IGR1'),2,baseline,timers,False),('mixed_generation',edit('N10IAR1','generation=1','generation=2',1),2,baseline,timers,False),
  ('wrong_phase',edit('N10ITR1','phase=1','phase=2',1),2,baseline,timers,False),
  ('mask_missing',edit('N10ITR1','daif=1c0','daif=140',1),2,baseline,timers,False),
  ('daif_other_bits',edit('N10ITR1','daif=1c0','daif=1c1',1),2,baseline,timers,False),
  ('restore_changed',edit('N10ITR1','daif=140','daif=141',2),2,baseline,timers,False),
  ('saved_changed',edit('N10IQR1','saved=140','saved=141'),2,baseline,timers,False),
  ('preempt_wrong',edit('N10ITR1','preempt=1','preempt=2',1),2,baseline,timers,False),
  ('cpu_wrong',edit('N10IGR1','cpu=0','cpu=1',1),2,baseline,timers,False),
  ('online_wrong',edit('N10ITR1','online=1','online=3',1),2,baseline,timers,False),
  ('ttbr_local',edit('N10IAR1','ttbr1=1234000012345000','ttbr1=2234000012345000',1),2,baseline,timers,False),
  ('timer_changed',edit('N10ITR1','cntkctl=b6','cntkctl=b7',1),2,baseline,timers,False),
  ('frequency_bad',edit('N10ITR1','cntfrq=18cba80','cntfrq=18cba81',1),2,baseline,timers,False),
  ('gic_changed',edit('N10IGR1','bpr=2','bpr=3',1),2,baseline,timers,False),
  ('gic_disabled',edit('N10IGR1','ctlr=1','ctlr=0',1),2,baseline,timers,False),
  ('pmr_zero',edit('N10IGR1','pmr=80','pmr=0',1),2,baseline,timers,False),
  ('dist_disabled',edit('N10IGR1','dist=1','dist=0',1),2,baseline,timers,False),
  ('conflicting_copy',edit('N10IAR1','mair=ff','mair=fe',1,False),2,baseline,timers,False),
  ('wrong_completion',base,3,baseline,timers,False)]
 overflow=base
 for tag in ('N10IAR1','N10ITR1','N10IGR1','N10IQR1'):
  lines=overflow.splitlines()
  for i,line in enumerate(lines):
   if line.startswith(tag+' '):
    t,rest=line.split(' ',1);body,digest=rest.rsplit(' checksum=',1);body=body.replace('generation=1','generation=4294967297',1);lines[i]=t+' '+body+' checksum='+format(checksum(body.encode()),'08x')
  overflow='\n'.join(lines)+'\n'
 cases.append(('generation_overflow',overflow,2,baseline,timers,False))
 for key,value in (('ctlr','1'),('pmr','80'),('bpr','2'),('iidr','20243b'),('dist','1'),('typer','467')):
  cases.append(('gic_overflow_'+key,edit('N10IGR1',key+'='+value,key+'=100000000',0),2,baseline,timers,False))
 for name,key in (('baseline_mpidr','mpidr'),('baseline_sctlr','sctlr'),('baseline_tcr','tcr'),('baseline_mair','mair'),('baseline_ttbr','ttbr1')):
  import copy
  b=copy.deepcopy(baseline);b['cpus'][0]['snapshot'][key]^=1;cases.append((name,base,2,b,timers,False))
 import copy
 b=copy.deepcopy(baseline);b['cpus'][0]['snapshot']['ttbr1']^=1<<48;cases.append(('cross_asid_allowed',base,2,b,timers,True))
 t=copy.deepcopy(timers);t['cpus'][0]['after']^=1;cases.append(('timer_cross_bind',base,2,baseline,t,False))
 outcomes=[]
 for name,text,completed,b,t,expected in cases:
  try:decode(text,ID,completed,b,t);accepted=True
  except ValueError:accepted=False
  if accepted!=expected:raise ValueError('IRQ decoder unexpected outcome '+name)
  outcomes.append({'case':name,'passed':True,'accepted':accepted})
 result={'passed':True,'cases':len(outcomes),'outcomes':outcomes,'actual_producer_frames_decoded':True,
  'native_log_sha256':{f'mode-{i}.log':hashlib.sha256((native/f'mode-{i}.log').read_bytes()).hexdigest() for i in (0,19,11)},
  'decoder_sha256':hashlib.sha256((HERE/'decode_pm_irq.py').read_bytes()).hexdigest(),'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--native',type=Path,required=True);a=p.parse_args();r=run(a.output,a.native);print(json.dumps({'passed':r['passed'],'cases':r['cases']}))
