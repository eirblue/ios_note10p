#!/bin/bash
# Stage Apple's open source HFS for the Note10 built-in filesystem (bsd/n10_hfs).
# Run once from the XNU source root, before or after 0021-exynos9825-builtin-hfs.patch.
set -euo pipefail

[[ -f bsd/kern/bsd_init.c && -f config/MASTER.arm64.exynos9825 ]] || {
    echo 'run from the patched Note10 XNU source root' >&2
    exit 1
}

# hfs-627.100.6, the same immutable commit as xnu/patches/0026-stage-hfs.sh.
# Fetch the commit, never a moving branch/tag.
hfs_sha=31d5ec238dfab485e78a9a30b8b92d13e8914f03
hfs_tmp=$(mktemp -d)
trap 'rm -rf "$hfs_tmp"' EXIT
git init -q "$hfs_tmp"
git -C "$hfs_tmp" fetch -q --depth 1 \
    https://github.com/apple-oss-distributions/hfs "$hfs_sha"
git -C "$hfs_tmp" checkout -q FETCH_HEAD
[[ "$(git -C "$hfs_tmp" rev-parse HEAD)" == "$hfs_sha" ]]

python3 - "$hfs_tmp" <<'PY'
from pathlib import Path
import shutil
import sys

source = Path(sys.argv[1])
target = Path('bsd/n10_hfs')
for directory in ('core', 'hfs_encodings'):
    if (target / directory).exists():
        raise SystemExit(f'refusing to overwrite existing HFS sources: {target / directory}')
# Preserve upstream copyright/license headers; no downloaded sources in git.
for directory in ('core', 'hfs_encodings'):
    shutil.copytree(source / directory, target / directory)

# Note10 has no AppleKeyStore (content protection is not built, see
# n10_hfs_compat.h); its header is only needed for the key-wrapping API.
path = target / 'core' / 'hfs_iokit.h'
text = path.read_text()
include = '#include <AppleKeyStore/AppleKeyStoreFSServices.h>\n'
first = 'int hfs_unwrap_key('
end = '__END_DECLS'
if text.count(include) != 1 or text.count(first) != 1 or text.count(end) != 1:
    raise SystemExit(f'HFS source changed: {path}')
text = text.replace(include, '#if CONFIG_PROTECT\n' + include + '#endif\n')
i, j = text.index(first), text.index(end)
text = text[:i] + '#if CONFIG_PROTECT\n' + text[i:j].rstrip('\n') + '\n#endif\n\n' + text[j:]
path.write_text(text)
PY

# Kernel builds use -nostdinc; HFS's kext-config.h needs the SDK's target macros.
hfs_sdk=$(xcrun --sdk iphoneos --show-sdk-path)
cp "$hfs_sdk/usr/include/TargetConditionals.h" bsd/n10_hfs/
echo "Staged hfs-627.100.6 ($hfs_sha) for Note10"
