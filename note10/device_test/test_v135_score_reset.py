"""One bundled NEW EVT1 reset, host budget, baseline and public codec batch."""
import argparse,base64,hashlib,json,re,subprocess,sys,zlib
from pathlib import Path
sys.dont_write_bytecode=True
from v130_contract import ROOT,private,ordinary,sha,digest,read,save
import v135_prepare as prepare
import v135_cycle as cycle
import v135_package as package
from v135_metadata import encode_public,decode_public,PREFIX,MAX_JSON,MAX_COMPRESSED
from v135_build import SETTINGS,NEW_FILES,SCOPE,RETAINED_COMMIT,RETAINED_SOURCE_SHA256,RETAINED_CONTEXT_SHA256,source_pins,continuation,retained_continuation
FIXTURE_SHA='5ce56a478d128e1db99553d46418617437e8499ded08ddea9df5f621af0c27fb'
HERE=Path(__file__).resolve().parent


def replace_function(text,name,replacement,expected=1):
    pattern=re.compile(r'(?m)^(?:static )?(?:int|void|u32) '+re.escape(name)+r'\([^)]*\)\s*\{')
    matches=list(pattern.finditer(text))
    if len(matches)!=expected:raise ValueError('retained fixture function boundary differs: '+name)
    for match in reversed(matches):
        at=match.end();depth=1
        while depth:
            if at>=len(text):raise ValueError('retained function closing boundary missing')
            depth+=(text[at]=='{')-(text[at]=='}');at+=1
        text=text[:match.start()]+replacement+text[at:]
    return text


def fixture(raw,regs):
    if digest(raw)!=FIXTURE_SHA:raise ValueError('exact accepted133 fixture scaffold required')
    text=raw.decode('utf-8')
    definitions=[line for line in regs.decode().splitlines() if re.match(r'#define\s+SW_RESET\s',line)]
    if len(definitions)!=1:raise ValueError('native SW_RESET definition differs')
    text=text.replace('#include <stdint.h>','#include <stdint.h>\n'+definitions[0]+'\nstatic int reset_busy_samples,reset_stuck,reset_reads;')
    text=replace_function(text,'n133_score_hardware_stop','#include "v135_score_reset.inc"',expected=2)
    text=text.replace('stage="score-halt";','stage="score-reset";')
    text=text.replace('N10XNU133','N10XNU135')
    text=replace_function(text,'writel',r'''static void writel(u32 value,void *p)
{uintptr_t off=(uintptr_t)p-(uintptr_t)score.system.sfr;assert(powered && clocks[0].enabled && clocks[1].enabled && irq_syncs && score.system.cache_slock.held);assert(value==1 && off==SW_RESET);writes++;}
''')
    text=replace_function(text,'readl',r'''static u32 readl(void *p)
{uintptr_t off=(uintptr_t)p-(uintptr_t)score.system.sfr;assert(powered && clocks[0].enabled && clocks[1].enabled && irq_syncs && score.system.cache_slock.held);mmio_reads++;
 if(off==SW_RESET){reset_reads++;if(reset_stuck)return 7;if(reset_busy_samples){reset_busy_samples--;return 1;}return 0;}
 assert(off==DMA0_QUEUE_STATUS || off==DMA1_QUEUE_STATUS || off==DMA2_QUEUE_STATUS || off==DMA3_QUEUE_STATUS);return registers[off/4];}
''')
    start=text.index('int main(void)\n{')
    text=text[:start]+r'''
static void fresh135(void){fresh();reset_busy_samples=reset_stuck=reset_reads=0;}
int main(void)
{
 unsigned int index;const unsigned int dma[]={DMA0_QUEUE_STATUS,DMA1_QUEUE_STATUS,DMA2_QUEUE_STATUS,DMA3_QUEUE_STATUS};
 fresh135();registers[TS_CACHE_STATUS/4]=5;registers[TS_INTR_ENABLE/4]=0x23ff;
 n133_score_shutdown(&pdev);assert(!score.n133_shutdown_result && !n131_dma_status(score.dev));
 assert(reset_reads==1 && mmio_reads==5 && writes==1 && !delays && clock_disables==2 && pm_gets==1 && pm_disabled==1);
 {int reads=mmio_reads;assert(!n133_score_prepare() && mmio_reads==reads);}
 fresh135();reset_busy_samples=2;n133_score_shutdown(&pdev);assert(!score.n133_shutdown_result && reset_reads==3 && mmio_reads==7 && delays==2 && writes==1);
 fresh135();reset_stuck=1;n133_score_shutdown(&pdev);denied(-ETIMEDOUT);
 assert(reset_reads==CHECK_RETRY_COUNT && mmio_reads==CHECK_RETRY_COUNT && delays==CHECK_RETRY_COUNT && writes==1 && clock_disables==2);
 assert(!strcmp(last_reason,"reset-ack") && last_state==7 && last_value==CHECK_RETRY_COUNT && last_aux==SW_RESET);
 for(index=0;index<4;index++){
  fresh135();registers[dma[index]/4]=0x1001;n133_score_shutdown(&pdev);denied(-ETIMEDOUT);
  assert(reset_reads==1 && mmio_reads==1+(int)index+CHECK_RETRY_COUNT && writes==1 && clock_disables==2);
  assert(!strcmp(last_reason,"dma-busy") && last_item==index && last_state==0x1001 && last_aux==dma[index]);
 }
 for(index=1;index<=2;index++){fresh135();foreign_gate=index;n133_score_shutdown(&pdev);denied(-EBUSY);assert(writes==1 && clock_disables==2);}
 fresh135();score.n133_ever_opened=true;n133_score_shutdown(&pdev);denied(-EBUSY);assert(!writes && !pm_gets);
 fresh135();score.system.n133_ever_booted=true;n133_score_shutdown(&pdev);denied(-EBUSY);assert(!writes && !pm_gets);
 fresh135();n130_arm_state=1;n133_score_shutdown(&pdev);assert(!writes && !pm_gets);
 puts("NEW EVT1 reset provider PASS");return 0;
}
'''
    return text


