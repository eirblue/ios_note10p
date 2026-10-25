# XNU 로드 버퍼 생성과 전달 연결

`handoff_bundle.py`는 실제 링크 XNU Mach-O를 메모리에 놓을 바이트 형태로 변환하고,
boot_args·raw ADT·전달 어댑터를 명시적 배치 계획에 연결한다.
**PC 모델용 구성 요소**이며 실제 RAM 예약·Linux kexec 실행·Samsung BOOT 이미지 생성 기능은 없다.

## 구현

| 버퍼 | 현재 실행형 기준 크기 | 내용 |
|---|---:|---|
| kernel.mem | 19,578,880 bytes | 파일을 단순 복사하지 않고 각 Mach-O 세그먼트를 VA 간격에 맞춰 배치. BSS·빈 영역·꼬리 padding은 0 |
| boot-args.mem | 16,384 bytes | 실제 ABI 1,152바이트와 0 padding. ADT virtual pointer·길이·메모리 범위 포함 |
| device-tree.mem | 16,384 bytes | bounded ADT codec를 통과한 트리와 0 padding |
| adapter.mem | 16,384 bytes | relocation 없는 ARM64 ELF의 상대 PT_LOAD 세그먼트와 수정된 64바이트 전달 record |

입력 XNU는 기존 verifier로 SHA-256·plain arm64 MH_EXECUTE·세그먼트 겹침·미정의 심볼·
진입 PC를 검사한다. ELF는 표/세그먼트 범위·실행 가능한 entry·writable record를 검사하며
relocation·dynamic dependency·W+X 세그먼트·중복/변경된 record를 거부한다.

커널·인자·ADT 외에 **adapter 영역도** `validate_placement`에 포함한다.
RAM 밖, 명시된 예약/점유 영역과 충돌, 서로 겹침, bootstrap 첫 block 밖의 메타데이터,
잘못된 정렬·topOfKernelData·40bit 한도 초과를 거부한다.
주소는 자동 선택하지 않는다. `reserved`와 `occupied` 목록이 필요하며 PC fixture에서만 빈 목록을 사용한다.

`handoff.json`에는 원본 Mach-O/ELF 해시, 각 버퍼의 주소·길이·해시 및 인자/진입 주소를 기록한다.
읽을 때는 payload 해시뿐 아니라 계획과 버퍼 위치, boot_args 재생성 바이트,
ADT 길이/padding, descriptor의 인자/entry/status까지 다시 대조한다.
`physical_reservation_verified=true` 또는 하드웨어 배포 허가를 주장하는 입력은 받지 않는다.
필드를 바꿔 실제 RAM 예약의 증거로 사용할 수 없다.

```text
python note10/xnu26/handoff_bundle.py --kernel-build NATIVE_BUILD --adapter TRANSFER_ELF --adt RAW_ADT --plan EXPLICIT_PC_PLAN --output PRIVATE_OUTPUT
python note10/xnu26/test_handoff_bundle.py
```

## 실제 명령 모델에 연결

`test_materialized_entry.py`는 검증된 실제 XNU 실행형과 실제 adapter ELF로 두 PC bundle을
만들고, **생성한 네 버퍼를 직접 로드**하여 실제 ARM64 명령을 실행한다.
기존 시험처럼 segment/descriptor를 시험 코드에서만 별도로 만들어 실행하는 경로와 구분한다.

- 비제로 값으로 채운 kernel memory에 전체 버퍼를 복사하고 실제 원본 세그먼트 바이트·BSS zero를 확인한다.
- adapter 전체 바이트와 entry/record 위치를 원본 ELF에서 재생성해 대조한다.
- XNU가 만들 bootstrap table 4개 page는 다시 비제로 값으로 채워 실제 초기화 루프를 검사한다.
- boot_args·ADT가 보존되는지와 ADT 첫/끝 바이트의 identity/virtual 매핑도 검사한다.
- 원본 XNU 전체 세그먼트 끝점 매핑·8,250회 kernel store 검사를 유지한다.
- 선택적으로 hash-bound 실측 CPU profile로 실제 TCR의 16K/40bit capacity를 검사한다.

Windows에서 두 모델 모두 각각 **24,999개 명령**, kernel store **8,250회/66,000 bytes**를
통과하고 MMU 활성화 직전에 멈췄다. 새로운 실제 기기 부팅 시험은 수행하지 않았다.

```text
python note10/xnu26/test_materialized_entry.py --kernel-build NATIVE_BUILD --adapter TRANSFER_ELF --observed-profile OBSERVED_PROFILE_JSON --output PRIVATE_MODEL_OUTPUT
```

7개 bundle PC 시험은 실제 빌드 adapter ELF·BSS/holes·ELF 변조/의존성·주소 충돌/점유·잘못된 하드웨어 주장·
파일 손상·manifest/descriptor 불일치를 포함한다. 기존 boot contract 시험 8개도 통과했다.
unit fixture와 통합 모델의 주소는 **합성 입력**이며 기기의 사용 가능한 RAM 주소가 아니다.

## 다음 실제 연결 조건

이 버퍼를 기기에 로드하려면 Linux가 보장하는 실제 RAM 예약/점유 증거와 로드 backend가 필요하다.
다른 CPU·DMA 장치 정지, dirty cache 정리, 적절한 EL에서 MMU/cache 종료와 GIC/timer 인계도 필요하다.
현재 raw ADT 통합 시험은 chosen/boot-args parser fixture이며 GIC 소유권을 만들어 넣지 않는다.
실제 Exynos ADT·GIC handoff·C arm_init·MMU 활성화·기기 로그 회수는 검증하지 않았다.

별도 boot-partition Linux 진단 시험은 initrd 전달 문제로 Android root에 진입했다.
그 이미지나 이 PC bundle을 XNU/iOS 설치 이미지로 취급하지 않는다. 기기 변경은 수행하지 않았다.
`deployment_ready=false`, `physical_reservation_verified=false`를 유지한다.

별도 [초기 RAM 예약 진단](../device_test/RESERVATION.md)에서 Linux memblock 예약과
내장 최소 initramfs를 추가했다. 실제 성공은 다음 수동 시험 로그로 확인하며,
그 이전 부팅의 예약 주소를 현재 recovery의 유효 주소로 취급하지 않는다.
동일한 256MiB 크기의 추가 합성 모델은 24,807개 명령/8,202회 kernel store를 통과했다.
