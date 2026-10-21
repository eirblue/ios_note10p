"""Fetch portable upstream host tools into the ignored workspace, without installation."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import stat
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OBSERVED_HASHES = {'win_flex_bison-2.5.25.zip': '8d324b62be33604b2c45ad1dd34ab93d722534448f55a16ca7292de32b6ac135'}
TOOLS = (
    ('llvm-mingw-20261006-ucrt-x86_64.zip',
     'https://github.com/mstorsjo/llvm-mingw/releases/download/20261006/llvm-mingw-20261006-ucrt-x86_64.zip',
     '317492c456aa27ee607a5919f1d2d38dcdc1112516a24d0bf4b00d078f52d17a', 'llvm-mingw'),
    ('win_flex_bison-2.5.25.zip',
     'https://github.com/lexxmark/winflexbison/releases/download/v2.5.25/win_flex_bison-2.5.25.zip',
     None, 'winflexbison-2.5.25'),
)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    directory = ROOT / 'host-tools/windows-build'
    directory.mkdir(parents=True, exist_ok=True)
    reports = []
    for name, url, expected, subdir in TOOLS:
        archive = directory / name
        if not archive.exists():
            print('Downloading ' + name, flush=True)
            temporary = archive.with_suffix('.zip.part')
            request = urllib.request.Request(url, headers={'User-Agent': 'note10-port-research'})
            with urllib.request.urlopen(request, timeout=60) as response, temporary.open('wb') as output:
                shutil.copyfileobj(response, output, 1024 * 1024)
            if expected and sha(temporary) != expected:
                raise ValueError('Upstream archive hash mismatch: ' + name)
            temporary.replace(archive)
        actual = sha(archive)
        if name in OBSERVED_HASHES and actual != OBSERVED_HASHES[name]:
            raise ValueError('Previously observed tool archive hash changed: ' + name)
        if expected and actual != expected:
            raise ValueError('Cached upstream archive hash mismatch: ' + name)
        destination = directory / subdir
        with zipfile.ZipFile(archive) as package:
            size = sum(m.file_size for m in package.infolist())
            if size > 3 * 1024**3 or shutil.disk_usage(directory).free < size + 512 * 1024**2:
                raise ValueError('Insufficient disk space or unexpectedly large tool archive')
            for member in package.infolist():
                relative = PurePosixPath(member.filename)
                path = destination.joinpath(*relative.parts)
                if (relative.is_absolute() or '..' in relative.parts or ':' in member.filename
                        or '\\' in member.filename or not path.resolve().is_relative_to(destination.resolve())
                        or stat.S_ISLNK(member.external_attr >> 16)):
                    raise ValueError('Unsafe tool archive member')
            print('Extracting ' + name, flush=True)
            package.extractall(destination)
        reports.append({'url': url, 'archive': archive.relative_to(ROOT).as_posix(),
                        'sha256': actual, 'upstream_digest_available': expected is not None,
                        'directory': destination.relative_to(ROOT).as_posix(), 'uncompressed_bytes': size})
    (directory / 'provenance.json').write_text(json.dumps(reports, indent=2))
    print(json.dumps(reports, indent=2))


if __name__ == '__main__':
    main()
