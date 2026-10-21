"""Read-only KDK XAR/PBZX/CPIO header extraction; never run the installer.

PBZX framing follows the documented implementation in blacktop/ipsw/pkg/ota/pbzx.
Only regular .h and Info.plist entries are written under the ignored tool cache.
"""
import hashlib
import io
import json
import lzma
from pathlib import Path, PurePosixPath
import stat
import struct
import xml.etree.ElementTree as ET
import zlib

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'host-tools/kdk'


def hash_file(path, algorithm='sha256'):
    digest = hashlib.new(algorithm)
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def xar_payloads(package, selected=('KDK.pkg/Payload', 'KDK_SDK.pkg/Payload')):
    with package.open('rb') as stream:
        magic, header_size, version, compressed, unpacked, algorithm = struct.unpack('>4sHHQQI', stream.read(28))
        if magic != b'xar!' or version != 1 or header_size < 28 or unpacked > 16 * 1024**2:
            raise ValueError('Unexpected XAR header')
        stream.seek(header_size)
        toc_raw = zlib.decompress(stream.read(compressed))
        if len(toc_raw) != unpacked:
            raise ValueError('XAR TOC size mismatch')
        toc = ET.fromstring(toc_raw).find('toc')
        heap = header_size + compressed
        members = []
        def walk(element, parent=''):
            for member in element.findall('file'):
                name = parent + member.findtext('name')
                if name in selected:
                    members.append((name, member.find('data')))
                walk(member, name + '/')
        walk(toc)
        outputs = []
        for name, data in members:
            offset, size = int(data.findtext('offset')), int(data.findtext('length'))
            checksum = data.find('archived-checksum')
            if checksum.attrib['style'] != 'sha1' or data.find('encoding').attrib['style'] != 'application/octet-stream':
                raise ValueError('Unsupported XAR payload encoding/checksum')
            path = BASE / 'xar-payloads' / name
            if not path.resolve().is_relative_to((BASE / 'xar-payloads').resolve()):
                raise ValueError('XAR payload path escaped cache')
            path.parent.mkdir(parents=True, exist_ok=True)
            if not (path.exists() and path.stat().st_size == size and hash_file(path, 'sha1') == checksum.text):
                stream.seek(heap + offset)
                remaining = size
                with path.open('wb') as output:
                    while remaining:
                        block = stream.read(min(8 * 1024**2, remaining))
                        if not block:raise ValueError('Truncated XAR payload')
                        output.write(block); remaining -= len(block)
            if hash_file(path, 'sha1') != checksum.text:
                raise ValueError('XAR archived checksum mismatch')
            outputs.append(path)
        return outputs


def chunks(path):
    with path.open('rb') as stream:
        if stream.read(4) != b'pbzx':raise ValueError('Missing PBZX magic')
        block_size = struct.unpack('>Q', stream.read(8))[0]
        if block_size > 64 * 1024**2:raise ValueError('Unexpected PBZX block size')
        while True:
            header = stream.read(16)
            if not header:break
            if len(header) != 16:raise ValueError('Truncated PBZX header')
            inflated, deflated = struct.unpack('>QQ', header)
            if not 0 < deflated <= inflated <= block_size:raise ValueError('Invalid PBZX sizes')
            raw = stream.read(deflated)
            if len(raw) != deflated:raise ValueError('Truncated PBZX block')
            data = lzma.decompress(raw) if deflated < inflated else raw
            if len(data) != inflated:raise ValueError('PBZX block size mismatch')
            yield data


class Stream:
    def __init__(self, parts):self.parts = iter(parts); self.buffer = b''
    def read(self, size):
        out = bytearray()
        while size:
            if not self.buffer:
                self.buffer = next(self.parts, b'')
                if not self.buffer:raise ValueError('Truncated CPIO stream')
            take = min(size, len(self.buffer))
            out.extend(self.buffer[:take]); self.buffer = self.buffer[take:]; size -= take
        return bytes(out)
    def skip(self, size):
        while size:
            take = min(size, 1024 * 1024); self.read(take); size -= take


def extract(path):
    stream = Stream(chunks(path))
    destination = BASE / 'headers' / path.parent.name
    headers = {}; members = 0; total = 0
    while True:
        header = stream.read(76)
        if header[:6] != b'070707':raise ValueError('Unsupported CPIO format (expected odc)')
        mode, name_size, file_size = int(header[18:24], 8), int(header[59:65], 8), int(header[65:76], 8)
        if not 0 < name_size <= 4096:raise ValueError('Invalid CPIO name length')
        raw_name = stream.read(name_size)
        if raw_name[-1:] != b'\0':raise ValueError('Unterminated CPIO name')
        name = raw_name[:-1].decode('utf-8')
        if name == 'TRAILER!!!':break
        members += 1
        relative = PurePosixPath(name[2:] if name.startswith('./') else name)
        output = destination.joinpath(*relative.parts)
        if relative.is_absolute() or '..' in relative.parts or ':' in name or '\\' in name or not output.resolve().is_relative_to(destination.resolve()):
            raise ValueError('Unsafe CPIO path')
        wanted = stat.S_ISREG(mode) and (name.endswith('.h') or relative.name == 'Info.plist')
        if not wanted:
            stream.skip(file_size); continue
        total += file_size
        if file_size > 16 * 1024**2 or total > 512 * 1024**2:raise ValueError('Unexpected KDK header size')
        raw = stream.read(file_size)
        output.parent.mkdir(parents=True, exist_ok=True); output.write_bytes(raw)
        headers[relative.as_posix()] = hashlib.sha256(raw).hexdigest()
    print(path.parent.name + ': ' + str(len(headers)) + ' header/plist files', flush=True)
    return {'payload_sha256': hash_file(path), 'members_scanned': members, 'files': headers,
            'output_directory': destination.relative_to(ROOT).as_posix(), 'bytes_written': total}


def main():
    package = BASE / 'unpacked/Kernel Debug Kit/KernelDebugKit.pkg'
    results = []
    for path in xar_payloads(package):
        print('Streaming ' + path.parent.name, flush=True)
        results.append(extract(path))
    report = {'package_sha256': hash_file(package), 'payloads': results,
              'installer_executed': False, 'macos_kdk_headers_not_exynos_drivers': True}
    (BASE / 'headers-report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({'payloads': len(results), 'files': sum(len(r['files']) for r in results), 'installer_executed': False}))


if __name__ == '__main__':
    main()
