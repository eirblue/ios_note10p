"""Compile the actual IRQ bridge/core plus sleh_irq fragment; emulate synthetic MMIO and kernel services."""
import hashlib
import json
from pathlib import Path
import subprocess
from prepare_build_selection import ROOT, NDK
from prepare_timer_selection import elf, function
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn import arm64_const as regs
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
import struct

def build():
    private=ROOT/'note10/private/xnu26-irq';tree=private/'patched-inputs'
    manifest=json.loads((private/'patch-result.json').read_text())
    for name,digest in manifest['component_sha256'].items():
        assert hashlib.sha256((tree/name).read_bytes()).hexdigest()==digest,name
    bridge=(tree/'pexpert/arm/pe_note10_irq.c').read_text(encoding='utf-8')
    bridge='\n'.join(line for line in bridge.splitlines() if not line.startswith('#include'))
    sleh=(tree/'osfmk/arm64/sleh.c').read_text(encoding='utf-8')
    fixture='''#include <stdint.h>
#include "note10/gicv2_mmio.h"
#define __unused __attribute__((unused))
#define MACH_ASSERT 0
#define USE_APPLEARMSMP 0
#define DBG_INTR_TYPE_OTHER 1
typedef uintptr_t vm_offset_t;
typedef uintptr_t vm_size_t;
typedef struct { unsigned num_cpus; } ml_topology_info_t;
typedef struct { unsigned unused; } arm_saved_state_t;
typedef struct { uint32_t cpu_decrementer; void (*interrupt_handler)(void *,void *,void *,int); void *interrupt_target,*interrupt_refCon,*interrupt_nub; int interrupt_source; } cpu_data_t;
static ml_topology_info_t topology;
static unsigned interrupts_enabled;
static cpu_data_t cpu;
static cpu_data_t *getCpuDatap(void) { return &cpu; }
const ml_topology_info_t *ml_get_topology_info(void) { return &topology; }
int ml_get_interrupts_enabled(void) { return interrupts_enabled; }
static const char * volatile panic_message;
__attribute__((noreturn,noinline)) void panic(const char *fmt,...) { panic_message=fmt; for (;;) __asm__ volatile("wfe"); }
__attribute__((noinline)) void sleh_interrupt_handler_prologue(arm_saved_state_t *s,unsigned type) { (void)s;(void)type;__asm__ volatile("":::"memory"); }
__attribute__((noinline)) void sleh_interrupt_handler_epilogue(void) { __asm__ volatile("":::"memory"); }
__attribute__((noinline)) void entropy_collect(void) { __asm__ volatile("":::"memory"); }
__attribute__((noinline)) void rtclock_intr(unsigned ignored) { (void)ignored; cpu.cpu_decrementer=12345; __builtin_arm_wsr64("CNTP_TVAL_EL0",12345); }
void test_configure(unsigned count,unsigned enabled) { topology.num_cpus=count; interrupts_enabled=enabled; }
'''+'\nvoid '+function((tree/'osfmk/arm/rtclock.c').read_text(encoding='utf-8'),'note10_rtclock_intr')+'\n'+bridge+'\nvoid '+function(sleh,'sleh_irq')+'\n'
    src=private/'irq-fragment.c';src.write_text(fixture,encoding='utf-8',newline='\n')
    tools=NDK/'toolchains/llvm/prebuilt/windows-x86_64/bin'
    flags=['--target=aarch64-none-elf','-march=armv8.2-a','-O2','-ffreestanding','-fno-builtin','-fno-stack-protector','-mgeneral-regs-only','-Wall','-Wextra','-Werror']
    objects=[]
    for source in (src,tree/'pexpert/arm/note10/gicv2.c',tree/'pexpert/arm/note10/gicv2_mmio.c'):
        obj=private/(source.stem+'.o');objects.append(obj)
        subprocess.run([str(tools/'clang.exe'),*flags,'-DARM64_BOARD_CONFIG_EXYNOS9825=1','-I',str(tree/'pexpert/arm'),'-c',str(source),'-o',str(obj)],check=True)
    script=private/'test.ld'
    script.write_text('ENTRY(sleh_irq)\nPHDRS { all PT_LOAD FLAGS(7); }\nSECTIONS { . = 0; .text : { *(.text*) } :all .rodata : { *(.rodata*) } :all .data : { *(.data*) } :all .bss : { *(.bss*) *(COMMON) } :all }\n')
    exe=private/'irq-fragment.elf'
    subprocess.run([str(tools/'ld.lld.exe'),'-T',str(script),*[str(o) for o in objects],'-o',str(exe)],check=True)
    # Other ARM64 configurations see empty new compilation units.
    for source in (tree/'pexpert/arm/pe_note10_irq.c',tree/'pexpert/arm/note10/gicv2.c',tree/'pexpert/arm/note10/gicv2_mmio.c'):
        subprocess.run([str(tools/'clang.exe'),*flags,'-fsyntax-only',str(source)],check=True)
    return exe

