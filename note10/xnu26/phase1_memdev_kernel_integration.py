"""Fixed v170 memdev source/member/provider proof in the existing1077-input link."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

import current_native_kernel as native
from phase1_iostorage_native_inputs import ROOT, require, sha
from prepare_memdev_wide_extent import REL, PATCH_NAME, PATCH_SHA256, POSTIMAGE_SHA256, REFERENCE_PINS, patch_bytes
from user_instruction_diagnostics import summarize

PROVIDERS = {'_bdevsw_add': 'bsd/kern/bsd_stubs.c', '_cdevsw_add_with_bdev': 'bsd/kern/bsd_stubs.c', '_buf_biodone': 'bsd/vfs/vfs_bio.c', '_buf_blkno': 'bsd/vfs/vfs_bio.c', '_buf_count': 'bsd/vfs/vfs_bio.c', '_buf_device': 'bsd/vfs/vfs_bio.c', '_buf_flags': 'bsd/vfs/vfs_bio.c', '_buf_map': 'bsd/vfs/vfs_bio.c', '_buf_setcount': 'bsd/vfs/vfs_bio.c', '_buf_seterror': 'bsd/vfs/vfs_bio.c', '_buf_setresid': 'bsd/vfs/vfs_bio.c', '_buf_unmap': 'bsd/vfs/vfs_bio.c', '_devfs_make_node': 'bsd/miscfs/devfs/devfs_tree.c', '_devfs_remove': 'bsd/miscfs/devfs/devfs_tree.c', '_enodev': 'bsd/kern/subr_xxx.c', '_enodev_strat': 'bsd/kern/subr_xxx.c', '_proc_suser': 'bsd/kern/kern_proc.c', '_uio_resid': 'bsd/kern/kern_subr.c', '_uiomove64': 'bsd/kern/kern_subr.c', '_bcopy_phys': 'osfmk/arm64/loose_ends.c', '_kernel_pmap': 'osfmk/arm/pmap/pmap.c', '_pmap_find_phys': 'osfmk/arm/pmap/pmap.c', '_mapping_set_mod': 'osfmk/arm/pmap/pmap.c', '_memmove': 'osfmk/arm64/bcopy.s', '_panic': 'osfmk/kern/debug.c', '_mach_assert_jump_key': 'osfmk/kern/debug.c', '_printf': 'osfmk/kern/printf.c'}
PROVIDER_PINS = {'bsd/kern/bsd_stubs.c': '949418ef11cf9237877e2c41de2ae1c0d18b04a4c03121208f44ec614b8ddff9', 'bsd/vfs/vfs_bio.c': 'ff92795c78510bec422b0a25e2c7ac51e9c9fbecc9f8eb1a83db5bdfe260bce4', 'bsd/miscfs/devfs/devfs_tree.c': '506762c70c2ce05464750f4e5e96dec3c1c1eee24d2322582cfd91456283063f', 'bsd/kern/subr_xxx.c': 'b2518759950620d6c5964d548c6e1838eb6fa83252a78760c71826edd57c548c', 'bsd/kern/kern_proc.c': '76f81fddf8562ae06c9229fef4be95bd9505cdd3866b2d0565b8104d2120f0c7', 'bsd/kern/kern_subr.c': '2ddfaf264427bed774733a3d37974e78343c097b8c156caaea0e6a7d695bdd62', 'osfmk/arm64/loose_ends.c': '07b99100ecbdc6ea40a1ce32af2a6fb8f086a1d4b40245c9b4c73c112aaafdaf', 'osfmk/arm/pmap/pmap.c': 'e1c6bc87e58a51c99918f2197a7e7c848eb6a68918f06879c4800e770a28b2d9', 'osfmk/arm64/bcopy.s': '36ed84c4ccdbb30760fad09980574d61c06eefbd4ba71b580d347c26118bff29', 'osfmk/kern/debug.c': 'f4694593a5dfeb5805efe869da9461d951e58b5ea2c4eb343d25d5ca166fe14c', 'osfmk/kern/printf.c': 'eb848a67bd193fc11ef2fe7d82ebf9d6af3bf7f54ac6b4ea9eea0c2261be246c'}
CARRIED = {'storage_final_PASS': '6d72d9b33c80d43712e20d454d5d9774693966e07ef8986cef769cac2248a11d', 'host9_PASS': 'cafbc2588c32d8f46b987b36a30eb9aefd77e3972bb5621fa55c51b9e14feaca', 'projection3_PASS': 'd72620771a5dc643ebb17a09dc19fb3855366537840c6ed11e0139ca56b43859', 'original_v169_FAIL': 'b985f3a9be5e501c151b6415f1fdb4caa55a153a41d30d07bd615cf41e697e53', 'local8_PASS': '49181dbe8a5f0495c5e4584b58cc426514a1a9a4d1c9889208beb6b6723e9c6a', 'original_v169_CI_passed': False}
EXPORTS = ['_mdev', '_mdevBMajor', '_mdevCMajor', '_mdevadd', '_mdevgetrange', '_mdevinit', '_mdevlookup', '_mdevremoveall']

def begin():
    return dict(schema='note10-v170-memdev-kernel-integration-v1', stage='source-binding',
        failure_code='source_binding_failed', predicates={}, patch_apply_attempts=0,
        native_compile_attempts=0, native_compiler_successes=0, dependency_compile_attempts=0,
        dependency_compiler_successes=0, compile_counts_complete=True, final_link_attempts=0,
        provider_binding_verified=False, kernel_link_verified=False, carried_evidence=CARRIED)


def gate(observation, code, condition):
    observation['predicates'][code] = bool(condition)
    observation['failure_code'] = 'none' if condition else code
    require(condition, code)


def roots(source, output, sdk):
    return {str(source): 'XNU', str(ROOT / 'note10/xnu26'): 'port',
        str(ROOT / 'note10/private/windows-xnu'): 'generated', str(output): 'output', str(sdk): 'SDK'}


def apply_patch(source, output, sdk, observation):
    observation.update(stage='patch-binding', failure_code='patch_binding_failed')
    patch = ROOT / 'note10/xnu26/patches' / PATCH_NAME
    before = (source / REL).read_bytes()
    gate(observation, 'exact_patch_inputs', sha(ROOT / 'note10/xnu26/prepare_memdev_wide_extent.py') ==
         '7ecb40c0f1371fa79c97b912fbf8e4f7edc641492bbf2e0c6ced1fa40117ede1' and patch_bytes(before) == patch.read_bytes())
    observed = {name: sha(source / name) for name in PROVIDER_PINS}
    observation['provider_source_sha256'] = observed
    gate(observation, 'real_provider_source_pins', observed == PROVIDER_PINS)
    observation.update(patch_apply_attempts=1, failure_code='patch_apply_failed')
    call = subprocess.run(['git', '-c', 'core.autocrlf=false', 'apply', str(patch)], cwd=source,
                          capture_output=True, timeout=30)
    (output / 'memdev-patch.internal.log').write_bytes(call.stdout + call.stderr)
    observation['patch_returncode'] = call.returncode
    proof = dict(schema='note10-v170-extra-memdev-patch-v1', source=REL,
        preimage_sha256=REFERENCE_PINS[REL][1], postimage_sha256=POSTIMAGE_SHA256, patch_sha256=PATCH_SHA256)
    observation['extra_patch'] = proof
    gate(observation, 'exact_patch_postimage', call.returncode == 0 and sha(source / REL) == POSTIMAGE_SHA256 and
         (source / REL).read_bytes().count(b'(uint64_t)mdev[devid].mdSize << 12') == 8)
    return proof


def bind_inventory(current, observation):
    rows = [row for row in current['inventory'] if row['source'] == REL]
    observation['native_inventory_count'] = len(current['inventory'])
    gate(observation, 'one_patched_native_member', len(current['inventory']) == 1067 and len(rows) == 1 and
         rows[0]['component'] == 'bsd' and rows[0]['kind'] == 'C' and rows[0]['source_sha256'] == POSTIMAGE_SHA256)
    observation.update(producer_id=current['producer_id'], input_binding=current['input_binding'],
        native_manifest_sha256=native.digest([{k: row[k] for k in ('source', 'component', 'kind', 'source_sha256')}
                                              for row in current['inventory']]))


def bind_providers(current, rows, defined, references, observation):
    observation.update(stage='provider-binding', failure_code='provider_binding_failed')
    by_path = {row['object_path']: row for row in rows}
    memdev = [row for row in rows if row['source'] == REL]
    gate(observation, 'one_current_memdev_object', len(rows) == len(by_path) == 1077 and len(memdev) == 1 and
         memdev[0]['source_sha256'] == POSTIMAGE_SHA256)
    member = memdev[0]
    own_exports = sorted(name for name, owners in defined.items() if member['object_path'] in owners)
    own_imports = sorted(name for name, owners in references.items() if member['object_path'] in owners)
    gate(observation, 'bounded_memdev_symbol_metadata', len(own_exports) <= 32 and len(own_imports) <= 256 and
         all(re.fullmatch(r'[A-Za-z_.$][A-Za-z0-9_.$]{0,383}', name) for name in own_exports + own_imports))
    observation['memdev_member'] = {k: member[k] for k in ('source', 'source_sha256', 'object_sha256')}
    observation.update(defined_exports=own_exports, observed_imports=own_imports)
    gate(observation, 'exact_memdev_exports_and_imports', own_exports == EXPORTS and own_imports == sorted(PROVIDERS))
    providers, predicates = {}, {}
    for symbol, expected in PROVIDERS.items():
        owners = defined.get(symbol, [])
        row = by_path.get(owners[0]) if len(owners) == 1 else None
        predicates[symbol] = row is not None and row['source'] == expected and row['source_sha256'] == PROVIDER_PINS[expected]
        if row is not None:
            providers[symbol] = {k: row[k] for k in ('source', 'source_sha256', 'object_sha256')}
    observation.update(providers=providers, provider_predicates=predicates)
    gate(observation, 'all27_direct_real_providers', len(providers) == 27 and all(predicates.values()))
    observation['provider_binding_verified'] = True


def final_symbols(symbols, linked, observation):
    observation.update(stage='final-symbols', failure_code='final_memdev_symbols_failed')
    names = [parts[-1] for line in symbols.splitlines() if len(parts := line.split()) >= 3 and
             re.fullmatch(r'[0-9a-fA-F]+', parts[0]) and parts[-2].isupper()]
    counts = {name: names.count(name) for name in EXPORTS + sorted(PROVIDERS)}
    observation['final_symbol_counts'] = counts
    gate(observation, 'final35_names_once', linked['object_count'] == 1077 and all(n == 1 for n in counts.values()))
    observation.update(stage='complete', failure_code='none', kernel_link_verified=True)


def storage_sink(observation, diagnostic_roots):
    def record(name, code, stderr, timed_out):
        require(re.fullmatch(r'[A-Za-z0-9_.+-]{1,96}', name), 'closed storage source label required')
        row = dict(source='@storage/' + name, timed_out=timed_out,
                   compiler_diagnostics=summarize(stderr, diagnostic_roots))
        if code is not None:
            row['returncode'] = code
        observation.setdefault('storage_diagnostics', []).append(row)
    return record


def link_runner(observation, diagnostic_roots):
    def diagnostics(stderr):
        raw = stderr.encode() if isinstance(stderr, str) else stderr
        normalized = re.sub(rb'(?m)^ld: (?!(?:fatal error|error|warning|note): )', b'error: ', raw[:65536])
        normalized = re.sub(rb'(?m)^ld: ', b'', normalized)
        value = summarize(normalized, diagnostic_roots)
        value.update(stderr_sha256=hashlib.sha256(raw).hexdigest(), stderr_bytes=len(raw), input_truncated=len(raw) > 65536)
        return value

    def run(argv, **kwargs):
        observation.update(final_link_attempts=1, failure_code='final_link_failed')
        try:
            call = subprocess.run(argv, **kwargs)
        except subprocess.TimeoutExpired as error:
            observation.update(link_timed_out=True, link_diagnostics=diagnostics(error.stderr or b''))
            raise
        observation.update(final_link_returncode=call.returncode,
                           link_diagnostics=diagnostics(call.stderr))
        return call
    return run


def collect_compile_reports(private, observation, diagnostic_roots):
    native_attempts = native_successes = dependency_attempts = dependency_successes = 0
    failed, seen = [], []
    for relative, dependency in [('objects/DEVELOPMENT/current-c-result.json', False),
        ('objects/DEVELOPMENT/current-cxx-result.json', False), ('objects/DEVELOPMENT/current-asm-result.json', False),
        ('current-public-result.json', True), ('current-link-metadata-result.json', True)]:
        path = private / relative
        if not path.is_file():
            continue
        seen.append(Path(relative).name)
        require(path.stat().st_size <= 32 * 1024 * 1024, 'bounded existing compiler metadata required')
        units = json.loads(path.read_bytes())['units']
        require(len(units) <= (4 if dependency else 1067), 'bounded current compile rows required')
        if dependency:
            dependency_attempts += len(units)
            dependency_successes += sum(row['passed'] is True for row in units)
        else:
            native_attempts += len(units)
            native_successes += sum(row['passed'] is True for row in units)
        for row in units:
            require(type(row['source']) is str and re.fullmatch(r'[@A-Za-z0-9_.+/-]{1,192}', row['source']) and
                    not row['source'].startswith('/') and '..' not in row['source'].split('/'),
                    'closed public compiler source identity required')
            if row['source'] == REL and 'diagnostics' in row:
                observation['memdev_compiler_diagnostics'] = summarize(row['diagnostics'].encode(), diagnostic_roots)
            if not row['passed']:
                failed.append(row)
    observation.update(native_compile_attempts=native_attempts, native_compiler_successes=native_successes,
        dependency_compile_attempts=dependency_attempts, dependency_compiler_successes=dependency_successes,
        completed_compile_reports=seen)
    if failed:
        row = sorted(failed, key=lambda r: r['source'])[0]
        if 'diagnostics' in row:
            observation['first_compiler_failure'] = dict(source=row['source'],
                compiler_diagnostics=summarize(row['diagnostics'].encode(), diagnostic_roots))
        else:
            observation['first_compiler_failure'] = dict(source=row['source'], failure_code='dependency_compile_failed')
            log = (private / 'public-dependencies.log' if row['source'].startswith('@public/') else
                   private / 'native-link' / (Path(row['source']).stem + '.log'))
            if log.is_file():
                with log.open('rb') as stream:
                    prefix = stream.read(65536)
                observation['first_compiler_failure'].update(capture='existing-private-log-prefix',
                    actual_log_bytes=log.stat().st_size, compiler_diagnostics=summarize(prefix, diagnostic_roots))
