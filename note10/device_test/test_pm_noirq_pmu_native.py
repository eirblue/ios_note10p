"""Actual noirq PMU helper/API with every read fault and no device locks."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from run_probe import ROOT
from prepare_abox_pmu import HERE,PINS,FINAL_CORE_SHA,validate_domains
from test_abox_pmu_native import STUB
from pmu_domain_table import DOMAINS
ACCEPTED=(0,49,55,56,62)
WRAPPER=r'''
static unsigned int nq_mode,nq_lane,nq_reads;
static int regmap_read(struct regmap*m,unsigned int offset,unsigned int*out){
 static const unsigned int domain[16][2]=DOMAIN_ARRAY;
 if(!nq_lane)return regular_regmap_read(m,offset,out);
 if(m!=&map || refs[0] || refs[1] || refs[2] || locks[0] || locks[1] || locks[2] || node_refs || properties || nq_reads>=48)abort();
 if(offset!=domain[nq_reads/3][nq_reads%3==1])abort();
 ++nq_reads;if(nq_mode>=1 && nq_mode<=48 && nq_reads==nq_mode)return -EIO;
 *out=nq_mode==49?0:0xffffffffU;return 0;
}
'''
MAIN=r'''
static void baseline(unsigned int generation){
 unsigned int phase;nq_lane=0;mode=0;
 for(phase=0;phase<3;++phase){setup();n10_abox_pmu_capture(phase,generation);if(refs[0] || refs[1] || refs[2] || locks[0] || locks[1] || locks[2] || node_refs || reads!=54)abort();}
}
int main(int argc,char**argv){
 struct n10_pmu_noirq_sample out;unsigned int generation,completed,saved_irq;int ret;
 nq_mode=atoi(argv[1]);generation=nq_mode==55?0xffffffffU:1;
 baseline(generation);setup();irq=saved_irq=nq_mode==56;nq_lane=1;
 if(nq_mode==51)n10_abox_pmu_samples[1].seen=0;
 if(nq_mode==52)++n10_abox_pmu_samples[1].generation;
 if(nq_mode==53)pmureg=NULL;
 if(nq_mode==54)pmureg=(void*)-1;
 if(nq_mode==57)generation=0;
 if(nq_mode==58)generation=2;
 if(nq_mode!=59)n10_pmu_noirq_capture(generation);
 if(nq_mode==50)n10_pmu_noirq_capture(generation);
 if(nq_mode==60)n10_pmu_noirq_last.state=0x10000;
 if(nq_mode==62){baseline(3);setup();nq_lane=1;nq_reads=0;generation=3;n10_pmu_noirq_capture(generation);}
 completed=generation+1;if(!completed)completed=1;if(nq_mode==61)++completed;
 if(n10_pmu_noirq_read(NULL,completed)!=-EINVAL || n10_pmu_noirq_read(&out,0)!=-EINVAL)abort();
 ret=n10_pmu_noirq_read(&out,completed);
 if(irq!=saved_irq || refs[0] || refs[1] || refs[2] || locks[0] || locks[1] || locks[2] || node_refs)abort();
 printf("{\"mode\":%u,\"ret\":%d,\"generation\":%u,\"seen\":%u,\"error\":%u,\"before\":%u,\"state\":%u,\"after\":%u,\"reads\":%u}\n",nq_mode,ret,out.generation,out.seen,out.error,out.before,out.state,out.after,nq_reads);return 0;
}
'''

def run(output,core_driver,pmu_source,domain_source):
    output=Path(output).resolve();core=Path(core_driver).read_bytes();pmu=Path(pmu_source).read_bytes();domain=Path(domain_source).read_bytes()
    if output.exists() or not output.is_relative_to((ROOT/'note10/private').resolve()):raise ValueError('Fresh private PMU noirq output required')
    if hashlib.sha256(core).hexdigest()!=FINAL_CORE_SHA or hashlib.sha256(pmu).hexdigest()!=PINS['drivers/soc/samsung/exynos-pmu.c'] or hashlib.sha256(domain).hexdigest()!=PINS['drivers/soc/samsung/cal-if/exynos9820/flexpmu_cal_local_exynos9820.h']:raise ValueError('Actual noirq PMU core/API/CAL input differs')
    validate_domains(domain.decode());output.mkdir(parents=True)
    clean=lambda s:re.sub(r'^#include[^\n]*\n','',s,flags=re.M)
    read_api=re.search(rb'int exynos_pmu_read\([^}]+\}',pmu).group().decode()
    getter=re.search(rb'struct regmap \*exynos_get_pmu_regmap\([^}]+\}',pmu).group().decode()
    wrapper=WRAPPER.replace('DOMAIN_ARRAY','{'+','.join('{0x%x,0x%x}'%(c,s) for _,c,s in DOMAINS)+'}')
    stub=STUB.replace('static int regmap_read(','static int regular_regmap_read(')
    header=(HERE/'abox_pmu_contract.h').read_text();backend=clean((HERE/'abox_pmu_backend.c').read_text())
    body=header+'void n10_fsys_pm_read(struct n10_fsys_pm_sample*out){memset(out,0,sizeof(*out));out->registered=1;}\n'+backend
    compiler=ROOT/'host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe' if sys.platform=='win32' else shutil.which('cc')
    def build(name,text):
        p=output/(name+'.c');p.write_bytes(text.encode());exe=output/(name+('.exe' if sys.platform=='win32' else ''))
        made=subprocess.run([str(compiler),'-std=c11','-O2',str(p),'-o',str(exe)],capture_output=True,timeout=60)
        (output/(name+'-compile.log')).write_bytes(made.stdout+made.stderr)
        if made.returncode:raise ValueError('Actual noirq PMU compilation failed')
        return exe
    common='#define CONFIG_NOTE10_PM_NOIRQ_TEST\n'+stub+wrapper+read_api+getter+body
    exe=build('pmu-noirq',common+MAIN);rows=[]
    for mode in range(63):
        ran=subprocess.run([str(exe),str(mode)],capture_output=True,timeout=15);(output/f'mode-{mode}.log').write_bytes(ran.stdout+ran.stderr)
        if ran.returncode:raise ValueError('Noirq PMU lifetime/IRQ/allowlist invariant failed mode '+str(mode))
        r=json.loads(ran.stdout);accepted=r['ret']==0
        expected_reads=mode if 1<=mode<=48 else 0 if mode in (51,52,53,54,57,58,59) else 48
        if accepted!=(mode in ACCEPTED) or r['reads']!=expected_reads:raise ValueError('Noirq PMU read failure/generation differs mode '+str(mode))
        if accepted and tuple(r[k] for k in ('before','state','after'))!=((0,0,0) if mode==49 else (0xffff,0xffff,0xffff)):raise ValueError('Noirq PMU bitmaps differ')
        rows.append(dict(mode=mode,passed=True,accepted=accepted,reads=r['reads']))
    missing=common.replace('#define CONFIG_EXYNOS_PMU','')+r'''
int main(void){struct n10_pmu_noirq_sample out;setup();nq_lane=1;
n10_abox_pmu_samples[0].seen=n10_abox_pmu_samples[1].seen=1;
n10_abox_pmu_samples[0].generation=n10_abox_pmu_samples[1].generation=1;
n10_pmu_noirq_capture(1);return nq_reads || reads || n10_pmu_noirq_last.error!=3 || n10_pmu_noirq_read(&out,2)!=-EIO;}
'''
    exe=build('missing-config',missing);ran=subprocess.run([str(exe)],capture_output=True,timeout=15)
    (output/'missing-config.log').write_bytes(ran.stdout+ran.stderr)
    if ran.returncode:raise ValueError('Disabled PMU stub was not refused without reads')
    result=dict(passed=True,cases=63,outcomes=rows,actual_pmu_noirq_backend_executed=True,pinned_pmu_api_executed=True,
        no_device_locks_in_noirq_lane=True,all_48_read_faults_refused=True,missing_config_refused_without_reads=True,
        prerequisite_regular_generation_required=True,irq_state_preserved=True,hardware_verified=False,
        core_sha256=FINAL_CORE_SHA,pmu_api_sha256=hashlib.sha256(pmu).hexdigest(),cal_sha256=hashlib.sha256(domain).hexdigest(),
        source_sha256={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in ('abox_pmu_contract.h','abox_pmu_backend.c','pmu_domain_table.py')},
        harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (output/'result.json').write_bytes((json.dumps(result,indent=2)+'\n').encode());return result
