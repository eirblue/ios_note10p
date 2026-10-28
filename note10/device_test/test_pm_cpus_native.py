"""Full pinned suspend caller, noirq helper and original CPU hotplug functions."""
import argparse,hashlib,json,re,shutil,subprocess,sys
from pathlib import Path
from run_probe import ROOT
from prepare_pm_noirq import HERE,FINAL_SHA
from prepare_pm_cpus import SOURCES,PINS
from test_fsys_pm_native import function
from test_pm_noirq_native import STUB,PMU_STUB,MAIN,IDENTITY
from test_pm_cpu_hotplug_native import STUB as HP_STUB,run as run_hotplug
from decode_pm_cpus import decode
from decode_pm_noirq import decode as decode_noirq
ACCEPTED=(0,19,23,28,30,36,42,69,70)
CPU_PMU=r'''
static struct n10_pmu_noirq_sample cpu_pmu_sample;
static unsigned int cpu_pmu_captures;
void n10_pmu_cpu_capture(unsigned int generation){
 if(!pm_mutex || irq || !late_suspended || !device_irq_off || online.bits!=1 || cpu_pmu_captures++)abort();
 cpu_pmu_sample=(struct n10_pmu_noirq_sample){generation,1,argument_mode==72?5:0,0,0,0};
 if(argument_mode==73)++cpu_pmu_sample.generation;
}
int n10_pmu_cpu_read(struct n10_pmu_noirq_sample*out,unsigned int completed){
 unsigned int next=cpu_pmu_sample.generation+1;if(!next)next=1;
 if(!pm_mutex)abort();*out=cpu_pmu_sample;
 return !out->generation || next!=completed || out->error || out->seen!=1 || ((out->before|out->state|out->after)&~65535U)?-EIO:0;
}
'''

