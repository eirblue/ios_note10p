"""Direct compiler-output stack-path boundary only; no old fixtures or compiler."""
import v223_native_prepare as producer


def run():
    assertions=0
    def check(ok):
        nonlocal assertions
        assertions+=1
        if not ok:raise AssertionError('stack sidecar path assertion failed')
    def command(options):
        return ('cmd_arch/arm64/mm/init.o := clang-14 '+options+' /synthetic/source/arch/arm64/mm/init.c\n\nsource_arch/arm64/mm/init.o := /synthetic/source/arch/arm64/mm/init.c\n').encode()
    def denied(options):
        try:producer.stack_sidecar_relative(command(options))
        except ValueError:return True
        return False
    check(str(producer.stack_sidecar_relative(command('-fstack-usage -c -o arch/arm64/mm/.tmp_init.o')))=='arch/arm64/mm/.tmp_init.su')
    check(str(producer.stack_sidecar_relative(command('-fstack-usage -c -o arch/arm64/mm/init.o')))=='arch/arm64/mm/init.su')
    check(denied('-fstack-usage -c'))
    check(denied('-fstack-usage -c -o arch/arm64/mm/.tmp_init.o -o arch/arm64/mm/init.o'))
    check(denied('-fstack-usage -c -o arch/arm64/mm/../mm/.tmp_init.o'))
    check(denied('-fstack-usage -c -o /arch/arm64/mm/.tmp_init.o'))
    check(denied('-c -o arch/arm64/mm/.tmp_init.o'))
    check(denied('-fstack-usage -c -o arch/arm64/mm/other.o'))
    return dict(groups=1,variants=8,assertions=assertions)
