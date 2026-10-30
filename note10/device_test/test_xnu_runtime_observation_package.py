"""New planner scope integration fixtures; old validators are isolated, not replayed."""
import argparse
import copy
from contextlib import ExitStack
import json
from pathlib import Path
import shutil
import tempfile
from unittest.mock import patch
import prepare_xnu_runtime_observation as prepare
from xnu_runtime_observation_binding import validate,package_scope,metadata_fields
from test_xnu_runtime_observation import reject,ram_frames

CASES=('production-on','production-off','rollback-off','prior-rows-unchanged','collector-valid','collector-missing',
 'scope-null','scope-no-trace','scope-no-recovery','scope-stray','scope-unknown',
 'binding-config','binding-image','binding-source','binding-prepared','binding-before','binding-model','binding-native-missing','binding-native-ambiguous',
 'manifest-new-validator-recorded','manifest-disabled-inventory-unchanged','manifest-flag-type-rejected')


def copy_inputs(artifact,destination,build):
    """Copy only bound regular files, never arbitrary artifact subtrees."""
    for folder,field in ((prepare.BASE,'before_sha256'),(prepare.PREPARED,'prepared_sha256')):
        mapping=build[prepare.FLAG+'_'+field]
        for name,expected in mapping.items():
            original=prepare.safe_path(artifact/folder,name)
            if prepare.sha(original.read_bytes())!=expected:raise ValueError('fixture prepared input hash differs')
            target=prepare.safe_path(destination/folder,name,False);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(original.read_bytes())
    proof_path=prepare.safe_path(artifact/prepare.MODEL,'result.json');proof=json.loads(proof_path.read_text(encoding='utf8'))
    compiled=proof.get('compiled_files_sha256',{})
    if set(compiled) not in ({'native.c','native','compile.log','native.log'},{'native.c','native.exe','compile.log','native.log'}):
        raise ValueError('fixture native proof inventory differs')
    for name,expected in {**compiled,'result.json':build[prepare.FLAG+'_model_sha256']}.items():
        original=prepare.safe_path(artifact/prepare.MODEL,name)
        if prepare.sha(original.read_bytes())!=expected:raise ValueError('fixture native input digest differs')
        target=prepare.safe_path(destination/prepare.MODEL,name,False);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(original.read_bytes())


def production(root,artifact,build,enabled):
    import test_cpu_pm_roundtrip_package_flow as legacy
    case=root/('on' if enabled else 'off');case.mkdir()
    art,backup,twrp,mk,parts=legacy.make_fixture(case,artifact,'runtime',True,True,True)
    metadata=json.loads((art/'build-result.json').read_text(encoding='utf8'))
    if enabled:
        metadata.update({key:value for key,value in build.items() if key==prepare.FLAG or key.startswith(prepare.FLAG+'_')})
        copy_inputs(artifact,art,build)
        image=(art/'Image').read_bytes()+prepare.MARKER
        config=(art/'handoff.config').read_bytes()+prepare.OPTION.encode()+b'=y\n'
        (art/'Image').write_bytes(image);(art/'handoff.config').write_bytes(config)
        metadata.update(image_sha256=prepare.sha(image),image_size=len(image),effective_config_sha256=prepare.sha(config))
    (art/'build-result.json').write_text(json.dumps(metadata),encoding='utf8')
    image=(art/'Image').read_bytes();header=legacy._header(prepare.sha(image));prototype=case/'prototype.img';packages_out=case/'packages'
    def fake_mk(command,**kwargs):
        output=Path(command[command.index('--output')+1]);size=legacy.prep.payload_size(len(image),0,2048,len(parts['boot']),allow_empty_ramdisk=True)
        output.write_bytes(b'P'*2048+image+bytes(size-2048-len(image)))
    with ExitStack() as stack:
        # Saved older contracts are not rerun; only the new production binding
        # and package/collector paths under test remain real.
        legacy._patch_legacy_gates(stack)
        stack.enter_context(patch.object(legacy.prep,'MKBOOTIMG_SHA256',prepare.sha(mk.read_bytes())))
        stack.enter_context(patch.object(legacy.prep,'TWRP_SHA256',prepare.sha(twrp.read_bytes())))
        stack.enter_context(patch.object(legacy.prep,'read_verified_backup',return_value=parts))
        stack.enter_context(patch.object(legacy.packages,'read_verified_backup',return_value=parts))
        stack.enter_context(patch.object(legacy.prep,'boot_header',return_value=header))
        stack.enter_context(patch.object(legacy.prep.subprocess,'run',side_effect=fake_mk))
        report=legacy.prep.prepare(backup,art,twrp,mk,prototype,auto_cycle_token=metadata['reservation_evidence_id'])
        packages=legacy.packages.build(backup,prototype,packages_out)
        records=legacy.verify_packages(packages_out)
        try:
            (packages_out/'ram-stage-fixture.json').write_text(json.dumps({'ram_directory':'/tmp/note10-reserve-deadbeef','fixture_only':True}),encoding='utf8',newline='\n')
            precheck=legacy.run_precheck_flow(art,backup,packages_out,header,parts)
            collector=legacy.run_collector_flow(art,backup,packages_out,case)
        except Exception as error:
            raise AssertionError('runtime package fixture '+('on' if enabled else 'off')+' precheck/collector: '+str(error)) from error
    if package_scope(report) is not enabled or package_scope(packages) is not enabled:raise AssertionError('production prepare/package new scope differs')
    if enabled and precheck.get(prepare.FLAG+'_scope_verified') is not True:raise AssertionError('production precheck planner gate missing')
    if any(package_scope(record) is not (enabled and record['mode']=='diagnostic') for record in records):raise AssertionError('planner rollback scope differs')
    return collector


