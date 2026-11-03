"""Closed v72 input/evidence additions; existing package actuator is unchanged."""
import hashlib
import json
from pathlib import Path
import re

PROFILE = 'sha256-kat-builtin-init-v2'
EXTRA_FIELDS = ('minimal_init_elf_sha256', 'initramfs_cpio_sha256',
                'builtin_init_manifest_sha256', 'guarded_init_main_sha256')
LOGS = (('last_kmsg.txt', '/proc/last_kmsg'),
        ('console-ramoops-0', '/sys/fs/pstore/console-ramoops-0'),
        ('dmesg-ramoops-0', '/sys/fs/pstore/dmesg-ramoops-0'))


def current_boot_binding(plan, pair, diagnostic):
    # Device-specific payload pins belong to the private reviewed plan, never
    # public source constants. The live common precheck still checks the bytes.
    data = plan.get('device_profile') == 'linux-data-carrier-v1'
    native = plan.get('device_profile') == 'native-memory-observation-v1'
    fdt = plan.get('device_profile') == 'early-fdt-binding-v1'
    affinity = plan.get('device_profile') == 'cpu-affinity-binding-v1'
    stream = plan.get('device_profile') == 'sha256-stream-state-v1'
    prior_profile = 'linux-data-carrier-v1' if data else 'early-fdt-binding-v1' if native else 'cpu-affinity-binding-v1' if fdt else 'sha256-stream-state-v1' if affinity else 'sha256-kat-builtin-init-v2' if stream else 'sha256-kat-recovery-v1'
    prior_head = '59bfd8d9f21047c9d943cd0dd4f4eb96fb5459e9' if data else 'a77f1eca32d1888f3266f49412dda9f0129f8719' if native else '24f0fb9c4680517d6b0411a9985847c42b692376' if fdt else '7e4a8c992f95f01429e824404378fa9271c0eb8e' if affinity else '149cb74c3f7640f2e26dfdcd1d775ec99f6c02ac' if stream else '9bfe108e7fd7a063bacce9418be46d269cb872d9'
    prior_host = '59bfd8d9f21047c9d943cd0dd4f4eb96fb5459e9' if data else '7490b4286417a6581be292de0ac1a5c3a6a079aa' if native else 'a0674c29eaa2bc8938023fc2be590b9a4a84374e' if fdt else '7e4a8c992f95f01429e824404378fa9271c0eb8e' if affinity else '149cb74c3f7640f2e26dfdcd1d775ec99f6c02ac' if stream else '5e233aa5f08473d716ca2e9b3d8937c1821d513f'
    prior_source = pair.get('source_head') == prior_head and pair.get('host_profile_source_head') == prior_host
    # Package-origin validation authenticates the complete retained host map.
    # These predecessor cases are exact retained DATA tuples, never BOOT pins.
    if data:
        prior_source = prior_source or (
            pair.get('source_head') == '0696b4dbf157a2d51b68b26e4a5237a7c51daa80' and
            pair.get('host_profile_source_head') == 'bdd56f101e3e9bb83ecbadad03be24473f143447' and
            pair.get('data_host_experiment') == 'v97-current-data-reuse-v91' and
            isinstance(pair.get('data_current_binding_sha256'), str) and
            re.fullmatch('[0-9a-f]{64}', pair['data_current_binding_sha256']) and
            'data_compare_schema' not in pair)
        prior_source = prior_source or (
            pair.get('source_head') == '4f9eb149bd116db77eaf3400a25f7454577268a9' and
            pair.get('host_profile_source_head') == '4f9eb149bd116db77eaf3400a25f7454577268a9' and
            pair.get('data_compare_schema') == 'n10-data-compare-v1' and
            not any(key in pair for key in ('data_host_experiment','data_current_binding_sha256')))
        prior_source = prior_source or (
            pair.get('source_head') == '566e0416fa0dcf87e70d556ba3c01e5c2f52b1df' and
            pair.get('host_profile_source_head') == '566e0416fa0dcf87e70d556ba3c01e5c2f52b1df' and
            pair.get('data_compare_schema') == 'n10-data-compare-v2' and
            not any(key in pair for key in ('data_host_experiment','data_current_binding_sha256',
                                           'data_input_range_schema','data_linked_kernel_bytes')))
    require(pair.get('device_profile') == prior_profile and
            prior_source and
            re.fullmatch('[0-9a-f]{64}', plan.get('current_boot_payload_sha256', '')) and
            plan['current_boot_payload_sha256'] == diagnostic['payload_sha256'],
            'reviewed exact prior profile/source/current BOOT chain required')


def require(value, message):
    if not value:
        raise ValueError(message)


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True)+'\n', encoding='utf8')


def raw_file(path, data):
    """One same-buffer write; canonical int5 fifth field is nlink, not ctime."""
    with Path(path).open('xb') as stream:
        stream.write(data)
    s = Path(path).stat()
    return dict(file=Path(path).name, bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                int5=[int(s.st_dev), int(s.st_ino), int(s.st_size), int(s.st_mtime_ns), int(s.st_nlink)],
                ctime_ns=int(s.st_ctime_ns))


