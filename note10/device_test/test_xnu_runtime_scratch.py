"""New production scratch wrapper/native/parser/adapter checks; no old suites."""
import argparse
import copy
import json
from pathlib import Path
import re
import subprocess
import tempfile
import prepare_xnu_runtime_scratch as p
from prepare_xnu_runtime_observation import sha,safe_path
from decode_xnu_runtime_scratch import decode,KEYS
from test_xnu_runtime_observation import PREFIX,ram_frames,reject

NATIVE_CASES=('minimum','different-base','upper-base','refused','invalid-pages','bad-base','args-every-byte','record-every-byte','adt-every-byte','all-canaries','plan-field')
PARSER_CASES=('valid','missing','one-copy','duplicate','conflict','checksum','truncated')+tuple('field-'+key for key in KEYS if key!='copy')
DRIVER=r'''
static int ready(void) {
 unsigned long pages=N10_RT_WINDOW>>PAGE_SHIFT;
 return n10_scratch_build(pages,pages,0);
}
static void one(const char *name,uint64_t base) {
 unsigned long pages=N10_RT_WINDOW>>PAGE_SHIFT;
 n10_window_base=base;n10_window_status=1;
 printf("CASE|%s\n",name);
 n10_observe_runtime_plan(pages,pages,0);
 n10_observe_runtime_scratch(pages,pages,0);
 if(n10_window_base!=base || n10_window_status!=1)abort();
}
int main(void) {
 unsigned int i;int ok;
 one("minimum",N10_RT_MIN_BASE);
 one("different-base",UINT64_C(0x100000000));
 one("upper-base",N10_RT_LIMIT-N10_RT_WINDOW);
 n10_window_base=N10_RT_MIN_BASE;n10_window_status=0;
 printf("REJECT|refused|%d\n",ready()!=0);
 n10_window_status=1;
 printf("REJECT|invalid-pages|%d\n",n10_scratch_build(1,2,1)!=0);
 n10_window_base=N10_RT_MIN_BASE+1;
 printf("REJECT|bad-base|%d\n",ready()!=0);
 n10_window_base=N10_RT_MIN_BASE;
 ok=1;for(i=0;i<1152;i++) {if(ready())abort();n10_scratch.args[16+i]^=1;if(!n10_scratch_check())ok=0;}
 printf("REJECT|args-every-byte|%d\n",ok);
 ok=1;for(i=0;i<64;i++) {if(ready())abort();n10_scratch.record[16+i]^=1;if(!n10_scratch_check())ok=0;}
 printf("REJECT|record-every-byte|%d\n",ok);
 ok=1;for(i=0;i<56;i++) {if(ready())abort();n10_scratch.adt[16+i]^=1;if(!n10_scratch_check())ok=0;}
 printf("REJECT|adt-every-byte|%d\n",ok);
 ok=1;for(i=0;i<16;i++) {
  unsigned int j;
  for(j=0;j<6;j++) {
   uint8_t *byte;
   if(ready())abort();
   switch(j) {
    case 0:byte=n10_scratch.args+i;break;
    case 1:byte=n10_scratch.args+1168+i;break;
    case 2:byte=n10_scratch.record+i;break;
    case 3:byte=n10_scratch.record+80+i;break;
    case 4:byte=n10_scratch.adt+i;break;
    default:byte=n10_scratch.adt+72+i;break;
   }
   *byte^=1;if(!n10_scratch_check())ok=0;
  }
 }
 printf("REJECT|all-canaries|%d\n",ok);
 if(ready())abort();n10_scratch.plan.entry_physical^=4;
 printf("REJECT|plan-field|%d\n",n10_scratch_check()!=0);
 return 0;
}
'''

def native_source(prepared):
    root=Path(prepared)/'arch/arm64/mm'
    reserve=(p.HERE/'xnu_reserve.c').read_bytes();start=reserve.index(b'static u32 n10_frame_checksum(')
    end=reserve.index(b'\n}',start)+2
    source=PREFIX.encode()+b'\n#define __initdata\n#define THREAD_SIZE 16384\n'+(root/'runtime_relocation.h').read_bytes()
    source+=(root/'note10_xnu_runtime_geometry.h').read_bytes()+(root/'note10_xnu_observation_geometry.h').read_bytes()+reserve[start:end]+b'\n'
    for name in ('runtime_relocation.c','note10_xnu_runtime_plan.c','note10_xnu_runtime_observation.c','note10_xnu_runtime_scratch.c'):
        raw=(root/name).read_bytes()
        for include in (b'#include "runtime_relocation.h"\n',b'#include "note10_xnu_runtime_geometry.h"\n',b'#include "note10_xnu_observation_geometry.h"\n'):raw=raw.replace(include,b'')
        source+=raw+b'\n'
    return source+DRIVER.encode()

def decode_args(build):return ('a'*32,build['xnu_payload_sha256'],build['xnu_payload_size'],build[p.FLAG+'_geometry_sha256'])

