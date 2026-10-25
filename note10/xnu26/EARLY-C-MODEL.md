# 초기 C 코드와 실제 상태의 PC 검증

실기기 예약 결과와 독립적인 작업이다. 검토한 source-built Mach-O 및 실제 전달 adapter를
PC에서 실행하고, MMU/cache/TLB·특정 시스템 레지스터 효과는 명시적 모형으로 처리한다.
커널 함수의 반환값을 성공으로 바꾸거나 panic을 우회하지 않는다.

기존 첫 `_static_if_init` 호출 직전 경계에서 더 진행해 다음을 확인했다.

- `static_if_init`, 등록된 초기화 함수, 명령 패치, memcpy 및 cpu_data_init 실행.
- 실제 static-if 항목 17,190개·키 9개의 count/linked-list membership/cycle/flags 검사.
- 초기화 함수 포인터 2개의 실제 간접 호출 순서와 명령 패치 10개의 store/결과 검사.
- 패치 방향이 실제 key 활성 상태와 일치하는지 검사.
- 실제 C 복사본 1,152바이트, BootArgs 포인터 및 zero-slide fixture 상태 검사.
- `PE_init_platform(FALSE, args)` 실제 실행과 clock 입력 채택 확인.
- 단일 CPU fixture로 CPU topology 파서를 실행하고 count/pointer/ID/cluster membership 및
  선언하지 않은 CPU MMIO 주소가 생기지 않았는지 검사.

초기 탐색에서 platform 호출 직전까지 224,864개, 최소 트리에서 PE 반환까지 227,740개,
clock fixture에서 topology 호출 직전까지 232,477개 명령을 추가 실행했다.
CPU ID=0 fixture의 parser 반환 경계는 239,394개 명령이다. 세 합성 RAM 배치에서 같았다.
모두 기존 MMU 활성화 경계 이후의 명령 수이며, MMU 활성화 명령 자체는 실행하지 않는다.

## 입력과 실패 조건

시험 트리의 arm-io ranges/CPU ID=0은 **합성 입력**이다. Linux FDT 전체의 변환 결과나
실제 Exynos 8코어 topology가 아니다. 기본 26MHz는 앞선 Linux 관측과 같은 수치이지만
CI에는 기기 로그/관측 profile을 올리지 않고 명시적 fixture 값으로 사용한다.
GIC 초기화/소유권 인계를 주장하는 `gic-handoff`는 넣지 않는다.

실제 C clock 초기화를 생략하면 WFE event index가 유효하지 않아 panic 호출 직전에 도달한다.
CPU의 필수 reg 속성을 생략해도 실제 missing-property panic 호출을 관측하고 거부한다.
panic 함수 본문이나 기기 재시작을 실행하지 않고 format/호출 경로를 private 결과에 기록한다.

XNU의 WFE 설정은 CNTKCTL 값을 읽고 EVENTI에 OR한다. 기존 선택 비트가 남으면
26MHz fixture의 기대 index=4와 달라질 수 있다. 전달 어댑터는 EVT 선택 비트 4:7이
0이 아니거나 CNTFRQ가 26MHz가 아니면 status=5로 거부하도록 보강했다.
레지스터를 초기화하거나 Linux 종료를 수행하는 코드가 아니다. 다른 CPU/장치 정지,
GIC/timer 인계 및 실제 초기 레지스터 상태는 여전히 별도 준비와 검증이 필요하다.

PC C-checkpoint에 stale event bits를 주입하면 최종 상태 검사가 거부한다.
별도 어댑터 명령 검사는 이 값을 **XNU 진입 전**부터 거부하는지 확인한다.
정상 fixture CNTKCTL 입력 0은 C 실행 후 0x4f, WFE event index는 4다.

## 재현

```text
powershell -NoProfile -ExecutionPolicy Bypass -File note10/shim/build_transfer.ps1 -OutputDirectory note10/private/xnu-transfer-timer
python note10/shim/test_transfer.py --elf note10/private/xnu-transfer-timer/transfer.elf
python note10/xnu26/test_early_c_state.py
python note10/xnu26/test_early_c_entry.py --kernel-build NATIVE_BUILD --adapter TIMER_ADAPTER_ELF --output PRIVATE_NEW_DIRECTORY --observed-profile PRIVATE_PROFILE
```

