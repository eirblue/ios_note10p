"""Private v157 draft: insert one observation into the two bound native inputs."""
import hashlib

MAIN_SHA = "36ca4c13d2339db1d897c0f851617fa658e3412373d31d10fc5c7ea1c9f1ff97"
RETURN_SHA = "833f609cac2a84eee47c89cda12c5e523e592ae99f1b090bfea86bd5e53729a3"
DECL = b"extern void n154_require_return_armed(void);\n"
SITE = (b'\tn154_require_return_armed();\n\targv_init[1] = n10_builtin_init_argument();\n'
        b'\targv_init[2] = NULL;\n\tret = run_init_process("/init");\n')
EXEC = b'\tret = run_init_process("/init");\n'
TU_SITE = b'#include "builtin_init_route.c"\n'
NEW_DECL = b"extern void n157_builtin_init_observe(void);\n"
NEW_CALL = b"\tn157_builtin_init_observe();\n"
NEW_INCLUDE = b'#include "v157_builtin_init_observation.inc"\n'


def splice(main, return_tu):
    if (any(main.count(anchor) != 1 for anchor in (DECL, SITE, EXEC)) or
            return_tu.count(TU_SITE) != 1 or
            b"n157_builtin_init_observe" in main or NEW_INCLUDE in return_tu):
        raise ValueError("unique fresh v157 insertion seam required")
    return (main.replace(DECL, DECL + NEW_DECL, 1).replace(EXEC, NEW_CALL + EXEC, 1),
            return_tu.replace(TU_SITE, TU_SITE + NEW_INCLUDE, 1))


def prepare(main, return_tu):
    if (hashlib.sha256(main).hexdigest(), hashlib.sha256(return_tu).hexdigest()) != (MAIN_SHA, RETURN_SHA):
        raise ValueError("exact predecessor guarded main and return TU required")
    return splice(main, return_tu)


def self_check():
    main = DECL + b"#endif\n" + SITE + b"\tif (!ret)\n\t\treturn 0;\n"
    unit = b"/* return code */\n" + TU_SITE + b"/* keep */\n"
    changed_main, changed_unit = splice(main, unit)
    assert NEW_CALL + EXEC in changed_main
    assert changed_main.replace(NEW_DECL, b"").replace(NEW_CALL, b"") == main
    assert changed_unit.replace(NEW_INCLUDE, b"") == unit
    for invalid in (main + EXEC, changed_main):
        try:
            splice(invalid, unit)
        except ValueError:
            continue
        raise AssertionError("duplicate or previously spliced execution seam accepted")


if __name__ == "__main__":
    self_check()
