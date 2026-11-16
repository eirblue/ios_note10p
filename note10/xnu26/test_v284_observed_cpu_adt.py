"""One new conjunction for the observed CPU binding; invented inputs only."""
import copy
import hashlib
import json
import struct

from boot_adt import decode
from v284_observed_cpu_adt import SCHEMA, compose


def synthetic_fdt(affinities=(0x11, 0x205, 0x302)):
    strings = b'#address-cells\0#size-cells\0device_type\0reg\0state\0'
    names = {key: strings.index(key.encode() + b'\0') for key in
             ('#address-cells', '#size-cells', 'device_type', 'reg', 'state')}
    body = bytearray()
    def begin(name):
        body.extend(struct.pack('>I', 1) + name.encode() + b'\0')
        body.extend(bytes(-len(body) & 3))
    def prop(name, value):
        body.extend(struct.pack('>III', 3, len(value), names[name]) + value)
        body.extend(bytes(-len(body) & 3))
    begin(''); begin('cpus')
    prop('#address-cells', struct.pack('>I', 2)); prop('#size-cells', bytes(4))
    for affinity in affinities:
        begin('cpu@' + format(affinity, 'x'))
        prop('device_type', b'cpu\0'); prop('reg', struct.pack('>Q', affinity))
        prop('state', b'running\0')  # Firmware text never selects the sampled CPU.
        body.extend(struct.pack('>I', 2))
    body.extend(struct.pack('>III', 2, 2, 9))
    return struct.pack('>10I', 0xd00dfeed, 56 + len(body) + len(strings), 56,
                       56 + len(body), 40, 17, 16, 0, len(strings), len(body)) + bytes(16) + body + strings


def synthetic_observation():
    identity = dict(id='a' * 32, boot='b' * 32, cycle='c' * 32)
    common = dict(identity, phase='linux-pid1-pre-ingest', valid=1, result=0,
                  FDT_bound=0, handoff_cpu_selected=0, post_shutdown=0, XNU=0)
    row = dict(schema=SCHEMA, build_evidence_id=identity['id'], kernel_boot_id=identity['boot'],
               cycle=identity['cycle'], Linux_PID1_pre_ingest_CPU_observation_verified=True,
               Linux_PID1_guarded_CPU_firmware_node_report_verified=True)
    for name in ('FDT_bound', 'authoritative_ADT', 'ADT_materialized', 'bootargs_materialized', 'handoff_cpu_selected',
                 'post_shutdown', 'XNU_entry_observed', 'XNU_execution_allowed', 'hardware_authorized',
                 'physical_ready', 'full_native_physical_ready'):
        row[name] = False
    row['cpu_observation'] = dict(common, cpu=5, mpidr=0x80000205, cntfrq=19200000, el=4)
    row['guarded_node_observation'] = dict(common, node_cpu=5, cpu_enter=5, cpu_sample=5,
        cpu_before_release=5, firmware_reg=0x205, address_cells=2, reg_bytes=8,
        pc_before=0, pc_after_capture=1, pc_after_query=1, pc_after_release=0)
    row['kernel_receipt'] = dict(identity, result=0, XNU=0, native_source=1, destination_hash_verified=1)
    return row


def test_new_binding():
    raw = synthetic_fdt()
    row = synthetic_observation()
    def call(value, tree=raw, **hashes):
        observation = json.dumps(value).encode()
        return compose(tree, observation, fdt_sha256=hashes.get('fdt', hashlib.sha256(tree).hexdigest()),
                       observation_sha256=hashes.get('observation', hashlib.sha256(observation).hexdigest()))
    candidate, metadata = call(row)
    cpus = decode(candidate).children[0].children
    assert [cpu.name for cpu in cpus] == ['cpu@11', 'cpu@205', 'cpu@302']
    for cpu, affinity in zip(cpus, (0x11, 0x205, 0x302)):
        expected = dict(device_type=b'cpu\0', reg=struct.pack('<I', affinity))
        if affinity == 0x205:
            expected.update(state=b'running\0', **{'timebase-frequency': struct.pack('<I', 19200000)})
        assert cpu.properties == expected
    assert metadata['observed_running_at_sample_only'] is True
    assert all(metadata[key] is False for key in ('same_boot_FDT_verified', 'complete_boot_tree',
        'handoff_ready', 'authoritative_ADT', 'memory_ownership', 'hardware_ready', 'physical_ready', 'xnu_executed'))
    def reject(value, tree=raw, **hashes):
        try:
            call(value, tree, **hashes)
        except ValueError:
            return
        raise AssertionError('new binding accepted a mismatched input')
    reject(row, fdt='0' * 64); reject(row, observation='0' * 64)
    reject(row, synthetic_fdt((0x11, 0x206)))
    reject(row, synthetic_fdt((0x205, 0x205)))
    mutations = [('schema', None, 'unreviewed-source'), ('physical_ready', None, True),
                 ('bootargs_materialized', None, True), ('authoritative_ADT', None, True),
                 ('FDT_bound', None, True), ('handoff_cpu_selected', None, True),
                 ('cpu_observation', 'mpidr', 0x80000206), ('cpu_observation', 'cntfrq', 0),
                 ('cpu_observation', 'post_shutdown', 1), ('cpu_observation', 'XNU', 1),
                 ('cpu_observation', 'handoff_cpu_selected', 1),
                 ('cpu_observation', 'phase', 'final-cpu'), ('cpu_observation', 'id', 'd' * 32),
                 ('guarded_node_observation', 'cpu_sample', 6),
                 ('guarded_node_observation', 'reg_bytes', 4),
                 ('guarded_node_observation', 'pc_after_release', 1),
                 ('kernel_receipt', 'boot', 'e' * 32)]
    for key, subkey, value in mutations:
        changed = copy.deepcopy(row)
        if subkey is None:
            changed[key] = value
        else:
            changed[key][subkey] = value
        reject(changed)
