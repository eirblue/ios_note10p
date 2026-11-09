"""Produce one complete current native-selected research kernel, with a direct link.

No historical objects, forced candidate archive, partial proof merge or device route.
"""
import argparse
import base64
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys

import build_native_bootstrap_selection as bootstrap
import current_native_kernel as native
from prepare_native_bootstrap_selection import ROOT, COMMIT

PRIVATE = ROOT / 'note10/private'
JOB = 'current-native-selected-link'
WORKFLOW = '.github/workflows/note10-current-native-selected-link.yml'
LEAF_WORKFLOW = '.github/workflows/note10-exynos-leaf-bootstrap-pc.yml'
CHECKED_WORKFLOW = '.github/workflows/note10-exynos-checked-ptpage-pc.yml'
STORAGE_WORKFLOW = '.github/workflows/note10-iostorage-final-link-pc.yml'
LIBDISPATCH = '2361ffb78a76f7ee488cd052eb0bc5c767118bf9'
CASE_IDS = ('test_current_inventory_resolves_owner_and_generated_identity',
            'test_current_context_rejects_stale_candidate_and_partial_objects',
            'test_direct_native_link_uses_current_filelist_and_reports_failure')


def ci_context(leaf=False, checked=False, storage=False):
    result = {k: os.environ.get(k, '') for k in ('GITHUB_SHA', 'GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT',
        'GITHUB_JOB', 'GITHUB_WORKFLOW_REF', 'GITHUB_WORKFLOW_SHA', 'GITHUB_REPOSITORY')}
    workflow = STORAGE_WORKFLOW if storage else (CHECKED_WORKFLOW if checked else (LEAF_WORKFLOW if leaf else WORKFLOW))
    if (not re.fullmatch('[0-9a-f]{40}', result['GITHUB_SHA']) or
        result['GITHUB_WORKFLOW_SHA'] != result['GITHUB_SHA'] or result['GITHUB_JOB'] != JOB or
        result['GITHUB_REPOSITORY'] != 'eirblue/ios_note10p' or
        not result['GITHUB_WORKFLOW_REF'].startswith('eirblue/ios_note10p/' + workflow + '@') or
        any(not re.fullmatch('[1-9][0-9]*', result[k]) for k in ('GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT'))):
        raise ValueError('exact current source/workflow/run/attempt/job required')
    if storage and (sys.platform != 'darwin' or os.environ.get('GITHUB_ACTIONS') != 'true' or
                    os.environ.get('GITHUB_EVENT_NAME') != 'workflow_dispatch' or result['GITHUB_RUN_ATTEMPT'] != '1' or
                    result['GITHUB_WORKFLOW_REF'] != 'eirblue/ios_note10p/' + workflow + '@refs/heads/main' or
                    os.environ.get('N10_EXPECTED_SOURCE_HEAD') != result['GITHUB_SHA']):
        raise ValueError('exact reviewed storage workflow first attempt required')
    return result


def prior_pass_authorization(ci):
    if os.environ.get('N10_BUILD_ONLY', 'false') == 'false':
        return None
    raw = os.environ.get('N10_PASSED_BATCH_CONTEXT_B64', '')
    if os.environ.get('N10_BUILD_ONLY') != 'true' or len(raw) > 16384:
        raise ValueError('Root-bound retained PASS context required for build-only')
    record = json.loads(base64.b64decode(raw, validate=True))
    required = {'accepted', 'current_source_commit', 'passed_source_commit', 'run_id', 'attempt',
                'result_sha256', 'test_sources_sha256', 'passed_case_ids'}
    expected = {n: native.file_sha(ROOT / 'note10/xnu26' / n)
                for n in ('current_native_kernel.py', 'test_current_native_kernel.py')}
    if (set(record) != required or record['accepted'] is not True or
        record['current_source_commit'] != ci['GITHUB_SHA'] or
        not re.fullmatch('[0-9a-f]{40}', record['passed_source_commit']) or
        any(type(record[k]) is not int or record[k] < 1 for k in ('run_id', 'attempt')) or
        not re.fullmatch('[0-9a-f]{64}', record['result_sha256']) or
        record['test_sources_sha256'] != expected or record['passed_case_ids'] != list(CASE_IDS)):
        raise ValueError('actual retained PASS must be bound by Root to unchanged test sources and this build head')
    return record


