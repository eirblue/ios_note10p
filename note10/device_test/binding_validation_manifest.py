"""Audit existing production binding calls without replacing or replaying validators.

Only existing builder aliases invoke validators. A temporary Python profile hook
observes canonical nested entrypoints during each such call. The saved order is
checked against this reviewed call graph; successful CI remains a separate gate.
"""
import ast
import dis
import hashlib
import json
import os
from pathlib import Path
import re
import sys

SCHEMA = 1
FILENAME = 'binding-validation-result.json'
KERNEL_COMMIT = '55f042627bb7030c93550faafa117674d32b21d1'
HERE = Path(__file__).resolve().parent
ENTRYPOINTS = {
    name + '_binding': 'validate_model' for name in
    ('pm_quiesce', 'gic_roundtrip', 'dma_pm', 'ufs_pm', 'iommu_pm', 'abox_pm',
     'abox_pmu', 'pm_noirq', 'pmu_settle', 'pm_cpus', 'pm_post_arch', 'pm_edge',
     'pm_callbacks', 'pm_preconditions', 'pm_branch', 'pm_irq')
}
ENTRYPOINTS.update({name + '_binding': 'validate' for name in
                   ('pmu_failure', 'gic_priority', 'pmu_state', 'pmu_control',
                    'fpsimd_reference', 'rcu_context', 'ehld_lock', 'ehld_irqsave',
                    'ehld_running_lock', 'cpu_pm_roundtrip')})
ENTRYPOINTS['xnu_runtime_observation_binding']='validate'
OPTIONAL_DIRECT=(('xnu_runtime_observation_binding',True),)


def active_direct(report=None):
    flag=report.get('xnu_runtime_observation',False) if report is not None else False
    if type(flag) is not bool:raise ValueError('manifest planner opt-in must be bool')
    return DIRECT+(OPTIONAL_DIRECT if flag else ())


