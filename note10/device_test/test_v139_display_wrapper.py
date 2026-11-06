"""NEW native adjacent-function lexical correction batch; old138 suites0."""
import argparse,json,re,subprocess,sys
from pathlib import Path
sys.dont_write_bytecode=True
from v130_contract import ROOT,private,ordinary,digest,hexid,save
from v135_metadata import encode_public
import v139_prepare as prepare
import v139_build as build
import v139_package as package
import v139_cycle as cycle
HERE=Path(__file__).resolve().parent
DP_SHA='cca9060fbf37aa5a0ac13bd184fc2af851e3bb3118c84dca2f8f1a145d034fe0'
PRIOR_FILE_SHA='c67bbacd773a24ce77c1cb78a5a4f24f9e016870ab66a0f90429bdcd01ac2e1a'
PRIOR_RESULT_SHA='ed63f0b5d95f6a0198495f68b77ac273942dc89b18f5ba619d423c3f47ee8ba9'
PAIR=('displayport_check_pixel_clock_for_hdr','displayport_get_min_link_rate')
C_PREFIX=r''' 
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>
#undef ESHUTDOWN
#define ESHUTDOWN 108
typedef uint8_t u8;
typedef uint64_t u64;
typedef int videoformat;
enum bit_depth { BPC_8=8,BPC_10=10 };
#define MAX_LINK_RATE_NUM 3
#define LINK_RATE_1_62Gbps 6
#define LINK_RATE_2_7Gbps 10
#define LINK_RATE_5_4Gbps 20
struct displayport_device {struct {bool hdr_support;} rx_edid_data;bool dex_setting,is_hmd_dev;};
static struct displayport_device fixture_dp;
static struct {struct {struct {u64 pixelclock;} bt;} dv_timings;} supported_videos[1];
static bool admitted=true;
static unsigned int active,logs;
static bool n138_user_begin(void){if(!admitted)return false;active++;return true;}
static void n138_user_end(void){assert(active);active--;}
static void displayport_info(const char *format,...){assert(format && strstr(format,"set link late:"));logs++;}
static struct displayport_device *get_displayport_drvdata(void){return &fixture_dp;}
static int displayport_check_edid_max_clock(struct displayport_device *dp,videoformat video,enum bit_depth depth)
{assert(dp==&fixture_dp && video==0 && depth==BPC_10);return true;}
static u8 displayport_reg_phy_get_link_bw(void){return LINK_RATE_5_4Gbps;}
static u8 displayport_reg_get_lane_count(void){return 4;}
static int displayport_check_link_rate_pixel_clock(u8 rate,u8 lanes,u64 pixel,enum bit_depth depth,int margin)
{assert(lanes<=4 && pixel && (depth==BPC_8 || depth==BPC_10) && (margin==0 || margin==1));return rate>=LINK_RATE_2_7Gbps;}
static u64 displayport_find_edid_max_pixelclock(void){return 100;}
'''
LEXICAL_SOURCE=r''' 
/* The following is comment data, never a definition or delimiter:
static int phantom(void)
{
}
*/
static int lexical_tokens(void)
{
 const char *text="{ } /* not a comment */ \\\" quote";
 char close='}';
 /* }
 { */
 return text[0]=='{' && close=='}';
 }
static int callback_boundary(int (*operation)(int),int value)
{ return operation(value); }
'''
C_MAIN=r''' 
static int plus_one(int value){return value+1;}
int main(void)
{
 supported_videos[0].dv_timings.bt.pixelclock=100;fixture_dp.rx_edid_data.hdr_support=true;
 assert(displayport_check_pixel_clock_for_hdr(&fixture_dp,0)==true && active==0);
 assert(displayport_get_min_link_rate(LINK_RATE_5_4Gbps,4)==LINK_RATE_2_7Gbps && logs==1 && active==0);
 assert(displayport_get_min_link_rate(LINK_RATE_1_62Gbps,4)==LINK_RATE_1_62Gbps);
 assert(displayport_get_min_link_rate(LINK_RATE_2_7Gbps,5)==LINK_RATE_5_4Gbps);
 assert(lexical_tokens()==1 && callback_boundary(plus_one,3)==4 && active==0);
 fixture_dp.dex_setting=true;fixture_dp.is_hmd_dev=false;
 assert(n139_branch_enabled(&fixture_dp)==1 && n139_branch_disabled(&fixture_dp)==1);
 fixture_dp.is_hmd_dev=true;
 assert(n139_branch_enabled(&fixture_dp)==0 && n139_branch_disabled(&fixture_dp)==1);
 admitted=false;
 assert(displayport_check_pixel_clock_for_hdr(&fixture_dp,0)==-ESHUTDOWN);
 assert(displayport_get_min_link_rate(LINK_RATE_5_4Gbps,4)==-ESHUTDOWN && active==0);
 return 0;
}
'''


