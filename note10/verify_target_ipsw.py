"""Verify active local IPSW identity, hashes and kernel version without mounting or flashing."""
import hashlib
import json
from pathlib import Path
import plistlib
import re
import struct
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]

def main():
    target = json.loads((ROOT / 'note10/target.json').read_text())
    path = ROOT / target['ipsw']
    with path.open('rb') as f: digest = hashlib.file_digest(f, 'sha256').hexdigest()
    if digest != target['sha256']: raise ValueError('IPSW SHA256 mismatch')
    out = ROOT / target['research_directory']
    out.mkdir(parents=True, exist_ok=True)
    components = []
    with zipfile.ZipFile(path) as z:
        manifest_raw = z.read('BuildManifest.plist')
        manifest = plistlib.loads(manifest_raw)
        if (manifest['ProductVersion'] != target['version'] or
            manifest['ProductBuildVersion'] != target['build'] or
            manifest['SupportedProductTypes'] != [target['product_type']]):
            raise ValueError('Unexpected manifest identity')
        identities = [b for b in manifest['BuildIdentities']
                      if b['Info'].get('Variant') == 'Customer Erase Install (IPSW)']
        if len(identities) != 1: raise ValueError('Ambiguous erase identity')
        identity = identities[0]
        for key in ('KernelCache', 'DeviceTree'):
            entry = identity['Manifest'][key]
            name = entry['Info']['Path']
            raw = z.read(name)  # zipfile checks the component CRC.
            if hashlib.sha384(raw).digest() != entry['Digest']:
                raise ValueError(key + ' manifest digest mismatch')
            destination = out / Path(name).name
            destination.write_bytes(raw)
            components.append({'component': key, 'path': name, 'size': len(raw),
                'sha384': hashlib.sha384(raw).hexdigest(), 'manifest_digest_matched': True})
        (out / 'BuildManifest.plist').write_bytes(manifest_raw)
        (out / 'Restore.plist').write_bytes(z.read('Restore.plist'))
    kernel_input = out / Path(components[0]['path']).name
    kernel_dir = out / 'kernelcache.decompressed'
    subprocess.run([str(ROOT / 'host-tools/ipsw/ipsw.exe'), 'kernel', 'dec',
                    str(kernel_input), '-o', str(kernel_dir)], check=True)
    kernel_path = kernel_dir / (kernel_input.name + '.decompressed')
    kernel = kernel_path.read_bytes()
    versions = sorted(set(v.decode() for v in re.findall(rb'Darwin Kernel Version [^\0\r\n]+', kernel)))
    if len(versions) != 1 or ('xnu-' + target['kernel_version'] + '~') not in versions[0]:
        raise ValueError('Unexpected decompressed kernel version')
    result = {'ipsw': path.name, 'size': path.stat().st_size, 'sha256': digest,
        'product_type': target['product_type'], 'version': target['version'], 'build': target['build'],
        'device_class': identity['Info']['DeviceClass'], 'chip_id': identity['ApChipID'],
        'board_id': identity['ApBoardID'], 'components': components, 'kernel_version': versions[0],
        'kernel_sha256': hashlib.sha256(kernel).hexdigest(),
        'kernel_outer_cpu_subtype': hex(struct.unpack_from('<I', kernel, 8)[0]),
        'scope': 'Local hash/CRC/manifest digest checks; not Apple signature authentication or boot verification'}
    (out / 'local-ipsw-verification.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))

if __name__ == '__main__': main()
