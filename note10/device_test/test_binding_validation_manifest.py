"""Focused manifest-only fixtures. Never imports or runs historical validators."""
import argparse
import copy
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
import binding_validation_manifest as audit

HERE = Path(__file__).resolve().parent
CASES = ('valid-manifest','source-order-preserved','original-call-once-return-preserved',
         'nested-call-recorded','legacy-notifier-input-remains-pinned','schema',
         'project-head','run-id','attempt','kernel-identity','missing-call','duplicate-call',
         'call-order','parent-order','multiplicity','unknown-validator','missing-proof',
         'proof-hash','proof-path','proof-symlink','module-hash','head-module-mismatch',
         'exception-outcome','false-outcome','report-proof-map','existing-proof-field',
         'manifest-hash','missing-manifest','source-order-reordered','source-order-naked')


def source(name):
    return (HERE.parents[1]/name).read_bytes()


def fixture(root):
    identity={'project_head':'a'*40,'run_id':123,'attempt':1,'kernel_source_commit':audit.KERNEL_COMMIT}
    report={'build_passed':True,'source_commit':audit.KERNEL_COMMIT,'binding_validation_schema':audit.SCHEMA}
    proof_fields={};calls=[]
    for sequence,wanted in enumerate(audit.expected_calls()):
        name=wanted['validator'];proofs=[]
        for path in audit.proof_names(name,wanted['require_package_flow']):
            target=root/path;target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text('synthetic manifest fixture only\n'+path,encoding='ascii')
            digest=audit.sha(target.read_bytes())
            proofs.append({'path':path,'sha256':digest,'build_report_field':['binding_validation_proof_sha256',name,path]})
            proof_fields.setdefault(name,{})[path]=digest
            if path in audit.EXISTING_FIELDS:report[audit.EXISTING_FIELDS[path]]=digest
        module='note10/device_test/'+name+'.py'
        calls.append(dict(wanted,sequence=sequence,entrypoint=audit.ENTRYPOINTS[name],module_path=module,
                          module_sha256=audit.sha(source(module)),completed_without_exception=True,
                          returned_outcome={'type':'builtins.bool','value':True,'scalar_serialized':True},proofs=proofs))
    order=list(dict.fromkeys(call['validator'] for call in calls))
    report['binding_validation_proof_sha256']=proof_fields
    document={'schema':audit.SCHEMA,'identity':identity,'build_completed':True,
              'builder_path':'note10/device_test/build_handoff_kernel.py',
              'builder_sha256':audit.sha(source('note10/device_test/build_handoff_kernel.py')),
              'recorder_path':'note10/device_test/binding_validation_manifest.py',
              'recorder_sha256':audit.sha(source('note10/device_test/binding_validation_manifest.py')),
              'direct_calls':[{'validator':name,'require_package_flow':stage} for name,stage in audit.DIRECT],
              'validator_order':order,'multiplicities':{name:sum(c['validator']==name for c in calls) for name in order},'calls':calls}
    return document,report,identity


def save(root,document,report):
    raw=(json.dumps(document,indent=2)+'\n').encode()
    (root/audit.FILENAME).write_bytes(raw)
    report['binding_validation_result_sha256']=audit.sha(raw)


def rejected(function,*args,**kwargs):
    try:function(*args,**kwargs)
    except (ValueError,FileNotFoundError):return True
    raise AssertionError('invalid manifest accepted')


def fake_function(module,body,extra=None):
    # Fresh fixture code with canonical frame metadata exercises recording only;
    # the actual source bytes are never imported or executed by these fixtures.
    namespace={'__name__':module};namespace.update(extra or {})
    exec(compile(body,str(HERE/(module+'.py')),'exec'),namespace)
    return namespace[audit.ENTRYPOINTS[module]]


