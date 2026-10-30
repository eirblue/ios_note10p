"""Default-off dispatch observation layered over the unchanged v52 snapshot."""
import hashlib
from pathlib import Path
from prepare_cpu_pm_roundtrip import replace_unique as replace, function

OPTION = 'CONFIG_NOTE10_CPU_PM_NOTIFIER_TRACE'
FLAG = 'cpu_pm_notifier_trace'
VERSION = FLAG + '_version'
PREFIX = FLAG + '_'
MARKER = b'N10CPDC1'
MODEL = 'cpu-pm-notifier-trace-model'
PACKAGE = 'cpu-pm-notifier-trace-package-model'
BASE = 'cpu-pm-notifier-trace-baseline'
PREPARED = 'cpu-pm-notifier-trace-prepared'
TARGETS = ('kernel/notifier.c', 'kernel/cpu_pm.c',
           'include/linux/note10_pm_preconditions.h',
           'arch/arm64/mm/note10_pm_pre_probe.c', 'kernel/power/Kconfig')
PINNED_NOTIFIER_SHA256 = 'ab19243be9cf32c9943fcdc352fef42357274ed4bbc9043f770f62e77bc968c5'
SOURCES = ('prepare_cpu_pm_notifier_trace.py', 'decode_cpu_pm_notifier_trace.py',
           'test_cpu_pm_notifier_trace.py', 'test_cpu_pm_notifier_trace_package.py',
           'cpu_pm_roundtrip_binding.py', 'build_handoff_kernel.py',
           'prepare_cpu_pm_roundtrip_flow_compat.py',
           'test_cpu_pm_roundtrip_package_flow.py')
