"""Synthetic production package and independent collector row tests for v53."""
import argparse
import copy
import hashlib
import json
from contextlib import contextmanager
from pathlib import Path
import tempfile
from prepare_cpu_pm_notifier_trace import SOURCES, FLAG, VERSION, PREFIX
from cpu_pm_roundtrip_binding import trace_package_scope, _validate_trace, PACKAGE_SOURCES
from test_cpu_pm_notifier_trace import evidence

HERE = Path(__file__).resolve().parent
CASES = ('production-trace-on', 'production-trace-off-counts-on',
         'production-trace-off-counts-off', 'collector-trace-pass',
         'collector-missing-fails-only-trace', 'collector-partial-fails-only-trace',
         'collector-conflict-fails-only-trace', 'collector-terminal-fails-all',
         'scope-requires-counts', 'scope-null-rejected', 'scope-stray-proof-rejected',
         'scope-package-proof-rejected', 'scope-unknown-rejected',
         'binding-config-mismatch', 'binding-image-mismatch', 'binding-source-mismatch',
         'binding-prepared-mismatch', 'binding-model-mismatch',
         'binding-executable-missing', 'binding-executable-both',
         'binding-disabled-evidence', 'binding-package-mismatch')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


@contextmanager
def fixture_workspace(artifact):
    """Use the production private root and reject overlap before fixture copies."""
    artifact_root = Path(artifact).resolve()
    private_path = HERE.parent/'private'
    if private_path.is_symlink() or not private_path.is_dir():
        raise ValueError('trace fixture private root is missing or unsafe')
    private_root = private_path.resolve()
    with tempfile.TemporaryDirectory(dir=private_root, prefix='cpu-pm-trace-fixture-') as temporary:
        workspace = Path(temporary).resolve()
        if workspace == private_root or not workspace.is_relative_to(private_root):
            raise ValueError('trace fixture workspace must remain inside the private root')
        if workspace.is_relative_to(artifact_root) or artifact_root.is_relative_to(workspace):
            raise ValueError('trace fixture workspace must be disjoint from artifact')
        yield workspace


def reject(function, *args, **kwargs):
    try:
        function(*args, **kwargs)
    except (ValueError, FileNotFoundError):
        return True
    raise AssertionError('invalid trace scope or binding accepted')


def collector_cases():
    from collect_reservation import decode_cpu_pm_roundtrip_observation as collect
    results = {}
    cases = (('collector-trace-pass', evidence(), 'passed', 'passed', 'passed'),
             ('collector-missing-fails-only-trace', '\n'.join(line for line in evidence().splitlines()
              if not line.startswith('N10CPD1')), 'passed', 'passed', 'failed'),
             ('collector-partial-fails-only-trace', evidence(trace_changes={'er': 5}), 'passed', 'passed', 'failed'),
             ('collector-conflict-fails-only-trace', evidence(trace_changes={'conflict': 1}), 'passed', 'passed', 'failed'),
             ('collector-terminal-fails-all', evidence(terminal=True), 'failed', 'failed', 'failed'))
    for name, text, pair, counts, trace in cases:
        observed = collect(text, 'a'*32, 43, True, True)
        if [observed[key]['status'] for key in ('evaluation_item', 'counts_evaluation_item', 'trace_evaluation_item')] != [pair, counts, trace]:
            raise AssertionError('independent collector row changed: '+name)
        results[name] = True
    return results


