# 임시 Linux handoff-host 커널과 privileged CPU 진단 준비

현재 TWRP의 CONFIG_KEXEC=n 제약을 조사하기 위한 **별도 PC 빌드 실험**이다.
현재 기기에 커널/모듈을 설치하거나 재부팅하지 않는다. XNU/iOS 빌드도 아니다.

`build_handoff_kernel.py`는 공개 corsicanu d2x 커널 커밋
`55f042627bb7030c93550faafa117674d32b21d1`의 공개 defconfig로 Linux Image를 빌드한다.
KEXEC와 해당 의존성을 활성화하고 LOCALVERSION을 별도로 표시한다.
private 기기 config나 이미지·DT를 CI로 전송하지 않는다. 소스 archive·config·도구·결과 해시를 기록한다.
Ubuntu의 ARM64 cross assembler와 Clang 14를 사용한다. 오래된 소스의 경고는 로그에 남긴다.
Windows에서는 이 전체 빌드 스크립트를 실행하지 않고 수동 Linux CI를 사용한다.

## 선택적 CPU 진단

`--caps`는 자체 `linux_caps.c`를 커널에 built-in으로 추가한다.
향후 사용자가 이 커널을 직접 부팅한 경우 Linux late_initcall에서 온라인 CPU를 관측하기 위한 코드다.
기존 TWRP에는 주입하지 않고 모듈 적재도 하지 않는다.

- `on_each_cpu`의 IRQ/preemption-safe callback에서 CurrentEL·MPIDR·MMFR0/1·ISAR1·CLIDR·CTR·CNTFRQ를 읽는다.
- CLIDR가 선언한 data/unified 및 instruction cache selector만 CCSIDR로 읽는다.
- CSSELR는 원래 값으로 복원하고 전후 값을 printk에 남긴다.
- CPU hotplug·MMU 전환·cache clean/invalidate·MMIO·기기 파티션·XNU 호출은 진단 코드에 없다.
- 출력은 `N10CAP1 BEGIN/CPU/CACHE/RESTORE/END` 형식이다.

`decode_linux_caps.py`는 완결된 단일 기록, CPU 개수, selector coverage, CSSELR 복원 및 정수 폭을 검사한다.
8개 CPU를 모두 관측하지 못하면 모든 대상 CPU의 16K 지원을 확정하지 않는다.
16K reserved encoding은 unknown이며 CCSIDR로 cache 전체 용량을 자동 계산하지 않는다.
이 결과는 Linux가 노출하는 privileged register view다. 부트로더 진입 상태나 상위 EL trap 부재의 증거는 아니다.
4개 PC decoder 시험은 합성 로그다. 실제 CPU 값을 읽었다는 의미가 아니다.

```text
python note10/device_test/test_linux_caps.py
python note10/device_test/decode_linux_caps.py FUTURE_CAPTURED_DMESG
```

커널 Image 빌드가 통과해도 부팅 이미지의 크기·ramdisk·DT/AVB·로그 회수와 기기 부팅을 검증해야 한다.
현재 TWRP 원본 전체 IMG는 실제 boot 파티션보다 커서 그대로 boot에 넣을 수 없다.
recovery를 보존하려면 별도의 boot용 ramdisk/패키징이 필요하다.
기기에서 관측한 vbmeta 헤더에는 verification-disabled flag가 있으나 실제 부팅 검증 동작을 보장하지 않는다.
커널 빌드 도구 자체는 vbmeta 변경·기기 설치를 수행하지 않는다.

## 별도 boot 프로토타입 생성기

`prepare_linux_boot.py`는 성공한 `--caps` 커널 빌드, 검증된 기기 백업 5개,
공식 d2x TWRP 원본과 SHA-256으로 고정한 Android 12 AOSP mkbootimg가 있어야 동작한다.
참조 도구: https://android.googlesource.com/platform/system/tools/mkbootimg/+/android-12.0.0_r1/mkbootimg.py
도구 SHA-256: `2a8d05d34110f66c463668f43fc812ce2e46e66459c347eaadb080271df69aa8`.

