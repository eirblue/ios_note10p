/* SPDX-License-Identifier: GPL-2.0-only */
/* Portable pixel renderer. Caller owns memory and serializes access. */
#ifndef N10_SCREEN_LOG_CORE_H
#define N10_SCREEN_LOG_CORE_H
#define N10_SCREEN_MAGIC 0x4e313053U
#define N10_SCREEN_LINES 64
#define N10_SCREEN_COLUMNS 96
struct n10_screen_text {
    unsigned int count;
    char line[N10_SCREEN_LINES][N10_SCREEN_COLUMNS];
};
/* Compact repeated machine records into a readable terminal line. */
static inline void n10_screen_line(char *out, const char *in)
{
    unsigned int n = 0, i, pass, length;
    const char *p, *start;
    for (p = in; *p && *p != ' ' && n < N10_SCREEN_COLUMNS - 1; ++p)
        out[n++] = *p;
    for (pass = 0; pass < 2; ++pass) {
        p = in;
        while (*p && *p != ' ') ++p;
        while (*p) {
            int priority, skip;
            while (*p == ' ') ++p;
            start = p;
            while (*p && *p != ' ') ++p;
            length = (unsigned int)(p - start);
            if (!length) break;
            priority = (length >= 6 && start[0]=='e' && start[1]=='r' && start[2]=='r' && start[3]=='o' && start[4]=='r' && start[5]=='=') ||
                       (length >= 7 && start[0]=='s' && start[1]=='t' && start[2]=='a' && start[3]=='t' && start[4]=='u' && start[5]=='s' && start[6]=='=');
            skip = (length >= 3 && start[0]=='i' && start[1]=='d' && start[2]=='=') ||
                   (length >= 4 && start[0]=='s' && start[1]=='e' && start[2]=='q' && start[3]=='=') ||
                   (length >= 6 && start[0]=='c' && start[1]=='y' && start[2]=='c' && start[3]=='l' && start[4]=='e' && start[5]=='=') ||
                   (length >= 9 && start[0]=='c' && start[1]=='h' && start[2]=='e' && start[3]=='c' && start[4]=='k' && start[5]=='s' && start[6]=='u' && start[7]=='m' && start[8]=='=');
            if (skip || priority != (pass == 0)) continue;
            if (n < N10_SCREEN_COLUMNS - 1) out[n++] = ' ';
            for (i = 0; i < length && n < N10_SCREEN_COLUMNS - 1; ++i)
                out[n++] = start[i];
        }
    }
    out[n] = 0;
}
static inline int n10_screen_geometry(unsigned int width, unsigned int height,
                               unsigned int align_w, unsigned int align_h,
                               unsigned int *w, unsigned int *h)
{
    if (!align_w || !align_h || width > 8192 || height > 8192)
        return -1;
    *w = width / 2 / align_w * align_w;
    *h = height / 2 / align_h * align_h;
    if (*w < 160 || *h < 96 || !*w || !*h)
        return -1;
    return 0;
}
static inline int n10_screen_render(unsigned int *pixels, unsigned long capacity,
                            unsigned int width, unsigned int height,
                            unsigned int stride, const unsigned char *font,
                            const struct n10_screen_text *text)
{
    unsigned int x, y, row, col, bit, gy, scale = 2;
    unsigned int rows, cols, start, total = 0, entry, length, offset, logical = 0;
    if (!pixels || !font || !text || width < 16 || height < 32 ||
        width > 4096 || height > 4096 || stride < width || stride > 8192 ||
        (unsigned long)stride * height > capacity || text->count > N10_SCREEN_LINES)
        return -1;
    for (y = 0; y < height; ++y)
        for (x = 0; x < width; ++x)
            pixels[(unsigned long)y * stride + x] = 0xff080808U;
    rows = height / (16 * scale);
    cols = width / (8 * scale);
    if (cols > N10_SCREEN_COLUMNS) cols = N10_SCREEN_COLUMNS;
    for (entry = 0; entry < text->count; ++entry) {
        length = 0;
        while (length < N10_SCREEN_COLUMNS && text->line[entry][length]) ++length;
        total += length ? (length + cols - 1) / cols : 1;
    }
    start = total > rows ? total - rows : 0;
    for (entry = 0; entry < text->count; ++entry) {
        length = 0;
        while (length < N10_SCREEN_COLUMNS && text->line[entry][length]) ++length;
        for (offset = 0; offset < (length ? length : 1); offset += cols, ++logical) {
            if (logical < start) continue;
            row = logical - start;
            for (col = 0; col < cols && offset + col < length; ++col) {
                unsigned char ch = text->line[entry][offset + col];
                if (ch < 32 || ch > 126) ch = '?';
                for (gy = 0; gy < 16; ++gy)
                    for (bit = 0; bit < 8; ++bit)
                        if (font[(ch - 32) * 16 + gy] & (0x80U >> bit))
                            for (y = 0; y < scale; ++y)
                                for (x = 0; x < scale; ++x)
                                    pixels[(unsigned long)(row * 32 + gy * 2 + y) * stride +
                                           col * 16 + bit * 2 + x] = 0xffd8f0d8U;
            }
        }
    }
    return 0;
}
#endif
