"""Four new groups for fixed native handoff artifact staging; no compiler or crypto."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import native_handoff_artifact as artifact


HEAD = '1' * 40
KERNEL = b'synthetic kernel bytes only'


def fixture(name):
    parent = OUTPUT / name
    build = parent / 'build'
    build.mkdir(parents=True)
    context = {'producer': {'source_commit': HEAD, 'ci_context': {
        'GITHUB_SHA': HEAD, 'GITHUB_RUN_ID': '1', 'GITHUB_RUN_ATTEMPT': '1'}},
        'bindings': {'synthetic': True}, 'inventory': [{'source': str(i)} for i in range(1067)]}
    context.update(producer_id=artifact.digest(context['producer']), input_binding=artifact.digest(context['bindings']))
    rows = [{'object_path': '/synthetic/' + str(i) + '.o', 'passed': True,
             'producer_id': context['producer_id'], 'input_binding': context['input_binding']}
            for i in range(1077)]
    filelist = ''.join(row['object_path'] + '\n' for row in rows).encode()
    proof = {'kernel_link_verified': True, 'provider_binding_verified': True,
             'extra_patch': {'postimage_sha256': artifact.POSTIMAGE_SHA256,
                             'patch_sha256': artifact.PATCH_SHA256},
             'memdev_member': {'source_sha256': artifact.POSTIMAGE_SHA256}}
    state = {'passed': True, 'phase': 'complete', 'producer_id': context['producer_id'],
             'input_binding': context['input_binding'], 'output_sha256': hashlib.sha256(KERNEL).hexdigest(),
             'output_bytes': len(KERNEL), 'memdev': proof}
    summary = {'schema': 'note10-v173-native-kernel-artifact-result-v1', 'source_head': HEAD,
               'run_id': 1, 'run_attempt': 1, 'passed': True, 'final_object_count': 1077,
               'kernel_sha256': state['output_sha256'], 'kernel_bytes': len(KERNEL), 'memdev_integration': proof}
    values = {'producer-context.json': context, 'current-object-receipts.json': rows[:1071],
              'storage-receipts.json': {'units': rows[1071:]}, 'result.json': state,
              'link-result.json': {'producer_id': context['producer_id'], 'input_binding': context['input_binding'],
                                  'link_succeeded': True, 'returncode': 0, 'object_count': 1077,
                                  'filelist_sha256': hashlib.sha256(filelist).hexdigest()}}
    for filename, value in values.items():
        (build / filename).write_bytes(artifact.encoded(value))
    (build / 'native-objects.filelist').write_bytes(filelist)
    (build / 'current-native.macho').write_bytes(KERNEL)
    summary_path = parent / 'summary.json'
    summary_path.write_bytes(artifact.encoded(summary))
    return build, summary_path, parent / 'stage'


def stage(data):
    return artifact.stage(*data, head=HEAD, run_id=1, attempt=1)


class NativeHandoffArtifactTests(unittest.TestCase):
    def test_1_exact_success_members_and_manifest(self):
        data = fixture('success')
        record = stage(data)
        self.assertTrue(record['kernel_retained'])
        expected = {'result.json', 'members.json', 'kernel/note10-experimental.macho', 'kernel/build-manifest.json',
                    *('ownership/' + name for name in artifact.RECEIPTS)}
        self.assertEqual({p.relative_to(data[2]).as_posix() for p in data[2].rglob('*') if p.is_file()}, expected)
        self.assertEqual((data[2] / 'kernel/note10-experimental.macho').read_bytes(), KERNEL)
        manifest = json.loads((data[2] / 'kernel/build-manifest.json').read_bytes())
        self.assertEqual((manifest['output_size'], manifest['output_sha256']),
                         (len(KERNEL), hashlib.sha256(KERNEL).hexdigest()))
        self.assertEqual(len(manifest['ownership']), 6)
        self.assertFalse(manifest['physical_reservation_verified'])
        self.assertFalse(manifest['hardware_verified'])
        self.assertFalse(manifest['deployment_ready'])
        self.assertEqual(manifest['device_operations'], [])
        members = json.loads((data[2] / 'members.json').read_bytes())
        self.assertEqual(len(members['members']), 9)
        for row in members['members']:
            raw = (data[2] / row['file']).read_bytes()
            self.assertEqual((row['bytes'], row['sha256']), (len(raw), hashlib.sha256(raw).hexdigest()))

    def test_2_identity_and_kernel_rejections(self):
        for change, code in (('run', 'producer_identity_required'), ('input', 'receipt_identity_required'),
                             ('patch', 'patched_consumer_required'), ('kernel', 'kernel_identity_required')):
            data = fixture(change)
            summary = json.loads(data[1].read_bytes())
            state_path = data[0] / 'result.json'
            state = json.loads(state_path.read_bytes())
            if change == 'run':
                summary['run_id'] = 2
            elif change == 'input':
                state['input_binding'] = '0' * 64
            elif change == 'patch':
                state['memdev']['extra_patch']['postimage_sha256'] = '0' * 64
                summary['memdev_integration'] = state['memdev']
            else:
                (data[0] / 'current-native.macho').write_bytes(b'changed bytes')
            data[1].write_bytes(artifact.encoded(summary))
            state_path.write_bytes(artifact.encoded(state))
            with self.subTest(change=change):
                record = stage(data)
                self.assertEqual(record['packaging_failure_code'], code)
                self.assertFalse(record['kernel_retained'])
                self.assertFalse((data[2] / 'kernel').exists())

    def test_3_partial_failure_preserves_reached_evidence(self):
        data = fixture('partial')
        summary = json.loads(data[1].read_bytes())
        summary.update(passed=False, native_stage='failed', failure_type='SyntheticCompileFailure')
        del summary['kernel_sha256'], summary['kernel_bytes']
        data[1].write_bytes(artifact.encoded(summary))
        raw_state = artifact.encoded({'phase': 'failed', 'memdev': {'stage': 'native-c', 'native_compile_attempts': None}})
        (data[0] / 'result.json').write_bytes(raw_state)
        (data[0] / 'current-native.macho').unlink()
        record = stage(data)
        self.assertFalse(record['kernel_retained'])
        self.assertEqual(record['producer_result'], summary)
        self.assertEqual((data[2] / 'ownership/native-state.json').read_bytes(), raw_state)
        self.assertFalse((data[2] / 'kernel').exists())
        early = OUTPUT / 'preflight'
        early.mkdir()
        record = stage((early / 'absent-build', early / 'absent-summary.json', early / 'stage'))
        self.assertFalse(record['kernel_retained'])
        self.assertIsNone(record['producer_result'])
        self.assertFalse((early / 'stage/ownership').exists())

    def test_4_bounds_fixed_selection_and_fresh_output(self):
        self.assertEqual((artifact.KERNEL_MAX, artifact.META_MAX, artifact.TOTAL_MAX),
                         (32 * 1024 * 1024, 8 * 1024 * 1024, 64 * 1024 * 1024))
        data = fixture('oversize')
        with patch.object(artifact, 'KERNEL_MAX', len(KERNEL) - 1):
            record = stage(data)
        self.assertEqual(record['packaging_failure_code'], 'input_size_limit')
        self.assertFalse((data[2] / 'kernel').exists())
        data = fixture('symlink')
        with patch.object(Path, 'is_symlink', lambda path: path == data[0] / 'current-native.macho'):
            record = stage(data)
        self.assertEqual(record['packaging_failure_code'], 'ordinary_input_required')
        data = fixture('unselected')
        (data[0] / 'unselected-private.log').write_bytes(b'never staged')
        self.assertTrue(stage(data)['kernel_retained'])
        self.assertFalse((data[2] / 'unselected-private.log').exists())
        with self.assertRaisesRegex(artifact.Rejected, 'fresh_stage_required'):
            stage(data)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    OUTPUT = args.output.resolve()
    if not OUTPUT.is_relative_to(artifact.PRIVATE.resolve()) or OUTPUT.exists():
        raise ValueError('Fresh private fixture output required')
    OUTPUT.mkdir(parents=True, exist_ok=False)
    unittest.main(argv=[sys.argv[0]])