def binding_cases(artifact,build,workspace):
    results={}
    for name in CASES[11:19]:
        root=workspace/name;root.mkdir();metadata=copy.deepcopy(build)
        copy_inputs(artifact,root,build)
        (root/'Image').write_bytes(prepare.MARKER)
        config=prepare.safe_path(artifact,'handoff.config').read_bytes()
        if prepare.sha(config)!=build.get('effective_config_sha256'):raise ValueError('fixture actual config digest differs')
        (root/'handoff.config').write_bytes(config)
        if name=='binding-config':(root/'handoff.config').write_bytes(b'')
        elif name=='binding-image':(root/'Image').write_bytes(b'')
        elif name=='binding-source':metadata[prepare.FLAG+'_sources_sha256']['prepare_xnu_runtime_observation.py']='0'*64
        elif name in ('binding-prepared','binding-before'):
            folder=prepare.PREPARED if name.endswith('prepared') else prepare.BASE
            path=root/folder/prepare.RESERVE;path.write_bytes(path.read_bytes()+b'\n')
        elif name=='binding-model':metadata[prepare.FLAG+'_model_sha256']='0'*64
        else:
            executable=next(path for path in (root/prepare.MODEL/'native',root/prepare.MODEL/'native.exe') if path.is_file())
            if name.endswith('missing'):executable.unlink()
            else:(executable.parent/('native.exe' if executable.name=='native' else 'native')).write_bytes(executable.read_bytes())
        results[name]=reject(validate,root,metadata)
    return results