def adjacent_source(raw):
    text,rows=prepare.definitions(raw);selected=[row for row in rows if row[4] in PAIR]
    if len(selected)!=2 or tuple(row[4] for row in selected)!=PAIR:raise ValueError('exact pinned adjacent native pair required')
    if any(a[2]>b[0] for a,b in zip(rows,rows[1:])):raise ValueError('overlapping new lexical edit spans')
    start,end=selected[0][0],selected[1][2]
    original=text[start:end]
    if ' \treturn ret_val;\n }\n\nstatic int displayport_get_min_link_rate' not in original:raise ValueError('actual failed indented native boundary absent')
    if 'displayport_info("set link late: 0x%x, lane cnt:%d\\n", min_link_rate, lane_cnt);' not in original:raise ValueError('actual native log string required')
    return original.encode(),rows


def branch_fragment(raw):
    text,rows=prepare.definitions(raw);rows=[row for row in rows if row[4]=='displayport_enum_dv_timings']
    if len(rows)!=1:raise ValueError('exact native conditional owner required')
    row=rows[0];body=text[row[1]:row[2]]
    start=body.index('#ifdef FEATURE_MANAGE_HMD_LIST\n');end=body.index('\n#endif',start)+len('\n#endif')
    selected=body[start:end]
    if selected!='#ifdef FEATURE_MANAGE_HMD_LIST\n\tif (displayport->dex_setting && !displayport->is_hmd_dev) {\n#else\n\tif (displayport->dex_setting) {\n#endif':raise ValueError('actual alternate-opening-brace source differs')
    return selected


def changed_fragments(raw):
    original,rows=adjacent_source(raw);pair=prepare.wrap_fragment(original,PAIR)
    original_literal=b'displayport_info("set link late: 0x%x, lane cnt:%d\\n", min_link_rate, lane_cnt);'
    assert pair.count(original_literal)==1
    _,selected=prepare.definitions(pair)
    assert [row[4] for row in selected]==[PAIR[0]+'_n138_native',PAIR[0],PAIR[1]+'_n138_native',PAIR[1]]
    assert all(a[2]<=b[0] for a,b in zip(selected,selected[1:]))
    lexical=prepare.wrap_fragment(LEXICAL_SOURCE.encode(),('lexical_tokens','callback_boundary'))
    _,lexical_rows=prepare.definitions(lexical)
    assert not any(row[4]=='phantom' for row in lexical_rows)
    selected_branch=branch_fragment(raw);branches=b''
    for enabled in (True,False):
        name='n139_branch_'+('enabled' if enabled else 'disabled')
        source=('static int '+name+'(struct displayport_device *displayport)\n{\n'+selected_branch+'\n return 1;\n }\n return 0;\n}\n').encode()
        value=prepare.wrap_fragment(source,(name,))
        branches+=(b'#define FEATURE_MANAGE_HMD_LIST 1\n' if enabled else b'#undef FEATURE_MANAGE_HMD_LIST\n')+value+b'#undef FEATURE_MANAGE_HMD_LIST\n'
    return dict(native_pair=pair,lexical_tokens=lexical,conditional_branches=branches),len(rows)


