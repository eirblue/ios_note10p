"""Local v131 private slot/package producer; one Image reader, no payload re-compression."""
import argparse
import json
import re
from pathlib import Path
import struct
import subprocess
import sys
import uuid
import zipfile
from v130_contract import ROOT,PAYLOAD_SCHEMA,BOOT_LIMIT,private,ordinary,hexid,sha,digest,read,save
from v130_slot import insert,metadata
from v131_build import source_pins,SETTINGS,BUILD_SCHEMA
MKBOOTIMG_SHA='2a8d05d34110f66c463668f43fc812ce2e46e66459c347eaadb080271df69aa8'
TWRP_SHA='e8de29b03fc3eab95f51663b08b2f848e168854a15f8a598a1f80d216f4794df'
INPUTS_SCHEMA='note10-v131-package-inputs-v1'
PACKAGE_SCHEMA='note10-v131-private-xnu-package-v1'
PLAN_SCHEMA='note10-v131-owned-xnu-cycle-v1'
PARTITIONS={'boot','recovery','dtb','dtbo','vbmeta'}

def header(raw,*,reference=False,file_size=None):
    if len(raw)<1660 or raw[:8]!=b'ANDROID!':raise ValueError('Android BOOT header required')
    keys=('kernel_size','kernel_addr','ramdisk_size','ramdisk_addr','second_size','second_addr','tags_addr','page_size','header_version','encoded_os')
    row=dict(zip(keys,struct.unpack_from('<10I',raw,8)));page=row['page_size']
    if row['header_version']!=1 or page not in (2048,4096,8192,16384):raise ValueError('observed v1 BOOT layout required')
    z=lambda s:s.split(b'\0',1)[0].decode('ascii')
    row.update(name=z(raw[48:64]),cmdline=z(raw[64:576])+z(raw[608:1632]),kernel_offset=page)
    row['ramdisk_offset']=page+(row['kernel_size']+page-1)//page*page
    row['payload_end']=row['ramdisk_offset']+(row['ramdisk_size']+page-1)//page*page
    row['recovery_dtbo_size'],row['recovery_dtbo_offset'],row['header_size']=struct.unpack_from('<IQI',raw,1632)
    total=len(raw) if file_size is None else file_size
    if (type(total) is not int or not len(raw)<=total<=128*1024*1024 or
        (not reference and total!=len(raw)) or not row['kernel_size'] or row['second_size'] or
        row['header_size']!=1648 or row['payload_end']>total):raise ValueError('unexpected BOOT payload layout')
    if row['recovery_dtbo_size']:
        if (not reference or row['recovery_dtbo_offset']!=row['payload_end'] or
            row['recovery_dtbo_offset']%page or row['recovery_dtbo_offset']+row['recovery_dtbo_size']>total):
            raise ValueError('unexpected reference recovery DTBO extent')
    elif row['recovery_dtbo_offset']:
        raise ValueError('empty recovery DTBO must have zero offset')
    return row



def pinned(item):
    if set(item)!={'path','sha256'}:raise ValueError('exact path/pin pair required')
    path=ordinary(item['path'])
    if sha(path)!=hexid(item['sha256']):raise ValueError('metadata/tool pin differs')
    return path

def contract(path,expected):
    path=ordinary(path)
    if sha(path)!=hexid(expected):raise ValueError('reviewed private package contract differs')
    row=read(path)
    roles={'build_result','payload_result','platform_result','backup_manifest','current130_package','current130_ledger','twrp','mkbootimg'}
    if set(row)!={'schema','inputs'} or row.get('schema')!=INPUTS_SCHEMA or set(row.get('inputs',{}))!=roles:raise ValueError('exact package source roles required')
    # Images and compressed member are consumed and hashed by their sole producer read below.
    paths={k:pinned(v) for k,v in row['inputs'].items() if k not in ('twrp',)}
    twrp=row['inputs']['twrp']
    if set(twrp)!={'path','sha256','header_sha256','bytes'}:raise ValueError('reviewed official header-only provenance required')
    paths['twrp']=ordinary(twrp['path']);hexid(twrp['sha256']);hexid(twrp['header_sha256'])
    if paths['twrp'].stat().st_size!=twrp['bytes']:raise ValueError('official reference size differs')
    return row,paths

def verify_sources(pins):
    if pins!=source_pins():raise ValueError('compiled source and current v131 domain differ')

