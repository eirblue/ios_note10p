"""Distinct native scoped-output candidate; current offline/device admission is blocked."""
from pathlib import Path
import kernel_readonly_span_candidate as ro3
import readonly_stage_witness as stage
import linux_data_carrier as data

KIND='kernel-scoped-verified-output-candidate'
SCHEMA='n10-scoped-verified-output-native-candidate-v1'
WIRE_SCHEMA='native-output-scope-v1'
SELECTOR='v116-native-scoped-output-candidate-pc-first'
REFERENCE_LINKED_BYTES=59588608
HANDLE_BYTES=24
SOURCES=('native_scoped_output.py','native_scoped_output.h','native_scoped_output_fixture.c','test_v116_native_scoped_output.py')
API_PINS=ro3.API_PINS


def selected(row):
    return any(row.get(key)==KIND for key in ('diagnostic_kind','data_input_kind','storage_input_kind')) or 'scoped_output_schema' in row


def refuse(row):
    data.require(not selected(row),'new scoped-output native candidate has no current offline/device admission')


def install(source,identity):
    result=stage.install(source,identity);source=Path(source)
    target=source/'drivers/misc/note10_sha256_kat.c';raw=target.read_bytes();match=b'#define N10_DATA_STAGE_WITNESS 1'
    data.require(raw.count(match)==1,'one native stage route required for scoped output')
    raw=raw.replace(match,match+b'\n#ifdef CONFIG_NOTE10_SCOPED_OUTPUT_LEASE\n#define N10_DATA_SCOPED_OUTPUT 1\n#endif',1);target.write_bytes(raw)
    result['drivers/misc/note10_sha256_kat.c']=data.sha(raw)
    config=source/'drivers/misc/note10_sha256_kat.Kconfig'
    config.write_bytes(config.read_bytes()+b'\nconfig NOTE10_SCOPED_OUTPUT_LEASE\n\tbool "Note10 scoped verified output lifetime candidate"\n\tdepends on NOTE10_KERNEL_READONLY_SPAN_CANDIDATE\n\tdefault n\n')
    result['drivers/misc/note10_sha256_kat.Kconfig']=data.sha(config.read_bytes())
    raw=(data.HERE/'native_scoped_output.h').read_bytes();(source/'drivers/misc/native_scoped_output.h').write_bytes(raw)
    result['drivers/misc/native_scoped_output.h']=data.sha(raw)
    return result
