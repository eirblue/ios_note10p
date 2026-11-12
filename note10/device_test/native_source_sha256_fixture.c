/* SPDX-License-Identifier: GPL-2.0-only */
#include <windows.h>
#include <bcrypt.h>
#include <stdio.h>
#include <string.h>
#include "native_source_sha256.h"
static unsigned int assertions;
static int expect(int ok){assertions++;if(!ok){fprintf(stderr,"assertion %u failed\n",assertions);return 0;}return 1;}
static int oracle(BCRYPT_ALG_HANDLE alg,const n209_u8 *data,unsigned int bytes,n209_u8 out[32])
{
    BCRYPT_HASH_HANDLE hash=NULL;DWORD size=0,got=0;PUCHAR object=NULL;int ok=0;
    if(BCryptGetProperty(alg,BCRYPT_OBJECT_LENGTH,(PUCHAR)&size,sizeof(size),&got,0)<0||got!=sizeof(size)||!size||size>1048576)return 0;
    object=HeapAlloc(GetProcessHeap(),HEAP_ZERO_MEMORY,size);if(!object)return 0;
    if(BCryptCreateHash(alg,&hash,object,size,NULL,0,0)>=0&&BCryptHashData(hash,(PUCHAR)data,bytes,0)>=0&&BCryptFinishHash(hash,out,32,0)>=0)ok=1;
    if(hash)BCryptDestroyHash(hash);SecureZeroMemory(object,size);HeapFree(GetProcessHeap(),0,object);return ok;
}
static int vector(BCRYPT_ALG_HANDLE alg,const n209_u8 *raw,unsigned int bytes,unsigned int stride,const char *known)
{
    struct n219_sha256 state;n209_u8 actual[32],expected[32];unsigned int at=0,i;char hex[65];int updates=1;
    n219_sha256_init(&state);
    while(at<bytes){unsigned int take=bytes-at;if(take>stride)take=stride;updates&=n219_sha256_update(&state,raw+at,take)==0;at+=take;}
    if(!expect(updates&&n219_sha256_final(&state,actual)==0))return 0;
    if(!expect(oracle(alg,raw,bytes,expected)&&!memcmp(actual,expected,32)))return 0;
    if(known){for(i=0;i<32;i++)sprintf(hex+2*i,"%02x",actual[i]);if(!expect(!strcmp(hex,known)))return 0;}
    return 1;
}
int main(void)
{
    BCRYPT_ALG_HANDLE alg=NULL;n209_u8 pattern[4096],digest[32];struct n219_sha256 s;unsigned int i;int clean=1;
    if(BCryptOpenAlgorithmProvider(&alg,BCRYPT_SHA256_ALGORITHM,NULL,0)<0)return 2;
    for(i=0;i<sizeof(pattern);i++)pattern[i]=(n209_u8)(i*37+11);
    /* group1: empty and abc; group2: padding55/56; group3: block64/65. */
    if(!vector(alg,pattern,0,1,"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")||
       !vector(alg,(const n209_u8 *)"abc",3,1,"ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")||
       !vector(alg,pattern,55,7,NULL)||!vector(alg,pattern,56,9,NULL)||
       !vector(alg,pattern,64,1,NULL)||!vector(alg,pattern,65,13,NULL))return 3;
    /* group4: pattern oracle; reset, overflow refusal and final material wipe. */
    if(!vector(alg,pattern,sizeof(pattern),127,NULL))return 4;
    n219_sha256_init(&s);s.count=((~(n209_u64)0)>>3);
    if(!expect(n219_sha256_update(&s,pattern,1)!=0&&s.count==((~(n209_u64)0)>>3)))return 5;
    n219_sha256_init(&s);
    if(!expect(n219_sha256_update(&s,"abc",3)==0&&n219_sha256_final(&s,digest)==0))return 6;
    for(i=0;i<sizeof(s.state);i++)if(((n209_u8 *)s.state)[i])clean=0;
    for(i=0;i<sizeof(s.buf);i++)if(s.buf[i])clean=0;
    if(!expect(clean&&s.count==0&&s.finalized==1&&n219_sha256_update(&s,pattern,1)!=0&&n219_sha256_final(&s,digest)!=0))return 7;
    BCryptCloseAlgorithmProvider(alg,0);
    printf("{\"schema\":\"note10-v219-direct-sha-fixture-v1\",\"passed\":true,\"groups\":4,\"variants\":8,\"assertions\":%u}\n",assertions);return 0;
}
