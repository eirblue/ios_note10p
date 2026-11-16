/* SPDX-License-Identifier: GPL-2.0-only */
#include "v278_current_owner_seal.h"
#ifdef __KERNEL__
#include <linux/string.h>
#else
#include <string.h>
#endif
int n278_seal_once(struct n278_seal *seal,const struct n210_request *request,
    const struct n210_destination *destination,const struct n210_context *context,
    const n209_u8 *descriptor_hash,const struct n210_receipt *prepared,
    unsigned int prepare_spent,const struct n217_state *ingest)
{
    struct n278_values candidate={0};struct n209_payload payload;
    const struct n217_result *result;unsigned int role,i;
    n209_u64 sizes[2];const n209_u8 *hashes[2];
    if(!seal)return -22;
    if(seal->phase!=N278_EMPTY)return -114;
    seal->phase=N278_REFUSED;
    if(!request||!destination||!context||!descriptor_hash||!prepared||!ingest||
       prepare_spent!=1||ingest->spent!=1||context->return_armed!=1||
       context->page_reserved!=1||context->pid1!=1||context->cap_sys_boot!=1||
       n210_request_valid(request,destination,context,descriptor_hash)||
       n210_receipt_matches(prepared,context,request)||
       n209_decode_payload(request->payload,sizeof(request->payload),&payload)||
       n209_layout_bounds(&payload,&destination->region,N209_ADT_MAX,&candidate.layout))return -22;
    result=&ingest->result;
    /* No standalone217 result validator exists: this is the new value join,
     * not another ingestion or spent/quarantine lifecycle. */
    if(memcmp(result->magic,"N217RCP1",8)||result->schema!=1||result->bytes!=352||
       result->status!=1||result->error_code||result->flags!=7||result->reserved||
       result->generation!=destination->region.generation||
       memcmp(result->build,context->build,32)||memcmp(result->boot,context->boot,32)||
       memcmp(result->cycle,context->cycle,32)||memcmp(result->cookie,destination->region.cookie,16)||
       result->files_held!=2||result->destination_content_verified!=1||result->quarantined||
       result->source_pages_physically_pinned!=0||result->staging_request_bytes!=N217_CHUNK)return -22;
    for(i=0;i<sizeof(result->tail);i++)if(result->tail[i])return -22;
    sizes[0]=payload.kernel_span;sizes[1]=payload.adapter_bytes;
    hashes[0]=payload.materialized_sha256;hashes[1]=payload.adapter_sha256;
    for(role=0;role<2;role++)if(result->source_bytes[role]!=sizes[role]||
       result->copied_bytes[role]!=sizes[role]||memcmp(result->source_sha256[role],hashes[role],32)||
       memcmp(result->destination_sha256[role],hashes[role],32))return -22;
    if(result->source_data_bytes!=sizes[0]+sizes[1])return -22;
    /* Existing209 bounds prove the full adapter page is inside this region. */
    candidate.adapter_entry=destination->region.base+candidate.layout.adapter_offset+payload.adapter_entry_offset;
    candidate.request=*request;candidate.context=*context;
    candidate.prepared=*prepared;candidate.ingested=*result;
    seal->values=candidate;seal->phase=N278_VALUES_ONLY;return 0;
}
