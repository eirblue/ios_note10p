"""Build a BOOT-only manual test ZIP and matching Android boot rollback ZIP.

PC packaging only. The generated updater writes BOOT when a human installs it
in TWRP; this builder never invokes ADB, flashes, installs, or reboots a phone.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile
from prepare_linux_boot import ROOT, read_verified_backup


def updater(*, mode, bootloader, partitions, payload_sha, current_boot_sha,reservation=False,window_access=False,xnu_stage=False,cpu_cache=False,pm_timer=False,auto_return=False):
    if window_access and not reservation:raise ValueError('RAM access requires the reservation diagnostic')
    if xnu_stage and not window_access:raise ValueError('XNU staging requires the RAM access diagnostic')
    if cpu_cache and not xnu_stage:raise ValueError('CPU/cache roundtrip requires XNU staging')
    if auto_return and not pm_timer:raise ValueError('Auto return requires PM/timer')
    if pm_timer and not cpu_cache:raise ValueError('PM/timer requires CPU/cache batch')
    if mode not in ('diagnostic','rollback') or not re.fullmatch(r'N976N[A-Z0-9]+',bootloader):
        raise ValueError('Unexpected package mode or bootloader')
    if not re.fullmatch(r'[0-9a-f]{64}',payload_sha) or not re.fullmatch(r'[0-9a-f]{64}',current_boot_sha):
        raise ValueError('Invalid expected digest')
    if {p['partition'] for p in partitions}!={'boot','recovery','dtb','dtbo','vbmeta'} or len(partitions)!=5:
        raise ValueError('Unexpected partition contract')
    if len({p['block_node'] for p in partitions})!=5:raise ValueError('Duplicate partition nodes')
    for item in partitions:
        if not re.fullmatch(r'/dev/block/sd[a-z][0-9]+',item['block_node']) or not re.fullmatch(r'[0-9a-f]{64}',item['sha256']):
            raise ValueError('Unsafe partition contract')
        if type(item['size']) is not int or not 0<item['size']<=128*1024*1024:
            raise ValueError('Invalid partition size')
    boot=next(p for p in partitions if p['partition']=='boot')
    script='''#!/sbin/sh
set -u
PATH=/sbin:/system/bin:/system/xbin:/vendor/bin:$PATH
export PATH
FD=${2:-}
ZIP=${3:-}
case "$FD" in ''|0|1|2|*[!0-9]*) echo "Invalid updater UI descriptor" >&2; exit 1 ;; esac
[ -w "/proc/self/fd/$FD" ] || { echo "Updater UI unavailable" >&2; exit 1; }
ui() { printf 'ui_print %s\\nui_print\\n' "$*" > "/proc/self/fd/$FD" || exit 1; }
abort() { ui "ERROR: $*"; exit 1; }
sum() { sha256sum "$1" | awk '{print $1}'; }
[ -n "$ZIP" ] && [ -f "$ZIP" ] || abort "Package file unavailable"
[ "$(id -u)" = 0 ] || abort "Root TWRP required"
[ "$(uname -m)" = aarch64 ] || abort "AArch64 required"
[ -n "$(getprop ro.twrp.version)" ] || abort "TWRP required"
case "$(getprop ro.product.device)" in d2x|d2xks) ;; *) abort "Expected d2x" ;; esac
'''
    script+='[ "$(getprop ro.bootloader)" = "'+bootloader+'" ] || abort "Bootloader differs from paired backup"\n'
    script+='ui "'+('Temporary Linux CPU diagnostic; not iOS/XNU.' if mode=='diagnostic' else 'Restore the paired Android BOOT backup.')+'"\n'
    script+='ui "Writes BOOT only. No automatic reboot."\n'
    if mode=='diagnostic' and reservation:
        script+='ui "RAM reservation test with built-in idle init: no TWRP UI or ADB after System boot."\n'
    if mode=='diagnostic' and window_access:
        script+='ui "Writes patterns to 256MiB of this boot\'s checked reserved RAM, reads back and clears it. No XNU branch."\n'
    if mode=='diagnostic' and xnu_stage:
        script+='ui "Copies an experimental XNU memory image into this boot\'s reserved RAM and verifies SHA256 readback. It does not execute XNU."\n'
    if mode=='diagnostic' and cpu_cache:
        script+='ui "Temporarily offlines secondary CPUs, maintains payload caches, restores CPUs and checks per-CPU reads. No DMA/MMU shutdown or XNU branch."\n'
    if mode=='diagnostic' and pm_timer:
        script+='ui "Tests device-driver suspend/resume and timer selector clear/restore. Low-level sleep is blocked. Drivers can hang during this test."\n'
    if mode=='diagnostic' and auto_return:
        script+='ui "Opt-in kernel requests recovery after 90 seconds. First automatic roundtrip is unverified."\n'
    for item in partitions:
        name=item['partition'];node=item['block_node']
        script+='[ "$(readlink -f /dev/block/by-name/'+name+')" = "'+node+'" ] || abort "Unexpected '+name+' block node"\n'
        script+='[ "$(blockdev --getsize64 '+node+')" = "'+str(item['size'])+'" ] || abort "Unexpected '+name+' size"\n'
        # A rollback must also work after a partial/failed BOOT write. Bind it
        # to the original non-BOOT components, not to a successful new BOOT.
        if name!='boot' or mode=='diagnostic':
            expected=current_boot_sha if name=='boot' else item['sha256']
            script+='[ "$(sum '+node+')" = "'+expected+'" ] || abort "Unexpected current '+name+' contents"\n'
    script+='''[ ! -L /tmp ] || abort "Unexpected tmp symlink"
awk '($2 == "/" || $2 == "/tmp") && length($2) > best {best=length($2); kind=$3}
     END {exit !(kind == "tmpfs" || kind == "ramfs" || kind == "rootfs")}' /proc/mounts || abort "RAM tmp required"
WORK=/tmp/note10-boot-$$
[ ! -e "$WORK" ] && [ ! -L "$WORK" ] || abort "Stale staging directory"
umask 077
mkdir "$WORK" || abort "Cannot create RAM staging directory"
unzip -p "$ZIP" boot.img > "$WORK/boot.img" || abort "Cannot extract BOOT payload"
'''
    script+='[ "$(sum "$WORK/boot.img")" = "'+payload_sha+'" ] || abort "Payload hash mismatch"\n'
    script+='dd if="$WORK/boot.img" of="'+boot['block_node']+'" bs=4096 2> "$WORK/write.log" || abort "BOOT write failed; stay in recovery"\n'
    script+='sync || abort "Sync failed; stay in recovery"\n'
    script+='[ "$(sum '+boot['block_node']+')" = "'+payload_sha+'" ] || abort "BOOT verification failed; stay in recovery"\n'
    script+='ui "BOOT written and verified. Recovery/DTB/DTBO/vbmeta were not written."\nui "Complete. Reboot only when ready for the manual test."\nexit 0\n'
    return script.encode('utf-8')


def build(backup,prototype,output,current_packages=None):
    if not output.resolve().is_relative_to((ROOT/'note10/private').resolve()):raise ValueError('Private output required')
    if output.exists():raise ValueError('Package directory already exists')
    parts=read_verified_backup(backup)
    manifest=json.loads((backup/'backup-manifest.json').read_text())
    metadata=json.loads(prototype.with_suffix('.json').read_text())
    raw=prototype.read_bytes()
    original=hashlib.sha256(parts['boot']).hexdigest()
    if metadata.get('prototype_created') is not True or metadata.get('kind')!='temporary Linux diagnostic boot; not XNU/iOS':
        raise ValueError('Verified diagnostic prototype required')
    if hashlib.sha256(raw).hexdigest()!=metadata['sha256'] or len(raw)!=metadata['size']:
        raise ValueError('Prototype differs from metadata')
    if metadata.get('backup_manifest_sha256')!=hashlib.sha256((backup/'backup-manifest.json').read_bytes()).hexdigest():
        raise ValueError('Prototype and backup are not paired')
    if metadata.get('original_boot_sha256')!=original or metadata.get('existing_recovery_partition_sha256')!=hashlib.sha256(parts['recovery']).hexdigest():
        raise ValueError('Prototype baseline differs')
    if not 0<len(raw)<=len(parts['boot']):raise ValueError('Prototype exceeds BOOT partition')
    current_boot=original
    if current_packages is not None:
        from stage_phase2 import verify_packages
        previous=verify_packages(current_packages)
        previous_result=json.loads((current_packages/'package-result.json').read_text())
        if previous_result.get('backup_manifest_sha256')!=metadata['backup_manifest_sha256']:
            raise ValueError('Previous diagnostic uses a different backup')
        candidates=[p for p in previous if p['mode']=='diagnostic']
        if len(candidates)!=1 or candidates[0]['payload_size']!=len(parts['boot']):
            raise ValueError('Previous diagnostic partition size differs')
        current_boot=candidates[0]['payload_sha256']
    reservation=metadata.get('early_xnu_reservation') is True
    window_access=metadata.get('window_access_diagnostic') is True
    xnu_stage=metadata.get('xnu_payload_stage_diagnostic') is True
    cpu_cache=metadata.get('cpu_cache_roundtrip_diagnostic') is True
    pm_timer=metadata.get('pm_timer_diagnostic') is True
    pm_quiesce=metadata.get('pm_quiesce_diagnostic') is True
    gic_roundtrip=metadata.get('gic_roundtrip_diagnostic') is True
    dma_pm_audit=metadata.get('dma_pm_audit_diagnostic') is True
    ufs_pm_audit=metadata.get('ufs_pm_audit_diagnostic') is True
    if ufs_pm_audit and (not dma_pm_audit or metadata.get('ufs_pm_audit_evidence_version')!=2):
        raise ValueError('Incomplete UFS PM audit package contract')
    iommu_pm_audit=metadata.get('iommu_pm_audit_diagnostic') is True
    if iommu_pm_audit and (not ufs_pm_audit or metadata.get('iommu_pm_audit_evidence_version')!=2):
        raise ValueError('Incomplete IOMMU PM audit package contract')
    abox_pm_audit=metadata.get('abox_pm_audit_diagnostic') is True
    if abox_pm_audit and (not iommu_pm_audit or metadata.get('abox_pm_audit_evidence_version')!=5):
        raise ValueError('Incomplete ABOX PM audit package contract')
    if dma_pm_audit and (not gic_roundtrip or metadata.get('dma_pm_audit_evidence_version')!=1):
        raise ValueError('Incomplete DMA PM audit package contract')
    if gic_roundtrip and (not pm_timer or metadata.get('gic_roundtrip_evidence_version')!=1):
        raise ValueError('Incomplete GIC diagnostic package contract')
    if pm_quiesce and (not pm_timer or metadata.get('pm_quiesce_evidence_version')!=1):
        raise ValueError('Incomplete PM quiesce package contract')
    auto_return=metadata.get('auto_return_diagnostic') is True
    if gic_roundtrip and not auto_return:raise ValueError('GIC roundtrip requires automatic recovery')
    screen_log=metadata.get('screen_log_diagnostic') is True
    if screen_log and not auto_return:raise ValueError('Screen log requires auto return')
    cycle=metadata.get('auto_cycle_token')
    if auto_return and (not pm_timer or not re.fullmatch(r'[0-9a-f]{32}',cycle or '')):raise ValueError('Incomplete auto-return cycle')
    if pm_timer and not cpu_cache:raise ValueError('PM/timer requires CPU/cache batch')
    if cpu_cache and not xnu_stage:raise ValueError('CPU/cache roundtrip needs XNU staging')
    xnu_sha=metadata.get('xnu_payload_sha256') if xnu_stage else None
    xnu_size=metadata.get('xnu_payload_size') if xnu_stage else None
    if xnu_stage and (not window_access or not re.fullmatch(r'[0-9a-f]{64}',metadata.get('xnu_payload_sha256','')) or
                      type(metadata.get('xnu_payload_size')) is not int):
        raise ValueError('XNU payload staging metadata is incomplete')
    if window_access and not reservation:raise ValueError('RAM access requires reserved RAM and idle init')
    if reservation and metadata.get('builtin_idle_init') is not True:raise ValueError('Reservation test needs built-in idle init')
    padded=raw+bytes(len(parts['boot'])-len(raw))
    output.mkdir(parents=True,exist_ok=False)
    result={'scope':'Manual BOOT-only Linux test and paired Android BOOT rollback; not full device backup',
            'manual_test_packages_created':True,'prototype_sha256':metadata['sha256'],
            'kernel_image_sha256':metadata['kernel_build_sha256'],
            'backup_manifest_sha256':metadata['backup_manifest_sha256'],
            'expected_current_boot_sha256':current_boot,
            'window_access_diagnostic':window_access,
            'xnu_payload_stage_diagnostic':xnu_stage,
            'cpu_cache_roundtrip_diagnostic':cpu_cache,
            'screen_log_diagnostic':screen_log,
            'pm_timer_diagnostic':pm_timer,'auto_return_diagnostic':auto_return,'auto_cycle_token':cycle,
            'pm_quiesce_diagnostic':pm_quiesce,'pm_quiesce_evidence_version':1 if pm_quiesce else None,
            'gic_roundtrip_diagnostic':gic_roundtrip,'gic_roundtrip_evidence_version':1 if gic_roundtrip else None,
            'dma_pm_audit_diagnostic':dma_pm_audit,'dma_pm_audit_evidence_version':1 if dma_pm_audit else None,
            'ufs_pm_audit_diagnostic':ufs_pm_audit,'ufs_pm_audit_evidence_version':2 if ufs_pm_audit else None,
            'iommu_pm_audit_diagnostic':iommu_pm_audit,'iommu_pm_audit_evidence_version':2 if iommu_pm_audit else None,
            'abox_pm_audit_diagnostic':abox_pm_audit,'abox_pm_audit_evidence_version':5 if abox_pm_audit else None,
            'xnu_payload_sha256':metadata.get('xnu_payload_sha256') if xnu_stage else None,
            'xnu_payload_size':metadata.get('xnu_payload_size') if xnu_stage else None,
            'builder_device_operations':[],'device_boot_tested':False,'deployment_ready':False,'packages':[]}
    for mode,payload in (('diagnostic',padded),('rollback',parts['boot'])):
        digest=hashlib.sha256(payload).hexdigest()
        script=updater(mode=mode,bootloader=manifest['bootloader'],partitions=manifest['partitions'],
                       payload_sha=digest,current_boot_sha=current_boot,reservation=reservation,
                       window_access=window_access,xnu_stage=xnu_stage and mode=='diagnostic',
                       cpu_cache=cpu_cache and mode=='diagnostic',pm_timer=pm_timer and mode=='diagnostic',auto_return=auto_return and mode=='diagnostic')
        metadata={'mode':mode,'writes':['boot'],'payload_sha256':digest,'payload_size':len(payload),
                  'updater_sha256':hashlib.sha256(script).hexdigest(),
                  'preserves_on_disk':['recovery','dtb','dtbo','vbmeta'],'automatic_reboot':False,
                  'recovery_reentry_guaranteed':False,'scope':'Human-triggered TWRP install only; not executed by builder'}
        metadata['test_purpose']=('xnu-payload-stage' if xnu_stage and mode=='diagnostic' else
                                  ('ram-window-access' if window_access else ('ram-reservation' if reservation else 'cpu-caps')))
        metadata['window_access_diagnostic']=window_access and mode=='diagnostic'
        metadata['xnu_payload_stage_diagnostic']=xnu_stage and mode=='diagnostic'
        metadata['cpu_cache_roundtrip_diagnostic']=cpu_cache and mode=='diagnostic'
        metadata['pm_timer_diagnostic']=pm_timer and mode=='diagnostic'
        metadata['pm_quiesce_diagnostic']=pm_quiesce and mode=='diagnostic'
        metadata['pm_quiesce_evidence_version']=1 if pm_quiesce and mode=='diagnostic' else None
        metadata['gic_roundtrip_diagnostic']=gic_roundtrip and mode=='diagnostic'
        metadata['gic_roundtrip_evidence_version']=1 if gic_roundtrip and mode=='diagnostic' else None
        metadata['dma_pm_audit_diagnostic']=dma_pm_audit and mode=='diagnostic'
        metadata['dma_pm_audit_evidence_version']=1 if dma_pm_audit and mode=='diagnostic' else None
        metadata['ufs_pm_audit_diagnostic']=ufs_pm_audit and mode=='diagnostic'
        metadata['ufs_pm_audit_evidence_version']=2 if ufs_pm_audit and mode=='diagnostic' else None
        metadata['iommu_pm_audit_diagnostic']=iommu_pm_audit and mode=='diagnostic'
        metadata['iommu_pm_audit_evidence_version']=2 if iommu_pm_audit and mode=='diagnostic' else None
        metadata['abox_pm_audit_diagnostic']=abox_pm_audit and mode=='diagnostic'
        metadata['abox_pm_audit_evidence_version']=5 if abox_pm_audit and mode=='diagnostic' else None
        metadata['screen_log_diagnostic']=screen_log and mode=='diagnostic'
        metadata['auto_return_diagnostic']=auto_return and mode=='diagnostic'
        metadata['auto_cycle_token']=cycle if auto_return and mode=='diagnostic' else None
        metadata['xnu_payload_sha256']=xnu_sha if xnu_stage and mode=='diagnostic' else None
        metadata['xnu_payload_size']=xnu_size if xnu_stage and mode=='diagnostic' else None
        target=output/(('note10-reservation-' if reservation else 'note10-phase2-')+mode+'.zip')
        files={'META-INF/com/google/android/update-binary':script,
               'META-INF/com/google/android/updater-script':b'# BOOT-only manual test/rollback\n',
               'boot.img':payload,'manifest.json':json.dumps(metadata,indent=2).encode()}
        with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
            for name,data in files.items():
                item=zipfile.ZipInfo(name,(2026,1,1,0,0,0));item.create_system=3
                item.external_attr=((0o100755 if name.endswith('update-binary') else 0o100644)<<16)
                item.compress_type=zipfile.ZIP_DEFLATED
                archive.writestr(item,data)
        with zipfile.ZipFile(target) as archive:
            if archive.testzip() is not None or hashlib.sha256(archive.read('boot.img')).hexdigest()!=digest:
                raise ValueError('Package integrity check failed')
        result['packages'].append({'file':target.name,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),**metadata})
    (output/'package-result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('backup','prototype','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--current-packages',type=Path,help='Verified prior diagnostic pair currently installed in BOOT')
    args=parser.parse_args();report=build(args.backup,args.prototype,args.output,args.current_packages)
    print(json.dumps({'packages':len(report['packages']),'builder_device_operations':[],'deployment_ready':False}))
