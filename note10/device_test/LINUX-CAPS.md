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
이 도구는 vbmeta를 변경하지 않고 플래시 파일/복원 명령도 만들지 않는다.
