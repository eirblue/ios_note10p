"""Typed native terminal witnesses over immutable135; no clock-OFF inference."""
from pathlib import Path
import re
import v135_prepare as retained
HERE=Path(__file__).resolve().parent
PINS=dict(retained.PINS)
PINS.update({'drivers/soc/samsung/cal-if/cal-if.c': 'a7966aab1e72fb4aca212cd788ae1e9e172354d87c6079c5465c1fe27420f53a', 'drivers/vision/npu/npu-device.c': '1c117b3f94a4bd17144fddbfab3da38e62d49376e9703a9a878cc13ce1c5f914', 'drivers/vision/npu/npu-system.c': '84b5c6630cb255b9373fcd863916378766d6a7e4154c47f3a9b68bff53c287ac', 'drivers/vision/npu/npu-protodrv.c': 'db26d10e73f05056b08d9705cc60f461061305828203310621269be3f6b0f7f1', 'drivers/vision/npu/npu-vertex.c': '6d06d3559e8f072d9a489b0a8a3dde61d66194bb49daf338aac1ee8a5dd919b9', 'drivers/vision/npu/npu-log.c': '019e912a913151e422ef942982cad911d939ef7a40721529d6fd2c261906175e', 'drivers/vision/npu/npu-profile.c': '56e3762b3516d0fd002ac814a8343fd3b7b2253cefb4b435e7ee793b71e80a5d', 'drivers/vision/npu/npu-qos.c': '6cd2ea7583103cff1bbf48c2e72dc89146e384e825ce11b1b8c37148688c2d9f', 'drivers/vision/npu/npu-ver.c': 'e876b4637fb0f44705507aead7ae8a19fa0a49c07df7416f0216e4b12f15b735', 'drivers/vision/npu/npu-debug.c': 'cfc923c8fe8a902ca9c790c835052140bf6faba33bf4a1f5ac01499e2aa9a2ff', 'drivers/vision/npu/npu-golden.c': 'c00020139c705c8766477125d2353f9d6b8ea6b84d5d360a7665af0d7b41097f', 'drivers/vision/npu/npu-util-memdump.c': '458cdfd71e23919fa36a12db26ba6f90318b679630a624871e259010488b7ddd', 'drivers/vision/npu/npu-memory.c': '5be697bfa62c5fdae56021861d1ae2fd35755e0fa1692420167bfe149f6817ee', 'drivers/vision/npu/interface/hardware/npu-interface.c': '648d2b9918b865de489b990a65304c42e854dfc4edbb64c3bede958b54d1b5b2', 'drivers/vision/score/hardware/v3/score_scq.c': 'fa6e7093cf0fb70c84549b343b07009e31cf8a5afb2ba4fdd227d5818b95f3f5'})
PINS['drivers/gpu/exynos/g2d/g2d_debug.c']='7504456404b0925e18a31663b5f04fe5741896a83507ae3857ae51b3ce8ae6ea'
OPTION=retained.OPTION
once=retained.once
sha=retained.sha


def profile(settings):
    retained.profile(settings)
    required={'EXYNOS_NPU':'y','NPU_HARDWARE':'y','NPU_INTERFACE':'y',
              'NPU_LOOPBACK':'n','NPU_ZEBU_EMULATION':'n','NPU_ZEBU_SYSMMU':'y',
              'EXYNOS_SOC_NAME':'"9820"','EXYNOS_IOVMM':'y','PM':'y',
              'PMUCAL':'y','PMUCAL_DBG':'y','VISION_UNITTEST':'y'}
    if any(settings.get(k)!=v for k,v in required.items()):raise ValueError('exact native NPU hardware profile required')
    return required