관측 profile은 선택 사항이다. 결과·버퍼는 private에 저장한다. 기존 ELF와 Linux 예약 진단 ZIP은
덮어쓰지 않았다. 플랫폼 하드웨어 준비 완료나 XNU/iOS 기기 부팅 성공을 의미하지 않는다.
이 모델의 CPU ID 레지스터·CNTKCTL·cache/TLB는 합성 상태다. 실제 예외 처리·GIC MMIO와
전체 arm_init 이후 VM/스케줄러/드라이버 초기화는 아직 검증하지 않았다.

## 초기 스레드와 시간 변환 추가 검증 (2026-10-25)

`thread_bootstrap` 반환까지 실제 239,922개 명령을 실행했다. 실제 configured ARM64
헤더를 컴파일한 `early_c_abi.json`을 기준으로 thread 전체 1,680바이트가 template 복사에
ctid=1,048,575와 priority=95 변경만 더한 결과인지 검사한다. 이 시점의 active=false와
미할당 CPU 포인터도 검사한다. memcpy의 실제 X0/X1/X2 인자가 목적지/template/1,680과
일치해야 한다. ABI 재검증 도구는 `verify_early_c_abi.py`이며 Windows configured 소스가 필요하다.

`machine_set_current_thread`, `cpu_bootstrap`, `rtclock_early_init` 및 실제 timebase_callback
이후, kernel_startup_bootstrap 호출 직전까지 240,463개 명령을 실행했다. thread의
CpuDatap과 CPU의 active-thread backpointer, TPIDR_EL1 및 preemption_count=0을 검사한다.
26MHz 입력에서 실제 RTClockData 결과는 초 divisor=26,000,000, 마이크로초 divisor=26,
나노초 환산 numer/denom=500/13이다.

이 경로의 CONTEXTIDR_EL1 쓰기는 실제 thread-register 설정 코드의 효과만 모델링한다.
CNTVCT_EL0=26,000,000은 명시적인 **정지된 합성 카운터**다. 실제 타이머의 증가, 인터럽트,
시계 정확도나 스케줄러 동작을 검증한 것이 아니다. 간접 timebase callback을 static-if
초기화 함수로 오인하지 않도록 initializer 순서 검사는 첫 PE 호출 이전으로 제한한다.

## Startup 정렬 및 잠금 단계 (PC 전용)

Unicorn의 명시적 max CPU 모델로 LSE LDADD를 실제 실행하여
kernel_startup_bootstrap 반환까지 1,021,267개 명령을 확인했다. 기본 CPU 모델에서는
LDADD가 지원되지 않아 예외가 발생하므로 기존 3개 배치 시험은 기본 모델을 유지하고
별도의 LSE 사례를 둔다. 기기 로그에 atomics가 관측되었지만 max 모델은 실제 Exynos의
미세구조나 전체 ISA와 같지 않으며, 실제 코어에서 LSE를 실행한 결과가 아니다.

실제 Mach-O __init_entry_set의 4,670개 항목을 원본 multiset과 비교하고, 실행 후
subsystem/rank 오름차순인지 확인한다. STARTUP_SUB_LOCKS=3까지 대상 1,006개의 실제
간접 콜백 순서·인자, startup_phase 및 다음 entry cursor를 대조한다. qsort 비교 함수와
초기화 콜백 모두 실제 커널 명령이며 함수 반환을 대체하지 않는다. 이 추가 단계만
명령 2,000,000개·호출 32,768회의 유한 실행 예산을 사용한다.

## CPU 초기화와 VM 호출 경계 (PC 전용)

