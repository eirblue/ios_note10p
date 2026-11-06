"""Exact146 ->147 synchronous deinit API errno, not callback attribution."""
from hashlib import sha256
import re

CTRL = 'drivers/vision/iva/iva_ctrl.c'
CTRL_SHA256 = 'a2a23d8ee3087b5672b04841ab1bae102221b8c96131dab71498add30d0669a4'
TOKENS = re.compile(rb'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[{}]', re.S)


def function_span(raw, name):
    matches = list(re.finditer(rb'^static\s+(?:inline\s+)?(?:void|int32_t|int|long)\s+(?:__maybe_unused\s+)?' + name.encode() + rb'\s*\(', raw, re.M))
    if len(matches) != 1:
        raise ValueError('exact native definition required: ' + name)
    start = matches[0].start()
    depth = 0
    for token in TOKENS.finditer(raw, raw.index(b'{', matches[0].end())):
        if token.group() == b'{':
            depth += 1
        elif token.group() == b'}':
            depth -= 1
            if not depth:
                return start, token.end()
    raise ValueError('unbalanced native function')


def once(raw, old, new):
    if raw.count(old) != 1:
        raise ValueError('exact native anchor missing or ambiguous')
    return raw.replace(old, new, 1)


def patch_native(ctrl):
    if sha256(ctrl).hexdigest() != CTRL_SHA256:
        raise ValueError('actual146 exact composed native ctrl required')
    start, end = function_span(ctrl, 'iva_ctrl_release_global_init_ref')
    body = ctrl[start:end]
    body = once(body, b'static void ', b'static int ')
    # Two void returns have different source branches; preserve each log/call.
    body = once(body, b'\t\tdev_info(dev, "plz check the pair of init/deinit\\n");\n\t\treturn;',
                b'\t\tdev_info(dev, "plz check the pair of init/deinit\\n");\n\t\treturn 0;')
    body = once(body, b'\t\tdev_err(dev, "%s() fail to deinit iva(%d)\\n", __func__, ret);\n\t\treturn;',
                b'\t\tdev_err(dev, "%s() fail to deinit iva(%d)\\n", __func__, ret);\n\t\treturn ret;')
    body = once(body, b'\tdev_dbg(dev, "%s()\\n", __func__);\n}',
                b'\tdev_dbg(dev, "%s()\\n", __func__);\n\treturn 0;\n}')
    ctrl = ctrl[:start] + body + ctrl[end:]
    start, end = function_span(ctrl, 'iva_ctrl_release_proc_init_ref')
    body = ctrl[start:end]
    body = once(body, b'static void ', b'static int ')
    body = once(body, b'\tint ret;', b'\tbool last;')
    body = once(body, b'\tret = kref_put(&iva->glob_init_ref, iva_ctrl_release_global_init_ref);\n\tif (!ret) {',
                b'\tlast = refcount_dec_and_test(&iva->glob_init_ref.refcount);\n'
                b'\tif (last)\n\t\treturn iva_ctrl_release_global_init_ref(&iva->glob_init_ref);\n'
                b'\tif (!last) {')
    body = body[:-1] + b'\treturn 0;\n}'
    ctrl = ctrl[:start] + body + ctrl[end:]
    start, end = function_span(ctrl, 'iva_ctrl_deinit')
    body = ctrl[start:end]
    body = once(body, b'\tunsigned int\tput_cnt;', b'\tunsigned int\tput_cnt;\n\tint ret = 0;')
    body = once(body, b'\t\tiva_ctrl_release_proc_init_ref(&proc->init_ref);',
                b'\t\tret = iva_ctrl_release_proc_init_ref(&proc->init_ref);')
    body = once(body, b'\t/* always return as successful */\n\treturn 0;',
                b'\t/* Synchronous API errno only; references remain consumed. */\n\treturn ret;')
    ctrl = ctrl[:start] + body + ctrl[end:]
    return {CTRL: ctrl}
