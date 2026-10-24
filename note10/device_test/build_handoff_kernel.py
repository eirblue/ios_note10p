"""Linux CI build of a pinned public d2x kernel with legacy kexec enabled.

Build feasibility only. No phone access, image packaging or deployment.
Uses the public defconfig, never a private device capture.
"""
import hashlib
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


def main():
    if not sys.platform.startswith('linux'): raise RuntimeError('Linux CI host required')
    OUT.mkdir(parents=True,exist_ok=True)
    report = {'source_repository':REPOSITORY,'source_commit':COMMIT,
              'public_defconfig':'exynos9820-d2x_defconfig','build_passed':False,
              'device_operations':[],'deployment_ready':False,'device_boot_tested':False,
              'scope':'Linux shutdown-host build feasibility; not XNU or an installable image',
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
        defconfig=source/'arch/arm64/configs/exynos9820-d2x_defconfig'
        report['public_defconfig_sha256']=hashlib.sha256(defconfig.read_bytes()).hexdigest()
        make=['make','-C',str(source),'O='+str(objects),'ARCH=arm64',
              'CC=clang-14','CROSS_COMPILE=aarch64-linux-gnu-',
              'CLANG_TRIPLE=aarch64-linux-gnu-','CROSS_COMPILE_ARM32=arm-linux-gnueabi-',
              # This older Makefile derives --prefix from elfedit's directory.
              # Debian keeps prefixed tools in /usr/bin and unprefixed cross
              # aliases here; using /usr/bin would select the x86 assembler.
              'GCC_TOOLCHAIN_DIR=/usr/aarch64-linux-gnu/bin/',
              'HOSTCC=gcc','HOSTCFLAGS=-Wno-error=deprecated-declarations','KCFLAGS=-Wno-error']
        run([*make,'exynos9820-d2x_defconfig'],'01-configure.log')
        config=objects/'.config'
        original=config.read_bytes();(OUT/'public-baseline.config').write_bytes(original)
        run([str(source/'scripts/config'),'--file',str(config),'--enable','KEXEC',
             '--set-str','LOCALVERSION','-note10-handoff-pc','--disable','LOCALVERSION_AUTO'],
            '02-enable-kexec.log')
        run([*make,'olddefconfig'],'03-olddefconfig.log')
        configured=config.read_text()
        required=('CONFIG_KEXEC=y','CONFIG_KEXEC_CORE=y','CONFIG_PM_SLEEP_SMP=y','CONFIG_ARM64_4K_PAGES=y')
        if not all(line in configured.splitlines() for line in required):
            raise ValueError('Requested kexec dependencies did not survive Kconfig')
        (OUT/'handoff.config').write_bytes(config.read_bytes())
        report['effective_config_sha256']=hashlib.sha256(config.read_bytes()).hexdigest()
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


if __name__=='__main__':main()
