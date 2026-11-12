/*
 * Cryptographic API.
 *
 * SHA-256, as specified in
 * http://csrc.nist.gov/groups/STM/cavp/documents/shs/sha256-384-512.pdf
 *
 * SHA-256 code by Jean-Luc Cooke <jlcooke@certainkey.com>.
 *
 * Copyright (c) Jean-Luc Cooke <jlcooke@certainkey.com>
 * Copyright (c) Andrew McDonald <andrew@mcdonald.org.uk>
 * Copyright (c) 2002 James Morris <jmorris@intercode.com.au>
 * SHA224 Support Copyright 2007 Intel Corporation <jonathan.lynch@intel.com>
 *
 * This program is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the Free
 * Software Foundation; either version 2 of the License, or (at your option) 
 * any later version.
 *
 */
/* Fixed raw-state interface derived from the pinned generic implementation.
 * No tfm/provider allocation or feature dispatcher. */
#include "native_source_sha256.h"
#ifdef __KERNEL__
#include <linux/string.h>
#else
#include <string.h>
#endif
static void n219_wipe(void *raw,unsigned int bytes)
{ volatile n209_u8 *p=raw;while(bytes--)*p++=0; }
static n209_u32 n219_load32(const n209_u8 *p)
{ return ((n209_u32)p[0]<<24)|((n209_u32)p[1]<<16)|((n209_u32)p[2]<<8)|p[3]; }
static n209_u32 n219_ror32(n209_u32 x,unsigned int n)
{ return (x>>n)|(x<<(32-n)); }
static inline n209_u32 n219_Ch(n209_u32 x, n209_u32 y, n209_u32 z)
{
	return z ^ (x & (y ^ z));
}

static inline n209_u32 n219_Maj(n209_u32 x, n209_u32 y, n209_u32 z)
{
	return (x & y) | (z & (x | y));
}

#define n219_e0(x)       (n219_ror32(x, 2) ^ n219_ror32(x,13) ^ n219_ror32(x,22))
#define n219_e1(x)       (n219_ror32(x, 6) ^ n219_ror32(x,11) ^ n219_ror32(x,25))
#define n219_s0(x)       (n219_ror32(x, 7) ^ n219_ror32(x,18) ^ (x >> 3))
#define n219_s1(x)       (n219_ror32(x,17) ^ n219_ror32(x,19) ^ (x >> 10))

static inline void n219_LOAD_OP(int I, n209_u32 *W, const n209_u8 *input)
{
	W[I] = n219_load32(input + 4 * I);
}

static inline void n219_BLEND_OP(int I, n209_u32 *W)
{
	W[I] = n219_s1(W[I-2]) + W[I-7] + n219_s0(W[I-15]) + W[I-16];
}

