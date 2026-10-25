"""Create a relocatable, data-only RAM-stage image from a verified XNU artifact.

This creates kernel.mem for the Linux staging diagnostic. It does not choose
physical addresses, modify the source artifact, build an iOS image, or execute XNU.
"""
import argparse
import hashlib
import json
from pathlib import Path
from handoff_bundle import materialize_kernel
from verify_experimental_artifact import verify

ROOT = Path(__file__).resolve().parents[2]


def build(artifact: Path, output: Path):
    artifact = artifact.resolve()
    output = output.resolve()
    if not output.is_relative_to((ROOT / 'note10/private').resolve()):
        raise ValueError('Private output directory required')
    if output.exists():
        raise ValueError('Refusing existing output directory')
    checked = verify(artifact)
    raw = (artifact / 'note10-experimental.macho').read_bytes()
    base, payload = materialize_kernel(raw, checked['segments'])
    if not payload or len(payload) > 64 * 1024 * 1024 or len(payload) % 0x4000:
        raise ValueError('Unexpected bounded 16K-aligned XNU memory image')
    output.mkdir(parents=True, exist_ok=False)
    target = output / 'kernel.mem'
    target.write_bytes(payload)
    report = {
        'schema': 1,
        'purpose': 'xnu-data-only-ram-stage',
        'source_kind': 'experimental-source-built-arm64-macho',
        'source_macho_sha256': checked['sha256'],
        'source_macho_size': len(raw),
        'virtual_base': hex(base),
        'entry_virtual_address': checked['entry_virtual_address'],
        'payload_file': target.name,
        'payload_size': len(payload),
        'payload_sha256': hashlib.sha256(payload).hexdigest(),
        'physical_address': None,
        'physical_reservation_verified': False,
        'deployment_ready': False,
        'device_operations': [],
        'xnu_executed': False,
    }
    (output / 'payload-manifest.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = build(args.artifact, args.output)
    print(json.dumps({key: result[key] for key in ('payload_file', 'payload_size', 'payload_sha256', 'deployment_ready')}))
