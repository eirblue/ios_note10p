"""Apply the opt-in paired irqsave token fix to the pinned v45 composition."""
import hashlib, re, shutil
from pathlib import Path

TARGET='drivers/soc/samsung/debug/exynos-ehld.c'
KCONFIG='kernel/power/Kconfig'
OPTION='CONFIG_NOTE10_EHLD_IRQSAVE_AUDIT'
BLOCK=b'\nconfig NOTE10_EHLD_IRQSAVE_AUDIT\n\tbool "EHLD paired irqsave token audit"\n\tdepends on NOTE10_EHLD_LOCK_AUDIT\n\tdefault n\n'

def sha(data): return hashlib.sha256(data).hexdigest()
def _function(data):
    signature=b'void exynos_ehld_event_raw_update_allcpu(void)'
    if data.count(signature)!=1: raise ValueError('EHLD function signature must be unique')
    start=data.find(signature)
    brace=data.find(b'{',start); depth=0
    for i in range(brace,len(data)):
        if data[i:i+1]==b'{': depth+=1
        elif data[i:i+1]==b'}':
            depth-=1
            if depth==0:return start,i+1,data[start:i+1]
    raise ValueError('unterminated EHLD function')
def transform_function(raw):
    start,end,fn=_function(raw)
    replacements=((b'unsigned long flags, count;',b'unsigned long main_flags, ctrl_flags, count;'),
      (b'raw_spin_lock_irqsave(&ehld_main.lock, flags);',b'raw_spin_lock_irqsave(&ehld_main.lock, main_flags);'),
      (b'raw_spin_lock_irqsave(&ctrl->lock, flags);',b'raw_spin_lock_irqsave(&ctrl->lock, ctrl_flags);'),
      (b'raw_spin_unlock_irqrestore(&ctrl->lock, flags);',b'raw_spin_unlock_irqrestore(&ctrl->lock, ctrl_flags);'),
      (b'raw_spin_unlock_irqrestore(&ehld_main.lock, flags);',b'raw_spin_unlock_irqrestore(&ehld_main.lock, main_flags);'))
    for old,new in replacements:
        if fn.count(old)!=1: raise ValueError('unexpected exact patch anchor: '+old.decode())
        fn=fn.replace(old,new,1)
    if b', flags);' in fn: raise ValueError('unpaired irqsave token remains in target function')
    return raw[:start]+fn+raw[end:]
def prepare(source, enabled, baseline_map):
    if enabled is not True: raise ValueError('v46 preparation requires explicit opt-in')
    source=Path(source)
    if not isinstance(baseline_map,dict) or len(baseline_map)!=78 or TARGET not in baseline_map or KCONFIG not in baseline_map:raise ValueError('exact v45 78-source snapshot map required')
    for name,digest in baseline_map.items():
        p=Path(name)
        if p.is_absolute() or p.as_posix()!=name or '..' in p.parts or not re.fullmatch(r'[0-9a-f]{64}',digest):raise ValueError('invalid v45 snapshot map entry')
    before_all={}
    for n in baseline_map:
        p=source/n
        if p.is_symlink() or not p.is_file():raise ValueError('v45 source missing or unsafe: '+n)
        before_all[n]=sha(p.read_bytes())
    if before_all!=baseline_map:raise ValueError('v45 source baseline differs')
    before={n:before_all[n] for n in (TARGET,KCONFIG)}
    target=source/TARGET; target_data=transform_function(target.read_bytes())
    k=source/KCONFIG; data=k.read_bytes()
    if data.count(b'config NOTE10_EHLD_IRQSAVE_AUDIT') or BLOCK.strip() in data:raise ValueError('irqsave option already exists')
    target.write_bytes(target_data)
    k.write_bytes(data+BLOCK)
    after={n:sha((source/n).read_bytes()) for n in (TARGET,KCONFIG)}
    return {'ehld_irqsave_audit':True,'ehld_irqsave_audit_version':1,'ehld_irqsave_baseline_sha256':before,'ehld_irqsave_prepared_sha256':after}
def snapshot(source,output,baseline_map):
    source,output=Path(source),Path(output)
    if not isinstance(baseline_map,dict) or len(baseline_map)!=78 or TARGET not in baseline_map or KCONFIG not in baseline_map:raise ValueError('exact v45 78-source map required')
    if output.exists():raise ValueError('irqsave snapshot already exists')
    names=set(baseline_map)
    for n in sorted(names):
        p=source/n
        if p.is_symlink() or not p.is_file():raise ValueError('invalid source '+n)
        q=output/n;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
    result={n:sha((output/n).read_bytes()) for n in sorted(names)}
    changed={n for n in names if result[n]!=baseline_map[n]}
    if changed!={TARGET,KCONFIG}:raise ValueError('snapshot must change exactly target and Kconfig')
    return result