static __attribute__((noinline)) void n219_sha256_transform(n209_u32 *state, const n209_u8 *input)
{
	n209_u32 a, b, c, d, e, f, g, h, t1, t2;
	n209_u32 W[64];
	int i;

	/* load the input */
	for (i = 0; i < 16; i++)
		n219_LOAD_OP(i, W, input);

	/* now blend */
	for (i = 16; i < 64; i++)
		n219_BLEND_OP(i, W);

	/* load the state into our registers */
	a=state[0];  b=state[1];  c=state[2];  d=state[3];
	e=state[4];  f=state[5];  g=state[6];  h=state[7];

	/* now iterate */
	t1 = h + n219_e1(e) + n219_Ch(e,f,g) + 0x428a2f98 + W[ 0];
	t2 = n219_e0(a) + n219_Maj(a,b,c);    d+=t1;    h=t1+t2;
	t1 = g + n219_e1(d) + n219_Ch(d,e,f) + 0x71374491 + W[ 1];
	t2 = n219_e0(h) + n219_Maj(h,a,b);    c+=t1;    g=t1+t2;
	t1 = f + n219_e1(c) + n219_Ch(c,d,e) + 0xb5c0fbcf + W[ 2];
	t2 = n219_e0(g) + n219_Maj(g,h,a);    b+=t1;    f=t1+t2;
	t1 = e + n219_e1(b) + n219_Ch(b,c,d) + 0xe9b5dba5 + W[ 3];
	t2 = n219_e0(f) + n219_Maj(f,g,h);    a+=t1;    e=t1+t2;
	t1 = d + n219_e1(a) + n219_Ch(a,b,c) + 0x3956c25b + W[ 4];
	t2 = n219_e0(e) + n219_Maj(e,f,g);    h+=t1;    d=t1+t2;
	t1 = c + n219_e1(h) + n219_Ch(h,a,b) + 0x59f111f1 + W[ 5];
	t2 = n219_e0(d) + n219_Maj(d,e,f);    g+=t1;    c=t1+t2;
	t1 = b + n219_e1(g) + n219_Ch(g,h,a) + 0x923f82a4 + W[ 6];
	t2 = n219_e0(c) + n219_Maj(c,d,e);    f+=t1;    b=t1+t2;
	t1 = a + n219_e1(f) + n219_Ch(f,g,h) + 0xab1c5ed5 + W[ 7];
	t2 = n219_e0(b) + n219_Maj(b,c,d);    e+=t1;    a=t1+t2;

	t1 = h + n219_e1(e) + n219_Ch(e,f,g) + 0xd807aa98 + W[ 8];
	t2 = n219_e0(a) + n219_Maj(a,b,c);    d+=t1;    h=t1+t2;
	t1 = g + n219_e1(d) + n219_Ch(d,e,f) + 0x12835b01 + W[ 9];
	t2 = n219_e0(h) + n219_Maj(h,a,b);    c+=t1;    g=t1+t2;
	t1 = f + n219_e1(c) + n219_Ch(c,d,e) + 0x243185be + W[10];
	t2 = n219_e0(g) + n219_Maj(g,h,a);    b+=t1;    f=t1+t2;
	t1 = e + n219_e1(b) + n219_Ch(b,c,d) + 0x550c7dc3 + W[11];
	t2 = n219_e0(f) + n219_Maj(f,g,h);    a+=t1;    e=t1+t2;
	t1 = d + n219_e1(a) + n219_Ch(a,b,c) + 0x72be5d74 + W[12];
	t2 = n219_e0(e) + n219_Maj(e,f,g);    h+=t1;    d=t1+t2;
	t1 = c + n219_e1(h) + n219_Ch(h,a,b) + 0x80deb1fe + W[13];
	t2 = n219_e0(d) + n219_Maj(d,e,f);    g+=t1;    c=t1+t2;
	t1 = b + n219_e1(g) + n219_Ch(g,h,a) + 0x9bdc06a7 + W[14];
	t2 = n219_e0(c) + n219_Maj(c,d,e);    f+=t1;    b=t1+t2;
	t1 = a + n219_e1(f) + n219_Ch(f,g,h) + 0xc19bf174 + W[15];
	t2 = n219_e0(b) + n219_Maj(b,c,d);    e+=t1;    a=t1+t2;

	t1 = h + n219_e1(e) + n219_Ch(e,f,g) + 0xe49b69c1 + W[16];
	t2 = n219_e0(a) + n219_Maj(a,b,c);    d+=t1;    h=t1+t2;
	t1 = g + n219_e1(d) + n219_Ch(d,e,f) + 0xefbe4786 + W[17];
	t2 = n219_e0(h) + n219_Maj(h,a,b);    c+=t1;    g=t1+t2;
	t1 = f + n219_e1(c) + n219_Ch(c,d,e) + 0x0fc19dc6 + W[18];
	t2 = n219_e0(g) + n219_Maj(g,h,a);    b+=t1;    f=t1+t2;
	t1 = e + n219_e1(b) + n219_Ch(b,c,d) + 0x240ca1cc + W[19];
	t2 = n219_e0(f) + n219_Maj(f,g,h);    a+=t1;    e=t1+t2;
	t1 = d + n219_e1(a) + n219_Ch(a,b,c) + 0x2de92c6f + W[20];
	t2 = n219_e0(e) + n219_Maj(e,f,g);    h+=t1;    d=t1+t2;
	t1 = c + n219_e1(h) + n219_Ch(h,a,b) + 0x4a7484aa + W[21];
	t2 = n219_e0(d) + n219_Maj(d,e,f);    g+=t1;    c=t1+t2;
	t1 = b + n219_e1(g) + n219_Ch(g,h,a) + 0x5cb0a9dc + W[22];
	t2 = n219_e0(c) + n219_Maj(c,d,e);    f+=t1;    b=t1+t2;
	t1 = a + n219_e1(f) + n219_Ch(f,g,h) + 0x76f988da + W[23];
	t2 = n219_e0(b) + n219_Maj(b,c,d);    e+=t1;    a=t1+t2;

	t1 = h + n219_e1(e) + n219_Ch(e,f,g) + 0x983e5152 + W[24];
	t2 = n219_e0(a) + n219_Maj(a,b,c);    d+=t1;    h=t1+t2;
	t1 = g + n219_e1(d) + n219_Ch(d,e,f) + 0xa831c66d + W[25];
	t2 = n219_e0(h) + n219_Maj(h,a,b);    c+=t1;    g=t1+t2;
	t1 = f + n219_e1(c) + n219_Ch(c,d,e) + 0xb00327c8 + W[26];
	t2 = n219_e0(g) + n219_Maj(g,h,a);    b+=t1;    f=t1+t2;
	t1 = e + n219_e1(b) + n219_Ch(b,c,d) + 0xbf597fc7 + W[27];
	t2 = n219_e0(f) + n219_Maj(f,g,h);    a+=t1;    e=t1+t2;
	t1 = d + n219_e1(a) + n219_Ch(a,b,c) + 0xc6e00bf3 + W[28];
	t2 = n219_e0(e) + n219_Maj(e,f,g);    h+=t1;    d=t1+t2;
	t1 = c + n219_e1(h) + n219_Ch(h,a,b) + 0xd5a79147 + W[29];
	t2 = n219_e0(d) + n219_Maj(d,e,f);    g+=t1;    c=t1+t2;
	t1 = b + n219_e1(g) + n219_Ch(g,h,a) + 0x06ca6351 + W[30];
	t2 = n219_e0(c) + n219_Maj(c,d,e);    f+=t1;    b=t1+t2;
	t1 = a + n219_e1(f) + n219_Ch(f,g,h) + 0x14292967 + W[31];
	t2 = n219_e0(b) + n219_Maj(b,c,d);    e+=t1;    a=t1+t2;

	t1 = h + n219_e1(e) + n219_Ch(e,f,g) + 0x27b70a85 + W[32];
	t2 = n219_e0(a) + n219_Maj(a,b,c);    d+=t1;    h=t1+t2;
	t1 = g + n219_e1(d) + n219_Ch(d,e,f) + 0x2e1b2138 + W[33];
	t2 = n219_e0(h) + n219_Maj(h,a,b);    c+=t1;    g=t1+t2;
	t1 = f + n219_e1(c) + n219_Ch(c,d,e) + 0x4d2c6dfc + W[34];
	t2 = n219_e0(g) + n219_Maj(g,h,a);    b+=t1;    f=t1+t2;
	t1 = e + n219_e1(b) + n219_Ch(b,c,d) + 0x53380d13 + W[35];
	t2 = n219_e0(f) + n219_Maj(f,g,h);    a+=t1;    e=t1+t2;
	t1 = d + n219_e1(a) + n219_Ch(a,b,c) + 0x650a7354 + W[36];
	t2 = n219_e0(e) + n219_Maj(e,f,g);    h+=t1;    d=t1+t2;
	t1 = c + n219_e1(h) + n219_Ch(h,a,b) + 0x766a0abb + W[37];
	t2 = n219_e0(d) + n219_Maj(d,e,f);    g+=t1;    c=t1+t2;
	t1 = b + n219_e1(g) + n219_Ch(g,h,a) + 0x81c2c92e + W[38];
	t2 = n219_e0(c) + n219_Maj(c,d,e);    f+=t1;    b=t1+t2;
	t1 = a + n219_e1(f) + n219_Ch(f,g,h) + 0x92722c85 + W[39];
	t2 = n219_e0(b) + n219_Maj(b,c,d);    e+=t1;    a=t1+t2;

	t1 = h + n219_e1(e) + n219_Ch(e,f,g) + 0xa2bfe8a1 + W[40];
	t2 = n219_e0(a) + n219_Maj(a,b,c);    d+=t1;    h=t1+t2;
	t1 = g + n219_e1(d) + n219_Ch(d,e,f) + 0xa81a664b + W[41];
	t2 = n219_e0(h) + n219_Maj(h,a,b);    c+=t1;    g=t1+t2;
	t1 = f + n219_e1(c) + n219_Ch(c,d,e) + 0xc24b8b70 + W[42];
	t2 = n219_e0(g) + n219_Maj(g,h,a);    b+=t1;    f=t1+t2;
	t1 = e + n219_e1(b) + n219_Ch(b,c,d) + 0xc76c51a3 + W[43];
	t2 = n219_e0(f) + n219_Maj(f,g,h);    a+=t1;    e=t1+t2;
	t1 = d + n219_e1(a) + n219_Ch(a,b,c) + 0xd192e819 + W[44];
	t2 = n219_e0(e) + n219_Maj(e,f,g);    h+=t1;    d=t1+t2;
	t1 = c + n219_e1(h) + n219_Ch(h,a,b) + 0xd6990624 + W[45];
	t2 = n219_e0(d) + n219_Maj(d,e,f);    g+=t1;    c=t1+t2;
	t1 = b + n219_e1(g) + n219_Ch(g,h,a) + 0xf40e3585 + W[46];
	t2 = n219_e0(c) + n219_Maj(c,d,e);    f+=t1;    b=t1+t2;
	t1 = a + n219_e1(f) + n219_Ch(f,g,h) + 0x106aa070 + W[47];
	t2 = n219_e0(b) + n219_Maj(b,c,d);    e+=t1;    a=t1+t2;

	t1 = h + n219_e1(e) + n219_Ch(e,f,g) + 0x19a4c116 + W[48];
	t2 = n219_e0(a) + n219_Maj(a,b,c);    d+=t1;    h=t1+t2;
	t1 = g + n219_e1(d) + n219_Ch(d,e,f) + 0x1e376c08 + W[49];
	t2 = n219_e0(h) + n219_Maj(h,a,b);    c+=t1;    g=t1+t2;
	t1 = f + n219_e1(c) + n219_Ch(c,d,e) + 0x2748774c + W[50];
	t2 = n219_e0(g) + n219_Maj(g,h,a);    b+=t1;    f=t1+t2;
	t1 = e + n219_e1(b) + n219_Ch(b,c,d) + 0x34b0bcb5 + W[51];
	t2 = n219_e0(f) + n219_Maj(f,g,h);    a+=t1;    e=t1+t2;
	t1 = d + n219_e1(a) + n219_Ch(a,b,c) + 0x391c0cb3 + W[52];
	t2 = n219_e0(e) + n219_Maj(e,f,g);    h+=t1;    d=t1+t2;
	t1 = c + n219_e1(h) + n219_Ch(h,a,b) + 0x4ed8aa4a + W[53];
	t2 = n219_e0(d) + n219_Maj(d,e,f);    g+=t1;    c=t1+t2;
	t1 = b + n219_e1(g) + n219_Ch(g,h,a) + 0x5b9cca4f + W[54];
	t2 = n219_e0(c) + n219_Maj(c,d,e);    f+=t1;    b=t1+t2;
	t1 = a + n219_e1(f) + n219_Ch(f,g,h) + 0x682e6ff3 + W[55];
	t2 = n219_e0(b) + n219_Maj(b,c,d);    e+=t1;    a=t1+t2;

	t1 = h + n219_e1(e) + n219_Ch(e,f,g) + 0x748f82ee + W[56];
	t2 = n219_e0(a) + n219_Maj(a,b,c);    d+=t1;    h=t1+t2;
	t1 = g + n219_e1(d) + n219_Ch(d,e,f) + 0x78a5636f + W[57];
	t2 = n219_e0(h) + n219_Maj(h,a,b);    c+=t1;    g=t1+t2;
	t1 = f + n219_e1(c) + n219_Ch(c,d,e) + 0x84c87814 + W[58];
	t2 = n219_e0(g) + n219_Maj(g,h,a);    b+=t1;    f=t1+t2;
	t1 = e + n219_e1(b) + n219_Ch(b,c,d) + 0x8cc70208 + W[59];
	t2 = n219_e0(f) + n219_Maj(f,g,h);    a+=t1;    e=t1+t2;
	t1 = d + n219_e1(a) + n219_Ch(a,b,c) + 0x90befffa + W[60];
	t2 = n219_e0(e) + n219_Maj(e,f,g);    h+=t1;    d=t1+t2;
	t1 = c + n219_e1(h) + n219_Ch(h,a,b) + 0xa4506ceb + W[61];
	t2 = n219_e0(d) + n219_Maj(d,e,f);    g+=t1;    c=t1+t2;
	t1 = b + n219_e1(g) + n219_Ch(g,h,a) + 0xbef9a3f7 + W[62];
	t2 = n219_e0(c) + n219_Maj(c,d,e);    f+=t1;    b=t1+t2;
	t1 = a + n219_e1(f) + n219_Ch(f,g,h) + 0xc67178f2 + W[63];
	t2 = n219_e0(b) + n219_Maj(b,c,d);    e+=t1;    a=t1+t2;

	state[0] += a; state[1] += b; state[2] += c; state[3] += d;
	state[4] += e; state[5] += f; state[6] += g; state[7] += h;

	/* clear any sensitive info... */
	a = b = c = d = e = f = g = h = t1 = t2 = 0;
	n219_wipe(W, 64 * sizeof(n209_u32));
}


