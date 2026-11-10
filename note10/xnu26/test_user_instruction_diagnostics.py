"""One new host-only diagnostic parser fixture; no compiler or old host cases."""
import json

from user_instruction_diagnostics import summarize


def main():
    roots = {'/repo/note10/xnu26': 'port', '/private/run/source': 'XNU',
             '/private/run/configured': 'generated', '/Applications/SDK With Spaces': 'SDK'}
    cases = [
        (b"/repo/note10/xnu26/fetch.c:12:4: error: use of undeclared identifier 'type_x'\n",
         'port/fetch.c', "use of undeclared identifier 'type_x'"),
        (b"/private/run/configured/meta.h:8:2: fatal error: unknown type name 'native_t'\n",
         'generated/meta.h', "unknown type name 'native_t'"),
        (b"clang: error: unknown argument: '-bad-flag'\n", 'driver', "unknown argument: '-bad-flag'"),
        (b"/private/run/source/bsd/a.h:1:1: fatal error: 'missing/public.h' file not found\n",
         'XNU/bsd/a.h', "'missing/public.h' file not found"),
        (b"clang: error: cannot open '/Applications/SDK With Spaces/header.h': type 'safe_t'\n",
         'driver', "cannot open 'SDK/header.h': type 'safe_t'"),
        (b"/Users/Secret/build/a.c:9:3: error: cannot open '/Unknown/Private File.h': type 'safe_t'\n",
         'external', "cannot open '[path; tail redacted]'"),
        (b"\x1b[31m/private/run/source/a.h:3:7: error: expected ')'\x1b[0m\nIn file included from /Users/Secret/a.h:1:\n  1 | foo: error: private source snippet\n  ^~~~\n",
         'XNU/a.h', "expected ')'"),
        (b"clang: error: cannot open C:\\Users\\Secret\\file.h: missing native_t\n",
         'driver', 'cannot open [path]: missing native_t'),
        (b"clang: error: '/repo/note10/xnu26-secret/file.h' unavailable\n",
         'driver', "'[path; tail redacted]'"),
        (b'clang: error: cannot open "/Users/O\'Neil/private.h": type \'safe_t\'\n',
         'driver', "cannot open '[path]': type 'safe_t'"),
        (b"clang: error: cannot open '/Users/O'Neil/private.h': type 'safe_t'\n",
         'driver', "cannot open '[path; tail redacted]'"),
        (b"clang: error: cannot open '/Users/O'Neil/private.h\n",
         'driver', "cannot open '[path; tail redacted]'"),
    ]
    for raw, file, message in cases:
        result = summarize(raw, roots)
        assert len(result['records']) == 1
        record = result['records'][0]
        assert record['file'] == file and record['message'] == message
        public = json.dumps(result)
        assert not any(token in public for token in ('/Users/', '/Unknown/', '/private/', '/Applications/',
                                                     'Secret', 'private source snippet'))
    capped = summarize(b"clang: error: " + b'x'*900 + b'\n' + b'clang: note: repeated\n'*20, roots)
    assert len(capped['records']) == 8 and capped['omitted_records'] == 13
    assert capped['records'][0]['message_truncated'] is True
    assert len(capped['records'][0]['message']) == 512 and capped['public_text_bytes'] <= 8192
    maximal = summarize((b'/private/run/source/' + b'a'*180 + b':1:1: error: ' + b'x'*600 + b'\n')*9, roots)
    assert len(json.dumps(maximal).encode()) <= 8192
    unmatched = summarize(b'not a compiler diagnostic\n' + b'x'*70000, roots)
    assert unmatched['records'] == [] and unmatched['input_truncated'] is True
    assert unmatched['unmatched_lines'] == 2
    assert summarize(b'', roots)['stderr_bytes'] == 0
    prefixed = summarize(b'clang: warning: warning text\nclang: note: preceding note\nclang: error: useful_error\n', roots)
    assert len(prefixed['records']) == 1 and prefixed['records'][0]['message'] == 'useful_error'
    unc = summarize(b'clang: error: cannot open "\\\\server\\share\\secret.h": safe_t\n'
                    b"clang: error: cannot open '\\\\server\\share\\secret.h': safe_t\n"
                    b'clang: error: cannot open \\\\server\\share\\secret.h: safe_t\n', roots)
    assert len(unc['records']) == 3 and all(row['path_redacted'] for row in unc['records'])
    assert not any(token in json.dumps(unc) for token in ('server', 'share', 'secret.h'))
    print(f'v163 compiler diagnostics: PASS ({len(cases)+6} cases)')


if __name__ == '__main__':
    main()
