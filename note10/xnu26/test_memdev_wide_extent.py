"""Prepare one fresh source-bound C arithmetic fixture; ROOT compiles/runs it."""
import argparse
import hashlib
import json
from pathlib import Path

from prepare_memdev_wide_extent import (
    REL, PATCH_NAME, REFERENCE_PINS, fixture_header, patch_bytes, transformed,
)

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    private = ROOT / 'note10/private'
    if (output == private or not output.is_relative_to(private) or output.exists() or
            source.is_relative_to(output) or output.is_relative_to(source)):
        parser.error('fresh private output separate from source required')
    references = {}
    for name, (size, digest) in REFERENCE_PINS.items():
        path = source / name
        if not path.is_file() or path.stat().st_size != size:
            raise ValueError('bounded reference source required: ' + name)
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError('reference source differs: ' + name)
        references[name] = raw
    after = transformed(references[REL])
    patch = patch_bytes(references[REL])
    public_patch = ROOT / 'note10/xnu26/patches' / PATCH_NAME
    if public_patch.stat().st_size != len(patch) or public_patch.read_bytes() != patch:
        raise ValueError('literal opt-in patch differs')
    header = fixture_header(after, references)
    output.mkdir(parents=True)
    files = {'memdev.c': after, PATCH_NAME: patch, 'memdev-arithmetic.h': header}
    for name, raw in files.items():
        with (output / name).open('xb') as stream:
            stream.write(raw)
    record = dict(schema='note10-v168-memdev-wide-extent-prepared-v1', prepare_attempts=1,
        shifted_sites=8, char_count_clamped=True, cases_planned=9,
        generated={name: dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
                   for name, raw in files.items()},
        reference_sha256={name: digest for name, (_, digest) in REFERENCE_PINS.items()},
        tests_executed=0, compiler_runs=0, reference_mutation=False, device_operations=0)
    with (output / 'PREPARED.json').open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(record, indent=2) + '\n')


if __name__ == '__main__':
    main()
