"""Fixed, source-only SDK/private/resource header availability inventory."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import stat
import subprocess
import time

import phase1_iostorage_declaration as sdk

ROOT = sdk.ROOT
MODE = 'genuine_storage_header_inventory'
SCHEMA = 'note10-v206-storage-header-inventory-result-v1'
OUTPUT = ROOT / 'note10/private/v206-storage-header-inventory-once'
FILES = ('note10/xnu26/phase1_storage_header_inventory.py', 'note10/xnu26/test_storage_header_inventory.py',
         '.github/workflows/note10-phase1-iostorage-declaration-pc.yml',
         'note10/xnu26/phase1_iostorage_declaration.py')
SOURCE_CAP = HEADER_CAP = 1048576
TOTAL_CAP, UNIQUE_CAP, META_CAP, QUERY_CAP, PATH_CAP = 67108864, 256, 8388608, 16384, 4096
ROOT_ROLES = ('sdk-public-versioned', 'sdk-private-versioned', 'sdk-public-alias', 'sdk-private-alias',
              'sdk-local', 'sdk-system', 'compiler-builtin')
ROOT_RELATIVE = ('System/Library/Frameworks/Kernel.framework/Versions/A/Headers',
                 'System/Library/Frameworks/Kernel.framework/Versions/A/PrivateHeaders',
                 'System/Library/Frameworks/Kernel.framework/Headers',
                 'System/Library/Frameworks/Kernel.framework/PrivateHeaders',
                 'usr/local/include', 'usr/include', 'include')
AUTHORITY = dict(new_header_interface_admitted=False, compile_recipe_closed=False,
    genuine_driver_object_compiled=False, new_driver_linked_in_native_kernel=False,
    registered_provider=False, matching_executed=False, transport_instantiated=False,
    runtime_backing_owner_verified=False, concrete_nub_dispatch_verified=False, runtime_IOKit_verified=False,
    firmware_abi_verified=False, native_activation=False, kernel_executed=False, physical_ready=False,
    new_device_input_admitted=False, new_RAM_MMIO_MMU_or_CPU_operation=False)
REQUIRED = ('IOKit/IODeviceTreeSupport.h', 'IOKit/IOKitKeys.h', 'IOKit/IOMapper.h', 'IOKit/IOSubMemoryDescriptor.h', 'IOKit/pwr_mgt/RootDomain.h', 'IOKit/perfcontrol/IOPerfControl.h', 'kern/energy_perf.h', 'kern/thread_call.h', 'kern/queue.h', 'libkern/OSAtomic.h', 'AssertMacros.h', 'stdatomic.h', 'DriverKit/OSObject.h', 'DriverKit/IOService.h', 'DriverKit/IOMemoryDescriptor.h')
PROBES = ('IOKit/IOService.h', 'kern/bits.h', 'libkern/c++/OSPtr.h', 'kern/assert.h', 'kern/kalloc.h', 'stdbool.h', 'stdint.h', 'string.h', 'libkern/c++/OSSharedPtr.h', 'libkern/c++/intrusive_shared_ptr.h', 'libkern/c++/OSMetaClass.h', 'kern/kern_types.h', 'mach/mach_types.h', 'sys/cdefs.h', 'mach/machine/vm_types.h', 'mach/boolean.h', 'mach/vm_types.h', 'kern/zalloc.h', 'libkern/section_keywords.h', 'os/alloc_util.h', 'kern/macro_help.h', 'machine/trap.h', 'kern/clock.h')



def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


def read_source(path):
    require(path.resolve() == path and not path.is_symlink() and path.is_file() and
            0 < path.stat().st_size <= SOURCE_CAP, 'bounded_source_file')
    with path.open('rb') as stream:
        raw = stream.read(SOURCE_CAP + 1)
    require(len(raw) == path.stat().st_size <= SOURCE_CAP, 'source_file_extent')
    return raw


def bounded_query(argv):
    process = subprocess.Popen(argv, cwd=ROOT, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
    buffers = {process.stdout: bytearray(), process.stderr: bytearray()}
    deadline = time.monotonic() + 30
    try:
        with selectors.DefaultSelector() as selector:
            for stream in buffers:
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ)
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(argv, 30)
                events = selector.select(remaining)
                if not events:
                    raise subprocess.TimeoutExpired(argv, 30)
                for key, _ in events:
                    buffer = buffers[key.fileobj]
                    available = QUERY_CAP - len(buffer)
                    chunk = os.read(key.fd, min(4096, available + 1))
                    if not chunk:
                        selector.unregister(key.fileobj)
                    elif len(chunk) > available:
                        raise ValueError('metadata_query_output_cap')
                    else:
                        buffer.extend(chunk)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired(argv, 30)
        returncode = process.wait(timeout=remaining)
        return returncode, bytes(buffers[process.stdout]), bytes(buffers[process.stderr])
    finally:
        try:
            if process.poll() is None:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
                process.wait(timeout=5)
        finally:
            process.stdout.close()
            process.stderr.close()


def metadata_query(argv):
    result = dict(attempted=True, returncode=None, value=None, failure_code=None)
    try:
        returncode, stdout, stderr = bounded_query(argv)
        result['returncode'] = returncode
        if returncode:
            result['failure_code'] = 'metadata_query_returncode'
        else:
            text = stdout.decode('utf-8').strip()
            if not text or len(text) > PATH_CAP or any(ord(c) < 32 for c in text):
                result['failure_code'] = 'metadata_query_value_shape'
            else:
                result['value'] = text
    except ValueError:
        result['failure_code'] = 'metadata_query_output_cap'
    except subprocess.TimeoutExpired:
        result['failure_code'] = 'metadata_query_timeout'
    except (OSError, UnicodeError):
        result['failure_code'] = 'metadata_query_unavailable'
    return result


def directory_value(query):
    value = query['value']
    if query['failure_code'] or type(value) is not str:
        return None
    path = Path(value)
    try:
        return path.resolve() if path.is_absolute() and path.is_dir() else None
    except (OSError, RuntimeError):
        return None


def query_roots():
    queries = {
        'sdk_path': metadata_query(['xcrun', '--sdk', 'macosx', '--show-sdk-path']),
        'sdk_version': metadata_query(['xcrun', '--sdk', 'macosx', '--show-sdk-version']),
        'compiler_path': metadata_query(['xcrun', '-f', 'clang']),
    }
    queries['compiler_resource'] = dict(attempted=False, returncode=None, value=None,
                                        failure_code='compiler_path_unavailable')
    compiler = queries['compiler_path']['value']
    if type(compiler) is str and not queries['compiler_path']['failure_code']:
        try:
            path = Path(compiler).resolve()
            if Path(compiler).is_absolute() and path.is_file():
                queries['compiler_resource'] = metadata_query([str(path), '-print-resource-dir'])
        except (OSError, RuntimeError):
            pass
    sdk_root = directory_value(queries['sdk_path'])
    resource_root = directory_value(queries['compiler_resource'])
    version = queries['sdk_version']['value']
    complete = sdk_root is not None and resource_root is not None and type(version) is str and bool(
        re.fullmatch(r'[0-9]+(?:\.[0-9]+){0,2}', version)) and all(
        q['attempted'] is True and q['returncode'] == 0 and q['failure_code'] is None for q in queries.values())
    return sdk_root, resource_root, queries, complete


def root_records(sdk_root, resource_root):
    records, aliases = [], {}
    for role, relative in zip(ROOT_ROLES, ROOT_RELATIVE):
        owner = resource_root if role == 'compiler-builtin' else sdk_root
        row = dict(role=role, path=None, canonical_path=None, available=False, alias_of=None,
                   status='root-unresolved')
        if owner is not None:
            path = owner / relative
            if len(str(path)) > PATH_CAP:
                row['status'] = 'root-rejected'
                records.append(row)
                continue
            row['path'] = str(path)
            try:
                canonical = path.resolve()
                if len(str(canonical)) > PATH_CAP or not canonical.is_relative_to(owner):
                    row['status'] = 'root-rejected'
                else:
                    row['canonical_path'] = str(canonical)
                    row['available'] = canonical.is_dir()
                    row['status'] = 'available' if row['available'] else 'root-unavailable'
                    if row['available']:
                        row['alias_of'] = aliases.get(str(canonical))
                        aliases.setdefault(str(canonical), role)
            except (OSError, RuntimeError):
                row['status'] = 'root-rejected'
        records.append(row)
    return records


def lexical_metadata(raw):
    # Literal include/guard observations only; no preprocessing or include traversal.
    try:
        text = raw.decode('utf-8')
    except UnicodeError:
        return dict(literal_includes=[], kernel_private_guard_literal_seen=None,
                    lexical_capture_truncated=True, conditional_edges_evaluated=False)
    includes = []
    for line in text.splitlines():
        match = re.match(r'\s*#\s*include\s*[<"]([^>"\r\n]{1,191})[>"]', line)
        if match and match.group(1) not in includes:
            includes.append(match.group(1))
    return dict(literal_includes=includes[:32], lexical_capture_truncated=len(includes) > 32,
                kernel_private_guard_literal_seen=bool(re.search(r'^\s*#\s*(?:ifdef|if).*\bKERNEL_PRIVATE\b', text, re.M)),
                conditional_edges_evaluated=False)


def observe_candidate(root, token, owners, files, cache, budget):
    row = dict(role=root['role'], path=None, canonical_path=None, file_id=None,
               status=root['status'] if not root['available'] else 'missing', reason=None, bytes=None)
    if root['path'] is None:
        return row
    candidate = Path(root['path']) / token
    if len(str(candidate)) > PATH_CAP:
        row.update(status='rejected', reason='header_path_cap')
        budget['complete'] = False
        return row
    row['path'] = str(candidate)
    if not root['available']:
        return row
    try:
        path = (Path(root['canonical_path']) / token).resolve()
        if len(str(path)) > PATH_CAP or not any(path.is_relative_to(owner) for owner in owners):
            row.update(status='rejected', reason='header_outside_actual_roots')
            budget['complete'] = False
            return row
        row['canonical_path'] = str(path)
        before = path.stat()
    except FileNotFoundError:
        return row
    except (OSError, RuntimeError):
        row.update(status='rejected', reason='header_stat_unavailable')
        budget['complete'] = False
        return row
    row['bytes'] = before.st_size
    if not stat.S_ISREG(before.st_mode) or before.st_ino <= 0:
        row.update(status='rejected', reason='ordinary_identifiable_header_required')
        budget['complete'] = False
        return row
    identity = (before.st_dev, before.st_ino)
    stamp = (before.st_size, before.st_mtime_ns)
    if identity in cache:
        file_id, prior_stamp = cache[identity]
        if prior_stamp != stamp:
            row.update(status='rejected', reason='header_identity_changed')
            budget['complete'] = False
        else:
            row.update(status=files[file_id]['status'], reason=files[file_id]['reason'], file_id=file_id)
        return row
    if len(files) >= UNIQUE_CAP:
        row.update(status='present-unhashed', reason='unique_header_file_cap')
        budget['complete'] = False
        return row
    file_id = sha((str(before.st_dev) + ':' + str(before.st_ino)).encode())
    record = dict(path=str(path), bytes=before.st_size, mtime_ns=before.st_mtime_ns,
                  status='present-unhashed', reason=None, sha256=None, literal_includes=[],
                  lexical_capture_truncated=True, kernel_private_guard_literal_seen=None,
                  conditional_edges_evaluated=False)
    files[file_id] = record
    cache[identity] = (file_id, stamp)
    row['file_id'] = file_id
    if not 0 < before.st_size <= HEADER_CAP:
        record.update(status='rejected', reason='header_source_extent_cap')
        budget['complete'] = False
    elif budget['bytes_reserved'] + before.st_size > TOTAL_CAP:
        record['reason'] = 'aggregate_header_source_cap'
        budget['complete'] = False
    else:
        budget['bytes_reserved'] += before.st_size
        budget['source_reads'] += 1
        try:
            with path.open('rb') as stream:
                raw = stream.read(before.st_size)
            budget['bytes_read'] += len(raw)
            after = path.stat()
            if len(raw) != before.st_size or (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) != (
                    before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns):
                record.update(status='rejected', reason='header_changed_during_read')
                budget['complete'] = False
            else:
                record.update(status='present', sha256=sha(raw), **lexical_metadata(raw))
                budget['hashes'] += 1
        except OSError:
            record.update(status='rejected', reason='header_source_read_unavailable')
            budget['complete'] = False
    row.update(status=record['status'], reason=record['reason'])
    return row


def inventory(sdk_root, resource_root, query_complete):
    tokens = REQUIRED + PROBES
    require(len(REQUIRED) == 15 and len(PROBES) == 23 and len(tokens) == len(set(tokens)) == 38 and
            all(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_./+\-]{0,190}\.h', name) and
                '..' not in name.split('/') and not name.startswith('/') for name in tokens), 'fixed_header_manifest')
    roots = root_records(sdk_root, resource_root)
    owners = [owner for owner in (sdk_root, resource_root) if owner is not None]
    headers, files, cache = {}, {}, {}
    budget = dict(complete=query_complete and all(row['status'] not in ('root-unresolved', 'root-rejected') for row in roots),
                  source_reads=0, bytes_read=0, bytes_reserved=0, hashes=0)
    for token in tokens:
        candidates = [observe_candidate(root, token, owners, files, cache, budget) for root in roots]
        present = [row for row in candidates if row['status'] in ('present', 'present-unhashed')]
        if present:
            status = 'present' if any(row['status'] == 'present' for row in present) else 'present-unhashed'
        elif any(row['status'] in ('root-unresolved', 'root-rejected') for row in candidates):
            status = 'unobserved'
        elif any(row['status'] == 'rejected' for row in candidates):
            status = 'rejected'
        else:
            status = 'missing'
        preferred = next((row for row in candidates if row['status'] == 'present'), present[0] if present else None)
        headers[token] = dict(group='required' if token in REQUIRED else 'probe', status=status,
                              candidates=candidates, preferred=preferred)
    missing = [name for name in REQUIRED if headers[name]['status'] == 'missing']
    rejected = [name for name in REQUIRED if headers[name]['status'] in ('rejected', 'present-unhashed')]
    unobserved = [name for name in REQUIRED if headers[name]['status'] == 'unobserved']
    outside = sorted({name for row in files.values() for name in row['literal_includes'] if name not in tokens})
    return dict(coverage_complete=True, inventory_complete=budget['complete'], all_required_headers_present=all(
                    headers[name]['status'] in ('present', 'present-unhashed') for name in REQUIRED),
                required_count=15, required_tokens=list(REQUIRED), probe_tokens=list(PROBES), roots=roots,
                headers=headers, files=files, required_missing=missing, required_rejected=rejected,
                required_unobserved=unobserved, unique_header_files=len(files), header_source_reads=budget['source_reads'],
                header_source_bytes=budget['bytes_read'], header_source_hashes=budget['hashes'],
                header_source_requested_bytes=budget['bytes_reserved'],
                outside_manifest_include_tokens=outside[:512], outside_manifest_capture_truncated=len(outside) > 512,
                lexical_capture_exhaustive=False, preference_is_compiler_resolution=False,
                new_header_interface_admitted=False, compile_recipe_closed=False)


def validate_inventory(value):
    require(value['coverage_complete'] is True and type(value['inventory_complete']) is bool and
            type(value['all_required_headers_present']) is bool and
            type(value['required_count']) is int and value['required_count'] == 15 and
            value['required_tokens'] == list(REQUIRED) and value['probe_tokens'] == list(PROBES) and
            [row['role'] for row in value['roots']] == list(ROOT_ROLES) and
            set(value['headers']) == set(REQUIRED + PROBES), 'complete_fixed_inventory_slots')
    statuses = {'present', 'present-unhashed', 'missing', 'rejected', 'unobserved'}
    candidate_statuses = {'present', 'present-unhashed', 'missing', 'rejected', 'root-unresolved', 'root-unavailable', 'root-rejected'}
    seen_roots = {}
    for row in value['roots']:
        require(type(row['available']) is bool and row['status'] in
                ('available', 'root-unresolved', 'root-unavailable', 'root-rejected') and
                row['available'] is (row['status'] == 'available') and
                all(row[key] is None or type(row[key]) is str and len(row[key]) <= PATH_CAP
                    for key in ('path', 'canonical_path')), 'bounded_root_observation')
        if row['alias_of'] is not None:
            require(row['available'] and row['alias_of'] in seen_roots and
                    seen_roots[row['alias_of']]['canonical_path'] == row['canonical_path'], 'root_alias_identity')
        seen_roots[row['role']] = row
    for token, header in value['headers'].items():
        require(header['group'] == ('required' if token in REQUIRED else 'probe') and header['status'] in statuses and
                [row['role'] for row in header['candidates']] == list(ROOT_ROLES), 'all_candidate_root_slots')
        for row in header['candidates']:
            require(row['status'] in candidate_statuses and all(row[key] is None or
                    (type(row[key]) is str and len(row[key]) <= PATH_CAP) for key in ('path', 'canonical_path')),
                    'candidate_path_shape')
            if row['status'] == 'present':
                require(digest(row['file_id']) and row['file_id'] in value['files'] and
                        value['files'][row['file_id']]['status'] == 'present', 'candidate_file_hash_reference')
    require(value['required_missing'] == [n for n in REQUIRED if value['headers'][n]['status'] == 'missing'] and
            value['required_rejected'] == [n for n in REQUIRED if value['headers'][n]['status'] in ('rejected', 'present-unhashed')] and
            value['required_unobserved'] == [n for n in REQUIRED if value['headers'][n]['status'] == 'unobserved'] and
            value['all_required_headers_present'] is all(value['headers'][n]['status'] in ('present', 'present-unhashed') for n in REQUIRED),
            'complete_missing_rejected_classification')
    require(type(value['unique_header_files']) is int and value['unique_header_files'] == len(value['files']) <= UNIQUE_CAP and
            type(value['header_source_reads']) is int and 0 <= value['header_source_reads'] <= UNIQUE_CAP and
            type(value['header_source_hashes']) is int and value['header_source_hashes'] == sum(
                row['status'] == 'present' for row in value['files'].values()) <= value['header_source_reads'] and
            type(value['header_source_bytes']) is int and type(value['header_source_requested_bytes']) is int and
            0 <= value['header_source_bytes'] <= value['header_source_requested_bytes'] <= TOTAL_CAP,
            'bounded_unique_header_observations')
    for file_id, row in value['files'].items():
        require(digest(file_id) and row['status'] in ('present', 'present-unhashed', 'rejected') and
                type(row['bytes']) is int and row['bytes'] >= 0 and type(row['mtime_ns']) is int and
                type(row['path']) is str and len(row['path']) <= PATH_CAP and
                type(row['lexical_capture_truncated']) is bool and row['conditional_edges_evaluated'] is False and
                (row['kernel_private_guard_literal_seen'] is None or type(row['kernel_private_guard_literal_seen']) is bool) and
                type(row['literal_includes']) is list and len(row['literal_includes']) <= 32 and
                all(type(name) is str and 0 < len(name) <= 191 for name in row['literal_includes']), 'header_observation_shape')
        if row['status'] == 'present':
            require(0 < row['bytes'] <= HEADER_CAP and digest(row['sha256']), 'bounded_present_header_digest')
    require(value['lexical_capture_exhaustive'] is False and value['preference_is_compiler_resolution'] is False and
            value['new_header_interface_admitted'] is False and value['compile_recipe_closed'] is False,
            'source_observations_do_not_close_compile_recipe')
    require(type(value['outside_manifest_include_tokens']) is list and len(value['outside_manifest_include_tokens']) <= 512 and
            all(type(name) is str and 0 < len(name) <= 191 for name in value['outside_manifest_include_tokens']) and
            type(value['outside_manifest_capture_truncated']) is bool, 'bounded_unfollowed_include_metadata')


def validate_result(value, head, run, committed_sources):
    require(value['schema'] == SCHEMA and value['feature'] == MODE and value['source_head'] == head and
            type(value['run_id']) is int and value['run_id'] == run and type(value['run_attempt']) is int and
            value['run_attempt'] == 1 and value['stage'] == 'complete' and
            value['source_sha256'] == committed_sources and set(committed_sources) == set(FILES) and
            all(digest(h) for h in committed_sources.values()) and value['authority'] == AUTHORITY and
            all(type(v) is bool and v is False for v in value['authority'].values()), 'current_inventory_source_identity')
    validate_inventory(value)
    require(type(value['passed']) is bool and value['passed'] is value['inventory_complete'] and
            all(type(value[k]) is int and value[k] == 0 for k in ('compiler_translation_attempts',
                'preprocessor_attempts', 'IIG_attempts', 'archive_GETs', 'source_text_GETs', 'object_reads',
                'tool_binary_hashes', 'nm_invocations', 'kernel_builds', 'links', 'device_operations')) and
            type(value['same_as205_SDK_version']) is bool and
            value['same_as205_SDK_version'] is (value['SDK_version'] == '26.5'), 'inventory_only_zero_compilation')
    require(set(value['queries']) == {'sdk_path', 'sdk_version', 'compiler_path', 'compiler_resource'} and
            type(value['root_query_attempts']) is int and 0 <= value['root_query_attempts'] <= 4 and
            value['root_query_attempts'] == sum(q['attempted'] is True for q in value['queries'].values()),
            'exact_metadata_query_set')
    require(all(type(q['attempted']) is bool and (q['returncode'] is None or type(q['returncode']) is int) and
                (q['value'] is None or type(q['value']) is str and len(q['value']) <= PATH_CAP) and
                (q['failure_code'] is None or type(q['failure_code']) is str and len(q['failure_code']) <= 96)
                for q in value['queries'].values()), 'bounded_metadata_query_records')
    require(value['SDK_version'] == value['queries']['sdk_version']['value'], 'reported_sdk_version_query_binding')
    if value['inventory_complete']:
        require(value['root_query_attempts'] == 4 and all(q['attempted'] is True and type(q['returncode']) is int and
                q['returncode'] == 0 and q['failure_code'] is None for q in value['queries'].values()) and
                value['required_unobserved'] == [] and all(row['status'] == 'present' for row in value['files'].values()),
                'complete_snapshot_not_unobserved_or_unhashed')
        require(all(row['status'] not in ('root-unresolved', 'root-rejected') for row in value['roots']) and
                all(row['status'] not in ('present-unhashed', 'rejected', 'root-unresolved', 'root-rejected')
                    for header in value['headers'].values() for row in header['candidates']),
                'complete_snapshot_has_no_unobserved_candidate')


def produce(result):
    sdk_root, resource_root, queries, complete = query_roots()
    result.update(queries=queries, SDK_version=queries['sdk_version']['value'],
                  same_as205_SDK_version=queries['sdk_version']['value'] == '26.5',
                  SDK_root=str(sdk_root) if sdk_root is not None else None,
                  compiler_resource_root=str(resource_root) if resource_root is not None else None,
                  root_query_attempts=sum(q['attempted'] is True for q in queries.values()), stage='fixed-header-inventory')
    result.update(inventory(sdk_root, resource_root, complete))
    result.update(stage='complete', passed=result['inventory_complete'])
    if not result['passed']:
        result['failure_code'] = 'incomplete_root_or_bounded_header_observation'


def run_CI_fixture(result):
    result.update(stage='new-fixture-before-header-queries', new_fixture_invocations=1)
    import test_storage_header_inventory as tests
    counts = tests.run()
    require(type(counts) is dict and counts ==
            dict(groups=3, cases=28, group_cases=[8, 12, 8], SDK_reads=0, tool_queries=0,
                 compiler_translations=0, old_suites=0) and
            all(type(value) is int for key, value in counts.items() if key != 'group_cases') and
            type(counts['group_cases']) is list and all(type(value) is int for value in counts['group_cases']),
            'exact_same_CI_new_fixture_counts')
    result.update(new_fixture_passed=True, new_fixture_counts=counts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    head, run = sdk.reviewed_identity()
    require(os.environ.get('N10_PROBE_MODE') == MODE and (ROOT / args.output).resolve() == OUTPUT and
            not OUTPUT.exists(), 'exact_fresh_inventory_output')
    OUTPUT.mkdir(parents=True, exist_ok=False)
    result = dict(schema=SCHEMA, feature=MODE, source_head=head, run_id=run, run_attempt=1,
                  source_sha256={name: sha(read_source(ROOT / name)) for name in FILES}, authority=AUTHORITY,
                  passed=False, stage='new-fixture-before-header-queries', new_fixture_invocations=0,
                  new_fixture_passed=False, new_fixture_counts=None, root_query_attempts=0,
                  compiler_translation_attempts=0, preprocessor_attempts=0,
                  IIG_attempts=0, archive_GETs=0, source_text_GETs=0, object_reads=0, tool_binary_hashes=0,
                  nm_invocations=0, kernel_builds=0, links=0, device_operations=0)
    try:
        run_CI_fixture(result)
        produce(result)
    except Exception as error:
        code = str(error)
        result.update(passed=False, failure_type=type(error).__name__,
                      failure_code=code if re.fullmatch('[A-Za-z_]{1,96}', code) else 'inventory_unclassified_failure')
    encoded = (json.dumps(result, sort_keys=True, indent=2) + '\n').encode()
    require(len(encoded) <= META_CAP, 'bounded_inventory_metadata_output')
    (OUTPUT / 'result.json').write_bytes(encoded)
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
