/*
 * Built-in AppleMobileFileIntegrity trust-cache query for Note10 (EXYNOS9825).
 *
 * The AMFI kext is absent; the kernel answers cdhash lookups itself from the
 * boot-supplied static trust caches (bsd/kern/n10_trustcache.c, patch 0025).
 * launchd_cache_loader (iOS 16.7, a RequireSuccess boot task) opens
 * IOServiceMatching("AppleMobileFileIntegrity") with type 0 and calls
 * selector 6 with one scalar and the 20-byte cdhash of launchd.plist.sig as
 * the input structure: kIOReturnSuccess = in a trust cache,
 * kIOReturnNotFound = not in a trust cache. That is the only selector served;
 * every other one fails with kIOReturnUnsupported. Every call is logged.
 */
#include <pexpert/arm64/board_config.h>

#include <IOKit/IOService.h>
#include <IOKit/IOUserClient.h>
#include <IOKit/IOKitKeys.h>
#include <IOKit/IOLib.h>
#include <IOKit/IOMemoryDescriptor.h>
#include <sys/proc.h>

extern "C" bool n10_tc_lookup(const uint8_t cdhash[20]);

#define N10_AMFI_SEL_TRUST_CACHE 6
#define N10_AMFI_CDHASH_LEN      20

class AppleMobileFileIntegrity : public IOService {
	OSDeclareDefaultStructors(AppleMobileFileIntegrity);

public:
	bool start(IOService *provider) APPLE_KEXT_OVERRIDE;
};

OSDefineMetaClassAndStructors(AppleMobileFileIntegrity, IOService);

bool
AppleMobileFileIntegrity::start(IOService *provider)
{
	if (!IOService::start(provider)) {
		return false;
	}
	setProperty(kIOUserClientClassKey, "AppleMobileFileIntegrityUserClient");
	registerService();
	IOLog("Note10 AMFI: trust-cache query service registered (selector 6 only)\n");
	return true;
}

class AppleMobileFileIntegrityUserClient : public IOUserClient {
	OSDeclareDefaultStructors(AppleMobileFileIntegrityUserClient);

public:
	IOReturn clientClose(void) APPLE_KEXT_OVERRIDE;
	IOReturn externalMethod(uint32_t selector, IOExternalMethodArguments *args,
	    IOExternalMethodDispatch *dispatch, OSObject *target,
	    void *reference) APPLE_KEXT_OVERRIDE;
};

OSDefineMetaClassAndStructors(AppleMobileFileIntegrityUserClient, IOUserClient);

IOReturn
AppleMobileFileIntegrityUserClient::clientClose(void)
{
	terminate();
	return kIOReturnSuccess;
}

IOReturn
AppleMobileFileIntegrityUserClient::externalMethod(uint32_t selector, IOExternalMethodArguments *args,
    __unused IOExternalMethodDispatch *dispatch, __unused OSObject *target,
    __unused void *reference)
{
	IOReturn ret = kIOReturnUnsupported;
	uint32_t in_struct = args->structureInputDescriptor != NULL ?
	    (uint32_t)args->structureInputDescriptor->getLength() : args->structureInputSize;
	const uint8_t *h = NULL;

	if (selector == N10_AMFI_SEL_TRUST_CACHE) {
		if (args->structureInputDescriptor != NULL || args->structureInput == NULL ||
		    args->structureInputSize != N10_AMFI_CDHASH_LEN) {
			ret = kIOReturnBadArgument;
		} else {
			h = (const uint8_t *)args->structureInput;
			ret = n10_tc_lookup(h) ? kIOReturnSuccess : kIOReturnNotFound;
		}
	}

	char name[32];
	proc_selfname(name, sizeof(name));
	if (h != NULL) {
		IOLog("Note10 AMFI: %s sel %u cdhash %02x%02x%02x%02x%02x%02x%02x%02x%02x%02x"
		    "%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x -> 0x%x\n", name, selector,
		    h[0], h[1], h[2], h[3], h[4], h[5], h[6], h[7], h[8], h[9],
		    h[10], h[11], h[12], h[13], h[14], h[15], h[16], h[17], h[18], h[19], ret);
	} else {
		IOLog("Note10 AMFI: %s sel %u in %u/%u -> 0x%x\n", name, selector,
		    args->scalarInputCount, in_struct, ret);
	}
	return ret;
}
