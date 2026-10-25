# 실측 CPU 조건과 XNU 진입 코드 연결

2026-10-25 수동 Linux 진단 BOOT 시험의 `/proc/last_kmsg`에서 실제 실행 배너와
완결된 N10CAP1 기록을 확보했다. Linux는 실행됐으나 외부 TWRP initrd가 사용되지 않고
Android root로 들어갔고, zygote 반복 종료 후 bootchecker가 SysRq crash를 요청했다.
기존 BOOT 복구 뒤 5개 부팅 파티션이 원본과 일치했지만 Android 부팅 반복은 남았다.
사용자 지시에 따라 Android 복구 작업을 중단하고 XNU PC 작업을 계속한다.

## 확인한 범위

- CPU 8개 모두 Linux EL1 view에서 16K stage-1 granule 지원을 보고했다.
- PA 폭은 CPU 4/5가 44bit, 나머지가 40bit다. 현재 XNU bootstrap의 40bit IPS를 모두 수용한다.
- CTR의 I/D 최소 라인은 모두 64 bytes다. CCSIDR에서 CPU 6/7의 L1 I line은 128 bytes이며 관측된 최대값도 128 bytes다.
- CNTFRQ는 모두 26MHz다. 이는 앞서 관측한 Linux DT timer 선언과 수치가 일치한다.
- CPU 1/6의 MPIDR affinity 필드가 중복되며 raw MPIDR은 다르다. 자동 CPU topology나 PSCI ID를 생성하지 않는다.
- XNU 초기 `MAX_CPUS=1` 제한을 유지한다. CPU 8개를 관측했다는 이유로 SMP를 활성화하지 않는다.

이 정보는 Linux가 읽은 privileged register view다. bootloader 진입·post-shutdown 상태,
상위 EL trap 부재, 실제 캐시 종료, MMU 전환, GIC 소유권을 검증한 결과가 아니다.

## 입력 생성·컴파일

`observed_profile.py`는 원본 로그를 엄격 decoder로 다시 해석한다. CPU 누락·16K 미지원·
40bit 미달·중복 raw MPIDR·서로 다른 timer/CTR 값 등을 거부하고, 원본 경로/SHA-256과
생성 헤더를 묶는다. 이후 로드 시 로그 해시·재생성 결과·헤더 바이트를 다시 대조한다.
로그 해시는 내용 연결의 증거이며 기기 암호학적 attestation은 아니다.

생성한 정의:

```c
#define N10_BOARD_SCHEMA 1
#define N10_ICACHE_LINE_LOG2 6
#define N10_DCACHE_LINE_LOG2 6
#define N10_MAX_CACHE_LINE_LOG2 7
#define N10_KERNEL_PAGE_SHIFT 14
```

기존 실험 빌드에 사용한 합성 입력과 **수치가 일치한다**. 기존 전체 XNU 실행형의
build manifest를 실측 전체 빌드로 바꾸지는 않는다.

`compile_observed_board.py`는 해시로 검증한 실제 patched XNU headers와 bootstrap/IRQ
C 파일을 이 헤더로 컴파일했다. assert 객체 1개·플랫폼 객체 2개가 통과했고 플랫폼
객체에는 vector/FP 레지스터가 없다. 공개 XNU source commit은
`ac9718fb1af618d5ce8678d0dc6e8a58f252216f`다.
의존성 진단용 VMAPPLE generated headers를 사용하므로 완전한 Exynos 구성 또는 전체 커널 빌드가 아니다.

```text
python note10/xnu26/observed_profile.py --log RAW_CAPTURE --output PRIVATE_OUTPUT
python note10/xnu26/compile_observed_board.py PRIVATE_OUTPUT/observed-profile.json
python note10/xnu26/test_observed_profile.py
```

6개 PC 시험에는 지원 불일치·기록 누락·affinity alias 처리·TCR 주소 폭/페이지 불일치·
원본 로그/생성 헤더 변조·private 출력 경로/덮어쓰기 거부 사례가 포함된다.
시험 fixture는 합성이며 실측 로그를 CI에 전송하지 않는다.

## 실제 XNU 명령과 대조

`test_linked_entry.py --observed-profile PATH`는 실제 링크 실행형과 전달 adapter의
명령을 기존 합성 RAM 두 배치에서 각각 24,999개 실행했다. 실제 코드가 설정한
`TCR_EL1=0x226511a511`의 양쪽 granule 16K와 IPS 40bit가 관측된 CPU 제약에 맞았다.
부팅 인자·테이블 store·전체 세그먼트 끝점 검사도 유지했다.

```text
python note10/xnu26/test_linked_entry.py NATIVE_BUILD --adapter TRANSFER_ELF --observed-profile PROFILE_JSON
```

명령 모델은 여전히 합성 EL1/cache/TLB/RAM이고 **MMU 활성화 직전**에 멈춘다.
관측값으로 실제 캐시 상태나 사용 가능한 RAM을 대신하지 않는다. 실측 capacity gate는
지원 여부 비교만 추가하며 명령 모델의 레지스터 값을 실기기 상태로 취급하지 않는다.

XNU 메모리 예약·Linux 종료/CPU 정지·캐시/MMU 전환·GIC handoff·실제 로그 회수 경로는
미완료다. XNU 실기기 실행·설치 가능한 iOS ROM은 아직 없다. `deployment_ready=false`를 유지한다.
