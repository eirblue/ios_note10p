"""One focused host batch for the v155 Android make environment and DHD link proof."""
import argparse
from io import BytesIO
import json
import os
from pathlib import Path
import subprocess
from unittest.mock import patch

import v154_linux_build as build
import v154_linux_prepare as prepare


def checks(source_pins):
    passed = []

    def check(condition, label):
        if not condition:
            raise AssertionError(label)
        passed.append(label)

    def refuses(operation, label):
        try:
            operation()
        except ValueError:
            passed.append(label)
        else:
            raise AssertionError('unexpected acceptance: '+label)

    expected_env = {'PLATFORM_VERSION': '11', 'ANDROID_MAJOR_VERSION': 'r'}
    check(build.MAKE_ENVIRONMENT == expected_env, 'producer environment metadata contains the two fixed values')
    argv = ['make', '-C', prepare.ROOT/'synthetic-source', '-j4', 'Image']
    log = BytesIO()
    done = subprocess.CompletedProcess(argv, 0)
    common = {'PATH': 'synthetic-tool-path', 'GITHUB_SHA': 'a'*40, 'PRESERVED_VALUE': 'synthetic'}
    for label, platform in (('omitted', {}), ('hostile', {'PLATFORM_VERSION': '10', 'ANDROID_MAJOR_VERSION': 'q'})):
        ambient = dict(common, **platform)
        with patch.dict(os.environ, ambient, clear=True), patch.object(build.subprocess, 'run', return_value=done) as invoke:
            actual = build.run_command(argv, log, 5400)
            invoke.assert_called_once_with(list(map(str, argv)), cwd=prepare.ROOT, stdout=log,
                                           stderr=subprocess.STDOUT, timeout=5400, env=dict(ambient, **expected_env))
            check(actual is done and dict(os.environ) == ambient, label+' platform values pinned in child only')

    exact = 'ffffff8008098000 T dhd_smmu_fault_handler\r\n'
    unrelated = 'ffffff8008098100 T dhd_smmu_fault_handler_clone\n'
    check(build.check_dhd_symbol(unrelated+exact) == dict(name='dhd_smmu_fault_handler', address=0xffffff8008098000, kind='T'),
          'same-build defined text symbol metadata')
    refuses(lambda: build.check_dhd_symbol(unrelated), 'missing exact DHD name refused')
    refuses(lambda: build.check_dhd_symbol(exact+exact), 'duplicate DHD definitions refused')
    refuses(lambda: build.check_dhd_symbol(' U dhd_smmu_fault_handler\n'), 'undefined DHD symbol refused')
    refuses(lambda: build.check_dhd_symbol(exact+' U dhd_smmu_fault_handler\n'), 'definition plus undefined duplicate refused')
    refuses(lambda: build.check_dhd_symbol(exact.replace(' T ', ' D ')), 'non-text DHD symbol refused')

    new = dict(schema=build.V155_HOST_SCHEMA, passed=True, result_sha256='1'*64,
               compiler_count=0, fixture_count=0, old_tests_count=0)
    passes = dict(accepted=prepare.HOST_PASS, new=new, retained_v154_host_result_sha256=build.V154_HOST_RESULT_SHA)
    context = dict(schema=prepare.CONTEXT_SCHEMA, scope='stock-linux-iva-mmap-denial-no-XNU', source_sha256=source_pins,
                   kernel=dict(commit=prepare.COMMIT, archive_sha256=prepare.ARCHIVE_SHA, defconfig_sha256=prepare.DEFCONFIG_SHA),
                   host_pass=passes)
    with patch.object(prepare, 'source_pins', return_value=source_pins):
        check(build.validate_context(context) is context, 'new v155 PASS and carried v154 SHA accepted')
        refuses(lambda: build.validate_context(dict(context, host_pass=dict(passes, new=dict(new, compiler_count=1)))),
                'new compiler count cannot carry v154 compiler')
        refuses(lambda: build.validate_context(dict(context, host_pass=dict(passes, new=dict(new, fixture_count=1)))),
                'new fixture count cannot carry v154 fixture')
        refuses(lambda: build.validate_context(dict(context, host_pass=dict(passes, new=dict(new, schema='note10-v154-linux-host-once-v1')))),
                'old host schema cannot represent new v155 PASS')
        refuses(lambda: build.validate_context(dict(context, host_pass=dict(passes, retained_v154_host_result_sha256='0'*64))),
                'wrong carried v154 result SHA refused')
    return passed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    out = prepare.private(args.output)
    out.mkdir(parents=True)
    result = dict(schema=build.V155_HOST_SCHEMA, passed=False, compiler_count=0, fixture_count=0,
                  old_tests_count=0, actual_Image_builds=0, actual_device_operations=0,
                  retained_v154_host_result_sha256=build.V154_HOST_RESULT_SHA)
    try:
        result['source_sha256'] = prepare.source_pins()
        passed = checks(result['source_sha256'])
        result.update(passed=True, checks=passed, check_count=len(passed), make_environment=dict(build.MAKE_ENVIRONMENT))
    except BaseException as exc:
        result.update(error_type=type(exc).__name__, error=str(exc)[:1024])
        prepare.save(out/'result.json', result)
        raise
    prepare.save(out/'result.json', result)
    print(json.dumps(dict(passed=True, checks=len(passed), compiler_count=0, fixture_count=0, old_tests_count=0)))


if __name__ == '__main__':
    main()
