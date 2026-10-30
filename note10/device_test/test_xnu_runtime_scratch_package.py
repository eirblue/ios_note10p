"""Focused new production package/collector paths and scratch proof mutations."""
import argparse
import copy
from contextlib import ExitStack
import json
from pathlib import Path
import shutil
import tempfile
from unittest.mock import patch
import prepare_xnu_runtime_scratch as p
from prepare_xnu_runtime_observation import sha,safe_path
from xnu_runtime_scratch_binding import validate,package_scope,metadata_fields
from test_xnu_runtime_observation import reject,ram_frames

CASES=('production-on','production-off','rollback-off','precheck-scope','collector-row','collector-valid','collector-missing',
 'scope-null','scope-no-prior','scope-version','scope-geometry','scope-unknown','scope-disabled-stray',
 'binding-config','binding-image','binding-source','binding-before','binding-final','binding-native','binding-stack',
 'manifest-recorded','manifest-off-unchanged','stack-duplicate-rejected','stack-unbounded-rejected')

def copy_inputs(artifact,destination,build):
    folders=(p.BASE,p.PREPARED,p.MODEL,'xnu-runtime-scratch-stack')
    for folder in folders:
        source=artifact/folder
        if not source.exists():continue
        for original in source.rglob('*'):
            if original.is_symlink():raise ValueError('unsafe scratch fixture input')
            if original.is_file():
                name=original.relative_to(artifact).as_posix();dest=safe_path(destination,name,False)
                dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(original.read_bytes())

def production(root,artifact,build,enabled):
    import test_cpu_pm_roundtrip_package_flow as legacy
    case=root/('on' if enabled else 'off');case.mkdir()
    art,backup,twrp,mk,parts=legacy.make_fixture(case,artifact,'scratch',True,True,True)
    metadata=json.loads((art/'build-result.json').read_text())
    # Preserve v56 opt-in in both cases; change only the independent v57 scope.
    metadata.update({k:v for k,v in build.items() if k=='xnu_runtime_observation' or k.startswith('xnu_runtime_observation_')})
    if enabled:
        metadata.update({k:v for k,v in build.items() if k==p.FLAG or k.startswith(p.FLAG+'_')})
        copy_inputs(artifact,art,build)
    image=(art/'Image').read_bytes()+p.prior.MARKER+(p.MARKER if enabled else b'')
    config=(art/'handoff.config').read_bytes()+b'CONFIG_NOTE10_XNU_RUNTIME_OBSERVATION=y\n'+(p.OPTION.encode()+b'=y\n' if enabled else b'')
    (art/'Image').write_bytes(image);(art/'handoff.config').write_bytes(config)
    metadata.update(image_sha256=sha(image),image_size=len(image),effective_config_sha256=sha(config))
    (art/'build-result.json').write_text(json.dumps(metadata))
    header=legacy._header(sha(image));prototype=case/'prototype.img';packages_out=case/'packages'
    def fake_mk(command,**kwargs):
        output=Path(command[command.index('--output')+1]);size=legacy.prep.payload_size(len(image),0,2048,len(parts['boot']),allow_empty_ramdisk=True)
        output.write_bytes(b'P'*2048+image+bytes(size-2048-len(image)))
    with ExitStack() as stack:
        legacy._patch_legacy_gates(stack)
        # Historical proof suite is isolated. Actual stack artifact is checked
        # by main() separately; the compact model image has no ARM64 object.
        stack.enter_context(patch('xnu_runtime_observation_binding.validate',return_value=True))
        stack.enter_context(patch('xnu_runtime_scratch_stack.validate',return_value={'fixture_only':True}))
        stack.enter_context(patch.object(legacy.prep,'MKBOOTIMG_SHA256',sha(mk.read_bytes())))
        stack.enter_context(patch.object(legacy.prep,'TWRP_SHA256',sha(twrp.read_bytes())))
        stack.enter_context(patch.object(legacy.prep,'read_verified_backup',return_value=parts))
        stack.enter_context(patch.object(legacy.packages,'read_verified_backup',return_value=parts))
        stack.enter_context(patch.object(legacy.prep,'boot_header',return_value=header))
        stack.enter_context(patch.object(legacy.prep.subprocess,'run',side_effect=fake_mk))
        report=legacy.prep.prepare(backup,art,twrp,mk,prototype,auto_cycle_token=metadata['reservation_evidence_id'])
        packages=legacy.packages.build(backup,prototype,packages_out);records=legacy.verify_packages(packages_out)
        (packages_out/'ram-stage-fixture.json').write_text(json.dumps({'ram_directory':'/tmp/note10-reserve-deadbeef','fixture_only':True}))
        precheck=legacy.run_precheck_flow(art,backup,packages_out,header,parts)
        collector=legacy.run_collector_flow(art,backup,packages_out,case)
    if package_scope(report) is not enabled or package_scope(packages) is not enabled:raise AssertionError('production scratch metadata differs')
    if enabled and precheck.get(p.FLAG+'_scope_verified') is not True:raise AssertionError('new precheck scope missing')
    if any(package_scope(r) is not (enabled and r['mode']=='diagnostic') for r in records):raise AssertionError('rollback scratch scope differs')
    if ('xnu_runtime_scratch' in collector['evaluation_items']) is not enabled:raise AssertionError('new collector row scope differs')
    return collector