def input_binding(root, result, image, lines, *, fdt_owned_route=False, native_memory_route=False, data_carrier_route=False, producing_sources=None):
    from builtin_init_route import cpio, elf_manifest, sha, builtin_cmdline_policy
    root = Path(root)
    require(result.get('builtin_init_route') is True, 'builtin route result required')
    required = {'CONFIG_NOTE10_BUILTIN_INIT_ROUTE=y', 'CONFIG_INITRAMFS_FORCE=y',
                'CONFIG_INITRAMFS_COMPRESSION_NONE=y'}
    require(required.issubset(lines), 'forced raw builtin init configuration required')
    values = [l.partition('=')[2] for l in lines if l.startswith('CONFIG_INITRAMFS_SOURCE=')]
    require(len(values) == 1 and values[0].startswith('"/') and values[0].endswith('/initramfs.cpio"'),
            'actual generated builtin archive input required')
    builtin_cmdline_policy('\n'.join(lines))
    elf, archive = (root/'minimal-init.elf').read_bytes(), (root/'initramfs.cpio').read_bytes()
    manifest = json.loads((root/'minimal-init.json').read_text(encoding='utf8'))
    require(manifest == {'elf': elf_manifest(elf), 'cpio_sha256': sha(archive),
                         'cpio_bytes': len(archive),
                         'members': ['dev', 'dev/console', 'dev/kmsg', 'init', 'TRAILER!!!']},
            'closed minimal init manifest differs')
    require(archive == cpio(elf) and image.count(archive) == 1, 'exact builtin archive embedding differs')
    inputs = {'minimal_init_elf_sha256': sha(elf), 'initramfs_cpio_sha256': sha(archive),
              'builtin_init_manifest_sha256': sha((root/'minimal-init.json').read_bytes()),
              'guarded_init_main_sha256': sha((root/'overlay/init/main.c').read_bytes())}
    require(all(result.get(k) == v for k, v in inputs.items()), 'actual builtin route pins differ')
    require(sum(map(bool, (fdt_owned_route, native_memory_route, data_carrier_route))) <= 1, 'one selected route consumer required')
    if data_carrier_route:
        from linux_data_carrier import input_binding as data_binding
        inputs.update(data_binding(result, lines, elf=elf, archive=archive, raw_inputs=inputs,producing_sources=producing_sources))
    if native_memory_route:
        from native_memory_observation import input_binding as native_binding
        inputs.update(native_binding(result,lines,elf=elf,archive=archive,raw_inputs=inputs))
    if fdt_owned_route:
        from early_fdt_binding import input_binding as fdt_binding
        inputs.update(fdt_binding(result,lines,elf=elf,archive=archive,raw_inputs=inputs))
    return inputs


def boot_identity_strings(data, identity, cycle):
    # Metadata inspection only, never acceptance of earlier boot frames. Keep
    # an earlier current-cycle boot visible even when latest-boot clipping wins.
    pattern = (rb'N10BOOTLINK2 boot=([0-9a-f]{32}) N10RET1 id='+identity.encode()+
               rb' cycle='+cycle.encode()+rb' ')
    return {m[1].decode() for m in re.finditer(pattern, data)}


def decode(data, banner, identity, cycle, *, digest_decoder=None, digest_marker=b'N10SHA1', component_evidence=None):
    from sha256_kat_device_profile import decode_selected
    require(len(boot_identity_strings(data, identity, cycle)) == 1,
            'ambiguous/multiple retained boot identities for one current cycle')
    options = dict(digest_decoder=digest_decoder)
    if component_evidence is not None:
        options['component_evidence'] = component_evidence
    clipped, observation = decode_selected(data, banner, identity, cycle, **options)
    start = observation['boot_byte_start']
    boot = data[start:]
    route = list(re.finditer(rb'N10ROUTE2 id=([0-9a-f]{32}) boot=([0-9a-f]{32}) cycle=([0-9a-f]{32}) route=builtin exec_attempt=1(?=\r?\n)', boot))
    init = list(re.finditer(rb'N10INIT2 id=([0-9a-f]{32}) boot=([0-9a-f]{32}) cycle=([0-9a-f]{32}) route=builtin started=1(?=\r?\n)', boot))
    require(len(route) == len(init) == 1 and route[0].groups() == init[0].groups(),
            'one matching route attempt and actual PID1 startup required')
    rid, token, cyc = route[0].groups()
    require(rid == identity.encode() and cyc == cycle.encode() and token != b'0'*32 and
            route[0].start() < init[0].start() and b'exec_failed=' not in boot,
            'builtin route/startup identity or order differs')
    frame_lines = []
    for line in boot.splitlines():
        current_sha = digest_marker+b' id='+identity.encode() in line
        current_ret = b'N10RET1 id='+identity.encode()+b' cycle='+cycle.encode() in line
        if current_sha or current_ret:
            require(b'N10BOOTLINK2 boot='+token+b' N10' in line,
                    'KAT/return frame lacks same boot association')
            frame_lines.append(line)
    require(frame_lines and boot.find(digest_marker+b' id='+identity.encode()) > init[0].end(),
            'KAT must follow actual minimal PID1 startup')
    # All current records in a file must be associated. Decoders keep their
    # original checksums/order semantics; this prefix is not authentication.
    observation['boot_identity'] = token.decode()
    observation['minimal_PID1_start_observed'] = True
    if component_evidence is not None:
        component_evidence['pid1_validation'] = 'validated'
        component_evidence['return_boot_association'] = 'validated'
    return clipped, observation