def function(raw,name):
    text=raw.decode();match=re.search(r'(?m)^((?:static\s+)?(?:inline\s+)?(?:unsigned\s+int|ssize_t|irqreturn_t|bool|void|int|long))\s+'+re.escape(name)+r'\(([^)]*)\)\s*\{',text)
    if not match:raise ValueError('native function absent: '+name)
    depth=1;end=None
    token=re.compile(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[{}]',re.S)
    for part in token.finditer(text,match.end()):
        if part.group()=='{':depth+=1
        elif part.group()=='}':depth-=1
        if depth==0:end=part.end();break
    if end is None:raise ValueError('native function extent differs: '+name)
    return text,match,end


def guarded(raw,name,event=None,user=False,refusal='-ESHUTDOWN',admission=None):
    text,m,end=function(raw,name);native=name+'_n136_native'
    signature=text[m.start():m.end()-1].rstrip();rtype=m.group(1).replace('static','').replace('inline','').strip()
    args=[] if m.group(2).strip() in ('','void') else [re.search(r'([A-Za-z0-9_]+)\s*$',v.strip()).group(1) for v in m.group(2).split(',')]
    call=native+'('+','.join(args)+')';answer='return;' if rtype=='void' else 'return '+refusal+';'
    native_body=text[m.start():end].replace(' '+name+'(',' '+native+'(',1)
    body=signature+'\n{\n#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\n'
    if user:
        if rtype!='void':body+='    '+rtype+' result;\n'
        body+='    if(!n136_npu_user_begin())'+answer+'\n'
    if event or admission:
        gate=admission or 'n136_npu_event('+event+')'
        body+='    if(!'+gate+'){'+('n136_npu_user_end();' if user else '')+answer+'}\n'
    if user:
        body+='    '+(('result='+call+';\n') if rtype!='void' else call+';\n')+'    n136_npu_user_end();'+('return result;' if rtype!='void' else 'return;')+'\n'
    else:body+='    '+('return '+call+';' if rtype!='void' else call+';return;')+'\n'
    body+='#else\n    '+('return '+call+';' if rtype!='void' else call+';return;')+'\n#endif\n}\n'
    return (text[:m.start()]+native_body+'\n'+body+text[end:]).encode()


def score_overlay(output):
    header=output['drivers/vision/score/score_device.h']
    header=b'#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\n#include <linux/v136_terminal.h>\n#endif\n'+header
    header=once(header,b'    bool n133_shutdown_seen;',b'    struct n136_witness n136_witness;\n    bool n133_shutdown_seen;')
    output['drivers/vision/score/score_device.h']=header
    raw=output['drivers/vision/score/v133_score.inc']
    raw=once(raw,b'struct score_system *system;unsigned long flags;int error;bool locked=false;',b'struct score_system *system;unsigned long flags;int error,n136_mode=-1;u32 n136_clkm,n136_clks;bool locked=false,n136_cal=false;struct n136_detail n136_detail={0};')
    raw=raw.replace(b'__clk_is_enabled(',b'__clk_get_enable_count(')
    raw=once(raw,b'    if(__clk_get_enable_count(device->clk.clkm) || __clk_get_enable_count(device->clk.clks)){error=-EBUSY;detail.reason="initial-clock-user";goto refused;}',b'''    n136_clkm=__clk_get_enable_count(device->clk.clkm);n136_clks=__clk_get_enable_count(device->clk.clks);
    if(n136_clkm || n136_clks){error=-EBUSY;detail.reason="initial-clock-reference";detail.state=n136_clkm;detail.aux=n136_clks;goto refused;}
    stage="score-cal";n136_mode=n136_cal_begin(N136_SCORE_DOMAINS,&n136_detail);
    if(n136_mode<0){error=n136_mode;detail.reason=n136_detail.reason;detail.item=n136_detail.item;detail.state=n136_detail.state;detail.aux=n136_detail.aux;goto refused;}
    n136_cal=true;
    if(!n136_mode)goto n136_software_recheck;''')
    raw=once(raw,b'    stage="score-reset";error=n133_score_hardware_stop(system,&detail);',b'''    n136_clkm=__clk_get_enable_count(device->clk.clkm);n136_clks=__clk_get_enable_count(device->clk.clks);
    if(n136_clkm!=1 || n136_clks!=1){
        error=-EBUSY;detail.reason="acquired-clock-reference";detail.state=n136_clkm;detail.aux=n136_clks;goto n136_owned_release;}
    stage="score-reset";error=n133_score_hardware_stop(system,&detail);
n136_owned_release:''')
    raw=raw.replace(b'stage="score-clock-off";',b'stage="score-clock-reference";')
    raw=once(raw,b'    if(__clk_get_enable_count(device->clk.clkm)){error=-EBUSY;detail.reason="dspm-clock-user";detail.item=0;detail.state=1;goto refused;}',b'    n136_clkm=__clk_get_enable_count(device->clk.clkm);\n    if(n136_clkm){error=-EBUSY;detail.reason="dspm-clock-reference";detail.item=0;detail.state=n136_clkm;goto refused;}')
    raw=once(raw,b'    if(__clk_get_enable_count(device->clk.clks)){error=-EBUSY;detail.reason="dsps-clock-user";detail.item=1;detail.state=1;goto refused;}',b'    n136_clks=__clk_get_enable_count(device->clk.clks);\n    if(n136_clks){error=-EBUSY;detail.reason="dsps-clock-reference";detail.item=1;detail.state=n136_clks;goto refused;}')
    raw=once(raw,b'    stage="score-recheck";error=n133_score_state_locked(device,&detail);',b'n136_software_recheck:\n    stage="score-recheck";error=n133_score_state_locked(device,&detail);')
    raw=once(raw,b'    stage="score-record";error=n130_dma_record(owner,0);',b'''    n136_cal_end(N136_SCORE_DOMAINS,true);n136_cal=false;
    stage="score-record";error=n136_witness_commit(&device->n136_witness,owner,n136_mode?N136_SCORE_RESET_DMA_FROZEN:N136_SCORE_DOMAINS_OFF_FROZEN,N136_SCORE_DOMAINS);
    if(!error)error=n130_dma_record(owner,0);''')
    raw=once(raw,b'refused:\n    n131_gate_refused',b'refused:\n    if(n136_cal)n136_cal_end(N136_SCORE_DOMAINS,false);\n    n131_gate_refused')
    raw=once(raw,b'    if(!error)error=n133_score_state_locked(device,&detail);',b'''    if(!error && ((device->n136_witness.type!=N136_SCORE_RESET_DMA_FROZEN && device->n136_witness.type!=N136_SCORE_DOMAINS_OFF_FROZEN) ||
       !n136_witness_valid(&device->n136_witness,owner,device->n136_witness.type,N136_SCORE_DOMAINS)))error=-EPERM;
    if(!error)error=n133_score_state_locked(device,&detail);''')
    raw=raw.replace(b'dspm-clock-user',b'dspm-clock-reference').replace(b'dsps-clock-user',b'dsps-clock-reference').replace(b'initial-clock-user',b'initial-clock-reference')
    raw=raw.replace(b'only our successful native-resume gate enables;',b'only our successful native-resume CCF enables;')
    raw=raw.replace(b'/* Native target-halt and DMA-idle predicates, with the already inspected\n * values retained for one bounded refusal record. No reset/cache flush. */',b'/* Actual EVT1 native reset completion and all4 DMA idle, with cached\n * same-read details. Clock state is not inferred from CCF ownership. */')
    for name in ('drivers/vision/score/v133_score.inc','drivers/vision/score/hardware/v3/v133_score.inc'):output[name]=raw
    system_h=output['drivers/vision/score/hardware/v3/score_system.h']
    system_h=once(system_h,b'    bool n133_ever_booted;',b'    bool n133_ever_booted;\n    bool n136_ever_rearmed;')
    system_h=once(system_h,b'int n133_score_hardware_stop(',b'''/* Admit before the first wake/command effect. A prior admission permanently
 * disqualifies cold proof; an admission after freeze never reaches MMIO. */
static inline bool n136_score_writer_enter(struct score_system *system)
{
    unsigned long flags;bool admit;
    spin_lock_irqsave(&system->n133_boot_lock,flags);
    admit=!system->n133_terminal;
    if(admit)system->n136_ever_rearmed=true;
    spin_unlock_irqrestore(&system->n133_boot_lock,flags);return admit;
}
int n133_score_hardware_stop(''')
    output['drivers/vision/score/hardware/v3/score_system.h']=system_h
    raw=raw.replace(b'!system->n133_terminal || system->n133_ever_booted',b'!system->n133_terminal || system->n133_ever_booted || system->n136_ever_rearmed')
    raw=once(raw,b'detail->value=system->n133_ever_booted;error=-EBUSY;',b'detail->value=system->n133_ever_booted;detail->aux=system->n136_ever_rearmed;error=-EBUSY;')
    for name in ('drivers/vision/score/v133_score.inc','drivers/vision/score/hardware/v3/v133_score.inc'):output[name]=raw
    system=output['drivers/vision/score/hardware/v3/score_system.c']
    system=once(system,b'void score_system_wakeup(struct score_system *system)\n{',b'''void score_system_wakeup(struct score_system *system)
{
#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
    if(!n136_score_writer_enter(system))return;
#endif''')
    for name in ('score_system_sw_reset','score_system_halt'):
        system=guarded(system,name,admission='n136_score_writer_enter(system)')
    output['drivers/vision/score/hardware/v3/score_system.c']=system
    driver=output['drivers/vision/score/score_device.c']
    driver=once(driver,b'\tpr_err("< SCore IOMMU FAULT HANDLER >\\n");',b'''#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
    if(!device || !n136_score_writer_enter(&device->system))return -EINVAL;
#endif
\tpr_err("< SCore IOMMU FAULT HANDLER >\\n");''')
    output['drivers/vision/score/score_device.c']=driver


def g2d_overlay(output):
    header=output['drivers/gpu/exynos/g2d/g2d.h']
    header=b'#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\n#include <linux/v136_terminal.h>\n#endif\n'+header
    header=once(header,b'    bool n132_terminal;',b'    struct n136_witness n136_witness;\n    spinlock_t n136_io_lock;\n    bool n136_io_frozen,n136_ever_dumped,n136_ever_pushed;\n    bool n132_terminal;')
    header=once(header,b'static inline bool n132_g2d_allocate_locked(',b'''static inline bool n136_g2d_io_enter(struct g2d_device *g2d)
{
    unsigned long flags;bool admit;
    if(!g2d)return false;
    spin_lock_irqsave(&g2d->n136_io_lock,flags);
    admit=!g2d->n136_io_frozen;
    if(admit)g2d->n136_ever_dumped=true;
    spin_unlock_irqrestore(&g2d->n136_io_lock,flags);return admit;
}
static inline bool n132_g2d_allocate_locked(''')
    output['drivers/gpu/exynos/g2d/g2d.h']=header
    raw=output['drivers/gpu/exynos/g2d/v132_g2d.inc']
    raw=once(raw,b'    if(!g2d->n132_terminal)',b'''    spin_lock_irqsave(&g2d->n136_io_lock,flags);
    n136_iof=g2d->n136_io_frozen;n136_ioh=g2d->n136_ever_dumped;
    if(!n136_iof || n136_ioh){detail->reason="debug-access-history";detail->state=n136_iof;detail->value=n136_ioh;error_n136=-EBUSY;}
    spin_unlock_irqrestore(&g2d->n136_io_lock,flags);
    if(error_n136)return error_n136;
    if(!g2d->n132_terminal)''')
    raw=once(raw,b'struct g2d_task *task;unsigned int count=0;unsigned long state=g2d->state;',b'struct g2d_task *task;unsigned int count=0;unsigned long state=g2d->state,flags;int error_n136=0;bool n136_iof,n136_ioh;')
    raw=once(raw,b'    stage="g2d-tasks";',b'''    spin_lock_irqsave(&g2d->n136_io_lock,flags);g2d->n136_io_frozen=true;
    spin_unlock_irqrestore(&g2d->n136_io_lock,flags);
    stage="g2d-tasks";''')
    raw=once(raw,b'    if(g2d->n132_ever_allocated)',b'    if(g2d->n136_ever_pushed){detail->reason="push-history";return -EBUSY;}\n    if(g2d->n132_ever_allocated)')
    raw=once(raw,b'    unsigned long flags;unsigned int job;int error;const char *stage="g2d-provider";',b'    unsigned long flags;unsigned int job;int error,n136_mode=-1;u32 n136_reference;bool n136_cal=false;struct n136_detail n136_detail={0};const char *stage="g2d-provider";')
    raw=once(raw,b'    stage="g2d-power";error=pm_runtime_get_sync(device);',b'''    n136_reference=__clk_get_enable_count(g2d->clock);
    if(n136_reference){error=-EBUSY;detail.reason="initial-clock-reference";detail.state=n136_reference;goto refused;}
    stage="g2d-cal";n136_mode=n136_cal_begin(N136_G2D_DOMAINS,&n136_detail);
    if(n136_mode<0){error=n136_mode;detail.reason=n136_detail.reason;detail.item=n136_detail.item;detail.state=n136_detail.state;detail.value=(int)n136_detail.aux;goto refused;}
    n136_cal=true;
    if(!n136_mode)goto n136_software_recheck;
    stage="g2d-power";error=pm_runtime_get_sync(device);''')
    raw=once(raw,b'    stage="g2d-fifo";error=g2d_hw_fifo_idle(g2d)?0:-EBUSY;',b'''    n136_reference=__clk_get_enable_count(g2d->clock);
    if(n136_reference!=1){error=-EBUSY;detail.reason="acquired-clock-reference";detail.state=n136_reference;goto n136_owned_release;}
    stage="g2d-fifo";error=g2d_hw_fifo_idle(g2d)?0:-EBUSY;''')
    raw=once(raw,b'    clk_disable(g2d->clock);',b'n136_owned_release:\n    clk_disable(g2d->clock);')
    raw=raw.replace(b'__clk_is_enabled(',b'__clk_get_enable_count(').replace(b'g2d-clock-off',b'g2d-clock-reference').replace(b'clock-enabled',b'clock-reference')
    raw=once(raw,b'    if(!error && __clk_get_enable_count(g2d->clock)){stage="g2d-clock-reference";error=-EBUSY;detail.reason="clock-reference";detail.value=1;}',b'    n136_reference=__clk_get_enable_count(g2d->clock);\n    if(!error && n136_reference){stage="g2d-clock-reference";error=-EBUSY;detail.reason="clock-reference";detail.state=n136_reference;}')
    raw=once(raw,b'    stage="g2d-recheck";',b'n136_software_recheck:\n    stage="g2d-recheck";')
    raw=once(raw,b'    stage="g2d-record";error=n130_dma_record(device,0);',b'''    n136_cal_end(N136_G2D_DOMAINS,true);n136_cal=false;
    stage="g2d-record";error=n136_witness_commit(&g2d->n136_witness,device,n136_mode?N136_G2D_FINITE_JOBS_FROZEN:N136_G2D_DOMAIN_OFF_FROZEN,N136_G2D_DOMAINS);
    if(!error)error=n130_dma_record(device,0);''')
    raw=once(raw,b'refused:\n    n131_gate_refused',b'refused:\n    if(n136_cal)n136_cal_end(N136_G2D_DOMAINS,false);\n    n131_gate_refused')
    raw=once(raw,b'    if(!error)error=n131_dma_status(device);',b'''    if(!error && ((g2d->n136_witness.type!=N136_G2D_FINITE_JOBS_FROZEN && g2d->n136_witness.type!=N136_G2D_DOMAIN_OFF_FROZEN) ||
       !n136_witness_valid(&g2d->n136_witness,device,g2d->n136_witness.type,N136_G2D_DOMAINS)))error=-EPERM;
    if(!error)error=n131_dma_status(device);''')
    raw=once(raw,b'    if(device->driver!=&g2d_driver.driver)return 0;',b'''    if(READ_ONCE(device->driver)!=&g2d_driver.driver)return 0;
    if(!device_trylock(device))return -EBUSY;
    if(device->driver!=&g2d_driver.driver){device_unlock(device);return -ENODEV;}''')
    raw=once(raw,b'    if(!g2d || g2d->dev!=device)return -ENODEV;',b'    if(!g2d || g2d->dev!=device){device_unlock(device);return -ENODEV;}')
    raw=once(raw,b'    if(error){if(detail.reason)',b'    device_unlock(device);\n    if(error){if(detail.reason)')
    output['drivers/gpu/exynos/g2d/v132_g2d.inc']=raw
    driver=output['drivers/gpu/exynos/g2d/g2d_drv.c']
    driver=once(driver,b'\tg2d_dev->dev = &pdev->dev;',b'''\tg2d_dev->dev = &pdev->dev;
#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
    spin_lock_init(&g2d_dev->n136_io_lock);
#endif''')
    driver=once(driver,b'int g2d_device_run(struct g2d_device *g2d_dev, struct g2d_task *task)\n{',b'''int g2d_device_run(struct g2d_device *g2d_dev, struct g2d_task *task)
{
#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
    /* Native caller holds lock_task: closes both normal and secure SMC push. */
    if(g2d_dev->n132_terminal)return -ESHUTDOWN;
    g2d_dev->n136_ever_pushed=true;
#endif''')
    output['drivers/gpu/exynos/g2d/g2d_drv.c']=driver


def g2d_io_overlay(stock,output):
    tasks=output['drivers/gpu/exynos/g2d/g2d_task.c']
    tasks=once(tasks,b'static void g2d_execute_task(struct g2d_device *g2d_dev, struct g2d_task *task)\n{',b'''static void g2d_execute_task(struct g2d_device *g2d_dev, struct g2d_task *task)
{
#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
    /* Native lock_task covers admission before the secure-enable SMC too. */
    if(g2d_dev->n132_terminal)return;
    g2d_dev->n136_ever_pushed=true;
#endif''')
    output['drivers/gpu/exynos/g2d/g2d_task.c']=tasks
    debug=stock['drivers/gpu/exynos/g2d/g2d_debug.c']
    for name in ('g2d_dump_info','g2d_dump_sfr','g2d_dump_afbcdata'):
        debug=guarded(debug,name,admission='n136_g2d_io_enter(g2d_dev)')
    output['drivers/gpu/exynos/g2d/g2d_debug.c']=debug
    driver=output['drivers/gpu/exynos/g2d/g2d_drv.c']
    driver=guarded(driver,'g2d_iommu_fault_handler',admission='n136_g2d_io_enter((struct g2d_device *)token)',refusal='0')
    driver=guarded(driver,'g2d_itmon_notifier',admission='n136_g2d_io_enter(container_of(nb,struct g2d_device,itmon_nb))',refusal='NOTIFY_DONE')
    output['drivers/gpu/exynos/g2d/g2d_drv.c']=driver


def npu_overlay(stock,output):
    names=tuple(p for p in PINS if p.startswith('drivers/vision/npu/') and p.endswith('.c'))
    for name in names:output[name]=b'#include <linux/v136_terminal.h>\n'+stock[name]
    driver=output['drivers/vision/npu/npu-device.c']
    driver=once(driver,b'\tdevice->dev = dev;',b'''\tdevice->dev = dev;
#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
    ret=n136_npu_register(device);if(ret)goto err_exit;
#endif''')
    driver=once(driver,b'\tdev_set_drvdata(dev, device);',b'''\tdev_set_drvdata(dev, device);
#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
    n136_npu_ready(device);
#endif''')
    text,m,end=function(driver,'npu_device_probe');probe=text[m.start():end]
    if probe.count('\tif (ret < 0)\n\t\treturn ret;')!=1:raise ValueError('native NPU IOVMM failure boundary differs')
    probe=probe.replace('\tif (ret < 0)\n\t\treturn ret;','\tif (ret < 0)\n\t\tgoto err_exit;',1)
    if probe.count('err_exit:\n')!=1:raise ValueError('native NPU probe failure boundary differs')
    probe=probe.replace('err_exit:\n','err_exit:\n#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\n    n136_npu_detach(device);\n#endif\n',1)
    driver=(text[:m.start()]+probe+text[end:]).encode()
    driver=guarded(driver,'npu_device_open','N136_OPEN')
    driver=guarded(driver,'npu_iommu_fault_handler','N136_FAULT',refusal='0')
    text,m,end=function(driver,'npu_device_remove');body=text[m.start():end]
    body=body.replace('device = dev_get_drvdata(dev);','device = dev_get_drvdata(dev);\n#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\n    n136_npu_detach(device);\n#endif',1)
    driver=(text[:m.start()]+body+text[end:]).encode()
    driver=once(driver,b'static struct platform_driver npu_driver = {',b'''#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
static void n136_npu_shutdown(struct platform_device *pdev);
#endif
static struct platform_driver npu_driver = {
#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
    .shutdown=n136_npu_shutdown,
#endif''')
    driver+=b'\n#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\n#include "v136_npu.inc"\n#endif\n'
    output['drivers/vision/npu/npu-device.c']=driver
    output['drivers/vision/npu/npu-system.c']=guarded(output['drivers/vision/npu/npu-system.c'],'npu_system_resume','N136_RESUME')
    output['drivers/vision/npu/npu-system.c']=guarded(output['drivers/vision/npu/npu-system.c'],'npu_system_suspend','N136_RESUME')
    output['drivers/vision/npu/npu-protodrv.c']=guarded(output['drivers/vision/npu/npu-protodrv.c'],'proto_drv_open','N136_OPEN')+b'''
#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
int n136_npu_protocol_cold(struct npu_device *d,struct n136_detail *detail)
{
    if(d->proto_drv!=&npu_proto_drv || npu_proto_drv.npu_device!=d || get_state()!=PROTO_DRV_STATE_PROBED ||
       npu_proto_drv.open_steps || npu_proto_drv.if_session_ctx || npu_proto_drv.if_mbox_ctx ||
       !list_empty(&npu_proto_drv.session_ref.entry_list)){
        detail->reason="protocol-state";detail->state=get_state();detail->aux=npu_proto_drv.open_steps;return -EBUSY;}
    return 0;
}
#endif
'''
    interface=output['drivers/vision/npu/interface/hardware/npu-interface.c']
    for name,event,refusal in [('npu_interface_open','N136_RESUME','-ESHUTDOWN'),('npu_interface_close','N136_RESUME','-ESHUTDOWN'),('fw_rprt_manager','N136_REPORT','0'),('__rprt_manager','N136_REPORT','0'),('mailbox_isr2','N136_REPORT','IRQ_HANDLED'),('mailbox_isr3','N136_REPORT','IRQ_HANDLED'),('mbx_rslt_fault_listener','N136_FAULT','0')]:
        interface=guarded(interface,name,event,refusal=refusal)
    interface+=b'''
#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
#include "npu-device.h"
int n136_npu_interface_cold(struct npu_device *d,struct n136_detail *detail)
{
    if(interface.sfr!=(volatile struct mailbox_sfr *)d->system.mbox_sfr.vaddr ||
       interface.addr || interface.mbox_hdr || !wq || work_busy(&work_report)){
        detail->reason="interface-state";return -EBUSY;}
    return 0;
}
#endif
'''
    output['drivers/vision/npu/interface/hardware/npu-interface.c']=interface
    for source,name,event in [('npu-util-memdump.c','npu_util_dump_handle_error_k','N136_FAULT'),('npu-log.c','fw_will_note','N136_FAULT'),('npu-memory.c','npu_memory_map','N136_MEMORY'),('npu-memory.c','npu_memory_alloc','N136_MEMORY'),('npu-memory.c','npu_memory_unmap','N136_MEMORY'),('npu-memory.c','npu_memory_free','N136_MEMORY')]:
        path='drivers/vision/npu/'+source;output[path]=guarded(output[path],name,event)
    vertex='drivers/vision/npu/npu-vertex.c'
    callbacks=re.findall(rb'\.[a-z0-9_]+\s*=\s*(npu_vertex_[a-z0-9_]+)',stock[vertex])
    for name in sorted(set(callbacks)):
        output[vertex]=guarded(output[vertex],name.decode(),user=True,refusal='0' if name==b'npu_vertex_poll' else '-ESHUTDOWN')
    # Every normal debugfs .open has a history gate. Already-open files imply
    # irreversible DEBUG history, so no cold provider can pass concurrently.
    for path in names:
        callbacks=set(re.findall(rb'\.open\s*=\s*([a-zA-Z][a-zA-Z0-9_]+)',stock[path]))
        for name in sorted(callbacks):
            if name.startswith(b'npu_vertex_'):continue
            if name==b'IDIOT_open':
                output[path]=once(output[path],b'static const struct file_operations npu_debug_unittest_fops',b'''static int n136_unittest_open(struct inode *inode,struct file *file)
{if(!N136_DEBUG_ADMIT())return -ESHUTDOWN;return IDIOT_open(inode,file);}
static const struct file_operations npu_debug_unittest_fops''')
                output[path]=once(output[path],b'.open = IDIOT_open',b'.open = n136_unittest_open')
            else:output[path]=guarded(output[path],name.decode(),'N136_DEBUG')
        sysfs=set(re.findall(rb'^static ssize_t ((?:npu_chg_log_level_(?:show|store)|npu_sysfs_(?:show|set)_qos|s_profiler_(?:show|store)|version_show))\(',stock[path],re.M))
        for name in sorted(sysfs):output[path]=guarded(output[path],name.decode(),user=True)
    mem='drivers/vision/npu/npu-util-memdump.c'
    output[mem]=once(output[mem],b'\tnpu_info(#__NPU_SRAM " SRAM dump open\\n");',b'\tif(!N136_DEBUG_ADMIT())return -ESHUTDOWN;\t\\\n\tnpu_info(#__NPU_SRAM " SRAM dump open\\n");')
    output['drivers/vision/npu/v136_npu.inc']=(HERE/'v136_npu.inc').read_bytes()


def render(stock,identity,source128):
    for name,pin in PINS.items():
        if sha(stock[name])!=pin:raise ValueError('pinned v136 native source differs: '+name)
    output=retained.render(stock,identity,source128)
    score_overlay(output);g2d_overlay(output);g2d_io_overlay(stock,output);npu_overlay(stock,output)
    scq=stock['drivers/vision/score/hardware/v3/score_scq.c']
    scq=once(scq,b'int score_scq_write(struct score_scq *scq, struct score_frame *frame)\n{\n\tint ret = 0;',b'''int score_scq_write(struct score_scq *scq, struct score_frame *frame)
{
\tint ret = 0;
#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
    struct score_system *n136_system=container_of(scq,struct score_system,scq);
    if(!n136_score_writer_enter(n136_system))return -ESHUTDOWN;
#endif''')
    output['drivers/vision/score/hardware/v3/score_scq.c']=scq
    cal=stock['drivers/soc/samsung/cal-if/cal-if.c']
    cal=once(cal,b'int cal_pd_control(unsigned int id, int on)',b'static int n136_cal_pd_native(unsigned int id, int on)')
    cal+=b'''
#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
#include "v136_cal.inc"
int cal_pd_control(unsigned int id,int on)
{
    unsigned int domain=n136_cal_domain(id);unsigned long flags;int error;bool refuse;
    if(!domain)return n136_cal_pd_native(id,on);
    mutex_lock(&n136_cal_lock);
    spin_lock_irqsave(&n136_cal_state_lock,flags);
    refuse=((n136_closed_domains|n136_reserved_domains)&domain)!=0;
    spin_unlock_irqrestore(&n136_cal_state_lock,flags);
    error=refuse?-ESHUTDOWN:n136_cal_pd_native(id,on);
    mutex_unlock(&n136_cal_lock);return error;
}
#else
int cal_pd_control(unsigned int id,int on){return n136_cal_pd_native(id,on);}
#endif
'''
    output['drivers/soc/samsung/cal-if/cal-if.c']=cal
    output['drivers/soc/samsung/cal-if/v136_cal.inc']=(HERE/'v136_cal.inc').read_bytes()
    output['include/linux/v136_terminal.h']=(HERE/'v136_terminal.h').read_bytes()
    api=output['include/linux/v130_kernel_api.h']
    output['include/linux/v130_kernel_api.h']=once(api,b'int n133_score_prepare(void);',b'int n133_score_prepare(void);\nint n136_npu_prepare(void);')
    kernel=output['arch/arm64/mm/v130_kernel.c']
    output['arch/arm64/mm/v130_kernel.c']=once(kernel,b'    if(!result)result=n130_iommu_prepare();',b'    if(!result)result=n136_npu_prepare();\n    if(!result)result=n130_iommu_prepare();')
    kconfig=output['arch/arm64/Kconfig']
    output['arch/arm64/Kconfig']=once(kconfig,b' depends on EXYNOS_SCORE && EXYNOS_SCORE_V3 && !EXYNOS_SCORE_V2 && !EXYNOS_SCORE_FPGA',b' depends on EXYNOS_SCORE && EXYNOS_SCORE_V3 && !EXYNOS_SCORE_V2 && !EXYNOS_SCORE_FPGA\n depends on EXYNOS_NPU && NPU_HARDWARE && NPU_INTERFACE && !NPU_LOOPBACK && !NPU_ZEBU_EMULATION')
    for path in ('drivers/vision/npu/npu-device.c','drivers/vision/score/score_device.c','drivers/gpu/exynos/g2d/g2d_drv.c'):
        output[path]=once(output[path],b'\t.driver = {',b'\t.driver = {\n#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\n        .suppress_bind_attrs=true,\n#endif')
    for name,raw in output.items():output[name]=raw.replace(b'N10XNU135',b'N10XNU136')
    return output


def install(source,identity,source128):
    source=Path(source).resolve();stock={name:(source/name).read_bytes() for name in PINS};output=render(stock,identity,source128)
    for name in output:
        path=source/name
        if not path.resolve().is_relative_to(source) or any(p.is_symlink() for p in (path,*path.parents)):raise ValueError('unsafe v136 native overlay path')
        if name not in PINS and path.exists():raise ValueError('new v136 component exists')
    for name,raw in output.items():
        path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    return {name:sha(raw) for name,raw in output.items()}