def manifest_case(workspace):
    import binding_validation_manifest as audit
    root=workspace/'manifest';root.mkdir()
    for name in audit.proof_names('xnu_runtime_scratch_binding',True):
        dest=root/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b'recorder mechanism fixture')
    namespace={'__name__':'xnu_runtime_scratch_binding'}
    exec(compile('def validate(root,report,require_package_flow=False):\n return True\n',str(audit.HERE/'xnu_runtime_scratch_binding.py'),'exec'),namespace)
    recorder=audit.Recorder(root,{p.FLAG:True,'xnu_runtime_observation':True},audit.KERNEL_COMMIT,enabled=True)
    recorder.direct_count=len(audit.DIRECT)+1
    recorder.call('xnu_runtime_scratch_binding',namespace['validate'],root,{},require_package_flow=True)
    if len(recorder.calls)!=1 or len(recorder.calls[0]['proofs'])!=3 or not recorder.calls[0]['completed_without_exception']:raise AssertionError('scratch actual validator call not recorded')
    if audit.active_direct({})!=audit.DIRECT:raise AssertionError('disabled validator inventory changed')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--artifact',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();artifact=args.artifact;out=args.output;out.mkdir(parents=True,exist_ok=False)
    build=json.loads((artifact/'build-result.json').read_text());validate(artifact,build)
    results={}
    with tempfile.TemporaryDirectory(dir=p.prior.ROOT/'note10/private') as temp:
        workspace=Path(temp)
        on=production(workspace,artifact,build,True);off=production(workspace,artifact,build,False)
        if {k:v for k,v in on['evaluation_items'].items() if k!=p.FLAG}!=off['evaluation_items']:raise AssertionError('new scratch row changed previous rows')
        results.update({k:True for k in CASES[:5]})
        from test_xnu_runtime_scratch import decode_args
        from collect_reservation import decode_runtime_scratch_observation
        text=(artifact/p.MODEL/'native.log').read_text();text=text.split('CASE|minimum\n',1)[1].split('CASE|different-base\n')[0]
        chosen=ram_frames(0x80000000)+text
        fixture=dict(build,reservation_evidence_id='a'*32)
        if decode_runtime_scratch_observation(chosen,'a'*32,fixture)['evaluation_item']['status']!='passed':raise AssertionError('production collector decoder rejected valid scratch')
        if decode_runtime_scratch_observation('','a'*32,fixture)['evaluation_item']['status']!='failed':raise AssertionError('missing scratch accepted')
        results.update({'collector-valid':True,'collector-missing':True})
        for name in CASES[7:13]:
            metadata=copy.deepcopy(build)
            if name=='scope-null':metadata[p.FLAG]=None
            elif name=='scope-no-prior':metadata['xnu_runtime_observation']=False
            elif name=='scope-version':metadata[p.FLAG+'_version']=True
            elif name=='scope-geometry':metadata[p.FLAG+'_geometry_sha256']='0'*64
            elif name=='scope-unknown':metadata[p.FLAG+'_unknown']=True
            else:metadata[p.FLAG]=False
            results[name]=reject(package_scope,metadata,True)
        for name in CASES[13:20]:
            root=workspace/name;root.mkdir();copy_inputs(artifact,root,build);metadata=copy.deepcopy(build)
            (root/'Image').write_bytes((artifact/'Image').read_bytes());(root/'handoff.config').write_bytes((artifact/'handoff.config').read_bytes())
            if name=='binding-config':(root/'handoff.config').write_bytes(b'')
            elif name=='binding-image':(root/'Image').write_bytes(b'')
            elif name=='binding-source':metadata[p.FLAG+'_sources_sha256']['xnu_runtime_scratch.c']='0'*64
            elif name in ('binding-before','binding-final'):
                dest=root/(p.BASE if name.endswith('before') else p.PREPARED)/p.prior.RESERVE;dest.write_bytes(b'bad')
            elif name=='binding-native':(root/p.MODEL/'native.log').write_bytes(b'bad')
            else:(root/'xnu-runtime-scratch-stack/init.su').write_bytes(b'bad')
            results[name]=reject(validate,root,metadata)
        manifest_case(workspace);results['manifest-recorded']=True;results['manifest-off-unchanged']=True
        from xnu_runtime_scratch_stack import calculate
        usage=(artifact/'xnu-runtime-scratch-stack/init.su').read_bytes();obj=(artifact/'xnu-runtime-scratch-stack/init.o').read_bytes()
        line=next(row for row in usage.splitlines() if b'n10_scratch_build' in row)
        results['stack-duplicate-rejected']=reject(calculate,usage+b'\n'+line+b'\n',obj)
        results['stack-unbounded-rejected']=reject(calculate,usage.replace(b'\tstatic',b'\tdynamic'),obj)
    if set(results)!=set(CASES) or not all(results.values()):raise AssertionError('scratch package case inventory differs')
    (out/'result.json').write_text(json.dumps(dict(passed=True,fixture_only=True,synthetic_only=True,hardware_verified=False,physical_memory_or_hardware_accessed=False,
      cases={k:results[k] for k in CASES},source_sha256=p.source_hashes(),
      production_paths=['prepare_linux_boot','build_boot_test_packages','stage_phase2.verify_packages','precheck_window_access','collect_reservation'],
      pc_fixture_stack_isolation_explicit=True,actual_stack_proof_checked_separately=True),indent=2)+'\n')
if __name__=='__main__':main()
