# v230 current-layout boot metadata

The new synthetic group passed: 1 group, 19 variants, 44 assertions. It exercised the actual C projection into 1,152-byte boot arguments and a 64-byte transfer record using the existing serializers.

One full target Image/PID1 CI passed. Image was 50,401,292 bytes, linked extent 57,098,240 bytes, and PID1 7,728 bytes. Linked non-init growth versus v229 was zero. The named source holder and fixed pool remain 6,258,688 bytes; linked non-init growth versus v225 remains 6,275,072 bytes. These figures are not additive.

Target evidence confirmed the 96-byte placement type, 8-byte alignment, and address offsets 40 and 88. The projection's static frame was 1,616 bytes; the two added objects had zero allocated writable bytes. This does not establish a complete runtime stack bound.

The projection has no runtime caller or reserved-destination writes. No package or device cycle ran; v229 remains installed. Complete ADT, live ownership, usable XNU RAM, native mapping, and XNU execution remain unproven.
