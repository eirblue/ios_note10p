"""One NEW package-only reference-header/source-domain batch. No old fixtures."""
import argparse
import copy
import json
from pathlib import Path
import struct
import traceback
import v129_package as package

ROOT=package.ROOT
SCOPE='v129-official-reference-header-domain-new-only'
SCHEMA='note10-v129-reference-header-package-test-v1'
PREFIX_BYTES=1660
OFFICIAL_SIZE=59125760
OFFICIAL_PREFIX_SHA256='b154c633842026b1497f97919094d30731544bf5c1e11bfc8c098ccacdc1da45'
OFFICIAL_PATH=ROOT/'note10/private/install-tools/twrp-3.7.0_9-1-d2x.img'


def reject(action):
    try:action()
    except ValueError:return
    raise ValueError('invalid NEW reference-header/domain case admitted')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--scope',required=True,choices=(SCOPE,))
    p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();out=package.private(a.output)
    if out.exists():p.error('fresh private package-only batch output required')
    out.mkdir()
    result=dict(schema=SCHEMA,scope=SCOPE,passed=False,run=1,source_sha256=package.package_producer_pins(),
        header_prefix_reads=0,full_TWRP_reads=0,Image_reads=0,payload_reads=0,fixture_compiles=0,fixture_processes=0,
        old129_fixture_runs=0,old128core_runs=0,old127_runs=0,Image_builds=0,CI_operations=0,device_operations=[])
    try:
        path=package.private(OFFICIAL_PATH)
        if path.is_symlink() or path.stat().st_size!=OFFICIAL_SIZE:raise ValueError('official reference size/path differs')
        with path.open('rb') as stream:raw=stream.read(PREFIX_BYTES)
        result['header_prefix_reads']=1
        if len(raw)!=PREFIX_BYTES or package.digest(raw)!=OFFICIAL_PREFIX_SHA256:raise ValueError('exact pinned official header prefix differs')
        actual=package.header(raw,reference=True,file_size=OFFICIAL_SIZE)
        if (actual['second_size']!=0 or actual['recovery_dtbo_size']!=2069888 or
            actual['recovery_dtbo_offset']!=actual['payload_end'] or actual['payload_end']!=57055232 or
            actual['header_size']!=1648 or actual['cmdline']!='buildvariant=eng'):
            raise ValueError('actual official recovery layout/cmdline differs')
        result['actual_reference_header']=actual
        rejected=[]
        def mutation(label,offset,fmt,value):
            bad=bytearray(raw);struct.pack_into(fmt,bad,offset,value)
            reject(lambda:package.header(bytes(bad),reference=True,file_size=OFFICIAL_SIZE));rejected.append(label)
        mutation('second-stage-not-supported',24,'<I',1)
        mutation('wrong-header-version',40,'<I',2)
        mutation('wrong-page-size',36,'<I',2049)
        mutation('wrong-header-size',1644,'<I',0)
        mutation('DTBO-overlaps-ramdisk',1636,'<Q',actual['payload_end']-2048)
        mutation('DTBO-not-at-canonical-end',1636,'<Q',actual['payload_end']+2048)
        mutation('DTBO-size-overruns-reference',1632,'<I',OFFICIAL_SIZE)
        mutation('DTBO-offset-overflows-file',1636,'<Q',(1<<64)-1)
        mutation('empty-DTBO-with-nonzero-offset',1632,'<I',0)
        reject(lambda:package.header(raw,reference=True,file_size=actual['payload_end']-1));rejected.append('payload-end-past-file')
        reject(lambda:package.header(raw[:1647],reference=True,file_size=OFFICIAL_SIZE));rejected.append('short-header')
        # Diagnostic BOOT remains kernel-only: no external ramdisk or embedded DTBO.
        diagnostic=bytearray(4096);diagnostic[:len(raw)]=raw
        struct.pack_into('<I',diagnostic,8,16);struct.pack_into('<I',diagnostic,16,0)
        struct.pack_into('<IQI',diagnostic,1632,0,0,1648)
        packed=package.header(bytes(diagnostic))
        if packed['ramdisk_size'] or packed['recovery_dtbo_size'] or packed['cmdline']!=actual['cmdline']:
            raise ValueError('diagnostic zero external payload/cmdline contract differs')
        forbidden=bytearray(diagnostic)+bytes(16);struct.pack_into('<IQ',forbidden,1632,16,4096)
        reject(lambda:package.header(bytes(forbidden)));rejected.append('reference-DTBO-not-allowed-in-diagnostic')
        # Test only source metadata here: no accepted kernel Image/config/CPIO reads.
        frozen=package.read(package.BUILD_SOURCE_MANIFEST)
        build=dict(ci_context=dict(GITHUB_SHA=package.BUILD_SOURCE_HEAD),
                   source_sha256={name:row['sha256'] for name,row in frozen['files'].items()})
        accepted=package.verify_build_source_domain(build)
        current=package.package_producer_pins();package.verify_pins(current)
        if accepted['note10/device_test/v129_package.py']==current['note10/device_test/v129_package.py']:
            raise ValueError('package delta was not separated from immutable build domain')
        bad=copy.deepcopy(build);bad['source_sha256']['note10/device_test/v129_package.py']=current['note10/device_test/v129_package.py']
        reject(lambda:package.verify_build_source_domain(bad));rejected.append('current-producer-pin-cannot-replace-old-build-pin')
        bad=copy.deepcopy(build);bad['ci_context']['GITHUB_SHA']='0'*40
        reject(lambda:package.verify_build_source_domain(bad));rejected.append('wrong-build-source-head')
        result.update(passed=True,rejections=rejected,immutable_build_source_sha256=accepted,
                      current_package_producer_sha256=current,official_prefix_sha256=package.digest(raw),
                      reference_scope='1660 header bytes plus stat size only; full reference hash is retained provenance, not reread here')
    except Exception:result['error']=traceback.format_exc()
    package.save(out/'result.json',result)
    print(json.dumps(dict(passed=result['passed'],header_prefix_reads=result['header_prefix_reads'],Image_reads=0)))
    return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
