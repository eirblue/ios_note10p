"""Exercise actual v38 PMU/EHLD memory-only getters and bounded row collector."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
from test_pm_preconditions_native import STUB
from test_pm_callbacks_producer import clean
HERE=Path(__file__).resolve().parent
STUB=STUB.replace('struct arm_pmu {struct notifier_block cpu_pm_nb;int num_events;struct pmu_hw_events *hw_events;unsigned long supported_cpus;};','struct perf_event {int poison;};struct arm_pmu {struct notifier_block cpu_pm_nb;int num_events;struct pmu_hw_events *hw_events;unsigned long supported_cpus;void *reset,*start,*stop;};')
MAIN=r'''
#define CHECK(x) do{if(!(x)){fprintf(stderr,"line %d\n",__LINE__);return 1;}}while(0)
int main(int argc,char**argv){int mode=atoi(argv[1]),i,ret;struct n10_branch_sample out={0};struct perf_event ev={0},other={0};struct notifier_block alien={0};
 pmu.cpu_pm_nb.notifier_call=cpu_pm_pmu_notify;pmu.num_events=4;pmu.hw_events=&hw;pmu.supported_cpus=1;pmu.reset=&hw;pmu.start=&hw;pmu.stop=&hw;hw.used_mask[0]=3;hw.events[0]=&ev;hw.events[1]=&other;ehld_ctrl.event=&ev;
 if(mode==1)ehld_ctrl.event=0;if(mode==2)pmu.supported_cpus=0;if(mode==3){pmu.num_events=0;}if(mode==4){pmu.num_events=32;hw.used_mask[0]=1UL<<31;hw.events[31]=&ev;}if(mode==5)pmu.num_events=33;if(mode==6)pmu.reset=pmu.start=pmu.stop=0;
 n10_branch_begin(1);ret=n10_branch_collect(&pmu.cpu_pm_nb,0,5);
 if(mode==5){CHECK(ret==-EINVAL);n10_branch_finish(ret);CHECK(n10_branch_copy(&out,2));return 0;}
 CHECK(!ret);CHECK(!n10_branch_collect(&alien,1,0));if(mode==9){pmu2.cpu_pm_nb.notifier_call=cpu_pm_pmu_notify;pmu2.num_events=1;pmu2.hw_events=&hw2;hw2.events[0]=&other;hw2.used_mask[0]=1;CHECK(!n10_branch_collect(&pmu2.cpu_pm_nb,2,5));}n10_branch_finish(0);CHECK(!n10_branch_copy(&out,2));CHECK(out.count==(unsigned)(mode==9?3:2) && out.row[1].kind==0 && !out.row[1].num && !out.row[1].used);
 if(mode==0)CHECK(out.row[0].used==3 && out.row[0].nonnull==3 && out.row[0].match==1 && out.row[0].supported==1 && out.row[0].reset && out.row[0].start && out.row[0].stop);
 if(mode==1)CHECK(!out.row[0].match);if(mode==2)CHECK(!out.row[0].supported);if(mode==3)CHECK(!out.row[0].used && !out.row[0].nonnull && !out.row[0].match);
 if(mode==4)CHECK(out.row[0].num==32 && out.row[0].used==0x80000000U && out.row[0].match==0x80000001U);
 if(mode==6)CHECK(!out.row[0].reset && !out.row[0].start && !out.row[0].stop);
 if(mode==7){n10_branch_invalidate();CHECK(n10_branch_copy(&out,2));n10_branch_begin(2);n10_branch_finish(0);CHECK(!n10_branch_copy(&out,3));}
 if(mode==8){n10_branch_begin(3);for(i=0;i<32;i++)CHECK(!n10_branch_collect(&alien,i,0));CHECK(n10_branch_collect(&alien,32,0)==-EIO);n10_branch_finish(-EIO);CHECK(n10_branch_copy(&out,4));}
 if(mode==9)CHECK(out.row[2].kind==5 && out.row[2].num==1 && out.row[2].used==1 && out.row[2].nonnull==1 && !out.row[2].match);
 return 0;}
'''
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);a=ap.parse_args();o=Path(a.output);o.mkdir(parents=True,exist_ok=False);names=('pm_branch_contract.h','pm_branch_ehld.c','pm_branch_pmu.c','pm_branch_chain.c');src=o/'branch.c';src.write_text(STUB+''.join(clean(n) for n in names)+MAIN,encoding='utf-8');cc=Path('host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe') if sys.platform=='win32' else 'cc';exe=o/('branch.exe' if sys.platform=='win32' else 'branch');r=subprocess.run([str(cc),'-std=gnu11',str(src),'-o',str(exe)],capture_output=True,timeout=60);(o/'compile.log').write_bytes(r.stdout+r.stderr)
 if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace'))
 cases=('match','null-ehld','unsupported','zero-slots','bit31','overflow','no-callbacks','invalidate-and-recover','capacity','multiple-pmu')
 for i,n in enumerate(cases):
  r=subprocess.run([str(exe),str(i)],capture_output=True,timeout=20);(o/f'case-{i}.log').write_bytes(r.stdout+r.stderr)
  if r.returncode:raise RuntimeError(n+': '+r.stderr.decode(errors='replace'))
 d={'passed':True,'hardware_verified':False,'cases':list(cases),'source_sha256':{n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in names},'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'generated_c_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'log_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in o.glob('*.log')}};(o/'result.json').write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
