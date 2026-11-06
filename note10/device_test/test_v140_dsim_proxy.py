'One NEW exact DSIM proxy/catalog/lifetime/protocol batch; old DPU suites0.'
import argparse,json,re,subprocess,sys
from pathlib import Path
sys.dont_write_bytecode=True
from v130_contract import ROOT,private,ordinary,digest,hexid,save
from v135_metadata import encode_public
import v140_prepare as prepare
import v140_build as build
import v140_package as package
import v140_cycle as cycle
HERE=Path(__file__).resolve().parent
CAL_SHA='f89dca2d21db09e106a4199222db5d084d9ec68203a40b62eee6ced91d18b7af'
PRIOR_FILE_SHA='4489928b216806e2d40d2ac14ecd94e5803cf6aa15a2d7d8a8ac79e1de337f28'
PRIOR_RESULT_SHA='f9f22f8b9ed80c170e9a18db7f4443a7043bf11894856a2c22e8bbd0a7e82d18'
C_PREFIX=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <errno.h>
typedef uint32_t u32;
typedef uint64_t resource_size_t;
#define ARRAY_SIZE(v) (sizeof(v)/sizeof((v)[0]))
#define READ_ONCE(v) (v)
#define smp_store_release(p,v) (*(p)=(v))
#define smp_load_acquire(p) (*(p))
#define pr_emerg(...) ((void)0)
#define N10_KEXEC_BUILD_ID "0123456789abcdef0123456789abcdef"
#include <linux/v138_display.h>
#define N138_SLOTS 12
#define DECON_OUT_DSI 0
#define DSI_MODE_SINGLE 0
struct task_struct {int id;};
static struct task_struct own={1},foreign={2},*fixture_task=&own;
static struct task_struct *get_current(void){return fixture_task;}
#define current get_current()
static bool fixture_irq;
static bool in_interrupt(void){return fixture_irq;}
typedef struct {bool held;} spinlock_t;
static spinlock_t n138_lock;
#define spin_lock_irqsave(p,f) do{assert(!(p)->held);(p)->held=true;(f)=0;}while(0)
#define spin_unlock_irqrestore(p,f) do{assert((p)->held);(p)->held=false;(void)(f);}while(0)
struct resource {resource_size_t start,end;};
static resource_size_t resource_size(const struct resource *res){return res->end-res->start+1;}
struct device_node {const char *compatible;bool available;int alias,refs,count;u32 cells,cal_id;struct resource res;struct device_node *links[3],*domain;};
struct device {struct device_node *of_node;};
struct v4l2_subdev {void *data;};
struct dsim_device {int id;struct v4l2_subdev sd;};
struct decon_device {int id;struct {int out_type,dsi_mode,out_idx[2];} dt;struct v4l2_subdev *out_sd[2],*dsim_sd[2];};
static struct decon_device primary,*decon_drvdata[3];
static struct dsim_device dsim;
static struct device_node dsim_node,dp_node,other_dsim,controllers[3],power_node;
static struct device devices[N138_SLOTS];
static struct n138_slot n138_slots[N138_SLOTS];
static struct n136_witness n138_witness;
static struct task_struct *n138_core_owner;
static bool n138_final_seen,n138_seen,n138_complete,n138_closed;
static int n138_final_result,n138_result;
static unsigned int n138_active,n138_history;
static bool frozen=true,extra_node;
static unsigned int metadata_reads,record_calls,unwinds;
static int recorded,forced_record_error,downstream_error;
static struct n138_slot *n138_find(unsigned int family,unsigned int id)
{static const unsigned int offsets[]={0,3,9,10};assert(family<4 && id<(family==0?3:family==1?6:family==2?1:2));return &n138_slots[offsets[family]+id];}
static bool n136_cal_frozen_stub(unsigned int domains){return frozen && domains==8;}
bool n136_cal_frozen(unsigned int domains){return n136_cal_frozen_stub(domains);}
static void *v4l2_get_subdevdata(struct v4l2_subdev *sd){return sd->data;}
static const char *dev_name(struct device *dev){assert(dev==&devices[10]);return "synthetic-dsim";}
static int n130_dma_record(struct device *dev,int result)
{assert(dev==&devices[10]);record_calls++;recorded=result?result:forced_record_error;return recorded;}
static void n131_gate_refused(const char *stage,int error,struct device *dev)
{assert(!strcmp(stage,"dsim-proxy") && error && dev==&devices[10]);}
static bool of_device_is_available(struct device_node *node){return node && node->available;}
static bool of_device_is_compatible(struct device_node *node,const char *name){return node && !strcmp(node->compatible,name);}
static int of_alias_get_id(struct device_node *node,const char *name){assert(!strcmp(name,"dsim"));return node->alias;}
static void of_node_put(struct device_node *node){if(node){assert(node->refs>0);node->refs--;}}
static struct device_node *next_dsim(struct device_node *previous)
{struct device_node *next=previous==NULL?&dsim_node:previous==&dsim_node && extra_node?&other_dsim:NULL;of_node_put(previous);if(next)next->refs++;return next;}
#define for_each_compatible_node(n,t,c) for((void)(c),(n)=next_dsim(NULL);(n);(n)=next_dsim(n))
static int of_property_count_u32_elems(struct device_node *node,const char *name)
{assert(!strcmp(name,"iommus"));metadata_reads++;return node->count;}
static struct device_node *of_parse_phandle(struct device_node *node,const char *name,unsigned int index)
{struct device_node *answer;metadata_reads++;if(!strcmp(name,"iommus"))answer=index<3?node->links[index]:NULL;else {assert(!strcmp(name,"samsung,power-domain") && index==0);answer=node->domain;}if(answer)answer->refs++;return answer;}
static int of_property_read_u32(struct device_node *node,const char *name,u32 *answer)
{metadata_reads++;if(!strcmp(name,"#iommu-cells"))*answer=node->cells;else {assert(!strcmp(name,"cal_id"));*answer=node->cal_id;}return 0;}
static int of_address_to_resource(struct device_node *node,unsigned int index,struct resource *answer)
{assert(index==0);metadata_reads++;*answer=node->res;return 0;}
/* N140_ACTUAL_CATALOG */
#define N140_DECON_NATIVE
#define N140_DSIM_CATALOG
#include "v140_dsim.inc"
int n138_display_final(void){return n138_final_result;}
static int n130_iommu_prepare(void){return downstream_error;}
int n138_display_unwind(void)
{unsigned int i;if(n138_core_owner!=current)return -EPERM;for(i=0;i<N138_SLOTS;i++)n138_slots[i].device_locked=false;n138_core_owner=NULL;unwinds++;return 0;}
/* N140_AFTER_SHUTDOWN */
'''
C_MAIN=r'''
static void setup(unsigned int parent_type)
{
 unsigned int i;fixture_task=&own;fixture_irq=false;frozen=true;extra_node=false;
 metadata_reads=record_calls=unwinds=0;recorded=forced_record_error=downstream_error=0;
 memset(&primary,0,sizeof(primary));memset(&dsim,0,sizeof(dsim));memset(devices,0,sizeof(devices));
 memset(n138_slots,0,sizeof(n138_slots));memset(&n140_dsim_witness,0,sizeof(n140_dsim_witness));memset(&n140_dsim_detail,0,sizeof(n140_dsim_detail));
 n140_dsim_seen=false;n140_dsim_result=-ENOENT;n138_lock.held=false;
 n138_core_owner=current;n138_final_seen=n138_seen=n138_complete=n138_closed=true;n138_final_result=n138_result=0;n138_active=n138_history=0;
 memset(&dsim_node,0,sizeof(dsim_node));memset(&dp_node,0,sizeof(dp_node));memset(&power_node,0,sizeof(power_node));memset(controllers,0,sizeof(controllers));memset(&other_dsim,0,sizeof(other_dsim));
 dsim_node.compatible=other_dsim.compatible="samsung,exynos9-dsim";dsim_node.available=other_dsim.available=true;other_dsim.alias=1;
 dsim_node.count=dp_node.count=3;devices[10].of_node=&dsim_node;devices[9].of_node=&dp_node;
 power_node.compatible="samsung,exynos-pd";power_node.available=true;power_node.cal_id=0xb1380003;
 power_node.res=(struct resource){0x15861e00,0x15861e1f};
 for(i=0;i<3;i++){
  controllers[i].compatible="samsung,exynos-sysmmu";controllers[i].available=true;controllers[i].domain=&power_node;
  controllers[i].res=(struct resource){0x190a0000+(resource_size_t)i*0x10000,0x190a8fff+(resource_size_t)i*0x10000};
  dsim_node.links[i]=dp_node.links[i]=&controllers[i];
 }
 for(i=0;i<N138_SLOTS;i++)if(i!=1 && i!=11){
  n138_slots[i].dev=&devices[i];n138_slots[i].lifetime=N138_BOUND;n138_slots[i].probe_completed=n138_slots[i].device_locked=true;
  n138_slots[i].generation=n138_slots[i].frozen_generation=2;n138_slots[i].stopped=parent_type==6;
 }
 n138_slots[10].family=N138_DSIM;n138_slots[10].object=&dsim;n138_slots[0].object=&primary;
 primary.out_sd[0]=primary.dsim_sd[0]=&dsim.sd;dsim.sd.data=&dsim;decon_drvdata[0]=&primary;
 n138_witness=(struct n136_witness){&devices[9],parent_type,8,true};
}
static void refs_balanced(void)
{unsigned int i;assert(!dsim_node.refs && !dp_node.refs && !other_dsim.refs && !power_node.refs);for(i=0;i<3;i++)assert(!controllers[i].refs);}
static void own_locks_held(void)
{unsigned int i;for(i=0;i<N138_SLOTS;i++)if(n138_slots[i].lifetime)assert(n138_slots[i].device_locked);}
int main(void)
{
 unsigned int reads,calls;struct n136_witness invalid={0};
 setup(6);assert(n140_dsim_final()==0 && recorded==0 && record_calls==1);
 assert(n140_dsim_witness.owner==&devices[10] && n140_dsim_witness.type==8 && n140_dsim_witness.domains==8);
 reads=metadata_reads;calls=record_calls;assert(n140_dsim_final()==0 && metadata_reads==reads && record_calls==calls);refs_balanced();own_locks_held();
 setup(7);assert(n140_dsim_final()==0 && n140_dsim_witness.type==9);refs_balanced();own_locks_held();
 assert(n136_witness_commit(&invalid,&devices[10],8,48)==-EPERM && !invalid.committed);
 setup(6);n138_slots[3].stopped=false;assert(n140_dsim_final()==-EPERM && !metadata_reads && !n140_dsim_witness.committed);own_locks_held();
 setup(6);n138_history=4;assert(n140_dsim_final()==-EPERM && !metadata_reads);own_locks_held();
 setup(6);n138_active=1;assert(n140_dsim_final()==-EPERM && !metadata_reads);
 setup(6);fixture_task=&foreign;assert(n140_dsim_final()==-EPERM && !metadata_reads);own_locks_held();
 setup(6);fixture_irq=true;assert(n140_dsim_final()==-EPERM && !metadata_reads);own_locks_held();
 setup(6);n138_slots[10].generation++;n138_slots[10].object=(void *)(uintptr_t)1;
 assert(n140_dsim_final()==-ENODEV && !metadata_reads && !n140_dsim_witness.committed);own_locks_held();
 setup(6);n138_slots[10].device_locked=false;n138_slots[10].object=(void *)(uintptr_t)1;
 assert(n140_dsim_final()==-ENODEV && !metadata_reads && !n140_dsim_witness.committed);
 setup(6);n138_slots[11].lifetime=N138_BOUND;assert(n140_dsim_final()==-ENODEV && !metadata_reads);
 setup(6);primary.out_sd[0]=NULL;assert(n140_dsim_final()==-ENODEV && !metadata_reads && !strcmp(n140_dsim_detail.reason,"dsim-proxy-output"));refs_balanced();
 setup(6);dsim.sd.data=NULL;assert(n140_dsim_final()==-ENODEV && !n140_dsim_witness.committed);refs_balanced();
 setup(6);extra_node=true;assert(n140_dsim_final()==-ENODEV && !metadata_reads);refs_balanced();
 setup(6);dsim_node.count=4;assert(n140_dsim_final()==-ENODEV && !n140_dsim_witness.committed);refs_balanced();
 setup(6);dp_node.links[1]=&controllers[0];assert(n140_dsim_final()==-ENODEV && n140_dsim_detail.item==1);refs_balanced();
 setup(6);controllers[0].cells=1;assert(n140_dsim_final()==-ENODEV && n140_dsim_detail.state==1);refs_balanced();
 setup(6);controllers[1].res.start++;assert(n140_dsim_final()==-ENODEV && n140_dsim_detail.item==1 && n140_dsim_detail.state==0x190b0001);refs_balanced();
 setup(6);power_node.cal_id=0xb1380004;assert(n140_dsim_final()==-ENODEV && n140_dsim_detail.state==0xb1380004);refs_balanced();
 setup(6);frozen=false;assert(n140_dsim_final()==-ENODEV && !metadata_reads);
 setup(6);forced_record_error=-ENOSPC;assert(n140_dsim_final()==-ENOSPC && recorded==-ENOSPC && n140_dsim_result==-ENOSPC);own_locks_held();refs_balanced();
 /* Only the new downstream failure integration; inherited DPU work is mocked. */
 setup(6);primary.out_sd[0]=NULL;assert(n130_after_shutdown()==-ENODEV && unwinds==1 && !n138_core_owner);
 setup(6);downstream_error=-EIO;assert(n130_after_shutdown()==-EIO && unwinds==1 && !n138_core_owner && n138_closed);
 return 0;
}
'''
KERNEL_SEED=b'''int n130_after_shutdown(void)
{
    int result=0;
    if(!result)result=n138_display_final();
    if(!result)result=n130_iommu_prepare();
    if(result)(void)n138_display_unwind();
    return result;
}
'''


def new_output(cal):
    seed={prepare.CAL_PATH:cal,'include/linux/v138_display.h':(HERE/'v138_display.h').read_bytes(),prepare.BASE+'decon_core.c':b'/* retained native DECON boundary */\n',prepare.BASE+'v138_display.c':b'/* retained aggregate boundary */\n','arch/arm64/mm/v130_kernel.c':KERNEL_SEED,'include/linux/v130_kernel_api.h':b'int n138_display_final(void);\n'}
    original=prepare.retained.render;prepare.retained.render=lambda stock,identity,source128:dict(seed)
    try:return prepare.render({},'a'*32,HERE)
    finally:prepare.retained.render=original


def cases(output):
    kernel=output['arch/arm64/mm/v130_kernel.c'];assert kernel.index(b'n138_display_final()')<kernel.index(b'n140_dsim_final()')<kernel.index(b'n130_iommu_prepare()')<kernel.index(b'n138_display_unwind()')
    assert b'N140_DSIM_PROXY_NATIVE_FROZEN' in output[prepare.CAL_PATH] and b'N140_DSIM_PROXY_OFF_FROZEN' in output[prepare.CAL_PATH]
    assert b'0xb1380003' in output[prepare.NATIVE_PATH] and b'0xb1400003' not in output[prepare.NATIVE_PATH]
    assert len(package.CURRENT139_SOURCE_SHA256)==94 and package.CURRENT139_SOURCE_SHA256==build.RETAINED_SOURCE_SHA256
    source=(HERE/'v140_package.py').read_text();assert 'current139_package' in source and 'current137_package' not in source
    loader=build.pid1_source();assert set(re.findall(rb'N10XNU[0-9]+',loader))=={b'N10XNU140'}
    source=(HERE/'v140_build.py').read_text();assert source.index('        loader=pid1_source()')<source.index("(out/'v140_loader.c').write_bytes(loader)")<source.index("result['PID1_source_sha256']=digest(loader)")<source.index("'00-new-PID1'")
    identity,cycle_id='a'*32,'b'*32;prefix='N10XNU140 id='+identity+' cycle='+cycle_id+' stage=begin\n'
    lines=''.join('N10XNU140 id='+identity+' terminal witness='+str(kind)+' domains='+str(domains)+' owner=synthetic'+str(kind)+'\n' for kind,domains in ((4,48),(3,6),(5,64),(6,8),(8,8)))
    detail='N10XNU140 id='+identity+' stage=dsim-proxy errno=-19 owner=synthetic8\nN10XNU140 id='+identity+' display reason=dsim-proxy-output item=0 state=0 value=-19 aux=0 owner=synthetic8\n'
    decoded=cycle.decode({'new':(prefix+lines+detail).encode()},identity,cycle_id)
    assert len(decoded['terminal_witness_commits'])==5 and decoded['terminal_witness_commits'][-1]['type']==8
    assert decoded['gate_refusals']==[dict(stage='dsim-proxy',errno=-19,owner='synthetic8')]
    assert decoded['display_refusal_details'][0]['reason']=='dsim-proxy-output'
    assert len(cycle.decode({'new':(prefix+lines+lines.replace('witness=8','witness=9')).encode()},identity,cycle_id)['terminal_witness_commits'])==5
    bad='N10XNU140 id='+identity+' terminal witness=8 domains=48 owner=synthetic\n';assert not cycle.decode({'new':(prefix+bad).encode()},identity,cycle_id)['terminal_witness_commits']
    off='N10XNU140 id='+identity+' terminal witness=9 domains=8 owner=synthetic\n';assert cycle.decode({'new':(prefix+off).encode()},identity,cycle_id)['terminal_witness_commits'][0]['type']==9
    assert not decoded['physical_XNU_entry_observed'] and not decoded['full_XNU_boot_observed']


def fixture(output):
    text,rows=prepare.retained.definitions(output[prepare.CAL_PATH]);selected={row[4]:text[row[0]:row[2]] for row in rows if row[4] in ('n136_witness_commit','n136_witness_valid')}
    if set(selected)!={'n136_witness_commit','n136_witness_valid'}:raise ValueError('actual selected witness definitions required')
    catalog=selected['n136_witness_commit']+'\n'+selected['n136_witness_valid']+'\n'
    return (C_PREFIX.replace('/* N140_ACTUAL_CATALOG */',catalog).replace('/* N140_AFTER_SHUTDOWN */',output['arch/arm64/mm/v130_kernel.c'].decode())+C_MAIN).encode()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('output','cc','retained-context','retained-cal-source'):parser.add_argument('--'+name,type=Path,required=True)
    for name in ('retained-context-sha256','retained-cal-source-sha256'):parser.add_argument('--'+name,required=True)
    args=parser.parse_args();out=private(args.output)
    if out.exists():parser.error('fresh new140 output required')
    prior_raw=ordinary(args.retained_context).read_bytes()
    if args.retained_context_sha256!=PRIOR_FILE_SHA or digest(prior_raw)!=hexid(args.retained_context_sha256):raise ValueError('exact retained139 PASS metadata required')
    previous=json.loads(prior_raw);build.retained_continuation(previous,build.RETAINED_SOURCE_SHA256)
    if digest(json.dumps(previous,sort_keys=True,separators=(',',':')).encode())!=build.RETAINED_CONTEXT_SHA256 or previous['delta_NEW_PASS']['result_sha256']!=PRIOR_RESULT_SHA:raise ValueError('retained139 source94 binding differs')
    cal=ordinary(args.retained_cal_source).read_bytes()
    if args.retained_cal_source_sha256!=CAL_SHA or digest(cal)!=hexid(args.retained_cal_source_sha256):raise ValueError('exact accepted139 generated public CAL required')
    current_source=dict(build.RETAINED_SOURCE_SHA256,**{name:digest((ROOT/name).read_bytes()) for name in build.NEW_FILES});out.mkdir(parents=True)
    result=dict(schema='note10-v140-dsim-proxy-result-v1',scope=build.SCOPE,passed=False,source_sha256={name:current_source[name] for name in build.NEW_FILES},retained139_result_sha256=PRIOR_RESULT_SHA,retained139_source_map_sha256='eec6c85f1629c73868890090b34e080eac7ec99085ebacce58a5f59c3740566e',retained_CAL_sha256=CAL_SHA,NEW_overlay_delta_render_invocations=0,NEW_host_invocations=0,compiler_invocations=0,fixture_processes=0,retained_overlay_render_invocations=0,old_tests_replayed=0,Image_reads=0,raw_kernel_reads=0,adapter_reads=0,compressions=0,device_operations=[])
    def persist():(out/'result.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
    try:
        result['NEW_overlay_delta_render_invocations']=1;persist();output=new_output(cal);directory=out/'rendered-inputs';directory.mkdir();pins={}
        for name,value in output.items():
            path=directory/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(value);pins[name]=digest(value)
        checkpoint=(json.dumps(dict(schema='note10-v140-new-render-checkpoint-v1',source_sha256=current_source,retained_CAL_sha256=CAL_SHA,fragments=pins),indent=2)+'\n').encode();(directory/'MANIFEST.json').write_bytes(checkpoint)
        result.update(checkpoint_file='rendered-inputs/MANIFEST.json',checkpoint_sha256=digest(checkpoint),NEW_overlay_delta_passed=True);persist()
        result['NEW_host_invocations']=1;persist();cases(output);result['NEW_host_cases_passed']=True;persist()
        generated=fixture(output);source=out/'new-dsim-proxy.c';source.write_bytes(generated);result.update(generated_C_file=source.name,generated_C_sha256=digest(generated));persist()
        include=out/'include/linux';include.mkdir(parents=True)
        for name in ('types.h','errno.h','of_address.h'):(include/name).write_bytes(b'/* synthetic native dependency */\n')
        (include/'v138_display.h').write_bytes(output['include/linux/v138_display.h']);(include/'v136_terminal.h').write_bytes((HERE/'v136_terminal.h').read_bytes());(out/'v140_dsim.inc').write_bytes(output[prepare.NATIVE_PATH])
        macros=['-DCONFIG_'+key+'=1' for key,value in build.SETTINGS.items() if value=='y'];exe=out/('new-dsim-proxy.exe' if sys.platform=='win32' else 'new-dsim-proxy')
        command=[str(ordinary(args.cc)),'-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wstrict-prototypes','-Wno-unused-function','-ferror-limit=0',*macros,'-I',str(out/'include'),str(source),'-o',str(exe)]
        result['compiler_invocations']=1;persist()
        with (out/'compile.log').open('xb') as log:subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=60)
        result['fixture_processes']=1;persist()
        with (out/'fixture.log').open('xb') as log:subprocess.run([str(exe)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=15)
        result['passed']=True;result_raw=(json.dumps(result,indent=2)+'\n').encode();delta=dict(schema='note10-v140-dsim-terminal-pass-v1',scope=build.SCOPE,passed=True,result_sha256=digest(result_raw),source_sha256=result['source_sha256'])
        candidate=dict(schema='note10-v140-public-terminal-continuation-v1',scope=build.SCOPE,passed=True,retained_source_commit=build.RETAINED_COMMIT,retained_terminal_PASS=previous,delta_NEW_PASS=delta,source_sha256=current_source)
        build.continuation(candidate,current_source);encoded=encode_public(candidate);(out/'result.json').write_bytes(result_raw);save(out/'public-dsim-continuation.json',candidate);(out/'public-dsim-continuation.txt').write_bytes((encoded+'\n').encode('ascii'))
    except BaseException:
        import traceback
        result['error']=traceback.format_exc();persist();raise
    print(json.dumps(dict(passed=True,compiler_invocations=1,fixture_processes=1,old_tests_replayed=0)))


if __name__=='__main__':main()