DIRECT = (
    ('pm_quiesce_binding', None), ('gic_roundtrip_binding', None),
    ('dma_pm_binding', None), ('ufs_pm_binding', None), ('iommu_pm_binding', None),
    ('abox_pm_binding', None), ('abox_pmu_binding', None), ('pm_noirq_binding', None),
    ('pmu_settle_binding', None), ('pm_cpus_binding', None), ('pm_post_arch_binding', None),
    ('pm_edge_binding', None), ('pm_callbacks_binding', None), ('pm_preconditions_binding', None),
    ('pm_branch_binding', None), ('pmu_failure_binding', False), ('pmu_failure_binding', True),
    ('gic_priority_binding', False), ('gic_priority_binding', True),
    ('pmu_state_binding', False), ('pmu_state_binding', True),
    ('pmu_control_binding', False), ('pmu_control_binding', True),
    ('fpsimd_reference_binding', False), ('fpsimd_reference_binding', True),
    ('rcu_context_binding', False), ('rcu_context_binding', True),
    ('ehld_lock_binding', False), ('ehld_lock_binding', True), ('pm_irq_binding', None),
    ('ehld_irqsave_binding', False), ('ehld_irqsave_binding', True),
    ('ehld_running_lock_binding', False), ('ehld_running_lock_binding', True),
    ('cpu_pm_roundtrip_binding', False), ('cpu_pm_roundtrip_binding', True),
)
CHILDREN = {
    'pm_branch_binding': 'pm_preconditions_binding',
    'gic_priority_binding': 'pmu_failure_binding',
    'pmu_state_binding': 'gic_priority_binding',
    'pmu_control_binding': 'pmu_state_binding',
    'fpsimd_reference_binding': 'pmu_control_binding',
    'rcu_context_binding': 'fpsimd_reference_binding',
    'ehld_lock_binding': 'rcu_context_binding',
    'ehld_irqsave_binding': 'ehld_lock_binding',
    'ehld_running_lock_binding': 'ehld_irqsave_binding',
    'cpu_pm_roundtrip_binding': 'ehld_running_lock_binding',
}
# Explicit, artifact-relative proof inventory. Files are measured at actual
# returns, not guessed from the expected ID list. Final build-report proof fields
# bind the same union of files; existing stronger proof fields are also checked.
PROOFS = {
    'pm_quiesce_binding': ('pm-quiesce-model/result.json', 'pm-usb-model/result.json'),
    'gic_roundtrip_binding': ('gic-roundtrip-model/result.json',),
    'dma_pm_binding': ('dma-pm-model/result.json',),
    'ufs_pm_binding': ('ufs-pm-model/result.json',),
    'iommu_pm_binding': ('iommu-pm-model/result.json',),
    'abox_pm_binding': ('abox-pm-model/result.json',),
    'abox_pmu_binding': ('abox-pmu-model/result.json',),
    'pm_noirq_binding': ('pm-noirq-model/result.json', 'pm-noirq-pmu-model/result.json'),
    'pmu_settle_binding': ('pmu-settle-model/result.json',),
    'pm_cpus_binding': ('pm-cpus-model/result.json', 'pm-cpus-hotplug-model/result.json'),
    'pm_post_arch_binding': ('pm-post-arch-model/result.json',),
    'pm_edge_binding': ('pm-edge-binding-model/result.json',),
    'pm_callbacks_binding': ('pm-callbacks-binding-model/result.json', 'cpu-pm-failure-guard-model/result.json'),
    'pm_preconditions_binding': ('pm-preconditions-scope-model/result.json',),
    'pm_branch_binding': ('pm-branch-scope-model/result.json',),
    'pm_irq_binding': ('pm-irq-binding-model/result.json',),
    'pmu_failure_binding': ('pmu-failure-model/result.json', 'pmu-failure-binding-model/result.json'),
    'gic_priority_binding': ('gic-priority-model/result.json', 'gic-priority-binding-model/result.json'),
    'pmu_state_binding': ('pmu-state-native-model/result.json', 'pmu-state-binding-model/result.json'),
    'pmu_control_binding': ('pmu-control-native-model/result.json', 'pmu-control-binding-model/result.json'),
    'fpsimd_reference_binding': ('fpsimd-reference-native-model/result.json', 'fpsimd-reference-binding-model/result.json'),
    'rcu_context_binding': ('rcu-context-native-model/result.json', 'rcu-context-binding-model/result.json'),
    'ehld_lock_binding': ('ehld-lock-native-model/result.json', 'ehld-lock-binding-model/result.json'),
    'ehld_irqsave_binding': ('ehld-irqsave-model/result.json', 'ehld-irqsave-binding-model/result.json'),
    'ehld_running_lock_binding': ('ehld-running-lock-model/result.json', 'ehld-running-lock-binding-model/result.json'),
    'cpu_pm_roundtrip_binding': ('cpu-pm-roundtrip-model/result.json', 'cpu-pm-roundtrip-binding-model/result.json',
                                 'cpu-pm-notifier-counts-model/result.json', 'cpu-pm-notifier-trace-model/result.json'),
}
PROOFS['xnu_runtime_observation_binding']=('xnu-runtime-observation-model/result.json','xnu-runtime-observation-package-model/result.json')
PACKAGE_PROOFS = {name + '_binding': name.replace('_', '-') + '-package-flow-model/result.json'
                  for name in ('pmu_failure', 'gic_priority', 'pmu_state', 'pmu_control',
                               'fpsimd_reference', 'rcu_context', 'ehld_lock',
                               'ehld_irqsave', 'ehld_running_lock', 'cpu_pm_roundtrip')}
