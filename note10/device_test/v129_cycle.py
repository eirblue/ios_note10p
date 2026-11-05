"""One dedicated129 proof cycle. No old cycle/profile imports or automatic retry."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import time
import zipfile
from v129_inputs import ROOT
from v129_package import private,read,save,sha,digest,hexid,validate_plan,backup

LOGS=(('last_kmsg.txt','/proc/last_kmsg'),('console-ramoops-0','/sys/fs/pstore/console-ramoops-0'),
      ('dmesg-ramoops-0','/sys/fs/pstore/dmesg-ramoops-0'))
LEDGER_SCHEMA='note10-v129-proof-ledger-v1'
APPROVAL_SCHEMA='note10-v129-physical-approval-v1'


def decode(logs,identity,cycle):
    hexid(identity,32);hexid(cycle,32)
    result=dict(schema='note10-v129-proof-observation-v1',build_evidence_id=identity,cycle=cycle,
        previous_boot_build_cycle_observed=False,reservation_ready_observed=False,final_hook_qualified_observed=False,
        normal_recovery_fallback_observed=False,physical_park_entry_observed=False,
        watchdog_reset_cause_source_validated=False,watchdog_to_TWRP_proven=False,XNU_executed=False,
        evidence_limit='N10KRET1 precedes native transfer; own RAM park word has no retained read channel')
    for name,raw in logs.items():
        if not 0<len(raw)<=16*1024*1024:continue
        text=raw.decode('utf-8',errors='replace')
        start=re.escape('N10KEXEC129 id='+identity+' cycle='+cycle+' event=begin')
        begin=list(re.finditer(start+r'\r?$',text,re.M))
        # Repeated target begin records in one log are ambiguous/stale, not proof.
        if len(begin)!=1:continue
        tail=text[begin[0].start():]
        if re.search(r'N10KEXEC129 id=[0-9a-f]{32} cycle=[0-9a-f]{32} event=begin',tail[len(begin[0].group()):]):continue
        result['previous_boot_build_cycle_observed']=True
        prefix=text[:begin[0].start()]
        ready='N10KRES1 id='+identity+' bytes=33554432 generation=1 ready=1 xnu=0'
        result['reservation_ready_observed']|=ready in prefix
        final=re.search(r'N10KRET1 id='+re.escape(identity)+r' marker_readback=1 wdt_qualified=1 first=([0-9]+) last=([0-9]+) timeout=([0-9]+) physical_park_pending=1 xnu=0',tail)
        if final:
            first,last,timeout=map(int,final.groups())
            if 0<last<first<=65535 and 1<=timeout<=30:
                result['final_hook_qualified_observed']=True;result['qualified_log_source']=name
        fallback='N10KEXEC129 id='+identity+' cycle='+cycle+' event=normal-recovery-request'
        result['normal_recovery_fallback_observed']|=fallback in tail
    if result['normal_recovery_fallback_observed']:
        result['watchdog_to_TWRP_proven']=False
    return result


class Adb:
    def __init__(self,path,serial):self.path=str(path);self.serial=serial;self.deadline=None
    def call(self,*args,timeout=30):
        if self.deadline is not None:
            remaining=self.deadline-time.monotonic()
            if remaining<=0:raise subprocess.TimeoutExpired('bounded recovery wait',timeout)
            timeout=min(timeout,remaining,3)
        done=subprocess.run([self.path,'-s',self.serial,*args],cwd=ROOT,capture_output=True,timeout=timeout)
        if done.returncode:raise RuntimeError('ADB '+args[0]+' failed; no retry')
        return done.stdout
    def text(self,*args,**kwargs):return self.call(*args,**kwargs).decode('utf-8',errors='strict').strip()


def preflight(adb,package,expected_boot,*,check_battery=True):
    if (not adb.text('shell','getprop','ro.twrp.version') or adb.text('shell','id','-u')!='0' or
        adb.text('shell','uname','-m')!='aarch64' or adb.text('shell','getprop','ro.product.device') not in ('d2x','d2xks') or
        adb.text('shell','getprop','ro.bootloader')!=package['bootloader']):raise ValueError('paired root d2x TWRP required')
    if check_battery:
        battery=adb.text('shell','cat','/sys/class/power_supply/battery/capacity')
        if re.fullmatch('[0-9]{1,3}',battery) is None or not 10<=int(battery)<=100:raise ValueError('battery10 gate failed')
    for row in package['partitions']:
        name=row['partition'];node=row['block_node']
        if adb.text('shell','readlink','-f','/dev/block/by-name/'+name)!=node or adb.text('shell','blockdev','--getsize64',node)!=str(row['size']):
            raise ValueError('live partition canonical node/size differs: '+name)
        observed=adb.text('shell','sha256sum',node).split()
        expected=expected_boot if name=='boot' else row['sha256']
        if not observed or observed[0]!=expected:raise ValueError('live partition digest differs: '+name)
    value=adb.text('shell','cat','/proc/sys/kernel/random/boot_id')
    if re.fullmatch('[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',value) is None:raise ValueError('boot ID unavailable')
    return value


def admit(plan_path,expected,approval_path,approval_sha):
    plan,package=validate_plan(plan_path,expected);approval_path=private(approval_path)
    if sha(approval_path)!=hexid(approval_sha,64):raise ValueError('exact physical review SHA required')
    row=read(approval_path)
    if (row.get('schema')!=APPROVAL_SCHEMA or row.get('decision')!='approve' or row.get('version')!='v129' or
        row.get('plan_sha256')!=expected or row.get('source_sha256')!=plan['source_sha256'] or
        row.get('cycle')!=plan['cycle'] or row.get('build_evidence_id')!=plan['build_evidence_id'] or
        row.get('physical_inert_park_proof_allowed') is not True or row.get('XNU_execution_allowed') is not False or
        row.get('battery_minimum')!=10 or row.get('host_BOOT_writes')!=1 or row.get('host_reboots')!=1 or
        row.get('internal_kexec_loads')!=1 or row.get('internal_kexec_REBOOTs')!=1 or
        row.get('normal_recovery_fallback_allowed') is not True or row.get('watchdog_automatic_reset_allowed') is not True):
        raise ValueError('exact new reviewed bounded physical proof approval required')
    evidence=row.get('reviewed_restore_evidence',[])
    if not isinstance(evidence,list) or not evidence:raise ValueError('reviewed physical restore/TWRP evidence references required')
    for item in evidence:
        path=private(item['path'])
        if sha(path)!=hexid(item['sha256'],64):raise ValueError('reviewed restore evidence changed')
    return plan,package


def consume(plan,plan_sha):
    directory=ROOT/'note10/private/device-test/v129-consumed-builds'
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
        except (RuntimeError,subprocess.TimeoutExpired):continue
        if 0<len(raw)<=16*1024*1024:(out/name).write_bytes(raw);logs[name]=raw
    result=decode(logs,identity,cycle)
    result['log_sha256']={name:digest(raw) for name,raw in logs.items()}
    # Raw platform reason is retained only; no unbound string becomes WDT proof.
    result['returned_recovery_bootreason_unqualified']=adb.text('shell','getprop','ro.boot.bootreason')[:256]
    save(out/'observation.json',result);return result


def run(plan_path,expected,approval_path,approval_sha,output,adb,*,execute=False):
    if not execute:raise ValueError('explicit --execute required; physical gate closed')
    plan,package=admit(plan_path,expected,approval_path,approval_sha);output=private(output)
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
        remote='/tmp/n10-v129-'+plan['cycle']+'.img'
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
        ledger['host_reboot_attempts']=1;record();adb.call('reboot',timeout=15)
        deadline=time.monotonic()+240;adb.deadline=deadline
        while time.monotonic()<deadline:
            try:
                new_id=preflight(adb,package,package['diagnostic_BOOT_sha256'],check_battery=False)
                if new_id!=old_id:break
            except (ValueError,RuntimeError,subprocess.TimeoutExpired):pass
            time.sleep(min(2,max(0,deadline-time.monotonic())))
        else:raise TimeoutError('no fresh TWRP return; stop without second write/reboot')
        adb.deadline=None
        ledger.update(recovery_returned=True,new_recovery_boot_id=new_id,status='returned-to-TWRP-not-reset-proof');record()
        observation=collect(adb,output,plan['build_evidence_id'],plan['cycle'])
        ledger['normal_recovery_fallback_observed']=observation['normal_recovery_fallback_observed']
        ledger['status']='cycle-complete-proof-limits-retained';record()
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
