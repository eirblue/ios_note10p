"""One new grouped PC proof; no recovery input or old suite is invoked."""
import struct
from boot_adt import Node, encode, decode
from exynos_early_adt import PROFILE, encode_early_adt, decode_early_adt


def _rejects(call):
    try:
        call()
    except ValueError:
        return True
    return False


def run_new_group():
    # Arbitrary synthetic values, never observations or runtime defaults.
    values = dict(cpu_affinity=1, timebase_frequency=1000000,
                  dram_base=0x10000000, dram_size=0x20000000)
    raw = encode_early_adt(**values)
    positive = decode_early_adt(raw) == values
    tree = decode(raw)
    positive = positive and tree.children[0].children[0].properties['reg'] == struct.pack('<I', 1)
    positive = positive and tree.children[1].properties['dram-size'] == struct.pack('<Q', values['dram_size'])
    width_tree = decode(raw)
    width_tree.children[0].children[0].properties['timebase-frequency'] = struct.pack('<Q', 1000000)
    missing_tree = decode(raw)
    missing_tree.children.pop()
    count_tree = decode(raw)
    count_tree.children[0].children.append(Node('cpu@2', dict(tree.children[0].children[0].properties, reg=struct.pack('<I', 2))))
    rejected = {
        'reg-loss': _rejects(lambda: encode_early_adt(**dict(values, cpu_affinity=1 << 32))),
        'timebase-width': _rejects(lambda: decode_early_adt(encode(width_tree))),
        'chosen-missing': _rejects(lambda: decode_early_adt(encode(missing_tree))),
        'CPU-count': _rejects(lambda: decode_early_adt(encode(count_tree)))}
    assert positive and all(rejected.values()), 'new early-consumer shape conjunction'
    return raw, dict(profile=PROFILE, groups=1, variants=1, assertions=1, positive_roundtrip=True,
                     negative_cases=4, rejected=rejected, synthetic_inputs=values,
                     complete_platform_ADT=False, live_handoff_qualified=False,
                     rootfs_compatibility_verified=False, hardware_ready=False)
