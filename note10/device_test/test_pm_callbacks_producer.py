"""Decode actual v35 producer output and reject damage and failure frames."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
from decode_pm_callbacks import decode
HERE=Path(__file__).resolve().parent
STUB=r'''
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#define N10_RESERVE_BUILD_ID "0123456789abcdef0123456789abcdef"
#define pr_info printf
static int mode;
static unsigned int n10_frame_checksum(const char *s,int n){unsigned int h=2166136261U;while(n--)h=(h^(unsigned char)*s++)*16777619U;return h;}
'''
MOCK=r'''
int n10_cb_read(struct n10_cb_phase *p,unsigned int completed,char symbols[N10_CB_SYMBOLS][N10_CB_NAME],unsigned int *count,int *bad){unsigned i;(void)completed;*bad=0;*count=2;strcpy(symbols[0],"same_name");strcpy(symbols[1],"same_name");for(i=0;i<3;i++){p[i].generation=1;p[i].seen=1;p[i].phase=i;p[i].family[0].count=2;p[i].family[0].entry[0].priority=1;p[i].family[0].entry[0].symbol[0]=1;p[i].family[0].entry[1].priority=-5;p[i].family[0].entry[1].symbol[0]=2;p[i].family[2].count=1;p[i].family[2].entry[0].a=1;strcpy(p[i].family[2].entry[0].name,"source");p[i].family[2].entry[0].symbol[0]=1;p[i].family[2].entry[0].symbol[1]=2;p[i].family[3].count=2;strcpy(p[i].family[3].entry[0].name,i==1?"event_b":"event_a");strcpy(p[i].family[3].entry[1].name,i==1?"event_a":"event_b");p[i].family[3].entry[0].a=i;p[i].family[3].entry[0].symbol[0]=1;}if(mode==2){unsigned f,j;*count=128;for(j=0;j<128;j++){memset(symbols[j],'a'+(j%26),96);symbols[j][96]=0;}for(i=0;i<3;i++)for(f=0;f<4;f++){p[i].family[f].count=(f==0||f==2)?32:64;for(j=0;j<p[i].family[f].count;j++){memset(p[i].family[f].entry[j].name,'n',96);p[i].family[f].entry[j].name[96]=0;}}return 0;}if(mode){p[1].error=-EBUSY;p[1].family[1].attempted=1;p[1].family[1].error=-EBUSY;return -EIO;}return 0;}
'''
def clean(n):return '\n'.join(x for x in (HERE/n).read_text(encoding='utf-8-sig').splitlines() if not x.startswith('#include'))+'\n'
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);o=Path(ap.parse_args().output);o.mkdir(parents=True,exist_ok=True);src=o/'producer.c';src.write_text(STUB+clean('pm_callbacks_contract.h')+MOCK+clean('pm_callbacks_probe.c')+'\nint main(int argc,char **argv){mode=atoi(argv[1]);(void)n10_report_pm_callbacks(2,0);return 0;}\n',encoding='utf-8');compiler=Path('host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe') if sys.platform=='win32' else 'cc';exe=o/('producer.exe' if sys.platform=='win32' else 'producer');p=subprocess.run([str(compiler),'-std=gnu11','-O2',str(src),'-o',str(exe)],capture_output=True,timeout=60);(o/'compile.log').write_bytes(p.stdout+p.stderr)
 if p.returncode:raise RuntimeError(p.stderr.decode(errors='replace'))
 logs=[]
 for mode in (0,1,2):
  p=subprocess.run([str(exe),str(mode)],capture_output=True,timeout=20);assert not p.returncode; text=p.stdout.decode();(o/f'mode-{mode}.log').write_text(text,encoding='utf-8');logs.append(text)
 evidence=decode(logs[0],'0123456789abcdef0123456789abcdef',2);assert evidence['symbols']==['same_name','same_name'];assert evidence['phases'][0][3][0]['name']!=evidence['phases'][1][3][0]['name'];assert evidence['phases'][1][3][0]['a']==1;assert evidence['phases'][0][2][0]['s0']==1 and evidence['phases'][0][2][0]['s1']==2 and evidence['phases'][0][3][0]['s0']==1
 for label,text in [('failed',logs[1]),('overbudget',logs[2]),('truncated',logs[0].splitlines()[0]+'\n'),('damaged',logs[0].replace('same_name','tampered',1)),('wrong-generation',logs[0].replace('generation=1','generation=3',1))]:
  try:decode(text,'0123456789abcdef0123456789abcdef',2)
  except ValueError:continue
  raise AssertionError(label+' accepted')
 (o/'result.json').write_text(json.dumps({'source_sha256':{n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in ('pm_callbacks_contract.h','pm_callbacks_probe.c','decode_pm_callbacks.py')},'generated_c_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'log_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(o.glob('*.log'))},'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'passed':True,'outcomes':[{'case':n,'passed':True} for n in ('baseline','same_name_distinct_ids','failure','overbudget','truncated','damaged','wrong_generation')],'actual_producer':True,'same_name_distinct_ids':True,'failure_rejected':True,'overbudget_rejected':True,'hardware_verified':False},indent=2)+'\n',encoding='utf-8');print('actual producer and decoder passed')
if __name__=='__main__':main()
