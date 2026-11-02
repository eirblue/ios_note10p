/* SPDX-License-Identifier: GPL-2.0-only */
/* Thin synthetic Linux API boundary; production wrapper/core included below. */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <openssl/sha.h>
#include "carrier_lzma.c"
#define N10_DATA_HOST_TEST
#define N10_DATA_IMAGE_EXPECTATION 1
#define __used __attribute__((used))
#define READ_ONCE(x) (*(volatile __typeof__(x) *)&(x))
#define __init
static unsigned long initrd_start, initrd_end, host_first, host_last;
static unsigned int allocations, frees, cleared = 1, fail_alloc, hashes, fail_hash, core_calls;
static void *allocated[2];
static size_t lengths[2];
#define n10_data_linear(x) ((x) >= host_first && (x) < host_last)
#define n10_data_pa(x) ((uint64_t)(x))
#define n10_data_va(x) ((unsigned long)(x))
#define n10_data_clear(p,n) memset((p),0,(n))
static void *fixture_alloc(size_t bytes)
{
    void *p;
    ++allocations;
    if (allocations == fail_alloc) return NULL;
    p = malloc(bytes);
    if (p) { allocated[allocations-1] = p; lengths[allocations-1] = bytes; }
    return p;
}
static void fixture_free(void *p)
{
    unsigned int i;
    size_t j;
    for (i = 0; i < 2; ++i) if (allocated[i] == p) {
        for (j = 0; j < lengths[i]; ++j) if (((unsigned char *)p)[j]) cleared = 0;
        ++frees; free(p); return;
    }
    abort();
}
#define n10_data_alloc(n) fixture_alloc(n)
#define n10_data_free(p) fixture_free(p)
static int n10_data_hash(const void *input, size_t bytes, unsigned char digest[32])
{
    if (++hashes == fail_hash) return -1;
    return SHA256(input,bytes,digest) ? 0 : -1;
}
static int fixture_decode(const uint8_t *input, size_t bytes, uint8_t *output, size_t capacity,
    void *workspace, size_t workspace_bytes, struct n10_lzma_result *result)
{
    ++core_calls;
    return n10_lzma_alone_decode(input,bytes,output,capacity,workspace,workspace_bytes,result);
}
#define n10_lzma_alone_decode fixture_decode
#include "linux_data_carrier.c"
#undef n10_lzma_alone_decode

/* The unchanged worker establishes real arm/admission/callback order. */
struct work_struct { int unused; };
struct delayed_work { struct work_struct work; };
struct workqueue_struct { int unused; };
typedef struct { int counter; } atomic_t;
#define ATOMIC_INIT(n) {n}
static atomic_t n10_return_requested = ATOMIC_INIT(0);
static unsigned long jiffies;
static unsigned int system_state, armed, callbacks, arm_fail;
static struct workqueue_struct queue;
static struct n10_data_outcome outcome;
#define SYSTEM_RUNNING 1u
#define WQ_UNBOUND 1u
#define WQ_MEM_RECLAIM 2u
#define DECLARE_DELAYED_WORK(name, fn) struct delayed_work name = {{0}}
#define late_initcall(fn)
#define pr_info(...) ((void)0)
static int atomic_read(atomic_t *a) { return a->counter; }
static int atomic_cmpxchg(atomic_t *a,int old,int value)
{ int before = a->counter; if (before == old) a->counter = value; return before; }
static unsigned long msecs_to_jiffies(unsigned int x) { return x; }
static int time_after_eq(unsigned long a,unsigned long b) { return (long)(a-b) >= 0; }
static int n10_arm_auto_return(void) { if (arm_fail) return 1; armed = 1; return 0; }
static struct workqueue_struct *alloc_workqueue(const char *name,unsigned int flags,int max)
{ (void)name; (void)flags; (void)max; return &queue; }
static int queue_delayed_work(struct workqueue_struct *q,struct delayed_work *w,unsigned long delay)
{ (void)q; (void)w; (void)delay; return 1; }
static void destroy_workqueue(struct workqueue_struct *q) { (void)q; }
static int fixture_emit(void)
{
    if (!armed || system_state != SYSTEM_RUNNING) abort();
    ++callbacks; n10_data_run(&outcome); return 0;
}
#define n10_sha256_kat_init fixture_emit
#include "sha256_kat_recovery_work.c"
#undef n10_sha256_kat_init

int main(int argc,char **argv)
{
    FILE *file;
    long size;
    unsigned char *data;
    const char *mode;
    char digest[65];
    unsigned int i;
    if (argc != 3) return 2;
    file = fopen(argv[1],"rb"); if (!file) return 2;
    if (fseek(file,0,SEEK_END) || (size=ftell(file)) <= 128 || size > (long)N10_LZMA_MAX_BYTES || fseek(file,0,SEEK_SET)) return 2;
    data = malloc((size_t)size); if (!data || fread(data,1,(size_t)size,file) != (size_t)size) return 2;
    fclose(file); mode = argv[2];
    initrd_start = host_first = (unsigned long)data;
    initrd_end = host_last = initrd_start+(unsigned long)size;
    if (!strcmp(mode,"reversed")) n10_data_capture(initrd_end,initrd_start);
    else if (!strcmp(mode,"nonlinear")) n10_data_capture(initrd_start-1,initrd_end);
    else if (strcmp(mode,"missing_capture")) n10_data_capture(initrd_start,initrd_end);
    if (!strcmp(mode,"repeat_capture")) n10_data_capture(initrd_start,initrd_end);
    if (!strcmp(mode,"changed")) --initrd_end;
    if (!strcmp(mode,"alloc1")) fail_alloc=1;
    if (!strcmp(mode,"alloc2")) fail_alloc=2;
    if (!strcmp(mode,"hash1")) fail_hash=1;
    if (!strcmp(mode,"hash2")) fail_hash=2;
    if (!strcmp(mode,"hash3")) fail_hash=3;
    n10_sha256_worker(NULL); /* Before arm: deadline refuses callback. */
    if (callbacks || core_calls || allocations || hashes) abort();
    arm_fail = !strcmp(mode,"arm_fail");
    (void)n10_sha256_recovery_init();
    n10_sha256_worker(NULL); /* Booting: actual worker requeues only. */
    if (callbacks || core_calls || allocations || hashes) abort();
    system_state = SYSTEM_RUNNING;
    if (strcmp(mode,"unarmed")) n10_sha256_worker(NULL);
    if (!strcmp(mode,"repeat_callback") || !strcmp(mode,"repeat_refused_callback")) n10_sha256_worker(NULL);
    for (i=0;i<32;++i) sprintf(digest+2*i,"%02x",outcome.digest[i]);
    digest[64]=0;
    printf("{\"status\":\"%s\",\"source\":\"image-slot-v1\",\"calls\":%u,\"callbacks\":%u,\"allocations\":%u,\"frees\":%u,\"cleared\":%u,\"written\":%llu,\"consumed\":%llu,\"digest\":\"%s\",\"reasons\":\"%08x\",\"expectations\":%u,\"captures\":%u,\"retained\":%u,\"hashes\":%u,\"carrier\":%llu,\"stream\":%llu,\"payload\":%llu}\n",
        outcome.status ? outcome.status : "skipped",core_calls,callbacks,allocations,frees,cleared,
        (unsigned long long)outcome.written,(unsigned long long)outcome.consumed,digest,
        outcome.reasons,outcome.expectations,outcome.captures,outcome.retained,hashes,
        (unsigned long long)outcome.carrier,(unsigned long long)outcome.stream,(unsigned long long)outcome.payload);
    free(data); return 0;
}
