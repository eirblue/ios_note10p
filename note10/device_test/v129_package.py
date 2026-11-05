"""Dedicated129 proof package; no generic observer/KAT/auto-return admission."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
import uuid
import zipfile
from v129_inputs import ROOT,INPUT_COMMIT,INPUT_PINS

COMMIT='55f042627bb7030c93550faafa117674d32b21d1'
ARCHIVE_SHA='46d6a563af04e0c2ed9c96c2a1af8cab2344b458c9554b09098e6a9e7219ae4c'
DEFCONFIG='exynos9820-d2x_defconfig'
MKBOOTIMG_SHA='2a8d05d34110f66c463668f43fc812ce2e46e66459c347eaadb080271df69aa8'
TWRP_SHA='e8de29b03fc3eab95f51663b08b2f848e168854a15f8a598a1f80d216f4794df'
SCHEMA='note10-v129-proof-package-v1'
PLAN_SCHEMA='note10-v129-proof-cycle-v1'
DISABLED=b'!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!'
PARTITIONS={'boot','recovery','dtb','dtbo','vbmeta'}


def digest(raw):return hashlib.sha256(raw).hexdigest()
def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def save(path,row):
    with Path(path).open('x',encoding='utf-8',newline='\n') as stream:stream.write(json.dumps(row,indent=2)+'\n')
def hexid(value,n):
    if not isinstance(value,str) or re.fullmatch('[0-9a-f]{'+str(n)+'}',value) is None:
        raise ValueError('exact lowercase hexadecimal identity required')
    return value
def private(path):
    path=Path(path).absolute()
    if path!=path.resolve() or not path.is_relative_to(ROOT/'note10/private') or path==ROOT/'note10/private':
        raise ValueError('canonical private workspace path required')
    return path
def verify_pins(row):
    if not isinstance(row,dict) or not row:raise ValueError('source pins required')
    for name,pin in row.items():
        target=ROOT/name
        if not target.resolve().is_relative_to(ROOT) or target.is_symlink() or sha(target)!=hexid(pin,64):
            raise ValueError('producer source changed: '+name)


def header(raw):
    if len(raw)<1660 or raw[:8]!=b'ANDROID!':raise ValueError('Android BOOT header required')
    keys=('kernel_size','kernel_addr','ramdisk_size','ramdisk_addr','second_size','second_addr','tags_addr','page_size','header_version','encoded_os')
    row=dict(zip(keys,struct.unpack_from('<10I',raw,8)));page=row['page_size']
    if row['header_version']!=1 or page not in (2048,4096,8192,16384):raise ValueError('observed v1 BOOT layout required')
    z=lambda s:s.split(b'\0',1)[0].decode('ascii')
    row.update(name=z(raw[48:64]),cmdline=z(raw[64:576])+z(raw[608:1632]),kernel_offset=page)
    row['ramdisk_offset']=page+(row['kernel_size']+page-1)//page*page
    row['payload_end']=row['ramdisk_offset']+(row['ramdisk_size']+page-1)//page*page
    row['recovery_dtbo_size']=struct.unpack_from('<I',raw,1632)[0]
    if row['second_size'] or row['recovery_dtbo_size'] or row['payload_end']>len(raw):raise ValueError('unexpected BOOT payload layout')
    return row


def backup(directory):
    directory=private(directory);row=read(directory/'backup-manifest.json')
    if row.get('complete') is not True or row.get('partition_writes') is not False or row.get('bootloader')!='N976NKSU2HWH5':
        raise ValueError('paired verified N976N backup required')
    parts={};nodes=set()
    for item in row['partitions']:
        name=item['partition'];node=item['block_node']
        if name not in PARTITIONS or name in parts or item['file']!=name+'.img' or node in nodes or re.fullmatch('/dev/block/sd[a-z][0-9]+',node) is None:
            raise ValueError('five unique source-bound partition rows required')
        raw=(directory/item['file']).read_bytes()
        if (directory/item['file']).is_symlink() or type(item['size']) is not int or not 0<item['size']<=128*1024*1024 or len(raw)!=item['size'] or digest(raw)!=hexid(item['sha256'],64) or item.get('remote_hash_before_and_after_match') is not True:
            raise ValueError('backup bytes differ')
        parts[name]=raw;nodes.add(node)
    if set(parts)!=PARTITIONS:raise ValueError('all five partitions required')
    return row,parts


def enable(raw,cycle):
    hexid(cycle,32)
    if raw.count(DISABLED)!=1 or cycle.encode() in raw:raise ValueError('unique disabled slot required')
    return raw.replace(DISABLED,cycle.encode(),1)


def validate_build(folder):
    folder=private(folder);row=read(folder/'result.json');raw=(folder/'Image').read_bytes()
    if (row.get('schema')!='note10-v129-kexec-host-build-v1' or row.get('version')!='v129' or row.get('passed') is not True or
        row.get('immutable_input_commit')!=INPUT_COMMIT or row.get('immutable_input_sha256')!=INPUT_PINS or
        row.get('execution_slot_enabled') is not False or row.get('skip_external_only_policy') is not True or
        row.get('common_PID1_RESTART2_recovery') is not True or row.get('early_recovery_marker_before_shutdown') is not True or
        row.get('marker_failure_aborts_shutdown') is not True or row.get('XNU_execution_allowed') is not False):
        raise ValueError('fresh source129 disabled proof build required')
    verify_pins(row['source_sha256']);hexid(row['build_evidence_id'],32)
    for file,key in [('Image','Image_sha256'),('actual-effective.config','effective_config_sha256'),('minimal-init.elf','PID1_sha256'),('park.bin','park_sha256'),('initramfs.cpio','initramfs_cpio_sha256')]:
        if sha(folder/file)!=hexid(row[key],64):raise ValueError('build bytes differ: '+file)
    config=(folder/'actual-effective.config').read_text().splitlines()
    required={'CONFIG_NOTE10_LEGACY_KEXEC_RECOVERY_PROOF=y','CONFIG_INITRAMFS_FORCE=y','CONFIG_CMDLINE_EXTEND=y','CONFIG_CMDLINE="rdinit=/init"','CONFIG_KEXEC=y','CONFIG_KEXEC_CORE=y','CONFIG_ARM64_4K_PAGES=y'}
    cpio=(folder/'initramfs.cpio').read_bytes()
    if not required.issubset(config) or raw.count(cpio)!=1 or raw.count(DISABLED)!=1 or raw[56:60]!=b'ARM\x64':
        raise ValueError('actual config/builtin/disabled Image binding differs')
    retained=row['retained_NEW_PASS_operator_binding']
    if retained.get('schema')!='note10-v129-retained-new-test-pass-v1' or retained.get('passed') is not True:
        raise ValueError('retained NEW129 PASS required')
    return row,raw


def zip_package(path,raw,metadata):
    # This is an inert transport ZIP. Only the reviewed dedicated cycle writes it.
    with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_STORED) as bundle:
        bundle.writestr('boot.img',raw);bundle.writestr('proof.json',json.dumps(metadata,sort_keys=True)+'\n')


def prepare(build,backup_dir,twrp,mkbootimg,output,current_boot_sha):
    output=private(output);build=private(build);backup_dir=private(backup_dir)
    if output.exists():raise ValueError('fresh proof package output required')
    current_boot_sha=hexid(current_boot_sha,64);row,image=validate_build(build)
    manifest,parts=backup(backup_dir);official=Path(twrp).read_bytes()
    require_paired_BOOT(current_boot_sha,parts['boot'])
    if digest(official)!=TWRP_SHA or not parts['recovery'].startswith(official) or sha(mkbootimg)!=MKBOOTIMG_SHA:
        raise ValueError('pinned recovery/mkbootimg required')
    stock=header(parts['boot']);reference=header(official)
    if stock['page_size']!=reference['page_size'] or any(stock[k]!=reference[k] for k in ('kernel_addr','tags_addr')):
        raise ValueError('paired BOOT/recovery load fields differ')
    if struct.unpack_from('<Q',image,8)[0]!=struct.unpack_from('<Q',official,reference['kernel_offset']+8)[0]:
        raise ValueError('Linux text offset differs from known recovery')
    if parts['vbmeta'][:4]!=b'AVB0' or not struct.unpack_from('>I',parts['vbmeta'],120)[0]&2:
        raise ValueError('observed verification-disabled vbmeta required')
    cycle=uuid.uuid4().hex;enabled=enable(image,cycle)
    if len(reference['cmdline'].encode())>1535 or 'n10.cycle=' in reference['cmdline']:
        raise ValueError('source-bound recovery commandline too long or already scoped')
    output.mkdir();kernel=output/'enabled-Image';kernel.write_bytes(enabled)
    encoded=stock['encoded_os'];os_version='.'.join(str((encoded>>n)&127) for n in (25,18,11))
    month=f'{2000+((encoded>>4)&127):04d}-{encoded&15:02d}'
    partial=output/'packed-boot.img'
    command=[sys.executable,'-B',str(Path(mkbootimg).resolve()),'--header_version','1','--kernel',str(kernel),'--base','0',
             '--kernel_offset',hex(stock['kernel_addr']),'--ramdisk_offset',hex(stock['ramdisk_addr']),
             '--tags_offset',hex(stock['tags_addr']),'--pagesize',str(stock['page_size']),'--board',stock['name'],
             '--cmdline',reference['cmdline'],'--os_version',os_version,'--os_patch_level',month,'--output',str(partial)]
    subprocess.run(command,check=True,capture_output=True,timeout=60,cwd=ROOT)
    packed=partial.read_bytes();observed=header(packed)
    if (observed['ramdisk_size'] or observed['cmdline']!=reference['cmdline'] or
        packed[observed['kernel_offset']:observed['kernel_offset']+observed['kernel_size']]!=enabled or
        any(observed[k]!=stock[k] for k in ('kernel_addr','tags_addr','page_size','name','encoded_os'))):
        raise ValueError('actual fresh BOOT roundtrip differs')
    trailer=b'SEANDROIDENFORCE'
    if parts['boot'][stock['payload_end']:stock['payload_end']+len(trailer)]!=trailer:
        raise ValueError('observed Samsung BOOT trailer differs')
    if len(packed)+len(trailer)>len(parts['boot']):raise ValueError('new BOOT exceeds partition')
    diagnostic=(packed+trailer).ljust(len(parts['boot']),b'\0');(output/'boot.img').write_bytes(diagnostic)
    package=dict(schema=SCHEMA,version='v129',cycle=cycle,build_evidence_id=row['build_evidence_id'],
        input_Image_sha256=digest(image),enabled_Image_sha256=digest(enabled),diagnostic_BOOT_sha256=digest(diagnostic),
        rollback_BOOT_sha256=digest(parts['boot']),expected_current_BOOT_sha256=current_boot_sha,
        build=str(build),build_result_sha256=sha(build/'result.json'),backup=str(backup_dir),
        backup_manifest_sha256=sha(backup_dir/'backup-manifest.json'),partitions=manifest['partitions'],bootloader=manifest['bootloader'],
        source_sha256=row['source_sha256'],immutable_input_commit=INPUT_COMMIT,immutable_input_sha256=INPUT_PINS,
        cmdline_source='pinned official recovery v1 BOOT header; kernel CMDLINE_EXTEND retains incoming chosen/bootargs',
        BOOT_cmdline=reference['cmdline'],bare_skip_builtin_preserved=True,external_ramdisk_included=False,
        XNU_execution_allowed=False,physical_gate_open=False)
    zip_package(output/'proof.zip',diagnostic,dict(schema=SCHEMA,cycle=cycle,mode='proof',BOOT_sha256=digest(diagnostic)))
    zip_package(output/'rollback.zip',parts['boot'],dict(schema=SCHEMA,cycle=cycle,mode='rollback',BOOT_sha256=digest(parts['boot'])))
    package['proof_zip_sha256']=sha(output/'proof.zip');package['rollback_zip_sha256']=sha(output/'rollback.zip')
    save(output/'package-result.json',package)
    plan=dict(schema=PLAN_SCHEMA,version='v129',cycle=cycle,build_evidence_id=row['build_evidence_id'],packages=str(output),
              package_result_sha256=sha(output/'package-result.json'),minimum_battery=10,return_timeout_seconds=240,
              host_BOOT_write_limit=1,host_reboot_limit=1,internal_kexec_load_limit=1,internal_kexec_REBOOT_limit=1,
              normal_recovery_fallback='pretransfer/failure only',watchdog_automatic_reset='observed separately',
              XNU_execution_allowed=False,source_sha256=row['source_sha256'])
    save(output/'plan.json',plan)
    return dict(plan=str(output/'plan.json'),plan_sha256=sha(output/'plan.json'),device_operations=[])


def validate_plan(path,expected):
    path=private(path)
    if sha(path)!=hexid(expected,64):raise ValueError('exact reviewed plan SHA required')
    plan=read(path)
    if (plan.get('schema')!=PLAN_SCHEMA or plan.get('version')!='v129' or plan.get('minimum_battery')!=10 or
        plan.get('return_timeout_seconds')!=240 or any(plan.get(k)!=1 for k in ('host_BOOT_write_limit','host_reboot_limit','internal_kexec_load_limit','internal_kexec_REBOOT_limit')) or
        plan.get('XNU_execution_allowed') is not False):raise ValueError('bounded proof-only plan required')
    hexid(plan['cycle'],32);hexid(plan['build_evidence_id'],32);verify_pins(plan['source_sha256'])
    folder=private(plan['packages'])
    if sha(folder/'package-result.json')!=hexid(plan['package_result_sha256'],64):raise ValueError('package manifest changed')
    package=read(folder/'package-result.json')
    if package.get('schema')!=SCHEMA or any(package.get(k)!=plan[k] for k in ('cycle','build_evidence_id','source_sha256')) or package.get('XNU_execution_allowed') is not False:
        raise ValueError('package scope differs')
    build,raw=validate_build(package['build']);manifest,parts=backup(package['backup'])
    require_paired_BOOT(package['expected_current_BOOT_sha256'],parts['boot'])
    if sha(Path(package['build'])/'result.json')!=package['build_result_sha256'] or sha(Path(package['backup'])/'backup-manifest.json')!=package['backup_manifest_sha256'] or package['partitions']!=manifest['partitions']:
        raise ValueError('build/backup manifest changed')
    if build['build_evidence_id']!=plan['build_evidence_id'] or package['input_Image_sha256']!=digest(raw):raise ValueError('build identity differs')
    enabled=enable(raw,plan['cycle']);boot=(folder/'boot.img').read_bytes();h=header(boot)
    if digest(enabled)!=package['enabled_Image_sha256'] or boot[h['kernel_offset']:h['kernel_offset']+h['kernel_size']]!=enabled or h['ramdisk_size'] or h['cmdline']!=package['BOOT_cmdline']:
        raise ValueError('enabled proof BOOT differs')
    for file,key,payload,mode in [('proof.zip','proof_zip_sha256',boot,'proof'),('rollback.zip','rollback_zip_sha256',parts['boot'],'rollback')]:
        if sha(folder/file)!=package[key]:raise ValueError('paired ZIP changed')
        with zipfile.ZipFile(folder/file) as bundle:
            if bundle.namelist()!=['boot.img','proof.json'] or bundle.read('boot.img')!=payload or read_zip_metadata(bundle)!=dict(schema=SCHEMA,cycle=plan['cycle'],mode=mode,BOOT_sha256=digest(payload)):
                raise ValueError('dedicated inert package contents differ')
    if digest(boot)!=package['diagnostic_BOOT_sha256'] or len(boot)!=len(parts['boot']) or package['rollback_BOOT_sha256']!=digest(parts['boot']):raise ValueError('full-partition payload differs')
    return plan,package


def read_zip_metadata(bundle):return json.loads(bundle.read('proof.json'))


def require_paired_BOOT(current_boot_sha,paired_boot):
    if hexid(current_boot_sha,64)!=digest(paired_boot):
        raise ValueError('current BOOT must be the exact paired backup BOOT; restore baseline first')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('build','backup','twrp','mkbootimg','output'):p.add_argument('--'+name,required=True,type=Path)
    p.add_argument('--current-boot-sha256',required=True);a=p.parse_args()
    print(json.dumps(prepare(a.build,a.backup,a.twrp,a.mkbootimg,a.output,a.current_boot_sha256)))
