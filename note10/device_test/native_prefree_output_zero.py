"""Distinct native prefree observer candidate; current admission is always blocked."""
from pathlib import Path
import linux_data_carrier as data
import native_scoped_output as scoped
KIND='kernel-prefree-output-zero-observation-candidate'
SCHEMA='n10-prefree-output-zero-native-candidate-v1'
WIRE_SCHEMA='native-prefree-output-zero-v1'
SELECTOR='v121-native-prefree-output-zero-candidate-pc-first'
REFERENCE_LINKED_BYTES=59588608
SOURCES=('native_prefree_output_zero.py','native_prefree_output_zero.h','native_prefree_output_zero_fixture.c','test_v121_native_prefree_output_zero.py')
API_PINS=scoped.API_PINS

def selected(row):
    return any(row.get(key)==KIND for key in ('diagnostic_kind','data_input_kind','storage_input_kind')) or 'prefree_output_schema' in row or row.get('schema')==SCHEMA

def refuse(row):
    data.require(not selected(row),'native121 has no current offline/device admission')

def install(source,identity):
    result=scoped.install(source,identity);source=Path(source)
    target=source/'drivers/misc/note10_sha256_kat.c';raw=target.read_bytes();match=b'#define N10_DATA_SCOPED_OUTPUT 1'
    data.require(raw.count(match)==1,'one scoped route required for distinct prefree producer')
    raw=raw.replace(match,match+b'\n#ifdef CONFIG_NOTE10_PREFREE_OUTPUT_ZERO\n#define N10_DATA_PREFREE_OUTPUT_ZERO 1\n#endif',1);target.write_bytes(raw)
    result['drivers/misc/note10_sha256_kat.c']=data.sha(raw)
    config=source/'drivers/misc/note10_sha256_kat.Kconfig'
    config.write_bytes(config.read_bytes()+b'\nconfig NOTE10_PREFREE_OUTPUT_ZERO\n\tbool "Note10 native prefree output zero observation candidate"\n\tdepends on NOTE10_SCOPED_OUTPUT_LEASE\n\tdefault n\n')
    result['drivers/misc/note10_sha256_kat.Kconfig']=data.sha(config.read_bytes())
    raw=(data.HERE/'native_prefree_output_zero.h').read_bytes();(source/'drivers/misc/native_prefree_output_zero.h').write_bytes(raw)
    result['drivers/misc/native_prefree_output_zero.h']=data.sha(raw)
    return result