def reject(call):
    try:call()
    except (ValueError,TimeoutError,subprocess.TimeoutExpired):return
    raise AssertionError('new failclosed branch did not reject')


def host_cases(result):
    prepare.profile(SETTINGS)
    for key in ('SOC_EXYNOS9820_EVT0','EXYNOS_SCORE_V2','EXYNOS_SCORE_FPGA'):
        reject(lambda key=key:prepare.profile(dict(SETTINGS,**{key:'y'})))
    reject(lambda:prepare.profile(dict(SETTINGS,SOC_EXYNOS9820='n')))
    loader=(HERE/'v130_loader.c').read_bytes().replace(b'N10XNU130',b'N10XNU135')
    build=(HERE/'v135_build.py').read_bytes();consumer=(HERE/'v135_cycle.py').read_bytes()
    assert b".replace(b'N10XNU130',b'N10XNU135')" in build and b'N10XNU135 id=%s cycle=%.32s stage=%s' in loader and b"prefix='N10XNU135 id='" in consumer
    renderer=(HERE/'v135_prepare.py').read_bytes()
    assert b'#include "v135_score_reset.inc"' in renderer and b".replace(b'N10XNU133',b'N10XNU135')" in renderer
    identity,cycle_id='a'*32,'b'*32
    begin='N10XNU135 id='+identity+' cycle='+cycle_id+' stage=begin\n'
    native='N10XNU135 id='+identity+' '
    proof=native+'stage=score-reset errno=-110 owner=synthetic-score\n'+native+'final_qualified=1 EL1_preserved=1 actual_XNU_pending=1\n'
    clean=cycle.decode({'synthetic':(begin+proof).encode()},identity,cycle_id)
    assert clean['previous_boot_build_cycle_observed'] and clean['gate_refusals'][0]['stage']=='score-reset'
    for barrier in (begin.replace('N10XNU135','N10XNU132'),begin.replace(identity,'c'*32),
                    begin.replace(cycle_id,'d'*32),begin.replace(identity,'not-hex'),
                    begin.replace('begin\n','begin JUNK\n'),
                    begin.replace('N10XNU135','N10XNU999').replace('begin\n','begin JUNK\n')):
        refused=cycle.decode({'synthetic':(begin+barrier+proof).encode()},identity,cycle_id)
        assert not refused['previous_boot_build_cycle_observed'] and not refused['gate_refusals'] and not refused['final_hook_qualified_observed']
        assert refused['internal_kexec_load_attempts_observed'] is None
    earlier=begin.replace(cycle_id,'d'*32)+native+'fresh_owned32M platform_ready=1 xnu_pending=1\n'
    assert not cycle.decode({'synthetic':(earlier+begin).encode()},identity,cycle_id)['reservation_ready_observed']
    result['new_consumer_boundary_cases']='clean135, foreign version/identity/cycle, malformed identity, dirty suffix, dirty foreign producer, no prior-section reservation reuse'
    original_call=cycle.NativeAdb.call;original_clock=cycle.time.monotonic;seen=[]
    try:
        cycle.NativeAdb.call=lambda self,*args,timeout=30:seen.append(timeout) or b''
        cycle.time.monotonic=lambda:100
        adb=cycle.Adb('synthetic-adb','synthetic-serial');adb.return_deadline=200
        adb.call('shell','sha256sum','synthetic-node',timeout=30);assert seen==[30]
        adb.return_deadline=108;adb.call('shell','sha256sum','synthetic-node');assert seen[-1]==8
        adb.return_deadline=99;reject(lambda:adb.call('shell','id','-u'))
        adb.deadline=200;reject(lambda:adb.call('shell','id','-u'))
    finally:cycle.NativeAdb.call=original_call;cycle.time.monotonic=original_clock
    old='00000000-0000-0000-0000-000000000001';new='00000000-0000-0000-0000-000000000002'
    class Fake:
        return_deadline=None
        def __init__(self,ready=True):self.now=0;self.calls=0;self.ready=ready
        def text(self,*args):
            self.calls+=1
            return ('3.7' if self.ready else '') if args[1]=='getprop' else new
        def sleep(self,value):self.now+=value
    fake=Fake();preflights=[]
    def preflight(adb,pkg,boot,*,check_battery):preflights.append(check_battery);return new
    assert cycle.wait_return(fake,{},'synthetic',old,20,clock=lambda:fake.now,sleep=fake.sleep,preflight_fn=preflight)==new and preflights==[False] and fake.return_deadline is None
    fake=Fake(False);reject(lambda:cycle.wait_return(fake,{},'synthetic',old,6,clock=lambda:fake.now,sleep=fake.sleep,preflight_fn=preflight));assert fake.now==6 and preflights==[False]
    fake=Fake();failures=[]
    def bad_preflight(*args,**kwargs):failures.append(1);raise ValueError('synthetic integrity failure')
    reject(lambda:cycle.wait_return(fake,{},'synthetic',old,20,clock=lambda:fake.now,sleep=fake.sleep,preflight_fn=bad_preflight));assert failures==[1] and fake.return_deadline is None
    result['host_budget_cases']='30s hash probe, remaining budget, expiry, inherited clamp refusal, lightweight polling, one hash phase, no integrity retry'
    current=dict(schema='note10-v133-private-xnu-package-v1',version='v133',cycle='a'*32,build_evidence_id='b'*32,diagnostic_BOOT_sha256='1'*64,rollback_BOOT_sha256='2'*64,bootloader='synthetic')
    rows=[dict(partition=n,file=n+'.img',block_node='/dev/block/sda'+str(i+1),size=4096,sha256=('2' if n=='boot' else '3')*64,remote_hash_before_and_after_match=True) for i,n in enumerate(('boot','recovery','dtb','dtbo','vbmeta'))]
    current['partitions']=rows
    current['source_sha256']=RETAINED_SOURCE_SHA256
    ledger=dict(schema='note10-v133-owned-XNU-ledger-v1',status='failed-spent-no-retry',recovery_returned=False,cycle='a'*32,build_evidence_id='b'*32,host_BOOT_write_attempts=1,host_reboot_attempts=1,old_recovery_boot_id=old)
    ack=dict(schema='note10-v133-user-two-manual-restarts-v1',user_reported_manual_reboots=2,additional_adb_reboot_will_not_be_executed=True,no_inference_about_native_XNU_attempt_counts=True)
    receipt=dict(schema='note10-v133-post-manual-restarts-readonly-receipt-v1',status='post-manual-restarts-readonly-collected',fresh_return_confirmed=True,safe_non_BOOT_partitions_match=True,original_ledger_unchanged=True,readonly_only=True,new_manual_restarts_ack_sha256='4'*64,observation_sha256='5'*64,current_BOOT_sha256='1'*64,preflight_invocations=1,collect_invocations=1,host_BOOT_writes=0,host_reboots=0,partition_mutations=0,cycle='a'*32,build_evidence_id='b'*32,new_recovery_boot_id=new,prior_manual_recovery_boot_id=old)
    receipt.update(source_commit=RETAINED_COMMIT,source_map_sha256=digest(json.dumps(RETAINED_SOURCE_SHA256,sort_keys=True,separators=(',',':')).encode()))
    observation=dict(schema='note10-v133-owned-XNU-observation-v1',cycle='a'*32,build_evidence_id='b'*32)
    backup=dict(complete=True,partition_writes=False,partitions=rows,bootloader='synthetic')
    def baseline(l=ledger,a=ack,rc=receipt,o=observation):return package.current_and_restore(current,l,backup,a,rc,o,ack_sha='4'*64,observation_sha='5'*64)
    assert baseline()[0]=='1'*64
    reject(lambda:baseline(l=dict(ledger,recovery_returned=True)))
    reject(lambda:baseline(rc=dict(receipt,current_BOOT_sha256='6'*64)))
    reject(lambda:baseline(rc=dict(receipt,host_reboots=1)))
    reject(lambda:baseline(rc=dict(receipt,new_recovery_boot_id=old)))
    reject(lambda:baseline(o=dict(observation,cycle='c'*32)))
    assert ledger['recovery_returned'] is False
    result['manual_baseline_cases']='separate failed ledger/manual ack/current-integrity proof; promotion, identity, replay and stale UUID refused'
    public={'schema':'synthetic','data':'x'*60000};encoded=encode_public(public);assert len(encoded)<65535 and decode_public(encoded)==public
    reject(lambda:decode_public('e30='));reject(lambda:decode_public(encoded[:-4]))
    def envelope(raw):return PREFIX+base64.b64encode(raw).decode('ascii')
    packed=zlib.compress(b'{}')
    reject(lambda:decode_public(envelope(packed+packed)))
    reject(lambda:decode_public(envelope(zlib.compress(b'x'*(MAX_JSON+1)))))
    reject(lambda:decode_public(envelope(b'x'*(MAX_COMPRESSED+1))))
    reject(lambda:decode_public(envelope(zlib.compress(b'not JSON'))))
    reject(lambda:decode_public(envelope(zlib.compress(b'\xff'))))
    result['public_codec_cases']='bounded public-only zlib roundtrip, old envelope/truncation/trailing member/size/UTF8/JSON refusal'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('output','cc','retained-fixture','retained-context','stock-score'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--retained-context-sha256',required=True);args=parser.parse_args()
    out=private(args.output)
    if out.exists():parser.error('fresh135 NEW-only output required')
    fixture_path=ordinary(args.retained_fixture);prior_path=ordinary(args.retained_context)
    if sha(prior_path)!=args.retained_context_sha256:raise ValueError('retained133 public context file pin differs')
    prior=read(prior_path);retained_continuation(prior,RETAINED_SOURCE_SHA256)
    if digest(json.dumps(prior,sort_keys=True,separators=(',',':')).encode())!=RETAINED_CONTEXT_SHA256:raise ValueError('immutable133 public PASS differs')
    stock=ordinary(args.stock_score/'hardware/v3/score_regs.h');makefile=ordinary(args.stock_score/'Makefile')
    if sha(stock)!=prepare.PINS['drivers/vision/score/hardware/v3/score_regs.h'] or sha(makefile)!=prepare.PINS['drivers/vision/score/Makefile']:raise ValueError('actual native register/branch source pin differs')
    native_make=makefile.read_bytes();assert b'ifeq ($(CONFIG_SOC_EXYNOS9820_EVT0),y)' in native_make and b'ccflags-$(CONFIG_SOC_EXYNOS9820)\t+= -DSCORE_EVT1' in native_make
    prepare.profile(SETTINGS);current=source_pins();out.mkdir(parents=True)
    result=dict(schema='note10-v135-score-reset-result-v1',scope=SCOPE,passed=False,compiler_invocations=0,fixture_processes=0,old_tests_replayed=0,source_sha256={name:current[name] for name in NEW_FILES},retained_fixture_sha256=FIXTURE_SHA,device_operations=[],raw_kernel_reads=0,adapter_reads=0,compressions=0,Image_reads=0)
    try:
        host_cases(result)
        generated=fixture(fixture_path.read_bytes(),stock.read_bytes());source=out/'new-score-reset.c';source.write_bytes(generated.encode())
        executable=out/('new-score-reset.exe' if sys.platform=='win32' else 'new-score-reset')
        macros=['-DCONFIG_'+name+'=1' for name,value in SETTINGS.items() if value=='y']
        command=[str(ordinary(args.cc)),'-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-unused-function','-DSCORE_EVT1=1',*macros,'-I',str(HERE),str(source),'-o',str(executable)]
        result['compiler_invocations']=1
        with (out/'compile.log').open('wb') as log:subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=60)
        result['fixture_processes']=1
        with (out/'fixture.log').open('wb') as log:subprocess.run([str(executable)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=15)
        result['passed']=True
        result_raw=(json.dumps(result,indent=2)+'\n').encode()
        delta=dict(schema='note10-v135-score-ts-reset-pass-v1',scope=SCOPE,passed=True,result_sha256=digest(result_raw),source_sha256=result['source_sha256'])
        candidate=dict(schema='note10-v135-public-score-reset-continuation-v1',scope=SCOPE,passed=True,retained_source_commit=RETAINED_COMMIT,retained_score_terminal_PASS=prior,delta_NEW_PASS=delta,source_sha256=current)
        continuation(candidate,current);encoded=encode_public(candidate)
        (out/'result.json').write_bytes(result_raw);save(out/'public-score-reset-continuation.json',candidate)
        (out/'public-score-reset-continuation.txt').write_text(encoded+'\n',encoding='ascii',newline='\n')
    except BaseException:
        import traceback
        result.update(passed=False,error=traceback.format_exc())
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n');raise
    print(json.dumps({'passed':True,'compiler_invocations':1,'fixture_processes':1,'old_tests_replayed':0}))


if __name__=='__main__':main()
