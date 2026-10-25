# PC 부팅 인자·메모리 배치·Apple DT 검증

현재 결과는 로더 구성 요소의 PC 검증이다. 설치 가능한 커널 이미지나 ROM은 아니다.
파티션 쓰기·기기 재부팅·XNU 실기기 실행을 수행하지 않았다.

## ARM64 boot_args

`boot_contract.py`는 revision 2 / version 2 구조체를 1,152바이트로 생성한다.
명령행의 UTF-8 바이트 길이·NUL, 정수 폭, 포인터 범위와 메모리 크기를 검사하며
ABI padding을 0으로 채운다. 화면 정보와 DT 포인터를 자동 추정하지 않는다.

`verify_boot_args_abi.py`는 저장된 Windows 컴파일 환경으로 실제 pinned 공개 XNU의
`pexpert/pexpert/arm64/boot.h`를 포함하는 ARM64 Mach-O 객체를 생성한다.
객체에서 구조체 크기·13개 필드 offset과 실제 C initializer를 읽어 Python 생성값과 비교했다.
1,152바이트 전체가 일치했다. ARM 객체를 Windows에서 실행한 결과는 아니다.
공개 소스 12377.121.6과 IPSW 커널 12377.122.8의 ABI 일치를 증명하지 않는다.

## 명시적 배치 검사

`validate_placement`는 제공된 RAM, 예약 영역, 현재 recovery/로더의 점유 영역과
커널·부팅 인자·선택적 DT 배치를 검사한다. 주소 자동 선정이나 실제 RAM 예약은 하지 않는다.
16K 정렬·범위·영역 충돌·topOfKernelData의 포함 범위를 검사한다.
빈 점유 목록은 합성 시험에서만 사용했다. 실제 recovery에서는 DT 예약 영역 외에도
실행 중인 커널·버퍼·스택·페이지 테이블을 보존할 점유/예약 정보가 필요하다.

실제 start.s는 Mach-O 헤더까지의 변위를 memSize에서 뺀 뒤 L2 블록 단위로
내림한 수만큼 매핑한다. 초기 매핑 전체가 32MiB 하나로 제한되는 것은 아니다.
생성기 정책상 부팅 인자·DT는 첫 32MiB 블록에 두고 커널은 여러 블록에 걸칠 수 있다.
전체 커널 세그먼트의 시작·끝을 실제 생성된 테이블로 walk하여 검증했다.
이 정책은 검증한 실행형·16K 구성에 한정되며 임의 커널의 범용 로더 계약이 아니다.

## Apple DT

`boot_adt.py`는 raw ADT를 생성·해석한다. 속성/노드 이름 한도, 크기·깊이·개수,
중복·순환, 잘린 입력과 padding을 검사한다. placeholder 속성은 지원하지 않는다.
Linux FDT를 그대로 복사하거나 V60의 MMIO·기기 식별값을 가져오지 않는다.

`test_linked_adt.py`는 실제 링크 실행형의 SecureDTInit/LookupEntry/GetProperty와
실제 문자열 비교 코드를 Unicorn에서 실행했다. 316바이트 합성 트리의 경로·속성 값과
없는 노드/속성 반환을 확인하고, 잘린 영역·과도한 속성 길이는 실제 panic 진입을 관측했다.
총 2,094개 명령이 실행됐다. parser 함수 시험이며 커널 초기화·보드 부팅은 아니다.
시험 DT에는 `gic-handoff`가 없다. 실제 GIC 소유권·초기화 없이 이 값을 만들어 넣으면 안 된다.
Apple `awl-scratch-supported`도 생성하지 않았다. 실제 CPU·메모리·클록·보드 트리는 미완료다.

## 재현

```text
python note10/xnu26/test_boot_contract.py
python note10/xnu26/test_boot_adt.py
python note10/xnu26/verify_boot_args_abi.py
python note10/xnu26/test_linked_entry.py PATH_TO_NATIVE_BUILD
python note10/xnu26/test_linked_adt.py PATH_TO_NATIVE_BUILD
```

처음 두 명령은 표준 Python만 필요하며 총 13개 시험이다. ABI 검사는 저장된 로컬
컴파일 환경·실제 공개 헤더가 필요하다. 링크 실행 시험은 검증된 native-build artifact와
Unicorn 2.1.4 / Capstone 5.0.9가 필요하다. 보고서와 객체는 `note10/private/`에만 저장한다.

## TWRP 보존과 남은 경계

[공식 d2x 안내](https://twrp.me/samsung/samsunggalaxynote10plus5G.html)는 recovery 커널
구성과 AVB 조건을 설명한다. recovery를 덮어쓰면 TWRP가 사라질 수 있고, boot만 바꿔도
검증·부팅 조건에 따라 재진입이 실패할 수 있다. TWRP 재진입을 보장하지 않는다.
현재 진단 ZIP은 RAM에서 관측만 수행하므로 커널/ROM 설치와 구분해야 한다.

기기 DT·예약 메모리 수집, RAM 실행 경로 지원 확인, CPU/캐시/MMU 정리·다른 CPU 정지,
GIC/timer 소유권 이전과 진단 로그 경로가 여전히 필요하다. RAM에서 XNU로 전환하면
실행 중인 TWRP도 계속 동작하는 것이 아니며, 실패 시 재부팅·재진입이 필요할 수 있다.
현재 코드에는 실제 handoff 실행 경로가 없고 `deployment_ready=false`를 유지한다.

## 실측 CPU capacity 연결

수동 Linux 커널 시험에서 얻은 8개 CPU의 16K·PA 폭·cache line 관측을
해시로 묶어 보드 컴파일과 실제 XNU 진입 코드의 TCR 대조에 사용했다.
[실행 결과·재현·한계](OBSERVED.md). RAM 예약이나 cache/MMU 전환 증거를 대신하지 않는다.
