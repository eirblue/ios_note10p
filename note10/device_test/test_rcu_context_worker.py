"""Exercise actual final worker and RCU producer with feature on/off."""
import argparse,hashlib,json,re,subprocess,sys
from pathlib import Path
import test_fpsimd_reference_worker as prior
from test_pm_callbacks_producer import clean
from test_fsys_pm_native import function
from decode_pm_preconditions import decode as decode_pre
from decode_rcu_context import decode as decode_rcu
RCU_MOCK=r'''int n10_rcu_read(struct n10_rcu_sample *s,unsigned int completed){(void)completed;if(mode==16)return -EIO;s->generation=1;s->seen=s->completed=1;s->row.chain_count=7;s->row.watching=mode==19?0:1;s->row.nesting_class=mode==19?0:2;s->row.positive_headroom_two=mode==19?0:1;s->row.nmi_nonzero=mode==19?1:0;return 0;}'''
CASES=[label+'-'+str(i) for label in ('enabled','disabled') for i in ((0,1,9,10,11,12,13,16,17,18,19) if label=='enabled' else (0,1,9,10,11,12,13,16))]
def make_code(root):
 worker=root/'arch/arm64/mm/note10_pm_timer_roundtrip.c';producer=root/'arch/arm64/mm/note10_rcu_context_probe.c';fps=root/'arch/arm64/mm/note10_fpsimd_reference_probe.c';clean_source=lambda p:re.sub(r'^#include[^\n]*\n','',p.read_text(encoding='utf8'),flags=re.M)
 stub=prior.WORKER_STUB.replace('static u32 n10_frame_checksum(const char*p,int n){(void)p;(void)n;return 0;}','static u32 n10_frame_checksum(const char*p,int n){u32 h=2166136261U;while(n--)h=(h^(unsigned char)*p++)*16777619U;return h;}')
 main='''\nint main(int argc,char**argv){mode=atoi(argv[1]);
#ifdef CONFIG_NOTE10_RCU_CONTEXT_AUDIT
 if(mode==17 || mode==18){unsigned int budget=mode==17?0:4090;return n10_rcu_emit("N10RCM1","",mode==17?512:10,&budget,0)?0:1;}
#endif
 n10_pm_worker(NULL);return 0;}\n'''
 return stub+prior.ADD+'#define CONFIG_NOTE10_PMU_CONTROL_AUDIT 1\n#define CONFIG_NOTE10_FPSIMD_REFERENCE_AUDIT 1\n'+''.join(clean(n) for n in ('pm_preconditions_contract.h','pm_branch_contract.h','pmu_state_contract.h','pmu_control_contract.h','fpsimd_reference_contract.h','rcu_context_contract.h'))+prior.MOCK.replace('value[4]=1','value[4]=2')+prior.BRANCH_MOCK.replace('mode==1','mode==10').replace('nonnull=1','nonnull=3')+prior.STATE_MOCK+prior.CONTROL_MOCK+prior.FPS_MOCK+RCU_MOCK+''.join(clean(n) for n in ('pm_preconditions_probe.c','pm_branch_probe.c','pmu_state_probe.c','pmu_control_probe.c'))+clean_source(fps)+clean_source(producer)+function(worker.read_text(),'static void n10_pm_worker(struct work_struct *unused)\n{')+main
def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--cc',default='clang');a=p.parse_args();root=a.source_root;out=a.output;out.mkdir(parents=True,exist_ok=False);code=make_code(root);identity='0123456789abcdef0123456789abcdef'
 for label,define in (('enabled','#define CONFIG_NOTE10_RCU_CONTEXT_AUDIT 1\n'),('disabled','')):
  src=out/(label+'.c');exe=out/(label+('.exe' if sys.platform=='win32' else ''));src.write_bytes((define+code).encode());c=subprocess.run([a.cc,'-std=gnu11','-O2',str(src),'-o',str(exe)],capture_output=True);(out/(label+'-compile.log')).write_bytes(c.stdout+c.stderr)
  if c.returncode:raise RuntimeError(c.stderr.decode(errors='replace'))
  for mode in ((0,1,9,10,11,12,13,16,17,18,19) if label=='enabled' else (0,1,9,10,11,12,13,16)):
   x=subprocess.run([str(exe.resolve()),str(mode)],capture_output=True);(out/f'{label}-{mode}.log').write_bytes(x.stdout+x.stderr)
   if x.returncode:raise RuntimeError(label+' '+str(mode))
   text=x.stdout.decode()
   if mode in (17,18):continue
   if label=='disabled':
    if 'N10RC' in text:raise ValueError('disabled RCU emitted frames')
   elif mode in (0,19):
    old=decode_pre(text,identity,2);row=decode_rcu(text,identity,2,old)['row'];assert row['watching']==(0 if mode==19 else 1)
   else:
    if 'N10RCQ1' not in text:raise ValueError('failure summary missing')
    try:decode_rcu(text,identity,2,{'generation':1,'rows':[]})
    except ValueError:continue
    raise ValueError('failure summary accepted')
 h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();paths={'worker':'arch/arm64/mm/note10_pm_timer_roundtrip.c','fps_producer':'arch/arm64/mm/note10_fpsimd_reference_probe.c','rcu_producer':'arch/arm64/mm/note10_rcu_context_probe.c'};result={'passed':True,'hardware_verified':False,'cases':CASES,'source_sha256':{k:h(root/v) for k,v in paths.items()},'harness_sha256':h(Path(__file__)),'generated_sha256':{n:h(out/n) for n in ('enabled.c','disabled.c')},'log_sha256':{n.name:h(n) for n in out.glob('*.log')}};(out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
if __name__=='__main__':main()