def generated_inputs(private):
    records = {}
    for filename, default_component in (('native-mig-result.json', 'osfmk'), ('native-extra-result.json', None)):
        report = json.loads((private / filename).read_text())
        if default_component and report.get('all_passed') is not True:
            raise ValueError('current native MIG declarations incomplete')
        for row in report['generated_sources']:
            key = (row.get('component', default_component), row['selected_name'])
            if key in records:
                raise ValueError('duplicate generator ownership')
            records[key] = dict(row, path=str(private / row['source']))
    return records


def collect_evidence(private, output):
    """New receipts, logs, generated config and objects only; no SDK/source dump."""
    if not private.exists():
        return
    for path in private.rglob('*'):
        relative = path.relative_to(private)
        wanted = (path.suffix in ('.json', '.log', '.o') or
                  (relative.parts[0] == 'configured' and (path.name == 'Makefile' or path.suffix == '.h')))
        if path.is_file() and not path.is_symlink() and wanted:
            dest = output / 'production' / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, dest)


def aliases_for_current(source, rows, output):
    from audit_link_inputs import symbols
    paths = [row['object_path'] for row in rows]
    raw = bootstrap.run(['xcrun', 'nm', '-g', *paths], ROOT, output / 'current-object-symbols.log')
    defined, references = symbols(raw.decode())
    unresolved = set(references) - set(defined)
    aliases, pins = {}, {}
    for path in sorted((source / 'config').glob('*.exports')):
        if not re.fullmatch(r'[^.]+(?:\.arm64)?\.exports', path.name):
            continue
        for line in path.read_text().splitlines():
            pair = line.split('#', 1)[0].strip()
            if pair.count(':') != 1:
                continue
            name, implementation = [s.strip() for s in pair.split(':')]
            if not all(re.fullmatch(r'[_A-Za-z][_A-Za-z0-9$]*', s) for s in (name, implementation)):
                continue
            if name not in unresolved or implementation not in defined:
                continue
            if name in aliases and aliases[name] != implementation:
                raise ValueError('ambiguous real export alias')
            aliases[name] = implementation
            pins[path.relative_to(source).as_posix()] = native.file_sha(path)
    raw_alias = output / 'current-aliases.exports'
    raw_alias.write_text(''.join(a + ':' + b + '\n' for a, b in sorted(aliases.items())))
    result = output / 'current-aliases.exp'
    bootstrap.run(['/bin/sh', source / 'config/generate_linker_aliases.sh', result, raw_alias],
                  ROOT, output / 'alias-generation.log')
    return result, dict(aliases=aliases, source_exports_sha256=pins,
                        generated_aliases_sha256=native.file_sha(result))