def instrumentation(root,report):
    recorder=audit.Recorder(root,report,audit.KERNEL_COMMIT,enabled=True)
    original=fake_function('pm_quiesce_binding',
        "def validate_model(root,report):\n report['original_calls']=report.get('original_calls',0)+1\n return None\n")
    if recorder.call('pm_quiesce_binding',original,root,report) is not None or report['original_calls']!=1:
        raise AssertionError('instrumentation changed original call or return')
    if len(recorder.calls)!=1 or recorder.calls[0]['completed_without_exception'] is not True or recorder.calls[0]['returned_outcome']['type']!='builtins.NoneType':
        raise AssertionError('actual None completion was not recorded')
    recorder=audit.Recorder(root,report,audit.KERNEL_COMMIT,enabled=True)
    recorder.direct_count=audit.DIRECT.index(('gic_priority_binding',False))
    child=fake_function('pmu_failure_binding','def validate(root,report,require_package_flow=True):\n return True\n')
    parent=fake_function('gic_priority_binding',
        'def validate(root,report,require_package_flow=True):\n return child(root,report)\n',{'child':child})
    if recorder.call('gic_priority_binding',parent,root,report,require_package_flow=False) is not True:
        raise AssertionError('nested original return changed')
    if ([call['validator'] for call in recorder.calls]!=['gic_priority_binding','pmu_failure_binding'] or
        recorder.calls[1]['parent_call']!=0 or recorder.calls[1]['require_package_flow'] is not True):
        raise AssertionError('nested canonical validator call was omitted')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists() or args.output.is_symlink():raise ValueError('fresh manifest fixture output required')
    args.output.mkdir(parents=True);results={}
    with tempfile.TemporaryDirectory(dir=args.output) as temporary:
        root=Path(temporary);document,report,identity=fixture(root);save(root,document,report)
        valid=audit.verify_manifest(root,report,identity,source)
        if valid['binding_validator_count']!=26:raise AssertionError('manifest inventory differs')
        results['valid-manifest']=True
        audit.verify_builder_schedule(source('note10/device_test/build_handoff_kernel.py'))
        results['source-order-preserved']=True
        instrumentation(root,report)
        results['original-call-once-return-preserved']=True;results['nested-call-recorded']=True
        guard=source('note10/device_test/test_cpu_pm_failure_guard_native.py').decode()
        builder=source('note10/device_test/build_handoff_kernel.py').decode()
        if ("ap.add_argument('--notifier-source')" not in guard or
            "if sha(files[n])!=PINS[n]" not in guard or
            "failure_guard_extra=['--notifier-source',str(OUT/TRACE_BASE/'kernel/notifier.c')]" not in builder or
            'trace_after=trace_transform(trace_before)' not in builder):
            raise AssertionError('legacy notifier pin/production composition input binding changed')
        results['legacy-notifier-input-remains-pinned']=True
        for name in CASES[5:]:
            bad=copy.deepcopy(document);metadata=copy.deepcopy(report);loader=source
            missing=None
            if name in ('source-order-reordered','source-order-naked'):
                builder=source('note10/device_test/build_handoff_kernel.py')
                first=b"validation.call('pm_quiesce_binding',validate_quiesce,OUT,report)"
                second=b"validation.call('gic_roundtrip_binding',validate_gic,OUT,report)"
                if name=='source-order-reordered':
                    builder=builder.replace(first,b'__FIRST_CALL__').replace(second,first).replace(b'__FIRST_CALL__',second)
                else:builder=builder.replace(first,b'validate_quiesce(OUT,report)')
                results[name]=rejected(audit.verify_builder_schedule,builder);continue
            if name=='schema':bad['schema']=False
            elif name=='project-head':bad['identity']['project_head']='b'*40
            elif name=='run-id':bad['identity']['run_id']=124
            elif name=='attempt':bad['identity']['attempt']=2
            elif name=='kernel-identity':bad['identity']['kernel_source_commit']='b'*40
            elif name=='missing-call':bad['calls'].pop()
            elif name=='duplicate-call':bad['calls'].append(copy.deepcopy(bad['calls'][0]))
            elif name=='call-order':bad['calls'][0],bad['calls'][1]=bad['calls'][1],bad['calls'][0]
            elif name=='parent-order':bad['calls'][0]['parent_call']=1
            elif name=='multiplicity':bad['multiplicities']['pm_quiesce_binding']+=1
            elif name=='unknown-validator':bad['calls'][0]['validator']='unknown_binding'
            elif name=='missing-proof':bad['calls'][0]['proofs'].pop()
            elif name=='proof-hash':bad['calls'][0]['proofs'][0]['sha256']='0'*64
            elif name=='proof-path':bad['calls'][0]['proofs'][0]['path']='../outside.json'
            elif name=='module-hash':bad['calls'][0]['module_sha256']='0'*64
            elif name=='head-module-mismatch':
                loader=lambda path:source(path)+(b'\nchanged HEAD module' if path.endswith('pm_quiesce_binding.py') else b'')
            elif name=='exception-outcome':bad['calls'][0]['completed_without_exception']=False
            elif name=='false-outcome':bad['calls'][0]['returned_outcome']['value']=False
            elif name=='report-proof-map':metadata['binding_validation_proof_sha256']={}
            elif name=='existing-proof-field':metadata['ehld_irqsave_model_sha256']='0'*64
            elif name=='missing-manifest':
                (root/audit.FILENAME).unlink();results[name]=rejected(audit.verify_manifest,root,metadata,identity,loader);continue
            save(root,bad,metadata)
            if name=='manifest-hash':metadata['binding_validation_result_sha256']='0'*64
            if name=='proof-symlink':
                original=Path.is_symlink;unsafe=root/bad['calls'][0]['proofs'][0]['path']
                with patch.object(Path,'is_symlink',lambda path:path==unsafe or original(path)):
                    results[name]=rejected(audit.verify_manifest,root,metadata,identity,loader)
            else:results[name]=rejected(audit.verify_manifest,root,metadata,identity,loader)
    if set(results)!=set(CASES) or not all(results.values()):raise AssertionError('manifest focused fixture inventory differs')
    proof={'passed':True,'synthetic_only':True,'hardware_verified':False,'cases':list(CASES),'results':results,
           'old_validators_imported_or_executed':False,'native_or_device_execution':False,
           'source_sha256':{name:audit.sha(source('note10/device_test/'+name)) for name in
                            ('binding_validation_manifest.py','test_binding_validation_manifest.py','build_handoff_kernel.py','test_cpu_pm_failure_guard_native.py')}}
    (args.output/'result.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8',newline='\n')


if __name__=='__main__':main()
