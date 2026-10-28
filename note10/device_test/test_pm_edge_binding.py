"""Exercise PM-edge scope and proof binding against synthetic artifact mutations."""
import argparse, copy, hashlib, json
from pathlib import Path
from run_probe import ROOT
import pm_edge_binding as binding
from prepare_pm_edge import HERE, SOURCES, PINS


def run(output):
    out=Path(output).resolve()
    if out.exists() or not out.is_relative_to((ROOT/'note10/private').resolve()): raise ValueError('Fresh private binding output required')
    out.mkdir(parents=True)
    actual={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES}
    prepared={n:hashlib.sha256(n.encode()).hexdigest() for n in ('drivers/base/power/note10_dma_pm.c','kernel/power/note10_pm_noirq.c','arch/arm64/mm/note10_pm_timer_roundtrip.c','kernel/power/suspend.c')}
    prepared.update({n:hashlib.sha256(n.encode()).hexdigest() for n in ('kernel/power/Kconfig','drivers/base/power/main.c','drivers/iommu/exynos-iommu.c','drivers/base/syscore.c')})
    prepared.update({'drivers/base/power/main.c':'271c104727a0266b9803c667fe5bddb8da679cc3f54d7cd5052d163b54e66270','drivers/iommu/exynos-iommu.c':'121f9001105ac9456418269fa31b7bd4a12726dbefd924c5c5c27c1564889260','drivers/base/syscore.c':'d15cab08efd46310218cfb08a056d16362f77a0252c3bce2c36158ae3eddf0d6'})
    prepared['kernel/power/suspend.c']='2bad7dc2695559e4df992a6571fb2c79cc4879384819f946254da4519049efde'
    prepared.update({'drivers/base/power/note10_pm_edge_dma.c':actual['pm_edge_dma_backend.c'],'drivers/iommu/note10_pm_edge_iommu.c':actual['pm_edge_iommu_backend.c'],'drivers/base/note10_pm_edge_syscore.c':actual['pm_edge_syscore_backend.c'],'arch/arm64/mm/note10_pm_edge_probe.c':actual['pm_edge_probe.c'],**{'include/linux/note10_pm_edge_'+k+'.h':actual['pm_edge_'+k+'_contract.h'] for k in ('dma','iommu','syscore')}})
    build={'pm_edge_inventory_diagnostic':True,'pm_edge_inventory_evidence_version':1,'pm_edge_source_pins':PINS,'pm_edge_sources_sha256':actual,'pm_edge_prepared_sha256':prepared,'pm_quiesce_patched_sha256':{'kernel/power/Kconfig':prepared['kernel/power/Kconfig']},
           **{n:True for n in ('pm_post_arch_diagnostic','pm_cpus_diagnostic','dma_pm_audit_diagnostic','iommu_pm_audit_diagnostic')}}
    config=[b'CONFIG_NOTE10_PM_EDGE_INVENTORY=y',b'CONFIG_KALLSYMS=y',b'CONFIG_NOTE10_PM_POST_ARCH=y',b'CONFIG_NOTE10_PM_CPUS_TEST=y',b'CONFIG_NOTE10_DMA_PM_AUDIT=y',b'CONFIG_NOTE10_IOMMU_PM_AUDIT=y']
    image=b' '.join(binding.MARKERS)
    models={}
    for kind,count,accepted,harness in (('dma',18,{0,14,21,28},'test_pm_edge_dma_native.py'),('iommu',32,{0,14,19,21,29},'test_pm_edge_iommu_native.py'),('syscore',25,{0,15,24},'test_pm_edge_syscore_native.py')):
        modes={'dma':{0,1,3,4,5,6,14,*range(20,31)},'iommu':{0,*range(1,15),*range(16,33)},'syscore':set(range(25))}[kind]
        models[kind]={'passed':True,'cases':count,'actual_backend_executed':True,'source_sha256':{k:actual[k] for k in ('pm_edge_'+kind+'_contract.h','pm_edge_'+kind+'_backend.c')},'harness_sha256':actual[harness],'outcomes':[{'mode':m,'passed':True,'accepted':m in accepted} for m in modes], 'legacy_backend_same_translation_unit':True}
    source={'dma':prepared['drivers/base/power/note10_dma_pm.c'],'noirq':prepared['kernel/power/note10_pm_noirq.c'],'worker':prepared['arch/arm64/mm/note10_pm_timer_roundtrip.c'],'suspend':prepared['kernel/power/suspend.c'],'edge':actual['pm_edge_dma_backend.c'],'producer':actual['pm_edge_probe.c'],'kconfig':prepared['kernel/power/Kconfig'],'pm_main':prepared['drivers/base/power/main.c'],'iommu_driver':prepared['drivers/iommu/exynos-iommu.c'],'syscore':prepared['drivers/base/syscore.c']}
    integration={'passed':True,'cases':22,'source_sha256':source,'harness_sha256':actual['test_pm_edge_integration_native.py'],'hardware_verified':False,'outcomes':[{'name':name,'mode':int(name.rsplit('-',1)[1]),'passed':True} for name in ([f'suspend-flow-{n}' for n in (0,1,2,19)]+[f'worker-{n}' for n in range(9)]+[f'producer-{n}' for n in range(9)])],**{k:True for k in ('actual_prepared_dma_hook_executed','actual_prepared_noirq_hook_executed','actual_suspend_caller_and_enter_executed','actual_prepared_worker_executed','actual_prepared_producer_executed','disabled_profile_matches_enabled_flow')}}
    names=['baseline','runtime_change','missing_dma','bad_checksum','missing_identity','missing_callback','missing_status','duplicate','dma_conflict','iommu_conflict','callback_conflict','callback_mask','bad_phase','wrong_generation','bad_sentinel','bad_status','failure_bitmask']+[f'producer_failure_{i}' for i in range(1,8)]
    logs={'producer-'+str(n)+'.log':hashlib.sha256(str(n).encode()).hexdigest() for n in range(9)}
    integration['producer_log_sha256']=logs.copy()
    decoder={'passed':True,'harness_sha256':actual['test_pm_edge_decoder.py'],'decoder_sha256':actual['decode_pm_edge.py'],'cases':24,'actual_producer_frames_decoded':True,'producer_log_sha256':logs.copy(),'outcomes':[{'case':name,'passed':True,'accepted':name in ('baseline','runtime_change')} for name in names]}
    def write(c,im,ms,integ,dec):
        (out/'handoff.config').write_bytes(b'\n'.join(c)+b'\n');(out/'Image').write_bytes(im)
        for kind,obj in ms.items():
            d=out/('pm-edge-'+kind+'-model');d.mkdir(exist_ok=True);(d/'result.json').write_text(json.dumps(obj),encoding='utf-8')
        for name,obj in [('integration',integ),('decoder',dec)]:
            d=out/('pm-edge-'+name+'-model');d.mkdir(exist_ok=True);(d/'result.json').write_text(json.dumps(obj),encoding='utf-8')
            if name=='integration':
                for n in range(9): (d/('producer-'+str(n)+'.log')).write_bytes(str(n).encode())
    rows=[]
    def check(name,mutate=None,accept=False):
        b=copy.deepcopy(build);c=config.copy();im=image;ms=copy.deepcopy(models);integ=copy.deepcopy(integration);dec=copy.deepcopy(decoder)
        if mutate:
            changed=mutate(b,c,im,ms,integ,dec)
            if isinstance(changed,bytes): im=changed
        write(c,im,ms,integ,dec)
        try: result=binding.validate_model(out,b); ok=result is True
        except (ValueError, OSError, KeyError, TypeError) as exc:
            if accept: raise ValueError('Valid synthetic proof rejected: '+str(exc)) from exc
            ok=False
        if ok!=accept:raise ValueError('Binding acceptance differs: '+name)
        rows.append({'name':name,'accepted':ok,'passed':True})
    check('valid',accept=True)
    for marker in binding.MARKERS:
        check('missing-image-'+marker.decode(),lambda b,c,im,m,i,d,marker=marker:im.replace(marker,b''))
    for key in ('pm_edge_inventory_diagnostic','pm_edge_inventory_evidence_version','pm_edge_source_pins','pm_edge_sources_sha256','pm_edge_prepared_sha256','pm_post_arch_diagnostic','pm_cpus_diagnostic','dma_pm_audit_diagnostic','iommu_pm_audit_diagnostic'):
        check('missing-build-'+key,lambda b,c,im,m,i,d,key=key:b.pop(key))
    for item in config:
        check('missing-config-'+item.decode(),lambda b,c,im,m,i,d,item=item:c.remove(item))
    check('explicit-opt-out',lambda b,c,im,m,i,d:b.update(pm_edge_inventory_diagnostic=False))
    for key in prepared:
        check('bad-prepared-'+key,lambda b,c,im,m,i,d,key=key:b['pm_edge_prepared_sha256'].__setitem__(key,'0'*64))
    for kind in models:
        check('bad-native-'+kind,lambda b,c,im,m,i,d,kind=kind:m[kind].__setitem__('harness_sha256','0'*64))
        check('missing-native-proof-'+kind,lambda b,c,im,m,i,d,kind=kind:m[kind].__setitem__('actual_backend_executed',False))
    for key in ('dma','noirq','worker','suspend','edge','producer','kconfig','pm_main','iommu_driver','syscore'):
        check('bad-integration-'+key,lambda b,c,im,m,i,d,key=key:i['source_sha256'].__setitem__(key,'0'*64))
    for key in ('harness_sha256','decoder_sha256'):
        check('bad-decoder-'+key,lambda b,c,im,m,i,d,key=key:d.__setitem__(key,'0'*64))
    check('missing-decoder-proof',lambda b,c,im,m,i,d:d.__setitem__('passed',False))
    check('changed-decoder-producer-log',lambda b,c,im,m,i,d:d['producer_log_sha256'].__setitem__('producer-0.log','0'*64))
    check('missing-decoder-producer-log',lambda b,c,im,m,i,d:d['producer_log_sha256'].pop('producer-1.log'))
    check('missing-producer-hash',lambda b,c,im,m,i,d:i['source_sha256'].pop('producer'))
    check('missing-integration-outcomes',lambda b,c,im,m,i,d:i.pop('outcomes'))
    check('replaced-integration-case',lambda b,c,im,m,i,d:i['outcomes'][0].__setitem__('name','unexpected'))
    check('missing-decoder-outcomes',lambda b,c,im,m,i,d:d.pop('outcomes'))
    check('failed-decoder-case',lambda b,c,im,m,i,d:d['outcomes'][0].__setitem__('passed',False))
    check('replaced-decoder-case',lambda b,c,im,m,i,d:d['outcomes'][0].__setitem__('case','unexpected'))
    check('missing-integration-case',lambda b,c,im,m,i,d:i['outcomes'].pop())
    check('failed-integration-case',lambda b,c,im,m,i,d:i['outcomes'][0].__setitem__('passed',False))
    check('missing-decoder-case',lambda b,c,im,m,i,d:d['outcomes'].pop())
    check('changed-decoder-acceptance',lambda b,c,im,m,i,d:d['outcomes'][0].__setitem__('accepted',False))
    result={'passed':True,'cases':len(rows),'outcomes':rows,'synthetic_proof_fixtures':True,'binding_sha256':hashlib.sha256(Path(binding.__file__).read_bytes()).hexdigest(),'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(run(a.output)))