def intrinsic_kernel_result(path, symbols_text, undefined, *, leaf=False):
    """Collect this producer's new link output once, not a standalone reader."""
    raw = path.read_bytes()
    if len(raw) < 32:
        raise ValueError('truncated produced kernel')
    magic, cpu, subtype, kind, count, size, flags, reserved = struct.unpack_from('<8I', raw)
    if (magic, cpu, subtype, kind) != (0xfeedfacf, 0x100000c, 0, 2) or count > 4096 or size > len(raw) - 32:
        raise ValueError('plain arm64 executable link output required')
    offset, entry, segments = 32, None, []
    pools=[]
    for _ in range(count):
        if offset + 8 > 32 + size:
            raise ValueError('truncated load command')
        cmd, length = struct.unpack_from('<II', raw, offset)
        if length < 8 or offset + length > 32 + size:
            raise ValueError('invalid load command')
        if cmd in (0xc, 0x80000018, 0x8000001f):
            raise ValueError('dynamic kernel dependency not supported')
        if cmd == 0x19:
            if length < 72:
                raise ValueError('truncated segment')
            name = raw[offset + 8:offset + 24].split(b'\0')[0].decode('ascii')
            va, span, fileoff, filesize, maximum, initial = struct.unpack_from('<QQQQII', raw, offset + 24)
            if filesize > span or fileoff + filesize > len(raw) or (initial & 6) == 6:
                raise ValueError('invalid produced segment')
            segments.append(dict(name=name, virtual_address=va, virtual_size=span,
                                 file_offset=fileoff, file_size=filesize, initial_protection=initial))
            if leaf:
                nsects=struct.unpack_from('<I',raw,offset+64)[0]
                if length!=72+80*nsects:raise ValueError('new kernel section bounds differ')
                for i in range(nsects):
                    section=struct.unpack_from('<16s16sQQ8I',raw,offset+72+80*i)
                    if section[0].rstrip(b'\0')==b'__n10bt':
                        pools.append(dict(segment=section[1].rstrip(b'\0').decode('ascii'),
                            address=section[2],bytes=section[3],alignment_log2=section[5],flags=section[8],
                            segment_start=va,segment_end=va+span,segment_protection=initial,segment_maximum_protection=maximum))
        if cmd == 5:
            if entry is not None or length != 288 or struct.unpack_from('<II', raw, offset + 8) != (6, 68):
                raise ValueError('unexpected ARM64 thread entry')
            entry = struct.unpack_from('<Q', raw, offset + 16 + 256)[0]
        offset += length
    symbols = {}
    for line in symbols_text.splitlines():
        parts = line.split()
        if len(parts) >= 3 and re.fullmatch('[0-9a-fA-F]+', parts[0]):
            symbols[parts[-1]] = int(parts[0], 16)
    required = ('__start', '_start_first_cpu', '_arm_init', '_arm_vm_init', '_pmap_bootstrap', '_PE_init_platform')
    if (offset != 32 + size or undefined.strip() or any(n not in symbols for n in required) or
        entry is None or symbols['__start'] != entry or
        not any(s['initial_protection'] & 4 and s['virtual_address'] <= entry < s['virtual_address'] + s['file_size'] for s in segments)):
        raise ValueError('current entry/undefined/layout output contract failed')
    result=dict(output_sha256=hashlib.sha256(raw).hexdigest(), output_bytes=len(raw),
                entry_virtual_address=hex(entry), architecture='arm64', mach_o_type='MH_EXECUTE',
                entry_symbols={n: hex(symbols[n]) for n in required}, segments=segments,
                undefined_symbols=[], deployment_ready=False)
    if leaf:
        if len(pools)!=1:raise ValueError('one actual Exynos zero-fill pool required')
        pool=pools[0];start=pool['address'];end=start+pool['bytes']
        selected=[s for s in segments if s['virtual_size']]
        base=min(s['virtual_address'] for s in selected);limit=max(s['virtual_address']+s['virtual_size'] for s in selected)
        mapper=symbols.get('_n10_exynos_bootstrap_map')
        span=(limit-base+16383)&~16383
        if (not 0<span<=33554432 or base%16384 or pool['segment']!='__DATA' or pool['bytes']!=163840 or start%16384 or pool['alignment_log2']<14 or
            pool['flags']&255!=1 or pool['segment_protection']!=3 or
            pool['segment_maximum_protection']&pool['segment_protection'] != pool['segment_protection'] or
            not pool['segment_start']<=start<end<=pool['segment_end'] or
            symbols.get('_bootstrap_pagetables')!=start or not base<=start<end<=limit or mapper is None or
            not any(s['initial_protection']&4 and s['virtual_address']<=mapper<s['virtual_address']+s['file_size'] for s in segments)):
            raise ValueError('actual new mapper/BSS pool/source payload containment failed')
        result.update(PC_only=True,physical_ready=False,bootstrap_pool=pool,
            mapper_virtual_address=hex(mapper),memory_image_span_bytes=span,
            memory_image_virtual_base=hex(base),entry_offset=entry-base,
            bootstrap_pool_relative_offset=start-base,physical_reservation_verified=False)
    return result


