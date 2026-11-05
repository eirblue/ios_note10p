"""One fresh generic disabled v130 Image. No private XNU/platform input is accepted."""
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
from v130_contract import ROOT,BUILD_SCHEMA,BOOT_LIMIT,sha,digest,read,private,hexid,save,DISABLED
from v130_sources import materialize,INPUT128,INPUT129
from v130_archive import COMMIT,ARCHIVE_SHA,DEFCONFIG,acquire,extract
from v130_slot import generic
import v130_prepare as prepare
HERE=Path(__file__).resolve().parent
WORKFLOW='.github/workflows/note10-v130-actual-xnu.yml'
SOURCES=('v130_archive.py', 'v130_build.py', 'v130_contract.py', 'v130_cycle.py', 'v130_dmaengine.inc', 'v130_fixture.c', 'v130_gate_core.h', 'v130_gic.inc', 'v130_handoff_core.c', 'v130_handoff_core.h', 'v130_iommu.inc', 'v130_kernel.c', 'v130_kernel_api.h', 'v130_loader.c', 'v130_package.py', 'v130_payload.py', 'v130_pl330.inc', 'v130_platform.py', 'v130_prepare.py', 'v130_slot.py', 'v130_sources.py', 'v130_timer.inc', 'v130_ufs.inc', 'v130_usb.inc', 'v130_usb_gadget.inc', 'test_v130_handoff.py')
FILES=tuple('note10/device_test/'+name for name in SOURCES)+('note10/xnu26/boot_adt.py',WORKFLOW)
SETTINGS=dict(KEXEC='y',KEXEC_JUMP='n',SMP='y',HOTPLUG_CPU='y',PM_SLEEP_SMP='y',ARM64_4K_PAGES='y',
    KVM='n',KVM_ARM_HOST='n',ARM64_VHE='n',SYSFS='y',OF='y',SEC_REBOOT='y',EXYNOS_PMU='y',
    S3C2410_WATCHDOG='y',S3C2410_SHUTDOWN_REBOOT='y',NOTE10_XNU_KEXEC_HANDOFF='y',
    NOTE10_LEGACY_KEXEC_RECOVERY_PROOF='n',EXYNOS_IOMMU='y',PL330_DMA='y',ARM_GIC='y',ARM_ARCH_TIMER='y',
    USB_GADGET='y',USB_DWC3='y',USB_DWC3_EXYNOS='y',USB_DWC3_GADGET='y',USB_DWC3_HOST='n',USB_DWC3_DUAL_ROLE='n',
    USB_CONFIGFS='n',USB_G_ANDROID='n',USB_GADGETFS='n',USB_ZERO='n',USB_MASS_STORAGE='n',
    USB_G_SERIAL='n',USB_ETH='n',USB_G_NCM='n',USB_G_ACM_MS='n',USB_G_MULTI='n',USB_G_HID='n',
    SCSI_UFSHCD='y',CRYPTO='y',CRYPTO_SHA256='y',CRYPTO_HASH='y',CRYPTO_USER_API='y',CRYPTO_USER_API_HASH='y',
    BLK_DEV_INITRD='y',RD_GZIP='y',INITRAMFS_FORCE='y',INITRAMFS_COMPRESSION_NONE='y',
    INITRAMFS_COMPRESSION_GZIP='n',INITRAMFS_COMPRESSION_BZIP2='n',INITRAMFS_COMPRESSION_LZMA='n',
    INITRAMFS_COMPRESSION_XZ='n',INITRAMFS_COMPRESSION_LZO='n',INITRAMFS_COMPRESSION_LZ4='n',
    CMDLINE='"rdinit=/init"',CMDLINE_FORCE='n',CMDLINE_EXTEND='y',CMDLINE_FROM_BOOTLOADER='n',
    LTO='n',LTO_CLANG='n',FTRACE_MCOUNT_RECORD='n',STACK_VALIDATION='n',LOCALVERSION_AUTO='n',
    LOCALVERSION='"-v130-owned-xnu"')


def source_pins():return {name:sha(ROOT/name) for name in FILES}