def current_and_restore(current,ledger,backup):
    if (current.get('schema')!='note10-v130-private-xnu-package-v1' or current.get('version')!='v130' or
        ledger.get('schema')!='note10-v130-owned-XNU-ledger-v1' or ledger.get('recovery_returned') is not True or
        any(type(ledger.get(k)) is not int or ledger[k]!=1 for k in ('host_BOOT_write_attempts','host_reboot_attempts','internal_kexec_load_attempts_observed','internal_kexec_REBOOT_attempts_observed')) or
        ledger.get('cycle')!=current.get('cycle') or ledger.get('build_evidence_id')!=current.get('build_evidence_id') or
        ledger.get('normal_recovery_fallback_observed') is not False or
        ledger.get('status')!='cycle-complete-XNU-proof-limits-retained'):raise ValueError('accepted consumed current130 return baseline required')
    if backup.get('complete') is not True or backup.get('partition_writes') is not False:raise ValueError('preserved safe126 backup required')
    rows=backup.get('partitions',[])
    if len(rows)!=5 or {r['partition'] for r in rows}!=PARTITIONS:raise ValueError('exact safe five-partition rows required')
    for row in rows:
        if (row['file']!=row['partition']+'.img' or row.get('remote_hash_before_and_after_match') is not True or
            type(row['size']) is not int or not 0<row['size']<=128*1024*1024 or
            re.fullmatch('/dev/block/sd[a-z][0-9]+',row['block_node']) is None):raise ValueError('unqualified restore partition')
        hexid(row['sha256'])
    safe=next(r for r in rows if r['partition']=='boot')
    if safe['sha256']!=current['rollback_BOOT_sha256'] or safe['sha256']==current['diagnostic_BOOT_sha256'] or backup['bootloader']!=current['bootloader']:
        raise ValueError('safe126 rollback must differ from enabled current130')
    for name in PARTITIONS-{'boot'}:
        a=next(r for r in rows if r['partition']==name);b=next(r for r in current['partitions'] if r['partition']==name)
        if any(a[k]!=b[k] for k in ('sha256','size','block_node')):raise ValueError('unmodified partition baseline differs')
    return hexid(current['diagnostic_BOOT_sha256']),safe

def zip_package(path,payload,meta):
    with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_STORED) as out:
        out.writestr('boot.img',payload);out.writestr('handoff.json',json.dumps(meta,sort_keys=True)+'\n')

