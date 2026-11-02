"""Private fixed-extent DATA preparation with one intrinsic bounded C decode.

No kernel reader, compression, BOOT packaging or device operation.
"""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import re
import struct

ROOT = Path(__file__).resolve().parents[2]
PRIVATE_ROOT = ROOT / 'note10/private'
MAX_BYTES = 64 * 1024 * 1024
WORKSPACE = 15980
HEADER = struct.Struct('<8sHHI4Q32s32s16s')
MAGIC = b'N10DATA1'
SOURCE_FILES = ('note10/device_test/carrier_lzma.h', 'note10/device_test/carrier_lzma.c',
                'note10/xnu26/current_data_carrier.py', 'note10/xnu26/test_current_data_carrier.py')
CASE_NAMES = (
    'test_finite_header_eos_and_container_data_identity',
    'test_truncation_and_early_eos_fail_with_bounded_counts',
    'test_properties_dictionary_header_and_output_caps',
    'test_workspace_and_host_allocation_failures',
    'test_fixed_carrier_length_padding_and_slice_bounds',
    'test_provenance_pins_and_fresh_output_preserve_inputs',
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def private(path):
    path = Path(path).absolute()
    require(path.resolve() == path and path.is_relative_to(PRIVATE_ROOT.resolve()) and
            path != PRIVATE_ROOT.resolve() and not any(p.is_symlink() for p in (path, *path.parents)),
            'ordinary private path required')
    return path


def read(path, cap):
    path = private(path)
    require(path.is_file() and 0 < path.stat().st_size <= cap, 'bounded private input required')
    with path.open('rb') as stream:
        raw = stream.read(cap + 1)
    require(0 < len(raw) <= cap, 'input exceeds cap')
    return raw


def json_pin(path, expected):
    require(type(expected) is str and re.fullmatch('[0-9a-f]{64}', expected), 'accepted SHA pin required')
    raw = read(path, 2 * 1024 * 1024)
    require(sha(raw) == expected, 'accepted metadata pin differs')
    value = json.loads(raw)
    require(type(value) is dict, 'metadata object required')
    return value


def source_pins():
    return {name: sha((ROOT/name).read_bytes()) for name in SOURCE_FILES}


class Result(ctypes.Structure):
    _fields_ = [('version', ctypes.c_uint32), ('status', ctypes.c_int32),
                ('consumed', ctypes.c_uint64), ('written', ctypes.c_uint64)]


def allocate_buffer(size):
    return ctypes.create_string_buffer(max(1, size))


class Decoder:
    def __init__(self, path, expected_sha):
        self.path = private(path)
        require(self.path.suffix.lower() == '.dll', 'selected host DLL required')
        raw = read(self.path, 8 * 1024 * 1024)
        require(sha(raw) == expected_sha, 'compiled decoder pin differs')
        self.sha256 = expected_sha
        self.library = ctypes.CDLL(str(self.path))
        self.function = self.library.n10_lzma_alone_decode
        self.function.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t,
                                  ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(Result)]
        self.function.restype = ctypes.c_int
        self.calls = 0

    def invoke(self, stream, capacity, workspace_bytes=WORKSPACE, workspace_offset=0, null_workspace=False):
        require(type(capacity) is int and 0 <= capacity <= MAX_BYTES and
                type(workspace_bytes) is int and 0 <= workspace_bytes <= WORKSPACE,
                'bounded host buffers required')
        require(workspace_offset in (0, 1), 'bounded workspace offset required')
        source = allocate_buffer(len(stream))
        output = allocate_buffer(capacity)
        workspace = allocate_buffer(WORKSPACE + 2)
        ctypes.memmove(source, stream, len(stream))
        result = Result()
        self.calls += 1
        status = self.function(source, len(stream), output, capacity,
            None if null_workspace else ctypes.c_void_p(ctypes.addressof(workspace)+workspace_offset),
            workspace_bytes, ctypes.byref(result))
        facts = dict(status=status, version=result.version, reported_status=result.status,
                     consumed=result.consumed, written=result.written)
        data = output.raw[:result.written] if status == 0 and result.written <= capacity else b''
        ctypes.memset(output, 0, max(1, capacity))
        return facts, data

    def decode(self, stream, expected_bytes):
        try:
            facts, decoded = self.invoke(stream, expected_bytes)
        except MemoryError as error:
            raise ValueError('host decode allocation failed') from error
        require(facts['status'] == facts['reported_status'] == 0 and facts['version'] == 1 and
                facts['written'] == expected_bytes and facts['consumed'] <= len(stream),
                'bounded C decode failed: '+json.dumps(facts, sort_keys=True))
        return facts, decoded


