"""Evaluate source header export lists with GNU Make, without SDK/tool discovery.

This evaluates assignment/conditional fragments only, not the full export build.
Missing generated inputs and unsupported fragments remain explicit in the report.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import os
import sys
from prepare_build_selection import ROOT, NDK


def assignments(text):
    output = []; define_depth = 0
    for line in text.replace('\\\n', ' ').splitlines():
        stripped = line.strip()
        if stripped.startswith('define '):define_depth += 1; continue
        if stripped == 'endef':define_depth -= 1; continue
        if define_depth:continue
        if re.match(r'^(?:ifeq|ifneq|ifdef|ifndef|else|endif)\b', stripped):
            output.append(line)
        elif re.match(r'^(?:(?:override|export)\s+)?[A-Za-z_][A-Za-z_0-9]*\s*[:?+]?=', stripped):
            if re.search(r'\$[({]\s*(?:shell|eval)\b', line):continue
            output.append(line)
    return '\n'.join(output)


def main():
    private = ROOT / 'note10/private/windows-xnu'
    source = ROOT / json.loads((private / 'configure-result.json').read_text())['source_directory']
    destination = private / 'source-exports'
    stage = private / 'export-probes'; stage.mkdir(exist_ok=True)
    make = os.environ.get('N10_MAKE') or str(NDK / 'prebuilt/windows-x86_64/bin/make.exe')
    exported = {}; unresolved = []
    for index, path in enumerate(sorted(source.rglob('Makefile'))):
        text = path.read_text(encoding='utf-8', errors='replace')
        if 'EXPORT_MI_LIST' not in text or 'EXPORT_MI_DIR' not in text:continue
        fragment = assignments(text) + '\n$(info N10_DIR=$(EXPORT_MI_DIR))\n$(info N10_FILES=$(EXPORT_MI_LIST))\nnote10_export_probe: ;\n'
        probe = stage / (str(index) + '.mk'); probe.write_text(fragment, encoding='utf-8', newline='\n')
        command = [str(make), '--no-print-directory', '-f', str(probe), 'note10_export_probe',
                   'CURRENT_ARCH_CONFIG=ARM64', 'CURRENT_ARCH_CONFIG_LC=arm64',
                   'CURRENT_MACHINE_CONFIG=EXYNOS9825', 'CURRENT_MACHINE_CONFIG_LC=exynos9825',
                   'PLATFORM=iPhoneOS', 'ARCH=arm64', 'MACHINE=arm64']
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=20)
        if result.returncode:
            unresolved.append({'makefile': path.relative_to(source).as_posix(), 'error': result.stderr}); continue
        info = dict(line.split('=', 1) for line in result.stdout.splitlines() if line.startswith('N10_'))
        directory = info.get('N10_DIR', '')
        component = path.relative_to(source).parts[0]
        for name in info.get('N10_FILES', '').split():
            original = path.parent / name
            if not original.is_file():
                unresolved.append({'makefile': path.relative_to(source).as_posix(), 'missing_export': name}); continue
            output = destination / component / directory / name
            if not output.parent.resolve().is_relative_to(destination.resolve()):raise ValueError('Export path escaped output')
            raw = original.read_bytes(); digest = hashlib.sha256(raw).hexdigest()
            key = output.relative_to(destination).as_posix()
            if key in exported and exported[key]['sha256'] != digest:
                raise ValueError('Conflicting header export: ' + key)
            output.parent.mkdir(parents=True, exist_ok=True)
            if sys.platform == 'darwin':
                # Preserve file identity for #pragma once when a source also
                # includes its local header by quotes. Only the isolated source
                # stage is linked; the pristine reference remains separate.
                if output.exists() or output.is_symlink():output.unlink()
                os.link(original, output)
            else:
                output.write_bytes(raw)
            exported[key] = {'source': original.relative_to(source).as_posix(), 'sha256': digest,
                             'makefile_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    report = {'exported': exported, 'unresolved': unresolved, 'full_make_export_stage': False,
              'files_modified_in_public_source': False,
              'export_file_identity_preserved': sys.platform == 'darwin'}
    (private / 'exports-result.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({'source_exports': len(exported), 'unresolved_export_inputs': len(unresolved), 'full_make_export_stage': False}))


if __name__ == '__main__':
    main()
