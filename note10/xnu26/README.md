# XNU 12377: Exynos9825 build selection

첫 패치는 xnu-12377.121.6의 `makedefs/MakeInc.def`에만 적용하는 **빌드 선택 설정**이다.
완성된 Note10+ 보드 구성이나 커널 이식 패치가 아니다.

## 구현

- 정상 ARM64 기기 목록에 EXYNOS9825 추가.
- EXYNOS9825 기계어 옵션: `-DARM64_BOARD_CONFIG_EXYNOS9825 -march=armv8.2-a+crypto`.
- 일반 kernel target 경로에서 architecture를 plain `arm64`로 고정; command-line `arm64e`도 덮어쓴다.
- 해당 기기에 한해 BTI build를 0으로 고정하여 BTI compiler instrumentation을 선택하지 않는다.
- 다른 Apple 기기의 기존 선택은 보존한다. simulator/host용 xnu build 경로는 이 패치 대상이 아니다.

`prepare_build_selection.py`는 활성 target의 pinned source 파일 SHA-256을 확인한 뒤 패치를 생성한다.
새 소스 내용이나 문맥이 달라지면 자동 추정 적용을 하지 않고 실패한다.
참조 소스는 수정하지 않고, 실제 apply/reverse 검증은 별도 private stage에서 수행한다.

## 검증

기존 Unity Android NDK에 포함된 Windows GNU Make 4.2.1을 발견해 사용했다.
XNU 소스에서 실제 선택 관련 Make fragment를 추출해 GNU Make로 평가했다.

- EXYNOS9825: 입력 architecture 공백/arm64/arm64e × 입력 BTI 0/1, **6종 모두 arm64·BTI 0**.
- T8101/T6050/VMAPPLE: 기존 소스와 결과 비교 **3종 통과**.
- pinned pristine source에 `git apply --check` 통과.
- 격리 stage의 실제 apply 결과와 예상 전체 파일 bytes 일치, reverse 후 원본 bytes 일치.
- Git의 전역 CRLF 설정과 무관하게 LF를 유지하도록 해당 명령에서만 core.autocrlf=false 사용.
- pristine 소스가 변경되지 않았음을 SHA와 bytes로 확인.

결과는 `note10/private/xnu26-selection/result.json`에 저장한다.
검사는 Make 선택 fragment에 한정한다. 전체 Makefile 평가, 생성 config header, 컴파일·링크 검사가 아니다.

재현:

```powershell
python note10/xnu26/prepare_build_selection.py
```

## 아직 구현하지 않은 부분

EXYNOS9825 이름을 목록에 넣는 것만으로 빌드 가능한 플랫폼이 생기지 않는다.
현재 `board_config.h`의 Exynos 분기·CPU/cache/page geometry·MASTER profile, platform support archive 대체,
GIC cold 초기화·MMU/부트 진입과 실제 하드웨어 검증은 미구현이다. 첫 선택 패치는 Apple platform support archive 링크를 제거하거나
필요한 기능을 no-op으로 채우지 않는다.
NDK GNU Make 확보는 Xcode/SDK/KDK 및 최신 Darwin compiler/linker 미확보 문제를 해결하지 않는다.
ARM64e 사용자 공간을 plain ARM64 kernel에서 실행하는 호환성도 별도 구현·검증이 필요하다.

이 패치를 적용한 전체 커널이나 부팅 이미지는 아직 만들지 않았다.

보드 설정의 미확정 cache/granule 값을 수집하기 위한 [privileged 진단 entry](../shim/README.md)를 추가했다.
연구용 ELF와 PC 합성 시험까지만 완료했으며, 실제 CPU 값을 취득하거나 보드 header를 확정한 단계는 아니다.

두 번째 패치는 [Exynos 물리 decrementer 선택](TIMER.md)이다. 실제 소스 함수 fragment를 컴파일하고
합성 register 환경에서 39종을 검사했다. 전체 커널 컴파일이나 실제 타이머 IRQ 전달 검증은 아니다.
패치 순서는 `patches/series`에 기록한다.

세 번째 패치는 [GICv2 타이머 IRQ bridge](IRQ.md)다. XNU IRQ 진입에서 타이머 callback과 EOI까지의
소스 경로를 추가하고 합성 20종을 검사했다.

네 번째 패치는 [검증된 handoff의 mapping·최초 binding 호출](BOOTSTRAP.md)을 추가한다.
합성 20종과 4개 패치/12개 파일의 순차 적용·복원 검사를 통과했다. 실제 GIC cold 초기화와
handoff 생산자, 보드/메모리 구성 및 전체 커널 빌드는 아직 미완료다.

다섯 번째 패치는 [명시적 입력형 Exynos 보드 헤더](BOARD.md)다. 실측값 기본값은 없으며,
합성 입력으로 실제 bootstrap·IRQ bridge 파일 전체의 Mach-O 객체를 생성했다.
현재 series는 5개 패치/17개 파일이다. 완성된 물리 보드 설정·MASTER·전체 커널 빌드는 아니다.

여섯 번째 패치는 [Exynos SoC MASTER·명시적 플랫폼 archive 입력](MASTER.md)이다.
설정 텍스트 3종과 GNU Make 입력 검사 17종을 추가했다. 현재 series는 6개 패치/18개 파일이며,
실제 config 도구 실행·생성 헤더·완성된 플랫폼 archive·전체 커널 링크는 아직 없다.

이후 [Windows native config·C audit](NATIVE-WINDOWS.md)에서 실제 config 도구와 24개 구성/421개 feature
헤더를 만들었다. 현재 series는 예외 header 범위 수정까지 7개 패치/18개 파일이다.
전체 C audit는 585/863개 컴파일·278개 실패이며 완성된 플랫폼 archive/커널 링크는 없다.
Apple Clang을 위한 [수동 macOS CI](CLOUD.md)를 준비했지만 사용자 GitHub 인증 전이라 실행하지 않았다.
