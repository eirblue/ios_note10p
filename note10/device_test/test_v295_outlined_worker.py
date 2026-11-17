"""Synthetic compiler-output cases only; no captured device/kernel fragments."""
import inspect
import v295_recovery_prepare as producer


def predicate():
    def branch(site, target, link=False):
        return (0x94000000 if link else 0x14000000) | (((target-site)//4) & 0x03ffffff)
    def body(start, words):
        return '\n'.join(f'{start+4*i:x}:\t{word:08x}\tsynthetic' for i, word in enumerate(words))
    nm = ('_text T 0 0\n_end B 1000 0\nn10_return_worker t 100 10\n'
          'kernel_restart T 800 4\nOUTLINED_FUNCTION_0 t 200 4\n'
          'OUTLINED_FUNCTION_1 t 210 4\nOUTLINED_FUNCTION_0 t 220 4\n')
    worker = body(0x100, [branch(0x100, 0x200, True), branch(0x104, 0x210, True),
                          branch(0x108, 0x220, True), 0xd65f03c0])
    bodies = {0x200: body(0x200, [0xd65f03c0]), 0x210: body(0x210, [0xd65f03c0]),
              0x220: body(0x220, [branch(0x220, 0x800)])}
    calls = []
    def capture(entry, index):
        calls.append(entry['address'])
        return bodies[entry['address']]
    proof = producer.worker_recovery_proof(worker, nm, capture)
    assert calls == [0x200, 0x210, 0x220] and len(proof['helpers']) == 3 and proof['helper_bytes'] == 12
    assert proof['witnesses'][0]['kernel_restart_address'] == 0x800

    def refused(symbols, data):
        try:
            producer.worker_recovery_proof(worker, symbols, lambda entry, index: data[entry['address']])
        except ValueError:
            return
        raise AssertionError('unclosed compiler proof accepted')
    refused(nm + 'alias t 200 4\n', bodies)
    refused(nm.replace('OUTLINED_FUNCTION_0 t 200 4', 'OUTLINED_FUNCTION_0 t 200 100'), bodies)
    refused(nm, {address: body(address, [0xd65f03c0]) for address in bodies})
    nested = dict(bodies)
    nested[0x200] = body(0x200, [branch(0x200, 0x300)])
    refused(nm + 'OUTLINED_FUNCTION_3 t 300 4\n', nested)

    source = inspect.getsource(producer.run_build)
    write = "(out / 'Image').write_bytes(raw)"
    assert source.count(write) == 1
    assert source.index("run([*make, 'V=1', '-j4', 'Image'], '04-Image', 5400)") < source.index(write)
    assert source.index(write) < source.index("result['compiled_Image_retained']") < source.index("run(['aarch64-linux-gnu-nm'")
    assert source.index(write) < source.index('result.update(image_proof(')
    assert {key: value for key, value in producer.SETTINGS.items() if key != 'LOCALVERSION'} == {
        key: value for key, value in producer.retained.SETTINGS.items() if key != 'LOCALVERSION'}
    return dict(passed=True, groups=1, variants=6, assertions=6)
