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


def admit_objects(current, rows):
    check_context(current)
    expected = {r['source']: r for r in current['inventory']}
    if len(expected) != len(current['inventory']):
        raise ValueError('duplicate inventory identity')
    if set(expected) & set(EXTRAS):
        raise ValueError('dependency identity collision')
    expected_categories = {name: 'native' for name in expected} | EXTRAS
    if set(current['dependencies']) != set(EXTRAS):
        raise ValueError('exact four genuine current dependency sources required')
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
        if name in EXTRAS and row.get('source_sha256') != current['dependencies'][name]['source_sha256']:
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
    command = [compiler, '--target=arm64-apple-ios26.5.2', '-mcpu=generic', '-march=armv8.2-a+crypto',
               '-isysroot', sdk, *flags, '-Wl,-filelist,' + str(filelist),
               '-Wl,-alias_list,' + str(aliases), runtime['path'], '-o', str(output)]
    result = runner(command, capture_output=True, text=True, timeout=240)
    (directory / 'kernel-link.log').write_text(result.stdout + result.stderr, encoding='utf-8')
    report = dict(attempted=True, link_succeeded=result.returncode == 0, returncode=result.returncode,
                  command=command, producer_id=current['producer_id'], input_binding=current['input_binding'],
                  object_count=len(paths), filelist_sha256=file_sha(filelist), candidate_archive_used=False,
                  full_upstream_make_build=False, hardware_verified=False, deployment_ready=False)
    (directory / 'link-result.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report
