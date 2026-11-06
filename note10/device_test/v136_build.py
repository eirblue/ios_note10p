"""One fresh generic disabled v136 Image. No private XNU/platform input is accepted."""
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
from v130_contract import ROOT,BOOT_LIMIT,sha,digest,read,private,hexid,save,DISABLED
from v130_sources import materialize,INPUT128,INPUT129
from v130_archive import COMMIT,ARCHIVE_SHA,DEFCONFIG,acquire,extract
from v130_slot import generic
import v136_prepare as prepare
from v135_build import SETTINGS as RETAINED_SETTINGS,FILES as RETAINED_FILES,continuation as retained_continuation
HERE=Path(__file__).resolve().parent
WORKFLOW='.github/workflows/note10-v136-npu-terminal.yml'
BUILD_SCHEMA='note10-v136-generic-xnu-host-v1'
SCOPE='v136-npu-terminal-new-only'
RETAINED_COMMIT='f9f1dc7e8f5520b5f9902c7c939b8dc87e3aaeed'
RETAINED_SOURCE_SHA256={'note10/device_test/v130_archive.py': 'bc49ffef72f73769de77a55432253f57f14d20433933ac56570f0ebfc3a1bce4', 'note10/device_test/v130_build.py': 'fc19d71224223a805daae73d5958a79eddc4577a6d09598e537aea07d29209d3', 'note10/device_test/v130_contract.py': 'd3336dccb8edf2366d4cc8233cd83d18b27f4d65c7dd3a3627807ddd0858c929', 'note10/device_test/v130_cycle.py': 'b1a5dd876b02c3680a1f789e19d21d6cf5cd4750a39241b20eb1a7adb5d6f360', 'note10/device_test/v130_dmaengine.inc': '4c1be828c50a1e42ad169afac07a32533680009caf1f2b6ad64f8517af9ba7c7', 'note10/device_test/v130_fixture.c': '1895ee818cf274e9e9d134f0c38658f83392f689004f0e3aa180e9396f6035c5', 'note10/device_test/v130_gate_core.h': '12b36033bda6976deba188099b5b6d1bd32748e84ea2edd796a4463faca7f543', 'note10/device_test/v130_gic.inc': 'ace8aed4e9f6880ef1744602b366c2dddbbd51a29d5b3414e13f7bd01d7276ee', 'note10/device_test/v130_handoff_core.c': '4cf36f2a3e95c537f95db521f0b1626f303bf85c2ee1071624182faa78c8793a', 'note10/device_test/v130_handoff_core.h': 'f424e9c6db1641d54e052ac14f2a0077016745d8aeb93c51d9941eaac53384de', 'note10/device_test/v130_iommu.inc': '25d3b471b5635af652993ae0601d5e42feb0da9fa4dafeb9dae7831433a61e81', 'note10/device_test/v130_kernel.c': 'e6a4747d461670a517059b75f211bd500bcbe2a69c26044c67178dd7c356e3f1', 'note10/device_test/v130_kernel_api.h': 'aa61dfffd257e94e2cb84a00085635a5133736512729c252cd680e73eefba77d', 'note10/device_test/v130_loader.c': '2663f22b3109b17f300fd80d2999b6aa18f052891b6157c63c5c020c69bc9b55', 'note10/device_test/v130_package.py': '7c12214b4a27c0ec8a5dd25c89adc74e39c135aa44816ea0a517a1ccc851e3df', 'note10/device_test/v130_payload.py': '45be7127de95f7a1ab60e3b0031d62bb8431b22906304da77af6e2e0c4fd1ac6', 'note10/device_test/v130_pl330.inc': '330583a2d4597c6f3d2d06ecca459c7379d898ab0f2fa3227824792d76940a21', 'note10/device_test/v130_platform.py': '62d727ab69abfa05e7427d5f332361ef52d25e537b26042b7d19465b5db2ec22', 'note10/device_test/v130_prepare.py': 'a5c2673f41ec55c9797d239c3550c12a95a5c3f6caa346f20c16911be64ecbee', 'note10/device_test/v130_slot.py': '07c05bc1507120ec8a184457a416e4b716283f54403967ff1c024e65a8563317', 'note10/device_test/v130_sources.py': 'ce40fcf158008ed9185ecba56ed902e4b57b70f80cdadaa377e6767f2969aae7', 'note10/device_test/v130_timer.inc': '8cb43fb5600759875a9c7a76610b69af2b13daea4823e5f09ad398de74892a31', 'note10/device_test/v130_ufs.inc': 'bfdf905f17ad2d35c966444f5d235a42ed5eb09ce0f6f52a7fea74fadc7551ac', 'note10/device_test/v130_usb.inc': '83ed2649607d4806bd77fce0f0a56e510ed5cdbd71079d458c5150a026ce1e02', 'note10/device_test/v130_usb_gadget.inc': 'f4ffc9f17d49d6b5a749ca4a39ff1aec2b2b959d6dae81d7e282ac014bd17b19', 'note10/device_test/test_v130_handoff.py': 'c878db51459f2461289f41064c5c51f27966d95c45fe0e29552bbb907228a1b5', 'note10/device_test/test_v130_pid1_write_return.py': 'b92c4658fc282d33364846b8983e4753e99a66a5b98133927ee4807244549b3d', 'note10/device_test/test_v130_return_order_ufs.py': '733fa71bd4bf8f2ad1f2e9598fd7fa0205aa09a3ba4f5fde98d140e89c2846c3', 'note10/device_test/test_v130_composite_include_contract.py': '3739093076c9451ded680dde711a757232ceac7a16f6e3c445d876aecf683a78', 'note10/device_test/test_v130_gadget_link_contract.py': '0c1a762f8558c9c34dac3cf7122dbebb848190e8697659e206efdf818051a279', 'note10/device_test/test_v130_host_power_contract.py': 'a95f6795949b54da7702682ce2786910b159ad9fda9bd63f1ff6580926666298', 'note10/xnu26/boot_adt.py': 'b64ceac3651957485e734ef9053f368f9238adb8d88b2adc5e5622c7ff974b33', '.github/workflows/note10-v130-actual-xnu.yml': 'fc78e86a052cd455a151a6b5148edf91d9d4a6376edc6c621cde558c9269be16', 'note10/device_test/v131_prepare.py': 'c27511dc9958ff2da20a892c9e39779305f2f613da26d4ac0e6374c97cfbdbae', 'note10/device_test/v131_dma_registry.inc': '83cbc2d1f2f9cf7030f1458060467d1a4bb3dc34ac08648f495f60152bf27221', 'note10/device_test/v131_ufs.inc': '8acdda2a872209ab8ee149eac50e5bd4201c6559b192d02bff31fbb524d920a7', 'note10/device_test/v131_iommu.inc': 'cdd345fce481e15bf012f116b0e2d19e936e9d7e4ffaa544995fbaeaa9a90d90', 'note10/device_test/v131_build.py': 'dd97630bbc648c0c85e79a4ae62dc9ce0d822710a4e5da49f48f1c5745a2c5d2', 'note10/device_test/v131_package.py': '733309b4ad5872e602a3b9655860243588bb685c456d09bc3cf1d543acd3f8d6', 'note10/device_test/v131_cycle.py': 'be39313d2e828537f7aecc7eb8096c3b291b45a7d73b876bd57a269516a8886f', 'note10/device_test/test_v131_terminal_dma.py': 'e9c263656da06eca9b4dc8fe3b330dd0f016ea4a639c8e41207916147585d4b9', '.github/workflows/note10-v131-terminal-dma.yml': 'af4d20a2647950eff6dcecb30483b5c828c8c34052904de7182753214092b2e2', 'note10/device_test/v132_prepare.py': 'f028e81cb6de9c432586203dace09068d0f4b4f452ca3608c9211e756e5030fd', 'note10/device_test/v132_g2d.inc': '4e21c5c44e2d6df37c7ab84f8f042f020519a9faeef9d9d7a9a4778ed8277cca', 'note10/device_test/v132_build.py': 'c59516dda1ce620872ccc6208d8454c4cfa7fa774b3bb4d78cae8dd0a216f5a4', 'note10/device_test/v132_package.py': '2ef7f89368f56f45690a7d7cd16fc4c25418f3fbeba3578241805c7419f4747a', 'note10/device_test/v132_cycle.py': '36e43099dc0ee9bea830d9a20cd775503f28e528db984233ef22ea0bfba33cb1', 'note10/device_test/test_v132_g2d_terminal.py': '93be9d4de1ec16a2f5c65de21ef039742a84d72b81989fb34765f6fb848d3dac', '.github/workflows/note10-v132-g2d-terminal.yml': 'ab6d7660801c6040d88323f10c913e75835bc5b94874bb56b493742be512d00f', 'note10/device_test/v133_prepare.py': '501dada9b8c723fa2354e67d86975b14f15712a8b9b87dbcd6b58676589e246f', 'note10/device_test/v133_score.inc': '7528c6fc343351d82addaa1ed4624c541264c7c3031c5a205a348042b31518e9', 'note10/device_test/v133_build.py': 'd585ceb1ef0f5f76ac5ef2afcbc0bfc3451dee21b8ced9407fb9d84b505f41c2', 'note10/device_test/v133_package.py': 'e70d0a8e82f955d4fb6002acbf2379916147b932061219d27c2242010e2ce948', 'note10/device_test/v133_cycle.py': 'c00d1e08e99be5be3398c3b1a8c00d91799b36119475f35d0f9a39e5f1484b4a', 'note10/device_test/test_v133_score_terminal.py': '4fbca726906fcf48bd6de486e496e5536c7bfc795384ba17df13f070f371b93d', '.github/workflows/note10-v133-score-terminal.yml': '4db7d67968594316b90aa3e1aa509e1095d3b95556c05f896f4b723023021057', 'note10/device_test/v135_prepare.py': '038397ee7fafd5c22df06a262d19513a42bd8cde5c97eff9048d09d4ae80f30d', 'note10/device_test/v135_score_reset.inc': '0c853ca0a2e6d482c24c1aea6a2787e0e4470bff183806327b6880aad6701ba7', 'note10/device_test/v135_build.py': '9cf02d7581ee279cc301b4e2dd1a6677f52a0ee81b0d1c8da02b129a7cb4fec7', 'note10/device_test/v135_package.py': '7576989fd4f40a2fd03f81a5a8bc0e2b58b5d2f13755239fe38107a97cb5104b', 'note10/device_test/v135_cycle.py': '824a6e1c1ba2126033400d0f2bf8fc6406d73bece38e5bfe46ea8e4ab7eb7540', 'note10/device_test/v135_metadata.py': 'd631d04e6f7a4cf1f48e6aeae53be8ef7a48599f4badf08091391fde96e218a9', 'note10/device_test/test_v135_score_reset.py': '0da4c43f87b5bea76a037caee67e1d5c1fc146509e3f525f7440a89425fa018b', '.github/workflows/note10-v135-score-ts-reset.yml': 'e4b5f197a5e8f7916d2b3ffaea98e0c5e5c80117e7a3017e554ac555f828f8fa'}
RETAINED_CONTEXT_SHA256='c4d9865f0f367b6ab330d254f0fa09c2309b898c8741ac6ffd16f03588c1a8d9'
NEW_NAMES=('v136_prepare.py','v136_terminal.h','v136_cal.inc','v136_npu.inc','v136_build.py','v136_package.py','v136_cycle.py','test_v136_terminal.py')
NEW_FILES=tuple('note10/device_test/'+name for name in NEW_NAMES)+(WORKFLOW,)
FILES=tuple(RETAINED_FILES)+NEW_FILES
SETTINGS=dict(RETAINED_SETTINGS,EXYNOS_SCORE='y',EXYNOS_SCORE_V3='y',EXYNOS_SCORE_V2='n',EXYNOS_SCORE_FPGA='n',SOC_EXYNOS9820_EVT0='n',COMMON_CLK='y',PM='y',SOC_EXYNOS9820='y',PM_DEVFREQ='y',EXYNOS_IOVMM='y',LOCALVERSION='"-v136-npu-terminal"',EXYNOS_NPU='y',NPU_HARDWARE='y',NPU_INTERFACE='y',NPU_LOOPBACK='n',NPU_ZEBU_EMULATION='n',NPU_ZEBU_SYSMMU='y',EXYNOS_SOC_NAME='"9820"',PMUCAL='y',PMUCAL_DBG='y',VISION_UNITTEST='y')