BLOCK = b'''\nconfig NOTE10_CPU_PM_NOTIFIER_TRACE
\tbool "Observe guarded CPU PM notifier dispatch order"
\tdepends on NOTE10_CPU_PM_NOTIFIER_COUNTS && NOTE10_CPU_PM_ROUNDTRIP
\tdefault n
'''
STRUCT = b'''#ifdef CONFIG_NOTE10_CPU_PM_NOTIFIER_TRACE
/* Scalar record only. Nibbles encode admitted roster indices 1..6. */
struct n10_cpu_pm_dispatch_sample {
 unsigned int generation, roster, phases, conflict, valid;
 unsigned int entered[2], returned[2], entry_order[2], return_order[2];
};
void n10_dispatch_begin(unsigned int generation);
void n10_dispatch_seed(unsigned int index, struct notifier_block *node);
void n10_dispatch_arm(struct notifier_block **head, unsigned long event, unsigned int phase);
void n10_dispatch_disarm(struct notifier_block **head, unsigned long event);
void n10_dispatch_finish(struct n10_cpu_pm_dispatch_sample *out);
#endif
'''
OBSERVER = b'''#ifdef CONFIG_NOTE10_CPU_PM_NOTIFIER_TRACE
#include <linux/smp.h>
#include <linux/string.h>
#include <linux/note10_pm_preconditions.h>
/* Private non-exported symbols: notifier.o has no CPU_PM symbol dependency.
 * Pointer fields are transient; only the scalar sample leaves this object.
 * All observers are notrace and do not invoke callbacks or acquire locks. */
static struct {
 struct notifier_block **head;
 struct notifier_block *blocks[6];
 int (*callbacks[6])(struct notifier_block *, unsigned long, void *);
 unsigned long event;
 unsigned int phase, armed, depth, active;
 struct n10_cpu_pm_dispatch_sample sample;
} n10_dispatch;
static const char n10_dispatch_marker[] __used = "N10CPDC1";

void notrace n10_dispatch_begin(unsigned int generation)
{
 if (raw_smp_processor_id() != 0) return;
 memset(&n10_dispatch, 0, sizeof(n10_dispatch));
 n10_dispatch.sample.generation = generation;
}
void notrace n10_dispatch_seed(unsigned int index, struct notifier_block *node)
{
 unsigned int i;
 if (raw_smp_processor_id() != 0) return;
 if (!n10_dispatch.sample.generation || !node || index >= 6 ||
     index != n10_dispatch.sample.roster) {
  n10_dispatch.sample.conflict = 1; return;
 }
 for (i = 0; i < index; i++)
  if (n10_dispatch.blocks[i] == node) n10_dispatch.sample.conflict = 1;
 n10_dispatch.blocks[index] = node;
 n10_dispatch.callbacks[index] = READ_ONCE(node->notifier_call);
 if (!n10_dispatch.callbacks[index]) n10_dispatch.sample.conflict = 1;
 n10_dispatch.sample.roster++;
}
void notrace n10_dispatch_arm(struct notifier_block **head, unsigned long event,
                              unsigned int phase)
{
 if (raw_smp_processor_id() != 0) return;
 if (n10_dispatch.armed || phase > 1 || !head ||
     !n10_dispatch.sample.generation || n10_dispatch.sample.roster != 6 ||
     (n10_dispatch.sample.phases & (1U << phase))) {
  n10_dispatch.sample.conflict = 1; return;
 }
 n10_dispatch.head = head; n10_dispatch.event = event;
 n10_dispatch.phase = phase; n10_dispatch.depth = 0;
 n10_dispatch.active = 0; n10_dispatch.armed = 1;
}
static void noinline notrace n10_dispatch_observe(struct notifier_block **head,
                                        unsigned long event,
                                        struct notifier_block *node,
                                        unsigned int returning)
{
 unsigned int index, phase;
 /* CPU0 first: a foreign CPU never reads or writes the owner's scalar latch
  * or transient pointers. Exact head/event gate precedes callback payload. */
 if (raw_smp_processor_id() != 0) return;
 if (!n10_dispatch.armed || head != n10_dispatch.head ||
     event != n10_dispatch.event) return;
 phase = n10_dispatch.phase;
 for (index = 0; index < 6; index++)
  if (n10_dispatch.blocks[index] == node) break;
 if (index == 6 || READ_ONCE(node->notifier_call) != n10_dispatch.callbacks[index])
  n10_dispatch.sample.conflict = 1;
 if (!returning) {
  if (n10_dispatch.depth) {
   n10_dispatch.sample.conflict = 1;
   if (n10_dispatch.depth < 7) n10_dispatch.depth++;
   return;
  }
  n10_dispatch.depth = 1; n10_dispatch.active = index + 1;
  if (n10_dispatch.sample.entered[phase] >= 6) {
   n10_dispatch.sample.conflict = 1; return;
  }
  n10_dispatch.sample.entered[phase]++;
  n10_dispatch.sample.entry_order[phase] =
   (n10_dispatch.sample.entry_order[phase] << 4) | (index + 1);
 } else {
  if (n10_dispatch.depth > 1) { n10_dispatch.depth--; return; }
  if (n10_dispatch.depth != 1 || n10_dispatch.active != index + 1)
   n10_dispatch.sample.conflict = 1;
  n10_dispatch.depth = 0; n10_dispatch.active = 0;
  if (n10_dispatch.sample.returned[phase] >= 6) {
   n10_dispatch.sample.conflict = 1; return;
  }
  n10_dispatch.sample.returned[phase]++;
  n10_dispatch.sample.return_order[phase] =
   (n10_dispatch.sample.return_order[phase] << 4) | (index + 1);
 }
}
void notrace n10_dispatch_disarm(struct notifier_block **head, unsigned long event)
{
 if (raw_smp_processor_id() != 0) return;
 if (!n10_dispatch.armed || head != n10_dispatch.head ||
     event != n10_dispatch.event) return;
 if (n10_dispatch.depth) n10_dispatch.sample.conflict = 1;
 n10_dispatch.sample.phases |= 1U << n10_dispatch.phase;
 n10_dispatch.armed = 0; n10_dispatch.head = NULL;
 n10_dispatch.event = 0; n10_dispatch.active = 0; n10_dispatch.depth = 0;
}
void notrace n10_dispatch_finish(struct n10_cpu_pm_dispatch_sample *out)
{
 unsigned int i;
 if (raw_smp_processor_id() != 0) {
  memset(out, 0, sizeof(*out)); return;
 }
 n10_dispatch.sample.valid = !n10_dispatch.armed &&
  !n10_dispatch.sample.conflict && n10_dispatch.sample.roster == 6 &&
  n10_dispatch.sample.phases == 3;
 for (i = 0; i < 2; i++)
  if (n10_dispatch.sample.entered[i] != 6 || n10_dispatch.sample.returned[i] != 6 ||
      n10_dispatch.sample.entry_order[i] != 0x123456U ||
      n10_dispatch.sample.return_order[i] != 0x123456U)
   n10_dispatch.sample.valid = 0;
 *out = n10_dispatch.sample;
 /* Wipe every transient block, callback-field and head pointer on all exits. */
 memset(&n10_dispatch, 0, sizeof(n10_dispatch));
}
NOKPROBE_SYMBOL(n10_dispatch_begin);
NOKPROBE_SYMBOL(n10_dispatch_seed);
NOKPROBE_SYMBOL(n10_dispatch_arm);
NOKPROBE_SYMBOL(n10_dispatch_observe);
NOKPROBE_SYMBOL(n10_dispatch_disarm);
NOKPROBE_SYMBOL(n10_dispatch_finish);
#endif
'''
FRAME_FORMAT = ('id=%s copy=%u generation=%u transaction=%u version=1 roster=%u phases=%u '
                'conflict=%u valid=%u en=%u er=%u ee=%u re=%u xn=%u xr=%u xe=%u rx=%u')
