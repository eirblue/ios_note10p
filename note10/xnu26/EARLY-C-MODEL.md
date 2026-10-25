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