def reviewed_decoder(receipt_path, receipt_sha256):
    path = private(receipt_path)
    receipt = json_pin(path, receipt_sha256)
    require(receipt.get('kind') == 'current-data-carrier-new-tests' and receipt.get('success') is True and
            receipt.get('selected') == list(CASE_NAMES) and receipt.get('passed') == list(CASE_NAMES) and
            receipt.get('failed') == [] and receipt.get('tests_run') == len(CASE_NAMES),
            'complete new same-source PASS batch required')
    require(receipt.get('source_sha256') == source_pins() and receipt.get('fixture_compiles') == 1,
            'same compiled source closure required')
    compiled = receipt['compiled']
    require(compiled.get('returncode') == 0 and compiled.get('dll_file') == 'carrier_lzma.dll',
            'one successful selected compilation required')
    return Decoder(path.parent/compiled['dll_file'], compiled['dll_sha256']), compiled


def finite_stream(original, payload_bytes):
    require(type(payload_bytes) is int and 0 < payload_bytes <= MAX_BYTES, 'bounded payload length required')
    require(18 <= len(original) <= MAX_BYTES and original[0] == 0x5d and
            int.from_bytes(original[1:5], 'little') == 1 << 23 and original[5:13] == b'\xff'*8,
            'selected unknown-size preset6 ALONE header required')
    return original[:5] + payload_bytes.to_bytes(8, 'little') + original[13:]


def container(stream, payload_bytes, payload_sha256, budget):
    require(type(budget) is int and 128 < budget <= MAX_BYTES and 18 <= len(stream) <= budget-128,
            'fixed carrier capacity exceeded')
    require(type(payload_sha256) is str and re.fullmatch('[0-9a-f]{64}', payload_sha256),
            'accepted decoded identity required')
    header = HEADER.pack(MAGIC, 1, 128, 0, budget, 128, len(stream), payload_bytes,
                         bytes.fromhex(sha(stream)), bytes.fromhex(payload_sha256), bytes(16))
    return header + stream + bytes(budget-128-len(stream))


def carrier_slice(raw, budget):
    require(type(budget) is int and 128 < budget <= MAX_BYTES and len(raw) == budget,
            'exact fixed carrier extent required')
    magic, version, header, flags, total, offset, count, size, stream_sha, payload_sha, reserved = HEADER.unpack_from(raw)
    require((magic, version, header, flags, total, offset, reserved) ==
            (MAGIC, 1, 128, 0, budget, 128, bytes(16)) and
            18 <= count <= budget-128 and 0 < size <= MAX_BYTES, 'closed carrier header required')
    stream = raw[offset:offset+count]
    require(not any(raw[offset+count:]) and sha(stream) == stream_sha.hex(), 'carrier stream or padding differs')
    require(stream[0] == 0x5d and int.from_bytes(stream[1:5], 'little') == 1 << 23 and
            int.from_bytes(stream[5:13], 'little') == size, 'finite stream/header mismatch')
    return stream, size, payload_sha.hex()