def build(work, output, *, leaf=False, checked=False, storage=False):
    # Reuse only provisioning/configuration primitives; never the v83 tests/build.
    if storage:
        checked = True
    if checked:leaf=True
    ci = ci_context(leaf, checked, storage=True) if storage else ci_context(leaf, checked)
    if storage:
        import phase1_iostorage_kernel_link as storage_link
        storage_link.verify_sources()
    if leaf and os.environ.get('N10_BUILD_ONLY','false')!='false':
        raise ValueError('new leaf scope has no retained-PASS skip gate')
    prior_pass = None if leaf else prior_pass_authorization(ci)
    bootstrap.provision(work, output, ci=ci,leaf=leaf,checked=checked)
    provisioned = json.loads((work / 'context.json').read_text())
    source, tool = Path(provisioned['source']), Path(provisioned['tool'])
    private = PRIVATE / 'windows-xnu'
    if private.exists():
        raise ValueError('fresh current production roots required')
    private.mkdir()
    state = dict(kind='v84-current-native-selected-link', phase='building', passed=False,
                 ci_context=provisioned['ci_context'], public_source_commit=COMMIT,
                 synthetic_board_inputs=True, full_upstream_make_build=False,
                 deployment_ready=False, hardware_verified=False, device_operations=[])
    if leaf:state.update(kind='v93-exynos-leaf-bootstrap-pc',PC_only=True,physical_ready=False,whole_XNU_kernel_entry_executed=False,hardware_XNU_executed=False)
    if checked:state.update(kind='v94-exynos-checked-ptpage-pc')
    if storage:
        state.update(kind='phase1-iostorage-final-link-pc', storage={'stage': 'pending'})
    state['build_only_prior_pass'] = prior_pass
    bootstrap.write_json(output / 'result.json', state)
    original_env = dict(os.environ)
    try:
        os.environ.update(N10_CC=provisioned['compiler'], N10_SDKROOT=provisioned['sdk'],
                          N10_MAKE=shutil.which('make') or 'make')
        makefiles, configured = {}, []
        for component in native.COMPONENTS:
            directory = private / 'configured/DEVELOPMENT' / component
            makefiles[component] = bootstrap.configure(source, tool, directory, component=component)
            configured.append(dict(variant='DEVELOPMENT', component=component,
                headers={p.name: native.file_sha(p) for p in directory.glob('*.h')},
                makefile_sha256=native.file_sha(directory / 'Makefile')))
        patched = {}
        for patch in provisioned['patch_sha256']:
            for line in (ROOT / 'note10/xnu26/patches' / patch).read_text().splitlines():
                if line.startswith('+++ b/'):
                    name = line[6:]
                    patched[name] = native.file_sha(source / name)
        bootstrap.write_json(private / 'configure-result.json', dict(source_directory=source.relative_to(ROOT).as_posix(),
            source_commit=COMMIT, configured=configured, patched_source_sha256=patched))
        target = json.loads((ROOT / 'note10/target.json').read_text())
        library = ROOT / target['research_directory'] / ('libdispatch-' + LIBDISPATCH)
        library.mkdir(parents=True, exist_ok=False)
        for n, command in enumerate((['git', 'init', '-q'],
            ['git', 'fetch', '--depth=1', 'https://github.com/apple-oss-distributions/libdispatch.git', LIBDISPATCH],
            ['git', 'checkout', '-q', '--detach', 'FETCH_HEAD'])):
            bootstrap.run(command, library, output / ('libdispatch-' + str(n) + '.log'))
        if subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=library).decode().strip() != LIBDISPATCH:
            raise ValueError('exact genuine public firehose source required')
        header = ROOT / 'host-tools/opensource-declarations/os/firehose_buffer_private.h'
        header.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(library / 'os/firehose_buffer_private.h', header)
        import cloud_compile
        import export_source_headers
        import generate_link_metadata
        import generate_native_mig
        import generate_native_extra
        import compile_native_components
        import generate_assym
        import compile_public_dependencies
        import compile_link_metadata
        from link_experimental_kernel import layout_flags
        with (output / 'current-generation.log').open('w') as log, contextlib.redirect_stdout(log):
            cloud_compile.sdk_declarations()
            export_source_headers.main()
            generate_link_metadata.main()
            generate_native_mig.main()
            generate_native_extra.main()
        generated = generated_inputs(private)
        rows = native.inventory(makefiles, source, generated, private)
        if storage and len(rows) != 1067:
            raise ValueError('accepted checked native inventory count required')
        bootstrap.selected_sources(makefiles)
        resource = Path(subprocess.check_output([provisioned['compiler'], '-print-resource-dir']).decode().strip())
        runtime = resource / 'lib/darwin/libclang_rt.cc_kext_ios.a'
        arches = bootstrap.run(['xcrun', 'lipo', '-archs', runtime], ROOT, output / 'compiler-runtime-architecture.log').decode().split()
        if 'arm64' not in arches:
            raise ValueError('plain arm64 current compiler runtime required')
        toolchain = dict(compiler=provisioned['compiler'], sdk=provisioned['sdk'],
            compiler_version=subprocess.check_output([provisioned['compiler'], '--version']).decode(),
            runtime=dict(path=str(runtime), sha256=native.file_sha(runtime), architectures=arches))
        producer = dict(source_commit=provisioned['ci_context']['GITHUB_SHA'], ci_context=provisioned['ci_context'],
            source_root=str(source), objects_root=str(private / 'objects/DEVELOPMENT'),
            public_source_commit=COMMIT, public_libdispatch_commit=LIBDISPATCH,
            patch_sha256=provisioned['patch_sha256'], configuration='DEVELOPMENT_ARM64_EXYNOS9825',
            toolchain=toolchain, fresh_work_root=str(work))
        producer['recipe_sha256'] = {n: native.file_sha(ROOT / 'note10/xnu26' / n) for n in (
            'build_current_native_kernel.py', 'current_native_kernel.py', 'build_native_bootstrap_selection.py',
            'prepare_native_bootstrap_selection.py', 'compile_native_components.py', 'generate_native_mig.py',
            'generate_native_extra.py', 'generate_assym.py', 'generate_link_metadata.py',
            'compile_public_dependencies.py', 'compile_link_metadata.py', 'export_source_headers.py',
            'link_experimental_kernel.py', 'audit_link_inputs.py', 'cloud_compile.py')}
        if leaf:
            producer['recipe_sha256'].update({n:native.file_sha(ROOT/'note10/xnu26'/n) for n in
                ('prepare_exynos_leaf_mapper.py','exynos_leaf_mapper.S','exynos_leaf_mapper.h')})
        if checked:
            producer['candidate_kind']='v94-exynos-checked-ptpage-pc'
            producer['recipe_sha256'].update({n:native.file_sha(ROOT/'note10/xnu26'/n) for n in
                ('prepare_exynos_checked_ptpage.py','exynos_checked_ptpage.c')})
        binding_files = ('configure-result.json', 'exports-result.json', 'native-mig-result.json',
                         'native-extra-result.json', 'native-link/generate-result.json')
        bindings = {n: native.file_sha(private / n) for n in binding_files}
        flags, layout = layout_flags((source / 'makedefs/MakeInc.def').read_text())
        bindings.update(KDK_public_input_sha256=cloud_compile.KDK_SHA,
                        public_firehose_header_sha256=native.file_sha(header),
                        link_flags_sha256=native.digest(flags))
        dep_paths = {'@public/libdispatch/firehose_buffer.c': library / 'src/firehose/firehose_buffer.c',
            '@metadata/version.c': private / 'native-link/version.c',
            '@metadata/lastkerneldataconst.c': source / 'libsa/lastkerneldataconst.c',
            '@metadata/lastkernelconstructor.c': source / 'libsa/lastkernelconstructor.c'}
        current = dict(kind='v84-current-native', producer=producer, producer_id=native.digest(producer),
            bindings=bindings, input_binding=native.digest(bindings), inventory=rows,
            dependencies={n: dict(path=str(p), source_sha256=native.file_sha(p)) for n, p in dep_paths.items()})
        bootstrap.write_json(output / 'producer-context.json', current)
        with (output / 'current-compilation.log').open('w') as log, contextlib.redirect_stdout(log):
            c = compile_native_components.main(current, 'C')
            base = next(r['command'] for r in c['units'] if r['source'] == 'osfmk/arm64/machine_routines.c')
            assym = generate_assym.main(current, base)
            current['assembly_input'] = native.digest(assym)
            cxx = compile_native_components.main(current, 'C++')
            assembly = compile_native_components.main(current, 'assembly')
            firehose = compile_public_dependencies.main(current,
                next(r['command'] for r in c['units'] if r['source'] == 'libkern/os/log.c'))
            metadata = compile_link_metadata.main(current, base)
        bootstrap.write_json(output / 'producer-context.json', current)
        objects = [r for report in (c, cxx, assembly, firehose, metadata) for r in report['units']]
        bootstrap.write_json(output / 'current-object-receipts.json', objects)
        if storage:
            storage_rows = storage_link.compile_storage(current, work, output, state['storage'])
            aliases, alias_evidence = aliases_for_current(source, objects + storage_rows, output)
            state['storage']['stage'] = 'storage-final-link'
            linked = native.direct_link(current, objects, output, provisioned['compiler'], provisioned['sdk'],
                                        flags, aliases, toolchain['runtime'], storage_rows=storage_rows)
        else:
            aliases, alias_evidence = aliases_for_current(source, objects, output)
            linked = native.direct_link(current, objects, output, provisioned['compiler'], provisioned['sdk'],
                                        flags, aliases, toolchain['runtime'])
        state.update(link=linked, alias_evidence=alias_evidence, layout_variables=layout,
                     producer_id=current['producer_id'], input_binding=current['input_binding'])
        if not linked['link_succeeded']:
            raise RuntimeError('current direct kernel link failed')
        kernel = output / 'current-native.macho'
        undefined = bootstrap.run(['xcrun', 'nm', '-u', kernel], ROOT, output / 'kernel-undefined.log').decode()
        symbols = bootstrap.run(['xcrun', 'nm', kernel], ROOT, output / 'kernel-symbols.log').decode()
        state.update(intrinsic_kernel_result(kernel, symbols, undefined,leaf=leaf))
        if storage:
            storage_link.verify_final_symbols(symbols, linked, state['storage'])
        state.update(phase='complete', passed=True, native_objects=len(rows), dependency_objects=4,
                     candidate_archive_used=False, old_suites_executed=0)
    except BaseException as error:
        state.update(phase='failed', passed=False, error=type(error).__name__ + ': ' + str(error))
        raise
    finally:
        bootstrap.write_json(output / 'result.json', state)
        if not storage:
            collect_evidence(private, output)
        os.environ.clear()
        os.environ.update(original_env)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--exynos-leaf',action='store_true',help='closed v93 PC-only EXYNOS mapper source candidate')
    p.add_argument('--exynos-checked-pages',action='store_true',help='closed v94 PC-only checked allocator plus mapper')
    args = p.parse_args()
    work, output = bootstrap.private(args.work), bootstrap.private(args.output)
    if work == output or work.is_relative_to(output) or output.is_relative_to(work):
        p.error('disjoint fresh private roots required')
    try:
        build(work, output,leaf=args.exynos_leaf,checked=args.exynos_checked_pages)
    except BaseException:
        print('current native payload build failed; private evidence retained', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
