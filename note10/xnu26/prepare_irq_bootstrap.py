"""Generate/check patch 0004 against the existing IRQ bridge series."""
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
from prepare_build_selection import ROOT, replace_one
from prepare_timer_selection import function

IDENTIFY='pexpert/arm/pe_identify_machine.c'
IDENTIFY_PIN='f7a7bbd1d9102b538abf548715f7bd5f86c1ac90ef6473fb4f09c2659cd8a74d'

def main():
    target=json.loads((ROOT/'note10/target.json').read_text())
    research=ROOT/target['research_directory']
    source=ROOT/json.loads((research/'xnu-reference.json').read_text())['source_directory']
    bridge=ROOT/'note10/private/xnu26-irq'
    manifest=json.loads((bridge/'patch-result.json').read_text())
    tree=bridge/'patched-inputs'
    old={}
    for name in ('pexpert/pexpert/arm/protos.h','pexpert/conf/files.arm64'):
        raw=(tree/name).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=manifest['component_sha256'][name]:raise ValueError('Bridge input mismatch')
        old[name]=raw.decode()
    raw=(source/IDENTIFY).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=IDENTIFY_PIN:raise ValueError('Pristine identify source mismatch')
    old[IDENTIFY]=raw.decode();new=dict(old)
    new[IDENTIFY]=replace_one(old[IDENTIFY],'#include <pexpert/arm64/board_config.h>',
        '#include <pexpert/arm64/board_config.h>\n#if defined(ARM64_BOARD_CONFIG_EXYNOS9825)\n#include <pexpert/arm/protos.h>\n#endif')
    anchor='''\t/* Set up mappings for interrupt controller and possibly timers (if they haven't been set up already) */
\tif (args != NULL) {
\t\tif (!pe_arm_map_interrupt_controller()) {
\t\t\treturn 0;
\t\t}
\t}'''
    new[IDENTIFY]=replace_one(new[IDENTIFY],anchor,'''#if defined(ARM64_BOARD_CONFIG_EXYNOS9825)
\t/* VM/topology are ready here on boot CPU; keep the common timebase setup below. */
\tif (args != NULL) pe_note10_init_irq();
#else
'''+anchor+'\n#endif')
    legacy='static uint32_t\n'+function(new[IDENTIFY],'pe_arm_map_interrupt_controller')
    new[IDENTIFY]=replace_one(new[IDENTIFY],legacy,
        '#if !defined(ARM64_BOARD_CONFIG_EXYNOS9825)\n'+legacy+'\n#endif /* !EXYNOS9825 */')
    new['pexpert/pexpert/arm/protos.h']=replace_one(old['pexpert/pexpert/arm/protos.h'],
        'void pe_note10_handle_irq(void);','void pe_note10_handle_irq(void);\nvoid pe_note10_init_irq(void);')
    name='pexpert/arm/pe_note10_bootstrap.c'
    old[name]='';new[name]=(ROOT/'note10/xnu26/pe_note10_bootstrap.c').read_text(encoding='utf-8')
    new['pexpert/conf/files.arm64']+=name+' standard\n'
    patch=''.join(''.join(difflib.unified_diff(old[n].splitlines(True),new[n].splitlines(True),
        fromfile='a/'+n if old[n] else '/dev/null',tofile='b/'+n)) for n in old)
    patch_file=ROOT/'note10/xnu26/patches/0004-exynos9825-irq-bootstrap.patch'
    patch_file.write_text(patch,encoding='utf-8',newline='\n')
    private=ROOT/'note10/private/xnu26-bootstrap';private.mkdir(exist_ok=True)
    stage=private/'stage'
    for name,body in old.items():
        p=stage/name;p.parent.mkdir(parents=True,exist_ok=True)
        if body:p.write_text(body,encoding='utf-8',newline='\n')
        elif p.exists():p.unlink()
    args=['git','-c','core.autocrlf=false','apply','--directory',stage.relative_to(ROOT).as_posix()]
    subprocess.run([*args,'--check',patch_file.relative_to(ROOT).as_posix()],cwd=ROOT,check=True)
    subprocess.run([*args,patch_file.relative_to(ROOT).as_posix()],cwd=ROOT,check=True)
    outputs=private/'patched-inputs'
    for name,body in new.items():
        assert (stage/name).read_bytes()==body.encode()
        p=outputs/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(body,encoding='utf-8',newline='\n')
    subprocess.run([*args,'--reverse',patch_file.relative_to(ROOT).as_posix()],cwd=ROOT,check=True)
    for name,body in old.items():assert (stage/name).read_bytes()==body.encode() if body else not (stage/name).exists()
    assert hashlib.sha256((source/IDENTIFY).read_bytes()).hexdigest()==IDENTIFY_PIN
    report={'identify_source_sha256':IDENTIFY_PIN,'preceding_bridge_patch_sha256':manifest['patch_sha256'],
        'patch_sha256':hashlib.sha256(patch_file.read_bytes()).hexdigest(),
        'files':{n:hashlib.sha256(v.encode()).hexdigest() for n,v in new.items()},
        'apply_reverse_passed':True,'source_unchanged':True,'cold_gic_initialization':False}
    (private/'patch-result.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({'files':len(new),'apply_reverse_passed':True,'source_unchanged':True}))
if __name__=='__main__':main()
