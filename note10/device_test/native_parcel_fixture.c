/* SPDX-License-Identifier: GPL-2.0-only */
/* Synthetic metadata only; callback success never attests hardware ownership. */
#include "native_parcel_core.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned int assertions, actions;
#define CHECK(ok) do { ++assertions; if (!(ok)) { fprintf(stderr,"assertion line%d\n",__LINE__); exit(1); } } while (0)
struct model { struct n209_destination expected; int return_blocked; };
static int source_live(void *context, const struct n209_payload *p)
{ (void)context; return p->kernel_span == 3*N209_PAGE ? 0 : -1; }
static int current(void *context, const struct n209_destination *d)
{ return memcmp(d,&((struct model *)context)->expected,sizeof(*d)) ? -1 : 0; }
static int qualified(void *context)
{ return ((struct model *)context)->return_blocked ? -1 : 0; }
static int exercise(const struct n209_payload *p, const struct n209_destination *d, n209_u64 adt,
                    const struct n209_prerequisites *ops, struct model *model, struct n209_layout *layout)
{
    int result=n209_prepare_layout(p,d,adt,ops,model,layout);
    if (!result) ++actions; /* Pure fixture counter, not a kexec/load operation. */
    return result;
}
static void reject(const struct n209_payload *p, const struct n209_destination *d, n209_u64 adt,
                   const struct n209_prerequisites *ops, struct model *model)
{
    unsigned int before=actions; struct n209_layout layout;
    CHECK(exercise(p,d,adt,ops,model,&layout) != 0);
    CHECK(actions == before);
}
int main(int argc, char **argv)
{
    n209_u8 wire[N209_PAYLOAD_BYTES]; FILE *input;
    struct n209_payload p, changed;
    struct n209_destination d={0}, stale;
    struct n209_prerequisites ops={source_live,current,qualified}, missing;
    struct n209_layout layout;
    struct model model;
    CHECK(argc == 2);
    input=fopen(argv[1],"rb"); CHECK(input != NULL);
    CHECK(fread(wire,1,sizeof(wire),input) == sizeof(wire)); CHECK(fgetc(input) == EOF); fclose(input);
    CHECK(n209_decode_payload(wire,sizeof(wire),&p) == 0);
    d.base=N209_ADDRESS_MIN+(p.virtual_base%N209_DESTINATION_BYTES); d.size=N209_DESTINATION_BYTES;
    d.generation=1; d.page_shift=12; d.status=1;
    memset(d.build,'1',sizeof(d.build)); memset(d.cookie,1,sizeof(d.cookie));
    model.expected=d; model.return_blocked=0;
    CHECK(exercise(&p,&d,128,&ops,&model,&layout) == 0);
    CHECK(layout.args_offset == p.kernel_span && layout.adt_offset == p.kernel_span+N209_PAGE &&
          layout.adapter_offset == p.kernel_span+2*N209_PAGE && layout.top_offset == p.kernel_span+3*N209_PAGE);
    changed=p; changed.kernel_span=N209_DESTINATION_BYTES+N209_PAGE; reject(&changed,&d,128,&ops,&model);
    changed=p; changed.kernel_entry_offset=p.kernel_span; reject(&changed,&d,128,&ops,&model);
    reject(&p,&d,N209_ADT_MAX+1,&ops,&model);
    changed=p; changed.kernel_span=N209_DESTINATION_BYTES; reject(&changed,&d,128,&ops,&model);
    changed=p; changed.kernel_span=N209_DESTINATION_BYTES-2*N209_PAGE; reject(&changed,&d,128,&ops,&model);
    stale=d; stale.generation=2; reject(&p,&stale,128,&ops,&model);
    stale=d; memset(stale.build,'2',sizeof(stale.build)); reject(&p,&stale,128,&ops,&model);
    stale=d; stale.cookie[0]^=1; reject(&p,&stale,128,&ops,&model);
    missing=ops; missing.source_live=NULL; reject(&p,&d,128,&missing,&model);
    missing=ops; missing.return_qualified=NULL; reject(&p,&d,128,&missing,&model);
    model.return_blocked=1; reject(&p,&d,128,&ops,&model);
    CHECK(actions == 1);
    printf("{\"groups\":[1,4,5,6,7,8],\"variants\":12,\"assertions\":%u,\"model_action_callbacks\":%u,"
           "\"physical_ready\":false,\"physical_reservation_verified\":false,\"device_authorized\":false}\n",assertions,actions);
    return 0;
}
