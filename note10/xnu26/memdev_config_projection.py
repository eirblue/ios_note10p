"""Public metadata projection only; never changes trusted native compiler defines."""
import hashlib
import json
import re


def project_defines(defines):
    if (type(defines) is not list or len(defines) > 1024 or
            any(type(flag) is not str or len(flag) > 4096 for flag in defines)):
        raise ValueError('bounded source-generated defines required')
    public, omitted = [], []
    for flag in defines:
        if re.fullmatch(r'-D[A-Za-z0-9_]+(?:=[A-Za-z0-9_+.-]+)?', flag):
            public.append(flag)
        else:
            name = re.match(r'-D([A-Za-z0-9_]{1,96})(?==|$)', flag)
            omitted.append(dict(name=name.group(1) if name else 'unclassified',
                sha256=hashlib.sha256(flag.encode()).hexdigest()))
    return public, dict(schema='note10-v169-bsd-defines-projection-v1', full_count=len(defines),
        full_sha256=hashlib.sha256(json.dumps(defines, separators=(',', ':')).encode()).hexdigest(),
        public_count=len(public), omitted_count=len(omitted), omitted=omitted)
