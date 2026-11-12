"""Fresh prepare-only Linux producer; no native source input or transfer mode."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import uuid
import zipfile
import v154_linux_prepare as p
import v154_linux_build as house
import v130_archive as archive_helper
from v130_slot import newc
import v161_initramfs_force as parser_helper
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
WORKFLOW='.github/workflows/note10-v210-native-prepare.yml'
JOB='v210-native-prepare'
BUILD_SCHEMA='note10-v210-native-prepare-build-v1'
CONTEXT_SCHEMA='note10-v210-native-prepare-public-input-v1'
MANIFEST_SCHEMA='note10-v210-native-prepare-sealed-members-v1'
PUBLIC_FILES=('native_parcel_core.h','native_parcel_core.c','native_prepare_core.h','native_prepare_core.c',
              'native_prepare_fixture.c','v210_native_prepare_kernel.c','v210_native_prepare_pid1.c',
              'v210_native_prepare.py','test_v210_native_prepare.py')
SLOT_BYTES=4096
SUCCESS_MEMBERS=('result.json','01-pid1.log','minimal-init.elf','initramfs.cpio','02-defconfig.log','03-settings.log','04-config.log','actual-effective.config','05-Image.log','Image','System.map','members.json')
FALSE_CLAIMS=dict(native_source_present=False,native_source_hash_in_RAM_verified=False,source_buffer_lifetime_verified=False,
                  bootargs_materialized=False,ADT_materialized=False,qualified_XNU_return=False,XNU_entry_observed=False,
                  native_virtual_mapping_verified=False,full_native_physical_ready=False,XNU_execution_allowed=False,internal_kexec_limit=0)
RETAINED_PINS={'.github/workflows/note10-v154-linux-iva-diagnostic.yml': '0986978993c167297a5301eac7bf8df331ec8ce40214653ebb449e6dada3cf0d', 'note10/device_test/auto_return.c': '9ec43d3d17f12fe90d2ab36e4712537b7f8275f6f27b6536bbef826f9692037d', 'note10/device_test/builtin_init_route.c': '2fb12577bfd332cd83c3e497aa5930c275983e0f9139d22f53b009b0a9249d74', 'note10/device_test/builtin_init_route.py': '46b100dc95f11e344c11b8cb3fba5d34d17b2884385923426a42246699fda43d', 'note10/device_test/note10_rootfs_snapshot.h': '9844788efebdcc5793bc0f50d9abc34ec0f396ac0e9431fb8f875aca604bfaf1', 'note10/device_test/sealed_affinity_artifact.cjs': '08c17edb82357d5719fbccd2427fca1970c09f6b3ee7aef91d6034f7d12f70ec', 'note10/device_test/test_v142_iva_native.py': '75def570efce26259ad451840df05e0d3a95eb3d671695e8be49cb47da041286', 'note10/device_test/test_v143_iva_timer.py': '4f10d8d433f03fd7bdf48bc1f3d159f72171770718977bbe2898db436603b230', 'note10/device_test/test_v144_iva_buffer.py': 'cd89349e83320de37a432e8dcea7d70e3218e6e96a4517b64b0faf3c5db753da', 'note10/device_test/test_v145_iva_sidecar.py': 'ccd2cc3af61f943df406480a822c742a1cf71d569ccb793220cfb85aa16cde05', 'note10/device_test/test_v146_iva_user_read.py': 'cc52c0d75892de88e171aa8aec2a9673b9c5c86deda00a4f0047597a96b823a6', 'note10/device_test/test_v147_iva_deinit.py': 'c459ac049ea36728c4bdcd11568a5446ae977395b28e4531161841be35bc0b9a', 'note10/device_test/test_v148_iva_init_pm.py': 'b25e5e2a71b6eebe338585b14efdce5e5e590f9f457343c100bcec3e1944331a', 'note10/device_test/test_v149_iva_init_state.py': 'e7348b501d3b225b2c90a388b4c362118a0927ed2e17a25b66ef6104de7e00e6', 'note10/device_test/test_v150_iva_mbox_register.py': 'bbbb548b9e3febe4660c5689ee5692a86b8f1e09b7f8711659d0597ce2ffd9d5', 'note10/device_test/test_v151_iva_mmap_deny.py': '16cd375f09e7fc160e3a610fd85bfc5a90b308ec03f66103092b16cfa76b31da', 'note10/device_test/test_v152_iva_fault_drain.py': 'dfa73f854bdd9dbbb3c0a019acea69acd960698fa8a9e0c08774c42e8043cc86', 'note10/device_test/test_v153_iommu_fault_register.py': 'b9c30a38ca5edaeb02dbe80eb016ace722a3a3559e5473a352983e9e731e45a3', 'note10/device_test/test_v154_linux_diagnostic.py': 'fff5f4608dab528c273341e90588671de733d60a145165d02a2cc1389e5dec19', 'note10/device_test/test_v155_linux_make_environment.py': '29f7e1a402f8b9fb7a7a73b16a44e985989dfacccc833cfb062ab788cceb9c44', 'note10/device_test/test_v190_last_complete_block_read.py': 'c306f792b0d19da9b82233c54f40a11d8089c963f2ece0757dae25b1fe32932d', 'note10/device_test/v130_archive.py': 'bc49ffef72f73769de77a55432253f57f14d20433933ac56570f0ebfc3a1bce4', 'note10/device_test/v130_contract.py': 'd3336dccb8edf2366d4cc8233cd83d18b27f4d65c7dd3a3627807ddd0858c929', 'note10/device_test/v130_slot.py': '07c05bc1507120ec8a184457a416e4b716283f54403967ff1c024e65a8563317', 'note10/device_test/v135_metadata.py': 'd631d04e6f7a4cf1f48e6aeae53be8ef7a48599f4badf08091391fde96e218a9', 'note10/device_test/v142_iva_native.py': '9497cec3143800a045557d3e2040a1afb0404bc41fa11f9c266a8b14cd269f08', 'note10/device_test/v143_iva_timer.inc': '730e2ab31cada507b7dd380d0a928aae502829b70b86a471d5b4010f626fb24d', 'note10/device_test/v143_iva_timer.py': 'cbd29b33ab47b4bd6fb92126a1c09c989767296a5d74329f886143a7e810a06a', 'note10/device_test/v144_iva_buffer.h': 'ca9bc9f95a4828b6c12895c3e15d4d0818a92b01699084842e3efb60b7f62d30', 'note10/device_test/v144_iva_buffer.py': 'b444b8f709b66c1f8f207ec1ec35c00372cd5046cb321afc1bcf613ed27d76ae', 'note10/device_test/v145_iva_sidecar.inc': '880e3a8f3a2c2e34adbc71faf3def748154db7eabf0d98270cec5c9be74f7377', 'note10/device_test/v145_iva_sidecar.py': '5792d1626ffc4aa2e00fb44b2332fb704d9451cf9390590e98af7822b03838fe', 'note10/device_test/v146_iva_user_read.py': '7b1d5e5d3b78e22d18801f5c3eae753ef3abb546de4d146629bb441fae844dc8', 'note10/device_test/v147_iva_deinit.py': 'e1155bf25728c651d7b56fae9501057c05a3981d75037f1a8568ac822497fac3', 'note10/device_test/v148_iva_init_pm.py': 'f62f03bf16846a2f7d0801558a9223946f85896655a0da6cab807ad86a63ecc0', 'note10/device_test/v149_iva_init_state.py': '43573487585fa5cab2926747f0833dff232acfc2efbbe842d98b3414d5abf876', 'note10/device_test/v150_iva_mbox_register.py': 'b10a752ff612ec64cbc79e5257cde1a7595cba092af7a1ed821bd33e7723e7c2', 'note10/device_test/v151_iva_mmap_deny.py': '6f0389cae219de419bd501a5e8dd1bfd675b699129870b2b9716ddd894357f0a', 'note10/device_test/v152_iva_fault_drain.py': 'b79c60b54f8405a1afd90ad68aefbfefd8d11fe92dc614dadd16524e7874235f', 'note10/device_test/v153_iommu_fault_register.py': '66ce02ac452a72d00282cd0bb2a6aa5995e4bd35315dace23cd4d78a248f07cc', 'note10/device_test/v154_linux_build.py': '8a282d960cb9dc52dad759876d05c0b4e905697f9851136458a774da192f5a8a', 'note10/device_test/v154_linux_cycle.py': 'a43282eb92923e2bcfe6cc50130e06591769ad9cb3af209a4aa4fd4299acce7a', 'note10/device_test/v154_linux_package.py': 'ca6c6e270d7baa04a8384fa371a105098e6bf55683ffb1d6dbe4d29dde81ad7e', 'note10/device_test/v154_linux_prepare.py': 'dfb5ee83861cef7f48eba31349a8fc9640928cff555471b88f35375ca4c17ada', 'note10/device_test/v154_linux_probe.c': 'b63f3d0fdedd4c267e3c4a2c2c0752e80c1d7b2b84b1f16274ace6649306fa4b', 'note10/device_test/v154_linux_return.c': '833f609cac2a84eee47c89cda12c5e523e592ae99f1b090bfea86bd5e53729a3', 'note10/device_test/v157_builtin_init_observation.inc': 'f9b97fa886ff303657b73b68276af4e31ee770fc0a6c8f1ff4392cbf4d675498', 'note10/device_test/v157_splice_observation.py': '212d3bb320767b54d686948c6d0974ffb1d389ed4a3a9f212ce12d7280bd3f34', 'note10/device_test/v159_rootfs_materialization.py': '2495fbdbf799b5686a603e1ae33116433f7ae6c885f41d250a14963d71173644', 'note10/device_test/v160_rootfs_relocation.py': 'dcd37fdf338eeb904aac1576b52ad381c97fbec7d6ab8eb683f35818826c24fe', 'note10/device_test/v161_initramfs_force.py': 'b9f6254bfb47c5cf4c453b0d92d1789d87c586746e38e9b0aef074b2673846d5', 'note10/device_test/v190_builtin_read.c': '75df8fb689158c1ca3f2e3e2f22a53683c21fa51788152f186504315ba797826', 'note10/xnu26/note10_iostorage_read_range.c': '12b9de8c5e7c59b0e2df4deec0e109043d53ee5f7dd45653ce899d0f17ae38a2', 'note10/xnu26/note10_iostorage_read_range.h': '61bd6d3741137139cbb00280334c763dbe85431483cbee8e31270c61361df2a3', 'note10/xnu26/note10_iostorage_read_request.c': '7b5fd68db13eb27ff35cf3f3f70fd9cda4cf76bc414867e8b802189efb6a6815', 'note10/xnu26/note10_iostorage_read_request.h': 'bedab328a94426f0409b3617d80746d3bf5ee76a03e2bcc2537808092f8d2f15'}


def require(ok,message):
    if not ok:raise ValueError(message)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def source_pins():
    pins=dict(RETAINED_PINS)
    for name,pin in pins.items():require(sha(p.ordinary(ROOT/name))==pin,'retained source changed: '+name)
    pins.update({'note10/device_test/'+name:sha(p.ordinary(HERE/name)) for name in PUBLIC_FILES})
    pins[WORKFLOW]=sha(p.ordinary(ROOT/WORKFLOW))
    return pins


def generic(init):
    require(64<=len(init)<=2097152 and init[:6]==b'\x7fELF\x02\x01' and init[18:20]==b'\xb7\0' and
            init.count(b'N10MININIT2:N210PREP')==1,'new static ARM64 prepare PID1 required')
    prefix=newc([('dev',0o040755,b'',0,0),('sys',0o040755,b'',0,0),('n10',0o040700,b'',0,0),
                 ('dev/console',0o020600,b'',5,1),('dev/kmsg',0o020600,b'',1,11),('init',0o100755,init,0,0)])
    prefix+=bytes(-len(prefix)%512)
    return prefix+bytes(SLOT_BYTES),len(prefix)


def private_member(descriptor,build,cycle):
    require(type(descriptor)is bytes and len(descriptor)==256 and descriptor[:8]==b'N209PAY1' and
            struct.unpack_from('<II',descriptor,8)==(1,256),'exact current209 descriptor required')
    p.hexid(build,32);p.hexid(cycle,32)
    binding=struct.pack('<8sII32s32s32s16s',b'N210BND1',1,128,build.encode(),cycle.encode(),hashlib.sha256(descriptor).digest(),bytes(16))
    member=newc([(name,0o100400,data,0,0) for name,data in (('n10/native-payload.bin',descriptor),('n10/binding.bin',binding))])
    require(len(member)<=SLOT_BYTES,'metadata-only slot exceeded')
    return member,binding


def insert(image,build,member,cycle):
    p.hexid(cycle,32)
    start,size,marker=(build[k] for k in ('slot_offset','slot_bytes','cycle_offset'))
    require(type(start)is type(size)is type(marker)is int and size==SLOT_BYTES and 64<=start<=len(image)-size and
            64<=marker and marker+33<=len(image) and not(start<=marker<start+size) and
            image[marker:marker+33]==p.CYCLE_MARKER+b'\0' and image.count(p.CYCLE_MARKER+b'\0')==1 and
            not any(image[start:start+size]) and 0<len(member)<=size and member.startswith(b'070701'),
            'exact disabled source-built slot/cycle required')
    changed=bytearray(image);changed[start:start+size]=member+bytes(size-len(member));changed[marker:marker+32]=cycle.encode()
    return bytes(changed)


def install(source,identity,buffers):
    # Install the unchanged stock-Linux driver/return base into a fresh tree only.
    result=p.install(source,identity,buffers)
    target=source/'init/initramfs.c';target.write_bytes(parser_helper.prepare(p.ordinary(target)))
    main=source/'arch/arm64/mm/init.c';raw=p.ordinary(main)
    anchor=b'void __init arm64_memblock_init(void)'
    require(raw.count(anchor)==raw.count(b'\tmemblock_allow_resize();')==1,'exact early memblock anchors required')
    includes=b'\n#ifdef CONFIG_NOTE10_V210_NATIVE_PREPARE\n#include "native_parcel_core.c"\n#include "native_prepare_core.c"\n#include "v210_native_prepare_kernel.c"\n#endif\n'
    raw=raw.replace(anchor,includes+anchor,1).replace(b'\tmemblock_allow_resize();',
        b'#ifdef CONFIG_NOTE10_V210_NATIVE_PREPARE\n    n210_early_reserve();\n#endif\n\tmemblock_allow_resize();',1);main.write_bytes(raw)
    for name in ('native_parcel_core.h','native_parcel_core.c','native_prepare_core.h','native_prepare_core.c','v210_native_prepare_kernel.c'):
        (main.parent/name).write_bytes(buffers['note10/device_test/'+name])
    # Return TU owns these real static identity/arm fields. Read-only accessor.
    target=source/'drivers/misc/v154_linux_return.c'
    target.write_bytes(p.ordinary(target)+b'\n#include "native_prepare_core.h"\nint n210_linux_context(struct n210_context *out)\n{\n    memset(out,0,sizeof(*out));\n    memcpy(out->build,N154_BUILD_ID,32);\n    memcpy(out->boot,n10_boot_id,32);\n    memcpy(out->cycle,(const void *)n10_cycle,32);\n    out->return_armed=READ_ONCE(n154_arm_result)==0;\n    return out->return_armed?0:-EAGAIN;\n}\n')
    for name in ('native_prepare_core.h','native_parcel_core.h'):(target.parent/name).write_bytes(buffers['note10/device_test/'+name])
    kconfig=source/'drivers/misc/Kconfig'
    kconfig.write_bytes(p.ordinary(kconfig)+b'\nconfig NOTE10_V210_NATIVE_PREPARE\n\tbool "Native descriptor preparation only"\n\tdepends on NOTE10_V154_LINUX_DIAGNOSTIC\n\tdefault n\n')
    result['new_overlay_paths']=['arch/arm64/mm/'+n for n in ('init.c','native_parcel_core.h','native_parcel_core.c','native_prepare_core.h','native_prepare_core.c','v210_native_prepare_kernel.c')]+['init/initramfs.c','drivers/misc/v154_linux_return.c','drivers/misc/native_prepare_core.h','drivers/misc/native_parcel_core.h','drivers/misc/Kconfig']
    result['new_overlay_sha256']={name:sha(p.ordinary(source/name)) for name in result['new_overlay_paths']}
    return result


def run_build(output,context,head):
    require(sys.platform=='linux' and context==dict(schema=CONTEXT_SCHEMA,source_head=head,source_sha256=source_pins(),new_fixture_PASS=context.get('new_fixture_PASS')),
            'exact source-bound new210 public context required')
    passed=context['new_fixture_PASS']
    require(set(passed)=={'schema','passed','groups','variants','assertions','result_sha256'} and passed['schema']=='note10-v210-native-prepare-fixture-result-v1' and
            passed['passed']is True and passed['groups']==6 and passed['variants']==16 and passed['assertions']==33,'new focused fixture PASS required')
    p.hexid(passed['result_sha256']);p.hexid(head,40)
    require(all(os.environ.get(k)==v for k,v in {'GITHUB_SHA':head,'GITHUB_WORKFLOW_SHA':head,'GITHUB_REPOSITORY':'eirblue/ios_note10p',
            'GITHUB_JOB':JOB,'GITHUB_RUN_ATTEMPT':'1'}.items()) and os.environ.get('GITHUB_WORKFLOW_REF','').startswith('eirblue/ios_note10p/'+WORKFLOW+'@'),'exact fresh CI dispatch required')
    out=Path(output).resolve();require(out==ROOT/'note10/private/v210-ci-native-prepare','fixed CI output required')
    work=out.with_name(out.name+'-work');archive=out.with_name(out.name+'-source.tar.gz')
    require(not any(x.exists() for x in (out,work,archive)),'fresh one-use producer required')
    out.mkdir(parents=True);identity=uuid.uuid4().hex
    result=dict(schema=BUILD_SCHEMA,version='v210',producer_revision='v210',passed=False,source_head=head,
                source_sha256=context['source_sha256'],public_input=context,build_evidence_id=identity,
                run_id=int(os.environ['GITHUB_RUN_ID']),run_attempt=1,full_Image_build_attempts=0,target_PID1_compile_links=0,
                old_tests_replayed=0,execution_slot_enabled=False,native_kernel_bytes_in_Image=0,native_adapter_bytes_in_Image=0,
                reservation_bytes=33554432,reservation_delta_vs208=33554432,stages={},**FALSE_CLAIMS)
    def persist():p.save(out/'result.json',result)
    def run(argv,label,timeout=600):
        result['stages'][label]=dict(argv=list(map(str,argv)),status='started');persist()
        with (out/(label+'.log')).open('xb') as log:done=house.run_command(argv,log,timeout)
        result['stages'][label].update(status='completed',returncode=done.returncode);persist()
        if not (out/(label+'.log')).stat().st_size:(out/(label+'.log')).write_bytes(b'completed\n')
        require(done.returncode==0,'producer stage failed: '+label)
    persist()
    try:
        for name in ('clang-14','gcc','make','aarch64-linux-gnu-gcc','arm-linux-gnueabi-gcc'):require(shutil.which(name)is not None,'required tool absent: '+name)
        archive_helper.acquire(archive)
        with archive.open('rb') as stream:archive_sha=hashlib.file_digest(stream,'sha256').hexdigest()
        require(archive.stat().st_size==p.ARCHIVE_BYTES and archive_sha==p.ARCHIVE_SHA,'exact stock source archive required')
        work.mkdir();source=archive_helper.extract(archive,work/'source');objects=work/'objects';objects.mkdir()
        buffers={name:p.ordinary(ROOT/name) for name in context['source_sha256']}
        result['preparation']=install(source,identity,buffers);persist()
        compile_sources=[HERE/n for n in ('v210_native_prepare_pid1.c','native_prepare_core.c','native_parcel_core.c')]
        result['target_PID1_compile_links']=1;persist()
        run(['aarch64-linux-gnu-gcc','-std=c11','-Os','-static','-fno-stack-protector','-Wall','-Wextra','-Werror',
             '-I',HERE,'-DN154_BUILD_ID="'+identity+'"',*compile_sources,'-o',out/'minimal-init.elf'],'01-pid1')
        init=p.ordinary(out/'minimal-init.elf',2097152);cpio,prefix=generic(init);(out/'initramfs.cpio').write_bytes(cpio)
        make=['make','-C',str(source),'O='+str(objects),'ARCH=arm64','CC=clang-14','CROSS_COMPILE=aarch64-linux-gnu-',
              'CLANG_TRIPLE=aarch64-linux-gnu-','CROSS_COMPILE_ARM32=arm-linux-gnueabi-','GCC_TOOLCHAIN_DIR=/usr/aarch64-linux-gnu/bin/',
              'HOSTCC=gcc','HOSTCFLAGS=-Wno-error=deprecated-declarations','KCFLAGS=-gdwarf-4']
        run([*make,p.DEFCONFIG],'02-defconfig')
        baseline=house.config_values(p.ordinary(objects/'.config'))
        require(baseline.get('NOTE10_V210_NATIVE_PREPARE','n')=='n','new profile must be default off')
        settings=dict(house.SETTINGS,NOTE10_V210_NATIVE_PREPARE='y',KEXEC='n',KEXEC_FILE='n',CRYPTO_SHA256='y',
                      CRYPTO_USER_API_HASH='y',INITRAMFS_SOURCE='"'+str(out/'initramfs.cpio')+'"',LOCALVERSION='"-v210-native-prepare"')
        edits=[]
        for key,value in settings.items():edits.extend(['--enable' if value=='y' else '--disable',key] if value in ('y','n') else ['--set-str',key,value[1:-1]] if value.startswith('"') else ['--set-val',key,value])
        run([source/'scripts/config','--file',objects/'.config',*edits],'03-settings');run([*make,'olddefconfig'],'04-config')
        config=p.ordinary(objects/'.config');values=house.config_values(config)
        for key,value in dict(p.REQUIRED_CONFIG,**settings).items():require(values.get(key,'n')==value,'effective setting differs: '+key)
        require(not any(key.startswith('NOTE10_') and value!='n' and key not in settings for key,value in values.items()),'unselected profile forbidden')
        (out/'actual-effective.config').write_bytes(config);result['effective_profile']=values
        result['cmdline_policy']=sys.modules['builtin_init_route'].builtin_cmdline_policy(config.decode())
        result['full_Image_build_attempts']=1;persist();run([*make,'V=1','-j4','Image'],'05-Image',5400)
        raw=p.ordinary(objects/'arch/arm64/boot/Image',p.IMAGE_LIMIT);symbols=p.ordinary(objects/'System.map',16777216).decode()
        result.update(house.check_image(raw,cpio,identity,symbols,b'N210PREP'))
        table={row[2]:int(row[0],16) for line in symbols.splitlines() if len(row:=line.split())==3 and row[2] in ('_text','_end')}
        require(set(table)=={'_text','_end'} and 0<table['_end']-table['_text']<=p.IMAGE_LIMIT,'measured linked extent cap')
        result['linked_end_minus_text']=table['_end']-table['_text']
        result['slot_offset']=result['initramfs_offset']+prefix;result['slot_bytes']=SLOT_BYTES
        require(not any(raw[result['slot_offset']:result['slot_offset']+SLOT_BYTES]),'generic private slot must stay zero')
        result['object_evidence']={}
        for name in ('arch/arm64/mm/init.o','drivers/misc/v154_linux_return.o','init/initramfs.o'):
            obj=p.ordinary(objects/name,67108864);cmdpath=Path(name).with_name('.'+Path(name).name+'.cmd');cmd=p.ordinary(objects/cmdpath)
            require(b'clang-14' in cmd and b'-DMODULE' not in cmd,'same Image builtin command required')
            result['object_evidence'][name]=dict(object_sha256=sha(obj),object_bytes=len(obj),command_sha256=sha(cmd))
        require(source_pins()==context['source_sha256'],'source changed during build')
        (out/'Image').write_bytes(raw);(out/'System.map').write_text(symbols)
        result.update(passed=True,PID1_sha256=sha(init),PID1_bytes=len(init),effective_config_sha256=sha(config),
                      native_make_target='Image',native_link_validation_status='linked-in-this-Image')
        persist()
    except BaseException as error:
        result.update(error_type=type(error).__name__,error=str(error)[:1024]);persist();raise
    return result


def seal(out,head):
    files=sorted(x for x in out.iterdir() if x.is_file());sizes={x.name:x.stat().st_size for x in files}
    result=json.loads((out/'result.json').read_bytes())
    require(set(sizes)<=set(SUCCESS_MEMBERS)-{'members.json'} and (result['passed']is not True or set(sizes)==set(SUCCESS_MEMBERS)-{'members.json'}),'exact producer members required')
    require(len(files)<=32 and all(not x.is_symlink() and 0<x.stat().st_size<=67108864 for x in files) and sum(sizes.values())<=134217728,'bounded producer evidence required')
    manifest=dict(schema=MANIFEST_SCHEMA,source_head=head,member_bytes=sizes,member_sha256={x.name:sha(p.ordinary(x,67108864)) for x in files},manifest_self_excluded=True)
    p.save(out/'members.json',manifest)
    with zipfile.ZipFile(out.with_suffix('.zip'),'x',compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in [*files,out/'members.json']:bundle.write(path,path.name)
    subprocess.run(['node',str(ROOT/'note10/device_test/sealed_affinity_artifact.cjs'),'seal',str(out.with_suffix('.zip')),
                    str(out.with_suffix('.n10sealed')),head],check=True,timeout=120)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--expected-source-head',required=True);parser.add_argument('--passed-new-test-context',required=True)
    args=parser.parse_args();house.recipient(os.environ['N10_RECIPIENT_PUBLIC_KEY_B64'])
    context=json.loads(base64.b64decode(args.passed_new_test_context,validate=True));require(len(json.dumps(context))<=65536,'bounded public context required')
    try:run_build(args.output,context,args.expected_source_head)
    finally:
        if args.output.is_dir():seal(args.output,args.expected_source_head)


if __name__=='__main__':main()