EXISTING_FIELDS = {
    'xnu-runtime-observation-model/result.json':'xnu_runtime_observation_model_sha256',
    'xnu-runtime-observation-package-model/result.json':'xnu_runtime_observation_package_sha256',
    'ehld-irqsave-model/result.json': 'ehld_irqsave_model_sha256',
    'ehld-irqsave-binding-model/result.json': 'ehld_irqsave_binding_sha256',
    'ehld-irqsave-package-flow-model/result.json': 'ehld_irqsave_package_flow_sha256',
    'ehld-running-lock-model/result.json': 'ehld_running_lock_model_sha256',
    'ehld-running-lock-binding-model/result.json': 'ehld_running_lock_binding_sha256',
    'ehld-running-lock-package-flow-model/result.json': 'ehld_running_lock_package_flow_sha256',
    'cpu-pm-roundtrip-model/result.json': 'cpu_pm_roundtrip_model_sha256',
    'cpu-pm-roundtrip-binding-model/result.json': 'cpu_pm_roundtrip_binding_sha256',
    'cpu-pm-roundtrip-package-flow-model/result.json': 'cpu_pm_roundtrip_package_flow_sha256',
    'cpu-pm-notifier-counts-model/result.json': 'cpu_pm_notifier_counts_model_sha256',
    'cpu-pm-notifier-trace-model/result.json': 'cpu_pm_notifier_trace_model_sha256',
    'cpu-pm-notifier-trace-package-model/result.json': 'cpu_pm_notifier_trace_package_sha256',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def safe_file(root, name):
    if not isinstance(name, str): raise ValueError('manifest path must be text')
    rel = Path(name)
    if rel.is_absolute() or '..' in rel.parts or rel.as_posix() != name or not rel.parts:
        raise ValueError('unsafe manifest path')
    root = Path(root)
    if root.is_symlink(): raise ValueError('unsafe manifest root')
    current = root
    for part in rel.parts:
        current = current/part
        if current.is_symlink(): raise ValueError('manifest symlink path')
    if not current.is_file() or not current.resolve().is_relative_to(root.resolve()):
        raise ValueError('manifest proof/source missing or escaped root')
    return current


def proof_names(validator, package):
    result = list(PROOFS[validator])
    if package is True and validator in PACKAGE_PROOFS:
        result.append(PACKAGE_PROOFS[validator])
        if validator == 'cpu_pm_roundtrip_binding':
            result.append('cpu-pm-notifier-trace-package-model/result.json')
    return result


def expected_calls(report=None):
    result = []
    def expand(validator, package, root, parent):
        index = len(result)
        result.append({'validator': validator, 'require_package_flow': package,
                       'root_call': root, 'parent_call': parent})
        child = CHILDREN.get(validator)
        if child:
            stage = (None if child == 'pm_preconditions_binding' else
                     False if validator in ('cpu_pm_roundtrip_binding','ehld_lock_binding') else
                     package if validator in ('ehld_running_lock_binding', 'ehld_irqsave_binding') else True)
            expand(child, stage, root, index)
    for root, (validator, package) in enumerate(active_direct(report)):
        expand(validator, package, root, None)
    return result


def verify_builder_schedule(raw):
    """Pure AST check: instrumentation keeps original aliases and source order."""
    tree = ast.parse(raw)
    imports = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in ENTRYPOINTS:
            for alias in node.names:
                if alias.name == ENTRYPOINTS[node.module]:
                    imports[alias.asname or alias.name] = node.module
    instrumented = []
    naked = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call): continue
        if isinstance(node.func, ast.Name) and node.func.id in imports:
            naked.append(node.lineno)
        if (isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and
                node.func.value.id == 'validation' and node.func.attr == 'call'):
            if len(node.args) < 4 or not isinstance(node.args[0], ast.Constant) or not isinstance(node.args[1], ast.Name):
                raise ValueError('manifest call site lost its original callable alias')
            validator = node.args[0].value
            if imports.get(node.args[1].id) != validator:
                raise ValueError('manifest call site validator/alias mismatch')
            package = True if ENTRYPOINTS[validator] == 'validate' else None
            for keyword in node.keywords:
                if keyword.arg == 'require_package_flow':
                    if not isinstance(keyword.value, ast.Constant) or type(keyword.value.value) is not bool:
                        raise ValueError('manifest call stage is not literal')
                    package = keyword.value.value
            instrumented.append((node.lineno, validator, package))
    schedule = tuple((validator, package) for _, validator, package in sorted(instrumented))
    if naked or schedule != DIRECT+OPTIONAL_DIRECT:
        raise ValueError('reviewed existing production validator schedule differs')
    return True


