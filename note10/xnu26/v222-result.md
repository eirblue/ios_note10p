# v222 result

v222 CI failed during post-build evidence collection. Device validation remains blocked.

| Focused checks | Result | Groups / variants / assertions |
| --- | --- | --- |
| v220 closed macro-safe attribute transform and syntax | PASS | 2 / 4 / 4 |
| v221 metadata-only compositor and admission | PASS | 3 / 6 / 8 |
| v222 canonical Base64 context wire | PASS | 1 / 3 / 3 |

The v221 checks were carried unchanged into v222; they were not rerun. Earlier SHA and syntax fixtures were not replayed.

[v221 CI](https://github.com/eirblue/ios_note10p/actions/runs/43238180708) failed because ROOT supplied plain JSON to an input requiring Base64-encoded JSON. It stopped before source acquisition, PID1 linking or Image building. v222 uses the tested encoder and strict decoder; raw JSON remains rejected.

[v222 CI](https://github.com/eirblue/ios_note10p/actions/runs/43241282181) completed the fresh v212 PID1 link and full Image build with exit code 0. The build included the reviewed integration through v220, including the v216 sensor guard and macro-safe SHA attributes. The failed producer reported:

- Image: 50,466,828 bytes.
- Linked extent: 57,114,624 bytes.
- Image/linked cap: 59,768,832 bytes.

Overall CI still failed: the evidence reader expected `init.su`, which was absent at that path. The recorded compiler command used `-fstack-usage` and output `.tmp_init.o`. A corresponding `.tmp_init.su` is a hypothesis for the successor to investigate; its existence and location were not observed.

Authenticated failure evidence was collected once. No Image was retrieved, and stack/type evidence did not complete. No battery or device queries occurred, and there is no physical or native-runtime proof.

The selected physical scope remains descriptor/binding metadata only: a 6 MiB slot, a 32 MiB reservation and zero native-source input allocation. Native ingestion remains unregistered and uncalled. A reviewed v223 correction and fresh successful CI are required before package/physical review and any battery check. v222 CI will not be retried.
