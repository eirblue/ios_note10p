# 작업 상태 (2026-10-31, Asia/Seoul)

## 2026-10-31: v63 SHA-256 제공자 객체·실제 헤더 레이아웃 정적 검증 통과

- **검증 소스:** `fc15da51e2295022796eb44779a1eb8008450b65`; [CI 41199181822](https://github.com/eirblue/ios_note10p/actions/runs/41199181822), 시도 1 통과. 부모 독립 판독기가 실제 API·원본 ZIP·1,216개 파일·원본 의존성·객체 증거를 결속했다.
- **새 범위:** 실제 `crypto/sha256_generic.o`와 같은 Kbuild 헤더·설정의 읽기 전용 레이아웃 오라클. 필수 DWARF 크기·멤버·오프셋을 유지하고, 빠진 정렬 정보만 실제 헤더 컴파일 값으로 보완·출처 표시했다. 등록 테이블 2개·콜백 재배치·initcall·9개 함수의 GPR 명령어 1,753개를 확인했다.
- 범위 내 함수 프레임 합계 576바이트는 전체 호출 경로 상한이 아니다. 외부 crypto core·메모리 함수와 실제 초기화 순서·실행 가능성은 미확정이다. 새 시험 기록은 CP1 29개, CP3 19개, CP4 3개로 각각 보존; CP4의 2개 링크 거부 시험은 합성 메타데이터이며 실제 OS 링크 생성 검증이 아니다. 기존 통과 시험 재실행·최종 CI 시험 호출 0회.
- v63 기기·BOOT·재부팅·Image·제공자 실행 0회. 첫 CI 41195005405와 로컬 판독 전 접근 오류 기록은 보존했다. [결과와 제한](xnu26/RUNTIME-RELOCATION.md).

## 2026-10-31: v62 전체 진단 TU 전 PM 경로의 정적 검증 통과

- **검증 소스:** `f4dd45ff040df1a6c67b4390d17046dc6970d921`; [CI 41189249719](https://github.com/eirblue/ios_note10p/actions/runs/41189249719) 첫 번째 시도 통과. 부모 독립 판독기가 실제 API·원본 ZIP·실제 객체·의존성 바이트와 공유 원본 입력을 결속했다.
- **새 범위:** 전체 진단 `init.c`를 실제 커널 헤더·생성 설정·Kbuild로 기본 비활성/명시적 활성 컴파일했다. 전 PM 호출 순서와 실패 분기, 전체 prefix 원복·검사 호출의 인자·반환값을 실제 객체에 결속했다. 새 명령어 검사에서 50개 word 필드를 확인했다. 래퍼는 실행하지 않았다.
- **새 입력 계약:** 원본 ZIP 23,625,005바이트·2,173개 항목을 보존했다. 완전한 원본 커널 압축파일은 SHA로 고정된 공유 입력으로 보존하고 모든 실제 원본 의존성 바이트를 독립 비교했다. 새 계약 합성 검사 18개 통과; 최종 CI의 기존 시험 호출은 0회다. 앞선 통과 기록은 원래 소스·체크포인트에 결속해 보존한다.
- v62 기기·BOOT·재부팅·Image 작업은 0회다. 외부 커널·IRQ 전체 스택, 실행 시간·회복 작업 경쟁·DMA·backup 손상 안전성은 미확정이다. CI 41183097021·41186369912는 실패로 보존하며 v57 단일 실기기 회차 소진 상태를 유지한다. [결과와 제한](xnu26/RUNTIME-RELOCATION.md).

## 2026-10-31: v61 실제 커널 TU 구성요소의 PC 실행 검증 통과

- **검증 소스:** `557fa38b7ec52eb1a563860172f00e1125b60339`; [CI 41176433103](https://github.com/eirblue/ios_note10p/actions/runs/41176433103) 첫 번째 시도 통과. 부모 독립 판독기가 실제 API·전체 산출물·소스·커널 객체·재배치·관측 바이트 결속을 확인했다.
- **실제 TU 범위:** 고정된 reservation-only `arch/arm64/mm/init.c`를 실제 커널 헤더·설정·Kbuild로 기본 비활성/활성 빌드했다. 기존 production C/H와 ABI는 유지하고, 부팅 경로에서 호출되지 않는 어댑터·닫힌 구성요소를 실제 `init.o`에서 추출해 PC 모델에서만 실행했다. 독립 재컴파일이나 OS provider stub은 사용하지 않았다.
- **결과:** 새 경계 검사 57개와 실제 객체 기반 PC 실행 4개 통과. 정적 GPR 명령 918개, 전체 prefix 원복·ABI·guard·모델 CPACR 0 조건을 확인했다. 컴파일러 프레임의 구성요소 추정은 모델 leaf 1,440바이트, 거절 깊이 프레임을 포함한 일반 ADT 6,192바이트이며 실제 `THREAD_SIZE`는 16,384바이트다.
- **분석 계측:** 함수/데이터 section·stack-usage·machine-outliner 비활성 옵션과 LLD14 `-O0`을 명시했다. 공유 읽기 전용 문자열 풀 1,217바이트 전체를 원본과 동일하게 보존하며 사용되지 않는 Linux 문자열도 포함함을 기록했다. 일반 production Image 명령이나 전체 OS/IRQ 스택 안전성의 증거는 아니다.
- v61 기기·BOOT·Image 작업은 0회다. 앞선 CI 41174341105·41175122836은 실패로 보존했다. v57 단일 실기기 회차 소진 상태를 유지하며 실제 예약 RAM 쓰기·XNU 실행·iOS 부팅을 주장하지 않는다. [결과와 제한](xnu26/RUNTIME-RELOCATION.md).

## 2026-10-31: v60 커널 옵션 일부의 GPR 전용 PC 실행 검증 통과

- **검증 소스:** `d5b56efa5b7d9f0313fb72639db332c581e7e6b2`; [CI 41168995359](https://github.com/eirblue/ios_note10p/actions/runs/41168995359) 첫 번째 시도 통과. 실제 API·전체 산출물·소스·입력·옵션·ABI·관찰 바이트 결속을 부모 검사기로 확인했다.
- **새 PC 범위:** 기존 production C/H를 유지하고, 보존된 v57 실제 컴파일 명령에서 선택한 `-Oz`·`-mno-implicit-float` 등 옵션 일부로 새 AArch64 ELF를 만들었다. 프로필/GPR 검사 17개와 새 프로필 대상 실행 4개가 통과했다. 실제 CI 정적 명령어 1,270개에서 FP/SIMD 명령·레지스터를 사용하지 않음을 확인했다. 이는 동적 실행 명령 수가 아니다.
- **실행 증거:** 모델 `CPACR_EL1`을 0으로 설정하고 네 경우 모두 실행 전후 0 readback을 확인했다. 정상·불일치 주입의 전체 원복, 용량·alias 거절, 기존 ABI·guard·메모리 분리 조건을 유지했다. 기본 v59 경로는 AST 비교로 보존했으며 이전 통과 시험 묶음을 로컬에서 반복하지 않았다.
- v60 기기·BOOT·Linux Image 작업은 0회다. 실제 Linux header/TU 통합, 실기기 EL1/FPU 준비, FP trap 동작 또는 x18 고정 여부를 증명하지 않는다. 현재 실기기 결과는 소진된 v57 단일 회차이며 XNU 실행·iOS 부팅은 없었다. [결과와 제한](xnu26/RUNTIME-RELOCATION.md).

## 2026-10-31: v59 비계측 AArch64 재배치·원복 PC 실행 검증 통과

- **검증 소스:** `5c3ca5f5a3b21af725701df16e057a485d9add76`; [CI 41167139172](https://github.com/eirblue/ios_note10p/actions/runs/41167139172) 첫 번째 시도 통과. 실제 실행·단계·산출물 digest·전체 파일·소스·입력·관찰 바이트 결속을 부모 검사기로 확인했다.
- **PC 실행:** 기존 production C/H를 바꾸거나 fixture observer를 넣지 않은 AArch64 ELF를 Unicorn 2.1.4에서 실행했다. 실제 payload 정상 이동·불일치 주입 뒤 전체 원복·backup 용량 거절·버퍼 alias 거절의 4개가 통과했다. 메타데이터 검사 8개와 명령어 결속 검사 6개도 통과했다.
- **증거 범위:** `0x1004000` 목적지의 실제 payload와 `0x22b0000` 전체 prefix·backup·guard를 독립 바이트 대조했다. target ABI·12개 인수·복귀 PC·SP·callee-saved 레지스터를 확인했다. FP/AdvSIMD는 PC 모델의 명시적 가정이다.
- v59 기기·BOOT·Linux Image 작업은 0회다. v57 단일 회차 소진 상태를 유지한다. 이전 통과 미변경 시험 묶음은 로컬에서 반복하지 않았다. 앞선 CI 41166367312는 최종 명령어 결속 오류로 실패한 이력을 보존했다. 물리 RAM 소유권·실기기 EL1 준비·XNU 실행·iOS 부팅을 확인한 결과는 아니다. [결과와 제한](xnu26/RUNTIME-RELOCATION.md).

## 2026-10-31: v58 PC 전용 payload 겹침 재배치·원복 검증 통과

- **검증 소스:** `12549ffe88438aa583690da744b9a8d035d84019`; [CI 41161078327](https://github.com/eirblue/ios_note10p/actions/runs/41161078327) 첫 번째 시도 통과. 실제 산출물의 원본 입력·소스·컴파일·검사 기록·전체 바이트를 고정한 부모 검사기가 통과했다.
- **PC 결과:** 새 네이티브 48개와 명령어 분류 39개가 통과했다. 실제 19,578,880바이트 payload를 모델 버퍼의 offset 0에서 planner가 계산한 `0x1004000`으로 겹침을 처리해 복사하고, 변경 영역 `0x22b0000`바이트 전체를 원복했다. 정상·주입 불일치 경로 모두 독립 snapshot과 바이트 대조를 통과했다.
- **코드 생성:** 별도 비계측 AArch64 object를 기존 planner와 결합해 미해결 호출·쓰기 가능한 전역 상태·금지된 시스템/명시적 trap 명령 부재를 확인했다. 이 AArch64 object를 실행한 결과는 아니다.
- v58 기기 조작·BOOT·Linux Image 빌드는 0회다. v57 실기기 46/46 성공과 이전 이력을 유지한다. 실패 CI 41160322285도 실패로 보존했으며 이전 entry·VM·seed 시험 묶음을 로컬에서 반복하지 않았다. 실제 예약 RAM 재배치·소유권·XNU 실행·iOS 부팅을 확인하지 않는다. [결과와 제한](xnu26/RUNTIME-RELOCATION.md).

## 2026-10-31: v57 caller-owned scratch 직렬화 단일 실기기 검증 통과

- **검증 소스:** `5afedf0bd305861b1b98e7b975ad9a6405d38b6a`; [CI 41109866784](https://github.com/eirblue/ios_note10p/actions/runs/41109866784) 첫 번째 시도 통과. 실제 manifest의 고유 검증기 28개·호출 129회, 실제 CI 단계 완료 기록과 산출물 digest를 결속했다. 결과 문서 게시 commit은 검증 소스와 별도다.
- **실기기 결과:** 새 단일 회차 1회에서 총 47개 중 필수 46개 모두 통과. v56의 필수 45개를 유지하고 `xnu_runtime_scratch`를 추가했다. 정상 TWRP 자동 복귀, 다섯 파티션 해시 일치, 복귀 무결성 확인 뒤 밝기 raw 10을 확인했다. 설치 직전 배터리는 29%였다.
- **새 관측 범위:** 전용 `__initdata` 버퍼에 boot_args 1152바이트·record 64바이트·합성 ADT 56바이트를 만들고 바이트와 canary를 대조했다. 같은 부팅에 결속된 checksummed `N10XSO1` 두 copy가 일치했으며 `scratch_materialized=1`, `reserved_materialized=0`, `ownership=0`, `executed=0`이다. 기존 `N10XPO1` 관측과 PM 판정은 유지한다.
- **스택 증거 한계:** 컴파일러 추정 7,840바이트와 16,384바이트 task stack의 차이는 8,544바이트다. 외부 경로 2,048바이트는 가정이며 전체 OS 스택 안전성의 측정·증명이 아니다.
- 앞선 실패 CI 41090887005·41097401475·41101985523과 v56 이전 이력을 보존했다. 이전 journal은 재실행하지 않았다. 새 예약 RAM metadata 설치·XNU 실행·iOS 부팅은 없었다. [결과와 제한](device_test/XNU-RUNTIME-OBSERVATION.md).

## 2026-10-31: v56 late-init XNU runtime plan 단일 실기기 관측 통과

- **검증 소스:** `e4e662059413fc1157df0587e4b088f762b0621f`; [CI 41075142026](https://github.com/eirblue/ios_note10p/actions/runs/41075142026) 첫 번째 시도 통과. 실제 실행 manifest의 고유 검증기 27개·호출 128회와 native 8개·parser 24개·preparer 18개·package 22개 증거를 결속했다. 이 소스 식별자는 결과 문서의 게시 commit과 구분한다.
- **실기기 결과:** 새 단일 사이클 1회에서 총 46개 중 필수 45개가 모두 통과했다. 기존 필수 44개를 유지하고 `xnu_runtime_plan` 행을 추가했다. 정상 TWRP 자동 복귀, 다섯 파티션 해시 일치, 무결성 확인 뒤 밝기 raw 10을 확인했다.
- **새 관측 범위:** 같은 부팅·build에 결속된 checksummed `N10XPO1` 두 copy가 일치했다. 자체 `plan_generation=1`, `phase=late-init`, `pm_completion_claimed=0`, `synthetic=1/materialized=0/ownership=0`이며 PM 완료 증거는 기존 독립 행에 남는다.
- 실패한 CI 41066125298·41067698092와 취소한 CI 41072098813을 보존했다. 준비·fixture 오류를 수정한 뒤 위 CI와 실기기 결과를 별도로 수락했다. v53·v54·v55 및 이전 실패 이력도 보존한다.
- 새 RAM layout이나 metadata를 설치하지 않았다. 기존 kernel-at-base writer는 유지하며 새 계획은 가상 배치 계산이다. XNU 실행·iOS 부팅·전역 DMA 정지·물리 소유권으로 확대하지 않는다. [결과와 제한](device_test/XNU-RUNTIME-OBSERVATION.md).

## 2026-10-30: v55 XNU runtime planner 커널 컴포넌트 PC 검증 통과

- **검증 소스:** `9cb92b1d68bf2d80fc3a5f5cbde62193c75715f9`; [CI 41058332903](https://github.com/eirblue/ios_note10p/actions/runs/41058332903) 첫 번째 시도 통과. 실제 고정 Linux 헤더로 분리된 disabled/enabled `arch/arm64/mm/init.o`를 모두 컴파일·보존한 뒤 증거 gate를 적용했다. 11개 소스와 1,506개 proof-file 해시를 결속했다.
- **결속 결과:** 두 모드의 의존성은 각각 730·735개다. 실제 타입 헤더의 기존 stdint 별칭, enabled wrapper→`n10_rt_plan` CALL26, disabled의 새 심볼·marker·의존성 부재와 canonical 예약 전용 소스의 byte identity를 확인했다.
- **범위 내 시험:** host wrapper 32개·frame 변조 3개·preparer/manifest 17개·dependency 36개가 통과했으며 대응하는 로컬 저장 증거도 통과했다. host wrapper는 planner stub을 사용하고 실제 커널 object는 실행하지 않았다. 로컬에서 기존 v54·PM 시험 묶음은 반복하지 않았다.
- 실패한 [CI 41055821209](https://github.com/eirblue/ios_note10p/actions/runs/41055821209)의 마지막 continuation 처리 오류와 [CI 41056966619](https://github.com/eirblue/ios_note10p/actions/runs/41056966619)의 별도 `source_` assignment 누락을 보존했다. 전체 logical line을 먼저 복원하고 동일 object의 primary source를 별도로 결속하도록 수정했으며 proof bytes는 gate 전에 보존한다.
- 판정은 **actual-kernel object integration plus host-wrapper evidence**다. 전체 Image·BOOT·minimal-init·CPIO·기기 조작·예약 RAM materialization은 없으며 물리 소유권·GIC·전체 DMA 정지·XNU 실행·iOS 부팅의 증거로 확대하지 않는다. v54와 기존 이력을 보존한다. [결과와 제한](device_test/XNU-RUNTIME-PLAN.md).

## 2026-10-30: v54 네이티브 런타임 재배치 PC 검증 통과

- **검증 소스:** `78797cb2e37e97d99463217f5418740a5ed76141`; [CI 41050904567](https://github.com/eirblue/ios_note10p/actions/runs/41050904567) 첫 번째 시도 통과. 결과의 13개 소스 해시를 결속했다. freestanding C planner·1152바이트 boot_args·64바이트 N10XFER1이 만든 metadata를 실제 4-buffer PC bundle에 직접 사용했다.
- **PC 결과:** 새 native 48개와 bundle 변조 거부 6개가 통과했다. 실제 XNU·adapter의 새 모델 1건은 24,839개 명령을 거쳐 MMU 활성화 직전에 멈췄고 DAIF는 `0x3c0`이었다. 기존 entry·VM·seed·PM 시험 묶음은 반복하지 않았다.
- **ABI·코드 생성:** 13개 offset과 전체 1152바이트를 비교했다. 로컬에서는 보존한 실제 헤더 oracle object와도 일치했으며 해당 oracle을 재컴파일하지 않았다. 새 ARM64 object에서 미해결 심볼·쓰기 가능한 전역 상태·특권 명령이 없음을 확인했다.
- 실패한 [CI 41050510506](https://github.com/eirblue/ios_note10p/actions/runs/41050510506)은 보존했다. 모듈의 내부 버전과 배포 패키지 버전을 혼동한 gate를 설치 metadata 기반 조기 검사로 수정했고, 패키지 pin은 유지했다.
- v54 기기 조작은 0회다. 합성 RAM·ADT의 PC 검증이며 물리 소유권·GIC 인계·전체 DMA 정지·폰 XNU 실행·iOS 부팅을 확인하지 않는다. v53 실기기 성공과 이전 이력은 보존한다. [검증 결과와 범위](xnu26/RUNTIME-RELOCATION.md).

## 2026-10-30: v53 CPU_PM dispatch 순서 관측과 단일 실기기 진단 통과

- **검증 소스:** `9c8410fac2fcca8cd7aeddb1ef79f5582c0a626f`; [CI 41010158045](https://github.com/eirblue/ios_note10p/actions/runs/41010158045) 통과. 실제 산출물의 manifest에서 26개 고유 결속 검증, 기존 직접 호출 36회와 중첩을 포함한 실제 호출 127회를 확인했다. trace native 22개·parser 24개·package 22개 증거가 결속됐다.
- **실기기 결과:** 단일 사이클 1회에서 총 45개 평가 중 필수 44개가 모두 통과했다. 기존 원본 CPU_PM enter/exit 쌍 1회에서 ENTER와 명시적 EXIT 모두 승인된 block 1→2→3→4→5→6의 진입·반환 순서와 집계 6+6을 확인했다.
- **복귀·무결성:** 정상 TWRP 자동 복귀, 다섯 파티션 해시 일치, 무결성 확인 뒤 밝기 raw 10을 확인했다. 설치 직전 배터리는 23%였다. 앞선 배터리 0% 중단 당시 설치·재부팅은 없었고, 해당 기록을 보존한 뒤 새 실기기 사이클은 1회만 수행했다.
- 실패한 CI 41002376625·41005053470·41008544786과 v49·v50 실패 결과는 보존했으며 이전 journal을 재실행하지 않았다.
- 관측은 notifier-block 경계의 식별·순서와 별도로 읽은 callback 필드의 승인 snapshot 일치에 한정된다. 해당 필드 읽기가 실제 간접 호출 명령의 target과 같았다는 증거, 전체 DMA 정지, XNU 실행 또는 iOS 부팅으로 확대하지 않는다. [관측 범위와 결과](device_test/CPU-PM-ROUNDTRIP.md).

## 2026-10-30: v52 CPU_PM notifier 집계와 단일 실기기 진단 통과

- **검증 소스:** `0d7bf9ed8f1d7d51587123b8c8d9bb9817999dc6`; [CI 40996078899](https://github.com/eirblue/ios_note10p/actions/runs/40996078899) 통과. 실제 산출물의 26개 결속과 notifier 집계 기능을 확인했다.
- **실기기 결과:** 새 계획과 journal의 단일 사이클 1회에서 총 44개 평가 중 필수 43개가 모두 통과했다. strict CPU_PM 쌍과 같은 transaction에 결속된 companion에서 ENTER 반환 6개와 명시적 EXIT 반환 6개를 집계했다.
- **복귀·무결성:** 정상 TWRP 자동 복귀, 다섯 파티션 해시 일치, 무결성 확인 뒤 밝기 raw 10을 확인했다.
- v49·v50 실패 기록과 v51 통과 기록은 보존하고 이전 journal을 재실행하지 않았다. 집계는 callback별 실행 식별·순서, 전체 DMA 정지, XNU 실행 또는 iOS 부팅을 증명하지 않는다. [관측 범위와 결과](device_test/CPU-PM-ROUNDTRIP.md).

## 2026-10-30: v51 CPU_PM 세대 결속 수정과 단일 실기기 진단 통과

- **검증 소스:** `bbf3b4bd8167cbbe103266d2da6809de4a9f8d3b`; [CI 40979304539](https://github.com/eirblue/ios_note10p/actions/runs/40979304539) 통과. 실제 산출물의 26개 결속과 새 collector 집중 증거를 확인했다. 기존 native·decoder 증거 바이트는 재사용했으며 이전 모델을 로컬에서 다시 돌리지 않았다.
- **실기기 결과:** 새 계획과 journal로 단일 사이클 1회를 수행했다. 필수 42개 평가가 모두 통과했고 CPU_PM 쌍은 strict generation 결속을 통과했다. 정상 TWRP 자동 복귀, 다섯 파티션 해시, 복귀 확인 후 밝기 raw 10을 확인했다. 설치 직전 배터리는 39%였다.
- **결과 증거:** 저장된 `RESULT.json`의 `source_commit`은 위 검증 소스 커밋이며 상태는 `single physical diagnostic passed`다. 결과 파일 SHA-256은 `20ea4047b6bf773143043ebb45049241c189e179948dd1c6651ae9ae2bed2c52`. 결과 증거는 소스 커밋과 구분되는 산출물이며 별도의 소스 커밋으로 표시하지 않는다.
- v50의 41/42 실패 기록과 journal은 그대로 보존했고 재실행하지 않았다. 이 결과는 callback별 runtime trace, 전체 DMA 정지, XNU 실행 또는 iOS 부팅을 확인하지 않는다.
- 수정 원인과 세대 변환 계약: [CPU-PM 왕복 진단](device_test/CPU-PM-ROUNDTRIP.md).

## 2026-10-30: v50 CPU_PM 세대 결속 수정 제안

- 소스 `d37a8677fa4f1187dfd740c56ea9eb951f0df955`의 [CI 40972669928](https://github.com/eirblue/ios_note10p/actions/runs/40972669928)가 통과했고 실제 산출물 26개 결속을 확인했다.
- 단일 v50 실기기 진단은 실패로 기록됐다. 필수 42개 평가 중 41개 통과, CPU_PM enter/exit 쌍 평가 1개는 collector 세대 결속 오류로 실패 유지.
- 저장된 pair 기록의 transaction generation은 producer 계약상 완료된 quiescence generation의 선행값이다. v50 collector가 완료값을 strict decoder에 직접 전달해 거부했다.
- v51에서는 collector만 uint32 완료값을 선행 세대로 변환한다. producer와 strict decoder는 유지한다. 성공/terminal 경로, wraparound, 잘못된 입력, 오래된 세대, ID·checksum 거부를 새 집중 시험으로 확인했고, 저장된 v50 로그는 오프라인에서만 재해석했다.
- v50 실패 기록은 변경하지 않으며 v51에서 재실행하지 않았다. 당시 검증 결과와 후속 v51 단일 진단은 위 항목에 기록했다. XNU 실행과 전체 DMA 정지는 확인되지 않았다.
- 상세 범위와 한계: [CPU-PM 왕복 진단](device_test/CPU-PM-ROUNDTRIP.md).

## 2026-10-30: v49 빌드 성공·실기기 PM 단계 실패

- 소스 `7111e3d2d65675365b6784710c6a9a43c93ea3b3`의 [CI 40947448390](https://github.com/eirblue/ios_note10p/actions/runs/40947448390)가 통과했다. 실제 산출물의 26개 결속을 확인했다. [CPU_PM 시험 범위](device_test/CPU-PM-ROUNDTRIP.md).
- 새 실기기 시험은 1회만 수행했다. 장치 PM 반환 단계에서 오류 `+1`을 관측해 중단했으며, CPU_PM enter/exit 쌍의 실행 기록은 없었다. 상위 샘플 읽기 실패 시 새 행의 출력도 생략되므로, 실제 호출 여부는 미확정이다. 필수 42개 중 6개가 통과했고, PM 이후 관측이 확인되지 않은 36개는 실패로 유지했다.
- 자동 TWRP 복귀와 동일 기기의 복귀 후 다섯 파티션 무결성을 확인했다. 설치 직전 배터리는 72%였으며, 무결성 확인 뒤 TWRP와 패널 raw 밝기를 10으로 확인했다. 같은 시험 기록은 재실행하지 않는다.
- 이 결과는 CPU_PM 쌍 실행, 전체 하드웨어 복원, XNU 실행 또는 iOS 부팅을 증명하지 않는다. 다음 수정은 저장된 PM 실패 지점 분석에 한정한다.


## 2026-10-30: v48 EHLD 관측 잠금 경합 생략과 실기기 회귀 통과

- 기본 비활성 옵션 v2에서 EHLD updater의 main/ctrl 및 dumper의 main lock을 한 번만 trylock한다. 경합 시 관측을 생략하며 이전 ring 값이 남을 수 있다. [수정 범위와 한계](device_test/EHLD-RUNNING-LOCK-AUDIT.md).
- 소스 `dd7dc575c4f871ddfc309ddeb51b6118325db5fa`의 [CI 40916389727](https://github.com/eirblue/ios_note10p/actions/runs/40916389727)가 통과했다. 25개 결속 검증의 CI 성공을 확인하고, 로컬에서는 수정·직접 영향 범위만 확인했다.
- 단일 실기기 시험 1회에서 기존 42개 평가의 필수 41개가 통과했다. 자동 TWRP 복귀·복귀 후 다섯 파티션 무결성을 확인했고, 확인 뒤 TWRP와 패널 raw 밝기를 시험 전후 모두 10으로 설정·확인했다. 설치 직전 배터리는 90%였다.
- 새 하드웨어 관측 행이나 직접 CPU-PM 호출은 추가하지 않았다. 경합 분기는 PC 모델로 확인했으며 실기기에서 panic·hardlockup·경합을 유발하지 않았다. 이 결과는 NMI 안전성, 전체 하드웨어 복원, XNU 실행 또는 iOS 부팅을 증명하지 않는다.

## 2026-10-30: v47 EHLD start/stop 상태 동기화와 실기기 회귀 통과

- 기본 비활성 옵션으로 EHLD start/stop의 두 상태 저장을 ctrl lock으로 보호했다. 이벤트 수명·준비 상태나 기존 비잠금 샘플의 원자성을 보장하지 않는다. [수정 범위와 한계](device_test/EHLD-RUNNING-LOCK-AUDIT.md).
- 소스 `f3fc2dee32602eefc2f90cb42e8fb9a42a5a200e`의 [CI 40903680433](https://github.com/eirblue/ios_note10p/actions/runs/40903680433)가 통과했다. 새 결속을 포함한 25개 검증의 CI 성공을 확인하고, 로컬에서는 수정·직접 영향 범위만 확인했다.
- 단일 실기기 시험 1회에서 기존 42개 평가의 필수 41개가 통과했다. 자동 TWRP 복귀·복귀 후 다섯 파티션 무결성을 확인했고, 확인 뒤 TWRP와 패널 raw 밝기를 시험 전후 모두 10으로 설정·확인했다. 설치 직전 배터리는 96%였다.
- 새 하드웨어 관측 행이나 직접 CPU-PM 호출은 추가하지 않았다. 이 회귀 결과는 이벤트 수명, NMI 안전성, 전체 하드웨어 복원, XNU 실행 또는 iOS 부팅을 증명하지 않는다.


## 2026-10-29: v46 EHLD irqsave 토큰 분리와 실기기 회귀 통과

- 기본 비활성 옵션으로 EHLD updater의 바깥 main lock과 안쪽 ctrl lock에 별도 irqsave 토큰을 사용하도록 했다. [수정 범위와 한계](device_test/EHLD-IRQSAVE-AUDIT.md).
- 소스 `0188d99a5b958789cf0790a410800db9911b2879`의 [CI 40883405339](https://github.com/eirblue/ios_note10p/actions/runs/40883405339)가 통과했다. 실제 커널 산출물에 대해 기존 23개와 새 irqsave 결속을 합친 24개 검증을 확인했다.
- 단일 실기기 시험 1회에서 기존 42개 평가의 필수 41개가 통과했다. 자동 TWRP 복귀와 복귀 후 다섯 파티션 무결성을 확인했고, 확인 뒤 TWRP와 패널 raw 밝기를 시험 전후 모두 10으로 설정·확인했다. 설치 직전 배터리는 93%였다.
- 새 하드웨어 관측 행은 추가하지 않았다. 알려진 IRQ 비활성 호출 경로에 대한 회귀 시험이며 IRQ 활성 하드웨어 도달성, event 수명, 전체 하드웨어 복원, XNU 실행 또는 iOS 부팅을 증명하지 않는다. 직접 CPU-PM 호출은 수행하지 않았다.

## 2026-10-29: v45 EHLD lock 관측과 실기기 회귀 통과

- 기본 비활성 EHLD lock 관측을 기존 CPU0 notifier 경로에 추가했다. [관측 범위와 한계](device_test/EHLD-LOCK-AUDIT.md).
- v45 커널 빌드와 단일 실기기 시험 1회가 완료됐다. 42개 평가에서 필수 41개를 통과했고, 자동 TWRP 복귀와 복귀 후 다섯 파티션 무결성 검사를 확인했다.
- 무결성 확인 뒤 TWRP와 패널 raw 밝기를 시험 전후 모두 10으로 확인했다. 직접 CPU-PM 호출이나 시험 중 instrumentation profile 동적 변경은 없었다.
- 이 관측은 readiness, 완전한 하드웨어 복원, XNU 실행 또는 iOS 부팅을 증명하지 않는다.

## 2026-10-29: v44 RCU 실행 문맥 관측과 단일 실기기 회귀 통과

- 기본 비활성 RCU 문맥 감사를 추가해 기존 CPU0 notifier 관측 경로에서 RAM 전용 소프트웨어 상태를 제한적으로 읽는다. [관측 범위와 한계](device_test/RCU-CONTEXT-AUDIT.md).
- 소스 `86e6f9c76fc1e156653fb66e621a873126a15b37`의 [CI 40775233439](https://github.com/eirblue/ios_note10p/actions/runs/40775233439)가 통과했다.
- 단일 실기기 시험 1회에서 41개 평가가 모두 통과했고, 자동 TWRP 복귀와 사후 5개 파티션 해시 검증을 확인했다. 설치 전 배터리는 41%였으며, pre/post 무결성 확인 뒤 TWRP와 패널 raw 밝기를 10으로 확인했다.
- 이 감사는 RAM 전용 관측이며 직접 CPU-PM 호출을 하지 않는다. 개별 필드 읽기는 원자적 스냅샷이 아니며 readiness, 완전한 하드웨어 복원, XNU 실행 또는 iOS 부팅을 증명하지 않는다.

## 2026-10-29: v43 FPSIMD 참조 관측과 실기기 회귀 통과

- 기존 단일 CPU0 관측 경로에 기본 비활성 FPSIMD 참조 감사를 추가했다. 소프트웨어 참조의 의미와 관측 범위는 [FPSIMD-REFERENCE-AUDIT.md](device_test/FPSIMD-REFERENCE-AUDIT.md)에 기록했다.
- 소스 `cb568978e3fcb173593e8f3f705688ca32f36a30`의 [CI 40769141674](https://github.com/eirblue/ios_note10p/actions/runs/40769141674)가 통과했다. 실제 준비 소스와 PC 합성 모델을 포함한 21개 결속을 확인했다.
- 실기기 단일 시험에서 40개 평가 전부, 자동 TWRP 복귀와 사후 5개 파티션 해시가 통과했다. 설치 직전 배터리는 47%였고 복귀 후 TWRP와 패널 밝기 설정값은 각각 raw 10으로 확인했다.
- 관측은 소프트웨어 참조 분류이며 FP 레지스터의 소유나 완전한 보존을 증명하지 않는다. 직접 CPU-PM 호출, 전체 DMA 정지, XNU 실행과 iOS 부팅은 검증하지 않았다.

## 2026-10-29: v42 PMU 제어 상태 관측과 실기기 회귀 통과

- 기존 단일 CPU0 관측 경로에 기본 비활성 PMU 제어 상태 감사를 추가했다. 관측 범위와 접근 조건은 [PMU-CONTROL-AUDIT.md](device_test/PMU-CONTROL-AUDIT.md)에 기록했다.
- 소스 `ca2260145601a65cf82fd9177a2a702c0daafd5a`의 [CI 40760960052](https://github.com/eirblue/ios_note10p/actions/runs/40760960052)가 통과했다. 실제 준비 소스와 PC 합성 모델을 포함한 20개 결속을 확인했다.
- 실기기 단일 시험에서 39개 평가 전부, 자동 TWRP 복귀와 사후 5개 파티션 해시가 통과했다. 설치 직전 배터리는 52%였고 복귀 후 TWRP와 패널 밝기 설정값은 각각 raw 10으로 확인했다.
- 관측은 EL1에서 보이는 상태에 한정된다. 상위 EL 접근 환경은 가정이며 동기 레지스터 접근 예외는 포착하지 않는다. 직접 CPU-PM 호출, 전체 하드웨어 복원, XNU 실행과 iOS 부팅은 검증하지 않았다.

## 2026-10-29: v41 PMU 소프트웨어 상태 관측과 실기기 회귀 통과

- 기존 단일 CPU0 관측 경로에서 사용 중인 PMU 이벤트의 소유권·슬롯·소프트웨어 상태를 읽는 기본 비활성 감사를 추가했다. 실행 중·STOPPED·CPU affinity와 실제 실행 CPU를 구분하며, 범위는 [PMU-STATE-AUDIT.md](device_test/PMU-STATE-AUDIT.md)에 기록했다.
- 소스 `d4709039decdc1fea3f20fd2308eebf92a58422e`의 [CI 40752209407](https://github.com/eirblue/ios_note10p/actions/runs/40752209407)가 통과했다. 실제 준비 소스의 PC 모델, 결속 변조 13개와 새 패키지 흐름 4개를 포함해 19개 소스·설정·모델 결속을 확인했다.
- 실기기 단일 시험에서 기존 37개와 새 상태 관측을 합친 38개 평가, 자동 TWRP 복귀와 사후 5개 파티션 해시가 모두 통과했다. 설치 직전 배터리는 59%였고 복귀 후 TWRP와 패널 밝기 설정값은 각각 raw 10으로 확인했다.
- 소프트웨어 상태 관측은 실제 카운터 활성화나 CPU-PM 호출의 안전성을 증명하지 않는다. 직접 CPU-PM 호출, 하드웨어 복원 시험, XNU 실행과 iOS 부팅은 수행하지 않았다.

## 2026-10-29: v40 GIC 우선순위 복원 가드와 실기기 회귀 통과

- 단일 banked GIC를 대상으로 기본 비활성 우선순위 복원 가드를 추가했다. 지원 구성과 복원 범위는 [GIC-PRIORITY-RESTORE.md](device_test/GIC-PRIORITY-RESTORE.md)에 기록했다.
- 소스 `2f386b280a9603e2930baee614ae04b7c675f058`의 [CI 40743591525](https://github.com/eirblue/ios_note10p/actions/runs/40743591525)가 통과했다. PC 합성 모델에서 원본·가드 비활성·활성 각 18개 사례, 결합 변조 13개와 패키지 흐름 4개 사례가 통과했다.
- 실기기 단일 시험에서 기존 37개 평가 전부, 자동 TWRP 복귀와 사후 5개 파티션 해시가 통과했다. 설치 직전 배터리는 67%였고 복귀 후 TWRP와 패널 밝기 설정값은 각각 raw 10으로 확인했다.
- 가드가 포함된 이미지의 회귀 시험이며 실제 CPU-PM 호출이나 하드웨어 실패 주입을 수행하지 않았다. 합성 모델은 실제 GIC 하드웨어 복원을 증명하지 않으며 XNU 실행, iOS 부팅과 전체 DMA 정지도 검증하지 않았다.

## 2026-10-29: v39 PMU 실패 복구 가드와 실기기 회귀 통과

- 기본 비활성 PMU 실패 복구 가드를 추가했다. 실행 중이던 이벤트만 복구 대상으로 기억하며, 이미 중지된 이벤트의 상태를 보존한다. 지원 범위와 수명 조건은 [PMU-FAILURE-RESTORE.md](device_test/PMU-FAILURE-RESTORE.md)에 기록했다.
- 소스 `602c86d0eaf8537f2cc88e4ecd149ef37bafc3d6`의 [CI 40737446128](https://github.com/eirblue/ios_note10p/actions/runs/40737446128)이 통과했다. PC 합성 모델은 가드 비활성 8개·활성 15개 사례와 패키지 흐름 4개 사례를 통과했다.
- 실기기 단일 시험에서 기존 37개 평가 전부, 자동 TWRP 복귀와 사후 5개 파티션 해시가 통과했다. 설치 직전 배터리는 72%였고 복귀 후 TWRP와 패널 밝기 설정값은 각각 raw 10으로 확인했다.
- 가드가 포함된 이미지의 회귀 시험이며 실제 CPU-PM 호출이나 하드웨어 실패 주입을 수행하지 않았다. 합성 모델은 실제 PMU 하드웨어 복원을 증명하지 않으며 XNU 실행, iOS 부팅과 전체 DMA 정지도 검증하지 않았다.

## 2026-10-29: v38 CPU-PM 분기 사전관측과 실기기 회귀 통과

- 기본 비활성 분기 관측을 추가해 기존 35개 평가와 신규 2개 평가를 함께 수행했다. PMU와 EHLD의 소프트웨어 연관을 비교하고 기존 GIC 관측에서 우선순위 lane의 차이를 도출한다.
- 소스 `736e14c97b634ad2f88e30c272a7d122043587e3`의 [CI 40724867871](https://github.com/eirblue/ios_note10p/actions/runs/40724867871)이 통과했다. PC에서 준비 소스 결합과 집중 합성 모델을 검증했고, 실기기 단일 시험에서 37개 평가 전부, 자동 TWRP 복귀와 사후 5개 파티션 해시가 통과했다. 설치 직전 배터리는 81%였고 복귀 후 TWRP와 패널 밝기 설정값은 각각 raw 10으로 확인했다.
- 소프트웨어 연관과 GIC 우선순위 차이는 관찰이며 CPU-PM 실행이나 하드웨어 복원의 안전성을 증명하지 않는다. 실제 CPU-PM 호출, XNU 실행, iOS 부팅과 전체 DMA 정지는 검증하지 않았다. 상세 범위는 [PM-BRANCH-AUDIT.md](device_test/PM-BRANCH-AUDIT.md)에 기록했다.

## 2026-10-29: v37 CPU0 PM 사전조건 관측과 실기기 회귀 통과

- 기본 비활성 CPU0 PM 소프트웨어 상태와 GIC 복원 입력 관측을 기존 진단에 추가했다. 새 PM 또는 CPU hotplug 주기를 추가하지 않으며 기존 33개 평가에 2개를 더한다.
- 소스 `b7cf1afb8eb0b33d87805239cb3bf48b25e54e95`의 [CI 40716543231](https://github.com/eirblue/ios_note10p/actions/runs/40716543231)이 통과했다. 27개 준비 소스의 결합 검증과 합성 모델을 통과했으며, 실기기 단일 시험에서 35개 평가 전부, 자동 TWRP 복귀 및 사후 5개 파티션 해시가 통과했다. 설치 직전 배터리는 90%였다.
- GIC 복원 기본값 비교의 불일치는 관찰 결과이며 CPU-PM 실행 허가를 의미하지 않는다. 실제 CPU-PM 호출, XNU 실행, iOS 부팅과 전체 DMA 정지는 검증하지 않았다. 상세 범위는 [PM-PRECONDITIONS.md](device_test/PM-PRECONDITIONS.md)에 기록했다.

## 2026-10-28: noirq CPU 정지·복원과 PMU·타이머 통합 준비

- v31은 기존 19개 평가에 noirq CPU 정지·복원, CPU 정지 시점의 PMU 관측, 8개 CPU 복원 후 타이머 읽기를 함께 추가해 22개 평가를 준비한다. 기존 TEST_PLATFORM 가드 안에서 원본 CPU API를 반드시 짝지어 호출하고 0xff→0x01→0xff 마스크를 검사한다.
- 전체 회귀 272개, 실제 suspend·noirq·hotplug 통합 90개, CPU 정지 PMU 63개, 원본 hotplug 28개, 타이머 읽기 18개, 작업 큐 6개가 통과했다. v31 `102b674`, CI `40620987599`의 단일 실기기 시험도 22개 평가, 자동복귀와 5개 파티션 무결성을 통과했다.
- CPU 마스크 0xff→0x01→0xff, CPU0만 온라인인 시점의 16개 PMU 도메인 비트 0, 오류 0을 관측했다. 복원 후 8개 CPU 모두 타이머 제어값 0xb6와 주파수 26MHz가 원래 값과 일치했다. 이후 시간별 PMU 마스크는 0x4088이었다. 전체 DMA 정지·XNU 실행은 증명하지 않는다. [PM-CPUS-AUDIT.md](device_test/PM-CPUS-AUDIT.md)에 결과와 범위를 기록했다.

## 2026-10-28: 복원 뒤 시간별 PMU 관측 준비

- v30은 기존 18개 평가를 유지하고 PM 복원 후 1초·5초·15초 목표의 읽기 전용 PMU 관측을 추가한다. 복원 직후의 전부 켜진 도메인 상태가 이후에도 유지되는지 판별하며 새 전원 제어나 강제 workqueue flush는 추가하지 않는다.
- 전체 회귀 262개, 실제 PMU·소유권 경로 184개와 지연 worker 13개, 기존 noirq·PMU·FSYS 모델을 통과했다. v30 `3f166c7`, CI `40616077040`의 단일 실기기 시험도 19개 평가, 자동복귀와 5개 파티션 무결성을 통과했다.
- 복원 직후 `0xffff`였던 16개 도메인 마스크는 실제 1.024초·5.120초·15.104초에 모두 `0x4088`이었다. DPU·EMBEDDED_G3D·FSYS0A만 켜진 상태로 관측됐고 나머지 13개는 꺼져 있었다. 직후의 전부 켜진 상태는 이 시간별 관측까지 지속되지 않았다. noirq 시점 마스크는 계속 0이었다. 자세한 범위는 [PMU-SETTLE-AUDIT.md](device_test/PMU-SETTLE-AUDIT.md)에 기록했다.

## 2026-10-28: late/noirq 왕복과 PMU 관측 통합 준비

- v29는 기존 16개 평가에 late/noirq 진입·복원과 해당 시점의 16개 PMU 도메인 관측을 묶는다. 소유 진단만 TEST_PLATFORM까지 진행하고 CPU 비활성화·syscore·실제 절전 진입 전에 복귀한다.
- 전체 회귀 254개, 실제 suspend 호출자·진입 C 경로 45개, noirq PMU 63개, 기존 PMU 88개와 FSYS 콜백 24개를 통과했다. v29 `9ccbc05`, CI `40611852128`의 단일 실기기 시험도 18개 평가, 자동복귀와 5개 파티션 무결성을 통과했다.
- noirq 시점의 16개 도메인 제어·상태·재확인 값은 모두 0이었다. FSYS0A 원본 전원 끄기 콜백·USB 조건 허용·제어 호출이 각 1회, 오류는 0이었다. 복원 직후에는 16개 모두 1로 관측돼 이후 안정 시점의 읽기 전용 관측을 다음으로 검토한다. 전체 DMA 정지·XNU 실행은 증명하지 않는다. 자세한 범위는 [PM-NOIRQ-AUDIT.md](device_test/PM-NOIRQ-AUDIT.md)에 기록했다.

## 2026-10-28: FSYS0A 원본 전원 끄기 정책 통합 추적 준비

- v28은 기존 15개 평가를 유지하고 FSYS0A의 원래 조건 결과·생략·제어 결과와 콜백 진입/종료를 기록한다. 조건 추가 호출이나 새 전원 제어 없이 실제 분기를 관측한다.
- 원본 전체 콜백·관측 경로·관측 비활성 경로를 비교한 C 시나리오 24개, PMU C 시나리오 88개와 회귀 245개를 통과했다. v28 `a310eee`, CI `40602830413`의 단일 실기기 시험에서 16개 평가, 자동복귀와 5개 파티션 무결성을 통과했다. FSYS0A 원본 전원 끄기 콜백·조건·제어 호출은 세 시점 모두 0회여서 USB 조건 거부 증거는 없었다. 현재 TEST_DEVICES가 late/noirq 이전에 반환하는 경계를 다음으로 검토한다.

## 2026-10-28: 전원 도메인 16개 통합 관측 준비

- v27은 기존 14개 평가를 유지하고 PMU_ALIVE의 16개 도메인 제어·실제 상태·재확인 제어값을 한 빌드에서 함께 관측한다. 원본 CAL·DT의 명시된 주소와 마스크만 사용하며 주변장치 MMIO나 전원 변경은 추가하지 않는다.
- 모든 54개 읽기의 개별 오류를 포함한 C 모델 88개와 회귀 239개가 통과했다. 기존 ABOX·UFS·IOMMU 모델 소스 해시도 유지됐다. v27 `073c069`, CI `40598642972`의 단일 실기기 시험에서 15개 평가, 자동 TWRP 복귀와 5개 파티션 무결성을 통과했다.

- 정지 전·정지 시점에는 16개 중 FSYS0A만 제어·상태 비트가 1이었고 나머지는 0이었다. 복원 후에는 EMBEDDED_G3D도 1로 관측됐다. 세 시점 모두 제어값 재확인 차이는 0이다. 전체 DMA 종료·XNU 실행의 증거로 확장하지 않는다.

## 2026-10-28: ABOX 실패 펌웨어 완료 후 재활성화 수정·실기기 확인

- v25 `42f042e`, CI `40538317465`의 단일 실기기 시험에서 기존 13개 평가, 자동 TWRP 복귀와 5개 파티션 해시를 통과했다.
- 별도 기본 비활성 guard로 NULL 펌웨어 완료 2회의 불필요한 runtime 재개를 차단했다. ABOX는 세 시점 모두 runtime-suspended를 유지했고, 보호용 시스템 PM 참조만 정상 생성·해제됐다. IOMMU runtime·policy-active 값도 0이다.
- ABOX C 모델 105개, IOMMU 25개, UFS/HCI 42개와 회귀 227개를 통과했다. IPC 큐는 버리지 않았으며, DSP·전체 DMA 종료나 XNU 실행은 아직 증명하지 않았다.
- v26 `08d944c`, CI `40545543987`은 기존 평가와 읽기 전용 PMU 관측을 묶은 단일 실기기 시험에서 14개 평가, 자동 TWRP 복귀와 5개 파티션 무결성을 모두 통과했다. 새 PMU C 모델 34개, 기존 C 모델 전부와 전체 회귀 236개도 통과했다.
- 두 ABOX 코어의 PMU power/enable 제어 비트는 세 시점 모두 0, standby 마스크 값은 코어별 0x11/0x1이었다. 실패 펌웨어 완료 2회는 계속 차단됐고 runtime-suspended와 정상 PM 보호 참조를 유지했다. 제어 비트는 전원 종료 확인 응답이 아니며 전체 DMA 정지·XNU 실행을 증명하지 않는다.

## 2026-10-27: 화면 로그를 끈 실기기 PM EBUSY 해결

- 공개 소스 `581688c`, 커널 CI `40421302683`로 새 BOOT의 단일 자동 실기기 시험을 통과했다.
- 시스템 PM 복귀 후 USB core의 runtime-active 상태를 정상 runtime-PM API로 다시 정지시키고 엄격한 quiesce 검사를 유지했다. PM·USB·wakeup·역순 복원 오류 모두 0, 8개 CPU 타이머 원래 값 복원을 확인했다.
- 새 TWRP 부팅 ID로 자동 복귀를 확인하고 원시 로그를 보존했다. 사후 5개 파티션 해시는 진단 BOOT를 포함해 모두 예상값과 일치했다.
- 검증 범위는 `screen_log=false`의 TEST_DEVICES 왕복 1회다. 전체 DMA 정지·GIC/MMU/cache 인계·XNU 실행·iOS 부팅이나 반복 안정성을 의미하지 않는다. 상세 결과와 범위는 `device_test/PM-TIMER.md`에 기록했다.

## 2026-10-27: 커널·XNU 우선, EBUSY 정상 정지 경로 준비

- 사용자 우선순위는 커널 및 iOS 포팅이다. 화면 터미널은 보조 진단으로 진행한다.
- v8의 세 PM 시도는 모두 동기화 시작 전 활성 wake lock으로 EBUSY를 반환했다. USB·DECON의 정상 정지와 역순 복원을 추가하고 기존 sync/freezer/wakeup 검사를 유지한다.
- 별도 NOTE10_PM_QUIESCE 설정, 비동기 USB 완료·케이블 변화·드라이버 오류·복원 실패 검사와 체크섬 N10QSC1 기록을 구현하고 PC 검사를 통과했다. 새 실기기 결과는 아직 없다.
- PM devices-only 왕복이 통과해도 모든 DMA/GIC/MMU/cache 인계 또는 기기 XNU 실행·iOS 부팅을 의미하지 않는다. 다음 빌드의 PC 검사와 실기기 검증을 이어간다.

- 기준 저장소 복제 및 커밋 고정 기록 완료.
- Note10+ 포팅 계획과 읽기 전용 ADB 수집 도구 작성.
- 공식 Google Platform-Tools ZIP 다운로드/압축 해제 완료 (`host-tools/`, Git 제외).
- Python 구문 검사 및 CLI 도움말 확인 통과. 실제 기기 수집은 미검증.
- 기존 Unity ADB는 서버 시작 실패. 새 ADB는 `Cannot mkdir '\.android': Permission denied`로 실행 실패. 프로젝트 내부 `ANDROID_USER_HOME` 지정으로도 해결되지 않음.
- WSL은 설치된 배포판/사용 가능한 환경을 확인하지 못함. AArch64 빌드 및 macOS/Xcode 기반 XNU 빌드는 수행하지 않음.
- 사용자 확인: SM-N976N, Android 12, OEM 잠금 해제 허용 예정. 실제 부트로더 언락은 확인되지 않음.
- 펌웨어 빌드번호/서비스 제공자 버전, USB 디버깅 및 PC 연결 상태 답변 대기.
- Android 12 계열 참조로 LineageOS lineage-19.1 d2x 및 exynos9820-common 소스 복제 완료. 커널 저장소는 Git 객체만 확보되었으며 Windows 예약 파일명 때문에 전체 checkout 실패. 아직 빌드하지 않음.
- 기기 재부팅/언락/플래시/파티션 변경 수행하지 않음.
- Note10+용 네이티브 shim/드라이버, 부팅 이미지, iOS GUI 및 정상 구동은 아직 구현·검증되지 않음.

추가 진행:

- 원본 N976NKSU2HXJ2 AP를 분석해 boot/recovery v1 헤더와 DT/DTBO 구조 판독. 재실행 도구는 inspect_firmware.py, 관측 정리는 HARDWARE.md.
- GICv2 선언 확인: V60 GICv3 경로를 재사용할 수 없음.
- 우선 iOS 대상 변경: iPhone 18 Pro / iOS 27.0.1 / 24A446.
- Apple CDN에서 매니페스트, 커널 및 DeviceTree 취득 및 digest 대조. 커널 실제 버전은 Darwin 27 / xnu-13432.2.10, 내부 커널은 arm64e.
- 대응 XNU 공개 태그 직접 조회는 404. 최신 사용자 공간의 ABI/명령어, AEA/APFS/cryptex 및 하드웨어 실행 호환성 미확인.
- 사용자 제공 전체 IPSW는 프로젝트 루트에 있고, 매니페스트/커널/DeviceTree가 CDN 취득 파일과 동일함을 확인. 전체 해시 결과는 research/ios27/local-ipsw-verification.json 참조.

다음 작업은 최신 사용자 공간의 CPU/ABI 요구사항 판독 및 이식 경로 검토, 실기기 CPU 기능/live DT/부팅 관측 확보다. 정상 구동·플래시 가능한 이미지는 아직 없다.

최근 추가 진행:

- ADB를 샌드박스 밖에서 실행하여 사용자가 연결한 SM-N976N을 읽기 전용 조회함. 연결 문제 해결.
- 실제 설치 빌드 N976NKSU2HWH5, 제공 AP N976NKSU2HXJ2: 불일치 확인. 실제 부트로더 locked, OEM unlock allowed=0.
- CPUinfo에 paca/pacg 기능 없음. 기능 레지스터 sysfs 없음. live DT는 일반 ADB에서 권한 거부.
- OS AEA 복호화 완료. Windows 직접 마운트 실패를 7-Zip APFS 읽기로 해결.
- launchd/dyld/SpringBoard 추출 및 Mach-O 정적 분석 도구 구현. 세 바이너리 ARM64e_X1, 인증 분기 명령 사용 확인. 두 명령은 독립 도구로 재확인.
- 실행 없이 해시/메타데이터/명령어를 분석한 결과다. 최신 사용자 공간 실행이나 부팅 성공은 아님.
- 상세 관측 및 남은 호환성 문제: USERLAND27.md.

CPU 실행 진단 추가:

- cpu_probe.c 및 재빌드 스크립트 구현. 기존 Android NDK로 AArch64 ELF 빌드, 경고 오류 취급 빌드 통과.
- 실기기에서 임시 실행해 코어 0–7 모두 PACIA/XPACI SIGILL 확인. affinity 복구 및 기기 임시 파일 삭제 완료.
- 레지스터 MRS는 커널에 의한 보정 가능성이 있어 물리 CPU 기능/16K 지원의 직접 증거로 사용하지 않음.
- 상세 결과 CPU-PROBE.md, 원본 결과 note10/private/cpu-probe-result.json.
- V60 패치에는 최신 ARM64e_X1 사용자 공간 호환 구현이 없음. 정확한 XNU 13432 소스/빌드 경로도 아직 미확보. 실행 가능한 iOS 호환 계층이나 Note10+ 커널 이미지를 구현했다고 주장하지 않음.

호환성 부품 구현:

- compat/auth_branch.c와 .h: 인증 분기 10종 decoder 및 외부 인증 callback을 요구하는 제한적 레지스터 전이 모델.
- 미구현 인증을 성공으로 처리하지 않음. PAC 암호 연산·명령 전체·XNU 연동은 아직 없음.
- Capstone 독립 oracle 288,009건, 실제 IPSW 코드 253,145 word 포함.
- SM-N976N에서 비교/전이 테스트 887,451개 검증 통과. 기기의 임시 테스트 파일·자료 삭제 완료.
- AArch64 freestanding ELF 및 Apple arm64 Mach-O 객체 컴파일 완료. 실제 XNU 빌드나 iOS 실행 성공을 뜻하지 않음.
- 상세: compat/README.md.

포인터 형식 구현 추가:

- compat/fixup24.c/.h: ARM64e USERLAND24(format 12) 4종 포인터 metadata decoder 및 읽기 전용 page walker.
- 원본 launchd/dyld/SpringBoard의 9개 페이지, 포인터 4,307개 추출. 실제 fixup 1,956개가 authenticated 형식.
- Apple dyld의 고정 커밋 원본 C bitfield header로 교차검증. 테스트 자료 24,322건 및 페이지/잘못된 입력 검증: SM-N976N에서 172,836개 assertion 통과.
- 재배치 적용, 심볼 해석, PAC 서명, 커널 연결은 아직 구현하지 않음. 상세 compat/FIXUP24.md.

로더 값 계산 추가:

- fixup_value.c: 일반 재배치/준비된 bind table의 포인터 값 계산, authenticated 값은 실제 서명 backend를 필수로 요구. 이미지 쓰기는 수행하지 않음.
- import_table.c: import 형식 1/2/3 해석, 이름과 라이브러리 ordinal/weak/addend를 범위 검사와 함께 반환.
- 원본 import 706개 및 포인터 테스트 24,322건. SM-N976N에서 89,186개 assertion 통과, 임시 파일 삭제.
- 실제 심볼 검색기, PAC signing backend, XNU 연결·부팅은 아직 미구현. 상세 compat/LOADER-VALUES.md.

실험용 소프트웨어 PAC 모델 추가:

- QEMU의 고정 커밋에서 architected QARMA3/5 코어를 독립 라이브러리로 이식. LGPL-2.1-or-later 고지·원본 저작권·라이선스·출처 유지.
- 제한된 lower-range VA/TBI 설정의 서명·인증, 앞선 분기/포인터 값 계산 부품과 adapter 연결.
- 공개 논문의 QARMA5 sigma2 정답 벡터 일치. 초기 sigma0 정답 선택 오류를 확인·수정하고 경위를 기록.
- SM-N976N에서 2,048 roundtrip, 31,744 signature-bit 변조 거부 및 연결 테스트: 37,911개 assertion 통과.
- 실제 Apple ARM64e_X1 설정, 주소 혼합, key lifecycle, 전체 PAC 명령, XNU trap 및 iOS 실행은 미검증/미구현. crypto primitive 테스트가 iOS 호환성을 보장하지 않음.
- 상세 compat/SOFT-PAC.md. 정상 구동·부팅 가능한 Note10+ 이미지는 아직 없음.

PAC 명령 상태 모델 추가:

- pac_instruction.c/.h: legacy PAC/AUT/XPAC 31형식 decoder와 제한적 소프트웨어 상태 실행.
- Capstone 독립 oracle 291,766건. 실제 코드의 지원 명령 2,955개 중 hint 130개 확인.
- SM-N976N에서 932,743개 assertion 통과; 임시 파일 삭제. 실제 iOS 명령 실행·XNU trap 테스트가 아님.
- 일부 hint는 구형 CPU에서 NOP이므로 undefined-instruction trap만으로 가로챌 수 없음. 실제 가로채기/코드 변환과 최신 ARM64e_X1 추가 명령 지원은 미구현.
- 상세 compat/PAC-INSTRUCTIONS.md. XNU 부팅 이미지는 아직 없음.

PAC hint 가로채기 실험 추가:

- test_hint_intercept.c: 시험용 AArch64 코드의 hint 4곳을 BRK로 바꾼 별도 메모리 페이지에서 실행.
- Android SIGTRAP의 저장 레지스터를 소프트웨어 PAC 모델에 전달하고 PC+4로 실제 복귀. RW 작성 후 RX 실행.
- SM-N976N 8코어에서 원본/변환 코드 각각 512회 호출, BRK 2,048회 처리, LR 서명 변화 1,024회 및 인증·strip 후 복원 확인.
- 기기 임시 파일 삭제 완료. iOS 원본 변환·실행이나 XNU 연결을 수행한 결과가 아님.
- 상세 compat/HINT-INTERCEPT.md. Apple PAC ABI·전체 hint·최신 ISA·코드서명/캐시·XNU 통합은 남아 있음.

Hint 위치 등록·연결 부품 추가:

- hint_sites.c/.h: 이미지별 immutable table 검증, slide 적용 PC 검색, 등록 위치·BRK 원문 일치 후 PAC 모델 호출.
- 원본 해시·실행 segment 범위·암호화 여부를 검사하고 별도 연구용 Mach-O 복사본/manifest 생성. 원상복구 시 전체 원본 일치 확인.
- dyld 130곳 변환, launchd/SpringBoard 해당 hint 0곳. dyld 변환본은 원래 코드 서명 무효이며 실행용이 아님.
- SM-N976N 실제 위치 130개·slide 3종·오류 거부 14,653 assertions 통과. 새 연결부로 8코어 BRK 2,048회 처리·복귀 재검증.
- 기기 시험 파일 삭제. iOS 원본 실행·XNU 부팅은 아직 없음. 상세 compat/HINT-SITES.md.

Exynos 초기 플랫폼 부품 추가:

- platform/gicv2.c/.h: callback 기반 GICv2 레지스터 관측, EOImode=0 IRQ 수신·완료 및 PPI/SPI 마스크 설정.
- 특수 INTID 1020–1023 완료 거부, SGI source CPU 포함 IAR 원문 보존, split EOI mode 거부. 초기화·실제 MMIO adapter는 미구현.
- SM-N976N Android 프로세스의 모의 레지스터로 token 1,132건 및 10,856 assertions 통과. 실제 하드웨어 IRQ 검증이 아님.
- Freestanding ELF/Apple arm64 객체 빌드, 기기 임시 파일 삭제 완료. 상세 platform/GICV2.md.
- 2026-10-21 Apple 공식 GitHub API 재확인: 목표 xnu-13432.2.10 태그 404, 최상단 공개 태그 xnu-12377.121.6. 기록 private/xnu-source-check.json.
- iOS 27을 구형 커널로 대체하거나 대응 소스/부팅 성공으로 취급하지 않음. XNU 빌드·연결 및 네이티브 부팅은 미완료.

사용자 지정 IPSW 변경:

- 활성 대상을 iPhone18,1 / iOS 26.5.2 / 23F84로 변경. 설정 note10/target.json, 상세 IOS26.md.
- 로컬 11,321,477,590-byte IPSW SHA-256 확인. BuildManifest 식별 및 kernelcache/DeviceTree의 CRC·SHA384 검증 통과.
- 실제 커널은 xnu-12377.122.8~1 / Darwin 25.5.0 / RELEASE_ARM64_T8150. 해당 공개 태그는 404.
- Apple 공개 xnu-12377.121.6 소스를 고정 커밋 ac9718fb1af618d5ce8678d0dc6e8a58f252216f로 취득·압축 해제. 정확히 일치하는 소스로 취급하지 않음.
- 분석 도구 기본 입력을 활성 대상으로 변경. 26.5.2 사용자 공간 미추출 상태에서 27 corpus 재사용·덮어쓰기를 거부하는 동작 확인.
- 기존 iOS 27 검사 결과는 역사 기록. 새 사용자 공간 추출·검사, XNU 빌드·기기 부팅은 아직 미완료.

iOS 26.5.2 사용자 공간·소스 빌드 조사 추가:

- OS AEA 복호화 완료. 복호화 APFS 9,571,401,728 bytes의 SHA384가 manifest OS Digest와 일치. launchd/dyld/SpringBoard/SystemVersion 추출·26.5.2/23F84 확인.
- 세 바이너리는 arm64e subtype 0x80000002. 지원 PAC 명령 7,662개, hint 4,157개, format 12 fixup 4,023개, import 669개 확인.
- 새 corpus로 Android 부품 검사 5종: 총 2,505,371 assertions 통과. 기기 임시 파일 삭제, 결과 private/ios26-results. 실제 iOS 실행 결과가 아님.
- 추출·활성 입력 해시/버전 검사·기기 검사 runner 구현. 상세 USERLAND26.md.
- 사용자 Mac 환경 없음 확인. Windows에서 전체 XNU 도구 체인 미확보, public 기기 구성에 Exynos 없음. 기존 패치 81개 독립 dry check 중 80개 실패; 실제 적용 없음.
- 소스 조사 기록 XNU26-BUILD.md, 재현 audit_xnu_build.py. 전체 커널 빌드·링크·네이티브 부팅은 미완료.

XNU 12377 첫 Exynos 빌드 선택 패치:

- xnu26/patches/0001-exynos9825-build-selection.patch: EXYNOS9825 기기 이름·ARMv8.2+crypto 옵션, 일반 커널 architecture arm64 고정, BTI build 0 분리.
- pinned 소스 hash guard 및 패치 생성·격리 stage apply/reverse 검증 도구 구현. 참조 소스는 수정하지 않음.
- NDK 내부 GNU Make 4.2.1을 발견. 실제 선택 fragment로 Exynos 입력 조합 6종과 기존 Apple 기기 3종 검사 통과.
- 선택 fragment 검증만 수행. Exynos board config/MASTER profile/플랫폼 archive 대체·초기화 드라이버 및 전체 컴파일·링크·부팅은 미완료.
- 상세 xnu26/README.md, 결과 private/xnu26-selection/result.json.

초기 capability 수집 entry 준비:

- 실기기 Android cache sysfs에서 항목을 얻지 못함. 실제 granule·cache 값을 임의의 보드 상수로 지정하지 않음.
- shim/cap_entry.S 및 320-byte record 해석기 구현. EL1/EL2별 register 관측, CLIDR 기반 CCSIDR 선택, CSSELR 복원, 완료 marker 및 halt.
- stack/MMIO/MMU 변경 없이 동작하도록 작성. NDK ARMv8.2 연구용 ELF compile/link 완료.
- 실제 조립 명령을 PC Unicorn + 합성 MRS/MSR로 검사: 102 cases, malformed record 9종 거부 통과. ELF/소스 hash 기록.
- 실기기 privileged 실행·기록 회수 경로는 미구현. 실제 cache/16KiB 지원, 보드 header, XNU 전체 빌드·부팅은 여전히 미확정/미완료.
- 상세 shim/README.md. 진단 ELF는 Samsung/Android 부팅 이미지가 아니며 기기에 실행·플래시하지 않음.

GICv2 MMIO 연결 부품 추가:

- platform/gicv2_mmio.c/.h: caller가 제공한 Device-mapped virtual window에 대한 volatile 32-bit 접근과 DSB SY/ISB callback 구현.
- 범위·정렬·중첩·overflow 검사 및 접근 register 제한. CTLR·SGI enable·특수 IRQ 완료 등 거부. 초기화·XNU mapping·IRQ vector는 미구현.
- SM-N976N에서 실제 하드웨어 주소가 아닌 Android 프로세스의 일반 메모리 배열로 30,166 assertions 통과. 시험 파일 삭제.
- freestanding ELF/Apple arm64 Mach-O 객체 빌드, undefined symbol 없음, ELF barrier 명령 확인.
- 실제 Device mapping/IRQ 전달이나 XNU 부팅 검증은 아님. 상세 platform/GICV2-MMIO.md.

XNU Exynos 물리 decrementer 선택 패치:

- xnu26/patches/0002-exynos9825-physical-decrementer.patch: Exynos 분기에서 CNTP TVAL/CTL 선택. 사용자 공간과 공유하는 CNTVCT timebase는 유지.
- 물리/가상 timer를 mask하고 초기화된 per-CPU decrementer 값을 적용한 후 물리 timer enable·ISB. Apple timer 동시 선택은 compile error로 거부.
- pinned 실제 소스 fragment를 compile/link해 합성 register로 실행: Exynos/generic/Apple 각 13종, 총 39종 통과. 실제 패치 apply/reverse 검사 및 pristine 보존 확인.
- 커널 전체 빌드·실제 타이머 IRQ·GICv2 vector 연결 및 CNTFRQ/ADT 일치는 아직 미검증/미완료. 상세 xnu26/TIMER.md.

XNU GICv2 timer IRQ bridge 패치:

- 0003 패치: GICv2 core/MMIO를 XNU source list에 포함하고 Exynos sleh_irq 분기 → pe_note10_handle_irq → rtclock_intr → EOIR 소스 경로 구현.
- 단일 CPU·IRQ masked·기존 non-secure EOImode0 초기화 상태를 요구하는 binding API. 초기화·mapping·최초 binding 호출은 아직 미구현.
- 타이머 source mask·cached decrementer expired 처리·callback·EOI·unmask 순서. 특수 IRQ에는 EOI 없이 복귀, 미구현/불량 상태는 panic.
- 실제 bridge/core/sleh_irq fragment compile/link 후 합성 실행 20종 통과. 8개 파일 patch 적용·되돌리기 검사, pristine source 보존.
- distributor CTLR read-only 관측 추가에 대해 SM-N976N 일반 RAM 버퍼 30,166 assertions 재검증. 실제 GIC/IRQ 접근은 없음.
- 상세 xnu26/IRQ.md. 전체 커널 compile/link·실기기 timer IRQ·XNU/iOS 부팅은 미완료.

XNU 최초 IRQ mapping/binding 호출 연결:

- 0004 패치: VM/topology 준비 후 pe_arm_init_interrupts에서 Exynos bootstrap 호출. 공통 pe_arm_init_timer 경로는 유지.
- 명시적 /chosen/note10-platform profile의 크기·모델·주소·PPI·GIC handoff 선언을 검사하고 runtime CNTFRQ/DT/XNU 주파수 일치 후 ml_io_map → binder 호출.
- 이는 사전 초기화된 GIC를 인계받는 경로이며 cold 초기화·실제 handoff 생산자는 아직 없음.
- 실제 bootstrap/init 소스 fragment compile 후 합성 서비스로 20종 실행 통과. 전체 4개 패치/12개 파일 순차 apply/reverse 및 원본 보존 검사 통과.
- PC 작업만 수행. 실기기 MMIO·실제 IRQ·전체 XNU build/link·iOS 부팅 검증은 없음. 상세 xnu26/BOOTSTRAP.md.

실기기 적용 전 PC 검증 절차:

- 사용자 지정 범위에 따라 기기 조작 없이 진행. bootstrap → 실제 binder/GIC → timer IRQ handler 통합 합성 검사 31종 통과.
- predevice.py: 활성 IPSW/사용자 공간 식별·부품 빌드·합성 검사·패치 순차 검증·입력 전후 해시·단계별 로그를 한 절차로 구성.
- profile 없는 PowerShell에서 Get-FileHash가 로드되지 않아 발생한 빌드 실패를 .NET SHA256으로 수정. 참조 해시 검사 자체는 유지.
- 전체 커널/메모리 계약/GIC handoff/사용자 공간/드라이버/배포 이미지/소스 ABI의 미완료 항목을 보고서에 명시.
- 적용 준비는 여전히 미완료. 상세 PREDEVICE.md. 실제 기기 적용 직전 단계에 도달했다고 표시하지 않음.

실제 XNU 헤더 의존성 검사 및 수정:

- 공개 생성 헤더 묶음 1.2MB의 SHA256·소스 버전 확인 후 .h 263개만 추출. VMAPPLE 설정이므로 Exynos 설정으로 취급하지 않음.
- 실제 헤더에서 두 Note10 source의 cpu_topology 직접 include가 cluster_type_t/MAX_CPU_TYPES 정의를 앞질러 실패함을 확인.
- machine_routines 경유로 수정하고 패치 0003/0004 재생성. 원본 공개 소스 보존.
- 수정 전 VMAPPLE 실패·수정 후 VMAPPLE syntax 통과·Exynos 보드 정의 누락 실패의 회귀 검사 추가.
- PC runner에 해당 진단을 추가. Exynos 실제 헤더/전체 커널 컴파일 성공은 아님. 상세 xnu26/HEADERS.md.

명시적 입력형 Exynos 보드 헤더 및 실제 연결 파일 컴파일:

- 0005 패치: Exynos board/proc_reg 경로 추가. cache/page 값은 기본값 없이 요구하며 단일 CPU로 제한. 물리 보드 설정 미확정.
- 헤더 22종: 합성 입력 통과, 누락/범위/Apple PAC·BTI·플랫폼·SPTM 충돌 거부. ARM_PGSHIFT와 요청값 일치 검사.
- 실제 bootstrap·IRQ bridge C 파일 전체를 실제 XNU 헤더와 합성 4K/16K 입력으로 컴파일해 Mach-O 객체 4개 생성. 전체 커널 컴파일/링크 아님.
- pexpert의 CPU 내부 상태 접근을 osfmk note10_rtclock_intr로 이동. 추가 wrapper 실제 함수는 합성 bridge/통합 시험에 포함.
- ml_io_map 초기 오류는 검사 명령의 PEXPERT_KERNEL_PRIVATE 누락으로 확인·수정. 소스 선언을 위조하지 않음.
- 전체 5개 패치/17개 파일 순차 apply/reverse 통과. 실기기 조작 없음. 상세 xnu26/BOARD.md.

Exynos SoC MASTER 및 플랫폼 archive 입력 분리:

- 0006 패치: 기존 doconf 우선순위를 이용하는 MASTER.arm64.exynos9825 추가. Apple PPL·CPU/pervasive counter·PV ticket·SPTM/tag 선택 제외. 다른 기본 그룹은 유지.
- pinned upstream sed/awk로 RELEASE/DEVELOPMENT/DEBUG 설정 텍스트 생성·검사. 실제 XNU config 도구·컴포넌트 헤더 생성은 미실행.
- Exynos 링크에 N10_PLATFORM_ARCHIVE를 명시적으로 요구. 잘못된 경로·플랫폼·구성 및 복수 구성 입력 거부. 기존 Apple/NONE 분기 유지 검사 포함 GNU Make 17종 통과.
- archive 검사는 경로/선택만 확인하며 실제 플랫폼 구현·ABI·전체 링크 검증이 아님. 테스트 fixture는 부품 객체 하나의 archive로 별도 표시.
- 전체 6개 패치/18개 파일 적용·복원 통과. 플랫폼 archive·Darwin 빌드 환경·실측값 및 부팅 이미지는 여전히 없음. 상세 xnu26/MASTER.md.

사용자 직접 조작이 필요한 지점까지 연속 PC 작업:

- 휴대용 Clang 23.1.3·Flex/Bison 확보. XNU 원본 config의 Windows 빌드 성공(호스트 BSD 타입/문자열 함수 호환만 추가).
- 7개 패치 적용 격리 소스에서 native config를 실제 실행: 8개 컴포넌트×3종=24개 Makefile, feature header 421개 생성.
- 원본 Makefile assignment/conditional 목록을 GNU Make로 평가해 헤더 907개 export. Skywalk는 SDK 누락이 아니라 export 경로 문제였음.
- KDK 26.5/25F71 다운로드·선언 헤더 추출. installer 미실행. XAR checksum·PBZX/CPIO 경로 검증, 헤더 해시 기록. Mac 플랫폼 코드를 Exynos 드라이버로 사용하지 않음.
- 0007 패치: Exynos sleh에서 미사용 Apple core-type helper include 제외. 실제 핵심 C 10개 전체 컴파일 성공.
- 전체 선택 C audit 863개 중 585개 컴파일·278개 실패, 생성 C 40개 미준비. 주된 차단은 Apple 전용 builtin 2종. 기타 플랫폼·MIG/VM 타입 등 실패 유지, 가짜 구현으로 통과시키지 않음.
- GitHub macos-26 수동 compile workflow 및 source-only 진단 수집 준비. PC에서 workflow/입력 3종 대조, 실제 Mac job 미실행.
- gh auth status는 로그아웃. 사용자 직접 GitHub 로그인과 사용할 저장소 지정이 필요한 다음 단계. 기기 조작·원격 push/dispatch 없음.
- 상세 xnu26/NATIVE-WINDOWS.md, xnu26/CLOUD.md. 전체 커널 링크·부팅 이미지는 여전히 없음.


## 2026-10-21: 실제 macOS 소스 생성·컴파일·부분 링크

- 사용자 GitHub 기기 인증 완료 및 지정한 eirblue/ios_note10p에 공개 소스만 업로드했다.
- Xcode 26.6 / Apple Clang 21.0.0에서 XNU builtin 2종 지원을 확인했다.
- KDK의 SDK/KernelSupport 실제 선언, 고정 커밋 libdispatch 선언을 사용한다. 임시 타입/빈 함수로 오류를 숨기지 않았다.
- 실제 Mach MIG 헤더 68개, 선택 Mach/보조 RPC C, BSD syscall/ioconf, DriverKit IIG 19개를 생성했다.
- 생성 코드 포함 C 903/903, C++ 129/129, assembly 19/19개 컴파일을 확인했다.
- genassym.c에서 148개 구조체 상수를 생성했다. 원본 sed recipe와 비교했다.
- 1,051개 객체를 Apple ld -r로 결합했다. 외부 정의 심볼 27,092개, 미해결 이름 316개다.
- 실제 실행: https://github.com/eirblue/ios_note10p/actions/runs/39531554122 . 자세한 범위는 xnu26/LINK.md.
- 현재 native 선택에는 start/arm_init/arm_vm_init/pmap_bootstrap이 없다. 별도 ARM 후보 소스를 검사 중이다.
- 완성된 Exynos 플랫폼 archive, 전체 XNU 링크, 부팅 이미지, iOS 사용자 공간 통합 및 실기기 부팅은 미완료다.
- 이번 단계의 ADB·재부팅·기기 쓰기·언락·플래시는 없다. original firmware/IPSW/기기 덤프/SDK/인증 정보는 업로드하지 않았다.


## 2026-10-21: 실험용 ARM64 실행형 링크 성공

- 검증 실행: https://github.com/eirblue/ios_note10p/actions/runs/39559172237 (`71b5960`).
- C 904/904, C++ 129/129, assembly 19/19, 별도 ARM 후보 15/15, firehose 1개와 메타데이터 3개 컴파일.
- 실제 SleepToken 선언과 저장 공간·genassym 조건을 맞췄다. 구조체 상수 149개를 원본 sed와 대조했다.
- 원본 VM 별칭 6개 및 실제 arm64 커널 compiler runtime을 연결했다. 임시 성공 함수로 대체하지 않았다.
- 1,071개 객체 부분 링크 후, XNU 원본 배치 옵션으로 18,505,624-byte arm64 MH_EXECUTE를 링크했다. 미해결 심볼과 동적 라이브러리 명령은 없다.
- 이 실행은 전체 upstream Make/커널 컬렉션/KPI/계측 재현이 아니다. 보드 입력은 합성이며 실제 부팅·부팅 이미지·드라이버·사용자 공간은 미완료다.
- 로컬 PC 검사 28/28 통과 및 Windows genassym 149개 생성 확인. 실기기 조작은 없다. 자세한 범위: xnu26/LINK.md.


## 2026-10-21: 원격 생성물 다운로드·독립 구조 검증 완료

- 최종 검증: https://github.com/eirblue/ios_note10p/actions/runs/39560904016 (`ff5ace1`), success.
- 실제 공개 ARM 구현 15개로 archive를 만들고 force-load하여 arm64 MH_EXECUTE를 다시 링크했다.
- 결과 18,522,008 bytes, SHA256 8584aec16c94eeb16b078cb18807f5b93b923c989c19afd78a778745d851454b.
- 원격 생성물을 Windows로 다운로드했다. 해시·세그먼트 범위/보호·정의 심볼·진입 PC를 읽기 전용 검사했다.
- __start와 진입 PC는 0xfffffff007340490으로 일치한다. 여섯 ARM 진입/초기화 심볼이 실제 출력에 있다.
- LLVM readobj도 plain arm64 / MH_EXECUTE로 확인했다. 다운로드 archive 해시도 일치한다.
- 로컬 PC 28개 검사 통과. 기기 접근·언락·재부팅·플래시는 없다.
- 실제 초기 EL/RAM/예약 영역/cache/page/GIC 상태는 미측정이다. 합성 값을 실제 부팅 계약으로 대체하지 않는다.
- Samsung 부팅 이미지·실제 부팅·저장장치/화면/터치·PAC 및 iOS 사용자 공간 통합은 여전히 미완료다.


## 2026-10-21: 실제 기기 시험 1단계 패키지 준비

- 사용자 확인: 현재 부트로더 잠금·순정 리커버리, 필요 시 직접 언락·TWRP 설치 예정.
- TWRP에서 실행할 RAM 전용 하드웨어 진단 ZIP과 Windows ADB/수집/분석 키트를 만들었다.
- 목표는 실제 선택된 DT·RAM/예약 영역·GIC/timer/PSCI·Linux config/log/cache 관측이다. XNU를 실행하거나 파티션에 쓰는 패키지가 아니다.
- 일반 Android·순정 recovery·다른 모델·비root·sideload·복수 ADB 기기를 거부한다. 새 메모리 세션만 생성하고 PC로 회수한다.
- raw DT 대신 sysfs devicetree tar fallback을 지원한다. 동적 예약/주소 가림/관측 실패를 기록하고 XNU 안전 로드 주소를 자동 선정하지 않는다.
- Windows PC 10개 시험 통과. 합성 파일시스템에서 실제 collector 흐름과 RAM guard, 가짜 ADB에서 전체 회수·분석 흐름을 확인했다.
- Linux 원격 시험도 10/10 통과: https://github.com/eirblue/ios_note10p/actions/runs/39566103989 (`15b004e`). ZIP 내부 파일·manifest가 일치한다. 압축 라이브러리 차이로 ZIP 압축 바이트 자체는 다를 수 있다.
- Windows 키트의 파일 해시·CLI import·PowerShell 구문·포함 ADB 버전 실행을 확인했다. Python 3은 필요하다.
- 공식 d2x TWRP 참조 이미지를 다운로드해 공식 SHA256 및 /sbin/sh/awk/cat/getprop/tar/adbd 포함을 확인했다. 실제 사용자 펌웨어 호환성/부팅은 미검증이다.
- 다음 사용자 조작: 데이터 백업 후 언락·호환 TWRP 설치 및 TWRP 홈 화면에서 USB 연결. 연결 전에는 이 도구가 기기에 접근하지 않았다.
- 자세한 실행법: device_test/README.ko.md. 실제 기기에서의 진단 실행과 XNU 초기 진입 시험은 아직 미완료다.


## 2026-10-22: 실기기 연결 전 PC 검증 추가

- 실기기 조작이 바로 다음 유일한 단계라는 이전 안내를 수정한다. 로더·부팅 인자·DT 변환·PAC 통합 등 PC에서 진행할 작업이 남아 있다.
- 실제 커널 명령/skip-data 레코드 2,256,028개를 정적으로 검사했다. 인식 가능한 PAC는 검출되지 않았으나 전체 ISA 호환성을 증명한 것은 아니다.
- SVE/SME 후보 19개는 pinned source의 panic 문자열·SHA256 K256·LZ4 테이블/상수와 바이트가 일치했다. 544개 미해독/비표시 데이터 레코드는 미분류로 남긴다.
- Apple AWL WatchdogDiag0 레지스터 접근 4곳을 확인했다. 기본 지원값 false 및 /arm-io/wdt/awl-scratch-supported gate를 원본에서 확인했다. Exynos DT 생성 시 해당 Apple 기능을 켜지 않아야 한다.
- 실제 링크된 __start부터 첫 CPU 진입을 합성 RAM 두 배치에서 각각 24,957개 명령 실행, 8,250개 store/66,000 bytes 확인 후 MMU 활성화 직전에 정지했다.
- 초기 테이블 네 페이지를 비제로 값으로 채운 뒤 초기화·커널/identity/부팅 인자 매핑을 검증했다. 기존 부팅 인자 버퍼는 변경되지 않았다.
- 부팅 인자를 초기 매핑 밖에 배치하는 부정 사례도 검사기가 거부했다. 임의의 빈 RAM 주소를 선택해서는 안 된다.
- 시스템 레지스터/cache/TLB는 합성 모델이고 CLIDR=0이다. 실제 캐시 동작·MMU 활성화·C arm_init·기기 부팅은 미검증이다.
- 상세 재현·제한: xnu26/ENTRY-MODEL.md. 기기 접근이나 플래시는 없다.

## 2026-10-22: 부팅 인자·ADT 생성 및 실제 파서 검증

- boot_args 생성기와 명시적 RAM 배치 검사기를 추가했다. 정렬·메모리/예약/실행 영역 충돌·포인터/명령행 범위를 검사한다. 실제 RAM을 예약하거나 주소를 자동 선정하지 않는다.
- pinned 공개 XNU boot.h를 실제 ARM64 객체로 컴파일하여 1,152바이트 크기·13개 필드 offset·C initializer 전체 바이트가 일치함을 확인했다. IPSW와 공개 소스 버전 차이는 남아 있다.
- 새 생성기를 실제 링크 커널 진입 시험에 연결했다. 두 배치에서 각각 24,957개 명령 실행을 유지했고, 전체 세그먼트 시작·끝의 virtual/identity 매핑을 추가로 확인했다.
- 초기 매핑이 32MiB 하나뿐이라는 설명을 정정한다. 헤더가 속한 블록부터 여러 L2 블록을 매핑하며 memSize 계산에서 제외되는 앞/뒤 영역이 있다. 메타데이터는 첫 블록에 두는 보수적 정책을 적용했다.
- bounded raw Apple DT codec 및 잘린 입력·중복·이름/크기·순환 검사를 추가했다. 부팅 인자/배치 8개와 ADT 5개 PC 시험을 통과했다.
- 실제 링크 SecureDT 함수와 문자열 비교 코드를 2,094개 명령 실행하여 합성 ADT 경로/속성, 없는 값 반환, 잘린 영역/과도한 속성 길이에 대한 panic 진입을 확인했다. 임시 성공 함수로 대체하지 않았다.
- 합성 ADT에 GIC handoff를 만들어 넣지 않았다. 실제 Linux DT 변환·CPU/캐시/MMU 전환·GIC 소유권·로그 경로는 미완료다.
- recovery 교체 시 TWRP가 사라질 수 있고 boot 변경도 AVB/부팅 조건에 영향을 받는다. TWRP 재진입을 보장하지 않는다. 현재 파티션 쓰기·기기 접근·플래시는 없다.
- 상세: xnu26/BOOT-CONTRACT.md. deployment_ready=false를 유지한다.

## 2026-10-25: TWRP 실기기 진단 수집 완료

- 사용자 보고로 언락·TWRP 설치 완료를 반영했다. 실제 ADB에서 d2x/exynos9825, TWRP 3.7.0_9-1, root 셸을 확인했다.
- RAM 전용 collector가 실제 live DT·iomem·config·dmesg 등을 수집했고 PC private 경로로 회수했다. collector 명령 모두 exit code 0, 원본 25개 파일의 로컬 해시를 기록했다. 원본은 업로드하지 않는다.
- DT memory 노드 8개·고정 예약 노드 16개·reg 없는 동적 예약 노드 4개를 관측했다. iomem은 실제 주소를 표시하지만 현재 빈/예약 가능한 RAM을 증명하지 않는다.
- GIC distributor/CPU interface 후보 주소, 26MHz 타이머/PPI 30, PSCI SMC가 실제 선택된 DT 선언과 일치했다. 하드웨어 레지스터 상태·소유권 handoff는 미검증이다.
- 현재 recovery Linux의 CONFIG_KEXEC=n을 확인했다. 현재 TWRP에서 표준 kexec로 XNU를 RAM 실행하는 경로는 바로 사용할 수 없다.
- Kconfig의 명시적 `is not set`을 미관측과 구분하도록 분석기를 수정했다. 충돌 설정 거부를 포함한 진단 PC 시험 11개를 통과했다.
- recovery는 4K 빌드다. CPU 전체의 16K 지원·초기 EL/MMU/cache 상태는 이 결과로 확정하지 않는다. cache sysfs 관측은 확보되지 않았다.
- 안전 XNU 로드 주소·실제 handoff·XNU 기기 실행은 미완료다. 기기 파티션 쓰기·재부팅·모듈 적재·kexec·플래시는 수행하지 않았다.

## 2026-10-25: 부팅 구성 백업과 XNU 인자 전달 연결

- 실제 boot/recovery가 별도 블록 노드인 것을 확인했다. boot ramdisk 0, recovery에는 TWRP ramdisk가 있다. boot 교체 후 TWRP 재진입까지 검증한 것은 아니다.
- boot/recovery/dtb/dtbo/vbmeta 5개를 새 PC private 세션에 읽기 전용 백업했다. 각 파일의 기기 전송 전후 SHA-256 및 PC 파일 해시가 같았다. 기존 recovery의 공식 TWRP IMG 범위가 원본과 바이트 일치했다.
- 백업 도구는 N976N bootloader와 고정 allowlist·크기·중복 노드·checksum을 검사한다. 7개 PC 시험 통과. 전체 Android/사용자 데이터/EFS 백업이나 복원 시험은 아니다.
- recovery uname 접미사와 일치하는 공개 kernel commit 55f042627bb7030c93550faafa117674d32b21d1을 찾았다. 실행 바이너리 재현 빌드 일치는 아직 입증하지 않았다.
- 해당 소스의 kexec tail이 x0-x3을 0으로 지우므로 별도 XNU boot_args 연결이 필요함을 확인했다. 현재 TWRP의 CONFIG_KEXEC=n은 그대로다.
- EL1 및 SCTLR M/C/I 꺼짐을 전제로 하는 stack 없는 전달 어댑터 ELF를 작성했다. 잘못된 상태/descriptor를 거부하며, MMU/cache 종료·CPU/장치 정지·RAM 예약·GIC 초기화는 수행하지 않는다.
- 실제 어셈블리 명령을 합성 모델에서 54종 검사했다. 실제 링크 XNU 앞에 연결한 두 RAM 배치에서 각각 24,999개 명령 후 MMU 활성화 직전에 정지했고, kernel store/세그먼트 매핑 검사를 유지했다.
- 상세 shim/TRANSFER.md. Android 부팅 이미지·설치 ZIP은 만들지 않았고, 기기 쓰기·재부팅·모듈 적재·XNU 실행은 없다.

## 2026-10-25: 수동 Linux 커널 시험 설치 직전 준비 완료

- 공개 d2x 소스로 KEXEC 및 built-in CPU 진단을 포함한 전체 Linux Image를 빌드했다. 최종 성공: https://github.com/eirblue/ios_note10p/actions/runs/40146021101 (`640d4ff`).
- Image 46,350,348 bytes, SHA-256 `5c7fa6f04e241644a6d8935d13ff2536bbe46f34aee5419a0de83318a16ce261`. 원래 TWRP 커널과 동일 바이너리라는 뜻은 아니다.
- 진단 빌드는 normal boot의 skip_initramfs 때문에 외부 initrd가 버려지지 않도록 해당 parser를 수정했다. 실제 Image 안의 진단 표식을 확인했다. 실제 bootloader의 initrd 전달은 미검증이다.
- 공식 TWRP ramdisk·고정 AOSP mkbootimg·읽기 전용 기기 백업을 사용해 별도 BOOT 시험 이미지를 만들었다. 57,317,392 bytes로 실제 BOOT 57,671,680 bytes 안에 들어간다.
- 원래 BOOT의 보드/OS/보안 패치 월과 Samsung 식별 표식을 유지했다. stale AVB 푸터·서명은 복사하지 않았다. 별도 DTB/DTBO와 기존 vbmeta는 변경하지 않는다. 실제 부팅 검증·DT 선택은 미검증이다.
- private 경로에 수동 TWRP 진단 설치 ZIP 및 원래 BOOT 복구 ZIP을 생성했다. 정확한 bootloader·블록 노드·크기·기존 비BOOT 해시를 검사한 후 BOOT 하나만 쓰고 전체 해시를 검증한다. 자동 재부팅·포맷은 없다.
- 최종 ZIP 두 개를 실제 TWRP의 새 RAM 폴더에 전송하고 원격 해시·네이티브 unzip 읽기·셸 구문 검사를 통과했다. 설치기는 실행하지 않았다. 실제 5개 부팅 파티션 해시는 원래 백업과 모두 일치했다.
- 전달 어댑터 54종 및 백업/decoder/boot/설치기 PC 검사 18개, 총 72개 통과: https://github.com/eirblue/ios_note10p/actions/runs/40147168707 (`d780cab`). 설치기 쓰기는 PC 일반 파일에서만 시험했다.
- PC에 ZIP 재전송·부팅 후 로그 수집 실행 파일과 설치/복구 안내서를 준비했다. 재부팅하면 RAM ZIP은 사라지며 PC 복사본으로 재전송한다. 설치·복구는 사용자가 TWRP에서 직접 실행해야 한다.
- 준비 완료는 **임시 Linux 커널 수동 시험 패키지**에 한정된다. 새 커널의 실제 부팅·화면·USB·recovery 재진입 및 BOOT 복원은 아직 시험하지 않았다. XNU/iOS 설치 이미지·기기 실행·하드웨어 handoff는 미완료다.
- 상세 device_test/LINUX-CAPS.md. 원본 기기 백업·생성 이미지·설치 ZIP은 업로드하지 않았다. 에이전트의 파티션 쓰기·재부팅·모듈 적재·kexec·XNU 실행은 없다.

## 2026-10-25: 수동 시험 후 이전 커널 로그에서 실측 확보

- 사용자가 BOOT 설치와 System 부팅을 직접 수행했다. 통신사 로고 후 재부팅 반복을 보고했으며 기존 TWRP로 돌아왔다.
- BOOT 해시는 진단 payload와 일치하고 recovery/DTB/DTBO/vbmeta는 원래 백업과 일치했다. TWRP에서 `/proc/last_kmsg` 2MiB와 pstore 로그를 읽기 전용으로 PC에 보관했다.
- last_kmsg에 `4.14.113-note10-handoff-pc` 배너와 완결된 N10CAP1 기록이 있다. 실제 진단 Linux 실행은 확인됐지만 TWRP 진단 환경의 정상 부팅 성공은 아니다.
- 엄격 decoder가 CPU 8개·cache selector coverage·CSSELR 복원 기록을 통과했다. Linux privileged view에서 모두 EL1·16K stage-1 지원·40bit IPS 수용 가능으로 관측됐다. PA 폭은 CPU 4/5가 44bit, 나머지가 40bit다. 부트로더 진입 상태·XNU 실행 증거는 아니다.
- 외부 initrd unpack 메시지는 없고 Android ext4 root가 마운트됐다. 약 53.65초에 bootchecker의 `sysrq: SysRq : Trigger a crash`와 `sysrq_handle_crash` PC, 이어서 kernel panic이 기록됐다. bootchecker가 crash를 요청한 조건과 bootloader의 initrd 미전달 여부는 추가 조사 대상이다.
- 원래 BOOT 복구 ZIP의 payload가 원본 백업과 일치함을 재검증하고 새 TWRP RAM 폴더에 전송했다. 복구 설치·재부팅은 사용자의 다음 직접 조작 단계다. 에이전트는 파티션 쓰기·재부팅을 수행하지 않았다.

## 2026-10-25: 실측 입력을 XNU 보드·진입 검사에 연결

- 사용자 복구 설치 이후 boot/recovery/DTB/DTBO/vbmeta 5개 전체 해시가 백업과 일치함을 확인했다. 원래 Samsung kernel 배너에서도 zygote 반복 종료·bootchecker SysRq panic이 나타났다. Android 정상 복구는 미완료이며 사용자 지시로 해당 복구 작업을 중단했다.
- Linux 진단 실측 원본 로그의 SHA-256·엄격 재해석·헤더 바이트를 연결하는 observed profile 생성/검증기를 추가했다. 원본 로그·개인 데이터는 업로드하지 않는다.
- I/D 최소 라인 64 bytes·최대 관측 line 128 bytes·페이지 16K·최소 PA 폭 40bit로 생성했다. 기존 전체 실험 빌드의 입력 수치와 같지만 그 manifest의 합성 입력 표시를 바꾸지는 않는다.
- raw MPIDR은 서로 다르나 CPU 1/6 affinity 필드가 겹친다. 자동 topology/PSCI ID를 만들지 않고 초기 XNU 단일 CPU 제한을 유지했다.
- 실측 입력으로 실제 XNU patched headers assert 및 bootstrap/IRQ C 파일을 ARM64 Mach-O 객체 3개로 컴파일했다. VMAPPLE generated dependencies를 사용한 구성 요소 검사이며 전체 kernel build가 아니다.
- 실제 링크 XNU와 전달 adapter를 합성 RAM 두 배치에서 각각 24,999개 명령 실행했다. 실제 TCR 0x226511a511의 16K/40bit가 8개 CPU 실측 capacity를 통과했고, MMU 활성화 전에 정지했다. 실기기 handoff·MMU 전환은 없다.
- 관측 불일치/변조/누락·TCR 불일치·출력 경로 거부 등 새 PC 시험 6개를 통과했다. 상세 xnu26/OBSERVED.md. XNU 하드웨어 실행과 iOS 설치 이미지는 미완료다.

## 2026-10-25: Mach-O 메모리 버퍼·부팅 인자·전달 adapter 묶음 구현

- 실제 검증된 XNU Mach-O 세그먼트로 19,578,880바이트 memory image를 생성했다. BSS·빈 영역·padding을 0으로 만들고 원본 파일 바이트를 유지한다.
- boot_args/ADT/adapter를 별도 16K page로 만들며 64바이트 record에 실제 변환된 entry/argument 주소를 연결한다. adapter까지 RAM/예약/점유/충돌 검사에 포함했다.
- ARM64 ELF 표·범위·entry·writable record를 검사하고 relocation/dynamic dependency/W+X를 거부한다. bundle 로드는 파일 해시와 계획·인자 바이트·ADT·descriptor를 재검증한다.
- 생성한 네 버퍼를 직접 명령 모델에 넣었다. 실제 원본 kernel/adapter와 BSS, ADT 보존 및 첫/끝 매핑을 추가 검증했다. 두 합성 RAM 배치에서 각각 24,999개 명령과 8,250회 kernel store 후 MMU 활성화 전에 정지했다.
- 실제 빌드 adapter ELF와 bundle 부정 사례를 포함한 새 PC 시험 7개, 기존 boot contract 8개를 통과했다. 실측 CPU capacity 비교도 통과했다. 상세 xnu26/HANDOFF-BUNDLE.md.
- 실제 RAM 예약이나 kexec backend를 구현한 것은 아니다. PC bundle은 물리 예약/하드웨어 배포 주장을 거부한다. 실제 CPU/DMA/cache/MMU 종료·GIC 인계·XNU 기기 실행·설치용 iOS ROM은 미완료다. 기기 변경은 없다.

## 2026-10-25: XNU용 초기 RAM 예약 진단 커널과 다음 수동 시험 준비

- 별도 Linux 확장에서 기존 kernel/initrd·DT reserved memory·CMA 예약 뒤 memblock free range를 찾아 256MiB/32MiB 정렬 영역을 예약하도록 구현했다. 범위/RAM/기존 예약 검사를 거쳐 late initcall에서 PFN 65,536개의 valid/PageReserved 상태를 기록한다. window 데이터 쓰기·XNU branch는 없다.
- 외부 TWRP initrd 전달에 의존하지 않도록 자체 static ARM64 PID1과 dev/console만 든 CPIO를 내장했다. CMDLINE_EXTEND/rdinit=/init 및 INITRAMFS_FORCE를 사용한다. 첫 Kconfig 실패 후 실제 의존성을 확인해 수정했다. bootloader 하드웨어 인자는 유지한다.
- 전체 Linux Image 빌드 성공: https://github.com/eirblue/ios_note10p/actions/runs/40160441675 (`50aca0d`). Image 46,350,348 bytes, SHA-256 `bdfe101c3f6f808415777458f8af6218c5e5f3c5c87e2aa882a3e1d0a6fd7f11`.
- 다운로드한 실제 Image의 gzip 스트림을 풀어 자체 CPIO와 전체 바이트가 일치함을 확인했다. 실제 PID1 ELF는 PC에서 write→ppoll 반복만 실행했다. 파일 열기·mount·reboot·kexec/XNU 호출은 없다.
- 높은 합성 PA 및 256MiB 창에서도 생성된 XNU 버퍼를 실제 명령 모델에 넣었다. 추가 사례는 24,807개 명령/8,202회 kernel store 후 MMU 활성화 전에 멈췄다. 기존 두 1GiB 사례도 유지했다. 실제 free RAM 주소 선정의 증거는 아니다.
- 최신 PC CI 성공: https://github.com/eirblue/ios_note10p/actions/runs/40161149833 (`fed95bd`). 어댑터·단위 검사 99개와 실제 최소 PID1 명령 모델을 통과했다. 실제 기기 RAM 예약은 아직 시험하지 않았다.
- 외부 ramdisk 없는 BOOT 시험 이미지 46,354,448 bytes를 만들고 별도 reservation 진단/원본 BOOT 복구 ZIP을 생성했다. 원래 보드/OS/패치 월·Samsung 표식을 유지하고 stale AVB footer는 복사하지 않는다.
- 실제 TWRP의 새 RAM 폴더로 최종 ZIP 2개를 전송하고 네이티브 unzip·셸 구문·원격 해시를 확인했다. 기기 5개 부팅 파티션은 원래 백업과 모두 일치한다. 설치/재부팅은 사용자 직접 조작 단계로 남겼다.
- 이 BOOT의 최소 PID1에는 TWRP UI/ADB가 없다. 사용자가 System 부팅을 관찰한 뒤 기존 recovery로 돌아오면 로그를 회수한다. decoder는 이전 Linux boot 문맥에만 유효한 예약으로 표시하며, 재부팅 후 그 주소 재사용을 허용하지 않는다.
- 상세 device_test/RESERVATION.md. 실제 CPU/DMA/cache/MMU 종료·GIC 인계·live load backend·XNU 실행은 여전히 미완료다. Android 정상 복구도 중단된 상태다. 에이전트는 기기 파티션 쓰기·재부팅을 수행하지 않았다.

## 2026-10-25: 첫 RAM 예약 시험 회수와 v2 로그 검증

- 사용자 수동 시험 후 기존 TWRP로 재진입했다. BOOT 전체 해시는 예약 진단 payload와 일치하며 recovery/DTB/DTBO/vbmeta는 원래 백업과 일치했다.
- 이전 부팅 로그에 pages=65536/reserved=65536/invalid=0/shift=12가 남았다. 그러나 RESERVED 주소와 build banner가 손상돼 엄격한 예약 검증은 통과시키지 않았다. 두 번 읽은 원본 SHA-256이 같아 전송 재시도로 회복되지 않았다. 원본 로그는 private에 보관한다.
- 약 125초 시점에 버튼 hard-reset hook과 panic 기록이 있었다. 이 관측을 XNU 실행이나 커널의 자발적 예약 실패로 바꾸어 설명하지 않는다.
- v2는 빌드 고유 ID·순번·전체 예약 정보·FNV-1a 오류 검출값을 포함한 N10RAM2 프레임 32개를 출력한다. 검증한 Image의 내부 ID와 연결된 서로 다른 순번 2개 이상이 완전히 일치해야 통과한다. 손상된 주소를 복원하지 않고 충돌·중복 순번·불완전 페이지 상태를 거부한다.
- 실제 C 검사값 함수를 Windows에서 컴파일해 Python 검증기와 1,026건 대조했다. 전체 예약 C 소스의 API를 명시적으로 모형화한 별도 PC 실행에서 정상 프레임 32개 및 find/reserve/invalid-PFN/unreserved-page 실패 경로 5개를 확인했다. 실기기 예약 검증의 대체 증거는 아니다.
- 최신 PC CI에서 어댑터·단위 검사 108개와 실제 최소 PID1 명령 모델이 통과했다: https://github.com/eirblue/ios_note10p/actions/runs/40163157625 (`5a543bf`). 누락 pstore 파일 오류를 로그로 저장하지 않도록 수정하고 v1/v2 수집 경로를 검사했다.
- 다음 설치 ZIP은 검증한 이전 진단 BOOT 해시를 설치 전 기준으로 연결할 수 있다. 원본 BOOT 복구 ZIP은 유지하며 비BOOT 4개 파티션의 원본 대조는 계속 필수다. 에이전트의 기기 설치·재부팅·파티션 쓰기는 없다.
- v2 전체 커널 빌드 성공: https://github.com/eirblue/ios_note10p/actions/runs/40162958220 (`88a97da`). Image 46,350,348 bytes, SHA-256 `8b16ccf9287b8f3bb97708875724d56eede31a3e91d0d5307f1bec307e568a01`. 빌드 고유 ID가 실제 Image에 한 번 포함됨을 확인했다.
- 실제 Image 내부 CPIO와 원본 archive를 대조했고 실제 init ELF 명령 모델도 통과했다. BOOT prototype 46,354,448 bytes 및 진단/원본 BOOT 복구 ZIP을 PC private에 완성했다. 패키지 SHA/CRC와 PC 셸 구문 검사를 통과했다.
- 빌드 완료 시 ADB transport가 없어 새 ZIP의 TWRP RAM 전송 및 현재 기기 재검사는 미완료다. 전송·검사·로그 회수용 PC 실행 파일과 수동 안내서를 준비했다. PC 패키지 준비와 실제 기기 설치 직전 상태를 별도 필드로 구분한다. v2 기기 시험 및 XNU 실행은 아직 없다.

## 2026-10-25: 실기기 결과와 독립적인 XNU C 진입 PC 검증

- 기존 adapter→XNU 모델에 선택적 continuation을 추가했다. 기존 기본 동작은 MMU 활성화 직전 정지를 유지한다. continuation은 실제 MMU 활성화 명령을 실행하지 않고, 생성된 실제 페이지 테이블로 확인한 소프트웨어 VA 별칭을 사용한다.
- 실제 Mach-O/생성 버퍼로 3개 합성 RAM 배치에서 `_arm_init` 가상 주소 진입과 x0 boot_args, interrupt/exception stack 전달을 확인했다. 각 사례는 기존 경계 이후 51개 명령을 실행해 첫 C 호출 `_static_if_init` 직전에 멈췄다. 호출 자체와 C 초기화 완료는 시험하지 않았다.
- 사례마다 별칭 페이지 1,199개와 fetch 51회/read 1회/store 18회의 주소 변환을 대조했다. 물리/가상 store 복사본은 검사기가 동기화하므로 hardware cache/TLB coherence 증거가 아니다.
- 실제 모형 L2 descriptor의 주소 비트 손상과 잘못된 boot_args 포인터를 거부했다. 기존 continuation 없는 3개 사례도 24,999/24,999/24,807개 명령 및 이전 정지 경계를 유지했다.
- 검증 kernel SHA를 고정하고 첫 호출 경계가 바뀌면 거부한다. 새 수동 CI도 성공했다: https://github.com/eirblue/ios_note10p/actions/runs/40167184145 (`6a4ba1d`). 공개 source-built artifact만 사용하며 기기 로그·observed profile·설치 ZIP은 업로드하지 않는다.
- 상세 xnu26/POST-MMU-MODEL.md. 실제 MMU/cache/TLB 전환·permission fault·Linux CPU/DMA 종료·GIC/timer 인계·XNU 하드웨어 실행은 미검증이다. 이번 작업에서 기기 접근·설치·재부팅이나 기존 설치 ZIP 변경은 없다.

## 2026-10-25: EL1 접근 권한의 PC 부분 검사

- `stage1_access.py`를 추가해 실제 모형 descriptor의 AF/AP, 상위 APTable/PXNTable, PXN/WXN/PAN/EPD 및 EL0-write-XN을 명령 fetch/read/store마다 검사한다. APTable의 EL0 접근 차단과 RO 상속을 적용하며, 경계 접근은 양쪽 16K 페이지를 확인한다.
- 검토한 little-endian 16K/47bit VA/40bit PA·canonical 주소·HA/HD/HPD 비활성 구성으로 제한한다. 자동 AF/dirty 갱신, LPA2/EPAN, 다른 구성은 거부한다. PAN=0은 정상 진입 모형의 명시적 입력이며 실측 PSTATE가 아니다.
- 별도 descriptor fixture 검사 12개, 실제 링크 XNU 정상 3개 배치와 실제 모형 테이블/레지스터/인자를 변경한 오류 사례 10개를 통과했다. 기존 추가 51개 명령과 `_static_if_init` 호출 직전 경계를 유지한다. 기존 MMU 이전 3개 회귀 사례도 통과했다.
- CI 성공: https://github.com/eirblue/ios_note10p/actions/runs/40168931459 (`33ee78f`). 상세 xnu26/POST-MMU-MODEL.md에 기준 공개 소스와 지원 범위를 기록했다.
- 완전한 MMU 또는 실제 permission fault 처리 모델은 아니다. stage-2, memory type, alignment 및 syndrome 전체, cache/TLB, 기기 XNU 실행은 검증하지 않았다. 기기 접근이나 기존 시험 ZIP 변경은 없다.

## 2026-10-25: 초기 스레드·타이머·startup PC 실행

- 실제 C 헤더의 ARM64 구조 배치를 컴파일해 기준 ABI를 만들었다. thread_bootstrap 반환 시 1,680바이트 template 복사와 ctid/priority 변경을 검사했다. 이후 CPU↔thread 포인터와 TPIDR_EL1, preemption_count=0을 확인했다.
- 기본 PC CPU 모델의 세 RAM 배치에서 kernel_startup_bootstrap 호출 직전까지 각각 240,463개 명령을 실행했다. 실제 timebase_callback의 26MHz 결과는 초 divisor=26,000,000, 마이크로초 divisor=26, 나노초 환산 500/13이다. CNTVCT는 정지된 합성 입력이며 실제 시계 동작 증거가 아니다.
- 별도 명시적 Unicorn max 모델에서 LSE LDADD를 포함해 1,021,267개 명령을 실행했다. startup 4,670개 항목의 정렬·원본 내용 보존, LOCKS 단계 1,006개 콜백의 순서·인자와 cursor/phase를 확인했다. 실제 Exynos CPU 모델 또는 물리 원자성 검증을 의미하지 않는다.
- 정상 경로, 실제 missing-clock/missing-reg panic, stale event-state 거부 및 이전 회귀 검사가 CI에서 통과했다: https://github.com/eirblue/ios_note10p/actions/runs/40174526056 (`904f893`). 상세 xnu26/EARLY-C-MODEL.md.
- 전달 adapter는 CNTFRQ=26MHz 및 CNTKCTL EVENTI 선택 비트 0을 요구하고 위반 시 status=5로 거부한다. 실제 어셈블리 81개 사례를 검사했다. 기존 설치 ZIP과 ELF는 보존했다. 이 단계에서 기기 접근·파티션 쓰기·재부팅은 없다.

## 2026-10-25: CPU·캐시·DRAM의 VM 진입 PC 검사

- 실제 cpu_init/processor_bootstrap 및 DRAM 파싱을 거쳐 arm_vm_init 호출 직전까지 1,053,279개 명령을 실행했다. configured ARM64 ABI로 CPU 유형·running/deadline, 캐시 기하·valid, DRAM 전역 값과 초기 physical page number를 확인했다.
- DRAM 속성이 없으면 실제 panic, 선택한 CCSIDR 입력이 없으면 모형 오류로 거부했다. 기존 진입·타이머·startup·권한 검사와 함께 CI가 통과했다: https://github.com/eirblue/ios_note10p/actions/runs/40175688715 (`96d8c1f`). 캐시/CPU/시계 입력은 합성이며 실기기 초기화 성공을 의미하지 않는다.
- 실제 adapter/XNU entry의 DAIFSet 효과를 상태에 반영하고, 정상 시험은 별도 DAIF 성공값을 주입하지 않는다. 반복 명령 해석만 주소+실제 opcode로 캐시하며 모든 fetch·메모리 접근 검사는 유지한다.
- 별도 VM 본문 탐색에서 실제 no-random-seed panic을 확인했고, 공개된 PC 전용 시드로 256바이트 복사와 ADT의 정확한 삭제 경계를 검사했다. entropy 품질이나 후속 PRNG/VM 초기화 완료를 검증한 것은 아니다. 하드웨어 시드 준비 상태는 false다.
- 시드 실제 명령 시험은 정상 복사/삭제, 누락 시 실제 panic, 전부 0인 입력의 실제 반환 0을 통과했다. 전부 0인 사례는 PE callback 반환에서 거부하며 후속 caller panic은 실행하지 않았다. 별도 경계/손상 fixture 검사 5개도 통과했다. CI는 entry/VM/seed 세 작업이 독립 배치를 구성해 병렬 실행하도록 분리했다.
- 세 병렬 CI 작업 모두 성공했다: https://github.com/eirblue/ios_note10p/actions/runs/40176478650 (`cdf4924`). 기존 진입 회귀와 CPU/DRAM 정상·누락 경로, 시드 복사/삭제·누락·zero 입력 검사를 함께 확인했다. 이 결과는 PC 모델 검증이며 실제 XNU 부팅 증거가 아니다.
- ADB 연결 목록이 비어 있어 기기 파티션 재검사·예약 v2 RAM 전송·수동 설치 시험은 진행하지 못했다. 기존 진단/복구 ZIP은 유지한다. 설치 가능한 XNU/iOS ROM이나 실기기 XNU 부팅 성공은 아직 없다.

## 2026-10-25: 예약 v2 실기기 시험 통과

- 사용자가 v2 진단을 직접 설치·부팅한 뒤 기존 TWRP로 돌아왔다. 검증된 Image 내부 빌드 ID와 일치하는 정상 N10RAM2 프레임 29개에서 256MiB, 65,536페이지 전체 PageReserved 및 invalid PFN=0을 확인했다. 손상된 프레임의 값을 복원하지 않았다.
- 현재 BOOT는 v2 진단 payload 전체 해시와 일치한다. recovery/DTB/DTBO/vbmeta도 원본 백업의 전체 해시와 일치한다. 에이전트는 로그·해시 읽기만 수행했다.
- 패닉 호출 경로에 버튼 재시작용 hard_reset_hook_callback이 기록됐다. idle PID1 marker와 완전한 CPU capability 기록은 이번 로그에서 확인하지 못했다. 이를 init 성공이나 전체 Linux 부팅 성공으로 확대 해석하지 않는다.
- 검증된 것은 이전 Linux 부팅의 allocator 제외다. 해당 물리 주소는 현재 TWRP에서 사용하거나 다음 부팅에 고정하지 않는다. RAM 쓰기/읽기, DMA·CPU 정지, cache/MMU/GIC 인계 및 XNU 실행은 아직 미검증이다.

## 2026-10-25: 다음 RAM 접근 진단 설치 준비

- 같은 부팅에서 새로 확보·검사한 예약 영역에 두 개의 상반 패턴을 쓰고 읽은 뒤 전체 zeroing/readback을 하는 opt-in Linux 진단을 만들었다. 예약/PFN/범위/linear-map 검사를 통과해야 실행하며 과거 물리 주소를 입력받지 않는다. XNU로 분기하지 않는다.
- 실제 core C의 PC 버퍼 시험 12개와 실제 wrapper/checksum C의 모형 시험 13개가 통과했다. 예약·매핑 거부 11개 경로는 buffer read/write가 0회였다. 데이터 불일치 뒤에도 scrub을 수행했다. 프레임 판정과 수집기는 예약-only 성공을 RAM 접근 성공으로 취급하지 않는다.
- 전체 커널 빌드 성공: https://github.com/eirblue/ios_note10p/actions/runs/40188747894 (`113d074`). Image 46,350,348 bytes, SHA-256 `9ad212692ae020cde2ca6b25fa27118e825c7b54d25d89a380e1107a4df915fd`. 실제 Image의 build ID/접근 marker와 내장 CPIO 및 실제 init ELF 명령을 확인했다.
- 회귀 CI 성공: https://github.com/eirblue/ios_note10p/actions/runs/40189794445 (`b1f142d`). core/wrapper 시험 소스 해시가 실제 커널에 포함한 소스 해시와 일치한다.
- PC에서 BOOT-only 진단·원본 BOOT 복구 ZIP을 생성하고 현재 TWRP RAM에 전송했다. 실제 ZIP 해시·네이티브 updater 구문·현재 BOOT(v2)와 원본 non-BOOT 4개 파티션 대조를 통과했다. 수동 설치 대기이며 에이전트의 설치·재부팅·파티션 쓰기는 없다. 새 진단의 실기기 RAM 접근 및 재진입 결과는 아직 없다.
- 별도로 검증된 v2 과거 영역의 크기/정렬을 PC에만 재생하여 실제 XNU 버퍼 배치와 VM 호출 직전까지 1,053,279개 명령을 확인했다. 현재 TWRP RAM 사용이나 하드웨어 MMU/XNU 실행의 증거가 아니다. 상세 device_test/WINDOW-ACCESS.md.

## 2026-10-25: RAM 접근 진단 v3 실기기 통과

- 사용자가 v3 BOOT 진단을 직접 설치·부팅한 뒤 기존 TWRP로 돌아왔다. 읽기 전용 로그 수집에서 빌드 ID가 일치하는 N10RAM2 예약 기록 32개와 N10MEM1 접근 기록 30개를 확인했다.
- 두 패턴 전체 쓰기·읽기, 전체 zeroing/readback 완료, 불일치 0, status 0이다. 따라서 같은 Linux 부팅의 캐시 활성 RAM 접근 진단은 통과했다.
- 현재 BOOT 해시는 v3 payload와 일치하고 recovery/DTB/DTBO/vbmeta는 원본 해시와 일치한다. 로그·파티션 기록은 `note10/private/device-observations/`에만 저장했다.
- 약 169초의 `Fatal exception in interrupt`는 `hard_reset_hook_callback` 경로에서 기록됐다. 이는 접근 검사 완료 후의 hard-reset hook 기록이며 XNU 실행이나 임의의 메모리 오류로 해석하지 않는다. N10INIT1 IDLE 표식은 없고 CPU capability 진단 필드는 손상되어 해석하지 않았다.
- XNU memory image를 새 부팅의 예약 영역에 복사하고 source/destination SHA-256·zero tail을 검사하는 opt-in Linux staging path, strict N10XNU1 decoder, artifact materializer 및 수동 ZIP metadata 연결을 준비했다. 후속 빌드와 수동 패키지 준비 결과는 다음 절에 기록했다. 기존 `handoff_bundle.py`는 PC용 배치 모델만 제공한다. 동적 entry/boot_args 배치, live DT 변환, CPU/DMA 정지, cache/MMU/GIC 인계도 미완료다.
- 검증 범위는 캐시가 켜진 Linux의 예약 RAM 접근까지다. cache/MMU 전환, XNU 진입, iOS 구동 증거가 아니다. 자동 설치·재부팅·파티션 쓰기·kexec·XNU 실행은 수행하지 않았다.

## 2026-10-25: XNU RAM 적재 진단 v4 수동 시험 준비

- 실험용 source-built Mach-O에서 19,578,880-byte memory image를 만들고, 현재 부팅의 예약 영역에 복사·SHA256 readback·zero-tail 검사를 수행하는 Linux 커널을 빌드했다. XNU로 분기하지 않는다.
- 전체 Linux CI 성공: https://github.com/eirblue/ios_note10p/actions/runs/40202988576 (`03862d7`). Image 52,576,268 bytes이며 내장 CPIO와 XNU payload 포함 여부를 검증했다. Samsung 환경변수는 모든 build step에 적용하고 builder에서도 검사한다.
- 실제 적재 C 코드의 PC RAM 검증 17개 사례가 통과했다. 정상 적재, 예약·매핑 거부, 파일·할당·해시 오류, 복사 후 오류 시 scrub을 검사했다. Linux API는 모델이며 해시는 실제 SHA256이다. source/payload 해시를 해당 커널 보고서와 대조했다.
- 새 BOOT prototype은 52,580,368 bytes로 실제 57,671,680-byte BOOT 파티션에 들어간다. v3 BOOT를 현재 기준으로 묶은 진단 ZIP과 원본 BOOT 복원 ZIP을 비공개 로컬에 생성하고 TWRP RAM에 전송했다. ZIP 2개 해시·네이티브 설치 스크립트 문법·현재 5개 파티션 대조를 통과했다.
- 수동 설치 대기다. v4의 실기기 payload 적재, TWRP 재진입, XNU 실행은 아직 확인되지 않았다. 원시 로그·백업·설치 ZIP·기기 주소는 공개 저장소에 포함하지 않는다.

## 2026-10-25: v4 실기기 RAM 적재·읽기 검증 통과

- 사용자가 v4를 직접 시험하고 TWRP로 돌아왔다. 최신의 명확한 부팅 시작 배너부터 이어지는 한 구간에서 N10RAM2 10개, N10MEM1 30개, N10XNU1 27개의 온전한 체크섬 기록을 확인했다. 세 종류 모두 동일 빌드 ID와 예약 영역에 묶여 있다.
- 256MiB 두 패턴 쓰기·읽기와 전체 zero/readback이 불일치 0으로 완료됐다. 실험용 XNU 이미지 19,578,880 bytes의 source/readback SHA256 및 zero-tail 검사도 성공했다. BOOT는 v4 payload, recovery/DTB/DTBO/vbmeta는 각각 원본 해시와 일치한다.
- 전체 원본 로그는 여러 부팅의 중복 sequence 때문에 최초 수집에서 거부됐다. 수집기를 보완해 마지막의 온전한 0초 Linux 배너가 검증한 Image 배너와 정확히 일치할 때만 그 이후의 연속 구간을 선택한다. 원본·선택 범위·SHA를 보존하며, 이전 성공 부팅으로 돌아가거나 손상된 문자를 복원하지 않는다. 같은 구간 안의 중복이나 최신 부팅의 불완전한 기록은 계속 거부한다. 수집기 계약 검사 13개 통과.
- 최신 구간은 약 2.61초에 적재 성공을 기록했고 약 47초에 hard_reset_hook_callback 경로의 panic이 남았다. idle-init 표식과 정상 CPU capability 파싱은 확인되지 않아 해당 항목의 성공으로 확대하지 않는다.
- v4는 예약·RAM 접근·XNU 데이터 적재를 한 부팅에 검사했다. 이후에도 같은 실행 환경에서 가능한 진단은 묶어 수집하되, CPU/DMA 정지와 cache/MMU/GIC 전환·XNU 진입은 별도의 검증 경계를 유지한다. 실제 XNU 실행 및 iOS 부팅은 아직 미검증이다.

## 2026-10-26: v5 CPU·캐시 통합 실기기 시험 준비

- 선행 RAM·XNU 적재가 성공하면 Linux 보조 CPU 정지, payload cache clean/invalidate와 SHA256 재검사, CPU 복귀, 8개 CPU의 전체 payload 읽기와 EL/MMU/timer 상태 기록, 최종 SHA256 검사를 한 부팅에 수행하는 opt-in 진단을 추가했다. CPU 정지 시도 뒤에는 실패 경로에서도 복귀 함수를 호출한다. 선행 검사 실패 시 이후 단계는 실행하지 않는다.
- 실제 CPU/cache C의 PC 모델 21개, RAM wrapper 13개, core 12개 및 적재 C 17개 사례가 통과했다. Linux CPU/cache/register API는 모델이며 real SHA256과 실제 payload 전체 읽기를 사용했다. strict CPU decoder 6개, collector 14개, kernel preparation 6개 및 package 6개 검사도 통과했다.
- 전체 Linux CI 성공: https://github.com/eirblue/ios_note10p/actions/runs/40206140366 (`524286b`). Image 52,576,268 bytes, SHA256 `a86dac6ccd27ac00a095def4a84825dfcf8265644d5a82bada4a114bd1771dbf`. 내장 CPIO·진단 marker 및 CPU/cache 모델의 소스·payload 해시 binding을 확인했다.
- 실제 BOOT 크기 검증 후 현재 v4 BOOT를 설치 전 기준으로 묶은 진단·원본 복원 ZIP을 비공개 로컬에 생성하고 TWRP RAM에 전송했다. ZIP 2개 해시·네이티브 updater 문법·현재 5개 파티션 검사를 통과했다. 설치·재부팅은 수동 단계다.
- 이번 진단은 실제 CPU 상태를 바꾸므로 정지·복귀 도중 멈출 수 있으며 새 동작과 TWRP 재진입은 아직 실기기 시험 전이다. Linux MMU/cache는 유지하고 DMA/GIC 인계 및 XNU branch는 포함하지 않는다. 상세 [CPU-CACHE.md](device_test/CPU-CACHE.md).


## 2026-10-26: 첫 자동 설치·진단 부팅·TWRP 복귀·로그 수집

- 승인된 소스 c3770b0의 CI 40325362180이 17분 41초에 성공했다. 자동 복귀 C 모델 10개 및 PC 계약/회귀 검사 71개를 통과했다.
- per-cycle 토큰은 커널의 고정 volatile 데이터 슬롯 32바이트에 넣고, 컴파일 원본과 그 슬롯 외 모든 바이트가 같은지 검증했다. BOOT 명령줄 전달에 의존하지 않는다.
- TWRP CLI로 1회 설치하고 실제 5개 파티션 해시를 확인한 뒤 System으로 1회 부팅했다. uptime 약 2.319초의 arm과 93.162초의 recovery 요청 각각 16개 체크섬 프레임이 보존됐고, 새로운 TWRP 부팅 ID로 자동 복귀해 원시 로그를 수집했다.
- RAM 접근·XNU 데이터 적재·CPU/cache는 통과했다. 8개 CPU의 타이머 clear/restore 기록 256개도 정상이다. PM은 3회 모두 EBUSY(16)로 device 단계 전에 중단됐다. 각 시도에 USB·DECON 활성 wakeup source가 관측됐으나 개별 소스 인과관계는 미확정이다.
- 전체 진단 실패로 반복을 중단했다. 자동 왕복 자체는 성공했지만 반복 허용용 single_cycle_verified는 발급하지 않았다. 복귀 후 BOOT는 이번 진단 이미지이고 recovery/DTB/DTBO/vbmeta는 원본과 일치한다. 기기는 TWRP에 있으며 XNU는 실행하지 않았다.
- 다음 빌드 요청 확정: 화면 왼쪽 위 가로 1/2 × 세로 1/2(면적 1/4) 터미널 로그 창. 현재 generic console 경로로는 표시 불가하며 DPU 전용 경로가 필요하다. 요구사항/소스 조사는 완료, 구현·실화면 검증은 남았다. 비공개 quarter-screen-preparation-20261026/PLAN.ko.md 참조.


## 2026-10-27: 단일 부팅 묶음 평가

- USB/DECON 정상 PM 경로로 EBUSY를 해소한 뒤 RAM 접근, XNU 데이터 적재, CPU/cache 왕복, timer/PM, GIC PMR 복원, DMA 프레임워크, UFS/HCI 및 등록 IOMMU 관측을 한 빌드·부팅에서 검증했다. 항목별 필수 판정과 전체 판정을 함께 저장한다.
- [통합 커널 CI 40443986097](https://github.com/eirblue/ios_note10p/actions/runs/40443986097)와 새 실기기 1회 시험이 통과했다. 자동으로 새 TWRP 부팅 ID로 돌아왔고, BOOT 및 원본 비BOOT 4개 파티션의 해시를 확인했다. PC 회귀 181개, UFS/HCI 실제 C 42개, IOMMU 실제 C 21개가 통과했다.
- UFS의 클록 유지 콜백에서 HCE와 transfer/task doorbell 0을 관측했다. IOMMU는 등록 드라이버의 활성/runtime/PM 및 부팅 hold·secure 설정·페이지 테이블 존재 플래그를 읽었다. 주소나 원시 기기 로그는 공개하지 않는다.
- IOMMU의 정상 시스템 suspend 콜백은 late 단계에 등록되어 있어 devices-only 결과를 전체 하드웨어 DMA 정지로 확대하지 않는다. 실제 XNU 실행과 GIC/MMU 소유권 인계는 미검증이다. 상세 [IOMMU 관측](device_test/IOMMU-PM-AUDIT.md), [UFS/HCI 관측](device_test/UFS-PM-AUDIT.md).


## 2026-10-27: IOMMU 식별·정책 관측 묶음 통과

- [확장 커널 CI 40447515344](https://github.com/eirblue/ios_note10p/actions/runs/40447515344)와 새 실기기 시험이 통과했다. 기존 9개 진단 및 CPU 기능·자동 복귀·파티션 무결성을 포함한 평가 12개 중 12개가 통과했고, 모든 필수 항목이 통과했다.
- runtime/syscore/manual-control 대상 1개와 드라이버 정책상 활성 1개를 관측해 같은 세대의 집계와 대조했다. 실제 컨트롤러 이름과 주소는 비공개로 보관한다. 정책상 활성 여부를 실제 DMA 전송이나 하드웨어 정지 증거로 확대하지 않는다. PC 회귀 185개 및 실제 IOMMU C 25개가 통과했다.

## 2026-10-27: ABOX 추가 통합 빌드 통과, 실기기 충전 대기

- [통합 커널 CI 40452870987](https://github.com/eirblue/ios_note10p/actions/runs/40452870987)가 소스 `2baa761`에서 통과했다. ABOX 드라이버·runtime·IPC 큐 및 정상 콜백 결과 관측을 기존 진단에 추가했다. 핵심 진단 10개와 CPU 기능·자동 복귀·5개 파티션 무결성을 함께 평가하는 13개 항목 구성이며 항목별 판정과 전체 필수 판정을 유지한다.
- PC 회귀 194개, 실제 ABOX C 25개·IOMMU C 25개·UFS/HCI C 42개가 통과했다. 실제 Image·설정·소스/모형 결합·초기 실행 코드 검증과 비공개 단일 시험 패키지 준비도 완료했다.
- 배터리가 사용자 지정 하한 10% 미만이므로 새 빌드의 기기 전송·설치·재부팅은 수행하지 않았다. 직전 빌드의 실기기 12개 항목 통과 기록을 유지하며 ABOX의 새 실기기 결과는 충전 후 시험 대기다. ABOX 소프트웨어 유휴 관측도 DSP/전체 DMA 종료나 XNU 실행 증거로 확대하지 않는다. 상세 [ABOX 관측](device_test/ABOX-PM-AUDIT.md).

## 2026-10-27: ABOX 포함 실기기 묶음 13개 통과

- 사용자가 저배터리 안내 후 이번 시험 진행을 명시 요청했다. 정확한 단일 계획에만 7% 하한 예외를 기록해 1회 설치·부팅했고, 자동 TWRP 복귀 및 5개 파티션 무결성을 포함한 13개 평가가 모두 통과했다. 기존 일반 하한 10%는 유지하며 이번 예외는 재사용하지 않는다.
- ABOX 3개 단계의 상태 관측은 통과했으나 보수적 소프트웨어 유휴 조건은 충족하지 않았다. runtime 소유 및 대기 작업이 관측되어 ABOX/DSP나 전체 DMA가 정지했다고 판정하지 않는다. 상세 상태·콜백 이력·기기 로그·패키지는 비공개로 보관한다. 실제 XNU 실행은 여전히 미검증이다.

## 2026-10-27: ABOX 작업·큐 진행 관측 빌드 통과

- [통합 커널 CI 40456766748](https://github.com/eirblue/ios_note10p/actions/runs/40456766748)가 소스 `af14c01`에서 통과했다. 정상 IPC 작업의 시작·완료·진행 단계, 기존 runtime 요청 반환과 펌웨어 허용 검사, 큐 입출력 및 대기 상태를 추가했다. 원래 호출·반환·분기 동작은 유지하고 전원이나 참조 횟수를 강제 변경하지 않는다.
- PC 회귀 201개와 실제 ABOX C 36개·IOMMU C 25개·UFS/HCI C 42개가 통과했다. 실제 이미지·설정·소스/모형 결합·초기 실행 코드 검증 및 비공개 단일 시험 패키지 준비를 마쳤다. 기존 13개 평가 구성을 유지한다.
- 배터리가 기본 하한 10% 미만이므로 새 빌드의 기기 전송·설치·재부팅은 수행하지 않았다. 직전 1회 저배터리 예외는 재사용하지 않으며, 이 빌드의 실기기 결과는 충전 후 시험 대기다. 상세 [ABOX 관측](device_test/ABOX-PM-AUDIT.md).

## 2026-10-27: 작업·큐 관측 실기기 13개 통과

- 사용자의 이번 시험 요청 후 배터리 22%에서 정상 하한으로 1회 설치·부팅했다. 저배터리 예외는 사용하지 않았다. 13개 평가 모두 통과했고 자동 TWRP 복귀와 5개 파티션 무결성을 확인했다.
- ABOX IPC 작업은 완료됐으나 펌웨어 허용 검사에서 큐 처리가 거부되어 작업이 남았다. 해당 작업이 계속 실행 중이라는 가설은 관측 시점에서 제외했으며, 모든 runtime 소유자를 식별하거나 DSP/전체 DMA 정지를 증명한 결과는 아니다. 다음 빌드는 원래 펌웨어 반환과 PM 준비 콜백의 판단을 추가 관측한다. 상세 [ABOX 관측](device_test/ABOX-PM-AUDIT.md).

## 2026-10-27: 펌웨어·PM 준비 관측 다음 빌드 통과

- [통합 커널 CI 40510283132](https://github.com/eirblue/ios_note10p/actions/runs/40510283132)가 소스 `b4fd5e0`에서 통과했다. 펌웨어 다운로드 원래 반환값과 정상 ABOX PM 준비 콜백의 진입·정리 가능 판단·선택적 runtime suspend 및 반환 결과를 추가 기록한다. 원래 호출 순서·조건·반환을 유지하며 추가 전원·펌웨어·QoS 요청이나 flush를 수행하지 않는다.
- PC 회귀 207개, 실제 ABOX C 46개·IOMMU C 25개·UFS/HCI C 42개가 통과했다. 실제 Image·설정·소스/모형 결합·초기 실행 코드 검증 및 비공개 단일 시험 패키지 준비를 마쳤다. 기존 13개 평가를 유지한다.
- 이번 요청의 다음 빌드 컴파일·오프라인 검증까지 완료했다. 새 빌드의 기기 전송·설치·재부팅은 수행하지 않았으며, 설치된 직전 빌드의 13개 실기기 통과와 5개 파티션 무결성 기록을 보존했다. 새 관측의 실기기 결과, DSP/전체 DMA 종료 및 실제 XNU 실행은 아직 미검증이다.

## 2026-10-27: 펌웨어·PM 준비 실기기 13개 통과

- 사용자의 연결 완료 후 배터리 60%에서 통합 시험을 1회 진행했다. 13개 평가가 모두 통과했고 자동 TWRP 복귀와 5개 파티션 무결성을 확인했다.
- 원래 펌웨어 다운로드의 `EAGAIN`과 정상 PM 준비 경로의 완료를 함께 관측했다. 이후에도 runtime 소유와 대기 큐가 남아, 다음 빌드에는 AUD QoS의 요청 목표·적용값·작업 상태 및 정상 runtime get/put 관측을 묶었다. 강제 참조 조작이나 전원 변경은 추가하지 않는다. 상세 [ABOX 관측](device_test/ABOX-PM-AUDIT.md).

## 2026-10-27: AUD QoS 다음 통합 빌드 통과

- [통합 커널 CI 40516819807](https://github.com/eirblue/ios_note10p/actions/runs/40516819807)가 소스 `02e4f5f`에서 통과했다. AUD QoS 요청·적용값·첫 활성 대상·대기/실행 작업과 원래 runtime get/put 관측을 추가했다. 원래 조건·호출 순서·반환을 유지하며, 기존 13개 평가 구성에 함께 포함했다.
- PC 회귀 217개와 실제 ABOX C 66개·IOMMU C 25개·UFS/HCI C 42개가 통과했다. 원본 QoS target/apply/worker와 실제 관측 코드를 모형에서 실행했고, 실제 Image·설정·소스/모형 결합·초기 실행 코드 검증과 비공개 시험 패키지 준비도 완료했다.
- 새 빌드의 기기 전송·설치·재부팅은 하지 않았다. 설치된 직전 빌드의 실기기 13개 통과·자동 복귀·5개 파티션 무결성 기록을 보존했다. QoS의 실제 소유 원인, DSP/전체 DMA 정지 및 XNU 실행은 아직 증명하지 않았다.


## 2026-10-27: AUD QoS 실기기 통과·초기화 참조 관측 추가

- 정상 배터리 하한으로 v21 통합 시험을 1회 진행했고, 13개 평가·자동 TWRP 복귀·5개 파티션 무결성이 모두 통과했다.
- 관측 시 AUD QoS 목표·적용값과 대기·실행 작업은 0이지만 ABOX 사용 참조와 IPC 큐가 남았다. QoS 해제 작업 지연 가설은 확인되지 않아 호출 순서를 변경하지 않았다.
- 다음 빌드는 원래 초기화 get·후기 초기화 put의 반환 및 참조 수 전후, 후기 초기화의 기기 존재 분기를 관측한다. 지연된 probe 이전에 후기 초기화가 실행됐는지는 실기기 확인 대상이다. 기존 13개 평가를 유지하며 참조 수를 강제 변경하지 않는다. 상세 [ABOX 관측](device_test/ABOX-PM-AUDIT.md).


## 2026-10-27: 초기화 참조 관측 통합 빌드 통과

- [v22 통합 커널 CI 40522790002](https://github.com/eirblue/ios_note10p/actions/runs/40522790002)가 소스 `8fbe4a2`에서 통과했다. 원래 초기화 get·후기 초기화 put의 반환과 전후 사용 참조, 기기 존재 분기를 관측하며 기존 13개 평가를 유지한다.
- 회귀 220개와 실제 ABOX C 79개·IOMMU C 25개·UFS/HCI C 42개가 통과했다. 실제 Image·설정·소스/모형 결합·초기 실행 코드와 비공개 단일 시험 계획·패키지 검증까지 완료했다.
- 이번 요청의 v21 실기기 시험과 다음 빌드 컴파일까지 완료했다. v22 실기기 시험은 대기 상태이며 초기화 순서 가설·DSP/전체 DMA 종료·XNU 실행은 아직 검증하지 않았다. 기본 배터리 하한 10%를 유지한다.


## 2026-10-28: 초기화 참조 관측 실기기 13개 통과

- 정상 배터리 하한으로 v22 통합 시험을 1회 진행했다. 13개 평가·자동 TWRP 복귀·5개 파티션 무결성이 모두 통과했다.
- 초기화의 원래 runtime get과 후기 초기화의 원래 put이 모두 실행됐고 각 호출 전후의 사용 참조가 정상 증가·감소했다. 후기 초기화 누락 가설은 확인되지 않았다. 이후 남은 참조는 다른 경로 추적 대상이며, 전체 소유권이나 DSP/전체 DMA 정지 증거로 확대하지 않는다.
- 사용자가 결과 기반 테스트·빌드의 직접 반복을 승인했다. 자정 안전 지점에서 비공개 요약을 새 세션으로 인계하고 다음 경로 분석·빌드·실기기 시험을 이어간다. 10분 주기 예약은 생성하지 않는다.


## 2026-10-28: v32 CPU 복원·페이로드 묶음 시험 통과

- [v32 통합 커널 CI 40624098218](https://github.com/eirblue/ios_note10p/actions/runs/40624098218)와 새 실기기 시험 1회가 통과했다. 기존 22개와 새 2개를 묶은 평가 24개가 모두 통과했다.
- PM 복귀 후 8개 CPU의 아키텍처 설정 비교와 페이로드 읽기 검사가 통과했다. 자동 TWRP 복귀와 5개 파티션 무결성도 통과했으며 설치 직전 배터리는 21%였다.
- PC 회귀 275개, 실제 관측 코드 C 오류 주입 37개, 조합된 PM 작업 경로 8개가 통과했다. 전체 DMA 종료, GIC/MMU/cache 인계 및 XNU 실행은 검증되지 않았다. 상세 [PM 이후 CPU 관측](device_test/PM-POST-ARCH-AUDIT.md).

## 2026-10-28: v33 PM 경계 읽기 전용 관측 시험 통과

- 공개 소스 `4fec819`, [통합 커널 CI 40632421099](https://github.com/eirblue/ios_note10p/actions/runs/40632421099)와 새 실기기 시험 1회가 통과했다. 기존 평가와 새 3개를 묶은 27개 평가, 자동 TWRP 복귀 및 사후 5개 파티션 무결성 검사가 모두 통과했다.
- PM 목록 1,388개 중 DMA 가능 장치는 277개였다. late/noirq 경계에서 각각 276개는 해당 PM 플래그가 설정됐고 1개는 syscore 예외였으며 미포함 범주는 0개였다. 이 값은 프레임워크 경유 여부이며 하드웨어 DMA 정지를 뜻하지 않는다.
- 등록 IOMMU 18개 중 17개에서 해당 late/noirq 플래그를 관측했고 1개는 syscore 예외였다. 드라이버 소프트웨어 조건상 active 12개, runtime-active 0개였다. syscore callback 등록 11개는 시험 전후 순서와 이름이 동일했다. [PM-EDGE-INVENTORY.md](device_test/PM-EDGE-INVENTORY.md)에 관측 범위와 한계를 기록했다.
- 실제 syscore 호출, 전체 DMA 정지, GIC/MMU/cache 인계, XNU 실행과 iOS 부팅은 확인하지 않았다.


## 2026-10-28: v34 CPU0 IRQ 관측 실기기 통과

- 공개 소스 `4cec79508c0bfaf09f12435b8ca6d981c0833f75`의 [통합 커널 CI 40636741343](https://github.com/eirblue/ios_note10p/actions/runs/40636741343)가 통과했고 실기기 1회에서 29개 평가가 모두 통과했다. 설치 직전 배터리는 11%였다.
- CPU0 IRQ 켜짐·꺼짐·복원 세 단계에서 아키텍처 및 타이머와 읽기 전용 GIC 비교가 통과했고 원래 IRQ 및 CPU 상태가 복원됐다. 자동 TWRP 복귀 및 사후 5개 파티션 해시 검사도 통과했다. PC 회귀 275개가 통과했다. 상세 [CPU0 IRQ 관측](device_test/PM-IRQ-AUDIT.md).
- 전체 DMA 정지, 실제 syscore 실행, MMU/cache 인계, XNU 실행과 iOS 부팅은 검증되지 않았다.

## 2026-10-28: v35 PM callback 메타데이터 실기기 통과

- 공개 소스 `591174d428082dec154ee3a078be30b923ccd8c2`의 [통합 커널 CI 40695605629](https://github.com/eirblue/ios_note10p/actions/runs/40695605629) 두 번째 시도가 통과했다. 새 실기기 시험 1회에서 기존 평가를 포함한 33개 평가 모두 통과했고 설치 직전 배터리는 91%였다.
- CPU-PM notifier, generic IRQ, clocksource, clockevent의 세 시점 메타데이터 검사가 통과했다. 원래 CPU 상태 복원, 자동 TWRP 복귀와 사후 5개 파티션 해시 검사도 통과했다. 등록된 callback은 가능한 경로이며 호출 실행을 뜻하지 않는다. [관측 범위와 한계](device_test/PM-CALLBACK-INVENTORY.md).
- XNU 입력 재빌드의 기존 결과와 차이는 UUID 및 빌드 시각 메타데이터에 한정됐고 실행 코드·나머지 데이터는 같았다. 실제 XNU 실행, iOS 부팅, 전체 DMA 정지, syscore 실행과 MMU/cache 인계는 검증되지 않았다.

## 2026-10-28: v36 CPU PM 실패 경로 보호와 실기기 회귀 통과

- 공개 소스 `0f1584873b667a88ed2f0e37e43f1ea6d1c62ad0`의 [통합 커널 CI 40705922907](https://github.com/eirblue/ios_note10p/actions/runs/40705922907)이 통과했다. CPU 및 클러스터 PM 진입의 notifier 호출 횟수를 초기화하고, 클러스터 진입 실패 시 원래 오류를 유지하면서 앞선 CPU 진입을 한 번 정리한다.
- 실제 Image 컴파일과 최종 소스 검증을 병행했다. PC guard 모형 19개, 프로세스 수명 검사 6개와 deadline 경계, 결합 변이 검사 12개가 통과했다. 기존 33개 평가의 실기기 회귀를 한 번 수행해 모두 통과했고, 설치 직전 배터리 97%, 자동 TWRP 복귀와 5개 파티션 해시를 확인했다. [관측 범위와 한계](device_test/PM-CALLBACK-INVENTORY.md).
- 하드웨어 CPU PM 실패 주입이나 직접 syscore 호출은 검증하지 않았다. 전체 DMA 정지, MMU/cache 인계, XNU 실행과 iOS 부팅도 확인하지 않았다.