class Recorder:
    def __init__(self, artifact, report, kernel_commit, enabled=False):
        self.root = Path(artifact); self.report = report; self.kernel = kernel_commit
        self.enabled = enabled; self.calls = []; self.direct_count = 0
        self.frames = {}; self.stack = []; self.error = None

    def _profile(self, frame, event, argument):
        if event not in ('call','return'):return
        validator = frame.f_globals.get('__name__')
        if validator not in ENTRYPOINTS or frame.f_code.co_name != ENTRYPOINTS[validator]: return
        try:
            if event == 'call':
                source = Path(frame.f_code.co_filename).resolve()
                expected_source = (HERE/(validator+'.py')).resolve()
                if source != expected_source: raise ValueError('validator executed from unexpected module path')
                package = frame.f_locals.get('require_package_flow') if ENTRYPOINTS[validator]=='validate' else None
                index = len(self.calls)
                record = {'sequence': index, 'validator': validator, 'entrypoint': ENTRYPOINTS[validator],
                          'root_call': self.direct_count, 'parent_call': self.stack[-1] if self.stack else None,
                          'require_package_flow': package, 'module_path': 'note10/device_test/'+validator+'.py',
                          'module_sha256': sha(source.read_bytes()), 'completed_without_exception': False,
                          'returned_outcome': None, 'proofs': []}
                self.calls.append(record); self.frames[id(frame)] = index; self.stack.append(index)
            elif event == 'return' and id(frame) in self.frames:
                index = self.frames.pop(id(frame)); record = self.calls[index]
                if not self.stack or self.stack.pop()!=index: raise ValueError('validator profile stack differs')
                # CPython reports a return event for exception unwinds too.
                # Only a real RETURN opcode establishes a completed return.
                opcode = dis.opname[frame.f_code.co_code[frame.f_lasti]] if frame.f_lasti >= 0 else ''
                record['completed_without_exception'] = opcode.startswith('RETURN_')
                kind = type(argument).__module__+'.'+type(argument).__qualname__
                record['returned_outcome'] = {'type': kind, 'value': argument if type(argument) in (bool,int,str,float,type(None)) else None,
                                              'scalar_serialized': type(argument) in (bool,int,str,float,type(None))}
                if record['completed_without_exception']:
                    for name in proof_names(validator, record['require_package_flow']):
                        path = safe_file(self.root, name)
                        record['proofs'].append({'path': name, 'sha256': sha(path.read_bytes()),
                            'build_report_field': ['binding_validation_proof_sha256',validator,name]})
        except Exception as error:
            if self.error is None: self.error = str(error)

    def call(self, validator, original, *args, **kwargs):
        if not self.enabled: return original(*args, **kwargs)
        package = kwargs.get('require_package_flow',True) if ENTRYPOINTS.get(validator)=='validate' else None
        direct=active_direct(self.report)
        if (self.direct_count >= len(direct) or direct[self.direct_count] != (validator,package) or
                original.__module__ != validator or original.__name__ != ENTRYPOINTS[validator]):
            raise ValueError('production validator call order/alias differs')
        if sys.getprofile() is not None: raise ValueError('existing profiler prevents exact validator audit')
        start = len(self.calls)
        sys.setprofile(self._profile)
        try:
            outcome = original(*args, **kwargs)
        finally:
            sys.setprofile(None)
        if self.error or self.frames or self.stack or len(self.calls)==start:
            raise ValueError('binding audit incomplete: '+str(self.error))
        self.direct_count += 1
        return outcome

    def finalize(self):
        if not self.enabled: return {}
        if self.direct_count != len(active_direct(self.report)) or self.report.get('build_passed') is not True:
            raise ValueError('existing binding calls/build have not completed')
        verify_builder_schedule((HERE/'build_handoff_kernel.py').read_bytes())
        identity = {'project_head': os.environ.get('GITHUB_SHA',''),
                    'run_id': int(os.environ.get('GITHUB_RUN_ID','0')),
                    'attempt': int(os.environ.get('GITHUB_RUN_ATTEMPT','0')),
                    'kernel_source_commit': self.kernel}
        require_identity(identity)
        document = {'schema': SCHEMA, 'identity': identity, 'build_completed': True,
                    'execution_scope': 'existing builder calls and nested canonical validator entrypoints; excludes subprocess models/tests',
                    'builder_path': 'note10/device_test/build_handoff_kernel.py',
                    'builder_sha256': sha((HERE/'build_handoff_kernel.py').read_bytes()),
                    'recorder_path': 'note10/device_test/binding_validation_manifest.py',
                    'recorder_sha256': sha(Path(__file__).read_bytes()),
                    'direct_calls': [{'validator': name,'require_package_flow': stage} for name,stage in active_direct(self.report)],
                    'calls': self.calls}
        proof_fields = {}
        for record in self.calls:
            for proof in record['proofs']:
                mapping = proof_fields.setdefault(record['validator'],{})
                if proof['path'] in mapping and mapping[proof['path']] != proof['sha256']:
                    raise ValueError('validator proof changed between existing calls')
                mapping[proof['path']] = proof['sha256']
        document['validator_order'] = list(dict.fromkeys(record['validator'] for record in self.calls))
        document['multiplicities'] = {name:sum(record['validator']==name for record in self.calls) for name in document['validator_order']}
        temporary_report = dict(self.report, binding_validation_proof_sha256=proof_fields)
        verify_document(document,self.root,temporary_report,identity,
                        lambda name: safe_file(HERE.parents[1],name).read_bytes())
        raw = (json.dumps(document,indent=2)+'\n').encode('utf8')
        output = self.root/FILENAME
        if output.exists() or output.is_symlink(): raise ValueError('binding manifest already exists/unsafe')
        output.write_bytes(raw)
        return {'binding_validation_result_sha256':sha(raw),'binding_validation_schema':SCHEMA,
                'binding_validation_proof_sha256':proof_fields}


def require_identity(identity):
    if (not isinstance(identity,dict) or set(identity)!={'project_head','run_id','attempt','kernel_source_commit'} or
            not isinstance(identity['project_head'],str) or re.fullmatch(r'[0-9a-f]{40}',identity['project_head']) is None or
            type(identity['run_id']) is not int or identity['run_id']<=0 or
            type(identity['attempt']) is not int or identity['attempt']!=1 or identity['kernel_source_commit']!=KERNEL_COMMIT):
        raise ValueError('binding manifest CI/project/kernel identity malformed')


