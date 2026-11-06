"""One dedicated138 owned-XNU cycle. Exact approval required; no automatic retry."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import time
import zipfile
from v130_contract import ROOT
from v130_contract import private,read,save,sha,digest,hexid
from v138_package import validate_plan

LOGS=(('last_kmsg.txt','/proc/last_kmsg'),('console-ramoops-0','/sys/fs/pstore/console-ramoops-0'),
      ('dmesg-ramoops-0','/sys/fs/pstore/dmesg-ramoops-0'))
LEDGER_SCHEMA='note10-v138-owned-XNU-ledger-v1'
APPROVAL_SCHEMA='note10-v138-physical-approval-v1'


def decode(logs,identity,cycle):
    hexid(identity,32);hexid(cycle,32)
    result=dict(schema='note10-v138-owned-XNU-observation-v1',build_evidence_id=identity,cycle=cycle,
        previous_boot_build_cycle_observed=False,reservation_ready_observed=False,final_hook_qualified_observed=False,
        normal_recovery_fallback_observed=False,internal_kexec_load_attempts_observed=None,
        internal_kexec_REBOOT_attempts_observed=None,physical_XNU_entry_observed=False,XNU_executed=False,
        full_XNU_boot_observed=False,watchdog_reset_cause_source_validated=False,gate_refusals=[],iommu_refusal_states=[],g2d_refusal_details=[],score_refusal_details=[],npu_refusal_details=[],display_refusal_details=[],
        terminal_witness_commits=[],
        evidence_limit='Native witness commits describe per-owner terminal predicates only; no physical clock-OFF, all-master, XNU-entry/fullboot or formal reset-cause promotion')
    for name,raw in logs.items():
        if not 0<len(raw)<=16*1024*1024:continue
        text=raw.decode('utf-8',errors='replace');prefix='N10XNU138 id='+identity+' cycle='+cycle+' stage='
        begin=list(re.finditer(r'(?<![A-Za-z0-9_])'+re.escape(prefix+'begin')+r'\r?$',text,re.M))
        if len(begin)!=1:continue
        prior_barrier=False;following_barrier=False
        for barrier in re.finditer(r'(?<![A-Za-z0-9_])N10XNU[^\n]*stage=begin[^\n]*$',text,re.M):
            if barrier.start()<begin[0].start():prior_barrier=True
            elif barrier.start()>begin[0].start():following_barrier=True;break
        if following_barrier:continue
        tail=text[begin[0].start():]
        result['previous_boot_build_cycle_observed']=True
        result['reservation_ready_observed']|=not prior_barrier and ('N10XNU138 id='+identity+' fresh_owned32M platform_ready=1 xnu_pending=1') in text[:begin[0].start()]
        result['final_hook_qualified_observed']|=('N10XNU138 id='+identity+' final_qualified=1 EL1_preserved=1 actual_XNU_pending=1') in tail
        result['normal_recovery_fallback_observed']|=prefix+'normal-recovery-request' in tail
        result['internal_kexec_load_attempts_observed']=len(re.findall(re.escape(prefix+'kexec-load-once')+r'\r?$',tail,re.M))
        result['internal_kexec_REBOOT_attempts_observed']=len(re.findall(re.escape(prefix+'kexec-reboot-once')+r'\r?$',tail,re.M))
        gate_prefix=re.escape('N10XNU138 id='+identity+' ')
        for kind,domains,owner in re.findall(gate_prefix+r'terminal witness=([1-7]) domains=([0-9]{1,3}) owner=([^\r\n]{1,64})\r?$',tail,re.M):
            kind,domains=int(kind),int(domains)
            if (kind,domains) not in ((1,48),(2,64),(3,6),(4,48),(5,64),(6,8),(7,8)):continue
            commit=dict(type=kind,domains=domains,owner=owner)
            if commit not in result['terminal_witness_commits'] and len(result['terminal_witness_commits'])<4:result['terminal_witness_commits'].append(commit)
        for stage,number,owner in re.findall(gate_prefix+r'stage=([a-z0-9-]{1,32}) errno=(-?[0-9]{1,5}) owner=([^\r\n]{1,64})\r?$',tail,re.M):
            if stage not in ('usb-terminal','ufs-terminal','ufs-provider','iommu-owner','dma-provider','final','g2d-provider','g2d-record','g2d-tasks','g2d-resources','g2d-power','g2d-clock','g2d-fifo','g2d-job','g2d-clock-reference','g2d-recheck','g2d-cached','score-provider','score-record','score-users','score-lifetime','score-resources','score-power','score-reset','score-clock-reference','score-recheck','score-cached','score-cal','g2d-cal','npu-provider','npu-users','npu-lifetime','npu-resources','npu-cal','npu-power-off','npu-cached','display-freeze','display-owners','display-queues','display-access','display-decon-stop','display-dpp-reset','display-cached'):continue
            refusal=dict(stage=stage,errno=int(number),owner=owner)
            if refusal not in result['gate_refusals'] and len(result['gate_refusals'])<8:result['gate_refusals'].append(refusal)
        for controller,active,runtime,effective in re.findall(gate_prefix+r'iommu controller=([^\r\n]{1,64}) active=([01]) runtime=([01]) effective=([01])\r?$',tail,re.M):
            state=dict(controller=controller,active=int(active),runtime=int(runtime),effective=int(effective))
            if state not in result['iommu_refusal_states'] and len(result['iommu_refusal_states'])<8:result['iommu_refusal_states'].append(state)
        for reason,item,state,value,owner in re.findall(gate_prefix+r'g2d reason=([a-z0-9-]{1,24}) item=([0-9]{1,3}) state=([0-9]{1,20}) value=(-?[0-9]{1,11}) owner=([^\r\n]{1,64})\r?$',tail,re.M):
            detail=dict(reason=reason,item=int(item),state=int(state),value=int(value),owner=owner)
            if detail not in result['g2d_refusal_details'] and len(result['g2d_refusal_details'])<8:result['g2d_refusal_details'].append(detail)
        for reason,item,state,value,aux,owner in re.findall(gate_prefix+r'score reason=([a-z0-9-]{1,24}) item=([0-9]{1,3}) state=([0-9]{1,10}) value=(-?[0-9]{1,11}) aux=([0-9]{1,10}) owner=([^\r\n]{1,64})\r?$',tail,re.M):
            detail=dict(reason=reason,item=int(item),state=int(state),value=int(value),aux=int(aux),owner=owner)
            if detail not in result['score_refusal_details'] and len(result['score_refusal_details'])<8:result['score_refusal_details'].append(detail)
        for reason,item,state,value,aux,owner in re.findall(gate_prefix+r'npu reason=([a-z0-9-]{1,24}) item=([0-9]{1,3}) state=([0-9]{1,10}) value=(-?[0-9]{1,11}) aux=([0-9]{1,10}) owner=([^\r\n]{1,64})\r?$',tail,re.M):
            detail=dict(reason=reason,item=int(item),state=int(state),value=int(value),aux=int(aux),owner=owner)
            if detail not in result['npu_refusal_details'] and len(result['npu_refusal_details'])<8:result['npu_refusal_details'].append(detail)
        for reason,item,state,value,aux,owner in re.findall(gate_prefix+r'display reason=([a-z0-9-]{1,40}) item=([0-9]{1,3}) state=([0-9]{1,10}) value=(-?[0-9]{1,11}) aux=([0-9]{1,10}) owner=([^\r\n]{1,64})\r?$',tail,re.M):
            detail=dict(reason=reason,item=int(item),state=int(state),value=int(value),aux=int(aux),owner=owner)
            if detail not in result['display_refusal_details'] and len(result['display_refusal_details'])<8:result['display_refusal_details'].append(detail)
    return result


from v130_cycle import Adb as NativeAdb,preflight

class Adb(NativeAdb):
    def __init__(self,path,serial):
        super().__init__(path,serial);self.return_deadline=None
    def call(self,*args,timeout=30):
        if self.deadline is not None:raise ValueError('inherited3s deadline must stay unset')
        if self.return_deadline is not None:
            remaining=self.return_deadline-time.monotonic()
            if remaining<=0:raise subprocess.TimeoutExpired('fresh return budget',timeout)
            timeout=min(float(timeout),remaining,30)
        return super().call(*args,timeout=timeout)


def wait_return(adb,package,expected_boot,old_id,deadline,*,clock=None,sleep=None,preflight_fn=None):
    clock=clock or time.monotonic;sleep=sleep or time.sleep;preflight_fn=preflight_fn or preflight
    adb.return_deadline=deadline;candidate=None
    try:
        while clock()<deadline:
            try:
                if adb.text('shell','getprop','ro.twrp.version'):
                    value=adb.text('shell','cat','/proc/sys/kernel/random/boot_id')
                    if re.fullmatch('[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',value) and value!=old_id:
                        candidate=value;break
            except (ValueError,RuntimeError,subprocess.TimeoutExpired):pass
            sleep(min(2,max(0,deadline-clock())))
        if candidate is None:raise TimeoutError('no fresh TWRP candidate; no second write/reboot')
        new_id=preflight_fn(adb,package,expected_boot,check_battery=False)
        if new_id!=candidate or clock()>deadline:raise ValueError('fresh same-epoch return integrity required')
        return new_id
    finally:adb.return_deadline=None


def admit(plan_path,expected,approval_path,approval_sha):
    plan,package=validate_plan(plan_path,expected);approval_path=private(approval_path)
    if sha(approval_path)!=hexid(approval_sha,64):raise ValueError('exact physical review SHA required')
    row=read(approval_path)
    if (row.get('schema')!=APPROVAL_SCHEMA or row.get('decision')!='approve' or row.get('version')!='v138' or
        row.get('plan_sha256')!=expected or row.get('source_sha256')!=plan['source_sha256'] or
        row.get('cycle')!=plan['cycle'] or row.get('build_evidence_id')!=plan['build_evidence_id'] or
        row.get('bounded_actual_XNU_attempt_allowed') is not True or row.get('XNU_execution_allowed') is not True or
        row.get('battery_minimum')!=10 or row.get('host_BOOT_writes')!=1 or row.get('host_reboots')!=1 or
        row.get('internal_kexec_loads')!=1 or row.get('internal_kexec_REBOOTs')!=1 or
        row.get('normal_recovery_fallback_allowed') is not True or row.get('watchdog_automatic_reset_allowed') is not True):
        raise ValueError('exact new reviewed bounded physical proof approval required')
    if any(type(row.get(k)) is not int for k in ('battery_minimum','host_BOOT_writes','host_reboots','internal_kexec_loads','internal_kexec_REBOOTs')):
        raise ValueError('physical limits require exact integer types')
    evidence=row.get('reviewed_restore_evidence',[])
    if not isinstance(evidence,list) or not evidence:raise ValueError('reviewed physical restore/TWRP evidence references required')
    for item in evidence:
        path=private(item['path'])
        if sha(path)!=hexid(item['sha256'],64):raise ValueError('reviewed restore evidence changed')
    return plan,package


def consume(plan,plan_sha):
    directory=ROOT/'note10/private/device-test/v138-consumed-builds'
    directory.mkdir(exist_ok=True)
    if directory!=directory.resolve():raise ValueError('canonical consumed-build journal required')
    path=directory/(hexid(plan['build_evidence_id'],32)+'.json')
    save(path,dict(schema=LEDGER_SCHEMA,build_evidence_id=plan['build_evidence_id'],cycle=hexid(plan['cycle'],32),
                   plan_sha256=hexid(plan_sha,64),status='reserved-before-first-device-mutation',no_replay=True))
    return path


def collect(adb,out,identity,cycle):
    logs={}
    for name,remote in LOGS:
        try:
            adb.call('shell','test','-r',remote,timeout=5)
            raw=adb.call('exec-out','cat',remote,timeout=30)
        except (RuntimeError,subprocess.TimeoutExpired,ValueError):continue
        if 0<len(raw)<=16*1024*1024:(out/name).write_bytes(raw);logs[name]=raw
    result=decode(logs,identity,cycle)
    result['log_sha256']={name:digest(raw) for name,raw in logs.items()}
    # Raw platform reason is retained only; no unbound string becomes WDT proof.
    result['returned_recovery_bootreason_unqualified']=adb.text('shell','getprop','ro.boot.bootreason')[:256]
    save(out/'observation.json',result);return result


def run(plan_path,expected,approval_path,approval_sha,output,adb,*,execute=False):
    if not execute:raise ValueError('explicit --execute required; physical gate closed')
    plan,package=admit(plan_path,expected,approval_path,approval_sha);output=private(output)
    review=read(approval_path)
    if str(Path(adb.path).resolve())!=review.get('adb_path') or sha(adb.path)!=hexid(review.get('adb_sha256')):raise ValueError('reviewed actual ADB executable differs')
    if output.exists():raise ValueError('fresh private cycle result required')
    old_id=preflight(adb,package,package['expected_current_BOOT_sha256'])
    output.mkdir();journal=consume(plan,expected)
    ledger=dict(schema=LEDGER_SCHEMA,cycle=plan['cycle'],build_evidence_id=plan['build_evidence_id'],plan_sha256=expected,
        consumed_build_journal=str(journal),host_BOOT_write_attempts=0,host_reboot_attempts=0,
        internal_kexec_load_attempts_observed=None,internal_kexec_REBOOT_attempts_observed=None,
        normal_recovery_fallback_observed=False,watchdog_automatic_resets_observed=None,
        recovery_returned=False,old_recovery_boot_id=old_id,status='consumed',XNU_executed=False)
    def record():
        (output/'ledger.json').write_text(json.dumps(ledger,indent=2)+'\n',encoding='utf-8')
    record()
    try:
        # /tmp must be recovery-owned RAM; never DATA, EFS or a guessed partition.
        mounts=adb.text('shell','cat','/proc/mounts').splitlines()
        rows=[s.split() for s in mounts if len(s.split())>=3 and s.split()[1] in ('/','/tmp')]
        chosen=max(rows,key=lambda s:len(s[1]),default=[])
        if not chosen or chosen[2] not in ('tmpfs','ramfs','rootfs'):raise ValueError('RAM /tmp required')
        remote='/tmp/n10-v138-'+plan['cycle']+'.img'
        adb.call('shell','test','!','-e',remote)
        boot=Path(plan['packages'])/'boot.img';adb.call('push',str(boot),remote,timeout=120)
        if adb.text('shell','sha256sum',remote).split()[0]!=package['diagnostic_BOOT_sha256']:raise ValueError('RAM staging digest differs')
        # Recheck all five immediately before the single write boundary.
        preflight(adb,package,package['expected_current_BOOT_sha256'])
        node=next(r['block_node'] for r in package['partitions'] if r['partition']=='boot')
        ledger['host_BOOT_write_attempts']=1;record()
        adb.call('shell','dd','if='+remote,'of='+node,'bs=4096',timeout=120)
        adb.call('shell','sync',timeout=30)
        preflight(adb,package,package['diagnostic_BOOT_sha256'])
        ledger['host_reboot_attempts']=1;record()
        deadline=time.monotonic()+240;adb.return_deadline=deadline
        try:
            adb.call('reboot',timeout=15)
            new_id=wait_return(adb,package,package['diagnostic_BOOT_sha256'],old_id,deadline)
        finally:adb.return_deadline=None
        ledger.update(recovery_returned=True,new_recovery_boot_id=new_id,status='returned-to-TWRP-XNU-entry-unproven');record()
        observation=collect(adb,output,plan['build_evidence_id'],plan['cycle'])
        ledger['normal_recovery_fallback_observed']=observation['normal_recovery_fallback_observed']
        ledger['internal_kexec_load_attempts_observed']=observation['internal_kexec_load_attempts_observed']
        ledger['internal_kexec_REBOOT_attempts_observed']=observation['internal_kexec_REBOOT_attempts_observed']
        ledger['status']='cycle-complete-XNU-proof-limits-retained';record()
    except BaseException as error:
        ledger.update(status='failed-spent-no-retry',error_type=type(error).__name__,error=str(error)[:512]);record();raise
    return ledger


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('plan','approval','output','adb'):p.add_argument('--'+name,type=Path,required=True)
    for name in ('plan-sha256','approval-sha256','serial'):p.add_argument('--'+name,required=True)
    p.add_argument('--execute',action='store_true');a=p.parse_args()
    adb_path=a.adb.absolute()
    if adb_path!=adb_path.resolve() or not adb_path.is_file() or not a.serial or len(a.serial)>128:p.error('canonical actual ADB executable and explicit transport required')
    print(json.dumps(run(a.plan,a.plan_sha256,a.approval,a.approval_sha256,a.output,Adb(adb_path,a.serial),execute=a.execute)))
