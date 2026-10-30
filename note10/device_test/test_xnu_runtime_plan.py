"""New v55 host-wrapper/preparer checks only; never executes a kernel object."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
sys.dont_write_bytecode=True
from unittest.mock import patch
import prepare_xnu_runtime_plan as prepare

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


PREFIX=r'''
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdarg.h>
#include <stdlib.h>
#include "runtime_relocation.h"
#include "note10_xnu_runtime_geometry.h"
#define __init
#define __used __attribute__((used))
#define noinline __attribute__((noinline))
#define PAGE_SHIFT 12
#define N10_RESERVE_BUILD_ID "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
typedef uint32_t u32;
static uint64_t n10_window_base;
static int n10_window_status;
static unsigned int planner_calls, mode, frames;
static char log_bytes[2048];
static unsigned int log_used;
static int scnprintf(char *out,size_t capacity,const char *format,...)
{
 va_list args;int result;va_start(args,format);result=vsnprintf(out,capacity,format,args);va_end(args);
 return result<0?result:((size_t)result>=capacity?(int)capacity-1:result);
}
static void pr_info(const char *format,...)
{
 va_list args;int result;va_start(args,format);
 result=vsnprintf(log_bytes+log_used,sizeof(log_bytes)-log_used,format,args);va_end(args);
 if(result<0 || (unsigned int)result>=sizeof(log_bytes)-log_used)abort();log_used+=(unsigned int)result;frames++;
}
int n10_rt_plan(const struct n10_rt_request *in,struct n10_rt_plan *out)
{
 planner_calls++;
 if(in->physical_base!=n10_window_base || in->window_size!=N10_RT_WINDOW ||
  in->image_virtual!=N10_RTP_IMAGE_VA || in->image_size!=N10_RTP_IMAGE_SIZE ||
  in->entry_virtual!=N10_RTP_ENTRY_VA || in->synthetic_adt!=1 || in->adt_length!=56 || !in->adt ||
  in->reserved || in->occupied || in->reserved_count || in->occupied_count ||
  in->command_line || in->command_length)abort();
 if(in->adt[0]!=1 || memcmp(in->adt+8,"name",4) || memcmp(in->adt+44,"device-tree",11))abort();
 memset(out,0,sizeof(*out));
 if(mode==1){memset(out,0xa5,sizeof(*out));return -7;}
 out->physical_base=in->physical_base;out->window_size=in->window_size;
 out->virtual_ram_base=N10_RTP_VIRTUAL_BASE;out->image_virtual=in->image_virtual;
 out->image_size=in->image_size;out->entry_virtual=in->entry_virtual;
 out->kernel_physical=in->physical_base+N10_RTP_KERNEL_OFFSET;
 out->entry_physical=in->physical_base+N10_RTP_ENTRY_OFFSET;
 out->kernel_end=in->physical_base+N10_RTP_END_OFFSET;
 out->arguments_physical=in->physical_base;out->device_tree_physical=in->physical_base+N10_RT_PAGE;
 out->device_tree_virtual=N10_RTP_VIRTUAL_BASE+N10_RT_PAGE;out->adapter_physical=in->physical_base+2*N10_RT_PAGE;
 out->mapping_blocks=7;out->kernel_blocks=2;out->adt_length=56;
 if(mode>=10 && mode<26)((unsigned char *)out)[8*(mode-10)]^=1;
 return 0;
}
'''
DRIVER=r'''
static int one(const char *name,uint64_t base,int reservation,unsigned long reserved,
 unsigned long count,unsigned long invalid,unsigned int testmode,int expected,unsigned int calls)
{
 int result;n10_window_base=base;n10_window_status=reservation;mode=testmode;
 planner_calls=frames=log_used=0;memset(log_bytes,0,sizeof(log_bytes));
 result=n10_xnu_runtime_plan_check(reserved,count,invalid);
 if(result!=expected || planner_calls!=calls || frames!=2 || n10_window_base!=base || n10_window_status!=reservation)return 1;
 printf("CASE|%s|%d|%u\n%s",name,result,planner_calls,log_bytes);return 0;
}
int main(void)
{
 unsigned int i;char name[64];unsigned long pages=(unsigned long)(N10_RT_WINDOW>>PAGE_SHIFT);
 if(one("minimum-current-base",N10_RT_MIN_BASE,1,pages,pages,0,0,0,1))return 1;
 if(one("distinct-current-base",UINT64_C(0x100000000),1,pages,pages,0,0,0,1))return 1;
 if(one("upper-current-base",N10_RT_LIMIT-N10_RT_WINDOW,1,pages,pages,0,0,0,1))return 1;
 if(one("status-zero",UINT64_C(0x100000000),0,pages,pages,0,0,-1,0))return 1;
 if(one("status-error",UINT64_C(0x100000000),-2,pages,pages,0,0,-1,0))return 1;
 if(one("status-unknown",UINT64_C(0x100000000),2,pages,pages,0,0,-1,0))return 1;
 if(one("below-minimum",N10_RT_MIN_BASE-N10_RT_BLOCK,1,pages,pages,0,0,-2,0))return 1;
 if(one("misaligned-base",N10_RT_MIN_BASE+1,1,pages,pages,0,0,-2,0))return 1;
 if(one("extent-above-limit",N10_RT_LIMIT-N10_RT_WINDOW+N10_RT_BLOCK,1,pages,pages,0,0,-2,0))return 1;
 if(one("base-overflow",UINT64_MAX&~(N10_RT_BLOCK-1),1,pages,pages,0,0,-2,0))return 1;
 if(one("count-zero",N10_RT_MIN_BASE,1,0,0,0,0,-3,0))return 1;
 if(one("count-partial",N10_RT_MIN_BASE,1,pages-1,pages-1,0,0,-3,0))return 1;
 if(one("count-oversize",N10_RT_MIN_BASE,1,pages+1,pages+1,0,0,-3,0))return 1;
 if(one("reserved-partial",N10_RT_MIN_BASE,1,pages-1,pages,0,0,-3,0))return 1;
 if(one("invalid-page",N10_RT_MIN_BASE,1,pages,pages,1,0,-3,0))return 1;
 if(one("planner-failure-garbage",N10_RT_MIN_BASE,1,pages,pages,0,1,-4,1))return 1;
 for(i=0;i<16;i++){
  snprintf(name,sizeof(name),"plan-field-%u",i);
  if(one(name,N10_RT_MIN_BASE,1,pages,pages,0,10+i,-5,1))return 1;
 }
 return 0;
}
'''


def checksum(raw):
    value=2166136261
    for byte in raw:value=((value^byte)*16777619)&0xffffffff
    return value


def function(raw,signature):
    start=raw.index(signature);brace=raw.index(b'{',start);depth=0
    for at in range(brace,len(raw)):
        if raw[at:at+1]==b'{':depth+=1
        elif raw[at:at+1]==b'}':
            depth-=1
            if not depth:return raw[start:at+1]
    raise ValueError('unterminated checksum source')


def parse_frame(line):
    import re
    match=re.fullmatch(r'N10XRP1 (.*) checksum=([0-9a-f]{8})',line)
    if not match:raise ValueError('bounded computational frame syntax')
    body,digest=match.groups()
    if len(body)>=256 or checksum(body.encode())!=int(digest,16):raise ValueError('frame length/checksum')
    fields=[item.split('=',1) for item in body.split(' ')]
    if any(len(item)!=2 for item in fields) or [item[0] for item in fields]!=['id','copy','status','kernel','entry','end','mapped','spans','synthetic','materialized']:
        raise ValueError('computational frame schema')
    row=dict(fields)
    if row['id']!='a'*32 or row['copy'] not in ('0','1') or row['synthetic']!='1' or row['materialized']!='0':raise ValueError('frame identity/scope')
    status=int(row['status']);offsets=[int(row[name],16) for name in ('kernel','entry','end')]
    counts=[int(row[name]) for name in ('mapped','spans')]
    if status not in (0,-1,-2,-3,-4,-5):raise ValueError('frame status')
    if status==0 and (offsets!=[0x1004000,0x1340490,0x22b0000] or counts!=[7,2]):raise ValueError('computed offsets differ')
    if status and (any(offsets) or any(counts)):raise ValueError('rejected plan contents published')
    return row


def check_wrapper_source():
    import re
    raw=(HERE/'xnu_runtime_plan.c').read_text()
    if raw.count('n10_rt_plan(&request,&plan)')!=1 or any(name in raw for name in ('n10_rt_build(', 'n10_rt_serialize_', 'memblock_', 'readl(', 'writel(', '__va(', 'phys_to_virt(', 'read_sysreg(', 'asm(')):
        raise ValueError('wrapper exceeds planner-only source scope')
    if raw.index('n10_window_status!=1')>raw.index('base=(uint64_t)n10_window_base') or raw.index('reserved!=count')>raw.index('n10_rt_plan(&request,&plan)'):
        raise ValueError('current reservation/page guards no longer precede planning')
    return {'single_planner_call':True,'no_materialization_or_hardware_call':True,'current_boot_base_guarded':True}


def reject(call,*args,**kwargs):
    try:call(*args,**kwargs)
    except (ValueError,FileNotFoundError):return True
    raise AssertionError('invalid source preparation accepted')


def preparer_cases(pristine,output,manifest):
    results={};input_init=prepare.file(pristine,prepare.INIT).read_bytes();input_config=prepare.file(pristine,prepare.KCONFIG).read_bytes()
    canonical=manifest.read_bytes().replace(b'\r\n',b'\n')
    for encoding,raw in (('LF',canonical),('CRLF',canonical.replace(b'\n',b'\r\n'))):
        path=output/('manifest-'+encoding+'.json');path.write_bytes(raw)
        if prepare.validate_manifest(path)!=prepare.validate_manifest(manifest):raise AssertionError('canonical geometry differs by accepted encoding')
        results['manifest-'+encoding]=True
    for encoding,raw in (('mixed',canonical.replace(b'\n',b'\r\n',1)),('lone-CR',canonical.replace(b'\n',b'\r',1))):
        path=output/('manifest-'+encoding+'.json');path.write_bytes(raw)
        results['manifest-reject-'+encoding]=reject(prepare.validate_manifest,path)
    def fixture(label):
        source=output/label
        for name,raw in ((prepare.INIT,input_init),(prepare.KCONFIG,input_config)):
            path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        baseline=prepare.canonical_reservation(source)
        return source,baseline
    source,baseline=fixture('disabled');before={name:prepare.file(source,name).read_bytes() for name in (prepare.INIT,prepare.RESERVE,prepare.KCONFIG)}
    off=prepare.prepare(source,baseline,manifest)
    if off['enabled'] is not False or before!={name:prepare.file(source,name).read_bytes() for name in before}:raise AssertionError('default-off modified canonical reservation-only source/config')
    results['default-off-byte-identical']=True
    source,baseline=fixture('enabled');on=prepare.prepare(source,baseline,manifest,True)
    if on['enabled'] is not True or not prepare.file(source,prepare.KCONFIG).read_bytes().endswith(prepare.BLOCK):raise AssertionError('enabled default-n config/source closure absent')
    for name,digest in on['after_sha256'].items():
        if prepare.sha(prepare.file(source,name).read_bytes())!=digest:raise AssertionError('copied production source hash differs')
    results['enabled-hash-bound-copy']=True;results['duplicate-insertion']=reject(prepare.prepare,source,baseline,manifest,True)
    for label in ('changed-init','changed-reservation','changed-config','changed-id','changed-provenance','writer-present','manifest-pin','opt-in-none','opt-in-string','production-pin'):
        source,baseline=fixture(label);chosen=manifest;enabled=True
        if label=='changed-init':path=source/prepare.INIT;path.write_bytes(path.read_bytes()+b'\n')
        elif label=='changed-reservation':path=source/prepare.RESERVE;path.write_bytes(path.read_bytes()+b'\n')
        elif label=='changed-config':path=source/prepare.KCONFIG;path.write_bytes(path.read_bytes()+b'\n')
        elif label=='changed-id':baseline['reservation_build_id']='b'*32
        elif label=='changed-provenance':baseline['older_preparer_executed']=True
        elif label=='writer-present':(source/'arch/arm64/mm/note10_xnu_payload_stage.c').write_bytes(b'writer')
        elif label=='manifest-pin':chosen=output/'changed-manifest.json';chosen.write_bytes(manifest.read_bytes()+b'\n')
        elif label=='opt-in-none':enabled=None
        elif label=='opt-in-string':enabled='false'
        before={name:prepare.file(source,name).read_bytes() for name in (prepare.INIT,prepare.RESERVE,prepare.KCONFIG)}
        if label=='production-pin':
            changed=output/'changed-runtime.c';changed.write_bytes(b'not v54 C')
            with patch.dict(prepare.COPIES,{'runtime_relocation.c':changed}):results[label]=reject(prepare.prepare,source,baseline,chosen,enabled)
        else:results[label]=reject(prepare.prepare,source,baseline,chosen,enabled)
        if before!={name:prepare.file(source,name).read_bytes() for name in before}:raise AssertionError('rejection changed source/config')
    return results


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kernel-source',type=Path,required=True)
    parser.add_argument('--payload-manifest',type=Path,default=HERE/'xnu_runtime_plan_payload.json')
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--cc',default='clang')
    args=parser.parse_args();private=(ROOT/'note10/private').resolve();destination=args.output.resolve();input_root=args.kernel_source.resolve()
    if (args.output.exists() or args.output.is_symlink() or not destination.is_relative_to(private) or
        destination==private or destination.is_relative_to(input_root) or input_root.is_relative_to(destination)):
        raise ValueError('fresh private wrapper output must be disjoint from source input')
    manifest=prepare.validate_manifest(args.payload_manifest);args.output.mkdir(parents=True)
    temporary=args.output/'tmp';temporary.mkdir();environment=dict(os.environ,TMP=str(temporary.resolve()),TEMP=str(temporary.resolve()),TMPDIR=str(temporary.resolve()))
    header=prepare.geometry_header(manifest);(args.output/prepare.GEOMETRY).write_bytes(header)
    checksum_source=function((HERE/'xnu_reserve.c').read_bytes(),b'static u32 n10_frame_checksum(')
    generated=PREFIX.encode()+checksum_source+b'\n'+(HERE/'xnu_runtime_plan.c').read_bytes()+DRIVER.encode()
    code=args.output/'host-wrapper.c';code.write_bytes(generated)
    binary=args.output/('host-wrapper.exe' if os.name=='nt' else 'host-wrapper')
    compiled=subprocess.run([args.cc,'-std=c11','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'note10/xnu26'),'-I',str(args.output),str(code),'-o',str(binary)],capture_output=True,env=environment,timeout=120)
    (args.output/'compile.log').write_bytes(compiled.stdout+compiled.stderr)
    if compiled.returncode:raise ValueError('new host-wrapper compile failed')
    ran=subprocess.run([str(binary.resolve())],capture_output=True,env=environment,timeout=30)
    (args.output/'wrapper.log').write_bytes(ran.stdout+ran.stderr)
    if ran.returncode or ran.stderr:raise ValueError('new host-wrapper cases failed')
    lines=ran.stdout.decode('ascii').splitlines();cases=[]
    for index in range(0,len(lines),3):
        if len(lines[index:index+3])!=3 or not lines[index].startswith('CASE|'):raise ValueError('wrapper case transcript malformed')
        first,second=parse_frame(lines[index+1]),parse_frame(lines[index+2])
        if first['copy']!='0' or second['copy']!='1' or {k:v for k,v in first.items() if k!='copy'}!={k:v for k,v in second.items() if k!='copy'}:raise ValueError('wrapper report copies conflict')
        cases.append(lines[index].split('|')[1])
    if len(cases)!=32 or len(set(cases))!=32:raise ValueError('new wrapper case inventory differs')
    negatives={}
    for label,line in (('checksum',lines[1][:-1]+('0' if lines[1][-1]!='0' else '1')),('truncated',lines[1][:20]),('materialized',lines[1].replace('materialized=0','materialized=1'))):
        negatives[label]=reject(parse_frame,line)
    source_scope=check_wrapper_source();preparer=preparer_cases(args.kernel_source,args.output,args.payload_manifest)
    result={'passed':True,'verdict':'host-wrapper and canonical-preparer evidence only','wrapper_cases':cases,'frame_mutations':negatives,
        'preparer_cases':preparer,'source_scope':source_scope,'host_executable_sha256':prepare.sha(binary.read_bytes()),
        'host_source_sha256':prepare.sha(generated),'wrapper_source_sha256':prepare.sha((HERE/'xnu_runtime_plan.c').read_bytes()),
        'geometry_sha256':prepare.sha(header),'actual_kernel_object_executed':False,'production_planner_executed_in_host':False,
        'old_v54_native_abi_entry_or_pm_suites_replayed':False,'physical_reservation_verified':False,
        'materialized':False,'hardware_verified':False,'deployment_ready':False,'device_operations':[]}
    (args.output/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'passed':True,'wrapper_cases':len(cases),'preparer_cases':len(preparer),'actual_kernel_object_executed':False}))


if __name__=='__main__':main()
