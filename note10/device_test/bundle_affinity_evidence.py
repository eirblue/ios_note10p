"""Bundle only the two new v78 output roots before private artifact sealing."""
import argparse
import json
import os
from pathlib import Path
import re
import uuid
import zipfile

BASE = Path(__file__).resolve().parents[1] / 'private'
MAX_EXPANDED = 512 * 1024 * 1024
MAX_ZIP = 256 * 1024 * 1024


def private(path):
    path = Path(path).absolute()
    if path.resolve() != path or not path.is_relative_to(BASE) or path == BASE:
        raise ValueError('ordinary private v78 path required')
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tests', required=True)
    parser.add_argument('--build', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--source', required=True)
    args = parser.parse_args()
    if not re.fullmatch('[0-9a-f]{40}', args.source):
        raise ValueError('exact producing source required')
    BASE.mkdir(parents=True, exist_ok=True)
    tests, build, output = (private(value) for value in (args.tests,args.build,args.output))
    if output.exists() or output.parent.resolve() != output.parent or not output.parent.is_dir():
        raise ValueError('fresh private ZIP output required')
    roots = (('new-tests',tests),('image-producer',build))
    if tests == build or tests.is_relative_to(build) or build.is_relative_to(tests) or any(output.is_relative_to(p) for _,p in roots):
        raise ValueError('disjoint bounded v78 output roots required')
    selected, expanded = [], 0
    for label, directory in roots:
        if not directory.exists():
            continue
        if not directory.is_dir():
            raise ValueError('v78 output root must be a directory')
        for path in sorted(directory.rglob('*')):
            if path.is_symlink():
                raise ValueError('symlink in v78 evidence')
            if not path.is_file():
                continue
            size = path.stat().st_size
            expanded += size
            if size > MAX_ZIP or expanded > MAX_EXPANDED or len(selected) >= 4096:
                raise ValueError('v78 evidence ZIP input budget')
            selected.append((path,label+'/'+path.relative_to(directory).as_posix()))
    temporary = output.with_name('.v78-bundle-'+uuid.uuid4().hex)
    try:
        with zipfile.ZipFile(temporary,'x',zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=False) as archive:
            archive.writestr('transport.json',json.dumps({'source_commit':args.source,'selected_files':len(selected),
                'expanded_bytes':expanded,'scope':'new-tests and image-producer only; may contain failed partial outputs'}))
            for path,name in selected:
                archive.write(path,name)
        if temporary.stat().st_size > MAX_ZIP:
            raise ValueError('v78 evidence ZIP compressed budget')
        os.link(temporary,output)
    finally:
        if temporary.exists():
            temporary.unlink()


if __name__ == '__main__':
    main()