def new_boundaries():
    original=prepare.retained.render;old_lexer=prepare.retained.definitions
    def selected(stock,identity,source128):
        assert prepare.retained.definitions is prepare.definitions
        return {'new-marker':b'N10XNU138 id=synthetic'}
    prepare.retained.render=selected
    try:assert prepare.render({},'a'*32,HERE)=={'new-marker':b'N10XNU139 id=synthetic'}
    finally:prepare.retained.render=original
    assert prepare.retained.definitions is old_lexer
    def failed(*args):raise ValueError('injected new callback failure')
    try:prepare.with_lexer(failed)
    except ValueError:pass
    else:raise AssertionError('new callback failure hidden')
    assert prepare.retained.definitions is old_lexer
    # A C branch mismatch is source ambiguity, never a first-branch guess.
    try:prepare.definitions(b'int mismatch(void)\n{\n#if X\n{\n#endif\n}\n')
    except ValueError:pass
    else:raise AssertionError('unequal branch depth admitted')
    loader=build.pid1_source();assert set(re.findall(rb'N10XNU[0-9]+',loader))=={b'N10XNU139'}
    source=(HERE/'v139_build.py').read_text()
    assert source.index('        loader=pid1_source()')<source.index("(out/'v139_loader.c').write_bytes(loader)")<source.index("result['PID1_source_sha256']=digest(loader)")<source.index("'00-new-PID1'")
    assert 'drivers/video/fbdev/exynos/dpu20/v138_display.o' in source and 'v139_display.o' not in source
    workflow=(ROOT/build.WORKFLOW).read_text()
    assert '  v139-display-wrapper-lexical:' in workflow and 'note10/device_test/v139_build.py' in workflow
    assert len(package.CURRENT137_SOURCE_SHA256)==79 and package.CURRENT137_SOURCE_SHA256!=build.RETAINED_SOURCE_SHA256
    assert 'current137_package' in (HERE/'v139_package.py').read_text() and 'current138_package' not in (HERE/'v139_package.py').read_text()
    identity,cycle_id='a'*32,'b'*32
    prefix='N10XNU139 id='+identity+' cycle='+cycle_id+' stage='
    native='N10XNU139 id='+identity+' stage=display-dpp-reset errno=-110 owner=synthetic\n'
    assert cycle.decode({'new':(prefix+'begin\n'+native).encode()},identity,cycle_id)['gate_refusals']==[dict(stage='display-dpp-reset',errno=-110,owner='synthetic')]
    assert not cycle.decode({'new':(prefix+'begin\n'+native).replace('N10XNU139','N10XNU138').encode()},identity,cycle_id)['previous_boot_build_cycle_observed']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('output','cc','retained-context','native-dp-source'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--retained-context-sha256',required=True);args=parser.parse_args();out=private(args.output)
    if out.exists():parser.error('fresh new139 output required')
    previous_raw=ordinary(args.retained_context).read_bytes()
    if args.retained_context_sha256!=PRIOR_FILE_SHA or digest(previous_raw)!=hexid(args.retained_context_sha256):raise ValueError('exact retained138 synthetic PASS required')
    previous=json.loads(previous_raw);build.retained_continuation(previous,build.RETAINED_SOURCE_SHA256)
    if digest(json.dumps(previous,sort_keys=True,separators=(',',':')).encode())!=build.RETAINED_CONTEXT_SHA256 or previous['delta_NEW_PASS']['result_sha256']!=PRIOR_RESULT_SHA:raise ValueError('retained138 PASS source binding differs')
    raw=ordinary(args.native_dp_source).read_bytes()
    if digest(raw)!=DP_SHA:raise ValueError('exact pinned DP native source required')
    current_source=dict(build.RETAINED_SOURCE_SHA256,**{name:digest((ROOT/name).read_bytes()) for name in build.NEW_FILES})
    out.mkdir(parents=True)
    result=dict(schema='note10-v139-display-wrapper-result-v1',scope=build.SCOPE,passed=False,source_sha256={name:current_source[name] for name in build.NEW_FILES},retained138_result_sha256=PRIOR_RESULT_SHA,retained138_source_map_sha256='e3e3c1560814fdd82d23c5670ceb9b64b1211651b5f59de404982c717eea357b',NEW_fragment_generations=0,NEW_boundary_invocations=0,compiler_invocations=0,fixture_processes=0,retained_overlay_render_invocations=0,old_tests_replayed=0,Image_reads=0,raw_kernel_reads=0,adapter_reads=0,compressions=0,device_operations=[])
    def persist():(out/'result.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
    try:
        result['NEW_fragment_generations']=1;persist();fragments,count=changed_fragments(raw)
        checkpoint={}
        for name,value in fragments.items():
            path=out/(name+'.c');path.write_bytes(value);checkpoint[path.name]=digest(value)
        checkpoint_raw=(json.dumps(dict(schema='note10-v139-new-fragment-checkpoint-v1',source_sha256=current_source,native_source_sha256=DP_SHA,fragments=checkpoint),indent=2)+'\n').encode()
        (out/'MANIFEST.json').write_bytes(checkpoint_raw);result.update(checkpoint_file='MANIFEST.json',checkpoint_sha256=digest(checkpoint_raw),native_definition_count=count,NEW_fragment_generation_passed=True);persist()
        result['NEW_boundary_invocations']=1;persist();new_boundaries();result['NEW_boundaries_passed']=True;persist()
        generated=(C_PREFIX.encode()+b'\n'+b'\n'.join(fragments.values())+C_MAIN.encode());source=out/'new-display-wrapper.c';source.write_bytes(generated)
        result.update(generated_C_file=source.name,generated_C_sha256=digest(generated));persist()
        macros=['-DCONFIG_'+key+'=1' for key,value in build.SETTINGS.items() if value=='y']
        executable=out/('new-display-wrapper.exe' if sys.platform=='win32' else 'new-display-wrapper')
        command=[str(ordinary(args.cc)),'-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wstrict-prototypes','-Wno-unused-function','-ferror-limit=0',*macros,str(source),'-o',str(executable)]
        result['compiler_invocations']=1;persist()
        with (out/'compile.log').open('xb') as log:subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=60)
        result['fixture_processes']=1;persist()
        with (out/'fixture.log').open('xb') as log:subprocess.run([str(executable)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=15)
        result['passed']=True;result_raw=(json.dumps(result,indent=2)+'\n').encode()
        delta=dict(schema='note10-v139-display-wrapper-lexical-pass-v1',scope=build.SCOPE,passed=True,result_sha256=digest(result_raw),source_sha256=result['source_sha256'])
        candidate=dict(schema='note10-v139-public-terminal-continuation-v1',scope=build.SCOPE,passed=True,retained_source_commit=build.RETAINED_COMMIT,retained_terminal_PASS=previous,delta_NEW_PASS=delta,source_sha256=current_source)
        build.continuation(candidate,current_source);encoded=encode_public(candidate)
        (out/'result.json').write_bytes(result_raw);save(out/'public-display-wrapper-continuation.json',candidate);(out/'public-display-wrapper-continuation.txt').write_bytes((encoded+'\n').encode('ascii'))
    except BaseException:
        import traceback
        result['error']=traceback.format_exc();persist();raise
    print(json.dumps(dict(passed=True,compiler_invocations=1,fixture_processes=1,old_tests_replayed=0)))


if __name__=='__main__':main()