def prepare(input_path,input_sha,output):
    output=private(output);spec,paths=contract(input_path,input_sha)
    if output.exists():raise ValueError('fresh package output required')
    build=read(paths['build_result']);payload=read(paths['payload_result']);platform=read(paths['platform_result'])
    if (build.get('schema')!=BUILD_SCHEMA or build.get('version')!='v131' or build.get('passed') is not True or build.get('execution_slot_enabled') is not False or
        build.get('private_payload_uploaded') is not False or payload.get('schema')!=PAYLOAD_SCHEMA or payload.get('passed') is not True or
        platform.get('schema')!='note10-v130-real-platform-derivation-v1' or platform.get('passed') is not True):raise ValueError('accepted generic build/ONE private member/actual platform required')
    verify_sources(build['source_sha256']);identity=hexid(build['build_evidence_id'],32)
    baseline=read(paths['current130_package']);ledger=read(paths['current130_ledger']);backup=read(paths['backup_manifest'])
    current_sha,safe=current_and_restore(baseline,ledger,backup)
    image=(paths['build_result'].parent/'Image').read_bytes()
    if digest(image)!=build['Image_sha256'] or len(image)!=build['Image_bytes'] or image[56:60]!=b'ARM\x64':raise ValueError('generic Image bytes differ')
    config=(paths['build_result'].parent/'actual-effective.config').read_bytes()
    if digest(config)!=build['effective_config_sha256']:raise ValueError('compiled config changed')
    for name,value in SETTINGS.items():
        line=('# CONFIG_'+name+' is not set' if value=='n' else 'CONFIG_'+name+'='+value).encode()
        if value!='n' and line not in config.splitlines():raise ValueError('required compiled profile differs')
    if payload.get('compressed_file')!='private-payload.cpio.gz':raise ValueError('exact retained gzip member name required')
    member=ordinary(paths['payload_result'].parent/payload['compressed_file']).read_bytes()
    if digest(member)!=payload['compressed_sha256'] or len(member)!=payload['compressed_bytes']:raise ValueError('ONE prepared gzip member differs')
    adt=(paths['platform_result'].parent/'platform.adt').read_bytes();actual=(paths['platform_result'].parent/'platform.contract').read_bytes()
    if digest(adt)!=platform['platform_adt_sha256'] or digest(actual)!=platform['platform_contract_sha256']:raise ValueError('actual derived platform differs')
    meta=metadata(adt,actual,platform['source_capture_sha256']);cycle=uuid.uuid4().hex
    enabled,usage=insert(image,build['layout'],member,meta,cycle)
    # Only source-built slot and separate source-built PID1 cycle field may change.
    layout=build['layout'];start=layout['slot_offset'];end=start+layout['slot_bytes'];cycle_at=layout['cycle_offset']
    if image[:cycle_at]!=enabled[:cycle_at] or image[cycle_at+32:start]!=enabled[cycle_at+32:start] or image[end:]!=enabled[end:]:raise ValueError('out-of-slot Image mutation')
    directory=paths['backup_manifest'].parent;safe_raw=(directory/safe['file']).read_bytes()
    if digest(safe_raw)!=safe['sha256'] or len(safe_raw)!=safe['size']:raise ValueError('safe126 rollback bytes differ')
    stock=header(safe_raw)
    with paths['twrp'].open('rb') as stream:reference_raw=stream.read(1660)
    if spec['inputs']['twrp']['sha256']!=TWRP_SHA or spec['inputs']['mkbootimg']['sha256']!=MKBOOTIMG_SHA:raise ValueError('official recovery/mkbootimg source pin required')
    if digest(reference_raw)!=spec['inputs']['twrp']['header_sha256']:raise ValueError('consumed official header bytes differ')
    reference=header(reference_raw,reference=True,file_size=paths['twrp'].stat().st_size)
    if any(stock[k]!=reference[k] for k in ('kernel_addr','tags_addr','page_size')):raise ValueError('official load contract differs')
    if len(reference['cmdline'].encode())>1535 or 'n10.cycle=' in reference['cmdline']:raise ValueError('official commandline contract differs')
    output.mkdir(parents=True);(output/'enabled-Image').write_bytes(enabled)
    encoded=stock['encoded_os'];os_version='.'.join(str((encoded>>n)&127) for n in (25,18,11));month=f'{2000+((encoded>>4)&127):04d}-{encoded&15:02d}'
    packed=output/'packed-boot.img'
    command=[sys.executable,'-B',str(paths['mkbootimg']),'--header_version','1','--kernel',str(output/'enabled-Image'),'--base','0',
        '--kernel_offset',hex(stock['kernel_addr']),'--ramdisk_offset',hex(stock['ramdisk_addr']),'--tags_offset',hex(stock['tags_addr']),
        '--pagesize',str(stock['page_size']),'--board',stock['name'],'--cmdline',reference['cmdline'],'--os_version',os_version,'--os_patch_level',month,'--output',str(packed)]
    subprocess.run(command,cwd=ROOT,check=True,capture_output=True,timeout=60)
    raw=packed.read_bytes();h=header(raw);trailer=b'SEANDROIDENFORCE'
    if h['ramdisk_size'] or h['recovery_dtbo_size'] or h['cmdline']!=reference['cmdline'] or raw[h['kernel_offset']:h['kernel_offset']+h['kernel_size']]!=enabled:
        raise ValueError('actual zero external ramdisk BOOT differs')
    if safe_raw[stock['payload_end']:stock['payload_end']+len(trailer)]!=trailer or len(raw)+len(trailer)>min(BOOT_LIMIT,len(safe_raw)):
        raise ValueError('actual BOOT capacity/source trailer differs')
    boot=(raw+trailer).ljust(len(safe_raw),b'\0');(output/'boot.img').write_bytes(boot)
    package=dict(schema=PACKAGE_SCHEMA,version='v131',cycle=cycle,build_evidence_id=identity,
        input_contract_path=str(ordinary(input_path)),input_contract_sha256=input_sha,input_Image_sha256=digest(image),enabled_Image_sha256=digest(enabled),
        diagnostic_BOOT_sha256=digest(boot),expected_current_BOOT_sha256=current_sha,rollback_BOOT_sha256=digest(safe_raw),
        backup=str(directory),backup_manifest_sha256=spec['inputs']['backup_manifest']['sha256'],partitions=backup['partitions'],bootloader=backup['bootloader'],
        source_sha256=source_pins(),build_source_sha256=build['source_sha256'],build_result_sha256=spec['inputs']['build_result']['sha256'],
        private_member_sha256=digest(member),platform_result_sha256=spec['inputs']['platform_result']['sha256'],usage=usage,
        compressed_member_reads=1,raw_kernel_reads=0,adapter_reads=0,compressions=0,
        official_reference_header_sha256=digest(reference_raw),official_reference_full_SHA_source='reviewed input metadata; this producer consumes only exact1660B header',
        XNU_execution_allowed=True,physical_gate_open=False,BOOT_cmdline=reference['cmdline'],external_ramdisk_included=False,
        return_evidence_limit='bounded automatic return previously observed; formal hardware reset cause and actual XNU entry remain unproven')
    zip_package(output/'xnu.zip',boot,dict(schema=PACKAGE_SCHEMA,cycle=cycle,mode='xnu',BOOT_sha256=digest(boot)))
    zip_package(output/'rollback.zip',safe_raw,dict(schema=PACKAGE_SCHEMA,cycle=cycle,mode='safe126-rollback',BOOT_sha256=digest(safe_raw)))
    package['xnu_zip_sha256']=sha(output/'xnu.zip');package['rollback_zip_sha256']=sha(output/'rollback.zip');save(output/'package-result.json',package)
    plan=dict(schema=PLAN_SCHEMA,version='v131',cycle=cycle,build_evidence_id=identity,packages=str(output),package_result_sha256=sha(output/'package-result.json'),
        minimum_battery=10,return_timeout_seconds=240,host_BOOT_write_limit=1,host_reboot_limit=1,internal_kexec_load_limit=1,internal_kexec_REBOOT_limit=1,
        normal_recovery_fallback='pretransfer/failure only',watchdog_automatic_reset='observed separately',XNU_execution_allowed=True,
        source_sha256=package['source_sha256'],build_source_sha256=build['source_sha256'])
    save(output/'plan.json',plan);return dict(plan=str(output/'plan.json'),plan_sha256=sha(output/'plan.json'),device_operations=[])

