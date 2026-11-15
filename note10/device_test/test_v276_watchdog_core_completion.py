"""One actual-C lifecycle batch plus three new hook/protocol/cross-TU predicates."""
import copy,hashlib,json,subprocess
from pathlib import Path
CASES=('deferred','immediate','sample-commit','failure-remove','duplicate','identity','completion-overlay','core-frame-schema','cross-TU-domain')

def reject(call):
    try:call()
    except (ValueError,KeyError):return True
    return False

def synthetic(p):
    source='/synthetic/source/drivers/watchdog/watchdog_core.c';target=p.CORE_TARGET
    command=('cmd_'+target+' := clang-14 -fstack-usage -fno-strict-aliasing -o '+target+' -c '+source+'\nsource_'+target+' := '+source+'\n')
    usage=source+':1:1:'+p.CORE_CALLER+'\t16\tstatic\n'
    elf=' [ 1] .text PROGBITS 00000000 000040 000014 00 AX 0 0 4\n 1: 0000000000000000 20 FUNC LOCAL DEFAULT 1 '+p.CORE_CALLER+'\n'
    item=dict(command=command,command_sha256=p.sha(command.encode()),stack_usage=usage,stack_sha256=p.sha(usage.encode()),stack_relative='drivers/watchdog/watchdog_core.su',elf_sections_and_symbols=elf,elf_evidence_sha256=p.sha(elf.encode()))
    table={p.CORE_CALLER:[dict(kind='t',address=0x1000,bytes=20,ordinal=1)]};nodes={};helper=None
    for i,name in enumerate(p.ROOTS):
        address=0x2000+i*0x100;table[name]=[dict(kind='T'if name=='n276_core_registered'else't',address=address,bytes=4,ordinal=10+i)]
        symbol=dict(symbol=name,address=address,bytes=4,aliases=[name]);key=format(address,'016x')+':4';nodes[key]=dict(proof=dict(symbol=symbol),selected_local_peak_bytes=0)
        if name=='n276_core_registered':helper=dict(linked_address=address,bytes=4)
    driver=dict(nodes=nodes,selected_extents=7,outlined_extents=0)
    body='0000000000001000 <'+p.CORE_CALLER+'>:\n 1000: a9bf7bfd stp x29, x30, [sp, #-16]!\n 1004: 910003fd mov x29, sp\n 1008: 94000000 bl '+format(helper['linked_address'],'x')+'\n 100c: a8c17bfd ldp x29, x30, [sp], #16\n 1010: d65f03c0 ret\n'
    return item,table,body,helper,driver

