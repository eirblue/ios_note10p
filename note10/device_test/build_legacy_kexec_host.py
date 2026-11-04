"""One fresh opt-in Linux host/PID1/park build; never emits a hardware package."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys

sys.dont_write_bytecode=True
from build_xnu_runtime_plan_component import acquire,extract,COMMIT,ARCHIVE_SHA,DEFCONFIG
import prepare_legacy_kexec_recovery as prepare
from test_legacy_kexec_backend import SOURCES,SCOPE

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
WORKFLOW='.github/workflows/note10-legacy-kexec-recovery-proof.yml'
FILES=tuple('note10/device_test/'+name for name in SOURCES)+(
    'note10/device_test/build_legacy_kexec_host.py',WORKFLOW,
    'note10/device_test/build_xnu_runtime_plan_component.py',
    'note10/device_test/sealed_affinity_artifact.cjs')
SETTINGS=dict(KEXEC='y',KEXEC_JUMP='n',SMP='y',HOTPLUG_CPU='y',PM_SLEEP_SMP='y',
              ARM64_4K_PAGES='y',SYSFS='y',OF='y',SEC_REBOOT='y',EXYNOS_PMU='y',
              S3C2410_WATCHDOG='y',S3C2410_SHUTDOWN_REBOOT='y',NOTE10_LEGACY_KEXEC_RECOVERY_PROOF='y',
              BLK_DEV_INITRD='y',INITRAMFS_FORCE='y',INITRAMFS_COMPRESSION_NONE='y',
              INITRAMFS_COMPRESSION_GZIP='n',INITRAMFS_COMPRESSION_BZIP2='n',INITRAMFS_COMPRESSION_LZMA='n',
              INITRAMFS_COMPRESSION_XZ='n',INITRAMFS_COMPRESSION_LZO='n',INITRAMFS_COMPRESSION_LZ4='n',
              CMDLINE='"rdinit=/init"',CMDLINE_FORCE='n',CMDLINE_EXTEND='y',CMDLINE_FROM_BOOTLOADER='n',
              LTO='n',LTO_CLANG='n',FTRACE_MCOUNT_RECORD='n',STACK_VALIDATION='n',LOCALVERSION_AUTO='n',
              LOCALVERSION='"-v128-kexec-recovery-proof"')


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def save(path,row):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(row,indent=2)+'\n',encoding='utf-8')


def cpio(init):
    if init[:6]!=b'\x7fELF\x02\x01' or init[18:20]!=b'\xb7\x00' or len(init)>1024*1024:
        raise ValueError('bounded new AArch64 PID1 required')
    out=bytearray()
    for name,mode,data,major,minor in [('dev',0o040755,b'',0,0),('sys',0o040755,b'',0,0),
        ('dev/console',0o020600,b'',5,1),('dev/kmsg',0o020600,b'',1,11),('init',0o100755,init,0,0),('TRAILER!!!',0,b'',0,0)]:
        encoded=name.encode()+b'\0';fields=(len(out)+1,mode,0,0,2 if mode==0o040755 else 1,0,len(data),0,0,major,minor,len(encoded),0)
        out.extend(b'070701'+''.join(f'{x:08x}' for x in fields).encode()+encoded);out.extend(bytes(-len(out)%4))
        out.extend(data);out.extend(bytes(-len(out)%4))
    out.extend(bytes(-len(out)%512));return bytes(out)


def pass_context(encoded):
    raw=base64.b64decode(encoded,validate=True)
    if len(raw)>32768:raise ValueError('bounded public synthetic PASS metadata required')
    row=json.loads(raw)
    expected={name:sha(HERE/name) for name in SOURCES}
    if (set(row)!={'schema','scope','passed','result_sha256','source_sha256'} or
        row['schema']!='note10-v128-retained-new-test-pass-v1' or row['scope']!=SCOPE or row['passed'] is not True or
        re.fullmatch('[0-9a-f]{64}',row['result_sha256'] or '') is None or row['source_sha256']!=expected):
        raise ValueError('Root-bound retained NEW PASS differs from unchanged sources')
    return row


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',required=True,type=Path);p.add_argument('--archive',type=Path)
    p.add_argument('--jobs',type=int,default=4);p.add_argument('--expected-source-head',required=True)
    p.add_argument('--passed-new-test-context-b64',required=True)
    a=p.parse_args();out=a.output.absolute();work=out.with_name(out.name+'-workspace')
    if (not sys.platform.startswith('linux') or out!=out.resolve() or out.exists() or work.exists() or
        not out.is_relative_to(ROOT/'note10/private') or out==ROOT/'note10/private' or not 1<=a.jobs<=8):
        p.error('fresh bounded private Linux host build required')
    if re.fullmatch('[0-9a-f]{40}',a.expected_source_head or '') is None:p.error('reviewed source head required')
    ci={name:os.environ.get(name,'') for name in ('GITHUB_SHA','GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT','GITHUB_JOB','GITHUB_WORKFLOW_REF','GITHUB_WORKFLOW_SHA','GITHUB_REPOSITORY')}
    if (ci['GITHUB_SHA']!=a.expected_source_head or ci['GITHUB_WORKFLOW_SHA']!=ci['GITHUB_SHA'] or
        ci['GITHUB_REPOSITORY']!='eirblue/ios_note10p' or ci['GITHUB_JOB']!='legacy-kexec-recovery-proof' or
        not ci['GITHUB_WORKFLOW_REF'].startswith('eirblue/ios_note10p/'+WORKFLOW+'@')):
        p.error('exact reviewed CI source/workflow/job required')
    retained=pass_context(a.passed_new_test_context_b64)
    manifest={name:sha(ROOT/name) for name in FILES}
    identity=hashlib.sha256(json.dumps(dict(source=manifest,ci=ci),sort_keys=True).encode()).hexdigest()[:32]
    archive=a.archive.absolute() if a.archive else out.with_name(out.name+'-kernel-input.tar.gz')
    if archive.is_symlink() or archive.is_relative_to(out) or archive.is_relative_to(work):p.error('ordinary immutable archive must stay external')
    out.mkdir(parents=True);commands=[]
    result=dict(schema='note10-v128-kexec-host-build-v1',version='v128',passed=False,ci_context=ci,source_sha256=manifest,
                kernel_commit=COMMIT,kernel_archive_sha256=ARCHIVE_SHA,public_defconfig=DEFCONFIG,
                build_evidence_id=identity,retained_NEW_PASS_operator_binding=retained,old_tests_replayed=0,
                hardware_package_emitted=False,hardware_package_emission_allowed=False,execution_slot_enabled=False,
                physical_ready=False,device_operations=[],XNU_execution_allowed=False)
    env=dict(os.environ,PLATFORM_VERSION='11',ANDROID_MAJOR_VERSION='r')

    def run(args,name,timeout=1800):
        command=[str(x) for x in args];log=out/(name+'.log');log.parent.mkdir(parents=True,exist_ok=True)
        row=dict(argv=command,log=str(log),completed=False);commands.append(row);save(out/'commands.json',commands)
        with log.open('wb') as stream:done=subprocess.run(command,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=timeout)
        row.update(completed=True,returncode=done.returncode);save(out/'commands.json',commands)
        if done.returncode:raise ValueError('fresh host command failed: '+name)
        return log.read_text(errors='strict')

    try:
        if not a.archive:acquire(archive)
        if sha(archive)!=ARCHIVE_SHA:raise ValueError('immutable kernel archive pin differs')
        work.mkdir();source=extract(archive,work/'source');objects=work/'objects';objects.mkdir()
        for name in prepare.PINS:
            target=out/'stock'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/name,target)
        overlays=prepare.install(source,identity);save(out/'overlay.json',dict(files_sha256=overlays,default_enabled=False))
        for name in overlays:
            target=out/'overlay'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/name,target)
        firmware=source/'firmware/Makefile';text=firmware.read_text()
        old='$(call cmd,fwbin,$(patsubst %.gen.S,%,$@))'
        new='$(call cmd,fwbin,$(if $(wildcard $(srctree)/$(patsubst %.gen.S,%,$@)),$(srctree)/$(patsubst %.gen.S,%,$@),$(patsubst %.gen.S,%,$@)))'
        if text.count(old)!=1:raise ValueError('pinned existing firmware rule differs')
        firmware.write_text(text.replace(old,new));result['firmware_make_sha256']=sha(firmware)
        tools={}
        for name in ('clang-14','gcc','make','aarch64-linux-gnu-gcc','arm-linux-gnueabi-gcc','aarch64-linux-gnu-ld','aarch64-linux-gnu-objcopy','aarch64-linux-gnu-nm'):
            tool=shutil.which(name)
            if not tool:raise ValueError('fresh build tool missing: '+name)
            tools[name]=dict(path=str(Path(tool).resolve()),sha256=sha(tool))
        save(out/'toolchain.json',tools)
        cc='aarch64-linux-gnu-gcc'
        run([cc,'-c','-nostdlib','-static','-ffreestanding',HERE/'kexec_recovery_park.S','-o',out/'park.o'],'00-park-compile')
        run(['aarch64-linux-gnu-ld','--build-id=none','-static','-e','_start','-Ttext=0',out/'park.o','-o',out/'park.elf'],'01-park-link')
        symbols=run(['aarch64-linux-gnu-nm','-n',out/'park.elf'],'02-park-symbols')
        run(['aarch64-linux-gnu-objcopy','-O','binary','--only-section=.text',out/'park.elf',out/'park.bin'],'03-park-binary')
        names={parts[-1]:int(parts[0],16) for line in symbols.splitlines() if len(parts:=line.split())==3 and re.fullmatch('[0-9a-fA-F]+',parts[0])}
        park=(out/'park.bin').read_bytes();cookie=names.get('n10_park_cookie',-1)
        if names.get('_start')!=0 or not 0<len(park)<=16384 or not 0<=cookie<=len(park)-16:
            raise ValueError('actual new park code/symbol geometry differs')
        header=('#define N10_KEXEC_BUILD_ID "'+identity+'"\n#define N10_PARK_COOKIE_OFFSET '+str(cookie)+'\nstatic const unsigned char n10_park_bytes[]={'+','.join(str(x) for x in park)+'};\n').encode()
        (out/'legacy_kexec_build.h').write_bytes(header)
        run([cc,'-std=c11','-O2','-ffreestanding','-fno-builtin','-fno-stack-protector','-nostdlib','-static','-Wall','-Wextra','-Werror',
             '-I',HERE,'-I',out,'-I','/usr/aarch64-linux-gnu/include','-Wl,--build-id=none','-Wl,-e,_start',
             HERE/'legacy_kexec_syscall.S',HERE/'legacy_kexec_loader.c',HERE/'legacy_kexec_core.c','-o',out/'minimal-init.elf'],'04-proof-PID1')
        init=(out/'minimal-init.elf').read_bytes();archive_data=cpio(init);(out/'initramfs.cpio').write_bytes(archive_data)
        make=['make','-C',source,'O='+str(objects),'ARCH=arm64','CC=clang-14','CROSS_COMPILE=aarch64-linux-gnu-',
              'CLANG_TRIPLE=aarch64-linux-gnu-','CROSS_COMPILE_ARM32=arm-linux-gnueabi-',
              'GCC_TOOLCHAIN_DIR=/usr/aarch64-linux-gnu/bin/','HOSTCC=gcc','HOSTCFLAGS=-Wno-error=deprecated-declarations','KCFLAGS=-gdwarf-4']
        run([*make,DEFCONFIG],'05-defconfig')
        baseline=(objects/'.config').read_bytes();(out/'public-baseline.config').write_bytes(baseline)
        if ('CONFIG_'+prepare.OPTION+'=y').encode() in baseline:raise ValueError('backend not default off')
        settings=dict(SETTINGS,INITRAMFS_SOURCE='"'+str(out/'initramfs.cpio')+'"')
        for index,(name,value) in enumerate(settings.items()):
            action=['--enable' if value=='y' else '--disable',name] if value in ('y','n') else ['--set-str',name,value[1:-1]]
            run([source/'scripts/config','--file',objects/'.config',*action],f'settings/{index:02d}')
        run([*make,'olddefconfig'],'06-effective-config')
        config=(objects/'.config').read_text();shutil.copyfile(objects/'.config',out/'actual-effective.config')
        for name,value in settings.items():
            wanted='# CONFIG_'+name+' is not set' if value=='n' else 'CONFIG_'+name+'='+value
            if wanted not in config.splitlines() and not(value=='n' and 'CONFIG_'+name+'=' not in config):
                raise ValueError('actual new host config differs: '+name)
        for line in ('CONFIG_KEXEC_CORE=y','CONFIG_PM_SLEEP_SMP=y','CONFIG_ARM64_4K_PAGES=y'):
            if line not in config.splitlines():raise ValueError('actual legacy backend dependency missing')
        run([*make,'V=1','-j'+str(a.jobs),'Image'],'07-fresh-Image',5400)
        raw=(objects/'arch/arm64/boot/Image').read_bytes()
        if raw[56:60]!=b'ARM\x64' or not 0<struct.unpack_from('<Q',raw,16)[0]<=57*1024*1024 or raw.count(archive_data)!=1:
            raise ValueError('new host Image/header/builtin PID1 binding differs')
        if raw.count(b'!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')!=1:raise ValueError('execution slot not uniquely disabled')
        shutil.copyfile(objects/'arch/arm64/boot/Image',out/'Image');shutil.copyfile(objects/'System.map',out/'System.map')
        object_pins={}
        for name in ('arch/arm64/mm/init.o','arch/arm64/kernel/machine_kexec.o','arch/arm64/kernel/relocate_kernel.o','drivers/samsung/sec_reboot.o','drivers/watchdog/s3c2410_wdt.o','init/main.o'):
            path=objects/name;target=out/'objects'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
            cmd=path.with_name('.'+path.name+'.cmd');shutil.copyfile(cmd,target.with_suffix('.cmd'))
            object_pins[name]=dict(sha256=sha(path),command_sha256=sha(cmd))
        if sha(archive)!=ARCHIVE_SHA or manifest!={name:sha(ROOT/name) for name in FILES}:raise ValueError('immutable build inputs changed')
        result.update(passed=True,Image_sha256=sha(out/'Image'),Image_bytes=len(raw),effective_config_sha256=sha(out/'actual-effective.config'),
                      park_sha256=sha(out/'park.bin'),PID1_sha256=sha(out/'minimal-init.elf'),objects=object_pins,
                      early_destination_bytes=33554432,destination_alignment=16384,same_boot_cookie_required=True,
                      persistent_park_evidence_validated=False,watchdog_to_TWRP_proven=False)
    except Exception:
        import traceback
        result['error']=traceback.format_exc()
    save(out/'result.json',result)
    return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