FRAME_ARGS = ('N10_RESERVE_BUILD_ID,copy,generation,s->dispatch.generation,s->dispatch.roster,s->dispatch.phases,'
              's->dispatch.conflict,s->dispatch.valid,s->dispatch.entered[0],'
              's->dispatch.returned[0],s->dispatch.entry_order[0],s->dispatch.return_order[0],'
              's->dispatch.entered[1],s->dispatch.returned[1],'
              's->dispatch.entry_order[1],s->dispatch.return_order[1]')
EMITTER = ('''#ifdef CONFIG_NOTE10_CPU_PM_NOTIFIER_TRACE
static int n10_pre_emit_dispatch(unsigned int copy,
 const struct n10_cpu_pm_roundtrip_sample *s, unsigned int generation, unsigned int *budget, int emit)
{
 char frame[512]; int n;
 n=snprintf(frame,sizeof(frame),"''' + FRAME_FORMAT + '",' + FRAME_ARGS + ''');
 return n10_pre_emit("N10CPD1",frame,n,budget,emit);
}
#endif
''').encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def transform(files):
    if set(files) != set(TARGETS) or any(not isinstance(v, bytes) for v in files.values()):
        raise ValueError('exact dispatch trace inputs required')
    if sha(files['kernel/notifier.c']) != PINNED_NOTIFIER_SHA256:
        raise ValueError('generic notifier baseline differs from pinned source')
    out = dict(files)
    notifier = out['kernel/notifier.c']
    notifier = replace(notifier, b'#include <linux/debug-snapshot.h>\n',
                       b'#include <linux/debug-snapshot.h>\n' + OBSERVER, 'observer definition')
    call = b'\t\tret = nb->notifier_call(nb, val, v);'
    notifier = replace(notifier, call,
        b'#ifdef CONFIG_NOTE10_CPU_PM_NOTIFIER_TRACE\n\t\tn10_dispatch_observe(nl, val, nb, 0);\n#endif\n' +
        call + b'\n#ifdef CONFIG_NOTE10_CPU_PM_NOTIFIER_TRACE\n\t\tn10_dispatch_observe(nl, val, nb, 1);\n#endif',
        'original callback statement boundary')
    out['kernel/notifier.c'] = notifier
    header = out[TARGETS[2]]
    header = replace(header, b'struct n10_cpu_pm_roundtrip_sample {',
                     STRUCT + b'struct n10_cpu_pm_roundtrip_sample {', 'scalar struct')
    header = replace(header, b' int enter_error, exit_error, error;\n',
                     b' int enter_error, exit_error, error;\n#ifdef CONFIG_NOTE10_CPU_PM_NOTIFIER_TRACE\n struct n10_cpu_pm_dispatch_sample dispatch;\n#endif\n', 'embedded scalar sample')
    out[TARGETS[2]] = header
    cpu = out['kernel/cpu_pm.c']
    cpu = replace(cpu, b'static ATOMIC_NOTIFIER_HEAD(cpu_pm_notifier_chain);',
                  b'#ifdef CONFIG_NOTE10_CPU_PM_NOTIFIER_TRACE\n#include <linux/note10_pm_preconditions.h>\n#endif\nstatic ATOMIC_NOTIFIER_HEAD(cpu_pm_notifier_chain);', 'trace declarations')
    call = b'\tret = __atomic_notifier_call_chain(&cpu_pm_notifier_chain, event, NULL,\n\t\tnr_to_call, nr_calls);'
    cpu = replace(cpu, call,
        b'#ifdef CONFIG_NOTE10_CPU_PM_NOTIFIER_TRACE\n\tif (n10_capture_nr_calls) n10_dispatch_arm(&cpu_pm_notifier_chain.head, event, event == CPU_PM_ENTER ? 0 : 1);\n#endif\n' +
        call + b'\n#ifdef CONFIG_NOTE10_CPU_PM_NOTIFIER_TRACE\n\tif (n10_capture_nr_calls) n10_dispatch_disarm(&cpu_pm_notifier_chain.head, event);\n#endif', 'notify phase scope')
    cpu = replace(cpu, b'    out->attempted = 1;\n',
                  b'    out->attempted = 1;\n#ifdef CONFIG_NOTE10_CPU_PM_NOTIFIER_TRACE\n    n10_dispatch_begin(generation);\n#endif\n', 'owned begin')
    cpu = replace(cpu, b'        index++;\n        node = rcu_dereference_raw(node->next);',
                  b'#ifdef CONFIG_NOTE10_CPU_PM_NOTIFIER_TRACE\n        n10_dispatch_seed(index, node);\n#endif\n        index++;\n        node = rcu_dereference_raw(node->next);', 'locked roster snapshot')
    cpu = replace(cpu, b'done:\n    out->error = error;',
                  b'done:\n#ifdef CONFIG_NOTE10_CPU_PM_NOTIFIER_TRACE\n    n10_dispatch_finish(&out->dispatch);\n#endif\n    out->error = error;', 'all-path pointer wipe')
    out['kernel/cpu_pm.c'] = cpu
    probe = out[TARGETS[3]]
    anchor = b'static int n10_pre_emit_terminal('
    probe = replace(probe, anchor, EMITTER + anchor, 'dispatch emitter')
    anchor = b'        ret=n10_pre_emit_counts(copy,&n10_pre_terminal_report,generation,&budget); if(ret)return ret;'
    probe = replace(probe, anchor, anchor + b'\n#ifdef CONFIG_NOTE10_CPU_PM_NOTIFIER_TRACE\n        ret=n10_pre_emit_dispatch(copy,&n10_pre_terminal_report,generation,&budget,1); if(ret)return ret;\n#endif', 'terminal companion')
    # This call shares the existing budget/length checks and emits one copy per outer loop.
    anchor = b'            for (i=0;i<3;i++) {'
    probe = replace(probe, anchor,
        b'#ifdef CONFIG_NOTE10_CPU_PM_NOTIFIER_TRACE\n            ret=n10_pre_emit_dispatch(copy,&n10_pre_report.roundtrip,generation,&budget,emit); if(ret)return ret;\n#endif\n' + anchor,
        'success companion')
    out[TARGETS[3]] = probe
    if b'config NOTE10_CPU_PM_NOTIFIER_TRACE' in out[TARGETS[4]]:
        raise ValueError('trace configuration already exists')
    out[TARGETS[4]] += BLOCK
    return out


def prepare(source, output):
    source, output = Path(source), Path(output)
    if source.is_symlink() or not source.is_dir() or output.is_symlink():
        raise ValueError('trace source/output root unsafe')
    for name in TARGETS:
        if (source/name).is_symlink() or not (source/name).is_file():
            raise ValueError('trace source target missing/unsafe')
    if any((output/dirname).exists() or (output/dirname).is_symlink() for dirname in (BASE,PREPARED)):
        raise ValueError('trace snapshot already exists or unsafe')
    before = {name: (source / name).read_bytes() for name in TARGETS}
    after = transform(before)
    for dirname, files in ((BASE, before), (PREPARED, after)):
        destination = output / dirname
        if destination.exists() or destination.is_symlink():
            raise ValueError('trace snapshot already exists or unsafe')
        for name in TARGETS:
            path = destination / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(files[name])
    for name in TARGETS:
        (source / name).write_bytes(after[name])
    return {FLAG: True, VERSION: 1,
            PREFIX + 'baseline_sha256': {name: sha(before[name]) for name in TARGETS},
            PREFIX + 'prepared_sha256': {name: sha(after[name]) for name in TARGETS}}
