"""New actual-XNU host/slot contract. Importing this module performs no I/O."""
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]
PAGE=16384
MEMORY=33554432
SLOT=8388608
BOOT_LIMIT=57671680
VIRTUAL=0xfffffff007004000
RESIDUE=VIRTUAL%MEMORY
SPAN=19136512
ENTRY=11039888
POOL=13025280
POOL_BYTES=163840
INPUT_SCHEMA='note10-v130-owned-xnu-inputs-v1'
SCOPE='v130-owned-xnu-handoff-new-only'
PAYLOAD_SCHEMA='note10-v130-private-payload-member-v1'
BUILD_SCHEMA='note10-v130-generic-xnu-host-v1'
PACKAGE_SCHEMA='note10-v130-private-xnu-package-v1'
PLAN_SCHEMA='note10-v130-owned-xnu-cycle-v1'
DISABLED=b'!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!'


def digest(raw):return hashlib.sha256(raw).hexdigest()
def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def read(path):return json.loads(Path(path).read_bytes())
def save(path,row):
    with Path(path).open('x',encoding='utf-8',newline='\n') as stream:stream.write(json.dumps(row,indent=2)+'\n')
def hexid(value,n=64):
    if not isinstance(value,str) or re.fullmatch('[0-9a-f]{'+str(n)+'}',value) is None:raise ValueError('exact lower-case hexadecimal pin required')
    return value
def ordinary(path):
    path=Path(path).absolute()
    if path!=path.resolve() or path.is_symlink() or not path.is_file():raise ValueError('canonical ordinary input required')
    return path
def private(path):
    path=Path(path).absolute()
    if path!=path.resolve() or path==ROOT/'note10/private' or not path.is_relative_to(ROOT/'note10/private'):
        raise ValueError('canonical project-private output required')
    return path
def align(value,bound=PAGE):return (value+bound-1)//bound*bound


def inputs(path,expected):
    path=ordinary(path)
    if sha(path)!=hexid(expected):raise ValueError('exact reviewed private input contract required')
    row=read(path)
    if row.get('schema')!=INPUT_SCHEMA or row.get('scope')!=SCOPE or set(row.get('inputs',{}))!={'kernel_mem','payload_fit','producer_result','adapter_elf','linux_archive'}:
        raise ValueError('explicit new v130 private input roles required')
    result={}
    for name,item in row['inputs'].items():
        if set(item)!={'path','sha256','bytes'} or type(item['bytes']) is not int or item['bytes']<=0:
            raise ValueError('input path/byte-count/pin contract differs')
        candidate=ordinary(item['path']);hexid(item['sha256'])
        if candidate.stat().st_size!=item['bytes']:raise ValueError('input size differs: '+name)
        # The large payload/adapter are hashed in their only necessary read.
        if name in ('payload_fit','producer_result') and sha(candidate)!=item['sha256']:
            raise ValueError('metadata pin differs: '+name)
        result[name]=(candidate,item)
    producer=read(result['producer_result'][0]);fit=read(result['payload_fit'][0])
    if (producer.get('kind')!='v94-exynos-checked-ptpage-pc' or producer.get('phase')!='complete' or producer.get('passed') is not True or
        fit.get('schema')!=1 or fit.get('purpose')!='current-source-payload-preparation' or
        fit.get('producer_result_sha256')!=result['producer_result'][1]['sha256'] or fit.get('current_producer_kind')!=producer['kind'] or
        producer.get('memory_image_virtual_base')!=hex(VIRTUAL) or producer.get('entry_offset')!=ENTRY or
        producer.get('memory_image_span_bytes')!=SPAN or producer.get('bootstrap_pool_relative_offset')!=POOL or
        producer.get('bootstrap_pool',{}).get('bytes')!=POOL_BYTES or fit.get('payload_bytes')!=SPAN or
        fit.get('payload_sha256')!=result['kernel_mem'][1]['sha256'] or result['kernel_mem'][1]['bytes']!=SPAN or
        fit.get('virtual_base')!=producer.get('memory_image_virtual_base') or fit.get('entry_virtual_address')!=producer.get('entry_virtual_address') or
        fit.get('entry_offset')!=ENTRY or fit.get('bootstrap_pool_relative_offset')!=POOL or fit.get('bootstrap_pool_bytes')!=POOL_BYTES or
        fit.get('producer_id')!=producer.get('producer_id') or fit.get('input_binding')!=producer.get('input_binding')):
        raise ValueError('accepted current94 raw-materialized input join differs')
    return result
