"""Source-bound host interpretation of the immutable v133 PID1 tag mismatch."""
import ast
import hashlib
import re

MAX_LOG_BYTES = 16 * 1024 * 1024
SOURCE_COMMIT = '9b68415369cb498560b5f922cc9dc6d14f92b578'
SOURCE_MAP_SHA256 = '611735dffb8f2e47d06e580b89f587742fa77688c8a1e688235e5e29ce2c9f82'
SOURCE_PINS = {
    'build': 'd585ceb1ef0f5f76ac5ef2afcbc0bfc3451dee21b8ced9407fb9d84b505f41c2',
    'loader': '2663f22b3109b17f300fd80d2999b6aa18f052891b6157c63c5c020c69bc9b55',
    'consumer': 'c00d1e08e99be5be3398c3b1a8c00d91799b36119475f35d0f9a39e5f1484b4a',
}


def derive_binding(build, loader, consumer):
    """Derive tags/stages from pinned source bytes, without executing them."""
    sources = dict(build=build, loader=loader, consumer=consumer)
    if any(type(raw) is not bytes or hashlib.sha256(raw).hexdigest() != SOURCE_PINS[key]
           for key, raw in sources.items()):
        raise ValueError('exact immutable133 producer/consumer sources required')
    tree = ast.parse(build.decode('utf-8'))
    assignments = [node for node in ast.walk(tree) if isinstance(node, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == 'loader' for t in node.targets)]
    if len(assignments) != 1:
        raise ValueError('unique actual PID1 construction required')
    call = assignments[0].value
    if (not isinstance(call, ast.Call) or not isinstance(call.func, ast.Attribute)
            or call.func.attr != 'replace' or len(call.args) != 2 or call.keywords
            or not isinstance(call.func.value, ast.Call)
            or not isinstance(call.func.value.func, ast.Attribute)
            or call.func.value.func.attr != 'read_bytes'):
        raise ValueError('actual PID1 literal replacement boundary differs')
    before, after = (ast.literal_eval(arg) for arg in call.args)
    emitter = re.search(rb'N10XNU[0-9]+ id=%s cycle=%\.32s stage=%s\\n', loader)
    native = re.search(rb"prefix='(N10XNU[0-9]+) id='\+identity", consumer)
    if emitter is None or native is None:
        raise ValueError('actual emitter/consumer boundaries absent')
    emitted = emitter.group().split(b' ', 1)[0].replace(before, after).decode('ascii')
    stages = tuple(sorted(set(match.decode('ascii') for match in
                              re.findall(rb'event\("([a-z0-9-]+)"\)', loader))))
    binding = dict(schema='note10-v134-immutable133-PID1-binding-v1',
                   source_commit=SOURCE_COMMIT, source_map_sha256=SOURCE_MAP_SHA256,
                   source_sha256=dict(SOURCE_PINS), pid1_prefix=emitted,
                   native_prefix=native.group(1).decode('ascii'), pid1_stages=list(stages))
    if emitted != 'N10XNU132' or binding['native_prefix'] != 'N10XNU133' or stages != (
            'begin', 'full-owned-parcel-ready', 'kexec-load-once', 'kexec-reboot-once',
            'normal-recovery-request', 'recovery-returned-terminal-no-retry'):
        raise ValueError('immutable133 mismatch relationship differs')
    return binding


def _binding_valid(binding):
    return binding == dict(schema='note10-v134-immutable133-PID1-binding-v1',
                           source_commit=SOURCE_COMMIT, source_map_sha256=SOURCE_MAP_SHA256,
                           source_sha256=SOURCE_PINS, pid1_prefix='N10XNU132',
                           native_prefix='N10XNU133', pid1_stages=[
                               'begin', 'full-owned-parcel-ready', 'kexec-load-once',
                               'kexec-reboot-once', 'normal-recovery-request',
                               'recovery-returned-terminal-no-retry'])


