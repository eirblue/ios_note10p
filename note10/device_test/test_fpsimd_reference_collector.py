"""Exercise v43 collector gating with real FPSIMD frames and fake device logs."""
import argparse,hashlib,json,unittest
from pathlib import Path
from unittest.mock import patch
from contextlib import ExitStack
import test_collect_reservation as fixtures
from test_pmu_state_decoder import frame as state_frame
from test_pmu_control_decoder import frame as control_frame
from test_fpsimd_reference_decoder import frame as fps_frame
from test_cpu_cache_decode import summary,snapshots
from test_pm_timer_contract import pm,timers

class FPSCollectorTests(unittest.TestCase):
 def run_case(self,include=True,malformed=False,active=True):
  fixture=fixtures.CollectorTests();ident=fixture.identity
  row=dict(id=ident,copy=0,generation=1,index=0,count=1,kind=5,num=2,supported=1,used=1,present=1,owned=1,observed=1,running=0,stopped=1,uptodate=0,abnormal=0,affinity0=0,unbound=1,other=0,oncpu0=1,active=1)
  q=dict(id=ident,copy=0,generation=1,status=0,count=1,complete=1)
  frames=[]
  for copy in (0,1):
   row['copy']=q['copy']=copy;frames.extend((state_frame('N10STAR1',row),state_frame('N10STAQ1',q)))
  log=fixture.frame(0)+fixture.frame(1)+fixture.access_frame(0)+fixture.access_frame(1)+fixture.xnu_frame(0)+fixture.xnu_frame(1)+summary(0)+summary(1)+snapshots()+pm(0)+pm(1)+timers()
  log+='\n'.join(frames)+'\n'
  control=dict(id=ident,copy=0,generation=1,index=0,chain_count=1,kind=5,num=2,used_sw=1,visible_phys=0x80000001,used_phys=0x80000000,current_el=1,model_match=1,variant=1,revision=0,pmuver=4,fgt=0,pmcr=1<<11,cntenset=0,intenset=0)
  control_summary=dict(id=ident,copy=0,generation=1,status=0,row_count=1,complete=1);control_frames=[]
  for copy in (0,1):
   control['copy']=control_summary['copy']=copy;control_frames.extend((control_frame('N10PCTR1',control),control_frame('N10PCTQ1',control_summary)))
  if include:log+='\n'.join(control_frames)+'\n'
  fps=dict(id=ident,copy=0,generation=1,index=0,chain_count=1,kind=3,reference=0,mm=1,foreign=0,depth=0)
  fq=dict(id=ident,copy=0,generation=1,status=0,row_count=1,complete=1)
  if include:
   for copy in (0,1):
    fps['copy']=fq['copy']=copy;log+=fps_frame('N10FPSM1',fps.items())+'\n'+fps_frame('N10FPSQ1',fq.items())+'\n'
  if malformed:log+='N10FPSX1 broken\n'
  prior={'generation':1,'rows':[{'generation':1,'index':0,'count':1,'kind':3,'valid':15,'a':1,'b':0,'c':0,'d':0}]};branch={'generation':1,'rows':[{'kind':5,'num':2,'used':1,'nonnull':3}],'cpu0_pmu_branch_audit':True,'cpu0_gic_priority_footprint':True}
  original=Path.read_text
  def read(path,*args,**kwargs):
   raw=original(path,*args,**kwargs)
   if path.name=='package-result.json':
    data=json.loads(raw);data.update(pm_preconditions_diagnostic=True,pm_preconditions_version=1,pm_branch_diagnostic=True,pm_branch_version=1,pmu_state_audit=True,pmu_state_audit_version=1,pmu_control_audit=True,pmu_control_audit_version=1,fpsimd_reference_audit=active,fpsimd_reference_audit_version=1 if active else None);return json.dumps(data)
   return raw
  with ExitStack() as stack:
   stack.enter_context(patch.object(Path,'read_text',read))
   for module in ('pm_preconditions_binding','pm_branch_binding'):
    stack.enter_context(patch(module+'.assert_scope',return_value=True));stack.enter_context(patch(module+'.validate_model',return_value=True))
   stack.enter_context(patch('pmu_state_binding.validate',return_value=True));stack.enter_context(patch('pmu_control_binding.validate',return_value=True));stack.enter_context(patch('fpsimd_reference_binding.validate',return_value=active));stack.enter_context(patch('decode_pmu_state.decode',return_value={}));stack.enter_context(patch('decode_pmu_control.decode',return_value={}));stack.enter_context(patch('collect_reservation.pm_completed_generation',return_value=2))
   stack.enter_context(patch('decode_pm_preconditions.decode',return_value=prior));stack.enter_context(patch('decode_pm_branch.decode',return_value=branch))
   return fixture.run_fixture(log,access=True,xnu_stage=True,cpu_cache=True,pm_timer=True)
 def test_disabled_is_valid_and_adds_one_evaluation(self):
  result=self.run_case();self.assertTrue(result['diagnostic_passed']);self.assertEqual(len(result['evaluation_items']),37);self.assertEqual(result['evaluation_items']['cpu0_fpsimd_reference_audit']['status'],'passed')
 def test_missing_or_malformed_state_fails(self):
  for args in ({'include':False},{'malformed':True}):
   result=self.run_case(**args);self.assertFalse(result['diagnostic_passed']);self.assertEqual(result['evaluation_items']['cpu0_fpsimd_reference_audit']['status'],'failed')
 def test_unrequested_reference_fails(self):
  result=self.run_case(active=False);self.assertFalse(result['diagnostic_passed']);self.assertNotIn('cpu0_fpsimd_reference_audit',result['evaluation_items'])
DEPENDENCIES=('test_pmu_control_collector.py','test_pmu_control_decoder.py','test_pmu_state_decoder.py','test_fpsimd_reference_decoder.py','test_pmu_state_collector.py','test_collect_reservation.py','test_cpu_cache_decode.py','test_cpu_cache_native.py','test_pm_timer_contract.py')
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--report');parser.add_argument('--output');args=parser.parse_args()
 base=Path(__file__).resolve().parent;measured={n:hashlib.sha256((base/n).read_bytes()).hexdigest() for n in DEPENDENCIES}
 if bool(args.report)!=bool(args.output):raise ValueError('report and output must be paired')
 if args.report and json.loads(Path(args.report).read_text(encoding='utf8')).get('fpsimd_reference_collector_dependencies_sha256')!=measured:raise ValueError('collector fixture dependencies changed since build report')
 result=unittest.main(argv=[__file__],exit=False)
 if not result.result.wasSuccessful():raise SystemExit(1)
 if args.output:
  out=Path(args.output);out.mkdir(parents=True,exist_ok=False)
  proof={'passed':True,'hardware_verified':False,'cases':['valid-reference-37-evaluations','missing-and-malformed-fail','unexpected-disabled-fail'],'dependencies_sha256':measured,'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
  (out/'result.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8',newline='\n')
