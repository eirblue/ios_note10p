# 작업 상태 (2026-10-20, Asia/Seoul)

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
