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


def main():
    private = ROOT / 'note10/private/windows-xnu'
    target = json.loads((ROOT / 'note10/target.json').read_text())
    library = ROOT / target['research_directory'] / ('libdispatch-' + COMMIT)
    configured = json.loads((private / 'configure-result.json').read_text())
    source = ROOT / configured['source_directory']
    audit = json.loads((private / 'objects/DEVELOPMENT/all-c-result.json').read_text())
    # libdispatch's kernel firehose mixes BSD and libkern interfaces. Reuse the
    # successful libkern logging environment, not Mach's conflicting clock_t and
    # standalone libsa types namespace.
    unit = next(r for r in audit['units'] if r['source'] == 'libkern/os/log.c')
    command = list(unit['command'])
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
    (private / 'public-dependencies-result.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({'public_firehose_compiled': passed, 'target_userland_abi_verified': False}), flush=True)


if __name__ == '__main__':main()
