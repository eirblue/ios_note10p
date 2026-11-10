"""v161 diagnostic-only skip_initramfs parser override and focused PC fixture source."""
import argparse
import hashlib
import json
from pathlib import Path

INPUT_SHA = '2f3de0ab1eff52c24ed050facfb21c2e994b22ff51f99d82046f16551cb0089b'
PARSER = b'''static int __init skip_initramfs_param(char *str)
{
\tif (*str)
\t\treturn 0;
\tdo_skip_initramfs = 1;
\treturn 1;
}
__setup("skip_initramfs", skip_initramfs_param);'''
ASSIGNMENT = b'''#if defined(CONFIG_NOTE10_V154_LINUX_DIAGNOSTIC) && defined(CONFIG_NOTE10_BUILTIN_INIT_ROUTE) && defined(CONFIG_INITRAMFS_FORCE)
\tdo_skip_initramfs = 0;
#else
\tdo_skip_initramfs = 1;
#endif'''
OPTIONS = ('CONFIG_NOTE10_V154_LINUX_DIAGNOSTIC', 'CONFIG_NOTE10_BUILTIN_INIT_ROUTE', 'CONFIG_INITRAMFS_FORCE')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def prepare(observed_rootfs):
    require(type(observed_rootfs) is bytes and hashlib.sha256(observed_rootfs).hexdigest() == INPUT_SHA and
            observed_rootfs.count(PARSER) == 1, 'exact accepted observed rootfs/parser required')
    return observed_rootfs.replace(PARSER, PARSER.replace(b'\tdo_skip_initramfs = 1;', ASSIGNMENT, 1), 1)


def fixture_source(observed_rootfs):
    modified = prepare(observed_rootfs)
    parser = PARSER.replace(b'\tdo_skip_initramfs = 1;', ASSIGNMENT, 1)
    require(modified.count(parser) == 1 and modified.replace(parser, PARSER, 1) == observed_rootfs,
            'only the exact parser assignment may change')
    # Compile the actual transformed parser in all eight boolean configurations.
    actual = modified[modified.index(parser):modified.index(parser)+len(parser)].decode('ascii')
    body = ['#include <stdio.h>\n#define __init\n#define __initdata\n#define __setup(name, fn)\n']
    tests = []
    for combination in range(8):
        for bit, option in enumerate(OPTIONS):
            body.append('#undef '+option+'\n')
            if combination & (1 << bit):
                body.append('#define '+option+' 1\n')
        body.append('#undef do_skip_initramfs\n#undef skip_initramfs_param\n')
        body.append(f'#define do_skip_initramfs n161_skip_{combination}\n')
        body.append(f'#define skip_initramfs_param n161_parse_{combination}\n')
        body.append('static int __initdata do_skip_initramfs;\n'+actual+'\n')
        expected = 0 if combination == 7 else 1
        tests.extend([f'n161_skip_{combination}=9; CHECK(n161_parse_{combination}(value)==0 && n161_skip_{combination}==9);',
                      f'n161_skip_{combination}=0; CHECK(n161_parse_{combination}(bare)==1 && n161_skip_{combination}=={expected});',
                      f'n161_skip_{combination}=1; CHECK(n161_parse_{combination}(bare)==1 && n161_skip_{combination}=={expected});'])
    body.append('#define CHECK(v) do { if (!(v)) return __LINE__; } while (0)\n')
    body.append('int main(void) { char bare[]="", value[]="=1";\n'+'\n'.join(tests)+'\n')
    body.append('CHECK(bare[0]==0 && value[0]==\'=\' && value[1]==\'1\' && value[2]==0);\n')
    body.append('puts("v161 diagnostic parser scope: PASS"); return 0; }\n')
    return ''.join(body).encode('ascii')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--fixture-source', type=Path, required=True)
    args = parser.parse_args()
    source, output = args.input, args.fixture_source
    require(source.resolve() == source and not source.is_symlink() and source.is_file() and
            0 < source.stat().st_size <= 65536, 'bounded canonical source input required')
    require(output.resolve() == output and output != source and not output.exists() and not output.is_symlink() and
            output.parent.is_dir() and output.parent.resolve() == output.parent,
            'fresh fixture file in ROOT-reserved canonical output directory required')
    fixture = fixture_source(source.read_bytes())
    require(len(fixture) <= 65536, 'bounded new fixture source required')
    with output.open('xb') as stream:
        stream.write(fixture)
    print(json.dumps(dict(schema='note10-v161-parser-fixture-source-v1', input_sha256=INPUT_SHA,
                          fixture_sha256=hashlib.sha256(fixture).hexdigest(), fixture_bytes=len(fixture),
                          compiler_count=0, fixture_count=0, old_tests_count=0)))


if __name__ == '__main__':
    main()
