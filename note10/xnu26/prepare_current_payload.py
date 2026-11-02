"""Prepare private current-source kernel load bytes and one compressed DATA stream.

No Mach-O reader, physical placement, boot package or execution is performed.
"""
import argparse
import hashlib
import json
import lzma
from pathlib import Path
import re

from handoff_bundle import materialize_kernel

PRIVATE_ROOT = Path(__file__).resolve().parents[1] / 'private'
MAX_BYTES = 64 * 1024 * 1024
MAX_JSON = 2 * 1024 * 1024
PAGE = 0x4000
CI_KEYS = ('GITHUB_SHA', 'GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT', 'GITHUB_JOB',
           'GITHUB_WORKFLOW_REF', 'GITHUB_WORKFLOW_SHA', 'GITHUB_REPOSITORY')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def digest(value):
    return sha(json.dumps(value, sort_keys=True, separators=(',', ':')).encode())


def private(path):
    path = Path(path).absolute()
    root = PRIVATE_ROOT.resolve()
    require(path.resolve() == path and path.is_relative_to(root) and path != root,
            'ordinary private path required')
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'symlink forbidden')
    return path


def bounded_read(path, limit):
    path = private(path)
    require(path.is_file() and 0 < path.stat().st_size <= limit, 'bounded regular input required')
    with path.open('rb') as stream:
        data = stream.read(limit + 1)
    require(0 < len(data) <= limit, 'input exceeds bound')
    return data


def pinned_json(path, expected):
    require(type(expected) is str and re.fullmatch('[0-9a-f]{64}', expected), 'SHA256 pin required')
    data = bounded_read(path, MAX_JSON)
    require(sha(data) == expected, 'accepted JSON pin differs')
    value = json.loads(data)
    require(type(value) is dict, 'JSON object required')
    return value


def expected_ci(source, run, attempt):
    require(type(source) is str and re.fullmatch('[0-9a-f]{40}', source), 'source commit required')
    require(all(type(v) is str and re.fullmatch('[1-9][0-9]*', v) for v in (run, attempt)),
            'positive run and attempt required')
    return dict(zip(CI_KEYS, (source, run, attempt, 'current-native-selected-link',
        'eirblue/ios_note10p/.github/workflows/note10-current-native-selected-link.yml@refs/heads/main',
        source, 'eirblue/ios_note10p')))


def admit(result, context, ci, public_source):
    require(result.get('kind') == 'v84-current-native-selected-link' and
            result.get('phase') == 'complete' and result.get('passed') is True,
            'accepted current producer completion required')
    require(context.get('kind') == 'v84-current-native', 'current producer context required')
    producer, bindings = context['producer'], context['bindings']
    require(type(producer) is dict and type(bindings) is dict, 'producer bindings required')
    require(result.get('ci_context') == ci == producer.get('ci_context') and
            producer.get('source_commit') == ci['GITHUB_SHA'], 'source/run/workflow mismatch')
    require(type(public_source) is str and re.fullmatch('[0-9a-f]{40}', public_source) and
            result.get('public_source_commit') == public_source == producer.get('public_source_commit'),
            'public source mismatch')
    require(producer.get('configuration') == 'DEVELOPMENT_ARM64_EXYNOS9825' and
            type(producer.get('fresh_work_root')) is str and bool(producer['fresh_work_root']),
            'fresh selected configuration required')
    require(not any(k in context for k in ('candidate_archive', 'historical_objects', 'platform_reports')),
            'foreign producer inputs forbidden')
    link = result['link']
    require(link.get('attempted') is True and link.get('link_succeeded') is True and
            type(link.get('returncode')) is int and link['returncode'] == 0 and
            link.get('candidate_archive_used') is False and result.get('candidate_archive_used') is False,
            'successful direct current link required')
    require(result.get('architecture') == 'arm64' and result.get('mach_o_type') == 'MH_EXECUTE' and
            result.get('undefined_symbols') == [] and result.get('old_suites_executed') == 0,
            'current intrinsic output required')
    require(result.get('deployment_ready') is False and result.get('hardware_verified') is False and
            result.get('device_operations') == [], 'host research scope required')
    require(context.get('producer_id') == result.get('producer_id') == link.get('producer_id') == digest(producer)
            and context.get('input_binding') == result.get('input_binding') == link.get('input_binding') == digest(bindings),
            'producer/config binding mismatch')