def run(exe,case):
    segments,symbols=elf(exe.read_bytes());base=0x1000000;dist=0x3000000;cpu=dist+0x1000
    u=Uc(UC_ARCH_ARM64,UC_MODE_ARM);u.mem_map(base,0x10000);u.mem_map(0x2000000,0x10000);u.mem_map(dist,0x2000)
    for va,_,data in segments:u.mem_write(base+va,data)
    u.reg_write(regs.UC_ARM64_REG_SP,0x2008000)
    def put(address,value):u.mem_write(address,struct.pack('<I',value))
    put(dist,case.get('dctl',1));put(dist+4,31);put(dist+8,0x12345678)
    put(cpu,case.get('cctl',1));put(cpu+0xfc,0x02043b);put(cpu+12,case.get('irq',30))
    trace=[];panicked=None;returned=False;stop=base+0xf000
    md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN)
    def gpr(name):return getattr(regs,'UC_ARM64_REG_'+name.upper())
    def instruction(engine,address,size,_):
        nonlocal panicked,returned
        if address==stop:returned=True;engine.emu_stop();return
        if address==base+symbols['panic']:
            ptr=engine.reg_read(regs.UC_ARM64_REG_X0)
            panicked=bytes(engine.mem_read(ptr,128)).split(b'\0')[0].decode();trace.append('panic');engine.emu_stop();return
        for symbol,event in [('rtclock_intr','callback'),('sleh_interrupt_handler_prologue','prologue'),('entropy_collect','entropy'),('sleh_interrupt_handler_epilogue','epilogue')]:
            if address==base+symbols[symbol]:
                trace.append(event)
                if event=='callback' and case.get('callback_mode_change'):put(cpu,513)
        i=next(md.disasm(bytes(engine.mem_read(address,size)),address))
        if i.mnemonic=='msr':
            reg,source=[p.strip().lower() for p in i.op_str.split(',')]
            assert reg in ('cntp_ctl_el0','cntp_tval_el0'),reg
            trace.append((reg,engine.reg_read(gpr(source))));engine.reg_write(regs.UC_ARM64_REG_PC,address+4)
        elif i.mnemonic=='mrs':raise AssertionError('Unexpected system-register read: '+i.op_str)
    def read(engine,access,address,size,value,_):
        if address==cpu+12:trace.append('iar')
    def write(engine,access,address,size,value,_):
        if address==base+symbols['cpu']:
            assert size==4
            trace.append(('cached_decrementer',value))
        if dist<=address<dist+0x2000:
            assert size==4
            if address==cpu+16:trace.append(('eoi',value))
            else:
                assert address==dist+0x100 and value==(1<<case.get('ppi',30))
                trace.append('enable_ppi')
    u.hook_add(UC_HOOK_CODE,instruction);u.hook_add(UC_HOOK_MEM_READ,read);u.hook_add(UC_HOOK_MEM_WRITE,write)
    def call(name,args=()):
        nonlocal returned
        returned=False
        for i,v in enumerate(args):u.reg_write(getattr(regs,'UC_ARM64_REG_X'+str(i)),v)
        u.reg_write(regs.UC_ARM64_REG_LR,stop)
        u.emu_start(base+symbols[name],base+0x10000,count=10000)
        assert returned or panicked
    call('test_configure',(case.get('cores',1),case.get('interrupts_enabled',0)))
    if not case.get('unbound'):
        call('pe_note10_bind_irq',(dist,case.get('dist_size',0x1000),cpu,0x1000,case.get('ppi',30)))
        if not panicked and case.get('rebind'):
            call('pe_note10_bind_irq',(dist,0x1000,cpu,0x1000,30))
    bind_trace=list(trace)
    if not panicked:trace.clear();call('sleh_irq',(0x2001000,))
    if case.get('panic'):
        assert panicked and case['panic'] in panicked,(case,panicked,trace)
        assert not any(isinstance(t,tuple) and t[0]=='eoi' for t in trace)
        assert ('cntp_ctl_el0',1) not in trace
    elif case.get('irq',30)>=1020:
        assert not panicked and trace==['prologue','iar','entropy','epilogue'],trace
    else:
        assert not panicked and trace==['prologue','iar',('cntp_ctl_el0',3),('cached_decrementer',0xffffffff),'callback',('cached_decrementer',12345),('cntp_tval_el0',12345),('eoi',case.get('irq',30)),('cntp_ctl_el0',1),'entropy','epilogue'],trace
        assert bind_trace==['enable_ppi']
    return {'name':case['name'],'panic':panicked,'passed':True}

def main():
    exe=build()
    cases=[{'name':'timer'},*({'name':'special_'+str(i),'irq':i} for i in range(1020,1024)),
        {'name':'unknown_spi','irq':40,'panic':'unimplemented interrupt'},
        {'name':'unknown_sgi','irq':7,'panic':'unimplemented interrupt'},
        {'name':'unbound','unbound':True,'panic':'binding missing'},
        {'name':'distributor_disabled','dctl':0,'panic':'initialized nonsecure'},
        {'name':'cpu_disabled','cctl':0,'panic':'initialized nonsecure'},
        {'name':'eoi_mode9','cctl':513,'panic':'initialized nonsecure'},
        {'name':'eoi_mode10','cctl':1025,'panic':'initialized nonsecure'},
        {'name':'repeat_binding','rebind':True,'panic':'repeated binding'},
        {'name':'zero_cpus','cores':0,'panic':'single CPU'},
        {'name':'multiple_cpus','cores':8,'panic':'single CPU'},
        {'name':'interrupts_unmasked','interrupts_enabled':1,'panic':'masked interrupts'},
        {'name':'bad_ppi_low','ppi':15,'panic':'invalid or repeated'},
        {'name':'bad_ppi_high','ppi':32,'panic':'invalid or repeated'},
        {'name':'bad_window','dist_size':4095,'panic':'invalid mapped'},
        {'name':'mode_changed_during_callback','callback_mode_change':True,'panic':'completion failed'}]
    result={'cases':[run(exe,c) for c in cases],'elf_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),
            'patch_sha256':json.loads((exe.parent/'patch-result.json').read_text())['patch_sha256'],
            'limits':'Compiled real bridge/GIC and sleh_irq function with synthetic kernel types/services/MMIO. No hardware or whole-kernel validation.'}
    (exe.parent/'test-result.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({'cases':len(cases),'passed':True,'hardware_accessed':False}))
if __name__=='__main__':main()
