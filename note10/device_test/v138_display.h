/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NOTE10_V138_DISPLAY_H
#define NOTE10_V138_DISPLAY_H
#include <linux/types.h>
#include <linux/errno.h>
#include <linux/v136_terminal.h>
struct device;
struct device_driver;
struct task_struct;
struct decon_device;
struct dpp_config;
struct v4l2_subdev;
struct decon_mode_info;
#define N138_DPU_DOMAINS (1U<<3)
#define N138_DPU_NATIVE_STOP_FROZEN 6U
#define N138_DPU_DOMAIN_OFF_FROZEN 7U
enum n138_family { N138_DECON=0, N138_DPP=1, N138_DP=2, N138_DSIM=3,
                   N138_HDR_ACCESS=4, N138_DP_PHY_ACCESS=5, N138_DECON_SHARED_ACCESS=6 };
enum n138_lifetime { N138_ABSENT=0, N138_PROBING=1, N138_RESOURCES=2,
                     N138_BOUND=3, N138_INVALID=4 };
struct n138_slot {
    struct device *dev;
    void *object;
    void *subdev;
    struct task_struct *probe_task;
    struct device_driver *bound_driver;
    void *borrower;
    unsigned int family, id, lifetime, generation, frozen_generation;
    int native_irq;
    bool probe_completed;
    bool locked, device_locked, pm_owned, stopped;
};
/* Returned only by the selected native translation units; never registered
 * dynamically by arbitrary masters. No driver-name admission. */
struct n138_native_ops {
    const char *compatible, *alias;
    unsigned int family, count;
    struct device_driver *driver;
    int (*validate)(struct n138_slot *, struct n136_detail *);
    int (*lock)(struct n138_slot *, struct n136_detail *);
    void (*unlock)(struct n138_slot *);
    int (*quiet)(struct n138_slot *, struct n136_detail *);
    int (*stop)(struct n138_slot *, struct n136_detail *);
};
struct n138_config_guard {
    struct n138_slot *owner,*channel;
    bool owner_core,channel_core,admitted;
};
bool n138_user_begin(void);
void n138_user_end(void);
bool n138_access_begin(unsigned int family, unsigned int id);
bool n138_dpp_write_begin(unsigned int id, u32 reg);
bool n138_dpp_transaction_begin(unsigned int id);
void n138_dpp_transaction_end(unsigned int id);
bool n138_secure_begin(void);
void n138_invalid(void);
#define N138_INVALIDATE_BEFORE(expression) (n138_invalid(),(expression))
int n138_probe(unsigned int family, unsigned int id, struct device *, void *, void *);
int n138_resources(unsigned int family, unsigned int id, void *);
int n138_ready(unsigned int family, unsigned int id, void *);
void n138_probe_result(struct device *, bool);
void n138_detach(struct device *);
bool n138_borrow(unsigned int id, void *decon);
int n138_config_begin(void *, void *, struct n138_config_guard *);
void n138_config_end(struct n138_config_guard *);
void n138_unowned_config(void);
int n138_owned_config(struct decon_device *, struct v4l2_subdev *,
                      const struct dpp_config *);
bool n138_proving(void);
bool n138_budget(void);
int n138_checkpoint(void);
int n138_poll_failure(const char *, unsigned int, u32, int);
int n138_refuse_access(const char *, unsigned int, u32);
void n138_resolved_failure(void);
bool n138_dp_accessible(void);
bool n138_native_dp_link_ready(void *);
bool n138_native_dsim_link_ready(void *);
int n138_shared_te_begin(void);
void n138_shared_te_end(void);
int n138_display_prepare(void);
int n138_display_final(void);
int n138_display_unwind(void);
bool n138_lease_matches(unsigned int, void *);
int n138_native_decon_stop(unsigned int, struct decon_mode_info *, unsigned int);
int n138_native_dpp_stop(unsigned int, unsigned long);
const struct n138_native_ops *n138_decon_native(void);
const struct n138_native_ops *n138_dpp_native(void);
const struct n138_native_ops *n138_dp_native(void);
const struct n138_native_ops *n138_dsim_native(void);
#endif
