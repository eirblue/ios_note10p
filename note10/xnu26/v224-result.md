# v224 result

[v224 CI](https://github.com/eirblue/ios_note10p/actions/runs/43261054452) succeeded at source `0c8fe959d0d1003746f41adb5c3f4766bf5784b6`. The new bounded metadata-interval checks passed (1 group, 10 variants, 10 assertions); v223 stack-path, v222 wire, v221 metadata and v220 macro results were carried without replay. Image size was 50,466,828 bytes and linked extent 57,114,624 bytes, within the 59,768,832-byte cap.

The sole physical cycle passed: descriptor/binding metadata was prepared in the reserved destination, normal TWRP return and all five partition hashes were verified, and TWRP/panel brightness readbacks confirmed raw 10. BOOT write and reboot were each consumed once; this build must not be replayed. v224 is the installed physical baseline.

The proven scope is 256-byte descriptor plus 128-byte binding metadata in a 6 MiB slot and the existing 32 MiB reservation, with zero native-source input allocation. Read completion was inapplicable; the reused loop's legacy read-failure status does not classify this metadata result. Native-source ingestion, source lifetime/pinning, virtual mapping, ADT/bootargs and XNU execution remain unproven.
