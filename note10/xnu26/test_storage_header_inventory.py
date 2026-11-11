"""New fixed SDK root/header inventory guards; no actual SDK or tools."""
from copy import deepcopy
import os
from pathlib import Path
import tempfile
import phase1_storage_header_inventory as module


def write(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return path


def setup(directory):
    sdk, resource = (directory / 'SDK').resolve(), (directory / 'resource').resolve()
    sdk.mkdir(); resource.mkdir()
    framework = sdk / 'System/Library/Frameworks/Kernel.framework'
    public = write(framework / 'Versions/A/Headers/IOKit/IODeviceTreeSupport.h', b'#define PUBLIC 1\n')
    write(framework / 'Versions/A/PrivateHeaders/IOKit/perfcontrol/IOPerfControl.h',
          b'#ifdef KERNEL_PRIVATE\n#include <kern/bits.h>\n#include <outside/not-followed.h>\n#endif\n')
    write(resource / 'include/stdatomic.h', b'#define ATOMIC_SOURCE 1\n')
    alias = framework / 'PrivateHeaders/IOKit/IODeviceTreeSupport.h'
    alias.parent.mkdir(parents=True)
    os.link(public, alias)
    return sdk, resource


def sample_result(snapshot):
    sources = {name: 'a' * 64 for name in module.FILES}
    value = deepcopy(snapshot)
    value.update(schema=module.SCHEMA, feature=module.MODE, source_head='b' * 40, run_id=1, run_attempt=1,
                 source_sha256=sources, authority=dict(module.AUTHORITY), passed=snapshot['inventory_complete'],
                 stage='complete', SDK_version='26.5', same_as205_SDK_version=True, root_query_attempts=4,
                 compiler_translation_attempts=0, preprocessor_attempts=0, IIG_attempts=0, archive_GETs=0,
                 source_text_GETs=0, object_reads=0, tool_binary_hashes=0, nm_invocations=0, kernel_builds=0,
                 links=0, device_operations=0, queries={name:dict(attempted=True, returncode=0,
                 value='observed', failure_code=None) for name in
                 ('sdk_path', 'sdk_version', 'compiler_path', 'compiler_resource')})
    value['queries']['sdk_version']['value'] = '26.5'
    return value, 'b' * 40, 1, sources


def query_capture_fixture(stdout_bytes, stderr_bytes, timeout=False):
    # Synthetic pipe/selector/process objects exercise capture without starting any tool.
    stats = dict(kills=0, waits=0, closed=0, largest_read=0)

    class Pipe:
        def __init__(self, descriptor, size):
            self.descriptor, self.remaining = descriptor, size
        def fileno(self):
            return self.descriptor
        def close(self):
            stats['closed'] += 1

    class Process:
        def __init__(self):
            self.stdout, self.stderr = Pipe(10, stdout_bytes), Pipe(11, stderr_bytes)
            self.returncode = None
        def poll(self):
            return self.returncode
        def kill(self):
            stats['kills'] += 1
            self.returncode = -9
        def wait(self, timeout):
            assert 0 < timeout <= 30
            stats['waits'] += 1
            self.returncode = 0 if self.returncode is None else self.returncode
            return self.returncode

    class Selector:
        def __init__(self):
            self.streams = {}
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def register(self, stream, events):
            self.streams[stream.fileno()] = stream
        def unregister(self, stream):
            del self.streams[stream.fileno()]
        def get_map(self):
            return self.streams
        def select(self, remaining):
            if timeout:
                return []
            from types import SimpleNamespace
            return [(SimpleNamespace(fd=fd, fileobj=stream), module.selectors.EVENT_READ)
                    for fd, stream in self.streams.items()]

    process = Process()
    pipes = {10:process.stdout, 11:process.stderr}
    def read(descriptor, requested):
        stats['largest_read'] = max(stats['largest_read'], requested)
        pipe = pipes[descriptor]
        count = min(pipe.remaining, requested)
        pipe.remaining -= count
        return b'x' * count
    old = module.subprocess.Popen, module.selectors.DefaultSelector, module.os.set_blocking, module.os.read
    try:
        module.subprocess.Popen = lambda *args, **kwargs: process
        module.selectors.DefaultSelector = Selector
        module.os.set_blocking = lambda descriptor, blocking: None
        module.os.read = read
        try:
            rc, stdout, stderr = module.bounded_query(['synthetic-metadata-query'])
            outcome = (rc, len(stdout), len(stderr))
        except (ValueError, module.subprocess.TimeoutExpired) as error:
            outcome = type(error).__name__
    finally:
        module.subprocess.Popen, module.selectors.DefaultSelector, module.os.set_blocking, module.os.read = old
    return outcome, stats


def run():
    counts = [0, 0, 0]

    def check(group, condition):
        assert condition
        counts[group] += 1

    def denied(group, function):
        try:
            function()
        except ValueError:
            counts[group] += 1
        else:
            raise AssertionError('new inventory denial failed')

    with tempfile.TemporaryDirectory(prefix='note10-inventory-fixture-') as temporary:
        directory = Path(temporary).resolve()
        sdk, resource = setup(directory)
        good = module.inventory(sdk, resource, True)
        check(0, len(good['roots']) == 7 and [r['role'] for r in good['roots']] == list(module.ROOT_ROLES) and
              len(good['headers']) == 38 and good['required_count'] == 15)
        private = good['headers']['IOKit/perfcontrol/IOPerfControl.h']
        check(0, private['status'] == 'present' and private['preferred']['role'] == 'sdk-private-versioned')
        check(0, good['headers']['stdatomic.h']['preferred']['role'] == 'compiler-builtin')
        check(0, len(good['required_missing']) == 12 and all(n in good['required_missing'] for n in
              ('kern/thread_call.h', 'DriverKit/IOService.h', 'DriverKit/IOMemoryDescriptor.h')))
        check(0, all([r['role'] for r in h['candidates']] == list(module.ROOT_ROLES) for h in good['headers'].values()))
        aliases = good['headers']['IOKit/IODeviceTreeSupport.h']['candidates']
        check(0, len({r['file_id'] for r in aliases if r['status'] == 'present'}) == 1)
        check(0, good['inventory_complete'] is True and good['all_required_headers_present'] is False)
        file = good['files'][private['preferred']['file_id']]
        check(0, file['kernel_private_guard_literal_seen'] is True and file['conditional_edges_evaluated'] is False and
              'outside/not-followed.h' in good['outside_manifest_include_tokens'] and good['compile_recipe_closed'] is False)

        check(1, module.validate_inventory(good) is None)
        check(1, good['header_source_reads'] == good['header_source_hashes'] == good['unique_header_files'] == 3)
        before = module.HEADER_CAP
        try:
            module.HEADER_CAP = 32
            capped = module.inventory(sdk, resource, True)
        finally:
            module.HEADER_CAP = before
        check(1, len(capped['headers']) == 38 and not capped['inventory_complete'] and
              'IOKit/perfcontrol/IOPerfControl.h' in capped['required_rejected'])
        before = module.TOTAL_CAP
        try:
            module.TOTAL_CAP = 1
            capped = module.inventory(sdk, resource, True)
        finally:
            module.TOTAL_CAP = before
        check(1, capped['header_source_bytes'] == capped['header_source_reads'] == 0 and
              len(capped['headers']) == 38 and capped['inventory_complete'] is False)
        before = module.UNIQUE_CAP
        try:
            module.UNIQUE_CAP = 1
            capped = module.inventory(sdk, resource, True)
        finally:
            module.UNIQUE_CAP = before
        check(1, capped['unique_header_files'] == capped['header_source_hashes'] == 1 and
              len(capped['headers']) == 38 and capped['inventory_complete'] is False)
        outside = (directory / 'outside').resolve(); outside.mkdir()
        root = dict(role=module.ROOT_ROLES[0], path=str(outside), canonical_path=str(outside),
                    available=True, status='available')
        budget = dict(complete=True, source_reads=0, bytes_read=0, hashes=0)
        rejected = module.observe_candidate(root, module.REQUIRED[0], [sdk, resource], {}, {}, budget)
        check(1, rejected['status'] == 'rejected' and rejected['reason'] == 'header_outside_actual_roots' and
              budget['source_reads'] == 0)
        unresolved = module.inventory(None, None, False)
        check(1, len(unresolved['required_unobserved']) == 15 and unresolved['required_missing'] == [] and
              len(unresolved['headers']) == 38 and unresolved['inventory_complete'] is False)
        lexical = module.lexical_metadata('\n'.join('#include <extra/h%d.h>' % n for n in range(40)).encode())
        check(1, len(lexical['literal_includes']) == 32 and lexical['lexical_capture_truncated'] is True and
              lexical['conditional_edges_evaluated'] is False)

        outcome, stats = query_capture_fixture(module.QUERY_CAP, module.QUERY_CAP)
        check(1, outcome == (0, module.QUERY_CAP, module.QUERY_CAP) and
              stats == dict(kills=0, waits=1, closed=2, largest_read=4096))
        outcome, stats = query_capture_fixture(module.QUERY_CAP + 1, 0)
        check(1, outcome == 'ValueError' and stats['kills'] == stats['waits'] == 1 and
              stats['closed'] == 2 and stats['largest_read'] <= 4096)
        outcome, stats = query_capture_fixture(0, module.QUERY_CAP + 1)
        check(1, outcome == 'ValueError' and stats['kills'] == stats['waits'] == 1 and
              stats['closed'] == 2 and stats['largest_read'] <= 4096)
        outcome, stats = query_capture_fixture(0, 0, timeout=True)
        check(1, outcome == 'TimeoutExpired' and stats['kills'] == stats['waits'] == 1 and
              stats['closed'] == 2 and stats['largest_read'] == 0)

        check(2, module.validate_result(*sample_result(good)) is None)
        item = sample_result(good); del item[0]['headers'][module.REQUIRED[-1]]
        denied(2, lambda: module.validate_result(*item))
        item = sample_result(good); item[0]['required_missing'].pop()
        denied(2, lambda: module.validate_result(*item))
        item = sample_result(good); item[0]['headers'][module.REQUIRED[0]]['candidates'].pop()
        denied(2, lambda: module.validate_result(*item))
        item = sample_result(good); item[0]['root_query_attempts'] = True
        denied(2, lambda: module.validate_result(*item))
        item = sample_result(good); item[0]['compiler_translation_attempts'] = 1
        denied(2, lambda: module.validate_result(*item))
        item = sample_result(good); item[0]['authority']['compile_recipe_closed'] = True
        denied(2, lambda: module.validate_result(*item))
        item = sample_result(good); item[0]['source_sha256'] = dict(item[3], **{module.FILES[0]:'0' * 64})
        denied(2, lambda: module.validate_result(*item))
    return dict(groups=3, cases=sum(counts), group_cases=counts, SDK_reads=0, tool_queries=0,
                compiler_translations=0, old_suites=0)
