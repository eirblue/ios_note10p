"""Exact native IVA IPC timer closure overlay; no retained renderer or runtime."""
from hashlib import sha256

HEADER = 'drivers/vision/iva/iva_ctrl.h'
IPC = 'drivers/vision/iva/iva_ipc_queue.c'
HELPER = 'drivers/vision/iva/v143_iva_timer.inc'
HELPER_SHA256 = '730e2ab31cada507b7dd380d0a928aae502829b70b86a471d5b4010f626fb24d'
NATIVE_SHA256 = {
    HEADER: '89fdd85645f1844a05551f225c9fbf1063762df0ea09f6d04d9cfbe546513f56',
    IPC: 'fd33bd4717e1028514f83c3378b44855f796f1475e38c0834cadeb9a4f6b06c5',
}
_HEADER_OLD = b'\tstruct timer_list\tto_timer;\t\t/* timeout */\n\tunsigned int\t\tto_in_ms;'
_HEADER_NEW = _HEADER_OLD + b'''
\t/* Selected native timeout lifetime; not a DMA/file ownership gate. */
\tstruct mutex\t\tto_lifecycle_lock;
\tspinlock_t\t\tto_state_lock;
\tbool\t\t\tto_closed;
\tbool\t\t\tto_removing;
\tbool\t\t\tto_arm_refused_after_dispatch;'''
_ARM_OLD = b'''\t\t\t\tipcq->to_in_ms = tmp_param.param_0;
\t\t\t\tdev_dbg(dev, "%s() time out(%d ms) req on FS\\n",
\t\t\t\t\t__func__, ipcq->to_in_ms);
\t\t\t\tret = mod_timer(&ipcq->to_timer,
\t\t\t\t\tjiffies + msecs_to_jiffies(ipcq->to_in_ms));
\t\t\t\tif (ret < 0) {
\t\t\t\t\tdev_err(dev,
\t\t\t\t\t\t"%s() fail to set to timer(%d ms), ret(%d)\\n",
\t\t\t\t\t\t__func__, ipcq->to_in_ms, ret);
\t\t\t\t}'''
_ARM_NEW = b'''\t\t\t\tret = n143_timer_arm(ipcq, tmp_param.param_0);
\t\t\t\tif (ret < 0) {
\t\t\t\t\tdev_err(dev, "%s() command sent; timeout admission refused(%d)\\n",
\t\t\t\t\t\t__func__, ret);
\t\t\t\t\treturn ret;
\t\t\t\t}'''
_INIT_OLD = b'''int iva_ipcq_init(struct iva_ipcq *ipcq, struct ipc_cmd_queue *cmd_q,
\t\t\tstruct ipc_res_queue *rsp_q)
{
\tstruct iva_dev_data\t*iva = ipcq->iva_data;
#ifdef CHECK_PARAM_REGION_ALIGN
\tint ret;
#endif
\t/* clear slot & req id */'''
_INIT_NEW = _INIT_OLD.replace(b'\t/* clear slot & req id */', b'''\tint n143_result;
\tmutex_lock(&ipcq->to_lifecycle_lock);
\tn143_timer_close_locked(ipcq, false);
\tif (n143_timer_removing_locked(ipcq)) {
\t\tn143_result = -ESHUTDOWN;
\t\tgoto n143_out;
\t}
\tif (!cmd_q || !rsp_q) {
\t\tn143_result = -EINVAL;
\t\tgoto n143_out;
\t}
\t/* clear slot & req id */''')
_INIT_ERROR_OLD = b'''\t\tdev_err(iva->dev, "%s() fail to init ipc queue, ret(%d)\\n",
\t\t\t\t__func__, ret);
\t\treturn ret;'''
_INIT_ERROR_NEW = _INIT_ERROR_OLD.replace(b'\t\treturn ret;', b'\t\tn143_result = ret;\n\t\tgoto n143_out;')
_INIT_TAIL_OLD = b'''\tdev_dbg(iva->dev, "%s() success !!!\\n", __func__);
\treturn 0;
}

void iva_ipcq_deinit'''
_INIT_TAIL_NEW = b'''\tdev_dbg(iva->dev, "%s() success !!!\\n", __func__);
\tn143_result = n143_timer_open_locked(ipcq);
n143_out:
\tmutex_unlock(&ipcq->to_lifecycle_lock);
\treturn n143_result;
}

void iva_ipcq_deinit'''
_DEINIT_OLD = b'''void iva_ipcq_deinit(struct iva_ipcq *ipcq)
{
\tstruct iva_dev_data\t*iva = ipcq->iva_data;
\tstruct ipc_res_queue\t*ap_rsp_q = ipcq->res_q;

\tap_rsp_q->flags = ~IPC_QUEUE_ACTIVE_FLAG;

\tipcq->cmd_q\t= NULL;
\tipcq->res_q\t= NULL;

\tdev_dbg(iva->dev, "%s() success !!!\\n", __func__);
}'''
_DEINIT_NEW = b'''void iva_ipcq_deinit(struct iva_ipcq *ipcq)
{
\tstruct iva_dev_data\t*iva = ipcq->iva_data;
\tstruct ipc_res_queue\t*ap_rsp_q;
\tmutex_lock(&ipcq->to_lifecycle_lock);
\tn143_timer_close_locked(ipcq, false);
\tif (n143_timer_removing_locked(ipcq))
\t\tgoto n143_out;
\tap_rsp_q = ipcq->res_q;
\tif (ap_rsp_q)
\t\tap_rsp_q->flags = ~IPC_QUEUE_ACTIVE_FLAG;

\tipcq->cmd_q\t= NULL;
\tipcq->res_q\t= NULL;

\tdev_dbg(iva->dev, "%s() success !!!\\n", __func__);
n143_out:
\tmutex_unlock(&ipcq->to_lifecycle_lock);
}'''
_PROBE_OLD = b'\tsetup_timer(&ipcq->to_timer, iva_ipcq_no_rsp_timer, (unsigned long)ipcq);'
_PROBE_NEW = b'\tn143_timer_probe(ipcq);\n' + _PROBE_OLD
_REMOVE_OLD = b'''void iva_ipcq_remove(struct iva_dev_data *iva)
{
\tstruct iva_ipcq *ipcq = &iva->mcu_ipcq;

\tdev_dbg(iva->dev, "%s()\\n", __func__);'''
_REMOVE_NEW = _REMOVE_OLD.replace(b'\tdev_dbg', b'''\tmutex_lock(&ipcq->to_lifecycle_lock);
\tif (n143_timer_removing_locked(ipcq))
\t\tgoto n143_out;
\tn143_timer_close_locked(ipcq, true);
\tdev_dbg''')
_REMOVE_TAIL_OLD = b'\tdevm_kfree(iva->dev, ipcq->rsv);\n}'
_REMOVE_TAIL_NEW = b'\tdevm_kfree(iva->dev, ipcq->rsv);\nn143_out:\n\tmutex_unlock(&ipcq->to_lifecycle_lock);\n}'