def produce(payload_manifest, *, payload_manifest_sha256, budget, output, decoder, compile_binding=None):
    output = private(output)
    require(not output.exists(), 'fresh output required')
    manifest_path = private(payload_manifest)
    require(manifest_path.name == 'payload-fit.json' and not manifest_path.is_relative_to(output),
            'fixed accepted manifest path required')
    manifest = json_pin(manifest_path, payload_manifest_sha256)
    require(manifest.get('schema') == 1 and manifest.get('purpose') == 'current-source-payload-preparation' and
            manifest.get('fits_budget') is True and manifest.get('carrier_admitted') is False and
            manifest.get('deployment_ready') is False and manifest.get('device_operations') == [] and
            manifest.get('xnu_executed') is False, 'accepted host-only payload required')
    require(manifest.get('compressed_file') == 'kernel.mem.lzma' and manifest.get('payload_file') == 'kernel.mem' and
            manifest.get('compression') == dict(format='LZMA_ALONE', preset=6, streams=1, padding_bytes=0) and
            type(budget) is int and budget == manifest.get('carrier_budget_bytes'), 'accepted carrier input shape differs')
    require(type(manifest.get('ci_context')) is dict and
            all(type(manifest.get(k)) is str and re.fullmatch('[0-9a-f]{64}', manifest[k])
                for k in ('producer_result_sha256', 'producer_context_sha256', 'producer_id', 'input_binding')),
            'accepted producer context required')
    original = read(manifest_path.parent/'kernel.mem.lzma', MAX_BYTES)
    require(len(original) == manifest['compressed_bytes'] and sha(original) == manifest['compressed_sha256'],
            'accepted compressed input differs')
    stream = finite_stream(original, manifest['payload_bytes'])
    raw = container(stream, manifest['payload_bytes'], manifest['payload_sha256'], budget)
    selected, expected_size, expected_sha = carrier_slice(raw, budget)
    output.mkdir(parents=True, exist_ok=False)
    before = decoder.calls
    try:
        facts, decoded = decoder.decode(selected, expected_size)
        require(decoder.calls == before+1 and sha(decoded) == expected_sha, 'functional decoded identity differs')
    except (ValueError, MemoryError) as error:
        with (output/'failure.json').open('x') as target:
            target.write(json.dumps(dict(accepted=False, decoder_calls=decoder.calls-before,
                                        error=str(error), carrier_admitted=False), indent=2)+'\n')
        raise
    report = dict(schema=1, purpose='fixed-data-carrier-host-preparation', accepted=True,
        payload_manifest_sha256=payload_manifest_sha256, input_ci_context=manifest['ci_context'],
        producer_id=manifest['producer_id'], input_binding=manifest['input_binding'],
        original_stream_sha256=manifest['compressed_sha256'], transport_stream_sha256=sha(stream),
        stream_transformation='ONLY ALONE header bytes5..12 replaced by accepted finite LE64 length',
        header_bytes=128, stream_offset=128, stream_bytes=len(stream), carrier_bytes=len(raw),
        padding_bytes=len(raw)-128-len(stream), carrier_sha256=sha(raw), payload_bytes=expected_size,
        payload_sha256=expected_sha, decoded_sha256=sha(decoded), decoded_bytes=len(decoded),
        decoder_calls=decoder.calls-before, decode=facts, decoder_dll_sha256=decoder.sha256,
        compile_binding=compile_binding, source_sha256=source_pins(),
        carrier_admitted=False, physical_reservation_verified=False, deployment_ready=False,
        device_operations=[], xnu_executed=False)
    for name, data in (('carrier.data', raw), ('carrier-manifest.json', (json.dumps(report, indent=2)+'\n').encode())):
        with (output/name).open('xb') as target:
            target.write(data)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--payload-manifest', type=Path, required=True)
    parser.add_argument('--payload-manifest-sha256', required=True)
    parser.add_argument('--decoder-test-result', type=Path, required=True)
    parser.add_argument('--decoder-test-result-sha256', required=True)
    parser.add_argument('--budget', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = vars(parser.parse_args())
    decoder, compiled = reviewed_decoder(args.pop('decoder_test_result'), args.pop('decoder_test_result_sha256'))
    report = produce(**args, decoder=decoder, compile_binding=compiled)
    print(json.dumps({k: report[k] for k in ('carrier_bytes', 'stream_bytes', 'payload_bytes',
                                            'decoder_calls', 'carrier_admitted', 'deployment_ready')}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
