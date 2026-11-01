/* One host compile, actual production component included below. No hardware API. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "exynos_early_clock_fixture.h"

struct fixture_property { char name[32]; const unsigned char *value; unsigned size; };
struct fixture_node {
    struct fixture_property props[8]; unsigned count;
    struct fixture_node *children[34]; unsigned children_count;
};
static struct fixture_node cpus, first, second;
static jmp_buf failure;
static unsigned panic_count, lookup_count;
static int missing_cpus, iterator_error, property_error;
static unsigned char frequency[8], other_frequency[8];
clock_frequency_info_t gPEClockFrequencyInfo;

void panic(const char *reason, ...) { (void)reason; panic_count++; longjmp(failure, 1); }
int SecureDTLookupEntry(DTEntry parent, const char *path, DTEntry *result)
{
    (void)parent; lookup_count++;
    if (strcmp(path, "/cpus") || missing_cpus) return kError;
    *result = &cpus; return kSuccess;
}
int SecureDTInitEntryIterator(DTEntry node, OpaqueDTEntryIterator *iter)
{ iter->node = node; iter->index = 0; return iterator_error == 1 ? kError : kSuccess; }
int SecureDTIterateEntries(OpaqueDTEntryIterator *iter, DTEntry *result)
{
    if (iterator_error == 2) return kError;
    if (iter->index >= iter->node->children_count) return kIterationDone;
    *result = iter->node->children[iter->index++]; return kSuccess;
}
int SecureDTInitPropertyIterator(DTEntry node, OpaqueDTPropertyIterator *iter)
{ iter->node = node; iter->index = 0; return property_error == 1 ? kError : kSuccess; }
int SecureDTIterateProperties(OpaqueDTPropertyIterator *iter, const char **result)
{
    if (property_error == 2) return kError;
    if (iter->index >= iter->node->count) return kIterationDone;
    *result = iter->node->props[iter->index++].name; return kSuccess;
}
int SecureDTGetProperty(DTEntry node, const char *name, const void **value, unsigned *size)
{
    for (unsigned i = 0; i < node->count; i++) if (!strcmp(node->props[i].name, name)) {
        *value = node->props[i].value; *size = node->props[i].size; return kSuccess;
    }
    return kError;
}

#define ARM64_BOARD_CONFIG_EXYNOS9825 1
#include "exynos_early_clock.c"

static void property(struct fixture_node *node, const char *name, const void *value, unsigned size)
{
    struct fixture_property *p = &node->props[node->count++];
    if (node->count > 8) abort();
    strcpy(p->name, name); p->value = value; p->size = size;
}
static void number(unsigned char *p, uint32_t value)
{ for (unsigned i = 0; i < 4; i++) p[i] = (unsigned char)(value >> (8 * i)); }
static void reset(uint32_t hz)
{
    memset(&cpus, 0, sizeof(cpus)); memset(&first, 0, sizeof(first)); memset(&second, 0, sizeof(second));
    memset(&gPEClockFrequencyInfo, 0xa5, sizeof(gPEClockFrequencyInfo));
    memset(frequency, 0, sizeof(frequency)); number(frequency, hz);
    panic_count = lookup_count = 0; missing_cpus = iterator_error = property_error = 0;
    property(&cpus, "name", "cpus", 5);
    property(&first, "name", "cpu@synthetic", 14);
    property(&first, "device_type", "cpu", 4);
    property(&first, "state", "running", 8);
    property(&first, "timebase-frequency", frequency, 4);
    cpus.children[cpus.children_count++] = &first;
}
static int invoke(int valid, uint32_t expected)
{
    clock_frequency_info_t before = gPEClockFrequencyInfo;
    if (setjmp(failure)) {
        return !valid && panic_count == 1 && !memcmp(&before, &gPEClockFrequencyInfo, sizeof(before));
    }
    pe_note10_early_clock_init();
    if (!valid || panic_count || lookup_count != 1) return 0;
    clock_frequency_info_t wanted = {0};
    wanted.timebase_frequency_hz = wanted.dec_clock_rate_hz = expected;
    return !memcmp(&wanted, &gPEClockFrequencyInfo, sizeof(wanted));
}
static int valid_cases(void)
{
    const uint32_t cases[] = {1000000U, 16909060U, 2147483647U};
    for (unsigned i = 0; i < sizeof(cases) / sizeof(cases[0]); i++) {
        reset(cases[i]); if (!invoke(1, cases[i])) return 0;
    }
    reset(16909060U);
    property(&second, "name", "unknown-state", 14); property(&second, "device_type", "cpu", 4);
    property(&second, "timebase-frequency", other_frequency, 8); /* Unselected semantics ignored. */
    cpus.children[cpus.children_count++] = &second;
    return invoke(1, 16909060U);
}
static int selector_cases(void)
{
    reset(16909060U); missing_cpus = 1; if (!invoke(0, 0)) return 0;
    reset(16909060U); iterator_error = 1; if (!invoke(0, 0)) return 0;
    reset(16909060U); iterator_error = 2; if (!invoke(0, 0)) return 0;
    reset(16909060U); property_error = 1; if (!invoke(0, 0)) return 0;
    reset(16909060U); property_error = 2; if (!invoke(0, 0)) return 0;
    reset(16909060U); first.props[2].value = (const unsigned char *)"run"; first.props[2].size = 4;
    if (!invoke(0, 0)) return 0;
    reset(16909060U); first.props[2].size = 7; if (!invoke(0, 0)) return 0;
    reset(16909060U); first.props[2].value = (const unsigned char *)"running\0x"; first.props[2].size = 10;
    if (!invoke(0, 0)) return 0;
    reset(16909060U); first.props[2] = first.props[3]; first.count = 3;
    if (!invoke(0, 0)) return 0;
    reset(16909060U); second = first; second.props[0].value = (const unsigned char *)"cpu@second";
    second.props[0].size = 11; cpus.children[cpus.children_count++] = &second;
    if (!invoke(0, 0)) return 0;
    reset(16909060U);
    struct fixture_node unknown[32];
    char names[32][16];
    memset(unknown, 0, sizeof(unknown));
    for (unsigned i = 0; i < 32; i++) {
        snprintf(names[i], sizeof(names[i]), "cpu@other%u", i);
        property(&unknown[i], "name", names[i], (unsigned)strlen(names[i]) + 1);
        property(&unknown[i], "device_type", "cpu", 4);
        cpus.children[cpus.children_count++] = &unknown[i];
    }
    return invoke(0, 0);
}
static int property_cases(void)
{
    const uint32_t bad[] = {0U, 999999U, 2147483648U};
    for (unsigned i = 0; i < sizeof(bad) / sizeof(bad[0]); i++) {
        reset(bad[i]); if (!invoke(0, 0)) return 0;
    }
    for (unsigned size = 0; size <= 8; size++) if (size != 4) {
        reset(16909060U); first.props[3].size = size; if (!invoke(0, 0)) return 0;
    }
    for (unsigned duplicate = 0; duplicate < 4; duplicate++) {
        reset(16909060U);
        struct fixture_property p = first.props[duplicate];
        property(&first, p.name, p.value, p.size); if (!invoke(0, 0)) return 0;
    }
    reset(16909060U); first.count = 3; if (!invoke(0, 0)) return 0;
    reset(16909060U); memset(first.props[0].name, 'x', 32);
    return invoke(0, 0);
}
int main(int argc, char **argv)
{
    if (argc != 2) return 2;
    int ok = !strcmp(argv[1], "valid") ? valid_cases() :
             !strcmp(argv[1], "selector") ? selector_cases() :
             !strcmp(argv[1], "properties") ? property_cases() : 0;
    printf("{\"passed\":%s,\"synthetic\":true,\"hardware_operations\":0}\n", ok ? "true" : "false");
    return ok ? 0 : 1;
}
