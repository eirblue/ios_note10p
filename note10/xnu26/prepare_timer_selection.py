"""Pinned XNU physical decrementer selection patch and source-fragment execution tests."""
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from prepare_build_selection import ROOT, NDK, replace_one
sys.path.insert(0,str(ROOT/'note10/shim'))
from test_cap_entry import elf
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
from unicorn import arm64_const as regs
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN

REL=Path('osfmk/arm64/machine_routines.c')
PIN='a1eb04ef6e17b597fbfedc41ff84558dcda18768fdb4f59f0dda242f9267800e'

def function(text,name):
    start=text.index('\n'+name+'(')+1
    brace=text.index('{',start);depth=1;end=brace+1
    while depth:
        depth+=(text[end]=='{')-(text[end]=='}');end+=1
    # The selected source functions contain no braces inside comments/strings.
    return text[start:end]

def fixture(text):
    start=text.index('#if defined(ARM64_BOARD_CONFIG_EXYNOS9825)\n#if HAS_APPLE_GENERIC_TIMER')
    end=text.index('\n/*\n * Assumes fiq, irq disabled.',start)
    return '''#include <stdint.h>
typedef int boolean_t;
#define TRUE 1
#define FALSE 0
#define ISB_SY 15
#define CNTV_CTL_EL0_ENABLE 1
#define CNTV_CTL_EL0_IMASKED 2
#define CNTV_CTL_EL0_ISTATUS 4
#define CNTP_CTL_EL0_IMASKED 2
#define assert(x) ((void)0)
typedef struct { uint32_t cpu_decrementer; void (*cpu_set_decrementer_func)(uint32_t); uint32_t (*cpu_get_decrementer_func)(void); } cpu_data_t;
static cpu_data_t test_cpu;
static cpu_data_t *getCpuDatap(void) { return &test_cpu; }
''' + text[start:end] + '\n' + '\n'.join([
        'void '+function(text,'ml_set_decrementer'),
        'uint32_t '+function(text,'ml_get_decrementer'),
        'boolean_t '+function(text,'ml_get_timer_pending'),
        'uint64_t '+function(text,'speculative_timebase'),
        'static void '+function(text,'_enable_virtual_timer')]) + '''
void test_reset(uint32_t value) { test_cpu.cpu_decrementer=value; test_cpu.cpu_set_decrementer_func=0; test_cpu.cpu_get_decrementer_func=0; }
void test_enable(void) { _enable_virtual_timer(); }
'''

