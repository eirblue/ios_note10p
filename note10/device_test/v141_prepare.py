"""Bounded exact-context display admission drain over immutable140."""
from pathlib import Path
import re
import v140_prepare as retained
import v139_prepare as lexical
from v138_prepare import once
HERE=Path(__file__).resolve().parent
PINS=retained.PINS
OPTION=retained.OPTION
profile=retained.profile
sha=retained.sha
BASE='drivers/video/fbdev/exynos/dpu20/'
NATIVE_PATH=BASE+'v141_admission.inc'


def edit(raw,name,callback):
    text,rows=lexical.definitions(raw);rows=[row for row in rows if row[4]==name]
    if len(rows)!=1:raise ValueError('one exact admission function required: '+name)
    row=rows[0];return (text[:row[0]]+callback(text[row[0]:row[2]])+text[row[2]:]).encode()


def admission_source(raw):
    raw=once(raw,b'struct n138_context { struct task_struct *task; unsigned int depth; bool interrupt; };',b'struct n138_context { struct task_struct *task; unsigned int depth,irq_state; const char *entry; bool task_owned; };')
    raw=edit(raw,'n138_context_locked',lambda body:body.replace('bool interrupt=in_interrupt();','unsigned int irq_state=irq_count();').replace('n138_contexts[i].interrupt==interrupt','n138_contexts[i].irq_state==irq_state'))
    def ticket(body):
        body=body.replace('n138_ticket_locked(void)','n138_ticket_locked(const char *entry)')
        body=body.replace('    if(!context)for','    if(n138_active==~0U){n138_history|=1;return false;}\n    if(!context)for',1)
        body=body.replace('context=&n138_contexts[i];context->task=current;',
            'if(n138_contexts[i].task || n138_contexts[i].task_owned){n138_history|=1;return false;}\n        get_task_struct(current);context=&n138_contexts[i];context->task=current;context->task_owned=true;',1)
        body=body.replace('context->interrupt=in_interrupt();break;','context->irq_state=irq_count();context->entry=entry?entry:"none";break;')
        return body.replace(' || n138_active==~0U','').replace('if(!context || context->depth==~0U)','if(!context || !context->task_owned || context->depth==~0U)')
    raw=edit(raw,'n138_ticket_locked',ticket)
    def named(body):
        body=body.replace('n138_user_begin(void)','n141_user_begin(const char *entry)').replace('n138_ticket_locked()','n138_ticket_locked(entry)')
        return body+'\nbool n138_user_begin(void)\n{ return n141_user_begin("compat"); }\n'
    raw=edit(raw,'n138_user_begin',named)
    for name,label in (('n138_access_begin','mmio'),('n138_dpp_write_begin','dpp-mmio'),('n138_secure_begin','secure')):
        raw=edit(raw,name,lambda body,label=label:body.replace('n138_ticket_locked()','n138_ticket_locked("'+label+'")'))
    def ending(body):
        body=body.replace('unsigned long flags;struct n138_context *context;','unsigned long flags;struct n138_context *context;struct task_struct *retired=NULL;')
        body=body.replace('if(n138_active && context){','if(n138_active && context && context->task_owned){')
        body=body.replace('if(!context->depth)context->task=NULL;','if(!context->depth){retired=context->task;context->task_owned=false;context->task=NULL;context->entry=NULL;}')
        return body.replace('    spin_unlock_irqrestore(&n138_lock,flags);','    spin_unlock_irqrestore(&n138_lock,flags);\n    if(retired)put_task_struct(retired);',1)
    raw=edit(raw,'n138_user_end',ending)
    raw=edit(raw,'n138_open_locked',lambda body:re.sub(r'/\*.*?\*/','/* Only an already counted exact task+IRQ-depth context may finish\n     * nested owned calls while closure is pending or refused. No new context;\n     * success requires actual active0/history0 before proof actions. */',body,count=1,flags=re.S))
    def prepare(body):
        start=body.index('    spin_lock_irqsave(&n138_lock,flags);')
        end=body.index('    ops[0]=n138_decon_native();',start)
        body=body[:start]+'    error=n141_display_close();\n    if(error)goto refused;\n'+body[end:]
        for anchor in ('        error=ops[family]->quiet(slot,&n138_detail);','        error=pm_runtime_get_if_in_use(slot->dev);','    mode=n136_cal_begin(N138_DPU_DOMAINS,&n138_detail);'):
            if body.count(anchor)!=1:raise ValueError('exact shared budget coupling required')
            indent=anchor[:len(anchor)-len(anchor.lstrip())]
            body=body.replace(anchor,indent+'error=n141_deadline_check();if(error)goto release;\n'+anchor,1)
        return '#include "v141_admission.inc"\n'+body
    return b'#include <linux/sched/task.h>\n'+edit(raw,'n138_display_prepare',prepare)


def named_entries(raw):
    text=raw.decode();code=lexical.lexical_code(text);changes=list(re.finditer(r'\bn138_user_begin\s*\(\s*\)',code))
    for match in reversed(changes):text=text[:match.start()]+'n141_user_begin(__func__)'+text[match.end():]
    return text.encode()


def render(stock,identity,source128):
    output=retained.render(stock,identity,source128)
    path=BASE+'v138_display.c';output[path]=admission_source(output[path])
    output['include/linux/v138_display.h']=once(output['include/linux/v138_display.h'],b'bool n138_user_begin(void);',b'bool n138_user_begin(void);\nbool n141_user_begin(const char *);')
    output[NATIVE_PATH]=(HERE/'v141_admission.inc').read_bytes()
    for name,raw in tuple(output.items()):
        if name.endswith(('.c','.h','.inc')):output[name]=named_entries(raw)
    return {name:raw.replace(b'N10XNU140',b'N10XNU141') for name,raw in output.items()}


def install(source,identity,source128):
    source=Path(source).resolve();stock={name:(source/name).read_bytes() for name in PINS};output=render(stock,identity,source128)
    for name in output:
        path=source/name
        if not path.resolve().is_relative_to(source) or any(p.is_symlink() for p in (path,*path.parents)):raise ValueError('unsafe141 overlay path')
        if name not in PINS and path.exists():raise ValueError('new141 component exists')
    for name,raw in output.items():
        path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    return {name:sha(raw) for name,raw in output.items()}
