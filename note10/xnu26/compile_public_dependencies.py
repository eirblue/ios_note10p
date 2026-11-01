"""Compile a pinned, genuine public kernel firehose implementation as a candidate.

No fake logging entry points are supplied. Object compilation does not establish
that this libdispatch revision is ABI-compatible with all target userland inputs.
"""
import hashlib
import json
from pathlib import Path
import subprocess
from prepare_build_selection import ROOT

COMMIT = '2361ffb78a76f7ee488cd052eb0bc5c767118bf9'


def main(current=None, base_command=None):
    private = ROOT / 'note10/private/windows-xnu'
    target = json.loads((ROOT / 'note10/target.json').read_text())
    library = ROOT / target['research_directory'] / ('libdispatch-' + COMMIT)
    configured = json.loads((private / 'configure-result.json').read_text())
    source = ROOT / configured['source_directory']
    audit = json.loads((private / 'objects/DEVELOPMENT/all-c-result.json').read_text()) if current is None else None
    # libdispatch's kernel firehose mixes BSD and libkern interfaces. Reuse the
    # successful libkern logging environment, not Mach's conflicting clock_t and
    # standalone libsa types namespace.
    if current is None:
        base_command = next(r for r in audit['units'] if r['source'] == 'libkern/os/log.c')['command']
    command = list(base_command)
    original = library / 'src/firehose/firehose_buffer.c'
    obj = private / 'objects/DEVELOPMENT/public_libdispatch_firehose_buffer.c.o'
    command[command.index('-c') + 1] = str(original)
    command[command.index('-o') + 1] = str(obj)
    command += ['-DLIBKERN_KERNEL_PRIVATE=1', '-DOS_FIREHOSE_SPI=1',
                '-I', str(source / 'libkern/firehose'), '-I', str(library)]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=60)
    log = private / 'public-dependencies.log'; log.write_bytes(result.stdout + result.stderr)
    passed = result.returncode == 0
    report = {'units': [{'source': '@public/libdispatch/firehose_buffer.c', 'passed': passed,
                         'command': command, 'source_sha256': hashlib.sha256(original.read_bytes()).hexdigest(),
                         'object_sha256': hashlib.sha256(obj.read_bytes()).hexdigest() if passed else None}],
              'public_source': 'https://github.com/apple-oss-distributions/libdispatch/tree/' + COMMIT,
              'target_userland_abi_verified': False, 'whole_kernel_build': False}
    if current is not None:
        from current_native_kernel import stamp
        stamp(current, report['units'][0], 'public')
        report['units'][0]['object_path'] = str(obj)
    (private / ('current-public-result.json' if current is not None else 'public-dependencies-result.json')).write_text(json.dumps(report, indent=2))
    print(json.dumps({'public_firehose_compiled': passed, 'target_userland_abi_verified': False}), flush=True)
    if current is not None and not passed:
        raise RuntimeError('current public firehose compilation failed')
    return report


if __name__ == '__main__':main()