def execute(path,variant):
    segments,symbols=elf(path.read_bytes());base=0x1000000
    u=Uc(UC_ARCH_ARM64,UC_MODE_ARM);u.mem_map(base,0x10000)
    for va,_,data in segments:u.mem_write(base+va,data)
    u.mem_map(0x2000000,0x10000);u.reg_write(regs.UC_ARM64_REG_SP,0x2008000)
    stop=base+0xf000;md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN)
    tval,ctl,counter=('cntp_tval_el0','cntp_ctl_el0','cntvct_el0') if variant=='exynos' else (
        ('s3_1_c15_c15_4','s3_1_c15_c0_5','s3_4_c15_c11_7') if variant=='apple' else
        ('cntv_tval_el0','cntv_ctl_el0','cntvct_el0'))
    values={counter:0x123456789,tval:0,ctl:0};writes=[];reads=[];returned=False
    def gpr(name):return getattr(regs,'UC_ARM64_REG_'+name.upper())
    def instruction(engine,address,size,_):
        nonlocal returned
        if address==stop:returned=True;engine.emu_stop();return
        i=next(md.disasm(bytes(engine.mem_read(address,size)),address))
        if i.mnemonic not in ('mrs','msr'):return
        a,b=[p.strip().lower() for p in i.op_str.split(',')]
        if i.mnemonic=='mrs':
            assert b in values,b
            reads.append(b);engine.reg_write(gpr(a),values[b])
        else:
            assert a in (tval,ctl,'cntp_ctl_el0','cntv_ctl_el0','s3_1_c15_c13_4'),a
            v=engine.reg_read(gpr(b));writes.append((a,v));values[a]=v
        engine.reg_write(regs.UC_ARM64_REG_PC,address+4)
    u.hook_add(UC_HOOK_CODE,instruction)
    def call(name,value=0):
        nonlocal returned
        returned=False;u.reg_write(regs.UC_ARM64_REG_X0,value);u.reg_write(regs.UC_ARM64_REG_LR,stop)
        u.emu_start(base+symbols[name],base+0x10000,count=2000)
        assert returned,name
        return u.reg_read(regs.UC_ARM64_REG_X0)
    cases=0
    for value in (0,1,0x7fffffff,0x80000000,0xffffffff):
        call('test_reset',value);writes.clear();call('test_enable')
        expected=[('cntp_ctl_el0',2),('cntv_ctl_el0',2),(tval,value),(ctl,1)] if variant=='exynos' else [
            (ctl,1),('cntp_ctl_el0',2)] + ([('s3_1_c15_c13_4',2)] if variant=='apple' else [])
        assert writes==expected,(variant,writes,expected)
        writes.clear();call('ml_set_decrementer',value)
        assert writes==[(tval,value)]
        assert call('ml_get_decrementer')==value
        assert call('speculative_timebase')==values[counter]
        cases+=1
    for value in range(8):
        values[ctl]=value
        assert call('ml_get_timer_pending')==int(bool(value&4));cases+=1
    assert set(reads)<={tval,ctl,counter}
    return cases

