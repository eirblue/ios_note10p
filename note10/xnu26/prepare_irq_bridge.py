"""Package the existing platform components into a pinned XNU IRQ bridge patch."""
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
from prepare_build_selection import ROOT, replace_one

PINS={
 'osfmk/arm/rtclock.h':'df78b4c8d7d61773e713f33545d77b5ee5cb3d90320a6a36f6957c6928cebab2',
 'osfmk/arm/rtclock.c':'b6da8a474428cab75ca8ff1f4295ae84b4c5eb5d96e2a5d2749a59cc6cc5febf',
 'osfmk/arm64/sleh.c':'4eeb208fb2510bfdc0338d1a1d7d2d702fe9eb65d332eea388720ef6574375d1',
 'pexpert/pexpert/arm/protos.h':'b667af4a892e4ac96c76039a0e0771aa55c4ae80e6d065d4e11c36dedbf082cd',
 'pexpert/conf/files.arm64':'b94caafc4d2aaaf190e7dc588af36a1a88905b0177b49e262b5caff2de3e7414'}

def main():
    target=json.loads((ROOT/'note10/target.json').read_text())
    research=ROOT/target['research_directory']
    source=ROOT/json.loads((research/'xnu-reference.json').read_text())['source_directory']
    old={}
    for name,pin in PINS.items():
        raw=(source/name).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=pin:raise ValueError('Source mismatch: '+name)
        old[name]=raw.decode()
    new=dict(old)
    new['osfmk/arm/rtclock.h']=replace_one(old['osfmk/arm/rtclock.h'],
        'extern void rtclock_intr(unsigned int);', 'extern void rtclock_intr(unsigned int);\n'
        '#if defined(ARM64_BOARD_CONFIG_EXYNOS9825)\nextern void note10_rtclock_intr(unsigned int);\n#endif')
    new['osfmk/arm/rtclock.c']+='''
#if defined(ARM64_BOARD_CONFIG_EXYNOS9825)
/* Keep per-CPU private bookkeeping in osfmk, not in pexpert. */
void
note10_rtclock_intr(unsigned int context)
{
    getCpuDatap()->cpu_decrementer=UINT32_MAX;
    rtclock_intr(context);
}
#endif
'''
    anchor='#if USE_APPLEARMSMP\n\tPE_handle_ext_interrupt();\n#else\n\t/* Run the registered interrupt handler. */'
    new['osfmk/arm64/sleh.c']=replace_one(old['osfmk/arm64/sleh.c'],anchor,
        '#if defined(ARM64_BOARD_CONFIG_EXYNOS9825)\n\tpe_note10_handle_irq();\n#elif USE_APPLEARMSMP\n\tPE_handle_ext_interrupt();\n#else\n\t/* Run the registered interrupt handler. */')
    anchor='void pe_init_fiq(void);'
    new['pexpert/pexpert/arm/protos.h']=replace_one(old['pexpert/pexpert/arm/protos.h'],anchor,anchor+'''

#if defined(ARM64_BOARD_CONFIG_EXYNOS9825)
/* Call only after nonsecure GICv2 initialization, with Device-mapped windows. */
void pe_note10_bind_irq(vm_offset_t, vm_size_t, vm_offset_t, vm_size_t, uint32_t);
void pe_note10_handle_irq(void);
#endif
''')
    bridge='pexpert/arm/pe_note10_irq.c'
    old[bridge]='';new[bridge]=(ROOT/'note10/xnu26/pe_note10_irq.c').read_text()
    paths=[bridge]
    for name in ('gicv2.c','gicv2.h','gicv2_mmio.c','gicv2_mmio.h'):
        name_out='pexpert/arm/note10/'+name
        old[name_out]='';body=(ROOT/'note10/platform'/name).read_text()
        new[name_out]='#if defined(ARM64_BOARD_CONFIG_EXYNOS9825)\n'+body+'\n#endif\n' if name.endswith('.c') else body
        if name.endswith('.c'):paths.append(name_out)
    new['pexpert/conf/files.arm64']=old['pexpert/conf/files.arm64']+'\n# Note10 components compile to empty units on other machine configurations.\n'+''.join(p+' standard\n' for p in paths)
    patch=''.join(''.join(difflib.unified_diff(old[n].splitlines(True),new[n].splitlines(True),
        fromfile='a/'+n if old[n] else '/dev/null',tofile='b/'+n)) for n in old)
    patch_path=ROOT/'note10/xnu26/patches/0003-exynos9825-timer-irq-bridge.patch'
    patch_path.write_text(patch,encoding='utf-8',newline='\n')
    private=ROOT/'note10/private/xnu26-irq';private.mkdir(exist_ok=True)
    stage=private/'stage'
    for name,body in old.items():
        p=stage/name;p.parent.mkdir(parents=True,exist_ok=True)
        if body:p.write_text(body,encoding='utf-8',newline='\n')
        elif p.exists():p.unlink()
    args=['git','-c','core.autocrlf=false','apply']
    subprocess.run([*args,'--check','--directory',source.relative_to(ROOT).as_posix(),patch_path.relative_to(ROOT).as_posix()],cwd=ROOT,check=True)
    command=[*args,'--directory',stage.relative_to(ROOT).as_posix()]
    subprocess.run([*command,patch_path.relative_to(ROOT).as_posix()],cwd=ROOT,check=True)
    for name,body in new.items():assert (stage/name).read_bytes()==body.encode(),name
    # A separate generated tree is used for compilation; stage is restored below.
    tree=private/'patched-inputs'
    for name,body in new.items():
        p=tree/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(body,encoding='utf-8',newline='\n')
    subprocess.run([*command,'--reverse',patch_path.relative_to(ROOT).as_posix()],cwd=ROOT,check=True)
    for name,body in old.items():
        assert ((stage/name).read_bytes()==body.encode()) if body else not (stage/name).exists()
        if name in PINS:assert hashlib.sha256((source/name).read_bytes()).hexdigest()==PINS[name]
    report={'source_sha256':PINS,'patch_sha256':hashlib.sha256(patch_path.read_bytes()).hexdigest(),
            'component_sha256':{n:hashlib.sha256(v.encode()).hexdigest() for n,v in new.items()},
            'apply_reverse_passed':True,'source_unchanged':True,'runtime_initialization_supplied':False}
    (private/'patch-result.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({'files':len(new),'apply_reverse_passed':True,'source_unchanged':True}))
if __name__=='__main__':main()
