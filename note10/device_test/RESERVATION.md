# XNU용 초기 RAM 예약 진단

## 2026-10-25 수동 시험과 기록 보강

첫 예약 시험 후 기존 TWRP 재진입 및 원본 recovery/DTB/DTBO/vbmeta 보존을 해시로 확인했다.
BOOT는 시험 패키지의 전체 파티션 payload와 일치했다. 이전 로그에는
`CHECK pages=65536 reserved=65536 invalid=0 shift=12`가 그대로 남았다.
그러나 초기 RESERVED 주소 및 build banner에 문자 손상이 있었고, 두 번 읽은 원본 해시가 같았다.
따라서 전송 재시도로 회복되지 않았으며, 주소를 추정하거나 예약 검증 완료로 처리하지 않았다.
약 125초 시점에는 버튼 hard-reset hook 및 panic 기록이 있었다. XNU는 실행하지 않았다.
원본 기기 로그는 private 보관하며 공개 저장소에는 포함하지 않는다.

다음 빌드는 `N10RAM2` 완결 프레임 32개를 late init에서 기록한다.
각 프레임은 빌드마다 생성한 128비트 ID, 순번, 주소/크기/정렬, 페이지 검사 결과,
ASCII 본문의 FNV-1a 32비트 오류 검출값을 포함한다. 이는 인증이나 암호학적 무결성 증명이 아니다.
회수기는 SHA-256으로 확인한 Image 안의 고유 ID를 확인하고, 해당 ID의 체크섬이 맞는
서로 다른 순번 2개 이상이 완전히 같은 결과를 나타내야 통과시킨다.
손상 프레임은 복원하지 않으며, 유효 프레임 간 충돌·중복 순번·비정상 페이지 상태는 거부한다.
기존 N10RAM1 빌드에는 기존의 엄격한 판정을 유지한다.

다음 설치 ZIP은 `--current-packages`로 검증한 이전 시험 BOOT를 설치 전 기준으로 삼을 수 있다.
원래 백업과의 결합 및 비BOOT 4개 파티션 대조는 계속 필수다. 자동 설치/재부팅은 없다.

v2 전체 Image 빌드와 고유 ID 내장 검사를 통과했다:
https://github.com/eirblue/ios_note10p/actions/runs/40162958220 .
수집기를 포함한 PC 검사 108개 및 실제 PID1 명령 모델도 통과했다:
https://github.com/eirblue/ios_note10p/actions/runs/40163157625 .
로컬 수동 ZIP 쌍은 완성했으나, 완료 시 ADB 연결이 없어 RAM 전송·현재 파티션 재검사는 대기 상태다.
이는 v2 실기기 시험이나 XNU 부팅 성공을 의미하지 않는다.

XNU 로드 버퍼 생성 뒤 실제로 필요한 **Linux allocator에서 제외된 RAM**을 준비하는 단계다.
아직 XNU를 실행하지 않으며, 실제 예약 성공은 사용자의 다음 수동 기기 시험 로그로 판정한다.
Android 부팅 복구와 별개로 진행한다. 원래 BOOT 복구 후에도 Android 부팅 반복이 남았다는 상태를 유지한다.

## 커널 경로

`build_handoff_kernel.py --caps --reserve`는 고정 공개 d2x Linux 소스에
`xnu_reserve.c`를 포함한다. 해시로 고정한 `arch/arm64/mm/init.c`의
`arm64_memblock_init`에서 kernel/initrd·DT reserved-memory·crashkernel·CMA 예약을 마친 후 호출한다.

- `memblock_find_in_range`로 2GiB 이상·1TiB 미만에서 256MiB/32MiB 정렬 free range를 찾는다.
- RAM 내부인지·기존 예약과 겹치지 않는지 검사한 뒤 `memblock_reserve`로 제외한다.
- 찾기/예약 실패를 명시적으로 기록한다. 임의 고정 주소를 선택하지 않고 window에 데이터를 쓰지 않는다.
- late initcall에서 해당 4K PFN 65,536개를 확인해 valid 및 PageReserved 상태를 집계한다.
- CPU/DMA 종료·cache/MMU 전환·GIC 인계·XNU branch는 수행하지 않는다.