def main():
    target=json.loads((ROOT/'note10/target.json').read_text())
    research=ROOT/target['research_directory']
    source=ROOT/json.loads((research/'xnu-reference.json').read_text())['source_directory']
    raw=(source/REL).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PIN:raise ValueError('Pinned timer source mismatch')
    old=raw.decode()
    anchor='#if HAS_APPLE_GENERIC_TIMER\n/* The kernel timer APIs always use the Apple timebase */'
    new=replace_one(old,anchor,'''#if defined(ARM64_BOARD_CONFIG_EXYNOS9825)
#if HAS_APPLE_GENERIC_TIMER
#error Exynos9825 cannot select the Apple generic timer
#endif
/* Keep the virtual timebase shared with userspace; decrementer TVAL is relative. */
#define KERNEL_CNTV_TVAL_EL0 "CNTP_TVAL_EL0"
#define KERNEL_CNTVCT_EL0    "CNTVCT_EL0"
#define KERNEL_CNTVCTSS_EL0  "CNTVCTSS_EL0"
#define KERNEL_CNTV_CTL_EL0  "CNTP_CTL_EL0"
#define KERNEL_CNTKCTL_EL1   "CNTKCTL_EL1"
#elif HAS_APPLE_GENERIC_TIMER
/* The kernel timer APIs always use the Apple timebase */''')
    anchor='\t__builtin_arm_wsr64(KERNEL_CNTV_CTL_EL0, cntvctl);\n\t/* disable the physical timer as a precaution, as its registers reset to architecturally unknown values */'
    new=replace_one(new,anchor,'''#if defined(ARM64_BOARD_CONFIG_EXYNOS9825)
\t/* IRQs are masked by the caller. Establish a known physical deadline first. */
\t__builtin_arm_wsr64("CNTP_CTL_EL0", CNTP_CTL_EL0_IMASKED);
\t__builtin_arm_wsr64("CNTV_CTL_EL0", CNTV_CTL_EL0_IMASKED);
\t__builtin_arm_wsr64(KERNEL_CNTV_TVAL_EL0, (uint64_t)getCpuDatap()->cpu_decrementer);
\t__builtin_arm_wsr64(KERNEL_CNTV_CTL_EL0, cntvctl);
\t__builtin_arm_isb(ISB_SY);
#else
\t__builtin_arm_wsr64(KERNEL_CNTV_CTL_EL0, cntvctl);
\t/* disable the physical timer as a precaution, as its registers reset to architecturally unknown values */''')
    anchor='\t__builtin_arm_wsr64("S3_1_C15_C13_4", CNTP_CTL_EL0_IMASKED);\n#endif\n}'
    new=replace_one(new,anchor,anchor[:-1]+'#endif /* ARM64_BOARD_CONFIG_EXYNOS9825 */\n}')
    patch=ROOT/'note10/xnu26/patches/0002-exynos9825-physical-decrementer.patch'
    patch.write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),
        fromfile='a/'+REL.as_posix(),tofile='b/'+REL.as_posix())),newline='\n')
    private=ROOT/'note10/private/xnu26-timer';private.mkdir(exist_ok=True)
    git=['git','-c','core.autocrlf=false','apply']
    subprocess.run([*git,'--check','--directory',source.relative_to(ROOT).as_posix(),patch.relative_to(ROOT).as_posix()],cwd=ROOT,check=True)
    stage=private/'stage';(stage/REL).parent.mkdir(parents=True,exist_ok=True);(stage/REL).write_bytes(raw)
    command=[*git,'--directory',stage.relative_to(ROOT).as_posix()]
    subprocess.run([*command,patch.relative_to(ROOT).as_posix()],cwd=ROOT,check=True)
    assert (stage/REL).read_bytes()==new.encode()
    subprocess.run([*command,'--reverse',patch.relative_to(ROOT).as_posix()],cwd=ROOT,check=True)
    assert (stage/REL).read_bytes()==raw and (source/REL).read_bytes()==raw
    c=private/'timer-fragment.c';c.write_text(fixture(new),newline='\n')
    script=private/'test.ld'
    script.write_text('ENTRY(test_enable)\nPHDRS { all PT_LOAD FLAGS(7); }\nSECTIONS { . = 0; .text : { *(.text*) } :all .rodata : { *(.rodata*) } :all .data : { *(.data*) } :all .bss : { *(.bss*) *(COMMON) } :all }\n')
    tools=NDK/'toolchains/llvm/prebuilt/windows-x86_64/bin'
    flags=['--target=aarch64-none-elf','-march=armv8.2-a','-O2','-ffreestanding','-fno-builtin','-fno-stack-protector','-mgeneral-regs-only','-Wall','-Wextra','-Werror']
    result=[]
    for variant,defines in [('exynos',['-DARM64_BOARD_CONFIG_EXYNOS9825=1']),('generic',[]),('apple',['-DHAS_APPLE_GENERIC_TIMER=1'])]:
        obj=private/(variant+'.o');exe=private/(variant+'.elf')
        subprocess.run([str(tools/'clang.exe'),*flags,*defines,'-c',str(c),'-o',str(obj)],check=True)
        subprocess.run([str(tools/'ld.lld.exe'),'-T',str(script),str(obj),'-o',str(exe)],check=True)
        result.append({'variant':variant,'cases':execute(exe,variant),'elf_sha256':hashlib.sha256(exe.read_bytes()).hexdigest()})
    conflict=subprocess.run([str(tools/'clang.exe'),*flags,'-DARM64_BOARD_CONFIG_EXYNOS9825=1','-DHAS_APPLE_GENERIC_TIMER=1','-fsyntax-only',str(c)],capture_output=True,text=True)
    assert conflict.returncode and 'Exynos9825 cannot select the Apple generic timer' in conflict.stderr
    report={'source_sha256':PIN,'patch_sha256':hashlib.sha256(patch.read_bytes()).hexdigest(),'variants':result,
            'conflicting_selection_rejected':True,'apply_reverse_passed':True,'source_unchanged':True,
            'limits':'Compiled actual source fragments with test-only CPU-data/assert definitions; emulated synthetic system registers, no hardware execution or full XNU build.'}
    (private/'result.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({'variant_cases':result,'conflict_rejected':True,'passed':True}))

if __name__=='__main__':main()
