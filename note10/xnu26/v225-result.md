# v225 result

[v225 CI](https://github.com/eirblue/ios_note10p/actions/runs/43273576942) succeeded at source `2530bfde8dd791abec634a15fa1db5b029c8b74d`. The new shared-state source/symbol checks passed (1 group, 3 variants, 6 assertions); v224 through v220 focused results were carried without replay. The same Image compiled both owner entry bodies against one 392-byte shared state, with no separate v219 state. This proves compiled state closure, not runtime no-replay.

Image size was 50,466,828 bytes, linked extent 57,114,624 bytes and PID1 7,704 bytes. Image and linked extent remained within 59,768,832 bytes. The sole physical cycle passed descriptor/destination metadata preparation, normal TWRP return, all five partition hashes and TWRP/panel raw-brightness 10 readbacks. BOOT write and reboot were each consumed once; v225 is the installed baseline and must not be replayed.

The physical proof remains 256-byte descriptor plus 128-byte binding metadata in a 6 MiB slot and the existing 32 MiB reservation, with zero native-source input allocation. Read completion was inapplicable; the reused loop's legacy read-failure status does not classify this metadata result. Native-source ingestion, runtime global no-replay, source lifetime/pinning, virtual mapping, ADT/bootargs and XNU execution remain unproven.