이것은 Linux allocator에서의 예약이다. secure firmware 소유권이나 DMA 정지를 증명하지 않는다.
재부팅하면 해당 Linux의 예약 문맥도 끝난다. 이전 로그의 주소를 현재 TWRP에서 재사용하면 안 된다.

## Android root로 넘어가지 않는 내장 init

이전 BOOT 시험에서 외부 TWRP ramdisk의 unpack 기록 없이 Android root가 마운트됐다.
예약 진단 빌드는 자체 `minimal_init.S`를 static ARM64 ELF로 만들고,
dev/console 및 init만 들어 있는 deterministic newc CPIO를 커널에 내장한다.
TeamWin ramdisk를 CI에 포함하거나 배포하지 않는다.

`CONFIG_CMDLINE_EXTEND=y` 및 `rdinit=/init`으로 부트로더 하드웨어 인자를 유지한다.
이 Kconfig 의존성을 만족시킨 뒤 `CONFIG_INITRAMFS_FORCE=y`로 외부 initrd를 무시한다.
skip_initramfs parser 처리도 유지해 내장 archive를 버리지 않도록 한다.
BOOT 생성기는 실제 Image 안에서 동일한 CPIO 원본 또는 그 gzip 스트림을 찾아 검증한다.
이 모드의 BOOT header에는 외부 ramdisk가 없다.

PID1은 콘솔에 `N10INIT1 IDLE`을 출력하고 ppoll로 대기한다.
실제 ELF를 Unicorn에서 실행해 write→ppoll 반복만 확인했다. 파일 열기·디스크 mount·
재부팅·module/kexec/XNU 호출이 없는 코드다. 이는 PC syscall 모델이며 기기 실행 증거는 아니다.

이 BOOT에서는 TWRP UI나 ADB가 실행되지 않는다. 기존 recovery의 TWRP는 디스크에 보존한다.
화면이 로고에 머무는 것만으로 성공을 판정하지 않는다. 사용자가 recovery로 돌아와 로그를 읽어야 한다.

## 판정·회수

기대 로그:

```text
N10RAM1 RESERVED base=... size=10000000 align=2000000
N10RAM1 CHECK pages=65536 reserved=65536 invalid=0 shift=12
```

`decode_reservation.py`는 정확한 예약 커널 banner, 단일 RESERVED/CHECK 순서,
페이지 수·범위·정렬을 요구한다. FAILED·누락·합쳐진 로그·PageReserved 부족은 거부한다.
성공해도 `safe_to_reuse_address_after_reboot=false`이며 XNU 실행/배포 성공 표시가 아니다.

`collect_reservation.py --packages DIR --kernel-build DIR`는 TWRP에서 last_kmsg와
이미 마운트된 pstore만 읽는다. Image/패키지 해시 및 정확한 source build banner와 연결하고,
원본·decoder 결과를 PC private에 저장한다. 설치·reboot·mount·포맷은 하지 않는다.

## PC 검사와 남은 연결

CPIO 독립 parser·잘못된 init/고정 source 거부·실제 Image archive 불일치 거부,
예약 로그 실패/누락/문맥 검사를 제공한다. 실제 static PID1 명령도 별도로 시험한다.
기존 XNU 버퍼 모델에는 높은 합성 PA와 256MiB 창을 추가했다.
기존 두 1GiB 모델은 각각 24,999개 명령, 256MiB 모델은 24,807개 명령 후 MMU 활성화 전에 멈췄다.
이 주소들은 기기의 free RAM을 지정한 것이 아니다.

예약된 문맥 안에서 실제 load backend를 실행하고 장치/CPU/cache/MMU/GIC를 인계하는 연결이
다음 단계다. 이 문서는 설치 가능한 iOS ROM이나 XNU 실기기 부팅 성공을 의미하지 않는다.