def probe(adb, remote, out, index):
    from sha256_kat_device_profile import log_probe_command
    require(remote in dict(LOGS).values(), 'fixed snapshot source required')
    command = ('shell', '-T', log_probe_command(remote))
    data = adb.call(*command)
    require(type(data) is bytes, 'native probe bytes required')
    row = raw_file(Path(out)/('probe-'+str(index)+'.bin'), data)
    normalized = {b'N10KAT_READABLE\r\n': b'N10KAT_READABLE\n',
                  b'N10KAT_ABSENT\r\n': b'N10KAT_ABSENT\n'}.get(data, data)
    row.update(command=list(command), raw_repr=repr(data), translated=normalized != data,
               normalized_repr=repr(normalized), metadata_only=True)
    # Receipt must exist before normalized metadata can be used.
    save(Path(out)/('probe-'+str(index)+'.json'), row)
    require(normalized in (b'N10KAT_READABLE\n', b'N10KAT_ABSENT\n'), 'malformed native log probe')
    return normalized


def snapshot(adb, out, bound, cycle, *, decode_fn=None):
    """All three fixed sources, once each, before evaluation; no raw merge."""
    out = Path(out)
    decode_fn = decode_fn or decode
    profile_name = bound.get('device_profile', PROFILE)
    rows, snapshots, selections, observations = [], {}, {}, []
    rejected_components = []
    for index, (name, remote) in enumerate(LOGS):
        from sha256_kat_device_profile import log_probe_command
        row = dict(name=name, remote=remote, status='pending',
                   probe_command=['shell', '-T', log_probe_command(remote)],
                   cat_command=['exec-out', 'cat', remote], cat_timeout_seconds=60)
        try:
            answer = probe(adb, remote, out, index)
            if answer == b'N10KAT_ABSENT\n':
                row['status'] = 'absent'
            else:
                data = adb.call('exec-out', 'cat', remote, timeout=60)
                require(type(data) is bytes and 0 < len(data) <= 16*1024*1024, 'raw log bound invalid')
                row.update(raw_file(out/name, data), status='captured')
                snapshots[name] = data
        except Exception as error:
            # Record failure and continue the remaining distinct snapshot
            # sources, never retry or turn this failure into a successful run.
            row.update(status='error', error_type=type(error).__name__, error=str(error)[:2048])
        rows.append(row)
        save(out/'capture-index.json', {'device_profile': profile_name, 'sources': rows,
             'logs_sha256': {n: hashlib.sha256(v).hexdigest() for n, v in snapshots.items()}})
    errors = [r['name']+': '+r.get('error', '') for r in rows if r['status'] == 'error']
    for name, data in snapshots.items():
        if cycle.encode() not in data:
            continue
        try:
            clipped, observation = decode_fn(data, bound['kernel_banner'], bound['build_evidence_id'], cycle)
            selection = raw_file(out/('selected-'+name), clipped)
            selections[name] = dict(selected_file=selection['file'], selected_sha256=selection['sha256'])
            observations.append(observation)
        except Exception as error:
            errors.append(name+': '+str(error))
            components = getattr(error, 'component_evidence', None)
            if isinstance(components, dict):
                rejected_components.append(dict(source=name, components=components))
    same = bool(observations) and all(o == observations[0] for o in observations)
    # Offsets may differ between independent intact sources; compare decoded
    # semantic identity rather than the position in each source file.
    if observations:
        same = all(all(o[k] == observations[0][k] for k in
                       ('kat', 'auto_return', 'boot_identity', 'minimal_PID1_start_observed')) for o in observations)
    if not observations:
        errors.append('no intact current-cycle minimal PID1/KAT/return observation')
    elif not same:
        errors.append('independent current-cycle observations disagree')
    passed = not errors and same
    result = dict(directory=str(out), device_profile=profile_name, diagnostic_passed=passed,
                  log_selections=selections, observations=observations, errors=errors,
                  logs_sha256={n: hashlib.sha256(v).hexdigest() for n, v in snapshots.items()},
                  snapshot_sources=rows, partition_writes=False, rebooted=False, xnu_executed=False,
                  legacy_evaluations_claimed=False, hardware_return_proven_by_frames=False)
    result['retained_boot_identity_strings'] = sorted(set().union(*[
        boot_identity_strings(data, bound['build_evidence_id'], cycle) for data in snapshots.values()]))
    result['actual_hardware_boot_count_proven'] = False
    if rejected_components:
        result['rejected_component_observations'] = rejected_components
    save(out/'result.json', result)
    return result
