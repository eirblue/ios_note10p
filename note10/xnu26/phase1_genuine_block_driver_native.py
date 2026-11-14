"""Closed default-off genuine storage family closure; no runtime caller."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
KEY='genuine_block_driver'
FRAMEWORK='BlockStorageDeviceDriverKit'
GENERATED='IOUserBlockStorageDevice.iig.cpp'
LOCK_EXPORTS={'_IOLockLock':'_lck_mtx_lock','_IOLockUnlock':'_lck_mtx_unlock'}
LOCK_SOURCE='osfmk/kern/lock_mtx.c'
LOCK_SHA='f9aaba2582d18925fa927cec86d31afa6ab23cc4a9e21339ce18b0470fb4c0e0'
EXPORT_SHA='a2b4b40b7559a37ccb0d29efb5972e30c9dda6a3e56eb57c9120c2a7a8eda76d'
SOURCES=('IOBlockStorageDriver.cpp','IOUserBlockStorageDevice_kext.cpp','IORequestsPool.cpp','IORequest.cpp')
PINS={'IOBlockStorageDriver.cpp': (118245, '2b592995cdd38f3c314940f6f85ac0b8f8523864332b9cd74ee6e9d7710b752e'), 'IOBlockStorageDriver.h': (59282, '61b9dee6666f0569d82089454e1cabb02e8beeabc3c1a1d8095d6757bd701bcd'), 'IOBlockStoragePerfControlExports.h': (1630, 'ee74993d98e760bdcc57e4b5b71f5d8c987e1d2978d8021038d14e26b0bee9e7'), 'IORequestsPool.h': (1536, '9b92f88c419615c2b8ca6e900f753be58355dfc3c07731ec8699c27a1133fb19'), 'IORequest.h': (2258, '89b821f46f07ba51cf706a73776ceca18f9dcbc0cc3b4d389ccceb58e6f50de8'), 'IOUserBlockStorageDevice_kext.h': (5495, '7fc745b48f9e83e453ab73a800926be918e212a187d248214a055ae8971d0d4f'), 'IOUserBlockStorageDevice_kext.cpp': (23321, 'bb593bb07f1c920e85f00598b1095d3492c159a4f75195de6907ec00288a1dc5'), 'IORequestsPool.cpp': (3020, 'b2bf3cd503aa57554e13cf79e2d2880b2af908c6ecc80a38f9accdfc5ba413f2'), 'IORequest.cpp': (3635, 'fd39eb863f42b27c33866a5b50884c9b0dc6a5b6e19e2a3b51cf15fb6dd2babe'), 'BlockStorageDeviceDriverKit/IOUserBlockStorageDevice.iig': (6150, '6c595e4170a2177404b1acbeefa0fa3c83d367720c2e2f7ae04fe55aca556bd0')}

def require(ok,message):
    if not ok:raise ValueError(message)

def digest(raw):return hashlib.sha256(raw).hexdigest()

def profile():return dict(schema='note10-v266-genuine-block-driver-profile-v1',commit='7edb88fbae296fb7c8ce2f64e115e116e566d51c',source_pins={k:dict(bytes=v[0],sha256=v[1])for k,v in PINS.items()},sources=list(SOURCES),generated=GENERATED,additional_units=5,storage_units=12,linked_units=1085,runtime_invoked=False)

def mode(value,factory):
    require(type(value)is type(factory)is bool and(not value or factory),'driver requires exact factory/native storage selection');return value

def enabled(current):
    from current_native_kernel import digest as context_digest
    producer,bindings=current['producer'],current['bindings']
    if KEY not in producer and KEY not in bindings:return False
    require(producer.get(KEY)==profile()and bindings.get(KEY)==context_digest(profile())and 'owned_ram_factory'in producer,'exact driver profile/source binding');return True

def storage_count(current):return 12 if enabled(current)else 7 if 'owned_ram_factory'in current['producer']else 6

def linked_count(current):return 1085 if enabled(current)else 1080 if 'owned_ram_factory'in current['producer']else 1078

def stage(archive,apple,commit):
    require(commit==profile()['commit'],'one exact existing family archive')
    for name,(size,sha)in PINS.items():
        member=archive.getmember('IOStorageFamily-'+commit+'/'+name);require(member.isfile()and member.size==size,'closed family source member')
        with archive.extractfile(member)as stream:raw=stream.read(size+1)
        require(len(raw)==size and digest(raw)==sha,'genuine unmodified family source')
        target=apple/name;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb')as out:out.write(raw)
    include=apple.parent/'public-sdk-objects/include/IOKit/storage'
    for name in ('IOBlockStorageDriver.h','IOBlockStoragePerfControlExports.h'):
        target=include/name;require(not target.exists(),'fresh selected genuine header');target.write_bytes((apple/name).read_bytes())

def iig_argv(tool,apple,source,sdk):
    root=apple/'generated';header=root/FRAMEWORK/'IOUserBlockStorageDevice.h';impl=root/FRAMEWORK/GENERATED
    kernel=sdk/'System/Library/Frameworks/Kernel.framework/Headers'
    return [str(tool),'--def',str(apple/FRAMEWORK/'IOUserBlockStorageDevice.iig'),'--header',str(header),'--impl',str(impl),'--framework-name',FRAMEWORK,'--','-I'+str(source/'iokit'),'-isystem',str(kernel),'-isystem',str(sdk/'usr/include'),'-isysroot',str(sdk),'-x','c++','-std=gnu++2b','-D__IIG=1','-DDRIVERKIT_PRIVATE=1','-DPRIVATE_WIFI_ONLY=1']

def unit_rows(apple,proof):
    require(proof['passed']is True and proof['IIG']['returncode']==0 and proof['IIG']['attempts']==1 and proof['IIG']['generated_impl_compiled']is True and re.fullmatch('[0-9a-f]{64}',proof['generated_sha256']),'actual official generated implementation proof')
    rows=[(apple/n,apple/(Path(n).stem+'.o'),PINS[n][1])for n in SOURCES]
    rows.append((apple/'generated'/FRAMEWORK/GENERATED,apple/'IOUserBlockStorageDevice.iig.o',proof['generated_sha256']))
    return rows

def compile_members(result,apple,storage_argv,source,sdk,require_object,*,runner=subprocess.run,diagnostic_sink=None):
    from phase1_iostorage_native_inputs import command
    require(storage_argv[-4:]==['-c',str(apple/'IOStorage.cpp'),'-o',str(apple/'IOStorage.o')],'actual native IOStorage command')
    proof=dict(profile=profile(),passed=False,units=[],IIG=dict(attempts=0,generated_impl_compiled=False));result['driver_compile']=proof
    def save():(apple/'driver-compile.json').write_text(json.dumps(proof,indent=2)+'\n')
    try:
        argv=iig_argv(command('xcrun','-f','iig'),apple,source,sdk);Path(argv[argv.index('--header')+1]).parent.mkdir(parents=True,exist_ok=False)
        proof['IIG'].update(attempts=1,argv=argv);save();call=runner(argv,capture_output=True,timeout=120);proof['IIG']['returncode']=call.returncode;(apple/'family-IIG.log').write_bytes(call.stdout+call.stderr)
        if diagnostic_sink:diagnostic_sink('family-IIG',call.returncode,call.stderr,False)
        if call.returncode:return False
        header=Path(argv[argv.index('--header')+1]);impl=Path(argv[argv.index('--impl')+1]);require(all(p.is_file()and not p.is_symlink()and 0<p.stat().st_size<=1048576 for p in (header,impl)),'bounded official generated source/header')
        proof.update(generated_sha256=digest(impl.read_bytes()),generated_header_sha256=digest(header.read_bytes()),generated_header_path=str(header),generated_source_path=str(impl))
        selected=[(apple/n,apple/(Path(n).stem+'.o'),PINS[n][1])for n in SOURCES]+[(impl,apple/'IOUserBlockStorageDevice.iig.o',proof['generated_sha256'])]
        for source_path,obj,expected in selected:
            require(digest(source_path.read_bytes())==expected,'exact family compile input')
            include=apple.parent/'public-sdk-objects/include'
            argv=[storage_argv[0],'-I',str(include),'-I',str(apple),'-I',str(apple/'generated'),'-I',str(header.parent),*storage_argv[1:-4],'-c',str(source_path),'-o',str(obj)]
            row=dict(source=str(source_path),source_sha256=expected,object_path=str(obj),argv=argv,passed=False);proof['units'].append(row);result['compile_attempts']+=1;result['target_object_compile_attempts']+=1;save()
            call=runner(argv,capture_output=True,timeout=120);row['returncode']=call.returncode;(apple/(obj.stem+'.compiler.log')).write_bytes(call.stdout+call.stderr)
            if diagnostic_sink:diagnostic_sink(source_path.name,call.returncode,call.stderr,False)
            if call.returncode:return False
            require_object(obj);row.update(passed=True,object_sha256=digest(obj.read_bytes()));result['compiled_arm64_objects']+=1
        proof['IIG']['generated_impl_compiled']=True;proof['passed']=True;return True
    except subprocess.TimeoutExpired as error:
        proof.update(error_type=type(error).__name__);(apple/'driver-timeout.log').write_bytes((error.stdout or b'')+(error.stderr or b''));raise
    finally:save()

def bind_origins(current,rows,defined,references,aliases,source_exports=None):
    require(enabled(current),'closed driver profile')
    own={r['source']:r for r in rows if r['source'].startswith(('@storage/','@storage-generated/'))and Path(r['source']).name in (*SOURCES,GENERATED)}
    expected={'@storage/'+n for n in SOURCES}|{'@storage-generated/'+GENERATED};require(set(own)==expected and sum(r['source']in expected for r in rows)==5,'exact five unique new current rows')
    report=current['storage']['proof']['driver_compile'];require(report['profile']==profile()and report['passed']is True and report['IIG']['attempts']==1 and report['IIG']['returncode']==0 and report['IIG']['generated_impl_compiled']is True,'actual compiler/IIG source authority')
    by_path={r['object_path']:r for r in rows};providers={};roots={};used_exports={}
    for name,row in own.items():
        require(row['passed']is True and row['category']=='storage'and row['producer_id']==current['producer_id']and row['input_binding']==current['input_binding'],'same-context genuine family row')
        if name.startswith('@storage/'):
            require(row['source_sha256']==PINS[Path(name).name][1],'genuine family source pin')
        else:require(row['source_sha256']==report['generated_sha256'],'exact generated IIG source pin')
        for symbol,users in references.items():
            if row['object_path']not in users:continue
            target_symbol=aliases.get(symbol,symbol);owners=defined.get(target_symbol,[]);require(len(owners)==1 and owners[0]in by_path,'new import requires unique genuine provider')
            target=by_path[owners[0]]
            if symbol in aliases:
                require(LOCK_EXPORTS.get(symbol)==target_symbol and source_exports is not None and source_exports.get('config/IOKit.exports')==EXPORT_SHA and target['source']==LOCK_SOURCE and target['source_sha256']==LOCK_SHA and target['category']=='native','only two original genuine lock export aliases')
                used_exports[symbol]=target_symbol
            require(target['passed']is True and target['category']in ('native','storage')and target['producer_id']==current['producer_id']and target['input_binding']==current['input_binding'],'genuine same-context provider')
            providers[symbol]={k:target[k]for k in ('source','source_sha256','object_sha256','category')}
    for cls,unit in (('IOBlockStorageDriver','IOBlockStorageDriver.cpp'),('IOUserBlockStorageDevice','IOUserBlockStorageDevice_kext.cpp')):
        row=own['@storage/'+unit];names=[n for n,owners in defined.items()if cls+'10gMetaClassE'in n and owners==[row['object_path']]];require(len(names)==1 and names[0]not in aliases,'real class retention definition');roots[cls]=names[0]
    return dict(profile=profile(),rows={n:{k:v[k]for k in ('source','source_sha256','object_path','object_sha256','category')}for n,v in own.items()},providers=providers,roots=roots,retained_lock_exports=used_exports,object_provenance_verified=True,runtime_invoked=False,passed=False)

def verify(current,storage,proof):
    require(enabled(current)and proof['profile']==profile()and proof['passed']is proof['object_provenance_verified']is True and proof['runtime_invoked']is False and proof['retained_lock_export_addresses_verified']is True,'genuine retained inert driver proof')
    report=storage['binding']['proof']['driver_compile'];require(report['profile']==profile()and report['passed']is True and report['IIG']['attempts']==1 and report['IIG']['returncode']==0 and report['IIG']['generated_impl_compiled']is True and len(report['units'])==5,'one official IIG plus five actual compiles')
    actual={row['source']:row for row in storage['units']if row['source']in proof['rows']};require(len(actual)==5,'five actual retained driver rows')
    for name,row in actual.items():
        require(proof['rows'][name]=={k:row[k]for k in ('source','source_sha256','object_path','object_sha256','category')},'exact driver receipt join')


def final_symbols(text,proof):
    addresses={}
    for line in text.splitlines():
        row=line.split()
        if len(row)>=3 and re.fullmatch('[0-9a-fA-F]+',row[0]):addresses.setdefault(row[-1],[]).append(int(row[0],16))
    require(all(len(addresses.get(n,[]))==1 for n in proof['roots'].values()),'two genuine retained class definitions')
    for name,target in proof['retained_lock_exports'].items():require(len(addresses.get(name,[]))==1 and addresses[name]==addresses.get(target),'same-run original lock export/target addresses')
    proof.update(passed=True,retained_lock_export_addresses_verified=True)
