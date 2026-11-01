/* Thin host fixture API. Production uses the real XNU header declarations. */
#include <stdint.h>
#include <stddef.h>
#include <setjmp.h>

typedef struct fixture_node *DTEntry;
typedef struct { DTEntry node; unsigned index; } OpaqueDTEntryIterator;
typedef struct { DTEntry node; unsigned index; } OpaqueDTPropertyIterator;
enum { kError = -1, kIterationDone = 0, kSuccess = 1 };

typedef struct clock_frequency_info_t {
    unsigned long bus_clock_rate_hz, cpu_clock_rate_hz, dec_clock_rate_hz;
    unsigned long bus_clock_rate_num, bus_clock_rate_den;
    unsigned long bus_to_cpu_rate_num, bus_to_cpu_rate_den;
    unsigned long bus_to_dec_rate_num, bus_to_dec_rate_den;
    unsigned long timebase_frequency_hz, timebase_frequency_num, timebase_frequency_den;
    unsigned long long bus_frequency_hz, bus_frequency_min_hz, bus_frequency_max_hz;
    unsigned long long cpu_frequency_hz, cpu_frequency_min_hz, cpu_frequency_max_hz;
    unsigned long long prf_frequency_hz, prf_frequency_min_hz, prf_frequency_max_hz;
    unsigned long long mem_frequency_hz, mem_frequency_min_hz, mem_frequency_max_hz;
    unsigned long long fix_frequency_hz;
} clock_frequency_info_t;

extern clock_frequency_info_t gPEClockFrequencyInfo;
void panic(const char *, ...) __attribute__((noreturn));
int SecureDTLookupEntry(DTEntry, const char *, DTEntry *);
int SecureDTInitEntryIterator(DTEntry, OpaqueDTEntryIterator *);
int SecureDTIterateEntries(OpaqueDTEntryIterator *, DTEntry *);
int SecureDTInitPropertyIterator(DTEntry, OpaqueDTPropertyIterator *);
int SecureDTIterateProperties(OpaqueDTPropertyIterator *, const char **);
int SecureDTGetProperty(DTEntry, const char *, const void **, unsigned *);
