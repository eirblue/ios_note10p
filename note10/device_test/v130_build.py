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
SOURCES=('v130_archive.py', 'v130_build.py', 'v130_contract.py', 'v130_cycle.py', 'v130_dmaengine.inc', 'v130_fixture.c', 'v130_gate_core.h', 'v130_gic.inc', 'v130_handoff_core.c', 'v130_handoff_core.h', 'v130_iommu.inc', 'v130_kernel.c', 'v130_kernel_api.h', 'v130_loader.c', 'v130_package.py', 'v130_payload.py', 'v130_pl330.inc', 'v130_platform.py', 'v130_prepare.py', 'v130_slot.py', 'v130_sources.py', 'v130_timer.inc', 'v130_ufs.inc', 'v130_usb.inc', 'v130_usb_gadget.inc', 'test_v130_handoff.py', 'test_v130_pid1_write_return.py')
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

RETAINED_SOURCE_COMMIT = '231cd13a6bb605d7f95dbfcba333fe49681e54f1'
RETAINED_SOURCE_SHA256 = {'note10/device_test/v130_archive.py': 'bc49ffef72f73769de77a55432253f57f14d20433933ac56570f0ebfc3a1bce4', 'note10/device_test/v130_build.py': 'dd4d84fb76942a8362687e7c8b375bfb2051d4258703a1711867dd3f572bd08f', 'note10/device_test/v130_contract.py': 'd3336dccb8edf2366d4cc8233cd83d18b27f4d65c7dd3a3627807ddd0858c929', 'note10/device_test/v130_cycle.py': 'b1a5dd876b02c3680a1f789e19d21d6cf5cd4750a39241b20eb1a7adb5d6f360', 'note10/device_test/v130_dmaengine.inc': '4c1be828c50a1e42ad169afac07a32533680009caf1f2b6ad64f8517af9ba7c7', 'note10/device_test/v130_fixture.c': '1895ee818cf274e9e9d134f0c38658f83392f689004f0e3aa180e9396f6035c5', 'note10/device_test/v130_gate_core.h': '12b36033bda6976deba188099b5b6d1bd32748e84ea2edd796a4463faca7f543', 'note10/device_test/v130_gic.inc': 'ace8aed4e9f6880ef1744602b366c2dddbbd51a29d5b3414e13f7bd01d7276ee', 'note10/device_test/v130_handoff_core.c': '4cf36f2a3e95c537f95db521f0b1626f303bf85c2ee1071624182faa78c8793a', 'note10/device_test/v130_handoff_core.h': 'f424e9c6db1641d54e052ac14f2a0077016745d8aeb93c51d9941eaac53384de', 'note10/device_test/v130_iommu.inc': '25d3b471b5635af652993ae0601d5e42feb0da9fa4dafeb9dae7831433a61e81', 'note10/device_test/v130_kernel.c': '400169512de4299f5e125d605991903d84c862666455b6b9a849c72d703ab4b8', 'note10/device_test/v130_kernel_api.h': 'b88e4dc8d7b00839c9c3566237de7f298989f117e38351640e448f31f75a6770', 'note10/device_test/v130_loader.c': '4fd191de634f4d6be070253e47e811518ce979a54d926d53bb3bfd8f2a1db10b', 'note10/device_test/v130_package.py': '7c12214b4a27c0ec8a5dd25c89adc74e39c135aa44816ea0a517a1ccc851e3df', 'note10/device_test/v130_payload.py': '45be7127de95f7a1ab60e3b0031d62bb8431b22906304da77af6e2e0c4fd1ac6', 'note10/device_test/v130_pl330.inc': '330583a2d4597c6f3d2d06ecca459c7379d898ab0f2fa3227824792d76940a21', 'note10/device_test/v130_platform.py': '62d727ab69abfa05e7427d5f332361ef52d25e537b26042b7d19465b5db2ec22', 'note10/device_test/v130_prepare.py': '168af92090a621f2886277b89b39c4c86c48fcfacc3d3c54c4c555dad71affbb', 'note10/device_test/v130_slot.py': '07c05bc1507120ec8a184457a416e4b716283f54403967ff1c024e65a8563317', 'note10/device_test/v130_sources.py': 'ce40fcf158008ed9185ecba56ed902e4b57b70f80cdadaa377e6767f2969aae7', 'note10/device_test/v130_timer.inc': '8cb43fb5600759875a9c7a76610b69af2b13daea4823e5f09ad398de74892a31', 'note10/device_test/v130_ufs.inc': '6ee7e2911f9ca2c46e94f6c47b3f445f33c517c3ded28fdca1fc3e13ea5158b0', 'note10/device_test/v130_usb.inc': '83ed2649607d4806bd77fce0f0a56e510ed5cdbd71079d458c5150a026ce1e02', 'note10/device_test/v130_usb_gadget.inc': 'f4ffc9f17d49d6b5a749ca4a39ff1aec2b2b959d6dae81d7e282ac014bd17b19', 'note10/device_test/test_v130_handoff.py': 'c878db51459f2461289f41064c5c51f27966d95c45fe0e29552bbb907228a1b5', 'note10/xnu26/boot_adt.py': 'b64ceac3651957485e734ef9053f368f9238adb8d88b2adc5e5622c7ff974b33', '.github/workflows/note10-v130-actual-xnu.yml': 'fc78e86a052cd455a151a6b5148edf91d9d4a6376edc6c621cde558c9269be16'}
RETAINED_SYNTHETIC_RESULT_SHA256 = 'd0766c39b59380bda49ac12d9320e06db40ffc39dd1568c7f9436df27b14dc72'
DELTA_SCOPE = 'v130-pid1-event-write-return-only'
DELTA_FILES = ('note10/device_test/v130_loader.c','note10/device_test/v130_build.py','note10/device_test/test_v130_pid1_write_return.py')


