"""Linux CI build of a pinned public d2x kernel with legacy kexec enabled.

Build feasibility only. No phone access, image packaging or deployment.
Uses the public defconfig, never a private device capture.
"""
import hashlib
import argparse
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
COMMIT = '55f042627bb7030c93550faafa117674d32b21d1'
REPOSITORY = 'corsicanu/android_kernel_samsung_universal9820'
OUT = ROOT / 'note10/private/handoff-kernel'


def main(caps=False,reserve=False,window_access=False,xnu_payload=None,xnu_manifest=None,cpu_cache=False,pm_timer=False):
    if not sys.platform.startswith('linux'): raise RuntimeError('Linux CI host required')
    if os.environ.get('PLATFORM_VERSION')!='11' or os.environ.get('ANDROID_MAJOR_VERSION')!='r':
        raise ValueError('Pinned Samsung build requires PLATFORM_VERSION=11 and ANDROID_MAJOR_VERSION=r')
    if reserve and not caps:raise ValueError('Reservation diagnostic requires caps/initramfs handling')
    if window_access and not reserve:raise ValueError('Window access requires the same-boot reservation diagnostic')
    if (xnu_payload is None)!=(xnu_manifest is None):raise ValueError('XNU payload and manifest must be paired')
    if xnu_payload is not None and not window_access:raise ValueError('XNU staging requires the opt-in window diagnostic')
    if cpu_cache and xnu_payload is None:raise ValueError('CPU/cache roundtrip requires XNU data staging')
    if pm_timer and not cpu_cache:raise ValueError('PM/timer requires CPU/cache batch')
    OUT.mkdir(parents=True,exist_ok=True)
    report = {'source_repository':REPOSITORY,'source_commit':COMMIT,
              'platform_version':os.environ['PLATFORM_VERSION'],
              'android_major_version':os.environ['ANDROID_MAJOR_VERSION'],
              'public_defconfig':'exynos9820-d2x_defconfig','build_passed':False,
              'device_operations':[],'deployment_ready':False,'device_boot_tested':False,
              'scope':'Linux shutdown-host build feasibility; not XNU or an installable image',
              'builtin_cpu_diagnostic':caps,
              'commands':[]}
    def run(arguments, log_name, timeout=120):
        report['commands'].append(arguments)
        print(log_name,flush=True)
        with (OUT/log_name).open('wb') as log:
            result=subprocess.run(arguments,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
        if result.returncode:raise RuntimeError(log_name+' failed; see saved build diagnostics')
    try:
        archive=OUT/'source.tar.gz'
        url='https://codeload.github.com/'+REPOSITORY+'/tar.gz/'+COMMIT
        print('Fetching pinned public kernel source',flush=True)
        with urllib.request.urlopen(url,timeout=90) as response, archive.open('wb') as target:
            total=0
            while chunk:=response.read(1024*1024):
                total+=len(chunk)
                if total>1536*1024*1024:raise ValueError('Source archive exceeds size cap')
                target.write(chunk)
        digest=hashlib.file_digest(archive.open('rb'),'sha256').hexdigest()
        report['source_archive_sha256']=digest
        parent=OUT/'source';parent.mkdir(exist_ok=True)
        expected='android_kernel_samsung_universal9820-'+COMMIT
        with tarfile.open(archive) as tree:
            members=tree.getmembers()
            if sum(m.size for m in members)>5*1024**3:raise ValueError('Expanded source exceeds size cap')
            for member in members:
                path=Path(member.name)
                if path.is_absolute() or '..' in path.parts or path.parts[0]!=expected:
                    raise ValueError('Unexpected kernel archive path')
            tree.extractall(parent,filter='data')
        source=parent/expected;objects=OUT/'objects'
        # The shipped-blob rule uses an object-relative .incbin path even
        # when make's VPATH found the real binary in the source tree. Prefer
        # that existing source binary, leaving generated .ihex outputs alone.
        firmware_make=source/'firmware/Makefile'
        firmware_text=firmware_make.read_text()
        old='$(call cmd,fwbin,$(patsubst %.gen.S,%,$@))'
        new='$(call cmd,fwbin,$(if $(wildcard $(srctree)/$(patsubst %.gen.S,%,$@)),$(srctree)/$(patsubst %.gen.S,%,$@),$(patsubst %.gen.S,%,$@)))'
        if firmware_text.count(old)!=1:raise ValueError('Unexpected pinned firmware rule')
        firmware_make.write_text(firmware_text.replace(old,new))
        report['firmware_rule_source_path_fix']=True
        report['firmware_makefile_patched_sha256']=hashlib.sha256(firmware_make.read_bytes()).hexdigest()
        if caps:
            import shutil
            # Samsung normal boot can append skip_initramfs. This diagnostic
            # must use the supplied TWRP initrd rather than mount Android root.
            initramfs=source/'init/initramfs.c'
            initramfs_text=initramfs.read_text()
            original_skip='\tdo_skip_initramfs = 1;'
            if initramfs_text.count(original_skip)!=1:
                raise ValueError('Unexpected pinned skip_initramfs parser')
            initramfs.write_text(initramfs_text.replace(original_skip,
                '\tpr_info("N10CAP1: keeping diagnostic initramfs\\n");'))
            report['diagnostic_preserves_external_initramfs']=True
            report['initramfs_patched_sha256']=hashlib.sha256(initramfs.read_bytes()).hexdigest()
            driver=Path(__file__).with_name('linux_caps.c')
            target=source/'drivers/misc/note10_handoff_caps.c'
            if target.exists():raise ValueError('Unexpected existing diagnostic source')
            shutil.copyfile(driver,target)
            with (source/'drivers/misc/Makefile').open('a') as build:
                build.write('\n# Note10 privileged capability diagnostic; no handoff execution\nobj-y += note10_handoff_caps.o\n')
            report['diagnostic_source_sha256']=hashlib.sha256(driver.read_bytes()).hexdigest()
        defconfig=source/'arch/arm64/configs/exynos9820-d2x_defconfig'
        if reserve:
            from prepare_reservation_kernel import prepare
            report.update(prepare(source,OUT,run,window_access=window_access,
                                  xnu_payload=xnu_payload,xnu_manifest=xnu_manifest,cpu_cache=cpu_cache,pm_timer=pm_timer))
            if window_access:report['scope']='Linux same-boot reserved RAM pattern/readback diagnostic; no XNU branch'
            if xnu_payload is not None:
                report['scope']='Experimental XNU memory-image data staging and SHA256 readback in this boot reservation; no XNU branch'
            if cpu_cache:
                report['scope']='Cached XNU data staging plus Linux CPU offline/online, cache maintenance and per-CPU readback; no DMA/MMU handoff'
        if pm_timer:
            report['scope']='Timer restoration before devices-only PM test, settled boot and bounded EBUSY retries; low-level entry blocked; no XNU branch'
        report['public_defconfig_sha256']=hashlib.sha256(defconfig.read_bytes()).hexdigest()
        make=['make','-C',str(source),'O='+str(objects),'ARCH=arm64',
              'CC=clang-14','CROSS_COMPILE=aarch64-linux-gnu-',
              'CLANG_TRIPLE=aarch64-linux-gnu-','CROSS_COMPILE_ARM32=arm-linux-gnueabi-',
              # This older Makefile derives --prefix from elfedit's directory.
              # Debian keeps prefixed tools in /usr/bin and unprefixed cross
              # aliases here; using /usr/bin would select the x86 assembler.
              'GCC_TOOLCHAIN_DIR=/usr/aarch64-linux-gnu/bin/',
              # Avoid DWARF5 forms unsupported by this source's objdump-based
              # scripts. Do not disable -Werror globally: cc-option probes
              # must reject unsupported compiler switches correctly.
              'HOSTCC=gcc','HOSTCFLAGS=-Wno-error=deprecated-declarations','KCFLAGS=-gdwarf-4']
        run([*make,'exynos9820-d2x_defconfig'],'01-configure.log')
        config=objects/'.config'
        original=config.read_bytes();(OUT/'public-baseline.config').write_bytes(original)
        run([str(source/'scripts/config'),'--file',str(config),'--enable','KEXEC',
             '--set-str','LOCALVERSION','-note10-reserve-pc' if reserve else '-note10-handoff-pc','--disable','LOCALVERSION_AUTO'],
            '02-enable-kexec.log')
        if reserve:
            run([str(source/'scripts/config'),'--file',str(config),'--set-str','INITRAMFS_SOURCE',
                 str(OUT/'initramfs.cpio'),'--set-str','CMDLINE','rdinit=/init',
                 '--disable','CMDLINE_FROM_BOOTLOADER','--disable','CMDLINE_FORCE',
                 '--enable','CMDLINE_EXTEND','--enable','INITRAMFS_FORCE'],'02-initramfs.log')
        run([*make,'olddefconfig'],'03-olddefconfig.log')
        configured=config.read_text()
        required=('CONFIG_KEXEC=y','CONFIG_KEXEC_CORE=y','CONFIG_PM_SLEEP_SMP=y','CONFIG_ARM64_4K_PAGES=y')
        (OUT/'handoff.config').write_bytes(config.read_bytes())
        if reserve:required+=('CONFIG_INITRAMFS_FORCE=y','CONFIG_CMDLINE_EXTEND=y','CONFIG_CMDLINE="rdinit=/init"')
        if xnu_payload is not None:required+=('CONFIG_CRYPTO=y','CONFIG_CRYPTO_HASH=y','CONFIG_CRYPTO_SHA256=y')
        if cpu_cache:required+=('CONFIG_HOTPLUG_CPU=y','CONFIG_SMP=y','CONFIG_PM_SLEEP_SMP=y')
        if pm_timer:required+=('CONFIG_SUSPEND=y','CONFIG_PM_SLEEP_DEBUG=y','CONFIG_PM_DEBUG=y')
        missing=[line for line in required if line not in configured.splitlines()]
        if missing:raise ValueError('Required Kconfig options missing: '+', '.join(missing))
        report['effective_config_sha256']=hashlib.sha256(config.read_bytes()).hexdigest()
        if caps:run([*make,'drivers/misc/note10_handoff_caps.o'],'04-caps-object.log')
        if reserve:run([*make,'arch/arm64/mm/init.o'],'04-reservation-object.log')
        run([*make,'-j'+str(min(os.cpu_count() or 2,8)),'Image'],'04-build.log',timeout=1500)
        image=objects/'arch/arm64/boot/Image'
        with image.open('rb') as stream:header=stream.read(64)
        if len(header)!=64 or header[56:60]!=b'ARM\x64':raise ValueError('Missing ARM64 Image header')
        text_offset,image_size,flags=struct.unpack_from('<3Q',header,8)
        # image_size is the in-memory footprint and can include BSS; it is
        # not required to fit in the on-disk Image byte count.
        if not 0<image_size<=256*1024*1024:raise ValueError('Invalid Image memory footprint')
        target=OUT/'Image'
        # Copy only the completed output; retain object-tree logs for diagnosis.
        import shutil
        shutil.copyfile(image,target)
        if reserve and target.read_bytes().count(report['reservation_evidence_id'].encode())!=1:
            raise ValueError('Unique reservation evidence ID not embedded in Image')
        if xnu_payload is not None:
            from prepare_reservation_kernel import verify_embedded_init
            embedded=verify_embedded_init(target.read_bytes(),(OUT/'initramfs.cpio').read_bytes())
            report['xnu_payload_initramfs_verified']=embedded['embedded_initramfs_verified']
            if b'N10XNU1' not in target.read_bytes():raise ValueError('XNU stage evidence marker missing from Linux Image')
        if cpu_cache and any(marker not in target.read_bytes() for marker in (b'N10QUI1',b'N10CPU2')):
            raise ValueError('CPU/cache evidence markers missing from Linux Image')
        if pm_timer and any(marker not in target.read_bytes() for marker in (b'N10PMT1',b'N10TMR1',b'N10BND1',b'N10TRY1')):
            raise ValueError('PM/timer evidence markers missing from Linux Image')
        report.update(build_passed=True,image_size=target.stat().st_size,
                      image_sha256=hashlib.file_digest(target.open('rb'),'sha256').hexdigest(),
                      arm64_text_offset=hex(text_offset),arm64_header_image_size=image_size,arm64_flags=hex(flags))
        for name,command in (('compiler',['clang-14','--version']),('linker',['aarch64-linux-gnu-ld','--version'])):
            report[name]=subprocess.check_output(command,text=True).splitlines()[0]
    except Exception as error:
        report['failure']=str(error)
        raise
    finally:
        (OUT/'build-result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps({key:report[key] for key in ('build_passed','deployment_ready','source_commit')}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--caps',action='store_true',help='Include built-in per-CPU printk diagnostic for a future manual boot')
    parser.add_argument('--reserve',action='store_true',help='Early XNU RAM reservation diagnostic with original built-in idle PID1')
    parser.add_argument('--window-access',action='store_true',help='Opt-in write/read/scrub of this boot\'s checked reservation; no XNU execution')
    parser.add_argument('--xnu-payload',type=Path,help='Verified experimental XNU kernel.mem for data-only RAM staging')
    parser.add_argument('--xnu-payload-manifest',type=Path,help='Hash-bound manifest from materialize_stage_payload.py')
    parser.add_argument('--cpu-cache',action='store_true',help='Opt-in CPU offline/online, cache maintenance and per-CPU payload reads')
    parser.add_argument('--pm-timer',action='store_true',help='Devices-only PM test and restored per-CPU event-stream normalization')
    args=parser.parse_args();main(caps=args.caps,reserve=args.reserve,window_access=args.window_access,
                                  xnu_payload=args.xnu_payload,xnu_manifest=args.xnu_payload_manifest,cpu_cache=args.cpu_cache,pm_timer=args.pm_timer)
