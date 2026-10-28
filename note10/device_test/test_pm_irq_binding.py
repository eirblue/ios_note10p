"""Read-only-scope and proof tamper checks for CPU0 IRQ binding."""
import argparse,copy,hashlib,json,shutil
from pathlib import Path
from run_probe import ROOT
from prepare_pm_irq import HERE,PINS,SOURCES
import pm_irq_binding as binding
import pm_edge_binding as edge

def run(output,source_root,native,decoder,integration,edge_artifact):
 out=Path(output).resolve();source=Path(source_root)
 if out.exists() or not out.is_relative_to((ROOT/'note10/private').resolve()):raise ValueError('Fresh private binding output required')
 out.mkdir(parents=True)
 sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
 paths=('include/linux/note10_pm_irq.h','kernel/power/note10_pm_irq.c','drivers/irqchip/note10_pm_irq_gic.c','arch/arm64/mm/note10_pm_irq_probe.c','kernel/power/note10_pm_cpus.c','arch/arm64/mm/note10_pm_timer_roundtrip.c','drivers/irqchip/irq-gic.c','kernel/power/suspend.c','kernel/power/Kconfig')
 prepared={p:sha(source/p) for p in paths}
 build={'pm_irq_diagnostic':True,'pm_irq_evidence_version':1,'pm_irq_source_pins':PINS,'pm_irq_sources_sha256':{n:sha(HERE/n) for n in SOURCES},'pm_irq_prepared_sha256':prepared,'pm_quiesce_patched_sha256':{'kernel/power/Kconfig':prepared['kernel/power/Kconfig']},'pm_edge_prepared_sha256':{'kernel/power/note10_pm_noirq.c':sha(source/'kernel/power/note10_pm_noirq.c')},**{k:True for k in ('pm_cpus_diagnostic','pm_post_arch_diagnostic','pm_edge_inventory_diagnostic','gic_roundtrip_diagnostic')}}
 config=[b'CONFIG_NOTE10_PM_IRQ_TEST=y',b'CONFIG_NOTE10_PM_CPUS_TEST=y',b'CONFIG_NOTE10_PM_POST_ARCH=y',b'CONFIG_NOTE10_PM_EDGE_INVENTORY=y',b'CONFIG_NOTE10_GIC_ROUNDTRIP=y',b'CONFIG_ARM_GIC=y',b'CONFIG_ARM64_4K_PAGES=y',b'CONFIG_PREEMPT_COUNT=y',b'CONFIG_ARM64_VA_BITS=39',b'CONFIG_PGTABLE_LEVELS=3',b'# CONFIG_UNMAP_KERNEL_AT_EL0 is not set',b'# CONFIG_ARM64_SW_TTBR0_PAN is not set']
 image=b' '.join(binding.MARKERS)
 models={}
 for name,path in [('native',native),('decoder',decoder),('integration',integration)]:
  models[name]=json.loads((Path(path)/'result.json').read_text())
 for name,path in [('native',native),('decoder',decoder),('integration',integration)]:
  d=out/('pm-irq-'+name+'-model');d.mkdir()
  for p in Path(path).glob('*.log'):shutil.copyfile(p,d/p.name)
 rows=[]
 def check(name,mutate=None,accept=False):
  b=copy.deepcopy(build);c=config.copy();im=image;m=copy.deepcopy(models)
  if mutate:
   x=mutate(b,c,im,m)
   if isinstance(x,bytes):im=x
  (out/'handoff.config').write_bytes(b'\n'.join(c)+b'\n');(out/'Image').write_bytes(im)
  for k,v in m.items():(out/('pm-irq-'+k+'-model')/'result.json').write_text(json.dumps(v),encoding='utf-8')
  try:ok=binding.validate_model(out,b) is True
  except (ValueError,OSError,KeyError,TypeError) as e:
   if accept:raise ValueError('Valid proof rejected: '+str(e)) from e
   ok=False
  if ok!=accept:raise ValueError('Binding acceptance differs: '+name)
  rows.append({'name':name,'accepted':ok,'passed':True})
 check('valid',accept=True)
 for name in ('GIC_NON_BANKED','TRACE_IRQFLAGS','DEBUG_SNAPSHOT_IRQ_DISABLED','DEBUG_SNAPSHOT_REG'):
  check('unset-'+name,lambda b,c,im,m,name=name:c.append(('# CONFIG_'+name+' is not set').encode()),accept=True)
 check('trace-support-is-not-trace-enabled',lambda b,c,im,m:c.append(b'CONFIG_TRACE_IRQFLAGS_SUPPORT=y'),accept=True)
 for marker in binding.MARKERS:check('missing-marker-'+marker.decode(),lambda b,c,im,m,marker=marker:im.replace(marker,b''))
 for key in ('pm_irq_diagnostic','pm_irq_evidence_version','pm_irq_source_pins','pm_irq_sources_sha256','pm_irq_prepared_sha256','pm_cpus_diagnostic','pm_post_arch_diagnostic','pm_edge_inventory_diagnostic','gic_roundtrip_diagnostic'):
  check('missing-build-'+key,lambda b,c,im,m,key=key:b.pop(key))
 for item in config:check('missing-config-'+item.decode(),lambda b,c,im,m,item=item:c.remove(item))
 check('explicit-opt-out',lambda b,c,im,m:b.update(pm_irq_diagnostic=False))
 check('metadata-null',lambda b,c,im,m:b.update(pm_irq_diagnostic=None))
 check('metadata-false-config-removed',lambda b,c,im,m:(b.update(pm_irq_diagnostic=False),c.remove(b'CONFIG_NOTE10_PM_IRQ_TEST=y')))
 check('metadata-null-config-removed',lambda b,c,im,m:(b.update(pm_irq_diagnostic=None),c.remove(b'CONFIG_NOTE10_PM_IRQ_TEST=y')))
 check('metadata-false-image-removed',lambda b,c,im,m:(b.update(pm_irq_diagnostic=False),b'')[1])
 for name in ('GIC_NON_BANKED','TRACE_IRQFLAGS','DEBUG_SNAPSHOT_IRQ_DISABLED','DEBUG_SNAPSHOT_REG'):
  for value in ('y','m'):check('forbidden-'+name+'-'+value,lambda b,c,im,m,name=name,value=value:c.append(('CONFIG_'+name+'='+value).encode()))
 for key in prepared:check('bad-prepared-'+key,lambda b,c,im,m,key=key:b['pm_irq_prepared_sha256'].__setitem__(key,'0'*64))
 for kind in models:
  check('missing-model-'+kind,lambda b,c,im,m,kind=kind:m[kind].__setitem__('passed',False))
  check('bad-harness-'+kind,lambda b,c,im,m,kind=kind:m[kind].__setitem__('harness_sha256','0'*64))
  check('missing-outcome-'+kind,lambda b,c,im,m,kind=kind:m[kind]['outcomes'].pop())
  check('failed-outcome-'+kind,lambda b,c,im,m,kind=kind:m[kind]['outcomes'][0].__setitem__('passed',False))
 check('changed-integration-case',lambda b,c,im,m:m['integration']['outcomes'][0].__setitem__('name','bogus'))
 check('missing-integration-source',lambda b,c,im,m:m['integration']['source_sha256'].pop('irq'))
 check('bad-integration-source',lambda b,c,im,m:m['integration']['source_sha256'].__setitem__('gic','0'*64))
 check('bad-decoder-source',lambda b,c,im,m:m['decoder'].__setitem__('decoder_sha256','0'*64))
 check('bad-native-log',lambda b,c,im,m:m['decoder']['native_log_sha256'].__setitem__('mode-0.log','0'*64))
 # Reuse actual previous edge model records, with v34 config and new metadata layered on top.
 edge_artifact=Path(edge_artifact)
 from prepare_pm_edge import SOURCES as EDGE_SOURCES, PINS as EDGE_PINS
 edge_src=json.loads((edge_artifact/'pm-edge-integration-model/result.json').read_text())['source_sha256']
 edge_prepared={'drivers/base/power/note10_dma_pm.c':edge_src['dma'],'kernel/power/note10_pm_noirq.c':edge_src['noirq'],'arch/arm64/mm/note10_pm_timer_roundtrip.c':edge_src['worker'],'kernel/power/suspend.c':edge_src['suspend'],'kernel/power/Kconfig':edge_src['kconfig'],'drivers/base/power/main.c':edge_src['pm_main'],'drivers/iommu/exynos-iommu.c':edge_src['iommu_driver'],'drivers/base/syscore.c':edge_src['syscore'],'drivers/base/power/note10_pm_edge_dma.c':edge_src['edge'],'drivers/iommu/note10_pm_edge_iommu.c':sha(HERE/'pm_edge_iommu_backend.c'),'drivers/base/note10_pm_edge_syscore.c':sha(HERE/'pm_edge_syscore_backend.c'),'arch/arm64/mm/note10_pm_edge_probe.c':edge_src['producer'],**{'include/linux/note10_pm_edge_'+k+'.h':sha(HERE/('pm_edge_'+k+'_contract.h')) for k in ('dma','iommu','syscore')}}
 eb=copy.deepcopy(build);eb.update({'pm_edge_inventory_evidence_version':1,'dma_pm_audit_diagnostic':True,'iommu_pm_audit_diagnostic':True,'pm_edge_source_pins':EDGE_PINS,'pm_edge_sources_sha256':{n:sha(HERE/n) for n in EDGE_SOURCES},'pm_edge_prepared_sha256':edge_prepared})

 for kind in ('dma','iommu','syscore','integration','decoder'):
  shutil.copytree(edge_artifact/('pm-edge-'+kind+'-model'),out/('pm-edge-'+kind+'-model'))
 ec=config+[b'CONFIG_KALLSYMS=y',b'CONFIG_NOTE10_DMA_PM_AUDIT=y',b'CONFIG_NOTE10_IOMMU_PM_AUDIT=y']
 eimage=image+b' '+b' '.join(edge.MARKERS)
 def layer(name,flag='keep',drop_config=False,drop_image=False,accept=False):
  b=copy.deepcopy(eb);c=ec.copy();im=eimage
  if flag=='missing':b.pop('pm_irq_diagnostic',None)
  elif flag=='false':b['pm_irq_diagnostic']=False
  elif flag=='null':b['pm_irq_diagnostic']=None
  if drop_config:c.remove(b'CONFIG_NOTE10_PM_IRQ_TEST=y')
  if drop_image:
   for marker in binding.MARKERS:im=im.replace(marker,b'')
  # Attempt to masquerade as v33 by reverting the other metadata's Kconfig hash.
  if flag!='keep':b['pm_quiesce_patched_sha256']['kernel/power/Kconfig']=b['pm_edge_prepared_sha256']['kernel/power/Kconfig']
  (out/'handoff.config').write_bytes(b'\n'.join(c)+b'\n');(out/'Image').write_bytes(im)
  try:ok=edge.validate_model(out,b) is True
  except (ValueError,OSError,KeyError,TypeError) as e:
   if accept:raise ValueError('Valid layered proof rejected: '+str(e)) from e
   ok=False
  if ok!=accept:raise ValueError('Layered binding differs: '+name)
  rows.append({'name':'layer-'+name,'accepted':ok,'passed':True})
 layer('valid',accept=True)
 layer('v33-disabled',flag='false',drop_config=True,drop_image=True,accept=True)
 for flag in ('missing','false','null'):
  layer(flag,flag=flag)
  layer(flag+'-config-removed',flag=flag,drop_config=True)
  layer(flag+'-image-removed',flag=flag,drop_image=True)
 result={'passed':True,'cases':len(rows),'outcomes':rows,'source_fixture_is_synthetic':True,'harness_sha256':sha(Path(__file__)),'binding_sha256':sha(Path(binding.__file__))}
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');return result

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('output','source-root','native','decoder','integration','edge-artifact'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();print(json.dumps(run(a.output,a.source_root,a.native,a.decoder,a.integration,a.edge_artifact)))