def run(output,suspend_source,raw_suspend,header,cpu_source,cpu_header,core_driver,pmu_source,domain_source):
    out=Path(output).resolve();source=Path(suspend_source).read_bytes();raw=Path(raw_suspend).read_bytes();header=Path(header).read_text()
    if out.exists() or not out.is_relative_to((ROOT/'note10/private').resolve()):raise ValueError('Fresh private CPU model required')
    from prepare_pm_diagnostic import SUSPEND_SHA
    if hashlib.sha256(source).hexdigest()!=FINAL_SHA or hashlib.sha256(raw).hexdigest()!=SUSPEND_SHA:raise ValueError('Pinned guarded suspend source differs')
    cpu=Path(cpu_source).read_bytes();cpuh=Path(cpu_header).read_bytes()
    if hashlib.sha256(cpu).hexdigest()!=PINS['kernel/cpu.c'] or hashlib.sha256(cpuh).hexdigest()!=PINS['include/linux/cpu.h']:raise ValueError('Pinned hotplug source differs')
    source=source.decode();raw=raw.decode();out.mkdir(parents=True)
    clean=lambda s:re.sub(r'^#include[^\n]*\n','',s,flags=re.M)
    stub=STUB
    for declaration in ('static int disable_nonboot_cpus(', 'static void enable_nonboot_cpus('):stub=stub.replace(function(stub,declaration),'')
    hp=clean(re.sub(r'\bmode\b','hp_mode',HP_STUB))
    for name in ('pr_info','pr_err','trace_suspend_resume','dbg_snapshot_suspend','BUG_ON'):
        hp=re.sub(r'^#define '+name+r'[^\n]*\n','',hp,flags=re.M)
    stub=stub.replace('static int pm_wakeup_pending(void){return 0;}','')
    prefix=stub[:stub.index('static void s2idle_begin')]
    start=header.index('struct platform_suspend_ops {');ops=header[start:header.index('};',start)+2]
    contract=(HERE/'pm_test_contract.h').read_text()+(HERE/'pm_quiesce_core.h').read_text()
    prefix+=ops+'\nstatic struct platform_suspend_ops ops;\nstatic const struct platform_suspend_ops*suspend_ops;\n'+contract
    prefix+='\nstatic struct n10_pm_result*n10_pm_active;\nstatic struct task_struct*n10_pm_owner;\n'+stub[stub.index('static void s2idle_begin'):]
    declarations=''.join(clean((HERE/n).read_text()) for n in ('abox_pmu_contract.h','pm_noirq_contract.h','pm_cpus_contract.h'))
    prefix=prefix.replace('static int dpm_suspend_start',declarations+'\nstatic int dpm_suspend_start')
    wrappers=''.join(function(raw,s) for s in ['static bool sleep_state_supported(', 'static int platform_suspend_prepare(', 'static int platform_suspend_prepare_late(', 'static int platform_suspend_prepare_noirq(', 'static void platform_resume_noirq(', 'static void platform_resume_early(', 'static void platform_resume_finish(', 'static int platform_suspend_begin(', 'static void platform_resume_end(', 'static void platform_recover(', 'static bool platform_suspend_again('])
    selector=source[source.index('#ifdef CONFIG_NOTE10_PM_NOIRQ_TEST\n\t\tpm_test_level = TEST_PLATFORM;'):];selector=selector[:selector.index('#endif')+6]
    prefix+=wrappers+'static void select_level(void){\n'+selector+'\n}\n'
    hp=hp.replace('static int pm_wakeup_pending(void){if(!locked)abort();','static int pm_wakeup_pending(void){if(!locked)return 0;')
    hp=hp.replace('online.bits|=1U<<cpu;return 0;','if(!(hp_mode==28 && cpu==7))online.bits|=1U<<cpu;return 0;')
    hp+='\n#define cpumask_bits(m) (&(m)->bits)\nstatic unsigned int argument_mode;\nstatic unsigned int raw_smp_processor_id(void){return argument_mode==85?1:online.bits==1?0:7;}\n'
    hotplug=function(cpu.decode(),'int freeze_secondary_cpus(')+function(cpu.decode(),'void enable_nonboot_cpus(')+function(cpuh.decode(),'static inline int disable_nonboot_cpus(')
    checksum=re.search(r'static u32 n10_frame_checksum[^}]+}',(HERE/'xnu_reserve.c').read_text()).group()
    bodies=function(source,'static int suspend_enter(')+function(source,'int suspend_devices_and_enter(')
    main=MAIN.replace('mode=atoi(argv[1]);','''argument_mode=atoi(argv[1]);mode=argument_mode<45?argument_mode:0;
 hp_mode=argument_mode>=45 && argument_mode<=65?argument_mode-44:argument_mode==69?25:argument_mode==70?26:argument_mode==86?28:0;
 online.bits=argument_mode==66?0xfe:argument_mode==67?1:argument_mode==68?0:argument_mode==87?0x1ff:0xff;
 cpu_hotplug_disabled=hp_mode==25?2:0;''')
    main=main.replace('pm_mutex=1;','''pm_mutex=1;
 if(argument_mode==89){n10_pm_cpus_last.seen=1;n10_pm_cpus_last.generation=out.qgeneration;}''')
    main=main.replace('pm_mutex=0;completed=','''
 if(argument_mode==71)n10_pm_cpus_last.before=254;
 if(argument_mode==75)n10_pm_cpus_last.attempted=0;
 if(argument_mode==76)n10_pm_cpus_last.seen=2;
 if(argument_mode==77)n10_pm_cpus_last.bad=1;
 if(argument_mode==78)cpu_pmu_sample.state=0x10000;
 if(argument_mode==79)cpu_pmu_sample.seen=0;
 if(argument_mode==80)n10_pm_cpus_last.enabled=0;
 if(argument_mode==81)n10_pm_cpus_last.generation=0;
 if(argument_mode==82)n10_pm_cpus_last.original_error=-5;
 if(argument_mode==83)n10_pm_cpus_last.error=-16;
 if(argument_mode==84)n10_pm_cpus_last.phase=5;
 if(argument_mode==88)n10_pm_cpus_last.stopped=2;
 if(locked || storage.bits || cpu_hotplug_disabled!=(hp_mode==25?2:0))abort();
 if(n10_pm_cpus_last.attempted && (downs!=ups && !(hp_mode>=1 && hp_mode<=7)))abort();
 if((argument_mode>=59 && argument_mode<=65 || argument_mode==86) && ret!=-EIO)abort();
 pm_mutex=0;completed=''')
    main=main.replace('n10_report_pm_noirq(mode==26?completed+1:completed);','''n10_report_pm_noirq(mode==26?completed+1:completed);
 n10_report_pm_cpus(argument_mode==74?completed+1:completed);''')
    compiler=ROOT/'host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe' if sys.platform=='win32' else shutil.which('cc')
    code='#define CONFIG_NOTE10_PM_NOIRQ_TEST\n#define CONFIG_NOTE10_PM_CPUS_TEST\n'+prefix+hp+hotplug+PMU_STUB+CPU_PMU
    code+=clean((HERE/'pm_noirq_backend.c').read_text())+clean((HERE/'pm_cpus_backend.c').read_text())+checksum
    code+=clean((HERE/'pm_noirq_probe.c').read_text())+clean((HERE/'pm_cpus_probe.c').read_text())+bodies+main
    p=out/'cpu-noirq.c';p.write_bytes(code.encode());exe=out/('cpu-noirq.exe' if sys.platform=='win32' else 'cpu-noirq')
    made=subprocess.run([str(compiler),'-std=c11','-O2',str(p),'-o',str(exe)],capture_output=True,timeout=60);(out/'compile.log').write_bytes(made.stdout+made.stderr)
    if made.returncode:raise ValueError('CPU full noirq integration model compilation failed')
    rows=[]
    for mode in range(90):
        ran=subprocess.run([str(exe),str(mode)],capture_output=True,timeout=15);(out/f'mode-{mode}.log').write_bytes(ran.stdout+ran.stderr)
        if ran.returncode:raise ValueError('CPU noirq invariant failed mode '+str(mode))
        try:
            decode_noirq(ran.stdout.decode(),IDENTITY,1 if mode==19 else 2,cpu_roundtrip=True)
            decode(ran.stdout.decode(),IDENTITY,1 if mode==19 else 2);accepted=True
        except ValueError:accepted=False
        if accepted!=(mode in ACCEPTED):raise ValueError('CPU noirq strict acceptance differs mode '+str(mode))
        rows.append(dict(mode=mode,passed=True,accepted=accepted))
    from test_pm_cpus_pmu_native import run as run_pmu
    pmu=run_pmu(out.parent/'pm-cpus-pmu-model',core_driver,pmu_source,domain_source)
    hp_result=run_hotplug(out.parent/'pm-cpus-hotplug-model',cpu_source,cpu_header)
    from test_pm_cpus_timer_native import run as run_timers
    timer_result=run_timers(out.parent/'pm-cpus-timer-model')
    from test_pm_cpus_queue_native import run as run_queue
    queue_result=run_queue(out.parent/'pm-cpus-queue-model')
    result=dict(passed=True,cases=90,outcomes=rows,pmu_model=pmu,hotplug_model=hp_result,timer_model=timer_result,queue_model=queue_result,
        actual_suspend_caller_and_enter_executed=True,actual_noirq_callback_hook_executed=True,actual_original_hotplug_executed=True,
        cpu_restore_failure_returns_eio=True,irq_syscore_machine_entry_blocked=True,partial_freeze_always_unwound=True,
        hardware_verified=False,suspend_sha256=FINAL_SHA,cpu_source_pins=PINS,
        source_sha256={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES},
        noirq_backend_sha256=hashlib.sha256((HERE/'pm_noirq_backend.c').read_bytes()).hexdigest(),
        harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (out/'result.json').write_bytes((json.dumps(result,indent=2)+'\n').encode());return result

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('output','suspend-source','raw-suspend','header','cpu-source','cpu-header','core-driver','pmu-source','domain-source'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();r=run(a.output,a.suspend_source,a.raw_suspend,a.header,a.cpu_source,a.cpu_header,a.core_driver,a.pmu_source,a.domain_source);print(json.dumps(dict(passed=r['passed'],cases=r['cases'],pmu_cases=r['pmu_model']['cases'],hotplug_cases=r['hotplug_model']['cases'])))
