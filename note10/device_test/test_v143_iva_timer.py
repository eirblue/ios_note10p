"""One NEW native-body IPC timer fixture; all execution belongs to ROOT."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
from v143_iva_timer import HEADER, IPC, HELPER, HELPER_SHA256, NATIVE_SHA256, patch_native

MCU = 'drivers/vision/iva/iva_mcu.c'
MCU_SHA256 = '0bf1bc903dcf14a3b5c413c43700bf337d559da3d9e93e6dc59712743b74ae6c'
TOKENS = re.compile(rb'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[{}]', re.S)


def selected_block(raw, pattern):
    matches = list(re.finditer(pattern, raw, re.M))
    if len(matches) != 1:
        raise ValueError('exact native definition required')
    start = matches[0].start()
    opening = raw.find(b'{', matches[0].end())
    depth = 0
    for token in TOKENS.finditer(raw, opening):
        if token.group() == b'{':
            depth += 1
        elif token.group() == b'}':
            depth -= 1
            if depth == 0:
                return raw[start:token.end()]
    raise ValueError('unbalanced native definition')


def function(raw, name):
    return selected_block(raw, rb'^(?:static\s+)?(?:inline\s+)?(?:int|void)\s+' + name.encode() + rb'\s*\(')


TYPES = r'''
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#undef ENABLE_IPCQ_WORK_QUEUE
#undef CHECK_PARAM_REGION_ALIGN
#define CONFIG_64BIT 1
#define __user
#define EINVAL 22
#define ESHUTDOWN 108
#define ENOMEM 12
#define EIO 5
#define EPERM 1
#define EBUSY 16
#define GFP_KERNEL 0
#define GFP_ATOMIC 1
#define MAX_IPCQ_PEND_NR 32
#define IPCQ_TIMEOUT_MS 2000
#define IPC_RES_Q_PARAM_SIZE 4
#define IPC_QUEUE_ACTIVE_FLAG 1U
#define IPC_CMD_FRAME_START 7U
#define ipc_func_sched_table 4U
#define ipc_func_iva_ctrl 2U
#define IPC_GET_FUNC(header) (header)
#define IPC_MK_HDR(a,b,c) ((a) + (b) + (c))
#define F_IPC_QUEUE_USED_SLOT 1U
#define F_IPC_QUEUE_MALLOC 2U
#define F_IPC_QUEUE_HEAD 4U
#define F_IPC_QUEUE_TAIL 8U
#define mbox_msg_default 0
#define mbox_msg_ipcq_ctrl 1
#define dev_dbg(dev, ...) ((void)(dev))
#define dev_info(dev, ...) ((void)(dev))
#define dev_err(dev, ...) ((void)(dev))
struct mutex { int held; };
typedef struct { int held; } spinlock_t;
typedef struct { int initialized; } wait_queue_head_t;
struct list_head { struct list_head *next, *prev; };
struct timer_list {
    void (*function)(uintptr_t);
    uintptr_t data;
    unsigned long expires;
    int pending, running;
};
struct device { int unused; };
struct iva_dev_data;
struct ipc_cmd_queue { int unused; };
struct ipc_res_queue { unsigned int flags; struct { unsigned int flags; } params[IPC_RES_Q_PARAM_SIZE]; };
struct iq_pend_mail { int unused; };
'''

DEPENDENCIES = r'''
typedef struct { int value; } atomic_t;
struct iva_dev_data { struct device *dev; struct iva_ipcq mcu_ipcq; atomic_t mcu_err_cnt; };
struct iva_proc { struct iva_dev_data *iva_data; };
struct ipc_cmd_param { uint32_t header, ipc_cmd_type, param_0; };
struct ipc_res_param { uint32_t header, rep_id, ret, ipc_cmd_type; uint16_t extra; };
struct _ipcq_res_param_ll { unsigned int flags; struct ipc_res_param res_param; };
enum mcu_err_context { muc_err_from_normal, mcu_err_from_irq, mcu_err_from_abort };
struct n143_callback { void *priv_data; };
static struct n143_callback iva_ipcq_cb, iva_ipcq_ctrl_cb;
static struct device device;
static struct iva_dev_data owner;
static struct iva_proc process;
static struct ipc_cmd_queue commands;
static struct ipc_res_queue responses;
static struct ipc_cmd_param command_slot;
static struct iq_pend_mail reservation[MAX_IPCQ_PEND_NR];
static struct _ipcq_res_param_ll synthetic_response;
static unsigned long jiffies = 100;
static unsigned int failures, cases, mod_calls, del_calls, sent, response_calls, frees;
static int allocation_fail, send_error, close_during_send, rearm_during_sync, queue_init_during_sync, queued_init;
static int rsv_freed, late_arm_result, queued_init_result;
static char cleanup[32];
static unsigned int cleanup_count;
static int iva_ipcq_init(struct iva_ipcq *, struct ipc_cmd_queue *, struct ipc_res_queue *);
static void iva_ipcq_deinit(struct iva_ipcq *);
static int n143_timer_arm(struct iva_ipcq *, unsigned int);
static void check(int condition, const char *label) {
    if (!condition) { fprintf(stderr, "FAIL %s\n", label); failures++; }
}
static void cleanup_event(char tag) { cleanup[cleanup_count++] = tag; cleanup[cleanup_count] = 0; }
static void mutex_init(struct mutex *lock) { lock->held = 0; }
static void mutex_lock(struct mutex *lock) { check(!lock->held, "no recursive lifecycle/native mutex"); lock->held = 1; }
static void mutex_unlock(struct mutex *lock) {
    check(lock->held, "balanced mutex release"); lock->held = 0;
    if (lock == &owner.mcu_ipcq.to_lifecycle_lock && queued_init) {
        queued_init = 0;
        queued_init_result = iva_ipcq_init(&owner.mcu_ipcq, &commands, &responses);
    }
}
static void mutex_destroy(struct mutex *lock) {
    check(!lock->held && !owner.mcu_ipcq.to_timer.pending && !owner.mcu_ipcq.to_timer.running, "drained before native mutex destroy");
    check(owner.mcu_ipcq.to_lifecycle_lock.held, "lifecycle held through native remove"); cleanup_event('D');
}
static void spin_lock_init(spinlock_t *lock) { lock->held = 0; }
static void spin_enter(spinlock_t *lock) { check(!lock->held, "no recursive spin lock"); lock->held = 1; }
static void spin_leave(spinlock_t *lock) { check(lock->held, "balanced spin release"); lock->held = 0; }
#define spin_lock_irqsave(lock, flags) do { (flags) = 1; spin_enter(lock); } while (0)
#define spin_unlock_irqrestore(lock, flags) do { (void)(flags); spin_leave(lock); } while (0)
static unsigned long msecs_to_jiffies(unsigned int milliseconds) { return milliseconds; }
static int mod_timer(struct timer_list *timer, unsigned long expires) {
    int pending = timer->pending;
    check(owner.mcu_ipcq.to_state_lock.held && !owner.mcu_ipcq.to_closed && !owner.mcu_ipcq.to_removing, "arm admitted under state lock");
    mod_calls++; timer->pending = 1; timer->expires = expires; return pending;
}
static int del_timer_sync(struct timer_list *);
static void fixture_setup_timer(struct timer_list *timer, void (*callback)(uintptr_t), uintptr_t data) {
    timer->function = callback; timer->data = data; timer->pending = timer->running = 0;
}
#define setup_timer(timer, callback, data) fixture_setup_timer(timer, callback, data)
static void init_waitqueue_head(wait_queue_head_t *queue) { queue->initialized = 1; }
static void list_init(struct list_head *list) { list->next = list->prev = list; }
#define INIT_LIST_HEAD(list) list_init(list)
static void *devm_kzalloc(struct device *dev, size_t bytes, int flags) {
    (void)dev; (void)bytes; (void)flags; return allocation_fail ? NULL : reservation;
}
static void devm_kfree(struct device *dev, void *pointer) {
    (void)dev; check(pointer == reservation && !rsv_freed, "one native reserved-buffer free");
    check(!owner.mcu_ipcq.to_timer.pending && !owner.mcu_ipcq.to_timer.running && owner.mcu_ipcq.to_removing, "timer permanently closed before free");
    rsv_freed = 1; frees++; cleanup_event('F');
}
static int iva_mbox_callback_register(int message, struct n143_callback *callback) { (void)message; (void)callback; return 0; }
static int iva_mbox_callback_unregister(struct n143_callback *callback) {
    check(!owner.mcu_ipcq.to_timer.pending && !owner.mcu_ipcq.to_timer.running, "drained before mailbox unregister");
    cleanup_event(callback == &iva_ipcq_ctrl_cb ? 'C' : 'I'); return 0;
}
static int atomic_read(const atomic_t *value) { return value->value; }
static void atomic_set(atomic_t *value, int number) { value->value = number; }
static int atomic_inc_return(atomic_t *value) { return ++value->value; }
static void *kmalloc(size_t bytes, int flags) {
    (void)bytes; check(flags == GFP_ATOMIC, "native timeout response remains atomic");
    return &synthetic_response;
}
static int iva_ipcq_insert_pending_mail(struct iva_ipcq *ipcq, uint64_t mail, bool from_mbox, bool from_irq) {
    (void)mail; (void)from_mbox; (void)from_irq;
    check(!ipcq->ipcq_mutex.held && !ipcq->ipcq_slock.held && !ipcq->rsv_slock.held && !ipcq->rspq_slock.held && !ipcq->to_state_lock.held, "all callback progress locks free during sync");
    check(!rsv_freed, "native callback before rsv free"); response_calls++; return 0;
}
static void wake_up(wait_queue_head_t *queue) { check(queue->initialized, "native response waiter initialized"); }
static int iva_ipcq_copy_from_user(uint32_t *dest, uint32_t *source, size_t bytes) { memcpy(dest, source, bytes); return 0; }
static bool iva_ipcq_handle_inside_func(struct iva_proc *proc, struct iva_ipcq *ipcq, struct ipc_cmd_param *param) { (void)proc; (void)ipcq; (void)param; return false; }
static int iva_ctrl_is_boot(struct iva_dev_data *iva) { (void)iva; return 1; }
static struct ipc_cmd_param *iva_ipcq_alloc_cmd(struct iva_ipcq *ipcq) { (void)ipcq; return &command_slot; }
static int iva_ipcq_send_cmd(struct iva_ipcq *ipcq, struct ipc_cmd_param *param) {
    (void)param; sent++;
    if (close_during_send) { close_during_send = 0; iva_ipcq_deinit(ipcq); }
    return send_error;
}
'''

CASES = r'''
static int del_timer_sync(struct timer_list *timer) {
    int pending = timer->pending;
    struct iva_ipcq *ipcq = &owner.mcu_ipcq;
    del_calls++;
    check(ipcq->to_lifecycle_lock.held && !ipcq->to_state_lock.held, "close synchronized outside state spinlock");
    check(!ipcq->ipcq_mutex.held && !ipcq->ipcq_slock.held && !ipcq->rsv_slock.held && !ipcq->rspq_slock.held && !ipcq->ipcq_stat.trans_mtx.held, "no callback-needed native lock held");
    check(ipcq->to_closed, "close visible before timer sync");
    if (rearm_during_sync) {
        rearm_during_sync = 0; late_arm_result = n143_timer_arm(ipcq, 99);
    }
    if (queue_init_during_sync) { queue_init_during_sync = 0; queued_init = 1; }
    timer->pending = 0;
    if (timer->running) { timer->function(timer->data); timer->running = 0; }
    return pending;
}
static void begin_case(bool initialize) {
    memset(&owner, 0, sizeof(owner)); memset(&process, 0, sizeof(process));
    memset(&commands, 0, sizeof(commands)); memset(&responses, 0, sizeof(responses));
    memset(&command_slot, 0, sizeof(command_slot)); memset(&synthetic_response, 0, sizeof(synthetic_response));
    mod_calls = del_calls = sent = response_calls = frees = cleanup_count = 0;
    cleanup[0] = 0; allocation_fail = send_error = close_during_send = rearm_during_sync = 0;
    queue_init_during_sync = queued_init = rsv_freed = 0; late_arm_result = queued_init_result = 0;
    owner.dev = &device; process.iva_data = &owner; cases++;
    check(iva_ipcq_probe(&owner) == 0, "actual native probe success");
    if (initialize) check(iva_ipcq_init(&owner.mcu_ipcq, &commands, &responses) == 0, "actual native init success");
}
int main(void) {
    int ret; unsigned int before;
    struct ipc_cmd_param request;
    /* 1: failed probe does not expose an uninitialized timer/lifecycle. */
    memset(&owner, 0, sizeof(owner)); owner.dev = &device; allocation_fail = 1; cases++;
    check(iva_ipcq_probe(&owner) == -ENOMEM && !owner.mcu_ipcq.to_timer.function, "probe allocation failure remains before timer setup");
    /* 2: probe starts closed; an arm cannot manufacture successful init. */
    begin_case(false); check(n143_timer_arm(&owner.mcu_ipcq, 5) == -ESHUTDOWN && mod_calls == 0 && owner.mcu_ipcq.to_arm_refused_after_dispatch, "probe closed refusal");
    /* 3-4: native mod_timer pending-state 0 and 1 are both success. */
    begin_case(true); check(n143_timer_arm(&owner.mcu_ipcq, 5) == 0 && mod_calls == 1 && owner.mcu_ipcq.to_timer.expires == 105, "first arm native expiry");
    begin_case(true); (void)n143_timer_arm(&owner.mcu_ipcq, 5); check(n143_timer_arm(&owner.mcu_ipcq, 8) == 0 && mod_calls == 2 && owner.mcu_ipcq.to_timer.expires == 108, "pending rearm not mistaken for errno");
    /* 5: arm-before-close canceled before native queue destruction. */
    begin_case(true); (void)n143_timer_arm(&owner.mcu_ipcq, 5); iva_ipcq_deinit(&owner.mcu_ipcq);
    check(owner.mcu_ipcq.to_closed && !owner.mcu_ipcq.to_timer.pending && !owner.mcu_ipcq.cmd_q && !owner.mcu_ipcq.res_q && responses.flags == ~IPC_QUEUE_ACTIVE_FLAG, "deinit drains then clears native pointers");
    /* 6-7: running native callback progresses; producer cannot rearm. */
    begin_case(true); owner.mcu_ipcq.to_timer.running = 1; iva_ipcq_deinit(&owner.mcu_ipcq);
    check(response_calls == 1 && !owner.mcu_ipcq.to_timer.running, "authentic timeout/error/response chain completes before drain returns");
    begin_case(true); owner.mcu_ipcq.to_timer.running = 1; rearm_during_sync = 1; iva_ipcq_deinit(&owner.mcu_ipcq);
    check(late_arm_result == -ESHUTDOWN && mod_calls == 0 && response_calls == 1 && owner.mcu_ipcq.to_arm_refused_after_dispatch, "close wins rearm while callback runs");
    /* 8-10: safe closed native invalid/repeated queue lifecycle. */
    begin_case(false); iva_ipcq_deinit(&owner.mcu_ipcq); iva_ipcq_deinit(&owner.mcu_ipcq);
    check(owner.mcu_ipcq.to_closed && !owner.mcu_ipcq.to_lifecycle_lock.held, "null/repeated deinit closed and balanced");
    begin_case(true); ret = iva_ipcq_init(&owner.mcu_ipcq, NULL, &responses);
    check(ret == -EINVAL && owner.mcu_ipcq.to_closed && !owner.mcu_ipcq.to_lifecycle_lock.held, "invalid cmd init never reopens");
    begin_case(true); ret = iva_ipcq_init(&owner.mcu_ipcq, &commands, NULL);
    check(ret == -EINVAL && owner.mcu_ipcq.to_closed && !owner.mcu_ipcq.to_lifecycle_lock.held, "invalid response init never reopens");
    /* 11-12: original native remove sequence only after timer closure. */
    begin_case(true); (void)n143_timer_arm(&owner.mcu_ipcq, 5); iva_ipcq_remove(&owner);
    check(strcmp(cleanup, "DCIF") == 0 && frees == 1 && owner.mcu_ipcq.to_removing && !iva_ipcq_cb.priv_data, "pending timer drained before original remove order");
    begin_case(true); owner.mcu_ipcq.to_timer.running = 1; iva_ipcq_remove(&owner);
    check(response_calls == 1 && strcmp(cleanup, "DCIF") == 0 && frees == 1, "running callback completes before original native free");
    /* 13-15: sticky removal on still-live native IPC object. */
    begin_case(true); iva_ipcq_remove(&owner); before = mod_calls;
    check(n143_timer_arm(&owner.mcu_ipcq, 5) == -ESHUTDOWN && mod_calls == before, "no arm after remove");
    begin_case(true); iva_ipcq_remove(&owner); ret = iva_ipcq_init(&owner.mcu_ipcq, &commands, &responses);
    check(ret == -ESHUTDOWN && owner.mcu_ipcq.to_closed && owner.mcu_ipcq.to_removing && frees == 1, "native init cannot reopen removing lifetime");
    begin_case(true); iva_ipcq_remove(&owner); iva_ipcq_remove(&owner);
    check(strcmp(cleanup, "DCIF") == 0 && frees == 1, "invalid repeated remove cannot repeat original cleanup");
    /* 16: a native command really dispatched before arm refusal. */
    begin_case(true); request.header = ipc_func_sched_table; request.ipc_cmd_type = IPC_CMD_FRAME_START; request.param_0 = 9;
    close_during_send = 1; ret = iva_ipcq_send_cmd_usr(&process, &request);
    check(ret == -ESHUTDOWN && sent == 1 && mod_calls == 0 && owner.mcu_ipcq.to_arm_refused_after_dispatch, "already sent reported honestly, no retry/undo/new hardware cleanup");
    /* 17-19: preserved native producer paths. */
    begin_case(true); request.param_0 = 0; ret = iva_ipcq_send_cmd_usr(&process, &request);
    check(ret == 0 && sent == 1 && mod_calls == 0, "zero means existing no-timeout behavior");
    begin_case(true); request.param_0 = 9; send_error = -EIO; ret = iva_ipcq_send_cmd_usr(&process, &request);
    check(ret == -EIO && sent == 1 && mod_calls == 0 && !owner.mcu_ipcq.to_arm_refused_after_dispatch, "existing send errno before timer arm");
    begin_case(true); ret = iva_ipcq_send_cmd_usr(&process, NULL);
    check(ret == -EINVAL && sent == 0 && mod_calls == 0, "native invalid user argument unchanged");
    /* 20: an init queued while closing executes only after pointer clearing. */
    begin_case(true); queue_init_during_sync = 1; iva_ipcq_deinit(&owner.mcu_ipcq);
    check(queued_init_result == 0 && !owner.mcu_ipcq.to_closed && owner.mcu_ipcq.cmd_q == &commands && owner.mcu_ipcq.res_q == &responses && !owner.mcu_ipcq.to_lifecycle_lock.held, "actual init reopens only after serialized drain");
    /* 21-23: real producer success, lifetime history, removed deinit guard. */
    begin_case(true); request.header = ipc_func_sched_table; request.ipc_cmd_type = IPC_CMD_FRAME_START; request.param_0 = 9;
    ret = iva_ipcq_send_cmd_usr(&process, &request);
    check(ret == 0 && sent == 1 && mod_calls == 1 && owner.mcu_ipcq.to_in_ms == 9 && owner.mcu_ipcq.to_timer.expires == 109, "actual native producer arms once with original interval");
    begin_case(true); iva_ipcq_deinit(&owner.mcu_ipcq); (void)n143_timer_arm(&owner.mcu_ipcq, 9);
    ret = iva_ipcq_init(&owner.mcu_ipcq, &commands, &responses);
    check(ret == 0 && owner.mcu_ipcq.to_arm_refused_after_dispatch && !owner.mcu_ipcq.to_closed, "successful native reinit never clears unsafe arm-refusal history");
    begin_case(true); iva_ipcq_remove(&owner); owner.mcu_ipcq.res_q = (struct ipc_res_queue *)(uintptr_t)1;
    iva_ipcq_deinit(&owner.mcu_ipcq);
    check(owner.mcu_ipcq.res_q == (struct ipc_res_queue *)(uintptr_t)1 && owner.mcu_ipcq.to_closed && !owner.mcu_ipcq.to_lifecycle_lock.held, "removed deinit never touches native response pointer");
    if (failures) return 1;
    printf("{\"passed\":true,\"cases\":%u}\n", cases); return 0;
}
'''


def ordinary(path):
    path = Path(path)
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise ValueError('absolute ordinary input required')
    return path.resolve()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('output', 'cc', 'native-root'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    out = args.output
    native_root = args.native_root
    if (not out.is_absolute() or out.resolve() != out or out.exists() or out.is_symlink() or
            not out.is_relative_to(ROOT / 'note10/private') or
            not native_root.is_absolute() or native_root.resolve() != native_root or
            native_root.is_symlink() or not native_root.is_dir() or
            out.is_relative_to(native_root) or native_root.is_relative_to(out)):
        parser.error('fresh separate canonical private output/native input root required')
    cc = ordinary(args.cc)
    stock = {name: ordinary(native_root / name).read_bytes() for name in NATIVE_SHA256}
    helper = ordinary(HERE / 'v143_iva_timer.inc').read_bytes()
    changed = patch_native(stock, helper)
    mcu = ordinary(native_root / MCU).read_bytes()
    if hashlib.sha256(mcu).hexdigest() != MCU_SHA256:
        raise ValueError('exact actual timeout dependency required')
    structs = [selected_block(changed[HEADER], rb'^struct ' + name + rb'\s*(?=\{)') + b';'
               for name in (b'iva_ipcq_stat', b'iva_ipcq')]
    callback = function(changed[IPC], 'iva_ipcq_no_rsp_timer')
    probe = function(changed[IPC], 'iva_ipcq_probe')
    # Host Windows is LLP64; these two pointer-transport ABI tokens become
    # uintptr_t. The authentic native function bodies and production API remain
    # otherwise unchanged; later actual AArch64 object compile covers real ABI.
    if callback.count(b'unsigned long data') != 1 or probe.count(b'(unsigned long)ipcq') != 1:
        raise ValueError('exact native timer ABI bridge required')
    callback = callback.replace(b'unsigned long data', b'uintptr_t data', 1)
    probe = probe.replace(b'(unsigned long)ipcq', b'(uintptr_t)ipcq', 1)
    bodies = [function(changed[IPC], 'iva_ipcq_send_rsp_k'),
              function(mcu, 'iva_mcu_handle_error_k'), callback,
              function(changed[IPC], 'iva_ipcq_init_param_regions'),
              function(changed[IPC], 'iva_ipcq_init'),
              function(changed[IPC], 'iva_ipcq_deinit'), probe,
              function(changed[IPC], 'iva_ipcq_remove'),
              function(changed[IPC], 'iva_ipcq_send_cmd_usr')]
    fixture = (TYPES.encode() + b'\n' + b'\n'.join(structs) + b'\n' + DEPENDENCIES.encode() +
               b'\n#include "v143_iva_timer.inc"\n' + b'\n'.join(bodies) + b'\n' + CASES.encode())
    out.mkdir(parents=True)
    result = dict(schema='note10-v143-native-timer-result-v1', passed=False,
                  scope='PC-only-native-IPC-timer-lifetime', NEW_transform_invocations=1,
                  compiler_invocations=0, fixture_processes=0, old_tests_replayed=0,
                  retained_render_invocations=0, kernel_CI=0, device_operations=[],
                  physical_ready=False, owner_success_emitted=False,
                  NEW_source_sha256={
                      'note10/device_test/v143_iva_timer.py': hashlib.sha256(ordinary(HERE / 'v143_iva_timer.py').read_bytes()).hexdigest(),
                      'note10/device_test/v143_iva_timer.inc': HELPER_SHA256,
                      'note10/device_test/test_v143_iva_timer.py': hashlib.sha256(ordinary(Path(__file__).resolve()).read_bytes()).hexdigest()},
                  native_input_sha256=NATIVE_SHA256, native_callback_dependency_sha256=MCU_SHA256,
                  host_pointer_ABI_bridges=2,
                  changed_native_sha256={name: hashlib.sha256(raw).hexdigest() for name, raw in changed.items()})
    def persist():
        (out / 'result.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())
    persist()
    for name, raw in changed.items():
        target = out / 'native-output' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    fixture_path = out / 'new-native-iva-timer.c'
    fixture_path.write_bytes(fixture)
    (out / 'v143_iva_timer.inc').write_bytes(helper)
    include = out / 'include/linux'
    include.mkdir(parents=True)
    for name in ('errno.h', 'mutex.h', 'spinlock.h', 'timer.h'):
        (include / name).write_bytes(b'/* fixture declarations supplied before authentic helper */\n')
    result['fixture_sha256'] = hashlib.sha256(fixture).hexdigest()
    executable = out / ('new-native-iva-timer.exe' if sys.platform == 'win32' else 'new-native-iva-timer')
    command = [str(cc), '-std=gnu89', '-O2', '-Wall', '-Wextra', '-Werror',
               '-Wstrict-prototypes', '-Wdeclaration-after-statement', '-Wno-unused-function',
               '-I', str(out / 'include'), str(fixture_path), '-o', str(executable)]
    result.update(compiler_invocations=1, compiler_argv=command)
    persist()
    with (out / 'compile.log').open('xb') as log:
        subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=60)
    result['fixture_processes'] = 1
    persist()
    with (out / 'fixture.log').open('xb') as log:
        done = subprocess.run([str(executable)], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
        log.write(done.stdout)
    done.check_returncode()
    receipt = json.loads(done.stdout)
    if receipt != {'passed': True, 'cases': 23}:
        raise ValueError('exact native timer fixture result required')
    result.update(passed=True, fixture_result=receipt)
    persist()
    print(json.dumps({'passed': True, 'cases': 23, 'physical_ready': False}))


if __name__ == '__main__':
    main()