void __attribute__((noinline)) n219_sha256_init(struct n219_sha256 *s)
{
    static const n209_u32 initial[8]={0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
    memset(s,0,sizeof(*s));memcpy(s->state,initial,sizeof(initial));
}
int __attribute__((noinline)) n219_sha256_update(struct n219_sha256 *s,const void *raw,unsigned int bytes)
{
    const n209_u8 *p=raw;unsigned int partial,take;
    const n209_u64 limit=((~(n209_u64)0)>>3);
    if(!s||s->finalized||(!raw&&bytes)||s->count>limit||(n209_u64)bytes>limit-s->count)return -1;
    partial=(unsigned int)(s->count&63);s->count+=bytes;
    if(partial){take=64-partial;if(take>bytes)take=bytes;
        if(take){memcpy(s->buf+partial,p,take);p+=take;}bytes-=take;partial+=take;
        if(partial==64)n219_sha256_transform(s->state,s->buf);
        else return 0;}
    while(bytes>=64){n219_sha256_transform(s->state,p);p+=64;bytes-=64;}
    if(bytes)memcpy(s->buf,p,bytes);return 0;
}
int __attribute__((noinline)) n219_sha256_final(struct n219_sha256 *s,n209_u8 out[32])
{
    unsigned int partial,i;n209_u64 bits;
    if(!s||!out||s->finalized||s->count>((~(n209_u64)0)>>3))return -1;
    bits=s->count<<3;partial=(unsigned int)(s->count&63);s->buf[partial++]=0x80;
    if(partial>56){memset(s->buf+partial,0,64-partial);n219_sha256_transform(s->state,s->buf);partial=0;}
    memset(s->buf+partial,0,56-partial);
    for(i=0;i<8;i++)s->buf[63-i]=(n209_u8)(bits>>(8*i));
    n219_sha256_transform(s->state,s->buf);
    for(i=0;i<32;i++)out[i]=(n209_u8)(s->state[i/4]>>(24-8*(i%4)));
    n219_wipe(s,sizeof(*s));s->finalized=1;return 0;
}
