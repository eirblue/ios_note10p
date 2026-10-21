"""Execute bootstrap/initialization source with synthetic DT, mapping and binding services."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
from prepare_build_selection import ROOT, NDK
from prepare_timer_selection import elf, function
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn import arm64_const as regs
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN

def build(integrated=False):
    private=ROOT/'note10/private/xnu26-bootstrap';tree=private/'patched-inputs'
    manifest=json.loads((private/'patch-result.json').read_text())
    for name,digest in manifest['files'].items():assert hashlib.sha256((tree/name).read_bytes()).hexdigest()==digest
    body=(tree/'pexpert/arm/pe_note10_bootstrap.c').read_text(encoding='utf-8')
    body='\n'.join(line for line in body.splitlines() if not line.startswith('#include'))
    bridge_tree=ROOT/'note10/private/xnu26-irq/patched-inputs'
    if integrated:
        bridge_manifest=json.loads((bridge_tree.parent/'patch-result.json').read_text())
        for name,digest in bridge_manifest['component_sha256'].items():
            assert hashlib.sha256((bridge_tree/name).read_bytes()).hexdigest()==digest,name
        bridge=(bridge_tree/'pexpert/arm/pe_note10_irq.c').read_text(encoding='utf-8')
        bridge='\n'.join(line for line in bridge.splitlines() if not line.startswith('#include'))
        bridge='void '+function((bridge_tree/'osfmk/arm/rtclock.c').read_text(encoding='utf-8'),'note10_rtclock_intr')+'\n'+bridge
        body='''#include "note10/gicv2_mmio.h"
typedef struct { uint32_t cpu_decrementer; } cpu_data_t;
static cpu_data_t cpu;
static cpu_data_t *getCpuDatap(void) { return &cpu; }
__attribute__((noinline)) void rtclock_intr(unsigned ignored) {
    (void)ignored; cpu.cpu_decrementer=12345;
    __builtin_arm_wsr64("CNTP_TVAL_EL0",12345);
}
'''+bridge+'\n'+body
    init=(tree/'pexpert/arm/pe_identify_machine.c').read_text(encoding='utf-8')
    types='''#include <stdint.h>
#include <stddef.h>
typedef uintptr_t vm_offset_t; typedef uintptr_t vm_size_t; typedef void *DTEntry;
typedef struct { unsigned num_cpus; } ml_topology_info_t;
#define kSuccess 0
'''
    declarations='''
extern int SecureDTLookupEntry(void *,char const *,DTEntry *);
extern int SecureDTGetProperty(DTEntry,char const *,void const **,unsigned int *);
extern vm_offset_t ml_io_map(uint64_t,vm_size_t);
extern void pe_note10_bind_irq(vm_offset_t,vm_size_t,vm_offset_t,vm_size_t,uint32_t);
__attribute__((noreturn)) extern void panic(char const *,...);
extern void kprintf(char const *,...);
extern uint32_t pe_arm_init_timer(void *);
'''
    src=private/'bootstrap-fragment.c'
    src.write_text(types+declarations+'''
static ml_topology_info_t topology; static unsigned enabled;
static struct { uint32_t timebase_frequency_hz; } gPEClockFrequencyInfo;
const ml_topology_info_t *ml_get_topology_info(void) { return &topology; }
int ml_get_interrupts_enabled(void) { return enabled; }
void test_setup(unsigned count,unsigned irq_enabled,uint32_t frequency) { topology.num_cpus=count; enabled=irq_enabled; gPEClockFrequencyInfo.timebase_frequency_hz=frequency; }
'''+body+'\nuint32_t '+function(init,'pe_arm_init_interrupts')+'\n',encoding='utf-8',newline='\n')
    stubs=private/'services.c'
    service_text=types+'''
int SecureDTLookupEntry(void *a,char const *b,DTEntry *c) { (void)a;(void)b;(void)c;return 1; }
int SecureDTGetProperty(DTEntry a,char const *b,void const **c,unsigned int *d) { (void)a;(void)b;(void)c;(void)d;return 1; }
vm_offset_t ml_io_map(uint64_t a,vm_size_t b) { (void)a;(void)b;return 0; }
void pe_note10_bind_irq(vm_offset_t a,vm_size_t b,vm_offset_t c,vm_size_t d,uint32_t e) { (void)a;(void)b;(void)c;(void)d;(void)e; }
__attribute__((noreturn)) void panic(char const *a,...) { (void)a;for (;;) __asm__ volatile("wfe"); }
void kprintf(char const *a,...) { (void)a; }
uint32_t pe_arm_init_timer(void *a) { (void)a;return 1; }
'''
    if integrated:
        service_text='\n'.join(line for line in service_text.splitlines() if not line.startswith('void pe_note10_bind_irq'))
    stubs.write_text(service_text,newline='\n')
    tools=NDK/'toolchains/llvm/prebuilt/windows-x86_64/bin'
    flags=['--target=aarch64-none-elf','-march=armv8.2-a','-mstrict-align','-O2','-ffreestanding','-fno-builtin','-fno-stack-protector','-mgeneral-regs-only','-Wall','-Wextra','-Werror']
    objects=[]
    sources=[src,stubs]
    if integrated:sources.extend(bridge_tree/'pexpert/arm/note10'/name for name in ('gicv2.c','gicv2_mmio.c'))
    for c in sources:
        obj=private/(c.stem+'.o');objects.append(obj)
        subprocess.run([str(tools/'clang.exe'),*flags,'-DARM64_BOARD_CONFIG_EXYNOS9825=1','-I',str(bridge_tree/'pexpert/arm'),'-c',str(c),'-o',str(obj)],check=True)
    script=private/'test.ld'
    script.write_text('ENTRY(pe_arm_init_interrupts)\nPHDRS { all PT_LOAD FLAGS(7); }\nSECTIONS { . = 0; .text : { *(.text*) } :all .rodata : { *(.rodata*) } :all .data : { *(.data*) } :all .bss : { *(.bss*) *(COMMON) } :all }\n')
    exe=private/('bootstrap-integrated.elf' if integrated else 'bootstrap-fragment.elf')
    subprocess.run([str(tools/'ld.lld.exe'),'-T',str(script),*[str(o) for o in objects],'-o',str(exe)],check=True)
    subprocess.run([str(tools/'clang.exe'),*flags,'-fsyntax-only',str(tree/'pexpert/arm/pe_note10_bootstrap.c')],check=True)
    return exe

def run(exe,case,integrated=False):
    base=0x1000000;stop=base+0xf000;data=0x4000000
    u=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
    for addr in (base,0x2000000,data):u.mem_map(addr,0x10000)
    if integrated:
        u.mem_map(0x3000000,0x2000)
        for addr,value in ((0x3000000,case.get('dctl',1)),(0x3000004,31),(0x3000008,0x12345678),
                (0x3001000,case.get('cctl',1)),(0x30010fc,0x02043b),(0x300100c,case.get('irq',30))):
            u.mem_write(addr,struct.pack('<I',value))
    segments,symbols=elf(exe.read_bytes())
    for va,_,raw in segments:u.mem_write(base+va,raw)
    u.reg_write(regs.UC_ARM64_REG_SP,0x2008000)
    properties={'compatible':b'samsung,exynos9825-note10\0','version':struct.pack('<I',1),
        'gic-handoff':struct.pack('<I',1),'gic-reg':struct.pack('<4Q',0x10101000,0x1000,0x10102000,0x1000),
        'timer-intid':struct.pack('<I',30),'timebase-frequency':struct.pack('<I',26000000)}
    properties.update(case.get('properties',{}));pointers={}
    for i,(name,raw) in enumerate(properties.items()):
        if raw is None:continue
        ptr=data+0x101+i*0x100;u.mem_write(ptr,raw);pointers[name]=(ptr,len(raw))
    trace=[];panic=None;returned=False;md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN)
    def reg(i):return getattr(regs,'UC_ARM64_REG_X'+str(i))
    def string(ptr):return bytes(u.mem_read(ptr,128)).split(b'\0')[0].decode()
    def ret(value=0):u.reg_write(reg(0),value);u.reg_write(regs.UC_ARM64_REG_PC,u.reg_read(regs.UC_ARM64_REG_LR))
    def instruction(engine,address,size,_):
        nonlocal panic,returned
        if address==stop:returned=True;engine.emu_stop();return
        args=[u.reg_read(reg(i)) for i in range(5)]
        if address==base+symbols['panic']:
            panic=string(args[0]);trace.append('panic');engine.emu_stop();return
        if address==base+symbols['kprintf']:ret();return
        if address==base+symbols['SecureDTLookupEntry']:
            assert string(args[1])=='/chosen/note10-platform';trace.append('lookup')
            if case.get('missing_node'):ret(1)
            else:u.mem_write(args[2],struct.pack('<Q',1));ret()
            return
        if address==base+symbols['SecureDTGetProperty']:
            name=string(args[1]);trace.append(('property',name))
            if name not in pointers:ret(1)
            else:
                ptr,length=pointers[name]
                u.mem_write(args[2],struct.pack('<Q',0 if case.get('null_property')==name else ptr))
                u.mem_write(args[3],struct.pack('<I',length));ret()
            return
        if address==base+symbols['ml_io_map']:
            maps=[t for t in trace if isinstance(t,tuple) and t[0]=='map']
            trace.append(('map',args[0],args[1]));expected=(0x10101000,0x10102000)[len(maps)]
            assert args[:2]==[expected,0x1000]
            mapping=0x3000000+len(maps)*0x1000
            if case.get('overlapping_maps'):mapping=0x3000000
            if case.get('unaligned_map'):mapping+=1
            ret(0 if case.get('map_failure')==len(maps)+1 else mapping);return
        if address==base+symbols['pe_note10_bind_irq']:
            trace.append('bind')
            if not integrated:
                assert args==[0x3000000,0x1000,0x3001000,0x1000,30]
                ret();return
        if integrated and address==base+symbols['rtclock_intr']:trace.append('callback')
        if address==base+symbols['pe_arm_init_timer']:trace.append('timebase');ret(1);return
        ins=next(md.disasm(bytes(u.mem_read(address,size)),address))
        if ins.mnemonic=='mrs':
            dst,sysreg=[p.strip().lower() for p in ins.op_str.split(',')]
            assert sysreg=='cntfrq_el0';trace.append('cntfrq')
            u.reg_write(getattr(regs,'UC_ARM64_REG_'+dst.upper()),case.get('counter_frequency',26000000))
            u.reg_write(regs.UC_ARM64_REG_PC,address+4)
        elif ins.mnemonic=='msr':
            assert integrated
            name,source=[p.strip().lower() for p in ins.op_str.split(',')]
            assert name in ('cntp_ctl_el0','cntp_tval_el0')
            trace.append((name,u.reg_read(getattr(regs,'UC_ARM64_REG_'+source.upper()))))
            u.reg_write(regs.UC_ARM64_REG_PC,address+4)
    u.hook_add(UC_HOOK_CODE,instruction)
    def write(engine,access,address,size,value,_):
        if 0x3000000<=address<0x3002000:
            assert size==4
            assert (address,value) in ((0x3000100,1<<30),(0x3001010,case.get('irq',30)))
            trace.append(('mmio_write',address,value))
    if integrated:u.hook_add(UC_HOOK_MEM_WRITE,write)
    def call(name,args):
        nonlocal returned
        returned=False
        for i,value in enumerate(args):u.reg_write(reg(i),value)
        u.reg_write(regs.UC_ARM64_REG_LR,stop);u.emu_start(base+symbols[name],base+0x10000,count=10000)
        assert returned or panic
    call('test_setup',(case.get('cpus',1),case.get('interrupts',0),case.get('kernel_frequency',26000000)))
    call('pe_arm_init_interrupts',(0 if case.get('null_args') else 1,))
    maps=[t for t in trace if isinstance(t,tuple) and t[0]=='map']
    if 'panic' in case:
        assert panic and case['panic'] in panic,(case,panic,trace)
        assert len(maps)==case.get('maps',0) and ('bind' in trace)==case.get('binding_panic',False) and 'timebase' not in trace
        assert not any(isinstance(t,tuple) and t[0]=='mmio_write' for t in trace)
    elif case.get('null_args'):assert not panic and trace==['timebase']
    else:
        ending=['bind',('mmio_write',0x3000100,1<<30),'timebase'] if integrated else ['bind','timebase']
        assert not panic and len(maps)==2 and trace[-len(ending):]==ending,trace
        assert u.reg_read(reg(0))==1
        if integrated:
            trace.clear();call('pe_note10_handle_irq',())
            if case.get('irq',30)>=1020:assert trace==[] and not panic,trace
            elif case.get('irq_panic'):
                assert panic and case['irq_panic'] in panic and trace==['panic'],(panic,trace)
            else:
                assert not panic and trace==[('cntp_ctl_el0',3),'callback',('cntp_tval_el0',12345),
                    ('mmio_write',0x3001010,30),('cntp_ctl_el0',1)],trace
    return {'name':case['name'],'panic':panic,'passed':True}

def main():
    integrated='--integrated' in sys.argv[1:]
    exe=build(integrated);u32=lambda n:struct.pack('<I',n)
    cases=[{'name':'valid_handoff'},{'name':'null_args_common_timebase','null_args':True},
        {'name':'missing_node','missing_node':True,'panic':'contract missing'},
        {'name':'wrong_compatible','properties':{'compatible':b'x'*len(b'samsung,exynos9825-note10\0')},'panic':'incompatible'},
        {'name':'bad_version','properties':{'version':u32(2)},'panic':'handoff required'},
        {'name':'handoff_unprepared','properties':{'gic-handoff':u32(0)},'panic':'handoff required'},
        {'name':'missing_reg','properties':{'gic-reg':None},'panic':'property'},
        {'name':'short_reg','properties':{'gic-reg':b'\0'*31},'panic':'property'},
        {'name':'null_reg','null_property':'gic-reg','panic':'property'},
        {'name':'wrong_address','properties':{'gic-reg':struct.pack('<4Q',0x10100000,0x1000,0x10102000,0x1000)},'panic':'windows'},
        {'name':'wrong_size','properties':{'gic-reg':struct.pack('<4Q',0x10101000,0x2000,0x10102000,0x1000)},'panic':'windows'},
        {'name':'wrong_ppi','properties':{'timer-intid':u32(27)},'panic':'PPI'},
        {'name':'wrong_dt_frequency','properties':{'timebase-frequency':u32(24000000)},'panic':'frequency mismatch'},
        {'name':'kernel_fallback','kernel_frequency':24000000,'panic':'frequency mismatch'},
        {'name':'zero_counter_frequency','counter_frequency':0,'panic':'frequency mismatch'},
        {'name':'counter_overflow','counter_frequency':1<<32,'panic':'frequency mismatch'},
        {'name':'map1_failed','map_failure':1,'maps':1,'panic':'distributor map failed'},
        {'name':'map2_failed','map_failure':2,'maps':2,'panic':'CPU interface map failed'},
        {'name':'smp','cpus':8,'panic':'single CPU'},{'name':'interrupts_enabled','interrupts':1,'panic':'masked interrupts'}]
    if integrated:
        cases.extend([{'name':'disabled_distributor','dctl':0,'maps':2,'binding_panic':True,'panic':'initialized nonsecure'},
            {'name':'disabled_cpu','cctl':0,'maps':2,'binding_panic':True,'panic':'initialized nonsecure'},
            {'name':'eoi_mode9','cctl':513,'maps':2,'binding_panic':True,'panic':'initialized nonsecure'},
            {'name':'eoi_mode10','cctl':1025,'maps':2,'binding_panic':True,'panic':'initialized nonsecure'},
            {'name':'overlapping_mappings','overlapping_maps':True,'maps':2,'binding_panic':True,'panic':'invalid mapped'},
            {'name':'unaligned_mapping','unaligned_map':True,'maps':2,'binding_panic':True,'panic':'invalid mapped'},
            {'name':'unknown_irq','irq':40,'irq_panic':'unimplemented interrupt'},
            *({'name':'special_irq_'+str(n),'irq':n} for n in range(1020,1024))])
    report={'cases':[run(exe,c,integrated) for c in cases],'elf_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),
        'patch_sha256':json.loads((exe.parent/'patch-result.json').read_text())['patch_sha256'],
        'limits':'Actual bootstrap/init source functions with synthetic types, DT, CNTFRQ, mapping, binding and common timebase services. No hardware or full kernel.'}
    if integrated:
        report['bridge_patch_sha256']=json.loads((ROOT/'note10/private/xnu26-irq/patch-result.json').read_text())['patch_sha256']
        report['limits']='Actual bootstrap/init, binder, GIC core/MMIO and timer IRQ handler linked together. Synthetic types, DT, registers, MMIO and kernel services. No hardware or full kernel.'
    (exe.parent/('integration-result.json' if integrated else 'test-result.json')).write_text(json.dumps(report,indent=2))
    print(json.dumps({'cases':len(cases),'passed':True,'hardware_accessed':False}))
if __name__=='__main__':main()