def decode(raw, identity, cycle, binding):
    """Interpret one saved capture; no device epoch or physical entry inference."""
    if not _binding_valid(binding):
        raise ValueError('exact source-derived immutable133 binding required')
    if any(type(value) is not str or re.fullmatch('[0-9a-f]{32}', value) is None
           for value in (identity, cycle)):
        raise ValueError('exact build/cycle identity required')
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_LOG_BYTES:
        raise ValueError('one bounded saved log required')
    result = dict(schema='note10-v134-retrospective133-observation-v1',
                  build_evidence_id=identity, cycle=cycle,
                  source_binding=binding, retrospective_compatibility=True,
                  identity_bound_PID1_begin_observed=False, ambiguous_begin=False,
                  PID1_stages_observed=[], internal_kexec_load_attempts_observed=None,
                  internal_kexec_REBOOT_attempts_observed=None,
                  reservation_ready_observed=False, final_hook_qualified_observed=False,
                  normal_recovery_fallback_observed=False, gate_refusals=[],
                  iommu_refusal_states=[], g2d_refusal_details=[], score_refusal_details=[],
                  log_reboot_epoch_proven=False, new_device_operation=False,
                  physical_XNU_entry_established=False, full_XNU_boot_established=False,
                  watchdog_reset_cause_established=False,
                  evidence_limit='Exact immutable133 PID1 uses132 while native kernel uses133. '
                  'Saved same-build/cycle sections do not establish reboot epoch, original240s '
                  'return, reset cause, physical XNU entry or its absence.')
    text = raw.decode('utf-8', errors='replace')
    pid = r'(?<![A-Za-z0-9_])' + re.escape('N10XNU132 id=' + identity + ' cycle=' + cycle + ' stage=')
    begin = list(re.finditer(pid + r'begin\r?$', text, re.M))
    if len(begin) != 1:
        result['ambiguous_begin'] = len(begin) > 1
        return result
    tail = text[begin[0].start():]
    # Another producer/identity/epoch begin after the admitted boundary is a
    # conservative refusal, including a native133 begin that this PID1 cannot emit.
    if re.search(r'N10XNU[0-9]+ id=[0-9a-f]{32} cycle=[0-9a-f]{32} stage=begin\r?$',
                 tail[len(begin[0].group()):], re.M):
        result['ambiguous_begin'] = True
        return result
    # Alias only exact PID1 stage lines in memory. Native kernel lines stay133.
    stages = '|'.join(re.escape(s) for s in binding['pid1_stages'])
    native_pid = 'N10XNU133 id=' + identity + ' cycle=' + cycle + ' stage='
    aliased = re.sub(pid + '(' + stages + r')\r?$',
                     lambda m: native_pid + m.group(1), tail, flags=re.M)
    stage_matches = re.findall(pid + '(' + stages + r')\r?$', tail, re.M)
    result['PID1_alias_lines'] = len(stage_matches)
    result['identity_bound_PID1_begin_observed'] = True
    result['PID1_stages_observed'] = [s for s in binding['pid1_stages'] if s in stage_matches]
    result['internal_kexec_load_attempts_observed'] = len(re.findall(pid + r'kexec-load-once\r?$', tail, re.M))
    result['internal_kexec_REBOOT_attempts_observed'] = len(re.findall(pid + r'kexec-reboot-once\r?$', tail, re.M))
    result['normal_recovery_fallback_observed'] = bool(re.search(pid + r'normal-recovery-request\r?$', tail, re.M))
    native = r'(?<![A-Za-z0-9_])' + re.escape('N10XNU133 id=' + identity + ' ')
    result['reservation_ready_observed'] = bool(re.search(native + r'fresh_owned32M platform_ready=1 xnu_pending=1\r?$', text[:begin[0].start()], re.M))
    result['final_hook_qualified_observed'] = bool(re.search(native + r'final_qualified=1 EL1_preserved=1 actual_XNU_pending=1\r?$', tail, re.M))
    gate_stages = {'usb-terminal', 'ufs-terminal', 'ufs-provider', 'iommu-owner', 'dma-provider', 'final'}
    gate_stages |= {'g2d-' + s for s in ('provider','record','tasks','resources','power','clock','fifo','job','clock-off','recheck','cached')}
    gate_stages |= {'score-' + s for s in ('provider','record','users','lifetime','resources','power','halt','clock-off','recheck','cached')}

    def append(key, value):
        if value not in result[key] and len(result[key]) < 8:
            result[key].append(value)

    for stage, errno, owner in re.findall(native + r'stage=([a-z0-9-]{1,32}) errno=(-?[0-9]{1,5}) owner=([^\r\n]{1,64})\r?$', aliased, re.M):
        if stage in gate_stages and -4095 <= int(errno) < 0:
            append('gate_refusals', dict(stage=stage, errno=int(errno), owner=owner))
    for controller, active, runtime, effective in re.findall(native + r'iommu controller=([^\r\n]{1,64}) active=([01]) runtime=([01]) effective=([01])\r?$', tail, re.M):
        if int(effective) == (int(active) & int(runtime)):
            append('iommu_refusal_states', dict(controller=controller, active=int(active), runtime=int(runtime), effective=int(effective)))
    for kind in ('g2d', 'score'):
        pattern = native + kind + r' reason=([a-z0-9-]{1,24}) item=([0-9]{1,3}) state=([0-9]{1,20}) value=(-?[0-9]{1,11})'
        if kind == 'score':
            pattern += r' aux=([0-9]{1,10})'
        pattern += r' owner=([^\r\n]{1,64})\r?$'
        for fields in re.findall(pattern, tail, re.M):
            reason, item, state, value = fields[:4]
            if not (0 <= int(item) <= 255 and 0 <= int(state) <= 0xffffffff and -0x80000000 <= int(value) <= 0x7fffffff):
                continue
            detail = dict(reason=reason, item=int(item), state=int(state), value=int(value), owner=fields[-1])
            if kind == 'score':
                if int(fields[4]) > 0xffffffff:
                    continue
                detail['aux'] = int(fields[4])
            append(kind + '_refusal_details', detail)
    return result