def run(output,producer,parameters):
    p=producer;out=Path(output);here=Path(__file__).resolve().parent;done=[]
    def save(name,value):(out/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    try:
        stage=out/'staged-source';(stage/'linux').mkdir(parents=True)
        (stage/'linux/v276_watchdog_binding.h').write_bytes((here/'v276_watchdog_binding.h').read_bytes())
        argv=parameters['compiler_argv'];save('COMPILE-STARTED.json',dict(attempt=1,argv=argv))
        with(out/'compiler.stdout').open('xb')as stdout,(out/'compiler.stderr').open('xb')as stderr:compiled=subprocess.run(argv,cwd=out,stdout=stdout,stderr=stderr,timeout=120)
        if compiled.returncode:raise ValueError('new276 C compile failed')
        exe=out/'watchdog-core-completion-fixture.exe';save('C-FIXTURE-STARTED.json',dict(attempt=1,argv=[str(exe)]))
        with(out/'fixture.stdout').open('xb')as stdout,(out/'fixture.stderr').open('xb')as stderr:called=subprocess.run([str(exe)],cwd=out,stdout=stdout,stderr=stderr,timeout=60)
        lines=(out/'fixture.stdout').read_bytes().replace(b'\r\n',b'\n').splitlines()
        for i,name in enumerate(CASES[:6]):
            if len(lines)<=i or lines[i]!=('N276CASE '+name+'=PASS').encode():raise ValueError('new276 C predicate '+name)
            done.append(name)
        if called.returncode or len(lines)!=6:raise ValueError('foreign276 fixture output')
        def pinned(name):
            pin=parameters[name];raw=Path(pin['path']).read_bytes()
            if len(raw)!=pin['bytes']or p.sha(raw)!=pin['sha256']:raise ValueError('new276 pinned source '+name)
            return raw
        old_driver=pinned('driver_source');old_core=pinned('core_source');driver=p.transform_binding(p.TARGET[:-2]+'.c',old_driver);core=p.transform_core(old_core)
        seam=p.GUARD+b'\tn276_core_registered(wdd);\n#endif\n';include=p.GUARD+b'#include <linux/v276_watchdog_binding.h>\n#endif\n'
        if core.count(seam)!=1 or core.replace(seam,b'',1).replace(include,b'',1)!=old_core or core.index(seam)<core.index(b'static int __watchdog_register_device')or core.index(seam)>core.index(b'int watchdog_register_device('):raise ValueError('new276 success-only core seam')
        prior=p.retained._ENV['transform_binding'](p.TARGET[:-2]+'.c',old_driver)
        undo=driver.replace(b'#include "v276_watchdog_driver.inc"',b'#include "v270_watchdog_driver.inc"',1).replace(b'\tif (n269_token == 1) n269_remove(wdt);\n',b'',1)
        if undo!=prior or not driver.index(b'n269_begin();')<driver.index(b's3c_wdt[cluster_index] = wdt;')or not driver.index(b' err:')<driver.index(b'if (n269_token == 1) n269_remove(wdt);')<driver.index(b'\treturn ret;',driver.index(b' err:')):raise ValueError('new276 token-gated failure seam')
        done.append(CASES[6]);identity=dict(id='a'*32,boot='b'*32,cycle='c'*32)
        def report(schema=2,state=2,flags=63,dog=7):return 'N276WDT '+' '.join(k+'='+v for k,v in identity.items())+f' result=0 schema={schema} state={state} error=0 cluster=0 variant=1 flags={flags} watchdog_id={dog} probe_cached_rate_hz=26000000 reserved=0 post_shutdown=0 armed=0 autonomous_return=0 XNU=0'
        observed=p.decode_binding([report()],identity)
        if not observed['qualified']or observed['watchdog_id_semantics']!='successful-core-registration'or p.decode_binding([report(flags=59,dog=4294967295)],identity)['qualified']or p.decode_binding([report(state=1)],identity)['qualified']or not reject(lambda:p.decode_binding([report(schema=1)],identity))or not reject(lambda:p.decode_binding([report().replace('a'*32,'d'*32)],identity)):raise ValueError('new276 strict core-registration frame')
        done.append(CASES[7]);item,table,raw,helper,graph=synthetic(p);proof=p.core_certificate(item,table,raw,helper,graph);aggregate=p.aggregate_extents(graph,proof['symbol']);bad=copy.deepcopy(item);bad['elf_sections_and_symbols']=bad['elf_sections_and_symbols'].replace('FUNC LOCAL','FUNC GLOBAL');bad['elf_evidence_sha256']=p.sha(bad['elf_sections_and_symbols'].encode())
        too_many=copy.deepcopy(graph)
        for i in range(31):
            address=0x4000+4*i;too_many['nodes'][format(address,'016x')+':4']=dict(proof=dict(symbol=dict(symbol='OUTLINED_FUNCTION_'+str(i),address=address,bytes=4)),selected_local_peak_bytes=0)
        too_many.update(selected_extents=38,outlined_extents=31)
        if not(aggregate['total']==8 and proof['notification_local_peak_bytes']==16 and proof['other_core_callee_peaks_included']is False and reject(lambda:p.core_provenance(bad,table))and reject(lambda:p.core_certificate(item,table,raw.replace('bl 2600','bl 2604'),helper,graph))and reject(lambda:p.aggregate_extents(too_many,proof['symbol']))and p.driver_provenance.__globals__['ROOTS']==p.ROOTS and len(p.ROOTS)==7 and len(p.own_frame.__globals__['ROOTS'])==8 and p.scoped_closure.__globals__['classify_edge']is p.classify_edge and p.scoped_closure.__globals__['own_frame']is p.own_frame and p._driver_collect.__globals__['scoped_closure']is p.scoped_closure and p._ENV['collect_binding']is p.collect_binding and p.BOUNDARIES is p.retained.BOUNDARIES and p.retained._WATCHDOG['ROOTS']!=p.ROOTS):raise ValueError('new276 fixed cross-TU/aggregate/namespace predicate')
        save('CORE-SYNTHETIC.json',dict(certificate=proof,aggregate=aggregate));done.append(CASES[8])
    except BaseException as error:
        error.fixture_progress=dict(groups=1,variants=9,assertions=len(done),planned_assertions=9,completed_variants=len(done),completed_assertions=len(done),case_names=done);raise
    return dict(groups=1,variants=9,assertions=9,completed_variants=9,completed_assertions=9,case_names=done,host_compile_attempts=1,host_fixture_process_attempts=1,old_tests_replayed=0)
