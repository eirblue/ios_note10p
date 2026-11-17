/* SPDX-License-Identifier: GPL-2.0-only */
/* Instantaneous cooperative admission only; no future deadline or ownership. */
int n210_linux_context(struct n210_context *out)
{
    memset(out,0,sizeof(*out));
    memcpy(out->build,N154_BUILD_ID,32);
    memcpy(out->boot,n10_boot_id,32);
    memcpy(out->cycle,(const void *)n10_cycle,32);
    out->return_armed=READ_ONCE(n154_arm_result)==0&&
        atomic_read(&n10_return_started)==1&&!atomic_read(&n10_return_requested)&&
        READ_ONCE(system_state)==SYSTEM_RUNNING&&delayed_work_pending(&n10_return_work);
    return out->return_armed?0:-EAGAIN;
}
