"""New context-wire boundary only; no old composer/guard/SHA fixtures."""
import json
import v222_native_prepare as producer


def run():
    assertions=0
    def check(ok):
        nonlocal assertions
        assertions+=1
        if not ok:raise AssertionError('context-wire assertion failed')
    def denied(wire):
        try:producer.decode_context_wire(wire)
        except ValueError:return True
        return False
    synthetic=dict(schema='synthetic-public-context',source_head='1'*40,source_sha256={'synthetic.c':'2'*64},passed=True)
    wire=producer.encode_context_wire(synthetic)
    check(type(wire)is str and producer.decode_context_wire(wire)==synthetic)
    check(denied(json.dumps(synthetic,sort_keys=True,separators=(',',':'))))
    check(denied('!not-base64!'))
    return dict(groups=1,variants=3,assertions=assertions)