def validate_plan(path,expected):
    path=ordinary(path)
    if sha(path)!=hexid(expected):raise ValueError('exact reviewed plan required')
    plan=read(path)
    if (plan.get('schema')!=PLAN_SCHEMA or plan.get('version')!='v131' or plan.get('XNU_execution_allowed') is not True or
        type(plan.get('minimum_battery')) is not int or plan['minimum_battery']!=10 or
        type(plan.get('return_timeout_seconds')) is not int or plan['return_timeout_seconds']!=240 or
        any(type(plan.get(k)) is not int or plan[k]!=1 for k in ('host_BOOT_write_limit','host_reboot_limit','internal_kexec_load_limit','internal_kexec_REBOOT_limit'))):raise ValueError('bounded actual-XNU plan required')
    verify_sources(plan['source_sha256']);folder=private(plan['packages'])
    if sha(folder/'package-result.json')!=plan['package_result_sha256']:raise ValueError('package receipt changed')
    package=read(folder/'package-result.json')
    if package.get('schema')!=PACKAGE_SCHEMA or any(package.get(k)!=plan[k] for k in ('cycle','build_evidence_id','source_sha256','build_source_sha256','XNU_execution_allowed')):
        raise ValueError('package/plan join differs')
    # Producer acceptance is retained; do not reread Image/raw XNU/recompress here.
    for name,key in [('boot.img','diagnostic_BOOT_sha256'),('xnu.zip','xnu_zip_sha256'),('rollback.zip','rollback_zip_sha256')]:
        if sha(folder/name)!=package[key]:raise ValueError('admitted package transport bytes differ')
    if package['expected_current_BOOT_sha256']==package['rollback_BOOT_sha256']:raise ValueError('enabled130 and safe126 baseline conflated')
    hexid(plan['cycle'],32);hexid(plan['build_evidence_id'],32);return plan,package

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--contract',required=True,type=Path);p.add_argument('--contract-sha256',required=True);p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();print(json.dumps(prepare(a.contract,a.contract_sha256,a.output)))
