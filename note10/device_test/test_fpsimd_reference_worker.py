"""Exercise composed worker and FPSIMD producer with feature on and off."""
import argparse,hashlib,json,re,subprocess,sys
from pathlib import Path
from test_pmu_control_worker import WORKER_STUB,ADD,MOCK,BRANCH_MOCK,STATE_MOCK,CONTROL_MOCK
from test_pm_callbacks_producer import clean
from test_fsys_pm_native import function
from decode_pm_preconditions import decode as decode_pre
from decode_fpsimd_reference import decode as decode_fps
FPS_MOCK=r'''int n10_fps_read(struct n10_fps_sample *s,unsigned int completed){(void)completed;if(mode==13)return -EIO;s->generation=1;s->seen=s->completed=1;s->row.index=3;s->row.chain_count=7;s->row.kind=3;s->row.reference=0;s->row.mm=1;s->row.foreign=0;s->row.depth=2;return 0;}'''
def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--cc',default='clang');a=p.parse_args();root=a.source_root;out=a.output;out.mkdir(parents=True,exist_ok=False)
 worker=root/'arch/arm64/mm/note10_pm_timer_roundtrip.c';producer=root/'arch/arm64/mm/note10_fpsimd_reference_probe.c';raw=worker.read_text(encoding='utf8');fps=re.sub(r'^#include[^\n]*\n','',producer.read_text(encoding='utf8'),flags=re.M)
 stub=WORKER_STUB.replace('static u32 n10_frame_checksum(const char*p,int n){(void)p;(void)n;return 0;}','static u32 n10_frame_checksum(const char*p,int n){u32 h=2166136261U;while(n--)h=(h^(unsigned char)*p++)*16777619U;return h;}')
 code=stub+ADD+'#define CONFIG_NOTE10_PMU_CONTROL_AUDIT 1\n'+''.join(clean(n) for n in ('pm_preconditions_contract.h','pm_branch_contract.h','pmu_state_contract.h','pmu_control_contract.h','fpsimd_reference_contract.h'))+MOCK.replace('value[4]=1','value[4]=2')+BRANCH_MOCK.replace('mode==1','mode==10').replace('nonnull=1','nonnull=3')+STATE_MOCK+CONTROL_MOCK+FPS_MOCK+''.join(clean(n) for n in ('pm_preconditions_probe.c','pm_branch_probe.c','pmu_state_probe.c','pmu_control_probe.c'))+fps+function(raw,'static void n10_pm_worker(struct work_struct *unused)\n{')+'''\nint main(int argc,char**argv){mode=atoi(argv[1]);
#ifdef CONFIG_NOTE10_FPSIMD_REFERENCE_AUDIT
 if(mode==14 || mode==15){unsigned int budget=mode==14?0:4090;return n10_fps_emit("N10FPSM1","",mode==14?512:10,&budget,0)?0:1;}
#endif
 n10_pm_worker(NULL);return 0;}\n'''
 identity='0123456789abcdef0123456789abcdef';cases=[]
 for label,define in (('enabled','#define CONFIG_NOTE10_FPSIMD_REFERENCE_AUDIT 1\n'),('disabled','')):
  src=out/(label+'.c');exe=out/(label+('.exe' if sys.platform=='win32' else ''));src.write_text(define+code,encoding='utf8',newline='\n');r=subprocess.run([a.cc,'-std=gnu11','-O2',str(src),'-o',str(exe)],capture_output=True);(out/(label+'-compile.log')).write_bytes(r.stdout+r.stderr)
  if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace'))
  for mode in ((0,1,9,10,11,12,13,14,15) if label=='enabled' else (0,1,9,10,11,12,13)):
   r=subprocess.run([str(exe.resolve()),str(mode)],capture_output=True);(out/f'{label}-{mode}.log').write_bytes(r.stdout+r.stderr)
   if r.returncode:raise RuntimeError('worker failed')
   text=r.stdout.decode();cases.append(label+'-'+str(mode))
   if mode in (14,15):continue
   if label=='disabled':
    if 'N10FPS' in text:raise ValueError('disabled feature emitted frames')
   elif mode==0:
    prior=decode_pre(text,identity,2);row=decode_fps(text,identity,2,prior);assert row['row']['reference']==0
   else:
    if 'N10FPSQ1' not in text:raise ValueError('failure summary missing')
    try:decode_fps(text,identity,2,{'generation':1,'rows':[]})
    except ValueError:continue
    raise ValueError('failure summary accepted')
 proof={'passed':True,'hardware_verified':False,'cases':cases,'source_sha256':{n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in {'worker':worker,'producer':producer}.items()},'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'generated_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.c')},'log_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.log')}};(out/'result.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8')
if __name__=='__main__':main()
