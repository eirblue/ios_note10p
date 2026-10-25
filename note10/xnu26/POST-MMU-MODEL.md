# XNU 가상 주소 진입 PC 모델

실기기 RAM 예약 결과와 독립적으로 준비한 검증이다. 실제 MMU를 켜거나 기기에서 XNU를 실행하지 않는다.
검토한 source-built Mach-O의 SHA-256을 고정하고 실제 adapter와 XNU 명령을 사용한다.

기존 시작 모델은 실제 startup 코드의 페이지 테이블 생성과 MMU 활성화 직전까지를 실행한다.
새 continuation은 그 결과를 검증한 뒤 MMU 활성화 명령을 **실행하지 않고 모델링**한다.
커널·메타데이터의 가상 주소 별칭을 소프트웨어 복사본으로 만들며, 각 16K 페이지의
처음/끝 주소를 XNU가 만든 테이블로 walk해 확인한다. 실제 CPU 주소 변환은 아니다.

가상 주소 복귀 이후 실제 명령이 `_arm_init`에 도달하는지, x0가 가상 boot_args 주소인지,
전달 내용이 유지되는지, interrupt/exception stack이 실제 linked symbol과 일치하는지 검사한다.
이어 C 함수의 첫 직접 호출 `_static_if_init` 직전까지 실행하고 멈춘다. 해당 호출은 실행하지 않는다.
모든 추가 instruction fetch와 데이터 read/store를 테이블의 주소 변환 결과와 대조한다.
가상 store의 물리 복사본은 검사기가 명시적으로 갱신한다. 하드웨어 coherence 시험이 아니다.

로컬 결과는 세 합성 RAM 배치에서 각각 다음과 같다.

- 기존 MMU 이전 명령: 24,999 / 24,999 / 24,807개.
- 추가 실행: 각 51개 명령, instruction fetch 51회, 데이터 read 1회, kernel store 18회.
- 가상 별칭 페이지 1,199개 확인; boot_args와 스택 전달 검사 통과.
- 실제 모형 RAM의 L2 descriptor 주소 비트 손상 및 잘못된 boot_args 포인터 주입은 거부.
- 기존 continuation 없는 세 사례도 원래 명령 수와 MMU 이전 정지를 유지.

주소는 합성 입력이다. 실제 예약 주소로 사용하면 안 된다. 기존 실측 CPU capacity profile과
비교한 로컬 검사도 있지만 시스템 레지스터·CLIDR/cache·TLB는 여전히 모형이다.
SCTLR/MMU 전환, stage-1 permission fault, cache/TLB 정합성, GIC/timer 소유권,
Linux CPU/DMA 종료 및 C 초기화 완료를 증명하지 않는다. XNU/iOS 실기기 부팅 결과도 아니다.

```text
python note10/xnu26/test_post_mmu_entry.py --kernel-build NATIVE_BUILD --adapter ADAPTER_ELF --output PRIVATE_NEW_DIRECTORY --observed-profile PRIVATE_PROFILE
```

관측 profile 옵션은 생략 가능하다. 결과·생성 버퍼는 private에 보관하고 기존 출력은 덮어쓰지 않는다.
새 GitHub 수동 workflow는 기존 공개 소스 빌드 run 39560904016의 artifact를 읽고 동일 모델을 실행한다.
그 artifact의 보존 기간이 끝나면 해당 workflow는 다운로드에서 실패하며, 다른 바이너리를 자동 대체하지 않는다.
커널 해시나 첫 호출 경계가 바뀌면 별도 검토 후 검증 계약을 갱신해야 한다.

로컬의 실측 capacity 비교 포함 모델 및 공개 artifact 기반 CI 모두 통과했다.
최종 CI: https://github.com/eirblue/ios_note10p/actions/runs/40167184145 (`6a4ba1d`).