def _once(raw, before, after):
    if raw.count(before) != 1:
        raise ValueError('exact selected native timer boundary required')
    return raw.replace(before, after, 1)


def patch_native(stock, helper):
    """Transform exact two native inputs and supplied reviewed helper bytes."""
    if type(stock) is not dict or set(stock) != set(NATIVE_SHA256):
        raise ValueError('exact native IPC/header roles required')
    if (type(helper) is not bytes or b'\r' in helper or
            sha256(helper).hexdigest() != HELPER_SHA256):
        raise ValueError('ordinary LF kernel helper bytes required')
    for name, pin in NATIVE_SHA256.items():
        if type(stock[name]) is not bytes or sha256(stock[name]).hexdigest() != pin:
            raise ValueError('exact pinned native source required: ' + name)
    header = _once(stock[HEADER], _HEADER_OLD, _HEADER_NEW)
    ipc = stock[IPC]
    for before, after in (
            (b'#undef DEBUG', b'#include "v143_iva_timer.inc"\n\n#undef DEBUG'),
            (_ARM_OLD, _ARM_NEW), (_INIT_OLD, _INIT_NEW),
            (_INIT_ERROR_OLD, _INIT_ERROR_NEW), (_INIT_TAIL_OLD, _INIT_TAIL_NEW),
            (_DEINIT_OLD, _DEINIT_NEW), (_PROBE_OLD, _PROBE_NEW),
            (_REMOVE_OLD, _REMOVE_NEW), (_REMOVE_TAIL_OLD, _REMOVE_TAIL_NEW)):
        ipc = _once(ipc, before, after)
    return {HEADER: header, IPC: ipc, HELPER: helper}
