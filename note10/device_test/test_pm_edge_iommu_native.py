"""Execute four-phase IOMMU backend with pinned helper predicates."""
import argparse, hashlib, json, re, shutil, subprocess, sys
from pathlib import Path
from run_probe import ROOT
from prepare_iommu_pm import inline_helpers
from test_iommu_pm_native import STUB as BASE
HERE=Path(__file__).resolve().parent
STUB=BASE.replace('syscore,is_prepared,is_suspended;', 'syscore,is_prepared,is_suspended,direct_complete,is_late_suspended,is_noirq_suspended;')
STUB=STUB.replace('devices[i].power.is_prepared=phase==1;devices[i].power.is_suspended=phase==1;', 'devices[i].power.is_prepared=(phase==1 || phase==2);devices[i].power.is_suspended=(phase==1 || phase==2);devices[i].power.is_late_suspended=(phase==1 || phase==2);devices[i].power.is_noirq_suspended=(phase==2);')
STUB=STUB.replace('if(mode==24)strcpy(devices[i].name,"sysmmu.same");', 'if(mode==24)strcpy(devices[i].name,"sysmmu.same");if(mode==30)strcpy(devices[i].name,"bad name");')
STUB += r'''
static unsigned int online_count=8;static unsigned long online_mask=255;
static int irqs_disabled(void){return irq;}
static unsigned int num_online_cpus(void){return online_count;}
#define cpu_online_mask (&online_mask)
#define cpumask_bits(p) (p)
'''
MAIN=r'''
int main(int argc,char**argv){
 unsigned int begin;struct device old_devices[66];struct sysmmu_drvdata old_data[66];struct n10_edge_iommu_sample out[4];
 mode=atoi(argv[1]);begin=(mode==14 || mode==29)?0xffffffffU:1;
 for(phase=0;phase<4;++phase){
  setup();irq=mode==18;online_count=mode==25?7:8;
  if(mode==26 && phase==2)devices[1].power.is_late_suspended=0;
  if(mode==27 && phase==3)devices[1].power.is_late_suspended=1;
  memcpy(old_devices,devices,sizeof(devices));memcpy(old_data,controllers,sizeof(controllers));
  if(!(mode==11 && phase==1))n10_edge_iommu_capture(phase,begin+(mode==13 && phase==1));
  if(mode==12 && phase==1)n10_edge_iommu_capture(phase,begin);
  if(refs || device_locked || spin_locked || irq!=(mode==18) || memcmp(old_devices,devices,sizeof(devices)) || memcmp(old_data,controllers,sizeof(controllers)))return 81;
 }
 if(mode==31)n10_edge_iommu_samples[0].prepared++;
 if(mode==32)n10_edge_iommu_samples[1].policy_active=65;
 if(mode==28)n10_edge_iommu_capture(0,0);
 if(mode==29)for(phase=0;phase<4;++phase){setup();n10_edge_iommu_capture(phase,1);}
 printf("%d\n",n10_edge_iommu_read(out,mode==14?1:2));return 0;
}
'''
def run(output, header):
    output=Path(output).resolve()
    if not output.is_relative_to((ROOT/'note10/private').resolve()) or output.exists():raise ValueError('fresh private directory required')
    output.mkdir(parents=True)
    names=('pm_edge_iommu_contract.h','pm_edge_iommu_backend.c');sources={n:(HERE/n).read_bytes() for n in names}
    clean=lambda s:re.sub(r'^#include[^\n]*\n','',s,flags=re.M)
    src=output/'iommu.c';src.write_text(STUB+inline_helpers(Path(header).read_bytes())+(HERE/'iommu_pm_contract.h').read_text()+clean((HERE/'iommu_pm_backend.c').read_text())+sources[names[0]].decode()+clean(sources[names[1]].decode())+MAIN)
    compiler=ROOT/'host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe' if sys.platform=='win32' else shutil.which('cc')
    exe=output/('iommu.exe' if sys.platform=='win32' else 'iommu')
    built=subprocess.run([str(compiler),'-std=c11','-O2',str(src),'-o',str(exe)],capture_output=True,timeout=60)
    (output/'compile.log').write_bytes(built.stdout+built.stderr)
    if built.returncode:raise RuntimeError('IOMMU actual-C compilation failed')
    modes=list(range(1,15))+[0,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32];accept={0,14,19,21,29};outcomes=[]
    for mode in modes:
        p=subprocess.run([str(exe),str(mode)],capture_output=True,timeout=15)
        (output/f'mode-{mode}.log').write_bytes(p.stdout+p.stderr)
        if p.returncode:raise ValueError('model execution failed '+str(mode))
        accepted=p.stdout.strip()==b'0'
        if accepted!=(mode in accept):raise ValueError('unexpected acceptance '+str(mode))
        outcomes.append({'mode':mode,'accepted':accepted})
    result={'passed':True,'cases':len(outcomes),'outcomes':outcomes,'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'actual_backend_executed':True,'legacy_backend_same_translation_unit':True,'source_sha256':{n:hashlib.sha256(v).hexdigest() for n,v in sources.items()}}
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--header',type=Path,required=True);a=p.parse_args();r=run(a.output,a.header);print(json.dumps({'passed':r['passed'],'cases':r['cases']}))
