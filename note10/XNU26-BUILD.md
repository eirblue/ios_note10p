# XNU 12377 공개 소스 빌드 조사

사용자에게 Mac/원격 macOS 환경이 없음을 확인했으며 Windows에서 가능한 분석·부품 교차 컴파일을 진행한다.
현재 확보한 소스는 Apple의 xnu-12377.121.6, commit ac9718fb1af618d5ce8678d0dc6e8a58f252216f다.
실제 IPSW의 12377.122.8과 동일한 버전으로 취급하지 않는다.

## 확인한 빌드 조건

소스 README와 makedefs/MakeInc.cmd·MakeInc.def를 직접 확인했다.

- 기본 빌드 경로는 xcrun으로 SDK/도구를 찾는다. 현재 Windows PATH에는 make/xcrun/xcodebuild가 없다.
- 이후 Unity NDK 내부의 Windows GNU Make 4.2.1을 발견해 빌드 선택 fragment 검사에 사용했다.
  전체 Darwin 도구 체인이 확보된 것은 아니다.
- README의 외부 Apple silicon 빌드 경로는 Xcode·SDK·KDK 및 AvailabilityVersions/headers/libfirehose 준비를 요구한다.
- ARM64 기본 아키텍처 선택은 arm64e 경로를 포함한다. PAC 없는 Exynos에서 그대로 사용할 수 있다고 가정하지 않는다.
- 공개 ARM64 기기 목록은 T6000…T8142, VMAPPLE 계열이며 Note10+/Exynos9825 기기 구성은 없다.
- NONE 이외 기기 구성은 KDK의 기기별 KernelSupport archive를 링크한다.
  Apple 기기용 archive가 Exynos 플랫폼 드라이버를 제공하는 것은 아니다.

따라서 단순히 make 명령의 기기 이름을 바꾸는 것으로 Note10+ 커널을 만들 수 없다.
현재는 빌드 의존성/플랫폼 대체 경로를 조사한 단계이며 전체 XNU 컴파일·링크는 수행하지 않았다.
Android NDK로 만든 freestanding ELF/Apple Mach-O 부품 객체와 전체 커널 빌드는 구분한다.

## 기존 V60 패치 대조

81개 패치를 **각각 pristine 12377.121.6 소스에 git apply --check**로 대조했다.
1개(`0006-sweet-master-config-open-source-asm-pmap.patch`)만 독립 검사에서 적용 가능했고 80개는 실패했다.
누적 적용 가능성이나 빌드 성공을 검사한 결과가 아니며, 실제 소스에 적용한 패치는 없다.
세대가 다른 patch 묶음을 일괄 적용하는 경로 대신 변경 내용을 다시 검토해야 한다.

재현: `python note10/audit_xnu_build.py`.
각 패치 진단·host 도구·기기 구성·소스 식별 기록은 `research/ios26/xnu-build-audit.json`에 저장한다.

## 다음 구현의 선행 조건

1. 공개 소스에서 Exynos용 non-PAC kernel 구성 및 플랫폼 초기화 경로 정의.
2. 현재 GICv2 부품을 실제 mapping·ordering·IRQ vector와 연결하고 timer/MMU/메모리 계약 확인.
3. 사용 가능한 최신 Darwin cross-build 도구·SDK/지원 라이브러리 조합 확보 및 최소 링크 검증.
4. 12377.121.6 기반 커널과 26.5.2 사용자 공간의 ABI 차이 검증.

이 조건들이 해결되기 전에는 부팅 가능한 커널이라고 표시하지 않는다.

첫 빌드 선택 패치는 [xnu26/README.md](xnu26/README.md)에 있다. Exynos용 plain ARM64·ARMv8.2 및
BTI 선택을 분리했고 GNU Make 설정 9종·격리 apply/reverse 검증을 통과했다.
참조 소스는 그대로이며 보드 profile·플랫폼 연결과 전체 빌드는 여전히 미완료다.

## 실제 헤더 검사 추가

`probe_kernel_headers.py`로 checksum 고정된 공개 생성 헤더 263개를 확보했다.
생성 자료의 version.c는 참조와 같은 12377.121.6을 표시하지만 설정은 VMAPPLE이므로 Exynos용으로 재사용하지 않는다.
실제 헤더 검사에서 Note10 두 소스의 cpu_topology 직접 include 문제를 발견해 machine_routines 경유로 수정했다.
수정 전 VMAPPLE 대조군은 cluster_type_t 오류, 수정 후 대조군은 syntax 통과한다.
수정 후 Exynos는 proc_reg.h의 `processor not supported`에서 실패한다. 아직 보드/CPU 정의가 없기 때문이다.
전체 커널 또는 Note10 소스 unit 전체 컴파일 결과가 아니다. 재현·제약은 [xnu26/HEADERS.md](xnu26/HEADERS.md).

## Windows native 설정 도구 및 실제 소스 컴파일

휴대용 Clang 23과 Flex/Bison으로 XNU 원본 config 도구를 Windows 실행 파일로 빌드했다.
24개 구성의 Makefile·421개 feature header를 생성했고 원본 Makefile export 목록에서 907개 헤더를 배치했다.
실제 핵심 C 10개가 컴파일됐으며 전체 C audit는 585/863개 성공·278개 실패다. 생성 C 40개, C++/ASM 및 전체 링크는 미완료다.
일반 LLVM에 없는 Apple XNU builtin이 주요 차단 조건으로 확인되어 수동 macOS CI를 준비했다.
현재 GitHub CLI 로그아웃 상태로 원격 작업은 하지 않았다. [NATIVE-WINDOWS.md](xnu26/NATIVE-WINDOWS.md), [CLOUD.md](xnu26/CLOUD.md).
