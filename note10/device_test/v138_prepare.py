"""Selected DPU20 aggregate terminal ownership over immutable137."""
from pathlib import Path
import re
import v137_prepare as retained
HERE=Path(__file__).resolve().parent
BASE='drivers/video/fbdev/exynos/dpu20/'
PINS=dict(retained.PINS)
OPTION=retained.OPTION
sha=retained.sha
once=retained.retained.once
# Exact public Linux55f042 source pins are added below; no private path reader.
NATIVE_PINS={'drivers/misc/tui/stui_core.c': 'a3e576493645d373d63a915a65f788db63b565d695f6d4d063323ab97e38b743', 'drivers/soc/samsung/exynos-hdcp/dp_link/exynos-hdcp2-dplink-inter.c': '82abc20c68fdcc7751b0bc8333341ecb84fcce9a0967d719080a0dc25aebab30', 'drivers/soc/samsung/exynos-hdcp/exynos-hdcp2-teeif.c': '327d3cce678562cbebb77e1d78d8d2bcb16c19f1591eaa7366447e86818783d0', 'drivers/soc/samsung/exynos-smc.c': '7b615918b710eeee66fde8abb72eb27904070ba9d975fc1c553348b9f17db737', 'drivers/video/fbdev/exynos/dpu20/Makefile': 'd720b4c9614077af410dbda1359f53ff53268a20421198bd1bce06f7f3764ea2', 'drivers/video/fbdev/exynos/dpu20/bts.c': '923f7b7b8385dca0590ae283fea01f0b706311ec23a0c026bd05cbf8d2301e2d', 'drivers/video/fbdev/exynos/dpu20/cal_9820/decon_reg.c': 'a6fa54305b75300685c18dfd76ad6bbd3b44e747e7a3180ccd86be42e409deaa', 'drivers/video/fbdev/exynos/dpu20/cal_9820/displayport_reg.c': 'f81af7bb71103008ee32dbd7a0105a9d53543467b03aac7008a480beef0889f0', 'drivers/video/fbdev/exynos/dpu20/cal_9820/dpp_reg.c': 'bbb68b22e126eebee871e7922a290be6f7d787ae2f6587de85f17e515dc8fbee', 'drivers/video/fbdev/exynos/dpu20/cal_9820/dsim_reg.c': '777aae74ccb2d00293dd4d0731f78a169d8f32650a4dd1f8b5697c61f34493f9', 'drivers/video/fbdev/exynos/dpu20/cursor.c': '91d8036b30288d7da4066bedc5135d45995295460e40a6f1decf4b78bf355071', 'drivers/video/fbdev/exynos/dpu20/decon.h': '7a99fd3dd6846759f4a0a1ca5d586e52d5123835ba705159b9b82bc17504a56c', 'drivers/video/fbdev/exynos/dpu20/decon_core.c': '88899aa623e35a1f0a76b6571bc514691a0d876db7eb17b4c6553a3dfbfb7816', 'drivers/video/fbdev/exynos/dpu20/decon_displayport.c': '103a50d133985f4c66e0d66bde2a9af6bd455fb053f71c614eadfeeaaee98dbb', 'drivers/video/fbdev/exynos/dpu20/decon_dsi.c': '49b91bca83baa78a6b20376429983db9fde259021b4612f39dd92726bd33e927', 'drivers/video/fbdev/exynos/dpu20/decon_wb.c': 'f04e29fa6740062367e81eb88eab64151da2a02d6f3e3baa09b2f9b2260d1532', 'drivers/video/fbdev/exynos/dpu20/displayport.h': '87db0cd91238861584623a7798f79d7c2f86570c42ae6c04cada927d4374dd30', 'drivers/video/fbdev/exynos/dpu20/displayport_drv.c': 'cca9060fbf37aa5a0ac13bd184fc2af851e3bb3118c84dca2f8f1a145d034fe0', 'drivers/video/fbdev/exynos/dpu20/displayport_edid.c': '721278a4f5cea450dd80c99042161fa287b3a7e8ee127df6417654017b36330e', 'drivers/video/fbdev/exynos/dpu20/displayport_hdcp13.c': 'd4d0f3081fbb48db2f7e9153c8e590661c4fc9e659ece43d2db2df19d17da8e7', 'drivers/video/fbdev/exynos/dpu20/displayport_hdcp22_if.c': '8a6aa26ff302dd8097d0be8e9b0b3ff6e551f55b0184589613ac0d4bcc090dc6', 'drivers/video/fbdev/exynos/dpu20/dpp.h': '27481453a564574ea3feb5a045bd15cf21b038d37472d321505a9bc412a7a7a2', 'drivers/video/fbdev/exynos/dpu20/dpp_drv.c': '8599fea4a38ac340df2d464f0dcd696724841eb26517df6cfefe1781769a152c', 'drivers/video/fbdev/exynos/dpu20/dsim.h': '8eccc6993533365ec7550a6eb3cb1770bd20b6926474c8e321f86456d4240538', 'drivers/video/fbdev/exynos/dpu20/dsim_drv.c': '480366e6acc4db44c662fbd7b3b817b0f1de147920b60a553ad2ec3ffe837713', 'drivers/video/fbdev/exynos/dpu20/helper.c': '441118484e3b06a26701a9602b086e4b553aac32416002b19004bcbd60d9e19c', 'drivers/video/fbdev/exynos/dpu20/mcd_hdr/hdr_drv.c': '1746da2429c495a400c1dda2e4b2309df8bebf7083974102525468d6e8fcdfed', 'drivers/video/fbdev/exynos/dpu20/mcd_hdr/hdr_reg.c': '0dd160bf596cef1ab4999c22d92b4abe4e283d5f5cae3cc98e398b2bc5ab6fe2', 'drivers/video/fbdev/exynos/dpu20/mcd_hdr/mcd_cm.c': 'd6154bdf7bc578a75512936b95ee717d86f2a3b24d897aec779771844608a8c9', 'drivers/video/fbdev/exynos/dpu20/secdp_aux_control.c': '149876d83cf70efce30f51cd7d5cf8f619214a7dc4363f14a75df87869699643', 'drivers/video/fbdev/exynos/dpu20/secdp_unit_test.c': 'ce32230d09d17dc996ff9027898d398a2765b928c545cbed1454bb0ac0aa0917', 'drivers/video/fbdev/exynos/dpu20/win_update.c': '9283437cbeb6e5b3957babdb62cd8d688bf4e7346f335ef7d1a480a0d39d9478'}
PINS.update(NATIVE_PINS)
FINITE_FILES=(
 'decon_core.c','decon_dsi.c','decon_displayport.c','decon_wb.c','cursor.c',
 'win_update.c','helper.c','dsim_drv.c','displayport_drv.c','displayport_edid.c',
 'displayport_hdcp13.c','displayport_hdcp22_if.c','secdp_unit_test.c',
 'secdp_aux_control.c','dpp_drv.c','bts.c','mcd_hdr/hdr_drv.c',
 'mcd_hdr/hdr_reg.c','mcd_hdr/mcd_cm.c','cal_9820/decon_reg.c',
 'cal_9820/dpp_reg.c','cal_9820/dsim_reg.c','cal_9820/displayport_reg.c')