def verify_document(document, artifact, report, identity, source_loader):
    """Inspect saved audit/proofs only; never import or run any old validator."""
    require_identity(identity)
    if not isinstance(document,dict):raise ValueError('binding manifest must be an object')
    require_identity(document.get('identity'))
    if (not isinstance(document,dict) or document.get('schema')!=SCHEMA or type(document.get('schema')) is not int or
            document.get('identity')!=identity or document.get('build_completed') is not True or
            report.get('build_passed') is not True or report.get('source_commit')!=KERNEL_COMMIT):
        raise ValueError('binding manifest/build identity differs')
    for key,expected_path in (('builder','note10/device_test/build_handoff_kernel.py'),
                              ('recorder','note10/device_test/binding_validation_manifest.py')):
        if document.get(key+'_path')!=expected_path or document.get(key+'_sha256')!=sha(source_loader(expected_path)):
            raise ValueError('binding manifest builder/recorder differs from exact project HEAD')
    verify_builder_schedule(source_loader(document['builder_path']))
    expected = expected_calls(report)
    calls = document.get('calls')
    if not isinstance(calls,list) or len(calls)!=len(expected): raise ValueError('binding call cardinality differs')
    if document.get('direct_calls')!=[{'validator':name,'require_package_flow':stage} for name,stage in active_direct(report)]:
        raise ValueError('binding direct call order/multiplicity differs')
    proof_fields = {}
    for sequence,(record,wanted) in enumerate(zip(calls,expected)):
        if (not isinstance(record,dict) or type(record.get('sequence')) is not int or
                record.get('sequence')!=sequence or
                any(type(record.get(k)) is not type(v) or record.get(k)!=v for k,v in wanted.items())):
            raise ValueError('binding actual nested call order/multiplicity differs')
        name=wanted['validator'];module_path='note10/device_test/'+name+'.py'
        if (record.get('entrypoint')!=ENTRYPOINTS[name] or record.get('module_path')!=module_path or
                record.get('module_sha256')!=sha(source_loader(module_path))):
            raise ValueError('executed validator module differs from exact project HEAD')
        outcome=record.get('returned_outcome')
        if (record.get('completed_without_exception') is not True or not isinstance(outcome,dict) or
                not isinstance(outcome.get('type'),str) or not outcome['type'] or
                (outcome['type']=='builtins.bool' and outcome.get('value') is not True)):
            raise ValueError('binding validator did not return a successful completed outcome')
        proofs=record.get('proofs');names=proof_names(name,wanted['require_package_flow'])
        if not isinstance(proofs,list) or [proof.get('path') for proof in proofs]!=names:
            raise ValueError('binding per-invocation actual proof inventory differs')
        for proof in proofs:
            path=proof['path'];digest=sha(safe_file(artifact,path).read_bytes())
            if proof.get('sha256')!=digest or proof.get('build_report_field')!=['binding_validation_proof_sha256',name,path]:
                raise ValueError('binding actual proof hash/report path differs')
            existing=EXISTING_FIELDS.get(path)
            if existing and report.get(existing)!=digest:raise ValueError('binding existing build-report proof digest differs')
            proof_fields.setdefault(name,{})[path]=digest
    order=list(dict.fromkeys(record['validator'] for record in calls))
    counts={name:sum(record['validator']==name for record in calls) for name in order}
    wanted_order=list(dict.fromkeys(item['validator'] for item in expected))
    if order!=wanted_order or document.get('validator_order')!=order or document.get('multiplicities')!=counts:
        raise ValueError('binding unique validator inventory/order/multiplicities differ')
    if report.get('binding_validation_proof_sha256')!=proof_fields:raise ValueError('binding build-report proof map differs')
    return {'passed':True,'schema':SCHEMA,'identity':identity,'validator_order':order,
            'binding_validator_count':len(order),'actual_invocation_count':len(calls),'multiplicities':counts,
            'historical_validators_replayed_locally':False}


def verify_manifest(artifact,report,identity,source_loader):
    path=safe_file(artifact,FILENAME);raw=path.read_bytes()
    if (type(report.get('binding_validation_schema')) is not int or report['binding_validation_schema']!=SCHEMA or
            report.get('binding_validation_result_sha256')!=sha(raw)):
        raise ValueError('actual binding manifest digest/schema differs')
    result=verify_document(json.loads(raw),artifact,report,identity,source_loader)
    return dict(result,manifest_sha256=sha(raw))
