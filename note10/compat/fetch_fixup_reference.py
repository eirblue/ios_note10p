"""Fetch the exact test reference header, preserving its original license."""
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
meta = json.loads(Path(__file__).with_name('fixup-reference.json').read_text())
target = ROOT / 'research/ios27/fixup-chains.h'
if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == meta['sha256']:
    print('Pinned reference already available')
else:
    with urllib.request.urlopen(meta['url'], timeout=30) as response:
        data = response.read(meta['size'] + 1)
    if len(data) != meta['size'] or hashlib.sha256(data).hexdigest() != meta['sha256']:
        raise ValueError('Reference integrity mismatch')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    print('Pinned reference downloaded and SHA-256 verified')
