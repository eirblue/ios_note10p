"""Extract selected active-target files using local IPSW, AEA and APFS readers."""
import hashlib
import json
from pathlib import Path
import plistlib
import subprocess
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
FILES = ('sbin/launchd', 'usr/lib/dyld',
         'System/Library/CoreServices/SpringBoard.app/SpringBoard',
         'System/Library/CoreServices/SystemVersion.plist')

def main():
    target = json.loads((ROOT / 'note10/target.json').read_text())
    out = ROOT / target['research_directory']
    manifest = plistlib.loads((out / 'BuildManifest.plist').read_bytes())
    if (manifest['ProductVersion'], manifest['ProductBuildVersion']) != (target['version'], target['build']):
        raise ValueError('Manifest does not match active target')
    identity = next(b for b in manifest['BuildIdentities']
                    if b['Info'].get('Variant') == 'Customer Erase Install (IPSW)')
    entry = identity['Manifest']['OS']
    name = entry['Info']['Path']
    if Path(name).name != name or not name.endswith('.dmg.aea'):
        raise ValueError('This workflow expects a root AEA-wrapped OS image')
    aea = out / name
    with zipfile.ZipFile(ROOT / target['ipsw']) as z:
        info = z.getinfo(name)
        valid = False
        if aea.is_file() and aea.stat().st_size == info.file_size:
            crc = 0
            with aea.open('rb') as f:
                while chunk := f.read(16 * 1024 * 1024): crc = zlib.crc32(chunk, crc)
            valid = crc == info.CRC
        if not valid:
            with z.open(name) as src, aea.open('wb') as dst:
                while chunk := src.read(16 * 1024 * 1024): dst.write(chunk)
            # zipfile checks the CRC when reading through EOF.
    image = out / name.removesuffix('.aea')
    def image_digest():
        if not image.is_file(): return None
        with image.open('rb') as f: return hashlib.file_digest(f, 'sha384').digest()
    if image_digest() != entry['Digest']:
        subprocess.run([str(ROOT / 'host-tools/ipsw/ipsw.exe'), 'fw', 'aea', str(aea), '-o', str(out)], check=True)
    digest = image_digest()
    if digest != entry['Digest']: raise ValueError('Decrypted OS SHA384 mismatch')
    subprocess.run([str(ROOT / 'host-tools/7zip/portable/7z.exe'), 'x', str(image),
                    '-o' + str(out / 'userland'), '-y', *FILES], check=True)
    version = plistlib.loads((out / 'userland' / FILES[-1]).read_bytes())
    if (version['ProductVersion'], version['ProductBuildVersion']) != (target['version'], target['build']):
        raise ValueError('Extracted system version mismatch')
    report = {'target':target,'aea':name,'aea_zip_crc_checked':True,
              'decrypted_image_size':image.stat().st_size,'decrypted_image_sha384':digest.hex(),
              'manifest_digest_matches_decrypted_image':True,'files':[]}
    for name in FILES:
        p = out / 'userland' / name
        report['files'].append({'file':p.relative_to(ROOT).as_posix(), 'size':p.stat().st_size,
                                'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    (out / 'userland-extraction.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({'version':version['ProductVersion'],'build':version['ProductBuildVersion'],'files':len(FILES)}))

if __name__ == '__main__': main()
