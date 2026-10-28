"""Exercise prepare -> package propagation against a bound synthetic Image."""
import argparse, hashlib, json, shutil, struct, tempfile
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
import prepare_linux_boot as prep
import build_boot_test_packages as packages
from stage_phase2 import verify_packages
from pmu_failure_binding import MARKER, PACKAGE_SOURCES, validate as validate_failure
from pm_callbacks_binding import MARKERS as CALLBACKS
from pm_preconditions_binding import MARKERS as PRECONDITIONS
from pm_branch_binding import MARKERS as BRANCH

def sha(x): return hashlib.sha256(x).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--artifact',required=True);ap.add_argument('--output',required=True);args=ap.parse_args()
    src=Path(args.artifact);out=Path(args.output)
    build_at_start=json.loads((src/'build-result.json').read_text(encoding='utf8'))
    source_dir=Path(__file__).resolve().parent
    measured={n:sha((source_dir/n).read_bytes()) for n in PACKAGE_SOURCES}
    if build_at_start.get('pmu_failure_package_sources_sha256')!=measured:raise ValueError('Package sources changed since build report')
    out.mkdir(parents=True,exist_ok=False)
    names=('pm-preconditions-prepared','pm-branch-prepared','pmu-failure-prepared','pmu-failure-model','pmu-failure-binding-model')
    with tempfile.TemporaryDirectory(dir=prep.ROOT/'note10/private') as t:
        root=Path(t);art=root/'artifact';art.mkdir()
        for n in names:shutil.copytree(src/n,art/n)
        config=(src/'handoff.config').read_bytes();(art/'handoff.config').write_bytes(config)
        b=json.loads((src/'build-result.json').read_text(encoding='utf8'))
        # This fixture exercises packaging before the actual Image build is marked complete.
        # Only the isolated synthetic copy is marked successful; never modify the source report.
        b['build_passed']=True
        if b.get('xnu_payload_stage_diagnostic') is True:
            b['xnu_payload_initramfs_verified']=True  # synthetic embedded-init check is mocked below
        image=bytearray(128);image[56:60]=b'ARM\x64';struct.pack_into('<Q',image,8,0)
        image=bytes(image)+b'N10RET1'+b''.join(CALLBACKS+PRECONDITIONS+BRANCH)+MARKER
        (art/'Image').write_bytes(image);b['image_sha256']=sha(image);b['image_size']=len(image);b['effective_config_sha256']=sha(config)
        b['auto_return_diagnostic']=True;b['builtin_idle_init']=True;b['early_xnu_reservation']=True
        for name,key in (('minimal-init.elf','minimal_init_elf_sha256'),('initramfs.cpio','initramfs_cpio_sha256')):
            (art/name).write_bytes(b'fixture');b[key]=sha(b'fixture')
        backup=root/'backup';backup.mkdir();twrp=root/'twrp.img';twrp.write_bytes(b'recovery');mk=root/'mk.py';mk.write_bytes(b'mkboot')
        vb=bytearray(256);vb[:4]=b'AVB0';struct.pack_into('>I',vb,120,2)
        boot=b'x'*32+b'SEANDROIDENFORCE'+bytes(131072-48)
        parts={'boot':boot,'recovery':b'recovery','dtb':b'dtb','dtbo':b'dtbo','vbmeta':bytes(vb)}
        records=[{'partition':k,'block_node':'/dev/block/sda'+str(i+14),'size':len(v),'sha256':sha(v)} for i,(k,v) in enumerate(parts.items())]
        (backup/'backup-manifest.json').write_text(json.dumps({'bootloader':'N976NTEST','partitions':records}),encoding='utf8')
        header={'header_version':1,'page_size':2048,'recovery_dtbo_size':0,'second_size':0,'kernel_addr':0,'tags_addr':0,'ramdisk_addr':0,'arm64_text_offset':0,'ramdisk_file_offset':2048,'ramdisk_size':0,'second_file_offset':32,'cmdline':'fixture','name':'fixture','os_version':'1.0.0','security_patch_month':'2026-01','kernel_sha256':sha(image)}
        def fake_mk(cmd,**kwargs):
            path=Path(cmd[cmd.index('--output')+1]);size=prep.payload_size(len(image),0,2048,len(boot),allow_empty_ramdisk=True);path.write_bytes(b'P'*2048+image+bytes(size-2048-len(image)))
        validators=('pm_quiesce_binding.assert_scope','gic_roundtrip_binding.validate_model','dma_pm_binding.validate_model','ufs_pm_binding.validate_model','iommu_pm_binding.validate_model','abox_pm_binding.validate_model','abox_pmu_binding.validate_model','pm_noirq_binding.validate_model','pmu_settle_binding.validate_model','pm_cpus_binding.validate_model','pm_post_arch_binding.validate_model','pm_edge_binding.validate_model','pm_callbacks_binding.validate_model','pm_preconditions_binding.validate_model','pm_branch_binding.validate_model','pm_irq_binding.validate_model','materialize_auto_cycle.validate','prepare_reservation_kernel.verify_embedded_init')
        with ExitStack() as stack:
            stack.enter_context(patch('pmu_failure_binding.validate',side_effect=lambda root,build:validate_failure(root,build,require_package_flow=False)))
            for v in validators:stack.enter_context(patch(v,return_value=True))
            stack.enter_context(patch.object(prep,'MKBOOTIMG_SHA256',sha(b'mkboot')));stack.enter_context(patch.object(prep,'TWRP_SHA256',sha(b'recovery')))
            stack.enter_context(patch.object(prep,'read_verified_backup',return_value=parts));stack.enter_context(patch.object(packages,'read_verified_backup',return_value=parts))
            stack.enter_context(patch.object(prep,'boot_header',return_value=header));stack.enter_context(patch.object(prep.subprocess,'run',side_effect=fake_mk))
            for case in ('ok','flag-missing','version-missing','proof-missing'):
                build=dict(b)
                if case=='flag-missing':build.pop('pmu_failure_restore')
                if case=='version-missing':build.pop('pmu_failure_restore_version')
                (art/'build-result.json').write_text(json.dumps(build),encoding='utf8')
                proof=art/'pmu-failure-binding-model/result.json';saved=proof.read_bytes()
                if case=='proof-missing':proof.unlink()
                try:
                    prototype=root/(case+'.img')
                    if case!='ok':
                        try:prep.prepare(backup,art,twrp,mk,prototype,auto_cycle_token='c'*32)
                        except (ValueError,KeyError,FileNotFoundError):pass
                        else:raise AssertionError('invalid feature evidence accepted: '+case)
                    else:
                        report=prep.prepare(backup,art,twrp,mk,prototype,auto_cycle_token='c'*32)
                        assert report['pmu_failure_restore'] is True and report['pmu_failure_restore_version']==1
                        result=packages.build(backup,prototype,root/'packages')
                        diag=next(x for x in verify_packages(root/'packages') if x['mode']=='diagnostic')
                        assert result['pmu_failure_restore'] is True and diag['pmu_failure_restore'] is True and diag['pmu_failure_restore_version']==1
                finally:
                    if not proof.exists():proof.write_bytes(saved)
    result={'passed':True,'hardware_verified':False,'cases':['synthetic-prototype-to-packages','missing-flag','missing-version','missing-binding-proof'],'harness_sha256':sha(Path(__file__).read_bytes()),'package_sources_sha256':measured}
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
if __name__=='__main__':main()
