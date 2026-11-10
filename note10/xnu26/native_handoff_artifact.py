"""Stage one bounded native kernel and its same-run receipts for existing sealing."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from current_native_kernel import digest
from prepare_memdev_wide_extent import PATCH_SHA256, POSTIMAGE_SHA256

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT / 'note10/private'
BUILD = PRIVATE / 'v173-native-kernel-artifact-build'
SUMMARY = PRIVATE / 'v173-native-kernel-artifact-result/result.json'
STAGE = PRIVATE / 'v173-native-kernel-artifact-stage'
ZIP = PRIVATE / 'v173-native-kernel-artifact.zip'
KERNEL_MAX = 32 * 1024 * 1024
META_MAX = 8 * 1024 * 1024
TOTAL_MAX = 64 * 1024 * 1024
RECEIPTS = {
    'producer-context.json': 'producer-context.json',
    'current-object-receipts.json': 'current-object-receipts.json',
    'storage-receipts.json': 'storage-receipts.json',
    'link-result.json': 'link-result.json',
    'native-state.json': 'result.json',
    'native-objects.filelist': 'native-objects.filelist',
}


class Rejected(ValueError):
    pass


def require(condition, code):
    if not condition:
        raise Rejected(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def read(path, limit, *, observations=None, member=None):
    if observations is not None:
        try:
            size = path.lstat().st_size
        except OSError:
            size = None
        observations.append(dict(member=member, observed_bytes=size, limit_bytes=limit))
    require(path.resolve() == path.absolute() and not path.is_symlink() and path.is_file(), 'ordinary_input_required')
    require(0 < path.stat().st_size <= limit, 'input_size_limit')
    with path.open('rb') as stream:
        raw = stream.read(limit + 1)
    require(0 < len(raw) <= limit and len(raw) == path.stat().st_size, 'input_size_changed')
    return raw


def success_payloads(build, producer, head, run_id, attempt, *, compact=False, observations=None):
    if compact:
        from compact_native_receipts import RAW_MAX
    receipts = {}
    for name, relative in RECEIPTS.items():
        limit = RAW_MAX if compact and name == 'current-object-receipts.json' else META_MAX
        receipts[name] = read(build / relative, limit, observations=observations, member='ownership/'+name)
    current = json.loads(receipts['producer-context.json'])
    rows = None if compact else json.loads(receipts['current-object-receipts.json'])
    storage = json.loads(receipts['storage-receipts.json'])
    link = json.loads(receipts['link-result.json'])
    state = json.loads(receipts['native-state.json'])
    ci = current['producer']['ci_context']
    require(ci['GITHUB_SHA'] == head and ci['GITHUB_RUN_ID'] == str(run_id) and
            ci['GITHUB_RUN_ATTEMPT'] == str(attempt) and current['producer']['source_commit'] == head,
            'same_run_source_required')
    require(current['producer_id'] == digest(current['producer']) and
            current['input_binding'] == digest(current['bindings']), 'current_identity_required')
    if compact:
        from compact_native_receipts import project
        rows, receipts['current-object-receipts.json'] = project(receipts['current-object-receipts.json'],
            current, storage, link, receipts['native-objects.filelist'], producer)
    for key in ('producer_id', 'input_binding'):
        require(state[key] == link[key] == current[key] and
                all(row[key] == current[key] for row in rows + storage['units']), 'receipt_identity_required')
    require(state['passed'] is True and state['phase'] == 'complete' and link['link_succeeded'] is True and
            link['returncode'] == 0 and link['object_count'] == producer['final_object_count'] == 1077 and
            len(current['inventory']) == 1067 and len(rows) == 1071 and len(storage['units']) == 6 and
            all(row['passed'] is True for row in rows + storage['units']), 'complete_ownership_required')
    paths = receipts['native-objects.filelist'].decode('utf-8').splitlines()
    require(paths == [row['object_path'] for row in rows + storage['units']] and len(set(paths)) == 1077 and
            link['filelist_sha256'] == sha(receipts['native-objects.filelist']), 'exact_filelist_required')
    proof = state['memdev']
    require(proof == producer['memdev_integration'] and proof['kernel_link_verified'] is True and
            proof['provider_binding_verified'] is True and proof['extra_patch']['postimage_sha256'] == POSTIMAGE_SHA256 and
            proof['extra_patch']['patch_sha256'] == PATCH_SHA256 and
            proof['memdev_member']['source_sha256'] == POSTIMAGE_SHA256, 'patched_consumer_required')
    kernel = read(build / 'current-native.macho', KERNEL_MAX, observations=observations, member='kernel/note10-experimental.macho')
    require(sha(kernel) == state['output_sha256'] == producer['kernel_sha256'] and
            len(kernel) == state['output_bytes'] == producer['kernel_bytes'], 'kernel_identity_required')
    ownership = [{'file': 'ownership/' + name, 'bytes': len(raw), 'sha256': sha(raw)}
                 for name, raw in sorted(receipts.items())]
    manifest = dict(schema='note10-v174-native-handoff-build-v1' if compact else 'note10-v173-native-handoff-build-v1', source_commit=head,
                    run_id=run_id, run_attempt=attempt, output_sha256=sha(kernel), output_size=len(kernel),
                    kernel_file='note10-experimental.macho', producer_id=current['producer_id'],
                    input_binding=current['input_binding'], extra_memdev_patch=proof['extra_patch'],
                    ownership=ownership, physical_reservation_verified=False, hardware_verified=False,
                    deployment_ready=False, device_operations=[])
    return {'kernel/note10-experimental.macho': kernel, 'kernel/build-manifest.json': encoded(manifest),
            **{'ownership/' + name: raw for name, raw in receipts.items()}}


def stage(build, summary, destination, *, head, run_id, attempt, compact=False):
    require(re.fullmatch('[0-9a-f]{40}', head) and type(run_id) is int and run_id > 0 and type(attempt) is int and attempt == 1,
            'exact_dispatch_identity_required')
    require(not destination.exists() and not destination.is_symlink() and
            destination.resolve() == destination.absolute(), 'fresh_stage_required')
    producer, payloads, code, error_type = None, {}, 'producer_not_passed', None
    observations = [] if compact else None
    failure_input = None
    try:
        producer = json.loads(read(summary, META_MAX, observations=observations, member='producer-result.json'))
        expected_schema = 'note10-v174-native-kernel-artifact-result-v1' if compact else 'note10-v173-native-kernel-artifact-result-v1'
        require(producer['schema'] == expected_schema and
                producer['source_head'] == head and producer['run_id'] == run_id and
                producer['run_attempt'] == attempt, 'producer_identity_required')
        if producer['passed'] is True:
            payloads = success_payloads(build, producer, head, run_id, attempt, compact=compact, observations=observations)
            code = 'none'
    except (OSError, ValueError, KeyError, TypeError) as error:
        payloads = {}
        code = str(error) if isinstance(error, Rejected) else 'input_read_or_shape_failed'
        if compact:
            from compact_native_receipts import CODES
            if str(error) in CODES:
                code = str(error)
            if code in {'ordinary_input_required', 'input_size_limit', 'input_size_changed'} and observations:
                failure_input = dict(observations[-1])
        error_type = type(error).__name__
    record = dict(schema='note10-v174-sealed-native-handoff-result-v1' if compact else 'note10-v173-sealed-native-handoff-result-v1', source_commit=head,
                  run_id=run_id, run_attempt=attempt, kernel_retained=code == 'none',
                  packaging_failure_code=code, producer_result=producer,
                  deployment_ready=False, physical_reservation_verified=False, device_operations=[])
    if compact:
        record['member_observations'] = observations
        if failure_input is not None:
            record['failure_input'] = failure_input
    if error_type:
        record['error_type'] = error_type
    if code != 'none':
        state_path = build / 'result.json'
        if state_path.exists():
            try:
                payloads['ownership/native-state.json'] = read(state_path, META_MAX)
            except (OSError, ValueError):
                record['native_state_retained'] = False
    payloads['result.json'] = encoded(record)
    members = [dict(file=name, bytes=len(raw), sha256=sha(raw)) for name, raw in sorted(payloads.items())]
    payloads['members.json'] = encoded(dict(schema='note10-v174-sealed-native-members-v1' if compact else 'note10-v173-sealed-native-members-v1',
        source_commit=head, run_id=run_id, run_attempt=attempt, kernel_retained=record['kernel_retained'], members=members))
    require(all(len(raw) <= (KERNEL_MAX if name.endswith('.macho') else META_MAX)
                for name, raw in payloads.items()) and sum(map(len, payloads.values())) <= TOTAL_MAX, 'stage_total_limit')
    destination.mkdir(parents=True, exist_ok=False)
    for name, raw in payloads.items():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(raw)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compact', action='store_true')
    compact = parser.parse_args().compact
    head, run = os.environ.get('GITHUB_SHA', ''), os.environ.get('GITHUB_RUN_ID', '')
    require(os.environ.get('GITHUB_REPOSITORY') == 'eirblue/ios_note10p' and
            sys.platform == 'darwin' and os.environ.get('GITHUB_ACTIONS') == 'true' and
            os.environ.get('GITHUB_EVENT_NAME') == 'workflow_dispatch' and
            os.environ.get('GITHUB_JOB') == 'current-native-selected-link' and
            os.environ.get('GITHUB_WORKFLOW_SHA') == head == os.environ.get('N10_EXPECTED_SOURCE_HEAD') and
            os.environ.get('GITHUB_WORKFLOW_REF') == 'eirblue/ios_note10p/.github/workflows/note10-iostorage-final-link-pc.yml@refs/heads/main' and
            os.environ.get('GITHUB_RUN_ATTEMPT') == '1' and re.fullmatch('[1-9][0-9]*', run), 'exact_workflow_required')
    build, summary, destination, output = BUILD, SUMMARY, STAGE, ZIP
    if compact:
        build = PRIVATE / 'v174-native-kernel-artifact-build'
        summary = PRIVATE / 'v174-native-kernel-artifact-result/result.json'
        destination = PRIVATE / 'v174-native-kernel-artifact-stage'
        output = PRIVATE / 'v174-native-kernel-artifact.zip'
    record = stage(build, summary, destination, head=head, run_id=int(run), attempt=1, compact=compact)
    absent_tests = PRIVATE / ('v174-no-old-tests' if compact else 'v173-no-old-tests')
    require(not absent_tests.exists(), 'no_old_test_root_required')
    subprocess.run([sys.executable, '-B', str(ROOT / 'note10/device_test/bundle_affinity_evidence.py'),
                    '--tests', str(absent_tests), '--build', str(destination), '--output', str(output), '--source', head],
                   cwd=ROOT, check=True, timeout=180)
    require(output.stat().st_size <= TOTAL_MAX, 'zip_size_limit')
    return 0 if record['kernel_retained'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