def binding_cases(artifact, output, build):
    """Mutate private copied inputs; original saved artifact remains immutable."""
    import shutil
    from prepare_cpu_pm_notifier_trace import BASE, PREPARED, MODEL, PACKAGE, TARGETS
    results = {}
    mutations = ('binding-config-mismatch', 'binding-image-mismatch', 'binding-source-mismatch',
                 'binding-prepared-mismatch', 'binding-model-mismatch', 'binding-executable-missing',
                 'binding-executable-both', 'binding-disabled-evidence', 'binding-package-mismatch')
    for name in mutations:
        root = output / name; root.mkdir()
        for dirname in (BASE, PREPARED, MODEL, 'cpu-pm-roundtrip-prepared'):
            shutil.copytree(artifact/dirname, root/dirname)
        # Compact image retains the exact marker scope; this validator's Image
        # checks are scoped, full Image/config hashes stay with the actual gate.
        (root/'Image').write_bytes(b'N10CPDC1')
        shutil.copyfile(artifact/'handoff.config', root/'handoff.config')
        metadata = copy.deepcopy(build)
        if name == 'binding-config-mismatch':
            path=root/'handoff.config';path.write_bytes(path.read_bytes().replace(b'CONFIG_NOTE10_CPU_PM_NOTIFIER_TRACE=y',b'CONFIG_NOTE10_CPU_PM_NOTIFIER_TRACE=n'))
        elif name == 'binding-image-mismatch': (root/'Image').write_bytes(b'')
        elif name == 'binding-source-mismatch': metadata[PREFIX+'sources_sha256']['prepare_cpu_pm_notifier_trace.py']='0'*64
        elif name == 'binding-prepared-mismatch':
            path=root/PREPARED/TARGETS[0];path.write_bytes(path.read_bytes()+b'\n')
        elif name == 'binding-model-mismatch': metadata[PREFIX+'model_sha256']='0'*64
        elif name in ('binding-executable-missing', 'binding-executable-both'):
            executable=next(path for path in (root/MODEL/'dispatch-native',root/MODEL/'dispatch-native.exe') if path.is_file())
            if name.endswith('missing'):executable.unlink()
            else:(root/MODEL/('dispatch-native.exe' if executable.name=='dispatch-native' else 'dispatch-native')).write_bytes(executable.read_bytes())
        elif name == 'binding-disabled-evidence':
            metadata={k:v for k,v in metadata.items() if not k.startswith(PREFIX)}
            metadata[FLAG]=False;metadata[VERSION]=None
            path=root/'handoff.config';path.write_bytes(path.read_bytes().replace(b'CONFIG_NOTE10_CPU_PM_NOTIFIER_TRACE=y',b'CONFIG_NOTE10_CPU_PM_NOTIFIER_TRACE=n'))
            (root/'Image').write_bytes(b'')
        elif name == 'binding-package-mismatch':
            (root/PACKAGE).mkdir();(root/PACKAGE/'result.json').write_text('{}',encoding='ascii')
            metadata[PREFIX+'package_sha256']='0'*64
        results[name]=reject(_validate_trace,root,metadata,require_package_flow=name=='binding-package-mismatch')
    return results


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--artifact',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    if args.output.exists() or args.output.is_symlink():raise ValueError('fresh trace package output required')
    build=json.loads((args.artifact/'build-result.json').read_text(encoding='utf8'))
    if trace_package_scope(build,allow_build_proof=True) is not True:raise ValueError('trace enabled artifact required')
    _validate_trace(args.artifact,build)
    args.output.mkdir(parents=True)
    results=collector_cases()
    # Use actual production-prepared metadata below for the scope mutation cases.
    from test_cpu_pm_roundtrip_package_flow import _prepare_packages
    with fixture_workspace(args.artifact) as root:
        on=_prepare_packages(root,args.artifact,'trace-on','f'*32,True,True,True)
        off_counts=_prepare_packages(root,args.artifact,'trace-off-counts','e'*32,True,True,False)
        off=_prepare_packages(root,args.artifact,'trace-off','d'*32,True,False,False)
        for name,fixture,expected in (('production-trace-on',on,True),
                                     ('production-trace-off-counts-on',off_counts,False),
                                     ('production-trace-off-counts-off',off,False)):
            package=json.loads((fixture['packages']/'package-result.json').read_text(encoding='utf8'))
            if (trace_package_scope(fixture['report']) is not expected or
                trace_package_scope(package) is not expected or
                fixture['precheck'].get('cpu_pm_notifier_trace_scope_verified') is not expected or
                fixture['collector'].get('cpu_pm_notifier_trace_scope_verified') is not expected):
                raise AssertionError('production trace package scope differs')
            from stage_phase2 import verify_packages
            records=verify_packages(fixture['packages'])
            if any(trace_package_scope(record) is not (expected and record['mode']=='diagnostic') for record in records):
                raise AssertionError('trace rollback scope differs')
            results[name]=True
        on_items=on['collector']['evaluation_items'];off_items=off_counts['collector']['evaluation_items']
        if {k:v for k,v in on_items.items() if k!='cpu0_cpu_pm_dispatch_trace'}!=off_items:
            raise AssertionError('trace changed existing collector rows')
        if on_items.get('cpu0_cpu_pm_dispatch_trace')!={'required':True,'status':'failed'}:
            raise AssertionError('missing trace log did not fail only new row')
        metadata=json.loads((on['packages']/'package-result.json').read_text(encoding='utf8'))
        for name in ('scope-requires-counts','scope-null-rejected','scope-stray-proof-rejected',
                     'scope-package-proof-rejected','scope-unknown-rejected'):
            bad=copy.deepcopy(metadata)
            if name=='scope-requires-counts':bad['cpu_pm_notifier_counts']=False;bad['cpu_pm_notifier_counts_version']=None
            elif name=='scope-null-rejected':bad[FLAG]=None
            elif name=='scope-stray-proof-rejected':bad[FLAG]=False;bad[VERSION]=None;bad[PREFIX+'model_sha256']='0'*64
            elif name=='scope-package-proof-rejected':bad[PREFIX+'model_sha256']='0'*64
            else:bad[PREFIX+'unknown']=True
            results[name]=reject(trace_package_scope,bad)
    with fixture_workspace(args.artifact) as root:
        results.update(binding_cases(args.artifact,root,build))
    if set(results)!=set(CASES) or not all(results.values()):raise AssertionError('trace package case inventory differs')
    proof={'passed':True,'synthetic_fixture':True,'hardware_verified':False,
           'cases':list(CASES),'results':results,'cpu_pm_validator_scope_only_stub':True,
           'sources_sha256':{n:sha((HERE/n).read_bytes()) for n in SOURCES},
           'package_sources_sha256':{n:sha((HERE/n).read_bytes()) for n in PACKAGE_SOURCES},
           'models_reexecuted':False,'physical_row_matrix':{'trace_on':[45,44],
               'trace_off_counts_on':[44,43],'trace_off_counts_off_roundtrip_on':[43,42]}}
    (args.output/'result.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8',newline='\n')


if __name__=='__main__':main()