def geometry(result):
    rows = result['segments']
    require(type(rows) is list and 1 <= len(rows) <= 64, 'bounded intrinsic segments required')
    require(type(result.get('output_bytes')) is int and 0 < result['output_bytes'] <= MAX_BYTES,
            'bounded source bytes required')
    require(type(result.get('output_sha256')) is str and
            re.fullmatch('[0-9a-f]{64}', result['output_sha256']), 'source byte pin required')
    selected = []
    for row in rows:
        require(type(row) is dict, 'segment object required')
        va, size, offset, count = (row[k] for k in ('virtual_address', 'virtual_size', 'file_offset', 'file_size'))
        require(all(type(v) is int and 0 <= v < 1 << 64 for v in (va, size, offset, count)),
                'unsigned segment fields required')
        require(va + size < 1 << 64 and offset + count <= result['output_bytes'] and count <= size,
                'intrinsic segment extent invalid')
        if size:
            selected.append(row)
    require(selected, 'nonzero load extent required')
    base = min(s['virtual_address'] for s in selected)
    end = max(s['virtual_address'] + s['virtual_size'] for s in selected)
    span = (end - base + PAGE - 1) & ~(PAGE - 1)
    require(base % PAGE == 0 and 0 < span <= MAX_BYTES and base + span < 1 << 64,
            'bounded aligned load span required')
    entry = result['entry_virtual_address']
    require(type(entry) is str and re.fullmatch('0x[0-9a-f]+', entry) and
            base <= int(entry, 16) < end, 'intrinsic entry outside span')
    return base, span


def prepare(producer_result, *, producer_sha256, context_sha256, source_commit,
            ci_run_id, ci_run_attempt, public_source_commit, budget, output):
    output = private(output)
    require(not output.exists(), 'fresh output required')
    require(type(budget) is int and 0 < budget <= MAX_BYTES, 'bounded explicit carrier budget required')
    result_path = private(producer_result)
    require(result_path.name == 'result.json', 'fixed current producer result required')
    context_path, kernel_path = (result_path.parent / n for n in ('producer-context.json', 'current-native.macho'))
    require(not any(p == output or p.is_relative_to(output) for p in (result_path, context_path, kernel_path)),
            'output must not contain inputs')
    result = pinned_json(result_path, producer_sha256)
    context = pinned_json(context_path, context_sha256)
    ci = expected_ci(source_commit, ci_run_id, ci_run_attempt)
    admit(result, context, ci, public_source_commit)
    base, span = geometry(result)
    raw = bounded_read(kernel_path, MAX_BYTES)
    require(len(raw) == result['output_bytes'] and sha(raw) == result['output_sha256'],
            'current kernel bytes differ')
    actual_base, payload = materialize_kernel(raw, result['segments'])
    require(actual_base == base and len(payload) == span, 'materialized extent differs')
    compressed = lzma.compress(payload, format=lzma.FORMAT_ALONE, preset=6)
    require(0 < len(compressed) <= MAX_BYTES + 1024 * 1024, 'compressed output bound exceeded')
    report = dict(schema=1, purpose='current-source-payload-preparation',
        producer_result_sha256=producer_sha256, producer_context_sha256=context_sha256,
        ci_context=ci, public_source_commit=public_source_commit, producer_id=result['producer_id'],
        input_binding=result['input_binding'], source_macho_sha256=result['output_sha256'],
        source_macho_bytes=len(raw), virtual_base=hex(base), entry_virtual_address=result['entry_virtual_address'],
        payload_file='kernel.mem', payload_bytes=len(payload), payload_sha256=sha(payload),
        compressed_file='kernel.mem.lzma', compressed_bytes=len(compressed), compressed_sha256=sha(compressed),
        compression=dict(format='LZMA_ALONE', preset=6, streams=1, padding_bytes=0),
        carrier_budget_bytes=budget, fits_budget=len(compressed) <= budget,
        budget_delta_bytes=budget-len(compressed), carrier_admitted=False,
        physical_reservation_verified=False, device_operations=[], xnu_executed=False, deployment_ready=False)
    output.mkdir(parents=True, exist_ok=False)
    for name, data in (('kernel.mem', payload), ('kernel.mem.lzma', compressed),
                       ('payload-fit.json', (json.dumps(report, indent=2)+'\n').encode())):
        with (output / name).open('xb') as stream:
            stream.write(data)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--producer-result', required=True, type=Path)
    for name in ('producer-sha256', 'context-sha256', 'source-commit', 'ci-run-id',
                 'ci-run-attempt', 'public-source-commit'):
        p.add_argument('--'+name, required=True)
    p.add_argument('--budget', required=True, type=int)
    p.add_argument('--output', required=True, type=Path)
    report = prepare(**vars(p.parse_args()))
    print(json.dumps({k: report[k] for k in ('payload_bytes', 'compressed_bytes', 'carrier_budget_bytes',
                                            'fits_budget', 'carrier_admitted', 'deployment_ready')}))
    return 0 if report['fits_budget'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
