"""New static builder-schedule/flag and incomplete-trace fixtures only."""
import argparse
import ast
import copy
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
import binding_validation_manifest as audit

CASES=('actual-builder-schedule','missing-scratch-call','duplicate-scratch-call','wrong-order',
 'wrong-stage','nonliteral-stage','wrong-callable-alias','naked-call',
 'baseline26','observation27','scratch28','scratch-without-observation',
 'null-observation','integer-observation','null-scratch','integer-scratch',
 'trace-before-first-guard','trace-before-source-audit')

def reject(call,*args):
    try:call(*args)
    except (ValueError,KeyError):return True
    raise AssertionError('invalid new schedule/flag fixture accepted')

def calls(tree):
    return sorted((n for n in ast.walk(tree) if isinstance(n,ast.Call) and
      isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and
      n.func.value.id=='validation' and n.func.attr=='call'),key=lambda n:n.lineno)

def mutation(raw,name):
    tree=ast.parse(raw);nodes=calls(tree)
    scratch=next(n for n in nodes if n.args[0].value=='xnu_runtime_scratch_binding')
    if name=='missing-scratch-call':scratch.func=ast.Name(id='_fixture_absent',ctx=ast.Load())
    elif name=='duplicate-scratch-call':tree.body.append(ast.Expr(value=copy.deepcopy(scratch)))
    elif name=='wrong-order':
        previous=nodes[-2]
        previous.args,scratch.args=scratch.args,previous.args
        previous.keywords,scratch.keywords=scratch.keywords,previous.keywords
    elif name in ('wrong-stage','nonliteral-stage'):
        keyword=next(k for k in scratch.keywords if k.arg=='require_package_flow')
        keyword.value=ast.Constant(value=False) if name=='wrong-stage' else ast.Name(id='fixture_stage',ctx=ast.Load())
    elif name=='wrong-callable-alias':scratch.args[1]=ast.Name(id='fixture_alias',ctx=ast.Load())
    else:tree.body.append(ast.Expr(value=ast.Call(func=copy.deepcopy(scratch.args[1]),args=[],keywords=[])))
    return ast.unparse(ast.fix_missing_locations(tree)).encode()

def trace_fixture(workspace,source_audit):
    root=workspace/('source-audit' if source_audit else 'first-guard');root.mkdir()
    report={'xnu_runtime_observation':True,'xnu_runtime_scratch':True,'build_passed':source_audit}
    recorder=audit.Recorder(root,report,audit.KERNEL_COMMIT,enabled=True)
    # Synthetic event fixture, explicitly not a canonical validator execution.
    recorder.calls=[{'validator':'xnu_runtime_scratch_binding','fixture_only':True},
                    {'validator':'xnu_runtime_scratch_binding','fixture_only':True}]
    if source_audit:recorder.direct_count=len(audit.active_direct(report))
    with patch.object(audit,'verify_builder_schedule',side_effect=ValueError('fixture terminal source audit')):
        reject(recorder.finalize)
    trace=(root/audit.TRACE_FILENAME).read_bytes();saved=json.loads(trace)
    error=json.loads((root/audit.ERROR_FILENAME).read_text())
    if (saved['calls']!=recorder.calls or saved['actual_invocation_count']!=len(recorder.calls) or
        saved['actual_direct_calls_completed']!=recorder.direct_count or
        saved['actual_multiplicities']!={'xnu_runtime_scratch_binding':2} or
        saved['complete'] is not False or saved['accepted'] is not False or saved['canonical_manifest'] is not False or
        error['trace_sha256']!=audit.sha(trace) or error['accepted'] is not False or
        (root/audit.FILENAME).exists()):raise AssertionError('actual incomplete events lost or mislabeled successful')
    return True

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--builder',type=Path,default=audit.HERE/'build_handoff_kernel.py');parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False);raw=args.builder.read_bytes()
    results={'actual-builder-schedule':audit.verify_builder_schedule(raw)}
    for name in CASES[1:8]:results[name]=reject(audit.verify_builder_schedule,mutation(raw,name))
    for name,report,count in (('baseline26',{},26),('observation27',{'xnu_runtime_observation':True},27),
      ('scratch28',{'xnu_runtime_observation':True,'xnu_runtime_scratch':True},28)):
        direct=audit.active_direct(report);expected=audit.DIRECT+(audit.OPTIONAL_DIRECT if count>=27 else ())+(audit.SCRATCH_OPTIONAL_DIRECT if count==28 else ())
        observed=list(dict.fromkeys(row['validator'] for row in audit.expected_calls(report)))
        if direct!=expected or len(observed)!=count:raise AssertionError('26/27/28 conditional schedule differs')
        results[name]=True
    invalid={'scratch-without-observation':{'xnu_runtime_scratch':True},'null-observation':{'xnu_runtime_observation':None},
      'integer-observation':{'xnu_runtime_observation':1},'null-scratch':{'xnu_runtime_scratch':None},
      'integer-scratch':{'xnu_runtime_observation':True,'xnu_runtime_scratch':1}}
    for name,report in invalid.items():results[name]=reject(audit.active_direct,report)
    with tempfile.TemporaryDirectory(dir=args.output) as temp:
        results['trace-before-first-guard']=trace_fixture(Path(temp),False)
        results['trace-before-source-audit']=trace_fixture(Path(temp),True)
    if set(results)!=set(CASES) or not all(results.values()):raise AssertionError('new focused schedule case inventory differs')
    (args.output/'result.json').write_text(json.dumps(dict(passed=True,fixture_only=True,validators_executed=False,
      compiler_executed=False,device_operations=False,canonical_manifest_created=False,
      builder_sha256=audit.sha(raw),recorder_sha256=audit.sha(Path(audit.__file__).read_bytes()),
      test_source_sha256=audit.sha(Path(__file__).read_bytes()),cases={n:results[n] for n in CASES}),indent=2)+'\n')
if __name__=='__main__':main()
