"""Actual bounded PMU helper/producer and pinned read/getter APIs under controlled stubs."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from run_probe import ROOT
from prepare_abox_pmu import HERE,PINS,SOURCES,FINAL_CORE_SHA,CORE_PATCHED_SHA,SUFFIX
from prepare_ufs_pm import instrument_dma
from decode_abox_pmu import decode
ID='0123456789abcdef0123456789abcdef'
ACCEPTED=(0,9,24,25,26,82)
STUB=r'''
#include <stdio.h>
#include <string.h>
#include <stdbool.h>
#include <stdlib.h>
#include <errno.h>
typedef unsigned int u32;
#define CONFIG_EXYNOS_PMU
#define N10_RESERVE_BUILD_ID "0123456789abcdef0123456789abcdef"
#define pr_info printf
#define scnprintf snprintf
#define IS_ERR_OR_NULL(p) (!(p) || (p)==(void*)-1)
struct device_node {int ordinal;};
struct device_driver {const char *name;};
struct device {struct device_driver *driver;struct device_node *of_node;struct device *parent;};
struct platform_device {struct device dev;};
static struct {struct device_driver driver;} samsung_abox_core_driver={{"samsung-abox-core"}};
static struct device_driver abox_driver={"samsung-abox"},foreign_driver={"foreign"},nameless_driver={NULL};
static struct device_node parent_node,children[65];
static struct platform_device parent_dev,core_dev[2],foreign_dev;
static unsigned int mode,phase,refs[3],locks[3],node_refs,reads,properties,irq;
struct regmap {int identity;};
static struct regmap map;
static struct regmap *pmureg;
static unsigned int allowed[2][6]={{0x2d80,1,0x2da0,1,0x2da4,0x11},{0x2e00,1,0x2e20,1,0x2e24,1}};
static int dev_index(struct device*d){if(d==&parent_dev.dev)return 0;if(d==&core_dev[0].dev)return 1;if(d==&core_dev[1].dev)return 2;abort();}
static struct device_node *of_find_compatible_node(void*a,void*b,const char*c){if(a || b || strcmp(c,"samsung,abox"))abort();if(mode==1)return NULL;++node_refs;return &parent_node;}
static struct platform_device *of_find_device_by_node(struct device_node*n){
 if(!node_refs)abort();if(n==&parent_node){if(mode==2)return NULL;++refs[0];return &parent_dev;}
 if(n!=&children[0] && n!=&children[1])abort();++refs[n->ordinal+1];return &core_dev[n->ordinal];
}
static void of_node_put(struct device_node*n){if(!n || !node_refs--)abort();}
static void put_device(struct device*d){int i=dev_index(d);if(locks[i] || !refs[i]--)abort();}
static int device_trylock(struct device*d){int i=dev_index(d);if(!refs[i] || locks[i])abort();if((mode==10 && !i)||(mode==21 && i==1))return 0;if(i && !locks[0])abort();locks[i]=1;return 1;}
static void device_unlock(struct device*d){int i=dev_index(d);if(!locks[i] || (!i && (locks[1] || locks[2])))abort();locks[i]=0;}
static struct device_node *next_child(struct device_node*p,struct device_node*old){
 int i;if(p!=&parent_node || !locks[0])abort();
 if(old)of_node_put(old);
 if(mode==26)i=!old?1:old->ordinal==1?0:2;else i=!old?0:old->ordinal+1;
 if(i>=(mode==12?1:mode==32?65:2))return NULL;
 ++node_refs;return &children[i];
}
#define for_each_available_child_of_node(p,n) for((n)=next_child((p),NULL);(n);(n)=next_child((p),(n)))
static int of_device_is_compatible(struct device_node*n,const char*c){if(strcmp(c,"samsung,abox-core"))abort();return n->ordinal<2;}
static int of_property_read_u32(struct device_node*n,const char*k,unsigned int*out){if(strcmp(k,"samsung,id") || n->ordinal>=2)abort();++properties;*out=mode==13?2:mode==14?0:n->ordinal;return 0;}
static int of_property_read_u32_array(struct device_node*n,const char*k,unsigned int*out,unsigned int count){
 unsigned int i;if(count!=2 || n->ordinal>=2)abort();++properties;
 if(!strcmp(k,"samsung,pmu_power"))i=0;else if(!strcmp(k,"samsung,pmu_enable"))i=2;else if(!strcmp(k,"samsung,pmu_standby"))i=4;else abort();
 if(mode==17)return -EINVAL;out[0]=allowed[n->ordinal][i];out[1]=allowed[n->ordinal][i+1];if(mode==15)out[0]+=4;if(mode==16)out[1]^=2;return 0;
}
static int regmap_read(struct regmap*m,unsigned int offset,unsigned int*out){
 unsigned int expected;
 if(reads<6)expected=allowed[reads/3][(reads%3)*2];
 else {
  static const unsigned int domain[16][2]={{0x1900,0x1904},{0x1d00,0x1d04},{0x1d80,0x1d84},{0x1e00,0x1e04},{0x1e80,0x1e84},{0x1f00,0x1f04},{0x2300,0x2304},{0x2100,0x2104},{0x2500,0x2504},{0x2400,0x2404},{0x2480,0x2484},{0x2580,0x2584},{0x2600,0x2604},{0x2a80,0x2a84},{0x2200,0x2204},{0x2b00,0x2b04}};
  expected=domain[(reads-6)/3][(reads-6)%3==1];
 }
 if(m!=&map || !locks[0] || !locks[1] || !locks[2] || properties!=8 || reads>=54 || offset!=expected)abort();
 if(!(mode==0 || (mode>=3 && mode<=9) || (mode>=24 && mode<=31) || mode>=34))abort();
 ++reads;if((mode>=3 && mode<=8 && reads==mode-2) || (mode>=34 && mode<=81 && reads==mode-27))return -EIO;
 *out=mode==9?0:mode==82?(reads&1):0xffffffffU;return 0;
}
static void setup(void){
 memset(refs,0,sizeof(refs));memset(locks,0,sizeof(locks));node_refs=reads=properties=0;
 for(int i=0;i<65;++i)children[i].ordinal=i;
 parent_dev.dev=(struct device){&abox_driver,&parent_node,NULL};
 for(int i=0;i<2;++i)core_dev[i].dev=(struct device){&samsung_abox_core_driver.driver,&children[i],&parent_dev.dev};
 if(mode==11)parent_dev.dev.driver=&foreign_driver;
 if(mode==33)parent_dev.dev.driver=&nameless_driver;
 if(mode==18)core_dev[0].dev.driver=&foreign_driver;
 if(mode==19)core_dev[0].dev.parent=&foreign_dev.dev;
 if(mode==20)core_dev[0].dev.of_node=&children[1];
 pmureg=mode==22?NULL:mode==23?(void*)-1:&map;
}
'''
MAIN=r'''
int main(int argc,char**argv){
 unsigned int generation,completed,saved_irq;struct device old[3];
 mode=atoi(argv[1]);generation=mode==24?0xffffffffU:1;
 if(n10_abox_pmu_read(NULL,2)!=-EINVAL)return 70;
 for(phase=0;phase<3;++phase){
  unsigned int expected;setup();irq=saved_irq=mode==25?1:phase%2;
  old[0]=parent_dev.dev;old[1]=core_dev[0].dev;old[2]=core_dev[1].dev;
  if(!(mode==28 && phase==1))n10_abox_pmu_capture(phase,generation+(mode==29 && phase==1));
  if(mode==27 && phase==1)n10_abox_pmu_capture(phase,generation);
  expected=(mode>=3 && mode<=8)?mode-2:((mode==0 || mode==9 || (mode>=24 && mode<=31) || mode>=82)?54:0);
  if(mode>=34 && mode<=81)expected=mode-27;
  if((mode==27 && phase==2)||(mode==28 && phase>=1)||(mode==29 && phase>=1))expected=0;
  if(refs[0] || refs[1] || refs[2] || locks[0] || locks[1] || locks[2] || node_refs || irq!=saved_irq || reads!=expected || memcmp(&old[0],&parent_dev.dev,sizeof(old[0])) || memcmp(&old[1],&core_dev[0].dev,sizeof(old[1])) || memcmp(&old[2],&core_dev[1].dev,sizeof(old[2])))return 71;
 }
 if(mode==31)n10_abox_pmu_samples[1].power[0]=2;
 if(mode==84)n10_abox_pmu_samples[1].domain_state=0x10000;
 if(mode==85)n10_abox_pmu_samples[1].seen=2;
 if(mode==86)n10_abox_pmu_samples[1].generation=3;
 completed=generation+1;if(!completed)completed=1;n10_report_abox_pmu(completed);return 0;
}
'''

def run(output,core_driver,pmu_source,dma_helper,domain_source):
    output=Path(output).resolve();core=Path(core_driver).read_bytes();pmu=Path(pmu_source).read_bytes();dma=Path(dma_helper).read_bytes()
    if output.exists() or not output.is_relative_to((ROOT/'note10/private').resolve()):raise ValueError('Fresh private PMU model output required')
    if hashlib.sha256(core).hexdigest()!=FINAL_CORE_SHA or not core.endswith(SUFFIX) or hashlib.sha256(core[:-len(SUFFIX)]).hexdigest()!=CORE_PATCHED_SHA:raise ValueError('Final/base core composition differs')
    if hashlib.sha256(pmu).hexdigest()!=PINS['drivers/soc/samsung/exynos-pmu.c']:raise ValueError('Pinned PMU API differs')
    if dma!=instrument_dma((HERE/'dma_pm_backend.c').read_bytes()):raise ValueError('Generated DMA PMU hook differs')
    from prepare_abox_pmu import validate_domains
    domain=Path(domain_source).read_bytes()
    if hashlib.sha256(domain).hexdigest()!=PINS['drivers/soc/samsung/cal-if/exynos9820/flexpmu_cal_local_exynos9820.h']:raise ValueError('Pinned CAL status input differs')
    validate_domains(domain.decode())
    output.mkdir(parents=True);sources={n:(HERE/n).read_bytes() for n in SOURCES}
    clean=lambda s:re.sub(r'^#include[^\n]*\n','',s,flags=re.M)
    read_api=re.search(rb'int exynos_pmu_read\([^}]+\}',pmu).group().decode()
    getter=re.search(rb'struct regmap \*exynos_get_pmu_regmap\([^}]+\}',pmu).group().decode()
    checksum=re.search(r'static u32 n10_frame_checksum[^}]+}',(HERE/'xnu_reserve.c').read_text()).group()
    compiler=ROOT/'host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe' if sys.platform=='win32' else shutil.which('cc')
    def build(name,code):
        source=output/(name+'.c');source.write_bytes(code.encode());exe=output/(name+('.exe' if sys.platform=='win32' else ''))
        made=subprocess.run([str(compiler),'-std=c11','-O2',str(source),'-o',str(exe)],capture_output=True,timeout=60);(output/(name+'-compile.log')).write_bytes(made.stdout+made.stderr)
        if made.returncode:raise ValueError('PMU actual-C model compilation failed')
        return exe
    body=sources['abox_pmu_contract.h'].decode()+clean(sources['abox_pmu_backend.c'].decode())+checksum+clean(sources['abox_pmu_probe.c'].decode())
    exe=build('pmu',STUB+read_api+getter+body+MAIN);rows=[]
    for mode in range(88):
        ran=subprocess.run([str(exe),str(mode)],capture_output=True,timeout=15);(output/f'mode-{mode}.log').write_bytes(ran.stdout+ran.stderr)
        if ran.returncode:raise ValueError('PMU refs/locks/state/allowed-read invariant failed mode '+str(mode))
        text=ran.stdout.decode()
        if mode==30:text='\n'.join(line for line in text.splitlines() if not ('phase=1 ' in line and 'index=0 ' in line))
        if mode==83:text='\n'.join(v for v in text.splitlines() if not (v.startswith('N10PDS1 ') and 'phase=1 ' in v))
        if mode==87:text=text.replace('N10PDS1','N10PDS0')
        try:obs=decode(text,ID,1 if mode==24 else 2);accepted=True
        except ValueError:accepted=False
        if accepted!=(mode in ACCEPTED):raise ValueError('Strict PMU decoder differs mode '+str(mode))
        if accepted:
            for phase in range(3):
                for core in range(2):
                    s=obs['phases'][phase][core]['snapshot'];expected=0 if mode==9 else 1
                    if mode==82:expected=1
                    if mode!=82 and (s['power']!=expected or s['enable']!=expected or s['standby']!=(0 if mode==9 else (0x11 if core==0 else 1))):raise ValueError('Masked PMU API value differs')
            for phase in range(3):
                snap=obs['power_domains']['phases'][phase]['snapshot']
                expected=(0,0,0) if mode==9 else (0x5555,0xaaaa,0x5555) if mode==82 else (0xffff,0xffff,0xffff)
                if tuple(snap[k] for k in ('before','state','after'))!=expected:raise ValueError('CAL domain bitmap differs')
            if obs['audio_dsp_shutdown_verified'] or not obs['control_bits_are_not_power_off_acknowledgments']:raise ValueError('PMU scope overstated')
        rows.append(dict(mode=mode,passed=True,accepted=accepted))
    missing=build('missing-config',STUB.replace('#define CONFIG_EXYNOS_PMU','')+read_api+getter+body+'int main(void){setup();n10_abox_pmu_capture(0,1);return reads || refs[0] || node_refs || n10_abox_pmu_samples[0].error!=3;}')
    ran=subprocess.run([str(missing)],capture_output=True,timeout=15);(output/'missing-config.log').write_bytes(ran.stdout+ran.stderr)
    if ran.returncode:raise ValueError('Missing real PMU config was not refused without reads')
    from test_dma_pm_native import STUB as DMA_STUB,MAIN as DMA_MAIN
    hook='\n#define CONFIG_NOTE10_ABOX_PMU_AUDIT\nstatic void n10_abox_pmu_capture(unsigned int phase,unsigned int generation){if(locked)abort();printf("PMUHOOK phase=%u generation=%u\\n",phase,generation);}\n'
    exe=build('hook',DMA_STUB+hook+(HERE/'dma_pm_contract.h').read_text()+clean(dma.decode())+checksum+clean((HERE/'dma_pm_probe.c').read_text())+DMA_MAIN)
    ran=subprocess.run([str(exe),'0'],capture_output=True,timeout=15);(output/'hook.log').write_bytes(ran.stdout+ran.stderr)
    if ran.returncode or re.findall(rb'PMUHOOK phase=(\d+) generation=(\d+)',ran.stdout)!=[(b'0',b'1'),(b'1',b'1'),(b'2',b'1')]:raise ValueError('PMU hook must execute after releasing the PM-list mutex')
    result=dict(passed=True,cases=88,outcomes=rows,source_sha256={n:hashlib.sha256(raw).hexdigest() for n,raw in sources.items()},
        final_core_sha256=FINAL_CORE_SHA,base_core_sha256=CORE_PATCHED_SHA,generated_dma_sha256=hashlib.sha256(dma).hexdigest(),
        harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),actual_backend_executed=True,actual_producer_executed=True,pinned_pmu_api_executed=True,actual_domain_reads_executed=True,
        all_tuples_validated_before_reads=True,missing_config_refused_without_reads=True,generated_unlocked_dma_hook_executed=True,hardware_verified=False)
    (output/'result.json').write_bytes((json.dumps(result,indent=2)+'\n').encode());return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--core-driver',type=Path,required=True);p.add_argument('--pmu-source',type=Path,required=True);p.add_argument('--dma-helper',type=Path,required=True);p.add_argument('--domain-source',type=Path,required=True)
    a=p.parse_args();r=run(a.output,a.core_driver,a.pmu_source,a.dma_helper,a.domain_source);print(json.dumps(dict(passed=r['passed'],cases=r['cases'])))
