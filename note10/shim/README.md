# Initial-entry capability capture prototype

Exynos 보드 header에 캐시·페이지 크기를 임의로 지정하지 않기 위해 초기 privileged 진단 코드를 준비했다.
SM-N976N의 Android cache sysfs 조회에서는 읽을 항목이 나오지 않았다.
이전 Android 사용자 모드 MMFR0 값도 커널 보정 가능성이 있어 실제 16KiB 지원의 근거로 사용하지 않는다.
보드 header/MASTER profile은 아직 작성 완료하지 않았다.

## 구현

- `cap_entry.S`: AArch64 EL1 또는 EL2에서 시작하는 단일 CPU의 stack 없는 진단 entry.
- x0–x3 전달 값, SP, 초기 DAIF/EL, MPIDR·타이머 주파수·CPU feature register를 저장한다.
- EL1 translation/control register를 저장하고, EL2로 진입했을 때만 EL2 register도 저장한다.
- CLIDR가 선언한 data/separate/unified cache에 한해 CSSELR로 선택하고 CCSIDR를 읽는다.
- CSSELR를 원래 값으로 복원한다. 기록을 초기화해 재진입 시 이전 값이 남지 않도록 한다.
- 종료 전 barrier와 완료 marker를 기록한 뒤 WFE loop에서 멈춘다.
- `decode_cap_record.py`: 320-byte versioned record에서 granule 지원 상태와 cache-maintenance line parameter를 해석한다.
  예약 encoding은 지원 여부 미상으로 남기며, 미완료·잘못된 형식의 기록은 거부한다.

MMIO, UART, 화면 출력, CPU 시작, 페이지 테이블 설정, cache clean/invalidate, XNU 호출은 구현하지 않았다.
SCTLR/TCR/TTBR는 읽기만 한다. 쓰는 시스템 상태는 DAIF mask와 일시적인 CSSELR다.
기록할 자기 data 영역이 writable인 AArch64 EL1/EL2 진입을 전제로 하며, Android 사용자 모드에서 실행할 수 없다.
다른 CPU가 같은 entry에 동시에 진입하는 경우는 지원하지 않는다.

결과물은 **연구용 ELF**다. Android/Linux boot image header, Samsung 패키징/서명이나 검증된 로드 위치가 없다.
현재 기기에 전송·실행·플래시하지 않았다. 기록을 실제로 회수할 초기 부팅 로그/메모리 접근 경로도 미구현이다.
가상화/상위 EL trap이 있으면 직접 MRS도 해당 EL에 노출된 값일 수 있다. 1개 CPU 기록으로 전체 코어를 판정하지 않는다.

## PC 검증

NDK Clang 9.0.8과 LLD로 ARMv8.2 ELF compile/link를 완료했다. linked ELF에 잔여 REL/RELA section이 없음을 검사했다.
Unicorn 2.1.4로 **실제 조립된 명령**을 실행하되 시스템 register MRS/MSR는 합성 값의 hook으로 대체했다.

- EL1/EL2, cache 배치 4종, 16KiB encoding 4종, 로드 base 3종 및 unsupported EL 분기: 102 cases 통과.
- x0–x3/SP 보존, 자기 record 내부 쓰기, EL별 register 접근, 유효 cache 선택, CSSELR 복원, 오래된 record 초기화 확인.
- 잘못된 길이/magic/version/status/EL/reserved bytes: 9종 거부 확인.
- EL0 분기 검사는 합성 CurrentEL hook에 대한 제어 흐름 검사일 뿐이다. 실제 EL0에서 CurrentEL MRS를 실행할 수 있다는 뜻이 아니다.

**하드웨어 feature 값이나 실제 privileged 실행을 검증한 시험은 아니다.**
결과·실행 ELF/소스 hash는 `note10/private/cap-probe/test-result.json`에 저장한다.
Unicorn과 Capstone은 PC 검사 도구이며, 목표 iOS를 에뮬레이터에서 구동하는 경로로 변경한 것이 아니다.

```powershell
./note10/shim/build.ps1
python note10/shim/test_cap_entry.py
# 향후 회수한 raw 320-byte record 해석:
python note10/shim/decode_cap_record.py PATH_TO_RECORD
```

ELF는 `note10/private/cap-probe/cap-probe.elf`에 생성한다. 기기용 부팅/플래시 명령은 제공하지 않는다.

필드 정의 참고:
[Arm CCSIDR_EL1 register](https://support.arm.com/documentation/ddi0601/2026-09/AArch64-Registers/CCSIDR-EL1--Current-Cache-Size-ID-Register),
[Arm Trusted Firmware의 MMFR0 field 정의](https://github.com/ARM-software/arm-trusted-firmware/blob/master/include/arch/aarch64/arch.h).
CCSIDR line parameter를 cache 전체 용량이나 실제 microarchitecture의 직접 증거로 확대 해석하지 않는다.