def source_pins():return {name:sha(ROOT/name) for name in FILES}


def continuation(row,current):
    keys={'schema','scope','passed','retained_source_commit','retained_terminal_PASS','delta_NEW_PASS','source_sha256'}
    if (not isinstance(row,dict) or set(row)!=keys or row['schema']!='note10-v136-public-terminal-continuation-v1' or
        row['scope']!=SCOPE or row['passed'] is not True or row['retained_source_commit']!=RETAINED_COMMIT or row['source_sha256']!=current):
        raise ValueError('exact successor NEW SCORE terminal PASS required')
    if set(current)!=set(RETAINED_SOURCE_SHA256)|set(NEW_FILES) or any(current.get(k)!=v for k,v in RETAINED_SOURCE_SHA256.items()):
        raise ValueError('retained source64 changed or successor SCORE source boundary differs')
    prior=row['retained_terminal_PASS'];retained_continuation(prior,RETAINED_SOURCE_SHA256)
    if digest(json.dumps(prior,sort_keys=True,separators=(',',':')).encode())!=RETAINED_CONTEXT_SHA256:
        raise ValueError('immutable accepted135 PASS context changed')
    delta=row['delta_NEW_PASS']
    if (not isinstance(delta,dict) or set(delta)!={'schema','scope','passed','result_sha256','source_sha256'} or
        delta['schema']!='note10-v136-npu-terminal-pass-v1' or delta['scope']!=SCOPE or delta['passed'] is not True or
        delta['source_sha256']!={name:current[name] for name in NEW_FILES}):
        raise ValueError('NEW SCORE terminal result binding differs')
    hexid(delta['result_sha256']);return row


