"""One NEW129 parser/PID1/admission batch. No old128core/entry execution."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import tarfile
import traceback
import v129_prepare as prepare
import v129_package as package
import v129_cycle as cycle
from v129_inputs import ROOT,INPUT_COMMIT,INPUT_PINS,materialize

HERE=Path(__file__).resolve().parent
SCOPE='v129-parser-fallback-package-new-only'
SOURCES=('v129_inputs.py','v129_prepare.py','v129_loader.c','v129_build.py','v129_package.py','v129_cycle.py','v129_fixture.c','test_v129_proof.py')


def reject(action):
    try:action()
    except (ValueError,FileExistsError):return
    raise ValueError('NEW boundary accepted invalid input')


def functions(raw,begin,end):
    text=raw.decode();start=text.index(begin);return text[start:text.index(end,start)]


def fixtures(out,stock,overlay,inputs):
    # Compile the actual pinned parser and the actual leading populate_rootfs
    # policy twice (option y/n), ending immediately before external initrd code.
    fragment=functions(overlay['init/initramfs.c'],'static int __initdata do_skip_initramfs;','\t/* If available load the bootloader supplied initrd */')+'\treturn 0;\n}\n'
    prefix='''#include <stdio.h>
#define __init
#define __initdata
#define __setup(a,b)
#define pr_info(...) ((void)0)
static unsigned long initrd_start,initrd_end;
static int freed,unpacked,defaulted;
static const char __initramfs_start[1]={0};
static const unsigned long __initramfs_size=1;
static void free_initrd(void){++freed;}
static int default_rootfs(void){++defaulted;return 0;}
static char *unpack_to_rootfs(const char *p,unsigned long n){(void)p;(void)n;++unpacked;return 0;}
#define panic(...) ((void)0)
'''
    fdt=stock['drivers/of/fdt.c'].decode()
    anchor='\t\tif (concat_cmdline) {'
    start=fdt.index(anchor);stop=fdt.index('\t\t} else {',start)
    concat=fdt[start:stop]+'\t\t}\n'
    prefix+='\n'.join(['#include <string.h>','#define COMMAND_LINE_SIZE 2048','#define min(a,b) ((a)<(b)?(a):(b))',
        'static unsigned long n10_strlcat(char *out,const char *src,unsigned long limit){unsigned long n=strlen(out),i=0;while(src[i] && n+i+1<limit){out[n+i]=src[i];i++;}out[n+i]=0;return n+i;}',
        '#define strlcat n10_strlcat','static void append_chosen(char *cmdline,const char *p,int l){const int concat_cmdline=1;',concat,'}'])+'\n'
    restart=functions(overlay['kernel/reboot.c'],'#ifdef CONFIG_NOTE10_LEGACY_KEXEC_RECOVERY_PROOF\nstatic int n10_proof_kernel_restart','static void kernel_shutdown_prepare')
    actual_reboot=overlay['kernel/reboot.c'].decode()
    declaration='static int n10_proof_kernel_restart(char *cmd);'
    if actual_reboot.count(declaration)!=1:raise ValueError('actual recovery helper declaration differs')
    branch=functions(overlay['kernel/reboot.c'],'\tcase LINUX_REBOOT_CMD_RESTART2:','\n#ifdef CONFIG_KEXEC_CORE')
    prefix+='''
typedef unsigned long long uint64_t;
#define current 0
#define EIO 5
#define EFAULT 14
#define KMSG_DUMP_RESTART 1
#define EXPORT_SYMBOL_GPL(name)
#define pr_emerg(...) ((void)0)
#include "v129_fixture_uapi.h"
static int marker_error,marker_calls,shutdown_calls,restart_order,restart_bad;
static int n10_sec_stage_kexec_recovery(void){++marker_calls;if(restart_order++)restart_bad=1;return marker_error;}
static void sec_debug_set_task_in_sys_reboot(uint64_t task){(void)task;}
static void kernel_restart_prepare(char *cmd){(void)cmd;++shutdown_calls;if(restart_order++!=1)restart_bad=1;}
static void migrate_to_reboot_cpu(void){if(restart_order++!=2)restart_bad=1;}
static void syscore_shutdown(void){if(restart_order++!=3)restart_bad=1;}
static void kmsg_dump(int reason){(void)reason;if(restart_order++!=4)restart_bad=1;}
static void machine_restart(char *cmd){(void)cmd;if(restart_order++!=5)restart_bad=1;}
#define CONFIG_NOTE10_LEGACY_KEXEC_RECOVERY_PROOF 1
'''+declaration+'\n'+restart+'''
static int copy_error;
static long strncpy_from_user(char *to,const char *from,unsigned long count)
{
    unsigned long n=0;
    if(copy_error)return -EFAULT;
    while(n<count && from[n]){to[n]=from[n];++n;}
    if(n<count)to[n]=0;
    return (long)n;
}
static int actual_sys_reboot_RESTART2(const char *arg)
{
    int ret=0;char buffer[256];
    switch(LINUX_REBOOT_CMD_RESTART2){
'''+branch+'''
    default:return -99;
    }
    return ret;
}
#undef CONFIG_NOTE10_LEGACY_KEXEC_RECOVERY_PROOF
'''
    enabled='#define CONFIG_NOTE10_LEGACY_KEXEC_RECOVERY_PROOF 1\n#define do_skip_initramfs yes_skip\n#define skip_initramfs_param yes_param\n#define populate_rootfs yes_populate\n'+fragment
    disabled='\n#undef CONFIG_NOTE10_LEGACY_KEXEC_RECOVERY_PROOF\n#undef do_skip_initramfs\n#undef skip_initramfs_param\n#undef populate_rootfs\n#define do_skip_initramfs no_skip\n#define skip_initramfs_param no_param\n#define populate_rootfs no_populate\n'+fragment
    end='''
#define CHECK(v) do {if(!(v))return __LINE__;}while(0)
int main(void){
 char bare[]="",value[]="=1",cmdline[2048]="rdinit=/init";
 const char dt[]="console=ttySAC0 skip_initramfs";
 append_chosen(cmdline,dt,sizeof(dt));CHECK(strcmp(cmdline,"rdinit=/init console=ttySAC0 skip_initramfs")==0);
 marker_error=-5;marker_calls=shutdown_calls=restart_order=restart_bad=0;
 CHECK(n10_proof_kernel_restart("recovery")==-EIO);CHECK(marker_calls==1 && !shutdown_calls && restart_order==1 && !restart_bad);
 marker_calls=shutdown_calls=restart_order=restart_bad=0;kernel_restart("recovery");
 CHECK(marker_calls==1 && !shutdown_calls && restart_order==1 && !restart_bad);
 marker_error=0;marker_calls=shutdown_calls=restart_order=restart_bad=0;
 CHECK(n10_proof_kernel_restart("recovery")==-EIO);CHECK(marker_calls==1 && shutdown_calls==1 && restart_order==6 && !restart_bad);
 marker_error=-5;marker_calls=shutdown_calls=restart_order=restart_bad=copy_error=0;
 CHECK(actual_sys_reboot_RESTART2("recovery")==-EIO);CHECK(marker_calls==1 && !shutdown_calls && restart_order==1 && !restart_bad);
 marker_error=0;marker_calls=shutdown_calls=restart_order=restart_bad=0;
 CHECK(actual_sys_reboot_RESTART2("recovery")==-EIO);CHECK(marker_calls==1 && shutdown_calls==1 && restart_order==6 && !restart_bad);
 marker_calls=shutdown_calls=restart_order=restart_bad=0;copy_error=1;
 CHECK(actual_sys_reboot_RESTART2("recovery")==-EFAULT);CHECK(!marker_calls && !shutdown_calls && !restart_order);
 initrd_start=123;initrd_end=456;freed=unpacked=defaulted=0;
 CHECK(yes_param(bare)==1);CHECK(yes_populate()==0);CHECK(unpacked==1 && freed==1 && !defaulted && !initrd_start && !initrd_end);
 yes_skip=0;unpacked=freed=0;CHECK(yes_param(value)==0);CHECK(!yes_skip);CHECK(yes_populate()==0 && unpacked==1 && !freed);
 initrd_start=123;initrd_end=456;freed=unpacked=defaulted=0;
 CHECK(no_param(bare)==1);CHECK(no_populate()==0);CHECK(defaulted==1 && freed==1 && !unpacked);
 no_skip=0;unpacked=freed=defaulted=0;CHECK(no_param(value)==0);CHECK(no_populate()==0 && unpacked==1 && !defaulted);
 puts("{\\"schema\\":\\"note10-v129-real-parser-fixture-v1\\",\\"passed\\":true}");return 0;
}
'''
    parser=out/'new-parser-fixture.c';parser.write_text(prefix+enabled+disabled+end,encoding='utf-8')
    # Source-bind the native syscall/UAPI contract; no platform sysroot guesses.
    unistd=stock['include/uapi/asm-generic/unistd.h'].decode();reboot=stock['include/uapi/linux/reboot.h'].decode();kexec=stock['include/uapi/linux/kexec.h'].decode()
    defs=[]
    for name in ('mount','openat','close','read','write','reboot','kexec_load'):
        value=re.search(r'^#define __NR_'+name+r'\s+([0-9]+)\s*$',unistd,re.M)
        if not value:raise ValueError('actual generic syscall macro differs')
        defs.append('#define __NR_'+name+' '+value[1])
    for name in ('LINUX_REBOOT_MAGIC1','LINUX_REBOOT_MAGIC2','LINUX_REBOOT_CMD_RESTART2','LINUX_REBOOT_CMD_KEXEC'):
        value=re.search(r'^#define\s+'+name+r'\s+(0x[0-9a-fA-F]+|[0-9]+)\s*$',reboot,re.M)
        if not value:raise ValueError('actual reboot UAPI macro differs')
        defs.append('#define '+name+' '+value[1])
    if re.search(r'#define\s+KEXEC_ARCH_AARCH64\s+\(183\s*<<\s*16\)',kexec) is None:raise ValueError('actual KEXEC UAPI flag differs')
    defs.extend(['#define KEXEC_ARCH_AARCH64 (183UL<<16)','struct kexec_segment {const void *buf; __UINT64_TYPE__ bufsz; const void *mem; __UINT64_TYPE__ memsz;};'])
    (out/'v129_fixture_uapi.h').write_text('\n'.join(defs)+'\n',encoding='utf-8')
    (out/'legacy_kexec_build.h').write_text('#define N10_KEXEC_BUILD_ID "'+'1'*32+'"\nstatic unsigned long n10_test_cookie_offset;\n#define N10_PARK_COOKIE_OFFSET n10_test_cookie_offset\nstatic const unsigned char n10_park_bytes[16]={0};\n',encoding='utf-8')
    return parser,HERE/'v129_fixture.c'


def synthetic_admission(out,source_map):
    synthetic=out/'synthetic-only';synthetic.mkdir();build=synthetic/'build';build.mkdir();back=synthetic/'backup';back.mkdir();folder=synthetic/'packages';folder.mkdir()
    identity='1'*32;token='2'*32
    cpio=b'NEW129_SYNTHETIC_CPIO_NOT_HARDWARE'+package.DISABLED
    image=bytearray(128);image[56:60]=b'ARM\x64';image=bytes(image)+cpio
    config='\n'.join(['CONFIG_NOTE10_LEGACY_KEXEC_RECOVERY_PROOF=y','CONFIG_INITRAMFS_FORCE=y','CONFIG_CMDLINE_EXTEND=y','CONFIG_CMDLINE="rdinit=/init"','CONFIG_KEXEC=y','CONFIG_KEXEC_CORE=y','CONFIG_ARM64_4K_PAGES=y'])+'\n'
    for name,raw in [('Image',image),('actual-effective.config',config.encode()),('minimal-init.elf',b'synthetic-PID1'),('park.bin',b'synthetic-park'),('initramfs.cpio',cpio)]: (build/name).write_bytes(raw)
    row=dict(schema='note10-v129-kexec-host-build-v1',version='v129',passed=True,immutable_input_commit=INPUT_COMMIT,
        immutable_input_sha256=INPUT_PINS,execution_slot_enabled=False,skip_external_only_policy=True,common_PID1_RESTART2_recovery=True,
        early_recovery_marker_before_shutdown=True,marker_failure_aborts_shutdown=True,
        XNU_execution_allowed=False,source_sha256=source_map,build_evidence_id=identity,retained_NEW_PASS_operator_binding=dict(schema='note10-v129-retained-new-test-pass-v1',passed=True))
    for name,key in [('Image','Image_sha256'),('actual-effective.config','effective_config_sha256'),('minimal-init.elf','PID1_sha256'),('park.bin','park_sha256'),('initramfs.cpio','initramfs_cpio_sha256')]:row[key]=package.sha(build/name)
    package.save(build/'result.json',row)
    rows=[]
    for i,name in enumerate(sorted(package.PARTITIONS)):
        raw=bytes([i+1])*4096;(back/(name+'.img')).write_bytes(raw)
        rows.append(dict(partition=name,block_node='/dev/block/sda'+str(i+1),size=len(raw),file=name+'.img',sha256=package.digest(raw),remote_hash_before_and_after_match=True))
    package.save(back/'backup-manifest.json',dict(complete=True,partition_writes=False,bootloader='N976NKSU2HWH5',partitions=rows))
    enabled=package.enable(image,token);boot=bytearray(4096);boot[:8]=b'ANDROID!';struct.pack_into('<10I',boot,8,len(enabled),0,0,0,0,0,0,2048,1,0);struct.pack_into('<IQI',boot,1632,0,0,1648);boot[2048:2048+len(enabled)]=enabled;boot=bytes(boot)
    (folder/'boot.img').write_bytes(boot)
    rollback=(back/'boot.img').read_bytes()
    for file,raw,mode in [('proof.zip',boot,'proof'),('rollback.zip',rollback,'rollback')]:package.zip_package(folder/file,raw,dict(schema=package.SCHEMA,cycle=token,mode=mode,BOOT_sha256=package.digest(raw)))
    metadata=dict(schema=package.SCHEMA,cycle=token,build_evidence_id=identity,source_sha256=source_map,XNU_execution_allowed=False,build=str(build),backup=str(back),
        build_result_sha256=package.sha(build/'result.json'),backup_manifest_sha256=package.sha(back/'backup-manifest.json'),partitions=rows,
        input_Image_sha256=package.digest(image),enabled_Image_sha256=package.digest(enabled),BOOT_cmdline='',diagnostic_BOOT_sha256=package.digest(boot),rollback_BOOT_sha256=package.digest(rollback),
        expected_current_BOOT_sha256=package.digest(rollback),
        proof_zip_sha256=package.sha(folder/'proof.zip'),rollback_zip_sha256=package.sha(folder/'rollback.zip'))
    package.save(folder/'package-result.json',metadata)
    plan=dict(schema=package.PLAN_SCHEMA,version='v129',cycle=token,build_evidence_id=identity,packages=str(folder),package_result_sha256=package.sha(folder/'package-result.json'),minimum_battery=10,return_timeout_seconds=240,
        host_BOOT_write_limit=1,host_reboot_limit=1,internal_kexec_load_limit=1,internal_kexec_REBOOT_limit=1,XNU_execution_allowed=False,source_sha256=source_map)
    path=folder/'plan.json';package.save(path,plan);package.validate_plan(path,package.sha(path))
    rejects=0
    for key,value in [('minimum_battery',9),('host_BOOT_write_limit',2),('host_reboot_limit',2),('internal_kexec_load_limit',2),('XNU_execution_allowed',True),('cycle','bad')]:
        bad={**plan,key:value};candidate=folder/('bad-'+key+'.json');package.save(candidate,bad);reject(lambda:package.validate_plan(candidate,package.sha(candidate)));rejects+=1
    reject(lambda:package.validate_plan(path,'0'*64));rejects+=1
    reject(lambda:package.enable(enabled,token));rejects+=1
    package.require_paired_BOOT(package.digest(rollback),rollback)
    reject(lambda:package.require_paired_BOOT(package.digest(boot),rollback));rejects+=1
    original_package=(folder/'package-result.json').read_bytes()
    mismatched={**metadata,'expected_current_BOOT_sha256':package.digest(boot)}
    (folder/'package-result.json').write_text(json.dumps(mismatched,indent=2)+'\n',encoding='utf-8')
    mismatch_plan={**plan,'package_result_sha256':package.sha(folder/'package-result.json')}
    candidate=folder/'bad-paired-baseline.json';package.save(candidate,mismatch_plan)
    reject(lambda:package.validate_plan(candidate,package.sha(candidate)));rejects+=1
    (folder/'package-result.json').write_bytes(original_package)

    reject(lambda:package.verify_pins({'note10/device_test/v129_loader.c':'0'*64}));rejects+=1
    approval=folder/'approval.json';package.save(approval,dict(schema=cycle.APPROVAL_SCHEMA,decision='approve',version='v129'))
    reject(lambda:cycle.admit(path,package.sha(path),approval,package.sha(approval)));rejects+=1
    # Consume only an injected synthetic journal directory, never production ledger.
    original=cycle.ROOT;cycle.ROOT=synthetic
    (synthetic/'note10/private/device-test').mkdir(parents=True)
    try:
        cycle.consume(plan,package.sha(path));reject(lambda:cycle.consume(plan,package.sha(path)));rejects+=1
    finally:cycle.ROOT=original
    good=('N10KRES1 id='+identity+' bytes=33554432 generation=1 ready=1 xnu=0\nN10KEXEC129 id='+identity+' cycle='+token+' event=begin\nN10KRET1 id='+identity+' marker_readback=1 wdt_qualified=1 first=100 last=99 timeout=30 physical_park_pending=1 xnu=0\n').encode()
    seen=cycle.decode({'synthetic':good},identity,token)
    if not seen['final_hook_qualified_observed'] or seen['physical_park_entry_observed'] or seen['watchdog_to_TWRP_proven']:raise ValueError('honest late-boundary decoder differs')
    if cycle.decode({'synthetic':good},identity,'3'*32)['previous_boot_build_cycle_observed']:raise ValueError('stale cycle log admitted')
    if cycle.decode({'synthetic':good+good},identity,token)['final_hook_qualified_observed']:raise ValueError('ambiguous duplicate log admitted')
    fallback=good+('N10KEXEC129 id='+identity+' cycle='+token+' event=normal-recovery-request\n').encode()
    if not cycle.decode({'synthetic':fallback},identity,token)['normal_recovery_fallback_observed']:raise ValueError('fallback classification differs')
    return dict(rejections=rejects,hardware_operations=0,synthetic_only=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--scope',required=True,choices=(SCOPE,));p.add_argument('--output',required=True,type=Path)
    p.add_argument('--compiler',type=Path,default=ROOT/'host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe');p.add_argument('--compiler-arg',action='append',default=[])
    p.add_argument('--archive',required=True,type=Path);a=p.parse_args();out=package.private(a.output)
    compiler=a.compiler.absolute()
    if out.exists() or not a.compiler.is_absolute() or compiler!=compiler.resolve() or not compiler.is_file():p.error('fresh private output and explicit canonical compiler required')
    out.mkdir();source_map={'note10/device_test/'+name:package.sha(HERE/name) for name in SOURCES}
    result=dict(schema='note10-v129-new-proof-test-v1',scope=SCOPE,passed=False,run=1,source_sha256={name:package.sha(HERE/name) for name in SOURCES},
                immutable_input_sha256=INPUT_PINS,compiler=dict(path=str(compiler),sha256=package.sha(compiler)),compiler_args=a.compiler_arg,
                fixture_compiles=0,fixture_processes=0,old128core_runs=0,old_entry_runs=0,Image_builds=0,device_operations=[],XNU_execution_allowed=False)
    try:
        if package.sha(a.archive)!=package.ARCHIVE_SHA:raise ValueError('kernel input archive differs')
        inputs=materialize(out/'immutable128-source');_,pins=prepare.setup(inputs)
        extra=('include/uapi/asm-generic/unistd.h','include/uapi/linux/reboot.h','include/uapi/linux/kexec.h')
        with tarfile.open(a.archive,'r:gz') as tar:
            stock={name:tar.extractfile('android_kernel_samsung_universal9820-'+package.COMMIT+'/'+name).read() for name in (*pins,*extra)}
        overlay=prepare.render(stock,'1'*32,inputs)
        recovery=overlay['kernel/reboot.c']
        declaration=b'static int n10_proof_kernel_restart(char *cmd);'
        definition=b'static int n10_proof_kernel_restart(char *cmd)\n'
        caller=b'ret = n10_proof_kernel_restart(buffer);'
        if recovery.count(declaration)!=1 or recovery.count(definition)!=1 or not recovery.index(declaration)<recovery.index(definition)<recovery.index(caller):
            raise ValueError('actual rendered recovery declaration/definition/caller order differs')
        if not recovery.index(b'n10_sec_stage_kexec_recovery()')<recovery.index(b'\tkernel_restart_prepare(cmd);'):
            raise ValueError('actual recovery marker must precede notifier/device shutdown')
        if b'ret = n10_proof_kernel_restart(buffer);' not in recovery or b'return -EIO;' not in recovery:
            raise ValueError('actual RESTART2 marker-failure error propagation missing')
        if b'n10_wdt_stage_kexec_return' in recovery:raise ValueError('early WDT start not allowed')
        if overlay['init/main.c'].count(b'            msleep(1000);')!=1 or overlay['init/main.c'].count(b'        msleep(1000);')<1:
            raise ValueError('returned kernel init recovery must park without panic/retry')
        bad=dict(stock);bad['init/initramfs.c']+=b'\n';reject(lambda:prepare.render(bad,'1'*32,inputs))
        fdt=stock['drivers/of/fdt.c']
        if b'#elif defined(CONFIG_CMDLINE_EXTEND)' not in fdt or b'p = of_get_flat_dt_prop(node, "bootargs", &l);' not in fdt or b'strncpy(cmdline + cmdline_len, p, copy_len);' not in fdt:raise ValueError('actual CMDLINE_EXTEND path differs')
        # Same effective string passed to the actual extracted parser fixture.
        cmdline='rdinit=/init'+' '+'console=ttySAC0 skip_initramfs'
        if 'skip_initramfs' not in cmdline.split():raise ValueError('bare incoming skip token lost')
        parser,pid1=fixtures(out,stock,overlay,inputs)
        for name,source in [('parser',parser),('PID1',pid1)]:
            exe=out/(name+('.exe' if os.name=='nt' else ''))
            command=[str(compiler),'-std=c11','-O0','-Wall','-Wextra','-Werror','-fno-builtin','-fno-stack-protector','-I',str(out),'-I',str(HERE),'-I',str(inputs/'note10/device_test'),str(source),'-o',str(exe),*a.compiler_arg]
            package.save(out/(name+'-compile-command.json'),command);result['fixture_compiles']+=1
            done=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=120);(out/(name+'-compile.log')).write_text(done.stdout+done.stderr)
            if done.returncode:raise ValueError('NEW129 '+name+' compile failed')
            result['fixture_processes']+=1;ran=subprocess.run([str(exe)],cwd=ROOT,capture_output=True,text=True,timeout=30)
            (out/(name+'-stdout.json')).write_text(ran.stdout);(out/(name+'-stderr.log')).write_text(ran.stderr)
            if ran.returncode or json.loads(ran.stdout).get('passed') is not True:raise ValueError('NEW129 '+name+' fixture failed')
        result['admission']=synthetic_admission(out,source_map)
        result.update(passed=True,overlay_sha256={name:package.digest(raw) for name,raw in overlay.items()},actual_bootargs_source_sha256=package.digest(fdt))
    except Exception:result['error']=traceback.format_exc()
    package.save(out/'result.json',result);print(json.dumps(dict(passed=result['passed'],fixture_compiles=result['fixture_compiles'],fixture_processes=result['fixture_processes'])))
    return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