def verify_log(text,build):
    text=text.replace('\r\n','\n')
    chunks=re.split(r'^CASE\|([^\n]+)\n',text,flags=re.M)
    if chunks[0] or tuple(chunks[1::2])!=NATIVE_CASES[:3]:raise ValueError('scratch native success case inventory differs')
    result={}
    for name,body,base in zip(chunks[1::2],chunks[2::2],(0x80000000,0x100000000,(1<<40)-0x10000000)):
        decode(ram_frames(base)+body,*decode_args(build));result[name]=True
    rejected=re.findall(r'^REJECT\|([^|]+)\|([01])$',text,re.M)
    if tuple(n for n,v in rejected)!=NATIVE_CASES[3:] or any(v!='1' for n,v in rejected):raise ValueError('production scratch rejection cases differ')
    result.update({n:True for n,v in rejected});return result

def parser_cases(text,build):
    text=text.replace('\r\n','\n')
    body=re.split(r'^CASE\|minimum\n',text,flags=re.M)[1].split('CASE|different-base\n')[0]
    text=ram_frames(0x80000000)+body;args=decode_args(build);decode(text,*args)
    lines=[line for line in text.splitlines() if line.startswith('N10XSO1 ')]
    prefix='\n'.join(line for line in text.splitlines() if not line.startswith('N10XSO1 '))+'\n'
    def change(line,key):
        raw=line.split(' ',1)[1].rsplit(' checksum=',1)[0]
        raw=re.sub(r'(?<!\S)'+key+r'=[^ ]+',key+'=invalid',raw)
        from decode_reservation import checksum
        return 'N10XSO1 '+raw+f' checksum={checksum(raw.encode()):08x}'
    results={'valid':True}
    for name in PARSER_CASES[1:]:
        chosen=list(lines)
        if name=='missing':chosen=[]
        elif name=='one-copy':chosen=chosen[:1]
        elif name=='duplicate':chosen=[chosen[0],chosen[0]]
        elif name=='conflict':chosen[1]=change(chosen[1],'base')
        elif name=='checksum':chosen[0]=chosen[0][:-1]+('0' if chosen[0][-1]!='0' else '1')
        elif name=='truncated':chosen[0]=chosen[0][:100]
        else:chosen=[change(line,name[6:]) for line in chosen]
        results[name]=reject(decode,prefix+'\n'.join(chosen),*args)
    return results

def adapter_cases(artifact,build,workspace):
    results={}
    for name in ('exact','off','duplicate','before-tamper'):
        source=workspace/name/'source';out=workspace/name/'output';out.mkdir(parents=True)
        metadata=copy.deepcopy(build)
        metadata={k:v for k,v in metadata.items() if k!=p.FLAG and not k.startswith(p.FLAG+'_')}
        metadata['reservation_source_sha256']=build['reservation_source_before_scratch_sha256']
        for n in build[p.FLAG+'_before_sha256']:
            raw=safe_path(artifact/p.BASE,n).read_bytes();dest=source/n;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
        if name=='off':
            if p.prepare(source,out,metadata,False)!={}:raise AssertionError('default off changed')
        elif name=='before-tamper':
            (source/p.prior.RESERVE).write_bytes(b'bad');reject(p.prepare,source,out,metadata,True)
        else:
            value=p.prepare(source,out,metadata,True)
            if value[p.FLAG+'_prepared_sha256']!=build[p.FLAG+'_prepared_sha256']:raise AssertionError('new adapter not reproducible')
            if name=='duplicate':reject(p.prepare,source,out,metadata,True)
        results[name]=True
    return results

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--artifact',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--cc',default='clang')
    args=parser.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=False)
    build=json.loads((args.artifact/'build-result.json').read_text());raw=native_source(args.artifact/p.PREPARED)
    (out/'native.c').write_bytes(raw)
    command=[args.cc,'-std=c11','-O2','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-unused-const-variable',str(out/'native.c'),'-o',str(out/'native')]
    completed=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(out/'compile.log').write_bytes(completed.stdout)
    if completed.returncode:raise RuntimeError('scratch focused native compile failed')
    candidates=[out/n for n in ('native','native.exe') if (out/n).is_file()]
    if len(candidates)!=1:raise RuntimeError('native executable ambiguous/missing')
    executable=candidates[0]
    completed=subprocess.run([str(executable)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(out/'native.log').write_bytes(completed.stdout)
    if completed.returncode:raise RuntimeError('scratch focused production wrapper failed')
    text=completed.stdout.decode();native=verify_log(text,build);parsers=parser_cases(text,build)
    with tempfile.TemporaryDirectory(dir=p.prior.ROOT/'note10/private') as temp:adapters=adapter_cases(args.artifact,build,Path(temp))
    result=dict(passed=True,fixture_only=True,synthetic_only=True,hardware_verified=False,physical_memory_or_hardware_accessed=False,
      source_sha256=p.source_hashes(),native_cases=native,parser_cases=parsers,adapter_cases=adapters,
      actual_production_build_and_wrapper_executed=True,files_sha256={n:sha((out/n).read_bytes()) for n in ('native.c',executable.name,'compile.log','native.log')})
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