def pass_context(encoded):
    from v135_metadata import decode_public
    return continuation(decode_public(encoded),source_pins())


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',required=True,type=Path);p.add_argument('--archive',type=Path)
    p.add_argument('--jobs',type=int,default=4);p.add_argument('--expected-source-head',required=True)
    p.add_argument('--passed-new-test-context',required=True);a=p.parse_args()
    out=private(a.output);work=out.with_name(out.name+'-workspace');hexid(a.expected_source_head,40)
    if not sys.platform.startswith('linux') or out.exists() or work.exists() or not 1<=a.jobs<=8:p.error('one fresh Linux build required')
    ci={k:os.environ.get(k,'') for k in ('GITHUB_SHA','GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT','GITHUB_JOB','GITHUB_WORKFLOW_REF','GITHUB_WORKFLOW_SHA','GITHUB_REPOSITORY')}
    if (ci['GITHUB_SHA']!=a.expected_source_head or ci['GITHUB_WORKFLOW_SHA']!=a.expected_source_head or
        ci['GITHUB_RUN_ATTEMPT']!='1' or
        ci['GITHUB_REPOSITORY']!='eirblue/ios_note10p' or ci['GITHUB_JOB']!='v136-npu-terminal' or
        not ci['GITHUB_WORKFLOW_REF'].startswith('eirblue/ios_note10p/'+WORKFLOW+'@')):p.error('exact reviewed source/workflow required')
    prepare.profile(SETTINGS)
    retained=pass_context(a.passed_new_test_context);pins=source_pins()
    identity=digest(json.dumps(dict(source=pins,ci=ci),sort_keys=True).encode())[:32]
    archive=a.archive.absolute() if a.archive else out.with_name(out.name+'-kernel-input.tar.gz')
    if archive.is_symlink() or archive.is_relative_to(out) or archive.is_relative_to(work):p.error('external ordinary source archive required')
    out.mkdir(parents=True);commands=[]
    result=dict(schema=BUILD_SCHEMA,version='v136',passed=False,ci_context=ci,source_sha256=pins,
        immutable128_source=INPUT128,immutable129_source=INPUT129,kernel_commit=COMMIT,kernel_archive_sha256=ARCHIVE_SHA,
        build_evidence_id=identity,retained_terminal_PASS=retained['retained_terminal_PASS'],delta_NEW_PASS=retained['delta_NEW_PASS'],
        retained_source_commit=RETAINED_COMMIT,retained_source_sha256=RETAINED_SOURCE_SHA256,
        native_include_compile_status='pending',native_link_validation_status='pending',
        old_tests_replayed=0,execution_slot_enabled=False,private_payload_uploaded=False,hardware_package_emitted=False,
        physical_ready=False,device_operations=[])
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
        loader=(HERE/'v130_loader.c').read_bytes().replace(b'N10XNU130',b'N10XNU135')
        (out/'v136_loader.c').write_bytes(loader)
        result['PID1_source_sha256']=digest(loader)
        run(['aarch64-linux-gnu-gcc','-std=c11','-O2','-static','-fno-stack-protector','-Wall','-Wextra','-Werror',
            '-I',HERE,'-I',out,'-Wl,--build-id=none',out/'v136_loader.c',HERE/'v130_handoff_core.c','-o',out/'minimal-init.elf'],'00-new-PID1')
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
        run([*make,'-k','V=1','-j'+str(a.jobs),'Image'],'03-new-Image',5400)
        result['native_include_compile_status']='compiled-by-this-CI'
        result['native_link_validation_status']='linked-by-this-CI'
        image=(objects/'arch/arm64/boot/Image').read_bytes();(out/'Image').write_bytes(image)
        symbols=(objects/'System.map').read_text()
        addresses={parts[2]:int(parts[0],16) for line in symbols.splitlines() if len(parts:=line.split())==3 and re.fullmatch('[0-9a-fA-F]+',parts[0])}
        if (image[56:60]!=b'ARM\x64' or len(image)>BOOT_LIMIT-32768 or image.count(archive_data)!=1 or image.count(DISABLED)!=1 or
            addresses.get('__initramfs_start',-1)-addresses.get('_text',-2)!=image.find(archive_data)):
            raise ValueError('actual source-built raw CPIO/symbol/disabled Image geometry differs')
        offset=image.find(archive_data);layout=dict(initramfs_offset=offset,initramfs_bytes=len(archive_data),prefix_bytes=prefix,
            slot_offset=offset+prefix,slot_bytes=len(archive_data)-prefix,cycle_offset=image.find(DISABLED))
        shutil.copyfile(objects/'System.map',out/'System.map')
        objects_pins={}
        for name in ('arch/arm64/mm/init.o','arch/arm64/kernel/machine_kexec.o','arch/arm64/kernel/relocate_kernel.o',
            'kernel/kexec_core.o','kernel/reboot.o','init/main.o','init/initramfs.o','drivers/samsung/sec_reboot.o',
            'drivers/watchdog/s3c2410_wdt.o','drivers/irqchip/irq-gic.o','drivers/clocksource/arm_arch_timer.o',
            'drivers/usb/dwc3/core.o','drivers/usb/dwc3/gadget.o','drivers/scsi/ufs/ufshcd.o','drivers/scsi/ufs/ufs-exynos.o','drivers/iommu/exynos-iommu.o','drivers/dma/dmaengine.o','drivers/dma/pl330.o','drivers/gpu/exynos/g2d/g2d_drv.o','drivers/gpu/exynos/g2d/g2d_task.o','drivers/vision/score/score_device.o','drivers/vision/score/score_core.o','drivers/vision/score/hardware/v3/score_system.o','drivers/vision/score/hardware/v3/score_scq.o','drivers/soc/samsung/cal-if/cal-if.o','drivers/vision/npu/npu-device.o','drivers/vision/npu/npu-system.o','drivers/vision/npu/npu-protodrv.o','drivers/vision/npu/npu-debug.o','drivers/vision/npu/npu-util-memdump.o','drivers/vision/npu/npu-vertex.o','drivers/vision/npu/npu-log.o','drivers/vision/npu/npu-profile.o','drivers/vision/npu/npu-qos.o','drivers/vision/npu/npu-memory.o','drivers/vision/npu/interface/hardware/npu-interface.o'):
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
