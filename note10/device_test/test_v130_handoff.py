"""One new-only grouped batch; actual private compression happens once after synthetic checks."""
import argparse
import base64
import gzip
import json
from pathlib import Path
import struct
import subprocess
import sys
import tarfile
import zlib
from v130_contract import *
from v130_build import source_pins
from v130_payload import produce as payload_produce
from v130_platform import produce as platform_produce,parse
from v130_slot import newc,generic,insert,metadata
from v130_package import current_and_restore
import v130_prepare as prepare
from v130_sources import INPUT128
sys.path.insert(0,str(ROOT/'note10/xnu26'))
from boot_adt import Node,encode,decode
HERE=Path(__file__).resolve().parent


def reject(call):
    try:call()
    except (ValueError,struct.error,zlib.error):return
    raise AssertionError('new boundary rejection did not reject')


def mixed(raw):
    """Host framing oracle only, not execution of Linux unpack_to_rootfs."""
    names=[];at=0
    while at<len(raw):
        if raw[at]==0:at+=1;continue
        if raw[at:at+2]==b'\x1f\x8b':
            member=zlib.decompressobj(31);decoded=member.decompress(raw[at:]);decoded+=member.flush()
            if not member.eof:raise ValueError('truncated gzip member')
            names.extend(mixed(decoded));at=len(raw)-len(member.unused_data);continue
        if at%4 or raw[at:at+6]!=b'070701' or at+110>len(raw):raise ValueError('invalid mixed newc member boundary')
        fields=[int(raw[at+6+i*8:at+14+i*8],16) for i in range(13)];size=fields[6];length=fields[11];name_start=at+110
        if not 1<=length<=256 or name_start+length>len(raw) or raw[name_start+length-1]:raise ValueError('newc name extent differs')
        name=raw[name_start:name_start+length-1].decode('ascii');body=(name_start+length+3)&~3
        if body+size>len(raw):raise ValueError('newc body truncated')
        at=(body+size+3)&~3
        if name!='TRAILER!!!':names.append(name)
    return names


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--scope',required=True,choices=[SCOPE]);p.add_argument('--inputs-contract',type=Path,required=True)
    p.add_argument('--inputs-sha256',required=True);p.add_argument('--compiler',type=Path,required=True)
    p.add_argument('--compiler-arg',action='append',default=[]);p.add_argument('--capture-receipt',required=True,type=Path)
    p.add_argument('--capture-sha256',required=True);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    out=private(a.output);compiler=ordinary(a.compiler);source=inputs(a.inputs_contract,a.inputs_sha256)
    if out.exists():p.error('fresh one-shot NEW batch output required')
    pins=source_pins();out.mkdir(parents=True)
    save(out/'attempt.json',dict(schema='note10-v130-new-batch-attempt-v1',scope=SCOPE,source_sha256=pins,old_tests_replayed=0))
    result=dict(schema='note10-v130-grouped-new-batch-v1',scope=SCOPE,passed=False,source_sha256=pins,
        compiler_path=str(compiler),compiler_sha256=sha(compiler),compiler_invocations=0,fixture_processes=0,
        actual_private_kernel_reads=0,actual_compressions=0,device_operations=[],old_tests_replayed=0)
    try:
        # Only new source/render contracts. No old v127/128/129 fixture/main call.
        archive=source['linux_archive'][0]
        if sha(archive)!=source['linux_archive'][1]['sha256']:raise ValueError('new batch source archive pin differs')
        prefix='android_kernel_samsung_universal9820-55f042627bb7030c93550faafa117674d32b21d1/'
        with tarfile.open(archive,'r:gz') as tar:stock={name:tar.extractfile(prefix+name).read() for name in prepare.PINS}
        frozen=ROOT/'note10/private/device-test/v128-legacy-kexec-recovery-proof-20261105/frozen-source'
        for target,name in prepare.COMMON.items():
            path=frozen/'note10/device_test'/name
            if sha(path)!=INPUT128['note10/device_test/'+name]:raise ValueError('immutable source component differs')
        rendered=prepare.render(stock,'0123456789abcdef0123456789abcdef',frozen)
        core=rendered['kernel/kexec_core.c'];machine=rendered['arch/arm64/kernel/machine_kexec.c']
        assert core.index(b'n130_before_shutdown(kexec_image)')<core.index(b'kernel_restart_prepare(NULL)')<core.index(b'n130_after_shutdown()')<core.index(b'machine_shutdown()')
        assert b'0, /* Source-bound preserve EL1' in machine and b'cbz' not in machine
        assert rendered['init/initramfs.c'].index(b'initrd_start = 0')<rendered['init/initramfs.c'].index(b'unpack_to_rootfs(__initramfs_start')
        assert b'n130_dma_frozen()) return -EBUSY' in rendered['include/linux/dmaengine.h']
        assert b'n130_ever_allocated' in rendered['drivers/dma/pl330.c']
        # Actual pinned source proof of mixed framing, raw single.cpio passthrough and gzip trailer consumption.
        assert b'decompress_method' in stock['init/initramfs.c'] and b'my_inptr' in stock['init/initramfs.c']
        assert b'strm->next_in - zbuf+8' in stock['lib/decompress_inflate.c']
        assert b'.incbin' in stock['usr/initramfs_data.S'] and b'__irf_end - __irf_start' in stock['usr/initramfs_data.S']
        synthetic_init=bytearray(128);synthetic_init[:6]=b'\x7fELF\x02\x01';synthetic_init[18:20]=b'\xb7\0';synthetic_init[64:96]=DISABLED
        generic_cpio,prefix_bytes=generic(bytes(synthetic_init));offset=256;image=bytes(offset)+generic_cpio
        layout=dict(slot_offset=offset+prefix_bytes,slot_bytes=SLOT,cycle_offset=offset+generic_cpio.index(DISABLED))
        member=gzip.compress(newc([('n10/kernel.mem',0o100400,b'synthetic-new-v130-only',0,0)]),mtime=0)
        meta=metadata(b'new synthetic ADT',bytes(128),'0'*64)
        enabled,usage=insert(image,layout,member,meta,'1'*32)
        assert set(mixed(enabled[offset:]))=={'dev','sys','n10','dev/console','dev/kmsg','init','n10/kernel.mem','n10/platform.adt','n10/platform.contract','n10/activation.contract'}
        reject(lambda:mixed(member[:-8]));reject(lambda:mixed(newc([('a',0o100400,b'abc',0,0)])[:-20]))
        reject(lambda:insert(image,layout,member,bytes(SLOT),'1'*32))
        dirty=bytearray(image);dirty[layout['slot_offset']]=1;reject(lambda:insert(bytes(dirty),layout,member,meta,'1'*32))
        reject(lambda:parse(bytes(40)))
        rows=[dict(partition=name,file=name+'.img',sha256='2'*64,size=4096,block_node='/dev/block/sda'+str(i+1),remote_hash_before_and_after_match=True) for i,name in enumerate(('boot','recovery','dtb','dtbo','vbmeta'))]
        saved=dict(complete=True,partition_writes=False,bootloader='synthetic',partitions=rows)
        current=dict(schema='note10-v129-proof-package-v2',version='v129',cycle='1'*32,build_evidence_id='3'*32,
            rollback_BOOT_sha256='2'*64,diagnostic_BOOT_sha256='4'*64,bootloader='synthetic',partitions=rows)
        prior=dict(schema='note10-v129-proof-ledger-v1',recovery_returned=True,host_BOOT_write_attempts=1,host_reboot_attempts=1,
            cycle='1'*32,build_evidence_id='3'*32,normal_recovery_fallback_observed=False)
        assert current_and_restore(current,prior,saved)[0]=='4'*64
        reject(lambda:current_and_restore(dict(current,rollback_BOOT_sha256='4'*64),prior,saved))
        reject(lambda:current_and_restore(current,dict(prior,cycle='5'*32),saved))

        tree=encode(Node('device-tree',children=[Node('chosen',properties={'dram-base':struct.pack('<Q',0x80000000),'dram-size':struct.pack('<Q',MEMORY)})]))
        (out/'synthetic.adt').write_bytes(tree);exe=out/('fixture.exe' if sys.platform=='win32' else 'fixture')
        command=[str(compiler),*a.compiler_arg,'-std=c11','-O2','-Wall','-Wextra','-Werror','-I',str(HERE),str(HERE/'v130_fixture.c'),str(HERE/'v130_handoff_core.c'),'-o',str(exe)]
        result['compiler_invocations']=1;save(out/'compiler-command.json',dict(argv=command))
        with (out/'compile.log').open('wb') as log:subprocess.run(command,cwd=ROOT,check=True,stdout=log,stderr=subprocess.STDOUT,timeout=120)
        result['fixture_processes']=1
        with (out/'fixture.log').open('wb') as log:subprocess.run([str(exe),str(out/'synthetic.adt'),str(out/'owned.adt')],cwd=ROOT,check=True,stdout=log,stderr=subprocess.STDOUT,timeout=30)
        final=decode((out/'owned.adt').read_bytes());chosen=final.children[0]
        assert int.from_bytes(chosen.properties['dram-base'],'little')%MEMORY==RESIDUE and int.from_bytes(chosen.properties['dram-size'],'little')==MEMORY
        synthetic=dict(schema='note10-v130-synthetic-new-result-v1',passed=True,scope=SCOPE,source_sha256=pins,
            native_compiles=1,native_processes=1,old_tests_replayed=0,mixed_CPIO_oracle='host framing only; pinned Linux source proof, no native unpacker execution claim',
            physical_XNU_executed=False)
        save(out/'synthetic-result.json',synthetic)
        public=dict(schema='note10-v130-public-new-pass-v1',scope=SCOPE,passed=True,synthetic_result_sha256=sha(out/'synthetic-result.json'),source_sha256=pins)
        save(out/'public-pass-context.json',public)
        (out/'public-pass-context.b64').write_text(base64.b64encode(json.dumps(public,separators=(',',':')).encode()).decode()+'\n')
        platform_result=platform_produce(a.capture_receipt,a.capture_sha256,out/'actual-platform-once')
        platform_metadata=read(platform_result)
        # Real payload is read/hash/compressed only here, once, after NEW checks pass.
        actual=payload_produce(a.inputs_contract,a.inputs_sha256,out/'private-member-once')
        result['actual_private_kernel_reads']=actual.get('kernel_input_reads',0);result['actual_compressions']=actual.get('compressions',0)
        if actual.get('passed') is not True:raise ValueError('actual ONE private compression/fit failed')
        if align(actual['compressed_bytes'],4)+platform_metadata['activation_member_bytes']>SLOT:raise ValueError('actual ONE compression plus actual platform metadata exceeds8MiB')
        if pins!=source_pins():raise ValueError('new source changed during grouped batch')
        result.update(passed=True,payload_result=str(out/'private-member-once/result.json'),platform_result=str(platform_result),
            public_PASS_contains_private_input_metadata=False,physical_ready=False)
    except Exception:
        import traceback
        result['error']=traceback.format_exc()
    save(out/'result.json',result);return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
