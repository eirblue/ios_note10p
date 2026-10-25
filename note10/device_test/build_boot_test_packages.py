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


def updater(*, mode, bootloader, partitions, payload_sha, current_boot_sha):
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


def build(backup,prototype,output):
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
    padded=raw+bytes(len(parts['boot'])-len(raw))
    output.mkdir(parents=True,exist_ok=False)
    result={'scope':'Manual BOOT-only Linux test and paired Android BOOT rollback; not full device backup',
            'builder_device_operations':[],'device_boot_tested':False,'deployment_ready':False,'packages':[]}
    for mode,payload in (('diagnostic',padded),('rollback',parts['boot'])):
        digest=hashlib.sha256(payload).hexdigest()
        script=updater(mode=mode,bootloader=manifest['bootloader'],partitions=manifest['partitions'],
                       payload_sha=digest,current_boot_sha=original)
        metadata={'mode':mode,'writes':['boot'],'payload_sha256':digest,'payload_size':len(payload),
                  'updater_sha256':hashlib.sha256(script).hexdigest(),
                  'preserves_on_disk':['recovery','dtb','dtbo','vbmeta'],'automatic_reboot':False,
                  'recovery_reentry_guaranteed':False,'scope':'Human-triggered TWRP install only; not executed by builder'}
        target=output/('note10-phase2-'+mode+'.zip')
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
    args=parser.parse_args();report=build(args.backup,args.prototype,args.output)
    print(json.dumps({'packages':len(report['packages']),'builder_device_operations':[],'deployment_ready':False}))