def continuation_context(row,current):
    if (not isinstance(row,dict) or set(row)!={'schema','scope','passed','retained_source_commit','retained_NEW_PASS','delta_NEW_PASS','source_sha256'} or
        row['schema']!='note10-v130-public-continuation-pass-v1' or row['scope']!=DELTA_SCOPE or row['passed'] is not True or
        row['retained_source_commit']!=RETAINED_SOURCE_COMMIT or row['source_sha256']!=current):
        raise ValueError('versioned continuation source binding differs')
    old=row['retained_NEW_PASS'];delta=row['delta_NEW_PASS']
    if (not isinstance(old,dict) or set(old)!={'schema','scope','passed','synthetic_result_sha256','source_sha256'} or
        old['schema']!='note10-v130-public-new-pass-v1' or old['scope']!='v130-owned-xnu-handoff-new-only' or old['passed'] is not True or
        old['source_sha256']!=RETAINED_SOURCE_SHA256 or old['synthetic_result_sha256']!=RETAINED_SYNTHETIC_RESULT_SHA256):
        raise ValueError('immutable original231cd13 synthetic PASS must be retained verbatim')
    if set(current)!=set(RETAINED_SOURCE_SHA256)|set(DELTA_FILES) or any(current[k]!=pin for k,pin in RETAINED_SOURCE_SHA256.items() if k not in DELTA_FILES):
        raise ValueError('unapproved source changed outside the three-file event-return delta')
    if (not isinstance(delta,dict) or set(delta)!={'schema','scope','passed','result_sha256','source_sha256'} or
        delta['schema']!='note10-v130-event-return-delta-pass-v1' or delta['scope']!=DELTA_SCOPE or delta['passed'] is not True or
        delta['source_sha256']!={name:current[name] for name in DELTA_FILES}):
        raise ValueError('NEW event-return delta PASS/source binding differs')
    hexid(delta['result_sha256']);return row


def pass_context(encoded):
    raw=base64.b64decode(encoded,validate=True)
    if len(raw)>32768:raise ValueError('bounded public continuation PASS metadata required')
    return continuation_context(json.loads(raw),source_pins())


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
        build_evidence_id=identity,retained_NEW_PASS=retained['retained_NEW_PASS'],delta_NEW_PASS=retained['delta_NEW_PASS'],
        continuation_source_binding=dict(schema=retained['schema'],scope=retained['scope'],retained_source_commit=retained['retained_source_commit'],current_source_sha256=retained['source_sha256']),
        old_tests_replayed=0,execution_slot_enabled=False,
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
