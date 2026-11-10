"""Bounded Clang diagnostic records; no snippets, include stacks or raw paths."""
import hashlib
import re

MAX_INPUT = 65536
MAX_RECORDS = 8
MAX_MESSAGE = 512
MAX_PUBLIC = 8192
ANSI = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')
LOCATION = re.compile(r'^(.+?):([0-9]+):([0-9]+): (fatal error|error|warning|note): (.*)$')
DRIVER = re.compile(r'^(?:(?:clang[-+A-Za-z0-9.]*|cc1): )?(fatal error|error|warning|note): (.*)$')
QUOTED_PATH = re.compile(r'"(?:[A-Za-z]:[\\/]|\\\\|/|~[\\/])[^"\r\n]*"')
SINGLE_PATH = re.compile(r"'(?:[A-Za-z]:[\\/]|\\\\|/|~[\\/])[^\r\n]*")
BARE_PATH = re.compile(r'''(?<![A-Za-z0-9_])(?:[A-Za-z]:[\\/]|\\\\|/(?=\S)|~[\\/])[^'",;:\r\n]*''')


def summarize(stderr, roots):
    """roots contains only compiler/public-source/generated/SDK roots, never HOME."""
    mappings = []
    for path, alias in sorted(roots.items(), key=lambda row: len(row[0]), reverse=True):
        if not path or not re.fullmatch(r'[A-Za-z][A-Za-z0-9-]{0,31}', alias):
            raise ValueError('closed diagnostic root alias required')
        mappings.append((re.compile(re.escape(path) + r'(?=$|[/\\\s\'":,)])'), alias))

    def logical(text):
        for pattern, alias in mappings:
            text = pattern.sub(lambda _: alias, text)
        return text

    def message(text):
        text = logical(text)
        # An unknown single-quoted path may contain apostrophes; do not guess its closing quote.
        text, single = SINGLE_PATH.subn("'[path; tail redacted]'", text)
        text, quoted = QUOTED_PATH.subn("'[path]'", text)
        text, bare = BARE_PATH.subn('[path]', text)
        text = ''.join(c if 32 <= ord(c) <= 126 else '?' for c in text)
        return text[:MAX_MESSAGE], bool(single or quoted or bare), len(text) > MAX_MESSAGE

    records = []
    unmatched = omitted = public_bytes = 0
    text = ANSI.sub('', stderr[:MAX_INPUT].decode('utf-8', errors='replace'))
    for row in text.splitlines():
        match = LOCATION.fullmatch(row)
        if match:
            filename, line, column, severity, detail = match.groups()
            file = logical(filename)
            known = any(file == alias or file.startswith(alias + '/') or file.startswith(alias + '\\')
                        for _, alias in mappings)
            file = file.replace('\\', '/')
            file = file if known and '..' not in file.split('/') else 'external'
            if not re.fullmatch(r'[A-Za-z0-9_./+-]{1,192}', file):
                file = 'external'
            line = min(int(line), 2**31-1) if len(line) <= 10 else 2**31-1
            column = min(int(column), 2**31-1) if len(column) <= 10 else 2**31-1
        else:
            match = DRIVER.fullmatch(row)
            if not match:
                unmatched += bool(row.strip())
                continue
            severity, detail = match.groups()
            file, line, column = 'driver', 0, 0
        if severity == 'warning' or (severity == 'note' and not records):
            unmatched += 1
            continue
        safe, redacted, truncated = message(detail)
        record = dict(file=file, line=line, column=column, severity=severity,
                      message=safe, path_redacted=redacted or file == 'external', message_truncated=truncated)
        size = len(safe) + len(file) + len(severity)
        if len(records) == MAX_RECORDS or public_bytes + size > MAX_PUBLIC:
            omitted += 1
        else:
            records.append(record)
            public_bytes += size
    return dict(schema='note10-v163-compiler-diagnostics-v1', stderr_sha256=hashlib.sha256(stderr).hexdigest(),
                stderr_bytes=len(stderr), input_truncated=len(stderr) > MAX_INPUT,
                records=records, omitted_records=omitted, unmatched_lines=unmatched,
                public_text_bytes=public_bytes)