SLEEPING_THREADS=frozenset(('decon_devfreq_change_task','decon_vsync_thread',
 'decon_fsync_thread','decon_displayport_vsync_thread','decon_hiber_thread','decon_doze_suspend_thread',
 'decon_doze_wake_thread','dsim_adap_freq_thread'))
TOKEN=re.compile(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[(){}]',re.S)


def profile(settings):
    retained.profile(settings)
    required={'EXYNOS_DPU20':'y','EXYNOS_DPP':'y','EXYNOS_DISPLAYPORT':'y',
              'SOC_EXYNOS9820':'y','SOC_EXYNOS9820_EVT0':'n',
              'SAMSUNG_TUI':'y','EXYNOS_CONTENT_PATH_PROTECTION':'y',
              'EXYNOS_MCD_HDR':'y','EXYNOS_COMMON_PANEL':'y',
              'EXYNOS_PLL_SLEEP':'y','SUPPORT_LEGACY_FENCE':'n',
              'EXYNOS_MIPI_DSIM':'y','EXYNOS_HDCP2':'y','EXTCON':'y',
              'USB_TYPEC_MANAGER_NOTIFIER':'y','TYPEC':'y',
              'EXYNOS_HIBERNATION_THREAD':'y'}
    if any(settings.get(k)!=v for k,v in required.items()):
        raise ValueError('exact selected138 native DPU20 profile required')
    return required


def balanced(text,start,left,right):
    depth=0
    for part in TOKEN.finditer(text,start):
        token=part.group()
        if token==left:depth+=1
        elif token==right:
            depth-=1
            if depth==0:return part.end()
    raise ValueError('unbalanced native source boundary')


def definitions(raw):
    """Definition extents, including pointer/function-pointer parameters.

    This never selects the first of duplicate definitions: callers requiring
    a named definition require exactly one selected pinned source definition.
    """
    text=raw.decode();rows=[]
    pattern=re.compile(r'(?m)^(?P<ret>[A-Za-z_][A-Za-z_0-9 \t*]*?)[ \t*](?P<name>[A-Za-z_][A-Za-z_0-9]*)[ \t]*\(')
    for match in pattern.finditer(text):
        close=balanced(text,match.end()-1,'(',')')
        body=close
        while body<len(text) and text[body].isspace():body+=1
        if body>=len(text) or text[body]!='{':continue
        # Pinned native C uses a column-zero outer close. Counting all braces
        # across mutually exclusive #if branches is incorrect (three selected
        # functions contain alternative opening braces). Lexical tokens exclude
        # comments/strings; no nested native statement closes at column zero.
        end=None
        body_line=text.count('\n',0,body)
        body_depth=1
        for token in TOKEN.finditer(text,body+1):
            if token.group()=='{':body_depth+=1
            elif token.group()=='}':body_depth-=1
            if token.group()=='}' and (token.start()==0 or text[token.start()-1]=='\n' or
                                       (body_depth==0 and text.count('\n',0,token.start())==body_line)):
                end=token.end();break
        if end is None:raise ValueError('exact native outer definition close required: '+match.group('name'))
        rows.append((match.start(),body,end,match.group('ret'),match.group('name'),text[match.end():close-1]))
    return text,rows


def selected(raw,name):
    text,rows=definitions(raw);rows=[row for row in rows if row[4]==name]
    if len(rows)!=1:raise ValueError('one exact native138 definition required: '+name)
    return text,rows[0]


def edit_function(raw,name,edit):
    text,row=selected(raw,name);start,body,end,_,_,_=row
    return (text[:start]+edit(text[start:end])+text[end:]).encode()


def handoff_body(original,changed):
    opening=original.index('{');other=changed.index('{')
    return original[:opening+1]+'\n#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\n'+changed[other+1:-1]+'\n#else\n'+original[opening+1:-1]+'\n#endif\n}'


def parameters(text):
    if text.strip() in ('','void'):return []
    pieces=[];depth=0;start=0
    for index,char in enumerate(text):
        if char in '([':depth+=1
        elif char in ')]':depth-=1
        elif char==',' and not depth:pieces.append(text[start:index]);start=index+1
    pieces.append(text[start:]);answer=[]
    for item in pieces:
        if '...' in item:raise ValueError('varargs is not a native producer wrapper')
        pointer=re.search(r'\(\s*\*\s*([A-Za-z_]\w*)\s*\)',item)
        clean=re.sub(r'\[[^]]*\]\s*$','',item).strip()
        name=pointer.group(1) if pointer else re.search(r'([A-Za-z_]\w*)\s*$',clean)
        if not name:raise ValueError('exact native argument name required')
        answer.append(name if isinstance(name,str) else name.group(1))
    return answer


def wrap(raw,names=None,access=None):
    """Full finite-call tickets; no cleanup attribute or changed native returns."""
    text,rows=definitions(raw);changes=[];seen=set()
    for start,body,end,rtype,name,args in rows:
        if names is not None and name not in names:continue
        if name in SLEEPING_THREADS:continue
        if '...' in args:
            # Only source-qualified printf/logging helpers may be omitted.
            if name not in ('dpu_debug_printk',):raise ValueError('unclassified varargs: '+name)
            seen.add(name)
            continue
        signature=text[start:body].rstrip();native=name+'_n138_native'
        if not args.strip():
            signature=re.sub(r'\b'+re.escape(name)+r'\s*\(\s*\)',name+'(void)',signature,count=1)
        clean=re.sub(r'\b(?:static|inline|__init|__exit|__maybe_unused|__always_inline)\b','',rtype).strip()
        name_position=re.search(r'\b'+re.escape(name)+r'\s*\(',signature).start()
        pointer='*' in signature[:name_position]
        clean=clean+(' *' if pointer and '*' not in clean else '')
        void=clean=='void'
        if void:refusal='return;'
        elif pointer:refusal='return NULL;'
        elif clean.startswith(('struct ','union ')):refusal='return ('+clean+'){0};'
        else:
            zero=clean.startswith(('unsigned','enum ')) or clean in ('u8','u16','u32','u64')
            refusal='return '+('false' if clean=='bool' else 'IRQ_HANDLED' if clean=='irqreturn_t' else '0' if zero else '-ESHUTDOWN')+';'
        call=native+'('+','.join(parameters(args))+')'
        gate='n138_user_begin()'
        if access is not None:gate=access(name,args)
        original=text[start:end]
        original=re.sub(r'\b'+re.escape(name)+r'(?=\s*\()',native,original,count=1)
        if not args.strip():original=re.sub(r'\b'+re.escape(native)+r'\s*\(\s*\)',native+'(void)',original,count=1)
        if not re.search(r'\bstatic\b',rtype):original='static '+original
        wrapper=signature+'\n{\n#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\n'
        if not void:wrapper+='    '+clean+' n138_answer;\n'
        if name in ('decon_remove','dpp_remove','displayport_remove','dsim_remove'):
            wrapper+='    n138_detach(&pdev->dev);\n'
        if name in ('decon_probe','dpp_probe','displayport_probe','dsim_probe'):
            wrapper+='    if(!'+gate+'){n138_probe_result(&pdev->dev,false);'+refusal+'}\n'
        else:wrapper+='    if(!'+gate+')'+refusal+'\n'
        wrapper+='    '+(call+';' if void else 'n138_answer='+call+';')+'\n'
        if name in ('decon_probe','dpp_probe','displayport_probe','dsim_probe'):
            wrapper+='    n138_probe_result(&pdev->dev,n138_answer==0);\n'
        wrapper+='    n138_user_end();\n'
        wrapper+='    return'+(';' if void else ' n138_answer;')+'\n#else\n    '+('return '+call+';' if not void else call+';return;')+'\n#endif\n}\n'
        # Retain an original-name declaration for recursion/callback addresses
        # inside the renamed body; native definition precedes its wrapper.
        changes.append((start,end,signature+';\n'+original+'\n'+wrapper));seen.add(name)
    if names is not None and seen!=set(names):raise ValueError('native138 accessor catalog differs: '+str(set(names)-seen))
    for start,end,replacement in reversed(changes):text=text[:start]+replacement+text[end:]
    return text.encode()


def probe_hooks(raw,family,variable,publish,ready_anchor,resource_anchor=None):
    name={'N138_DECON':'decon_probe','N138_DPP':'dpp_probe',
          'N138_DP':'displayport_probe','N138_DSIM':'dsim_probe'}[family]
    identity='0' if family=='N138_DP' else variable+'->id'
    # Bookkeeping refusal poisons only the new handoff proof. Do not invent a
    # new jump into native partial-probe cleanup after workers were registered.
    subdev='&dpp->sd' if family=='N138_DPP' else 'NULL'
    register='(void)n138_probe('+family+','+identity+',dev,'+variable+','+subdev+');\n\t'
    def change(body):
        if body.count(publish)!=1 or body.count(ready_anchor)!=1:
            raise ValueError('exact probe/ready138 anchors required: '+name)
        body=body.replace(publish,'#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\n\t'+register+'#endif\n\t'+publish,1)
        resources='(void)n138_resources('+family+','+identity+','+variable+');'
        ready='(void)n138_ready('+family+','+identity+','+variable+');'
        if resource_anchor is not None:
            if body.count(resource_anchor)!=1:raise ValueError('exact initial display resource138 boundary required')
            body=body.replace(resource_anchor,'#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\n\t'+resources+'\n#endif\n\t'+resource_anchor,1)
            addition=ready
        else:addition=resources+'\n\t'+ready
        return body.replace(ready_anchor,'#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\n\t'+addition+'\n#endif\n\t'+ready_anchor,1)
    return edit_function(raw,name,change)


def dpp_overlay(output):
    header=output[BASE+'dpp.h']
    header=once(header,b'\tstruct dpp_config *dpp_config;',b'\tstruct dpp_config *dpp_config;\n#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\n    struct dpp_config n138_saved_config;\n#endif')
    output[BASE+'dpp.h']=header
    raw=output[BASE+'dpp_drv.c']
    def config(body):
        if body.count('mutex_lock(&dpp->lock);')!=1 or body.count('mutex_unlock(&dpp->lock);')!=1:
            raise ValueError('exact owned DPP native mutex138 boundary required')
        return body.replace('mutex_lock(&dpp->lock);','#ifndef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\n    mutex_lock(&dpp->lock);\n#endif').replace('mutex_unlock(&dpp->lock);','#ifndef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\n    mutex_unlock(&dpp->lock);\n#endif')
    raw=edit_function(raw,'dpp_set_config',config)
    def ioctl(body):
        start=body.index('\tcase DPP_WIN_CONFIG:');end=body.index('\n\tcase DPP_STOP:',start)
        native=body[start:end]
        return body[:start]+'\tcase DPP_WIN_CONFIG:\n#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\n        n138_unowned_config();return -EPERM;\n#else\n'+native.split('\n',1)[1]+'\n#endif\n'+body[end:]
    raw=edit_function(raw,'dpp_subdev_ioctl',ioctl)
    def stop(body):
        body=body.replace('mutex_lock(&dpp->lock);','''mutex_lock(&dpp->lock);
#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
    if(!n138_dpp_transaction_begin(dpp->id)){mutex_unlock(&dpp->lock);return -EPERM;}
#endif''',1)
        return body.replace('mutex_unlock(&dpp->lock);\n\treturn ret;','''#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
    n138_dpp_transaction_end(dpp->id);
#endif
    mutex_unlock(&dpp->lock);
\treturn ret;''',1)
    raw=edit_function(raw,'dpp_stop',stop)
    output[BASE+'dpp_drv.c']=probe_hooks(raw,'N138_DPP','dpp','dpp_drvdata[dpp->id] = dpp;',
        'dpp_info("dpp%d is probed successfully\\n", dpp->id);')
    expected={'decon_core.c':3,'cursor.c':1,'decon_dsi.c':1}
    pattern=rb'v4l2_subdev_call\(sd,\s*core,\s*ioctl,\s*DPP_WIN_CONFIG,\s*&dpp_config\)'
    for name,count in expected.items():
        raw=output[BASE+name]
        if len(re.findall(pattern,raw))!=count:raise ValueError('five exact owned DPP config138 call sites required: '+name)
        output[BASE+name]=re.sub(pattern,b'n138_owned_config(decon,sd,&dpp_config)',raw)


def native_poll(raw,name,reader,mask,reason,native_error,limit):
    text,row=selected(raw,name);start,body,end,_,_,_=row
    signature=text[start:body]
    replacement=signature+'''{
    u32 n138_snapshot=0;unsigned long n138_left='''+str(limit)+''';int n138_error;
    do {
        n138_error=n138_checkpoint();
        if(n138_error)return n138_poll_failure("'''+reason+'''",id,n138_snapshot,n138_error);
        n138_snapshot='''+reader+''';
        n138_error=n138_checkpoint();
        if(n138_error)return n138_poll_failure("'''+reason+'''",id,n138_snapshot,n138_error);
        if(!(n138_snapshot&('''+mask+''')))return 0;
        udelay(10);
    }while(--n138_left);
    return n138_poll_failure("'''+reason+'''",id,n138_snapshot,'''+native_error+''');
}'''
    # Preserve the complete original normal-operation wait/log behavior.
    replacement=signature+'{\n#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\n    if(n138_proving()){\n'+replacement[len(signature)+1:-1]+'\n    }\n#endif\n    {\n'+text[body+1:end-1]+'\n    }\n}'
    return (text[:start]+replacement+text[end:]).encode()


def cal_poll_overlay(output):
    path=BASE+'cal_9820/dpp_reg.c';raw=output[path]
    raw=native_poll(raw,'idma_reg_wait_sw_reset_status','dma_read(id,IDMA_ENABLE)','IDMA_SRESET','idma-reset','-1',100000)
    raw=native_poll(raw,'dpp_reg_wait_sw_reset_status','dpp_read(id,DPP_ENABLE)','DPP_SRSET','dpp-reset','-EBUSY',100000)
    def deinit(body):
        body=body.replace('{','{\n    int n138_error;',1)
        old='''if (idma_reg_wait_sw_reset_status(id) ||
\t\t\t\t\tdpp_reg_wait_sw_reset_status(id))
\t\t\t\treturn -1;'''
        new='''n138_error=n138_checkpoint();if(n138_error)return n138_error;
            n138_error=idma_reg_wait_sw_reset_status(id);if(n138_error)return n138_error;
            n138_error=dpp_reg_wait_sw_reset_status(id);if(n138_error)return n138_error;'''
        if old not in body:raise ValueError('exact native IDMA/DPP ACK propagation138 required')
        # The selected proof uses this exact IDMA+DPP branch; other branches
        # retain native semantics and are refused by the provider catalog.
        return body.replace(old,new,1)
    output[path]=edit_function(raw,'dpp_reg_deinit',lambda body:handoff_body(body,deinit(body)))
    path=BASE+'cal_9820/decon_reg.c';raw=output[path]
    def reset(body):
        body=body.replace('int tries;','int tries;\n    u32 n138_snapshot;int n138_error;')
        body=body.replace('decon_write_mask(id, GLOBAL_CONTROL, ~0, GLOBAL_CONTROL_SRESET);',
            'n138_error=n138_checkpoint();if(n138_error)return n138_error;\n    decon_write_mask(id, GLOBAL_CONTROL, ~0, GLOBAL_CONTROL_SRESET);',1)
        old='if (~decon_read(id, GLOBAL_CONTROL) & GLOBAL_CONTROL_SRESET)'
        new='''n138_error=n138_checkpoint();if(n138_error)return n138_poll_failure("decon-reset",id,0,n138_error);
        n138_snapshot=decon_read(id,GLOBAL_CONTROL);
        n138_error=n138_checkpoint();if(n138_error)return n138_poll_failure("decon-reset",id,n138_snapshot,n138_error);
        if (~n138_snapshot & GLOBAL_CONTROL_SRESET)'''
        if old not in body:raise ValueError('exact native DECON reset ACK138 required')
        body=body.replace(old,new,1)
        return body.replace('return -EBUSY;','return n138_poll_failure("decon-reset",id,n138_snapshot,-EBUSY);',1)
    raw=edit_function(raw,'decon_reg_reset',lambda body:handoff_body(body,reset(body)))
    raw=edit_function(raw,'decon_reg_set_te_qactive_pll_mode',lambda body:body.replace('u32 val, mask;','u32 val, mask;\n    (void)id;',1))
    def run_off(body):
        body=body.replace('u32 status;','u32 status=0;int n138_error;')
        body=body.replace('status = decon_reg_get_run_status(id);','''n138_error=n138_checkpoint();if(n138_error)return n138_poll_failure("decon-run-off",id,status,n138_error);
        status = decon_reg_get_run_status(id);
        n138_error=n138_checkpoint();if(n138_error)return n138_poll_failure("decon-run-off",id,status,n138_error);''',1)
        return body.replace('return -EBUSY;','return n138_poll_failure("decon-run-off",id,status,-EBUSY);',1)
    output[path]=edit_function(raw,'decon_reg_wait_run_is_off_timeout',lambda body:handoff_body(body,run_off(body)))


ACCESSORS={
 'decon.h':('decon_read','decon_read_mask','decon_write','decon_write_mask',
             'dsc_read','dsc_write','dsc_write_mask','sysreg_read','sysreg_read_mask',
             'sysreg_write','sysreg_write_mask'),
 'dpp.h':('dpp_read','dpp_read_mask','dpp_write','dpp_write_mask',
           'dma_com_read','dma_com_read_mask','dma_com_write','dma_com_write_mask',
           'dma_read','dma_read_mask','dma_write','dma_write_mask'),
 'dsim.h':('dsim_read','dsim_read_mask','dsim_write','dsim_write_mask',
            'dsim_phy_read','dsim_phy_read_mask','dsim_phy_extra_write','dsim_phy_write','dsim_phy_write_mask'),
 'displayport.h':('displayport_read','displayport_read_mask','displayport_write','displayport_write_mask',
                   'displayport_phy_enabled','displayport_phy_read','displayport_phy_read_mask',
                   'displayport_phy_write','displayport_phy_write_mask')}


def accessor_gate(header,name,args):
    if header=='dpp.h':
        if 'write' in name:return 'n138_dpp_write_begin(id,reg_id)'
        return 'n138_access_begin(N138_DPP,id)'
    if header=='decon.h':
        if name in ('decon_read','decon_read_mask'):
            return 'n138_access_begin((id==0 && reg_id==CLOCK_CONTROL_0)?N138_DECON_SHARED_ACCESS:N138_DECON,id)'
        if name=='decon_write_mask':
            return 'n138_access_begin((id==0 && reg_id==CLOCK_CONTROL_0 && mask==CLOCK_CONTROL_0_TE_QACTIVE_PLL_ON && !(val&mask))?N138_DECON_SHARED_ACCESS:N138_DECON,id)'
        return 'n138_access_begin(N138_DECON,'+('0' if name.startswith('dsc_') else 'id')+')'
    if header=='dsim.h':return 'n138_access_begin(N138_DSIM,id)'
    return 'n138_access_begin('+('N138_DP_PHY_ACCESS' if '_phy_' in name else 'N138_DP')+',0)'


def invalidate_releases(raw):
    text=raw.decode();changes=[]
    excluded=[(m.start(),m.end()) for m in TOKEN.finditer(text) if m.group().startswith(('/*','//','"',"'"))]
    names=r'iounmap|devm_iounmap|free_irq|devm_free_irq|kthread_stop|destroy_workqueue|pm_runtime_disable|kfree'
    for match in re.finditer(r'\b('+names+r')\s*\(',text):
        if any(start<=match.start()<end for start,end in excluded):continue
        end=balanced(text,match.end()-1,'(',')')
        if match.group(1)=='kfree' and text[match.end():end-1].strip() not in ('decon','dpp','displayport','dsim'):continue
        changes.append((match.start(),end,'N138_INVALIDATE_BEFORE('+text[match.start():end]+')'))
    for start,end,replacement in reversed(changes):text=text[:start]+replacement+text[end:]
    return text.encode()


def secure_overlay(output):
    path='drivers/misc/tui/stui_core.c'
    def start(body):
        anchor='pr_debug("[STUI] STUI_HW_IOCTL_START_TUI called\\n");'
        if body.count(anchor)!=1:raise ValueError('exact earliest TUI START138 boundary required')
        return body.replace(anchor,'#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\n    if(!n138_secure_begin())return STUI_RET_ERR_INTERNAL_ERROR;\n    n138_user_end();\n#endif\n        '+anchor,1)
    raw=edit_function(output[path],'stui_process_cmd',start)
    output[path]=wrap(raw,names={'stui_process_cmd'})
    path=BASE+'decon_core.c'
    # Even a direct trusted-UI control entry, bypassing the user ioctl, taints
    # before its native worker/register/mapping effects.
    output[path]=wrap(output[path],names={'decon_tui_protection'},access=lambda name,args:'n138_secure_begin()')
    path='drivers/soc/samsung/exynos-hdcp/exynos-hdcp2-teeif.c'
    text,rows=definitions(output[path]);names={row[4] for row in rows}
    output[path]=wrap(output[path],names=names,
        access=lambda name,args:'n138_user_begin()' if name=='hdcp_tee_open' else 'n138_secure_begin()')
    path='drivers/soc/samsung/exynos-hdcp/dp_link/exynos-hdcp2-dplink-inter.c'
    output[path]=wrap(output[path],names={'hdcp_dplink_auth_check'},access=lambda name,args:'n138_secure_begin()')
    path='drivers/soc/samsung/exynos-smc.c';raw=output[path]
    text,row=selected(raw,'exynos_smc');start,body,end,_,_,_=row
    native='static '+text[start:end].replace(' exynos_smc(',' exynos_smc_n138_native(',1)
    helper='''
#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
static bool n138_smc_target(unsigned long cmd,unsigned long arg1,unsigned long arg2)
{
    unsigned long address;
    if(cmd==SMC_PROTECTION_SET && arg2>=PROT_GF0 && arg2<=PROT_WB1)return true;
    if(cmd!=(unsigned long)SMC_CMD_REG || (arg1&SMC_REG_CLASS_MASK)!=SMC_REG_CLASS_SFR_W)return false;
    address=(arg1&~(unsigned long)SMC_REG_CLASS_MASK)<<2;
    return (address>=0x19000000UL && address<0x19200000UL) ||
           (address>=0x130b0000UL && address<0x130c0000UL);
}
#endif
int exynos_smc(unsigned long cmd,unsigned long arg1,unsigned long arg2,unsigned long arg3)
{
    int answer;
#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
    bool target=n138_smc_target(cmd,arg1,arg2);
    if(target && !n138_secure_begin())return -ESHUTDOWN;
#endif
    answer=exynos_smc_n138_native(cmd,arg1,arg2,arg3);
#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
    if(target)n138_user_end();
#endif
    return answer;
}
'''
    output[path]=(text[:start]+native+helper+text[end:]).encode()


def render(stock,identity,source128):
    for name,wanted in NATIVE_PINS.items():
        if name not in stock or sha(stock[name])!=wanted:raise ValueError('pinned138 native source differs: '+name)
    output=retained.render(stock,identity,source128)
    for name in NATIVE_PINS:
        if name not in output:output[name]=stock[name]
    for path in (BASE+name for name in FINITE_FILES):
        if path not in output:raise ValueError('exact selected DPU source absent: '+path)
    dpp_overlay(output)
    output[BASE+'decon_core.c']=probe_hooks(output[BASE+'decon_core.c'],'N138_DECON','decon',
        'decon_drvdata[decon->id] = decon;',
        'decon_info("decon%d registered successfully", decon->id);',
        'ret = decon_initial_display(decon, false);')
    output[BASE+'displayport_drv.c']=probe_hooks(output[BASE+'displayport_drv.c'],'N138_DP','displayport',
        'displayport_drvdata = displayport;',
        'displayport_info("displayport driver has been probed.\\n");')
    output[BASE+'dsim_drv.c']=probe_hooks(output[BASE+'dsim_drv.c'],'N138_DSIM','dsim',
        'dsim_drvdata[dsim->id] = dsim;',
        'dsim_info("dsim%d driver(%s mode) has been probed.\\n", dsim->id,')
    cal_poll_overlay(output)
    # The secure/TUI specialized wrappers precede generic finite-call guards;
    # exclude their original and renamed definitions from a second wrapper.
    secure_overlay(output)
    for name in FINITE_FILES:
        path=BASE+name;raw=invalidate_releases(output[path]);_,rows=definitions(raw)
        names={row[4] for row in rows if not row[4].endswith('_n138_native') and
               row[4]!='decon_tui_protection'}
        output[path]=wrap(raw,names=names-SLEEPING_THREADS)
    for name,names in ACCESSORS.items():
        output[BASE+name]=wrap(output[BASE+name],names=names,
            access=lambda function,args,header=name:accessor_gate(header,function,args))
    # Raw HDR and DSIM sysreg accesses bypass the inline SFR primitives.
    for name,names,gate in (
        ('mcd_hdr/hdr_reg.c',{'mcd_reg_read','mcd_reg_write','mcd_reg_write_mask'},'n138_access_begin(N138_HDR_ACCESS,hdr->id)'),
        ('cal_9820/dsim_reg.c',{'dpu_sysreg_select_dphy_rst_control','dpu_sysreg_dphy_reset'},'n138_access_begin(N138_DSIM,dsim_id)')):
        # Already generic-wrapped original functions get an outer exact-resource
        # guard, with a distinct suffix to keep original prototypes unambiguous.
        raw=output[BASE+name]
        for function in names:
            raw=raw.replace((function+'_n138_native').encode(),(function+'_n138_inner').encode())
        output[BASE+name]=wrap(raw,names=names,access=lambda function,args,value=gate:value)
    header=b'#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\n#include <linux/v138_display.h>\n#else\n#define N138_INVALIDATE_BEFORE(expression) (expression)\n#endif\n'
    for path in set(BASE+name for name in FINITE_FILES)|set(BASE+name for name in ACCESSORS)|{
        'drivers/misc/tui/stui_core.c','drivers/soc/samsung/exynos-hdcp/exynos-hdcp2-teeif.c',
        'drivers/soc/samsung/exynos-hdcp/dp_link/exynos-hdcp2-dplink-inter.c','drivers/soc/samsung/exynos-smc.c'}:
        output[path]=header+output[path]
    for name,branch in {'decon_core.c':'N138_DECON_NATIVE','dpp_drv.c':'N138_DPP_NATIVE',
                        'displayport_drv.c':'N138_DP_NATIVE','dsim_drv.c':'N138_DSIM_NATIVE',
                        'cal_9820/decon_reg.c':'N138_DECON_CAL','cal_9820/dpp_reg.c':'N138_DPP_CAL'}.items():
        include='../v138_display_native.inc' if name.startswith('cal_9820/') else 'v138_display_native.inc'
        output[BASE+name]+=('\n#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\n#define '+branch+'\n#include "'+include+'"\n#endif\n').encode()
    output[BASE+'v138_display_native.inc']=(HERE/'v138_display_native.inc').read_bytes()
    output[BASE+'v138_display.c']=(HERE/'v138_display.c').read_bytes()
    output['include/linux/v138_display.h']=(HERE/'v138_display.h').read_bytes()
    output[BASE+'Makefile']+=b'\nobj-$(CONFIG_NOTE10_XNU_KEXEC_HANDOFF) += v138_display.o\n'
    cal=output['drivers/soc/samsung/cal-if/v136_cal.inc']
    cal=b'#include <linux/v138_display.h>\n'+cal
    cal=once(cal,b'index==1 || index==2 || index==4',b'index==1 || index==2 || index==3 || index==4')
    cal=once(cal,b'{0,0x1d00,0x1d80,0,0x1e80',b'{0,0x1d00,0x1d80,0x1e00,0x1e80')
    cal=once(cal,b'"blkpwr_npu1",NULL,"blkpwr_dspm"',b'"blkpwr_npu1","blkpwr_dpu","blkpwr_dspm"')
    cal=once(cal,b'domains!=N136_G2D_DOMAINS)return -EINVAL;',b'domains!=N136_G2D_DOMAINS && domains!=N138_DPU_DOMAINS)return -EINVAL;')
    cal=once(cal,b'(type==N136_G2D_DOMAIN_OFF_FROZEN && domains==N136_G2D_DOMAINS)))',
        b'(type==N136_G2D_DOMAIN_OFF_FROZEN && domains==N136_G2D_DOMAINS) ||\n         (type==N138_DPU_NATIVE_STOP_FROZEN && domains==N138_DPU_DOMAINS) ||\n         (type==N138_DPU_DOMAIN_OFF_FROZEN && domains==N138_DPU_DOMAINS)))')
    output['drivers/soc/samsung/cal-if/v136_cal.inc']=cal
    path='arch/arm64/mm/v130_kernel.c';raw=output[path]
    raw=once(raw,b'    if(result)n131_gate_refused("dma-provider",result,NULL);\n    return result;',
        b'    if(result)n131_gate_refused("dma-provider",result,NULL);\n    if(!result)result=n138_display_prepare();\n    return result;')
    raw=once(raw,b'    if(!result)result=n130_iommu_prepare();',
        b'    if(!result)result=n138_display_final();\n    if(!result)result=n130_iommu_prepare();')
    raw=edit_function(raw,'n130_after_shutdown',lambda body:body.replace(
        '    return result;','    if(result)(void)n138_display_unwind();\n    return result;',1))
    raw=once(raw,b'void n130_terminal_recovery(void)\n{',
        b'void n130_terminal_recovery(void)\n{\n    (void)n138_display_unwind();')
    raw=once(raw,b'if(result){n131_gate_refused("final",result,NULL);WRITE_ONCE(n130_arm_state,4);return result;}',
        b'if(result){n131_gate_refused("final",result,NULL);WRITE_ONCE(n130_arm_state,4);(void)n138_display_unwind();return result;}')
    output[path]=raw
    output['include/linux/v130_kernel_api.h']=once(output['include/linux/v130_kernel_api.h'],b'int n130_before_device_shutdown(void);',
        b'int n130_before_device_shutdown(void);\nint n138_display_prepare(void);\nint n138_display_final(void);\nint n138_display_unwind(void);')
    output['kernel/kexec_core.c']=once(output['kernel/kexec_core.c'],b' Unlock:\n\tmutex_unlock(&kexec_mutex);',
        b' Unlock:\n#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\n    (void)n138_display_unwind();\n#endif\n\tmutex_unlock(&kexec_mutex);')
    kconfig=output['arch/arm64/Kconfig']
    output['arch/arm64/Kconfig']=once(kconfig,b' depends on EXYNOS_NPU && NPU_HARDWARE && NPU_INTERFACE && !NPU_LOOPBACK && !NPU_ZEBU_EMULATION',
        b' depends on EXYNOS_NPU && NPU_HARDWARE && NPU_INTERFACE && !NPU_LOOPBACK && !NPU_ZEBU_EMULATION\n depends on EXYNOS_DPU20 && EXYNOS_DPP && EXYNOS_DISPLAYPORT && EXYNOS_MIPI_DSIM')
    return {name:raw.replace(b'N10XNU137',b'N10XNU138') for name,raw in output.items()}


def install(source,identity,source128):
    source=Path(source).resolve()
    stock={name:(source/name).read_bytes() for name in PINS}
    output=render(stock,identity,source128)
    for name in output:
        path=source/name
        if not path.resolve().is_relative_to(source) or any(p.is_symlink() for p in (path,*path.parents)):
            raise ValueError('unsafe138 native overlay path')
        if name not in PINS and path.exists():raise ValueError('new138 component exists')
    for name,raw in output.items():
        path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    return {name:sha(raw) for name,raw in output.items()}