def manifest_cases(workspace):
    import binding_validation_manifest as audit
    root=workspace/'manifest';root.mkdir()
    for name in audit.proof_names('xnu_runtime_observation_binding',True):
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'recorder mechanism fixture only')
    # Exercise actual profiling, without running any historical validator or
    # pretending this small synthetic call is an actual CI manifest.
    namespace={'__name__':'xnu_runtime_observation_binding'}
    code=compile('def validate(root,report,require_package_flow=False):\n return True\n',str(audit.HERE/'xnu_runtime_observation_binding.py'),'exec')
    exec(code,namespace)
    recorder=audit.Recorder(root,{prepare.FLAG:True},audit.KERNEL_COMMIT,enabled=True)
    recorder.direct_count=len(audit.DIRECT)
    if recorder.call('xnu_runtime_observation_binding',namespace['validate'],root,{},require_package_flow=True) is not True:
        raise AssertionError('new validator callable result not preserved')
    if len(recorder.calls)!=1 or recorder.calls[0]['validator']!='xnu_runtime_observation_binding' or recorder.calls[0]['completed_without_exception'] is not True or len(recorder.calls[0]['proofs'])!=2:
        raise AssertionError('new actual profile invocation/proofs absent')
    if audit.active_direct({})!=audit.DIRECT:raise AssertionError('disabled manifest inventory changed')
    return {'manifest-new-validator-recorded':True,'manifest-disabled-inventory-unchanged':True,
      'manifest-flag-type-rejected':reject(audit.active_direct,{prepare.FLAG:1})}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--artifact',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();artifact=args.artifact.resolve();output=args.output.resolve();private=(prepare.ROOT/'note10/private').resolve()
    if args.output.exists() or args.output.is_symlink() or output==private or not output.is_relative_to(private):raise ValueError('fresh private package proof output required')
    output.mkdir(parents=True);build=json.loads((artifact/'build-result.json').read_text(encoding='utf8'));validate(artifact,build)
    results={}
    with tempfile.TemporaryDirectory(prefix='xnu-observation-package-',dir=private) as temporary:
        workspace=Path(temporary).resolve()
        if workspace.is_relative_to(artifact) or artifact.is_relative_to(workspace):raise ValueError('package fixtures must be disjoint from artifact')
        on=production(workspace,artifact,build,True);off=production(workspace,artifact,build,False)
        results.update({'production-on':True,'production-off':True,'rollback-off':True})
        if {key:value for key,value in on['evaluation_items'].items() if key!='xnu_runtime_plan'}!=off['evaluation_items']:
            raise AssertionError('new observation altered old collector rows')
        if on['evaluation_items'].get('xnu_runtime_plan')!={'required':True,'status':'failed'} or 'xnu_runtime_plan' in off['evaluation_items']:
            raise AssertionError('missing planner evidence or disabled row schema differs')
        results['prior-rows-unchanged']=True
        from collect_reservation import decode_runtime_plan_observation
        native=(artifact/prepare.MODEL/'native.log').read_text(encoding='ascii').split('CASE|different-base')[0].split('\n',1)[1]
        text=ram_frames(0x80000000)+native
        if decode_runtime_plan_observation(text,'a'*32,build)['evaluation_item']['status']!='passed':raise AssertionError('valid selected companion collector row failed')
        if decode_runtime_plan_observation(ram_frames(0x80000000),'a'*32,build)['evaluation_item']['status']!='failed':raise AssertionError('missing selected companion row accepted')
        results.update({'collector-valid':True,'collector-missing':True})
        metadata={**build,**metadata_fields(build)}
        metadata={key:value for key,value in metadata.items() if not key.startswith(prepare.FLAG+'_') or key in (prepare.VERSION,prepare.FLAG+'_geometry_sha256')}
        for name in CASES[6:11]:
            bad=copy.deepcopy(metadata)
            if name=='scope-null':bad[prepare.FLAG]=None
            elif name=='scope-no-trace':bad['cpu_pm_notifier_trace']=False
            elif name=='scope-no-recovery':bad['auto_return_diagnostic']=False
            elif name=='scope-stray':bad[prepare.FLAG]=False;bad[prepare.VERSION]=None
            else:bad[prepare.FLAG+'_unknown']=True
            # Metadata-only fixtures retain unrelated build fields; the new
            # package validator still checks strict old feature prerequisites.
            results[name]=reject(package_scope,bad,allow_build_proof=True)
        results.update(binding_cases(artifact,build,workspace))
        results.update(manifest_cases(workspace))
    if set(results)!=set(CASES) or not all(results.values()):raise AssertionError('focused planner package case inventory differs')
    result={'passed':True,'cases':results,'source_sha256':{name:prepare.sha((prepare.HERE/name).read_bytes()) for name in prepare.SOURCES},
      'production_paths':['prepare_linux_boot','build_boot_test_packages','stage_phase2.verify_packages','precheck_window_access','collect_reservation'],
      'fixture_only':True,'legacy_validators_isolated':True,'old_models_replayed':False,'device_operations':[]}
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')


if __name__=='__main__':main()