단일 CPU·split-L1/L2 캐시·디버그 기능 없음·정지 카운터를 명시한 추가 fixture에서
`cpu_init`, `processor_bootstrap` 및 DRAM 속성 파싱을 실행했다. `arm_vm_init` 호출 직전
경계는 1,053,279개 명령이다. 실제 CPU 자료의 ARM64/V8 유형과 running flag,
EndOfAllTime deadline, 캐시 정보의 valid/line/용량 및 DRAM 전역 변수·초기 page number를
configured C ABI로 검사한다. fixture의 I/D 캐시는 각각 32KiB, L2는 1MiB, line은 64B다.
이는 실제 코어의 캐시를 다시 측정한 결과가 아니다.

레지스터 입력은 allowlist로 제한하며 CCSIDR은 실제 CSSELR 쓰기로 선택한 입력만 읽는다.
입력이 없으면 거부한다. SP 선택을 실제 두 stack bank에 반영하고 경계에서 exception stack이
유지되는지 검사한다. adapter와 XNU entry의 실제 DAIFSet 명령 효과를 모델 상태에 반영하므로
정상 VM 시험은 별도 DAIF 성공값을 주입하지 않는다. 실제 인터럽트를 발생시키지는 않는다.
ID_AA64DFR0=0은 디버그 기능을 선언하지 않은 합성 입력이며 기기 실측값이 아니다.

매 instruction fetch와 메모리 접근의 테이블·권한 검사는 유지한다. 반복 명령의 해석만
주소와 실제 4바이트 opcode를 키로 캐시하여 반복 qsort 비교의 PC 비용을 줄였다.
코드 패치로 bytes가 바뀌면 다시 해석한다. `arm_vm_init` 본문·새 VM 테이블·할당기 동작은
이 시험에 포함하지 않는다. 기기 실행·예약·캐시/MMU/GIC 인계는 여전히 별도 검증 대상이다.

```text
python note10/xnu26/test_vm_entry.py --kernel-build NATIVE_BUILD --adapter TIMER_ADAPTER_ELF --handoff-bundle EARLY_C_OUTPUT/case-0 --output PRIVATE_NEW_VM_DIRECTORY
```

handoff-bundle 인자는 선택 사항이다. 생략하면 기존 실행 사례와 같은 합성 1GiB 배치를
독립적으로 구성한다. CI의 entry/VM/seed 작업은 서로의 실기기 결과나 실행 버퍼를 기다리지 않는다.

## 부팅 시드 소비 경계 (PC 전용)

VM 본문 탐색에서 실제 `no random seed` panic을 관측했다. XNU는 `/chosen/random-seed`에서
256바이트를 요청한다. 공개된 예측 가능한 PC fixture를 넣은 시험은 실제
`PE_get_random_seed` 반환까지 1,058,021개 명령을 실행했다. 반환값과 목적지 256바이트,
ADT 시드의 정확한 zeroing 및 다른 ADT bytes 보존을 검사한다.

이 단계에서만 canonical ADT를 구조적으로 파싱해 찾은 해당 property의 데이터 범위에
store를 허용한다. boot_args·ADT 헤더·다른 property로 범위를 넓히지 않는다. 물리/가상
복사본 동기화 및 모든 메모리 접근 검사는 유지한다. 시드 값의 중복 byte pattern을 검색해
주소를 추정하지 않는다. 경계·내용 손상에 대한 별도 작은 fixture 검사도 둔다.

이는 시드 전달 인터페이스 시험이다. PC 시드는 비밀이나 entropy가 아니며 **실기기에
사용할 수 없다**. 후속 PRNG 초기화·entropy 품질·모든 임시 복사본의 삭제를 검증하지 않았다.
VM 본문 일부에 진입했지만 VM 초기화 완료나 실제 하드웨어 부팅을 뜻하지 않는다.

```text
python note10/xnu26/test_seed_fixture.py
python note10/xnu26/test_seed_entry.py --kernel-build NATIVE_BUILD --adapter TIMER_ADAPTER_ELF --output PRIVATE_NEW_SEED_DIRECTORY
```

진입·VM·시드 세 독립 작업의 CI가 모두 통과했다:
https://github.com/eirblue/ios_note10p/actions/runs/40176478650 (`cdf4924`).
로컬 및 CI 모두 기기 설치·재부팅·파티션 쓰기를 수행하지 않았다.
