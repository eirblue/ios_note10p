# XNU 진입 어댑터 준비와 복원 기준 확보

현재 TWRP는 CONFIG_KEXEC=n이다. 여기의 코드로 기기에서 XNU를 실행한 것은 아니다.
`xnu_transfer.S`는 **CPU/장치 종료가 이미 완료된 이후**의 인자 전달만 다루는 PC 연구용 구성 요소다.
Android boot/recovery 이미지, Linux Image 또는 설치 ZIP으로 포장하지 않았다.

## 관측과 공개 소스

실기기에서 boot와 recovery가 별도 블록 노드임을 확인했다. 현재 boot의 ramdisk 크기는 0이며
recovery에는 TWRP ramdisk가 있다. 따라서 recovery를 바꾸지 않는 경로를 검토할 수 있다.
boot 교체가 AVB와 부팅 경로에 미치는 영향까지 검증하거나 TWRP 재진입을 보장한 것은 아니다.

관측한 recovery uname의 g55f042627 접미사와 일치하는 공개 커밋은
[corsicanu kernel 55f042627bb7030c93550faafa117674d32b21d1](https://github.com/corsicanu/android_kernel_samsung_universal9820/commit/55f042627bb7030c93550faafa117674d32b21d1)이다.
이는 실행 바이너리의 재현 빌드 일치를 입증하지 않는다.
이 소스의 `arch/arm64/kernel/machine_kexec.c`는 다른 CPU 정지 조건과 cache flush 뒤
cpu_soft_restart로 MMU/cache를 종료하는 경로를 사용한다. 실제 실행된 경로는 아니다.
`relocate_kernel.S` 마지막은 **x0–x3을 모두 0으로 지우고 새 진입점으로 branch**한다.
따라서 해당 경로를 향후 활성화하더라도 XNU boot_args를 x0에 넣는 별도 연결이 필요하다.

## 어댑터의 범위

- stack 없이 PC-relative 64바이트 descriptor를 읽는다. relocation 없는 ELF로 링크한다.
- EL1만 지원한다. SCTLR_EL1의 M/C/I 중 하나라도 켜져 있으면 거부한다.
- magic/version/size/예약값·flags·인자와 진입점의 0/정렬/상위 주소 비트를 검사한다.
- DAIF를 mask하고, 준비된 boot_args 주소를 x0에 넣고 x1–x3을 0으로 지운 뒤 지정 진입점으로 branch한다.
- writable 자기 descriptor의 status와 관측 SCTLR만 기록한다. 실패 시 WFE loop에서 정지한다.
- status=1은 **branch 시도 표시**이며 XNU 부팅 성공 표시가 아니다.

Caller는 인자/커널/어댑터의 실제 RAM 예약·범위·비중첩·캐시 정합성을 먼저 보장해야 한다.
M/C/I가 꺼졌다는 사실만으로 이전 dirty cache가 적절히 clean됐다고 판단할 수 없다.
기기 종료, 다른 CPU 정지, cache/TLB 정리, EL2→EL1 전환, GIC 소유권 이전,
Exynos ADT 생성과 실패 로그 회수는 이 어댑터가 구현하지 않는다. Linux의 kexec도 활성화하지 않는다.
기본 descriptor의 인자·진입점은 0이므로 그 상태로는 branch하지 않는다.

## PC 시험

Windows NDK Clang 9 + LLD로 ELF를 만들고 실제 명령을 Unicorn에서 실행했다.
시스템 레지스터·DAIF·barrier는 합성 모델이다.
3개 로드 위치에서 정상 전달과 EL2/EL3·MMU/cache 활성·descriptor 오류를 포함한 **54개 사례**를 통과했다.
EL0 시험은 없다. 실제 EL0의 CurrentEL 읽기를 지원하는 코드가 아니다.

이후 실제 링크 XNU 실행형 앞에 어댑터를 배치하고, x0–x3을 0에서 시작시켰다.
합성 RAM 두 배치에서 **각 24,999개 명령**을 실행하여 XNU의 MMU 활성화 직전까지 도달했다.
커널의 8,250개 store/66,000 bytes와 전체 세그먼트 끝점 매핑을 확인했다.
초기 매핑 밖의 boot_args는 기존 테이블 검사기가 거부했다. XNU가 직접 이를 거부한 것은 아니다.
실제 CPU·Linux 종료 경로·MMU 활성화·C arm_init·드라이버·사용자 공간은 실행하지 않았다.

```text
powershell -NoProfile -ExecutionPolicy Bypass -File note10/shim/build_transfer.ps1
python note10/shim/test_transfer.py
python note10/xnu26/test_linked_entry.py NATIVE_BUILD --adapter note10/private/xnu-transfer/transfer.elf
```

## 읽기 전용 부팅 구성 백업

`note10/device_test/backup_boot.py --read`는 TWRP/root/AArch64·N976N bootloader를 확인하고
고정 allowlist **boot/recovery/dtb/dtbo/vbmeta**만 PC private의 새 세션으로 읽는다.
크기·경로·중복 블록·총량을 제한하며, 전송 전후 기기 SHA-256과 PC 파일 해시가 같아야 완료한다.
기존 백업은 덮어쓰지 않는다. 복원 명령이나 기기 쓰기·재부팅 기능은 없다.
7개 PC 시험은 잘못된 모델·허용되지 않은 파티션·크기·전송 손상·해시 변경 등을 거부했다.

실기기 5개 구성의 백업과 해시 대조를 완료했다. recovery 백업의 앞부분은 공식 TWRP 원본 이미지와
바이트가 같았다. 파티션 전체에는 뒤쪽 추가 공간이 있으므로 원본 IMG 전체 해시와는 구분한다.
이 백업은 전체 Android·사용자 데이터·EFS 백업이 아니며, 복원 성공을 시험한 결과도 아니다.
원본 이미지·DT·기기 로그·전체 헤더와 hash manifest는 private에만 보관한다.

## Timer entry guard (2026-10-25)

Current source additionally requires CNTFRQ_EL0=26,000,000 and clear CNTKCTL_EL1
EVENTI selector bits [7:4]. A mismatch returns status 5 before branching to XNU.
The guard does not reset those registers or quiesce Linux/devices. The actual
assembly instruction suite now covers 81 cases across three placements.
`build_transfer.ps1 -OutputDirectory PRIVATE_NEW_DIRECTORY` and
`test_transfer.py --elf PRIVATE_NEW_DIRECTORY/transfer.elf` preserve older ELFs
and their bundle hashes. Existing diagnostic ZIPs are unchanged.