현재 boot/recovery의 헤더·주소 호환 여부와 실제 boot 파티션 크기를 검사한다.
공식 TWRP ramdisk는 그대로 쓰며, boot 경로의 별도 DTB/DTBO 파티션 사용을 전제로
embedded recovery_dtbo는 포함하지 않는다. 이 DT 선택 방식의 실제 부팅 검증은 아직 필요하다.
커널/ramdisk 바이트와 결과 크기를 재검사하고 출력은 PC private 경로에만 생성한다.
원래 BOOT의 보드·OS 버전·보안 패치 월 및 payload 뒤의 `SEANDROIDENFORCE` 표식을 유지한다.
내용이 바뀌므로 원본의 AVB 푸터·서명을 복사하지 않는다. 이는 서명 생성이나 부팅 검증 통과를 뜻하지 않는다.
기존 파일은 덮어쓰지 않는다. 성공한 커널 입력이 없으면 이미지를 만들지 않는다.

생성돼도 `deployment_ready=false`인 **임시 Linux 진단 boot 프로토타입**이다.
이 생성기에는 ADB·플래시·TWRP 교체·vbmeta 수정 기능이 없다.
현재 커널·모든 복구 영역을 지우는 설치 프로그램이나 iOS ROM으로 해석하면 안 된다.

## 수동 BOOT 시험 패키지

`--caps` 빌드는 normal boot의 `skip_initramfs`가 제공된 진단 initrd를 버리지 않도록
고정 소스의 해당 parser만 수정한다. 수정 파일 해시를 빌드 결과에 기록하며,
이 처리를 확인한 빌드만 boot 생성기의 입력으로 받는다. 실제 bootloader가 ramdisk를
전달하는지와 별도 DTB/DTBO 선택, 화면·USB 작동은 첫 실기기 시험 전까지 미검증이다.

`build_boot_test_packages.py --backup DIR --prototype IMAGE --output DIR`은 private 경로에
진단 ZIP과 짝지어진 원래 BOOT 복구 ZIP을 만든다. 두 ZIP 모두 사용자가 TWRP에서
설치할 때만 BOOT에 쓴다. 생성기·전송기는 설치 코드를 실행하지 않는다.

- N976N의 정확한 bootloader·블록 노드·5개 파티션 크기를 고정한다.
- recovery/DTB/DTBO/vbmeta 전체 해시가 백업과 같아야 한다. 진단 설치는 원래 BOOT 해시도 요구한다.
- 복구 설치는 부분 BOOT 쓰기 실패에 대응하도록 현재 BOOT 해시 일치를 요구하지 않는다.
- payload를 RAM에 풀어 해시 검증 후 BOOT 하나에 쓰고 전체 BOOT 해시를 재검증한다.
- 자동 재부팅·포맷·mount·다른 파티션 쓰기를 하지 않는다. recovery 재진입을 보장하지 않는다.
- 실제 updater 제어 흐름은 PC 일반 파일에서 시험했다. 기기 블록 쓰기 성공의 증거는 아니다.

`stage_phase2.py --packages DIR`은 ZIP/내용 해시를 검증하고 TWRP의 새 `/tmp` 디렉터리로
전송한다. 네이티브 unzip 읽기와 원격 해시를 확인하며 설치하지 않는다. 재부팅하면 RAM 파일은 사라진다.

사용자가 진단 ZIP을 설치한 뒤 **Reboot > System**으로 BOOT 커널을 시작한다.
TWRP 화면이 떠도 `Reboot > Recovery`로 시작한 원래 커널과 구분해야 한다.
`collect_phase2.py`는 `4.14.113-note10-handoff-pc` 및 KEXEC 설정을 확인하고,
dmesg·config·live DT를 PC private 경로로 읽어 CPU 진단을 해독한다. 자동 설치·재부팅은 없다.
