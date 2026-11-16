"""Cross-capture CPU reference input for PC projection; never a platform ADT."""
import hashlib
import json
import struct

from boot_adt import decode, encode
from linux_cpu_adt import MAX_FDT, MAX_FRAGMENT, translate

SCHEMA = 'note10-v244-native-CPU-guarded-node-observation-v1'
POLICY = 'note10-v284-cross-capture-observed-CPU-reference-v1'
MAX_OBSERVATION = 8 * 1024 * 1024
MPIDR_HWID_MASK = 0xff00ffffff
QUALIFICATION = dict(same_boot_FDT_verified=False, observed_running_at_sample_only=True,
                     complete_boot_tree=False, handoff_ready=False, authoritative_ADT=False,
                     memory_ownership=False, hardware_ready=False, physical_ready=False,
                     xnu_executed=False)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def _integer(value, maximum=0xffffffff):
    return type(value) is int and 0 <= value <= maximum


def _observation(raw):
    row = json.loads(raw)
    require(type(row) is dict and row.get('schema') == SCHEMA, 'observation schema')
    for key in ('Linux_PID1_pre_ingest_CPU_observation_verified',
                'Linux_PID1_guarded_CPU_firmware_node_report_verified'):
        require(row.get(key) is True, 'verified scalar reports required')
    for key in ('FDT_bound', 'authoritative_ADT', 'ADT_materialized', 'bootargs_materialized', 'handoff_cpu_selected',
                'post_shutdown', 'XNU_entry_observed', 'XNU_execution_allowed',
                'hardware_authorized', 'physical_ready', 'full_native_physical_ready'):
        require(row.get(key) is False, 'reference-only observation required')
    cpu = row['cpu_observation']
    node = row['guarded_node_observation']
    receipt = row['kernel_receipt']
    require(all(type(report) is dict for report in (cpu, node, receipt)), 'report objects')
    for report in (cpu, node):
        require(report.get('phase') == 'linux-pid1-pre-ingest' and
                type(report.get('valid')) is int and report['valid'] == 1 and
                type(report.get('result')) is int and report['result'] == 0,
                'successful pre-ingest report required')
        for key in ('FDT_bound', 'handoff_cpu_selected', 'post_shutdown', 'XNU'):
            require(type(report.get(key)) is int and report[key] == 0, 'no final-state authority')
    for key, outer in (('id', 'build_evidence_id'), ('boot', 'kernel_boot_id'), ('cycle', 'cycle')):
        value = row.get(outer)
        require(type(value) is str and len(value) == 32 and
                all(c in '0123456789abcdef' for c in value) and
                cpu.get(key) == node.get(key) == receipt.get(key) == value, 'report identity join')
    require(all(type(receipt.get(key)) is int and receipt[key] == value for key, value in
                (('result', 0), ('XNU', 0), ('native_source', 1), ('destination_hash_verified', 1))),
            'successful ingestion receipt')
    index = cpu.get('cpu')
    require(_integer(index) and all(type(node.get(key)) is int and node[key] == index
            for key in ('node_cpu', 'cpu_enter', 'cpu_sample', 'cpu_before_release')),
            'guarded CPU identity')
    require(cpu.get('el') == 4 and type(cpu.get('el')) is int and
            _integer(cpu.get('cntfrq')) and cpu['cntfrq'] > 0, 'EL1 observed counter frequency')
    affinity = node.get('firmware_reg')
    require(_integer(affinity) and _integer(cpu.get('mpidr'), 0xffffffffffffffff) and
            cpu['mpidr'] & MPIDR_HWID_MASK == affinity, 'firmware affinity differs from MPIDR')
    require(type(node.get('address_cells')) is int and node['address_cells'] in (1, 2) and
            type(node.get('reg_bytes')) is int and node['reg_bytes'] == 4 * node['address_cells'],
            'firmware reg width')
    require(all(type(node.get(key)) is int and node[key] == value for key, value in
            (('pc_before', 0), ('pc_after_capture', 1), ('pc_after_query', 1), ('pc_after_release', 0))),
            'guard interval provenance')
    return index, affinity, cpu['cntfrq']


def compose(fdt_bytes, observation_bytes, *, fdt_sha256, observation_sha256):
    """Return private candidate bytes/qualification from two explicitly pinned inputs."""
    for raw, digest, lower, upper in ((fdt_bytes, fdt_sha256, 40, MAX_FDT),
                                     (observation_bytes, observation_sha256, 1, MAX_OBSERVATION)):
        require(type(raw) is bytes and lower <= len(raw) <= upper, 'bounded input bytes')
        require(type(digest) is str and len(digest) == 64 and
                all(c in '0123456789abcdef' for c in digest) and
                hashlib.sha256(raw).hexdigest() == digest, 'input source SHA256')
    index, affinity, frequency = _observation(observation_bytes)
    fragment, description = translate(fdt_bytes, include_firmware_timebase=False)
    root = decode(fragment)
    require(root.name == 'device-tree' and len(root.children) == 1 and
            root.children[0].name == 'cpus', 'CPU description shape')
    cpus = root.children[0].children
    selected = [cpu for cpu in cpus if cpu.properties.get('reg') == struct.pack('<I', affinity)]
    require(len(selected) == 1, 'unique firmware affinity description required')
    selected[0].properties.update(state=b'running\0', **{'timebase-frequency': struct.pack('<I', frequency)})
    candidate = encode(root)
    require(0 < len(candidate) <= MAX_FRAGMENT, 'candidate bound')
    metadata = dict(policy=POLICY, **QUALIFICATION, cpu_count=len(cpus),
                    selected_linux_cpu=index, selected_firmware_reg=affinity,
                    observed_cntfrq=frequency, fdt_sha256=fdt_sha256,
                    observation_sha256=observation_sha256,
                    candidate_bytes=len(candidate), candidate_sha256=hashlib.sha256(candidate).hexdigest(),
                    description_policy=description['policy'], reference=description['reference'],
                    input_relation='historical-FDT and separately sampled Linux scalar report; affinity/value join only')
    return candidate, metadata