def pass_context(encoded):
    raw=base64.b64decode(encoded,validate=True)
    if len(raw)>32768:raise ValueError('bounded synthetic PASS metadata required')
    row=json.loads(raw)
    if (set(row)!={'schema','scope','passed','synthetic_result_sha256','source_sha256'} or
        row['schema']!='note10-v130-public-new-pass-v1' or row['scope']!='v130-owned-xnu-handoff-new-only' or
        row['passed'] is not True or row['source_sha256']!=source_pins()):raise ValueError('new synthetic PASS source binding differs')
    hexid(row['synthetic_result_sha256']);return row


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',required=True,type=Path);p.add_argument('--archive',type=Path)
    p.add_argument('--jobs',type=int,default=4);p.add_argument('--expected-source-head',required=True)
    p.add_argument('--passed-new-test-context-b64',required=True);a=p.parse_args()
    out=private(a.output);work=out.with_name(out.name+'-workspace');hexid(a.expected_source_head,40)
    if not sys.platform.startswith('linux') or out.exists() or work.exists() or not 1<=a.jobs<=8:p.error('one fresh Linux build required')
    ci={k:os.environ.get(k,'') for k in ('GITHUB_SHA','GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT','GITHUB_JOB','GITHUB_WORKFLOW_REF','GITHUB_WORKFLOW_SHA','GITHUB_REPOSITORY')}
    if (ci['GITHUB_SHA']!=a.expected_source_head or ci['GITHUB_WORKFLOW_SHA']!=a.expected_source_head or
        ci['GITHUB_REPOSITORY']!='eirblue/ios_note10p' or ci['GITHUB_JOB']!='v130-actual-xnu' or
        not ci['GITHUB_WORKFLOW_REF'].startswith('eirblue/ios_note10p/'+WORKFLOW+'@')):p.error('exact reviewed source/workflow required')
    retained=pass_context(a.passed_new_test_context_b64);pins=source_pins()
    identity=digest(json.dumps(dict(source=pins,ci=ci),sort_keys=True).encode())[:32]
    archive=a.archive.absolute() if a.archive else out.with_name(out.name+'-kernel-input.tar.gz')
    if archive.is_symlink() or archive.is_relative_to(out) or archive.is_relative_to(work):p.error('external ordinary source archive required')
    out.mkdir(parents=True);commands=[]
    result=dict(schema=BUILD_SCHEMA,version='v130',passed=False,ci_context=ci,source_sha256=pins,
        immutable128_source=INPUT128,immutable129_source=INPUT129,kernel_commit=COMMIT,kernel_archive_sha256=ARCHIVE_SHA,
        build_evidence_id=identity,retained_NEW_PASS=retained,old_tests_replayed=0,execution_slot_enabled=False,
        private_payload_uploaded=False,hardware_package_emitted=False,physical_ready=False,device_operations=[])
    env=dict(os.environ,PLATFORM_VERSION='11',ANDROID_MAJOR_VERSION='r')
    def run(args,name,timeout=1800):
        log=out/(name+'.log');log.parent.mkdir(parents=True,exist_ok=True)
        row=dict(argv=[str(x) for x in args],log=str(log),completed=False);commands.append(row)
        (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
        with log.open('wb') as stream:done=subprocess.run(row['argv'],cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=timeout)
        row.update(completed=True,returncode=done.returncode);(out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
        if done.returncode:raise ValueError('new host command failed: '+name)
    try:
        domains=materialize(out/'immutable-source-domains')
        if not a.archive:acquire(archive)
        if sha(archive)!=ARCHIVE_SHA:raise ValueError('kernel archive differs')
        work.mkdir();source=extract(archive,work/'source');objects=work/'objects';objects.mkdir()
        overlays=prepare.install(source,identity,domains['source128']);save(out/'overlay.json',dict(files_sha256=overlays,default_enabled=False))
        for name in overlays:
            target=out/'overlay'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/name,target)
        firmware=source/'firmware/Makefile';raw=firmware.read_bytes()
        old=b'$(call cmd,fwbin,$(patsubst %.gen.S,%,$@))'
        new=b'$(call cmd,fwbin,$(if $(wildcard $(srctree)/$(patsubst %.gen.S,%,$@)),$(srctree)/$(patsubst %.gen.S,%,$@),$(patsubst %.gen.S,%,$@)))'
        if raw.count(old)!=1:raise ValueError('existing firmware source boundary differs')
        firmware.write_bytes(raw.replace(old,new));result['firmware_make_sha256']=sha(firmware)
        tools={}
        for name in ('clang-14','gcc','make','aarch64-linux-gnu-gcc','arm-linux-gnueabi-gcc'):
            tool=shutil.which(name)
            if not tool:raise ValueError('new build tool missing: '+name)
            tools[name]=dict(path=str(Path(tool).resolve()),sha256=sha(tool))
        save(out/'toolchain.json',tools)
        (out/'v130_build_id.h').write_text('#define N130_BUILD_ID "'+identity+'"\n')
        run(['aarch64-linux-gnu-gcc','-std=c11','-O2','-static','-fno-stack-protector','-Wall','-Wextra','-Werror',
            '-I',HERE,'-I',out,'-Wl,--build-id=none',HERE/'v130_loader.c',HERE/'v130_handoff_core.c','-o',out/'minimal-init.elf'],'00-new-PID1')
        init=(out/'minimal-init.elf').read_bytes();archive_data,prefix=generic(init);(out/'initramfs.cpio').write_bytes(archive_data)
        make=['make','-C',source,'O='+str(objects),'ARCH=arm64','CC=clang-14','CROSS_COMPILE=aarch64-linux-gnu-',
            'CLANG_TRIPLE=aarch64-linux-gnu-','CROSS_COMPILE_ARM32=arm-linux-gnueabi-','GCC_TOOLCHAIN_DIR=/usr/aarch64-linux-gnu/bin/',
            'HOSTCC=gcc','HOSTCFLAGS=-Wno-error=deprecated-declarations','KCFLAGS=-gdwarf-4']
        run([*make,DEFCONFIG],'01-defconfig');baseline=(objects/'.config').read_bytes();(out/'public-baseline.config').write_bytes(baseline)
        if ('CONFIG_'+prepare.OPTION+'=y').encode() in baseline:raise ValueError('new profile is not default off')
        settings=dict(SETTINGS,INITRAMFS_SOURCE='"'+str(out/'initramfs.cpio')+'"')
        for index,(name,value) in enumerate(settings.items()):
            action=['--enable' if value=='y' else '--disable',name] if value in ('y','n') else ['--set-str',name,value[1:-1]]
            run([source/'scripts/config','--file',objects/'.config',*action],f'settings/{index:02d}')
        run([*make,'olddefconfig'],'02-effective-config');config=(objects/'.config').read_text();shutil.copyfile(objects/'.config',out/'actual-effective.config')
        for name,value in settings.items():
            wanted='# CONFIG_'+name+' is not set' if value=='n' else 'CONFIG_'+name+'='+value
            if wanted not in config.splitlines() and not(value=='n' and 'CONFIG_'+name+'=' not in config):raise ValueError('effective profile differs: '+name)
        run([*make,'V=1','-j'+str(a.jobs),'Image'],'03-new-Image',5400)
        image=(objects/'arch/arm64/boot/Image').read_bytes();symbols=(objects/'System.map').read_text()
        addresses={parts[2]:int(parts[0],16) for line in symbols.splitlines() if len(parts:=line.split())==3 and re.fullmatch('[0-9a-fA-F]+',parts[0])}
        if (image[56:60]!=b'ARM\x64' or len(image)>BOOT_LIMIT-32768 or image.count(archive_data)!=1 or image.count(DISABLED)!=1 or
            addresses.get('__initramfs_start',-1)-addresses.get('_text',-2)!=image.find(archive_data)):
            raise ValueError('actual source-built raw CPIO/symbol/disabled Image geometry differs')
        offset=image.find(archive_data);layout=dict(initramfs_offset=offset,initramfs_bytes=len(archive_data),prefix_bytes=prefix,
            slot_offset=offset+prefix,slot_bytes=len(archive_data)-prefix,cycle_offset=image.find(DISABLED))
        shutil.copyfile(objects/'arch/arm64/boot/Image',out/'Image');shutil.copyfile(objects/'System.map',out/'System.map')
        objects_pins={}
        for name in ('arch/arm64/mm/init.o','arch/arm64/kernel/machine_kexec.o','arch/arm64/kernel/relocate_kernel.o',
            'kernel/kexec_core.o','kernel/reboot.o','init/main.o','init/initramfs.o','drivers/samsung/sec_reboot.o',
            'drivers/watchdog/s3c2410_wdt.o','drivers/irqchip/irq-gic.o','drivers/clocksource/arm_arch_timer.o',
            'drivers/usb/dwc3/core.o','drivers/usb/dwc3/gadget.o','drivers/scsi/ufs/ufshcd.o','drivers/scsi/ufs/ufs-exynos.o','drivers/iommu/exynos-iommu.o','drivers/dma/dmaengine.o','drivers/dma/pl330.o'):
            path=objects/name;target=out/'objects'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
            command=path.with_name('.'+path.name+'.cmd');shutil.copyfile(command,target.with_suffix('.cmd'))
            objects_pins[name]=dict(sha256=sha(path),command_sha256=sha(command))
        if pins!=source_pins():raise ValueError('source changed during build')
        result.update(passed=True,Image_sha256=digest(image),Image_bytes=len(image),layout=layout,objects=objects_pins,
            PID1_sha256=digest(init),initramfs_sha256=digest(archive_data),effective_config_sha256=sha(out/'actual-effective.config'))
    except Exception:
        import traceback
        result['error']=traceback.format_exc()
    save(out/'result.json',result);return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
