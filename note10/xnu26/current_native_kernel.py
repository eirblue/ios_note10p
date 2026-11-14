"""Closed current native source/object ownership and the direct link operation."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

COMPONENTS = ('osfmk', 'bsd', 'iokit', 'libkern', 'pexpert', 'libsa', 'security', 'san')
KINDS = {'CFILES': 'C', 'CXXFILES': 'C++', 'SFILES': 'assembly'}
EXTRAS = {'@public/libdispatch/firehose_buffer.c': 'public',
          '@metadata/version.c': 'metadata', '@metadata/lastkerneldataconst.c': 'metadata',
          '@metadata/lastkernelconstructor.c': 'metadata'}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def owned(path, root):
    path, root = Path(path).absolute(), Path(root).absolute()
    if path.resolve() != path or not path.is_relative_to(root) or path == root or not path.is_file():
        raise ValueError('ordinary current input within owned root required')
    return path


def inventory(makefiles, source, generated, generated_root):
    """No set-based deduplication: every configured occurrence has one owner."""
    if set(makefiles) != set(COMPONENTS):
        raise ValueError('all eight current component Makefiles required')
    rows, paths, names, objects = [], set(), set(), set()
    for component in COMPONENTS:
        text = makefiles[component].replace('\\\n', ' ')
        for variable, kind in KINDS.items():
            matches = re.findall(r'^' + variable + r'=(.*)$', text, re.M)
            if len(matches) != 1:
                raise ValueError('exact one native source assignment required')
            for token in matches[0].split():
                if token.startswith('$(SOURCE_DIR)/'):
                    name = token[len('$(SOURCE_DIR)/'):]
                    path = owned(Path(source) / name, source)
                else:
                    if not token.startswith('./') or '..' in Path(token).parts:
                        raise ValueError('unresolved configured input: ' + component + ':' + token)
                    record = generated.get((component, token))
                    if not record or record.get('passed') is not True:
                        raise ValueError('one successful current generated input required: ' + token)
                    path = owned(record['path'], generated_root)
                    if file_sha(path) != record['source_sha256']:
                        raise ValueError('generated source changed')
                    name = '@generated/' + component + '/' + token.removeprefix('./')
                object_name = name.replace('/', '_').replace('@', '') + '.o'
                if name in names or path in paths or object_name in objects:
                    raise ValueError('duplicate native source ownership or object path: ' + name)
                names.add(name)
                paths.add(path)
                objects.add(object_name)
                rows.append(dict(source=name, component=component, kind=kind, token=token,
                                 path=str(path), source_sha256=file_sha(path), object_name=object_name))
    return rows


def check_context(current):
    if current.get('kind') != 'v84-current-native' or current.get('producer_id') != digest(current['producer']):
        raise ValueError('closed current producer required')
    if current.get('input_binding') != digest(current['bindings']):
        raise ValueError('current config/header/generator binding required')
    if not re.fullmatch('[0-9a-f]{40}', current['producer']['source_commit']):
        raise ValueError('exact project source required')
    if any(key in current for key in ('candidate_archive', 'historical_objects', 'platform_reports')):
        raise ValueError('candidate or historical inputs forbidden')


def admit_compile(current, names, owners, inputs, source, kind):
    check_context(current)
    expected = {r['source']: r for r in current['inventory'] if r['kind'] == kind}
    if len(names) != len(set(names)) or set(names) != set(expected):
        raise ValueError('complete exact current native language inventory required')
    for name in names:
        row = expected[name]
        path = inputs.get(name, Path(source) / name)
        if (owners.get(name) != row['component'] or str(Path(path)) != row['path'] or
            file_sha(path) != row['source_sha256']):
            raise ValueError('native input/owner binding changed: ' + name)
    if kind == 'assembly' and not current.get('assembly_input'):
        raise ValueError('current generated assembly offsets required')


def stamp(current, row, category):
    row.update(producer_id=current['producer_id'], input_binding=current['input_binding'], category=category)
    if category == 'native' and row['source'].endswith(('.s', '.S')):
        row['assembly_input'] = current['assembly_input']
    return row


def extra_sources(current):
    extras = dict(EXTRAS)
    if 'user_exception_fetch' in current['producer']:
        from prepare_user_exception_fetch import UNIT, admit_binding
        admit_binding(current)
        extras[UNIT] = 'port'
    elif 'user_exception_fetch' in current['bindings']:
        raise ValueError('caller binding without opt-in producer')
    from phase1_owned_ram_kernel_integration import enabled as owned_factory_enabled, UNIT as FACTORY_UNIT
    if owned_factory_enabled(current):extras[FACTORY_UNIT] = 'port'
    if set(current['dependencies']) != set(extras):
        raise ValueError('exact default-off/on extra-source set required')
    return extras


def expected_objects(current, *, storage=False):
    from phase1_owned_ram_kernel_integration import enabled as factory_enabled
    return len(current['inventory']) + len(extra_sources(current)) + (__import__('phase1_genuine_block_driver_native').storage_count(current)if storage else 0)


def admit_objects(current, rows):
    check_context(current)
    expected = {r['source']: r for r in current['inventory']}
    if len(expected) != len(current['inventory']):
        raise ValueError('duplicate inventory identity')
    extras = extra_sources(current)
    if set(expected) & set(extras):
        raise ValueError('dependency identity collision')
    expected_categories = {name: 'native' for name in expected} | extras
    if set(current['dependencies']) != set(extras):
        raise ValueError('exact genuine current dependency sources required')
    seen, paths = set(), set()
    for row in rows:
        name = row['source']
        if (name in seen or name not in expected_categories or row.get('passed') is not True or
            row.get('category') != expected_categories[name] or
            row.get('producer_id') != current['producer_id'] or
            row.get('input_binding') != current['input_binding']):
            raise ValueError('missing, stale, failed or mixed current object')
        if name in expected and row.get('source_sha256') != expected[name]['source_sha256']:
            raise ValueError('object source mismatch')
        if name in extras and row.get('source_sha256') != current['dependencies'][name]['source_sha256']:
            raise ValueError('current dependency source mismatch')
        if name in expected and expected[name]['kind'] == 'assembly' and row.get('assembly_input') != current.get('assembly_input'):
            raise ValueError('assembly generator mismatch')
        path = owned(row['object_path'], current['producer']['objects_root'])
        if path in paths or file_sha(path) != row['object_sha256']:
            raise ValueError('duplicate or changed current object')
        paths.add(path)
        seen.add(name)
    if seen != set(expected_categories):
        raise ValueError('partial current object production cannot link')
    return [Path(row['object_path']) for row in rows]


def direct_link(current, rows, directory, compiler, sdk, flags, aliases, runtime, *,
                runner=subprocess.run, storage_rows=None):
    """Exactly one final link. No partial merge, archive discovery or fallback."""
    paths = admit_objects(current, rows)
    directory = Path(directory)
    if storage_rows is not None:
        from phase1_iostorage_kernel_link import admit_storage
        paths += admit_storage(current, storage_rows, directory, paths)
    output = directory / 'current-native.macho'
    if output.exists() or (directory / 'native-objects.filelist').exists():
        raise ValueError('fresh direct link outputs required')
    if any('force_load' in arg or 'architecture-candidates' in arg for arg in flags):
        raise ValueError('forced candidate/platform archive forbidden')
    toolchain = current['producer']['toolchain']
    if (compiler != toolchain['compiler'] or sdk != toolchain['sdk'] or
        any(runtime.get(k) != toolchain['runtime'][k] for k in ('path', 'sha256')) or
        digest(flags) != current['bindings']['link_flags_sha256']):
        raise ValueError('current compiler, runtime and source layout recipe required')
    if file_sha(runtime['path']) != runtime['sha256']:
        raise ValueError('current compiler runtime changed')
    filelist = directory / 'native-objects.filelist'
    filelist.write_text('\n'.join(str(p) for p in paths) + '\n', encoding='utf-8')
    from phase1_owned_ram_kernel_integration import link_root
    retention = link_root(current)
    command = [compiler, '--target=arm64-apple-ios26.5.2', '-mcpu=generic', '-march=armv8.2-a+crypto',
               '-isysroot', sdk, *flags, *retention, '-Wl,-filelist,' + str(filelist),
               '-Wl,-alias_list,' + str(aliases), runtime['path'], '-o', str(output)]
    result = runner(command, capture_output=True, text=True, timeout=240)
    (directory / 'kernel-link.log').write_text(result.stdout + result.stderr, encoding='utf-8')
    report = dict(attempted=True, link_succeeded=result.returncode == 0, returncode=result.returncode,
                  command=command, producer_id=current['producer_id'], input_binding=current['input_binding'],
                  object_count=len(paths), filelist_sha256=file_sha(filelist), candidate_archive_used=False,
                  full_upstream_make_build=False, hardware_verified=False, deployment_ready=False)
    (directory / 'link-result.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


def admit_owned_ram_factory_object(profile):
    """One fixed port object; never a complete v84 inventory or link profile."""
    root=Path(__file__).resolve().parents[2]
    if set(profile)!={'kind','producer','producer_id','bindings','input_binding','unit'} or profile['kind']!='note10-v260-owned-ram-factory-object-v1':
        raise ValueError('dedicated single-factory profile required')
    producer=profile['producer'];unit=profile['unit'];bindings=profile['bindings']
    if (profile['producer_id']!=digest(producer) or profile['input_binding']!=digest(bindings) or
        not re.fullmatch('[0-9a-f]{40}',producer['source_commit']) or
        producer['public_source_commit']!='ac9718fb1af618d5ce8678d0dc6e8a58f252216f' or
        producer['configuration']!='DEVELOPMENT_ARM64_EXYNOS9825'):
        raise ValueError('fresh native generation/producer identity required')
    expected=root/'note10/xnu26/note10_owned_ram_nub.cpp'
    if (set(unit)!={'source','component','kind','path','source_sha256','object_path'} or
        unit['source']!='@port/note10_owned_ram_nub.cpp' or unit['component']!='iokit' or unit['kind']!='C++' or
        unit['path']!=str(expected) or file_sha(owned(expected,root/'note10/xnu26'))!=unit['source_sha256']):
        raise ValueError('only the exact owned-RAM factory input is admitted')
    private=Path(producer['generated_root']);objects=Path(producer['objects_root']);apple=Path(producer['apple_headers_root'])
    if (private.resolve()!=private or not private.is_relative_to(root/'note10/private') or
        objects!=private/'objects/DEVELOPMENT' or unit['object_path']!=str(objects/'port_note10_owned_ram_nub.cpp.o') or
        apple.resolve()!=apple or not apple.is_relative_to(root/'note10/private')):
        raise ValueError('fixed private factory outputs/header root required')
    if any(Path(path).exists()for path in (unit['object_path'],str(Path(unit['object_path']).with_suffix('.d')),str(objects/'FACTORY-COMPILE-STARTED.json'))):raise ValueError('fresh one-object attempt required')
    for key in ('configure-result.json','exports-result.json','native-mig-result.json','native-extra-result.json','native-link/generate-result.json'):
        if file_sha(owned(private/key,private))!=bindings[key]:raise ValueError('same-job native generation changed')
    for name,value in bindings['port_source_sha256'].items():
        if name not in ('note10_owned_ram_nub.cpp','note10_owned_ram_nub.h','note10_readonly_ram_block_device.h') or file_sha(owned(root/'note10/xnu26'/name,root/'note10/xnu26'))!=value:
            raise ValueError('closed factory declarations changed')
    if unit['source_sha256']!=bindings['port_source_sha256']['note10_owned_ram_nub.cpp']:raise ValueError('factory row/source binding differs')
    for name,value in bindings['apple_header_sha256'].items():
        if file_sha(owned(apple/name,apple))!=value:raise ValueError('pinned original storage header changed')
    if not bindings['apple_header_sha256']:raise ValueError('original storage headers required')
    if set(bindings['port_source_sha256'])!={'note10_owned_ram_nub.cpp','note10_owned_ram_nub.h','note10_readonly_ram_block_device.h'}:
        raise ValueError('exact factory declaration closure required')
    return dict(units=[unit['source']],owners={unit['source']:'iokit'},input_files={unit['source']:expected},language='C++',native_headers_only=True)
