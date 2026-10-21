# 실기기 적용 전 PC 검증

현재 **적용 준비 미완료**다. 이 절차는 부품 컴파일과 합성 검증을 재실행하며,
전체 XNU나 Note10 부팅 이미지를 생성하지 않는다.

사용자의 작업 범위는 실기기 적용 전까지다. 아래 runner에는 ADB·기기 쓰기·재부팅·언락·플래시 단계가 없다.
기존 `compat/run_target_tests.ps1`과 기기 수집기는 이 절차에서 호출하지 않는다.

## 재현

프로젝트 루트에서, 현재 구성된 Windows Python/Unity NDK 환경을 사용한다.

```powershell
C:\Python314\python.exe note10/predevice.py
```

- 원본 IPSW SHA256, 활성 사용자 공간 3개 파일의 해시/버전, 공개 XNU 참조 식별자를 검사한다.
- 호환성·GIC 부품을 ELF/Apple Mach-O 객체 및 Android 시험 바이너리로 컴파일한다.
  Android 시험 바이너리는 PC에서 실행하거나 기기에 전송하지 않는다.
- capability ELF를 재빌드하고 합성 레지스터 검사·불량 기록 거부 검사를 실행한다.
- XNU 선택·timer·IRQ bridge·bootstrap 패치를 재생성하고 합성 검사를 실행한다.
- bootstrap 통합 검사에서는 실제 binder/GIC core/MMIO/IRQ handler를 함께 링크한다.
  DT·CPU 레지스터·MMIO·커널 서비스는 합성이므로 실제 인터럽트 전달 증거는 아니다.
- 패치 7개/18개 파일을 격리 소스에 순차 적용·복원하고 원본 보존을 검사한다.
- 입력형 Exynos 보드 헤더 22종 및 실제 bootstrap/IRQ C 파일의 Mach-O 객체 4개를 검사한다.
  cache/page 값은 합성 입력이며 실측 보드 설정이 아니다. 상세 [xnu26/BOARD.md](xnu26/BOARD.md).
- SoC MASTER 설정 텍스트 3종과 플랫폼 archive 입력의 GNU Make 검사 17종을 실행한다.
  실제 XNU config 도구·전체 링크를 실행한 것은 아니다. 상세 [xnu26/MASTER.md](xnu26/MASTER.md).
- 이어서 실제 XNU config 도구의 Windows 빌드·24개 native 구성 생성·907개 source export·실제 C 파일 10개 컴파일을 검증한다.
  별도 전체 C audit는 585/863개 컴파일·278개 실패 및 생성 C 40개 미준비 상태다. 상세 [xnu26/NATIVE-WINDOWS.md](xnu26/NATIVE-WINDOWS.md).
- 준비한 수동 macOS CI의 형태와 입력 생성 부분을 PC에서 검사한다. 실제 원격 실행은 하지 않는다. [인증 단계](xnu26/CLOUD.md).
- 실제 XNU 헤더로 include 순서 회귀를 검사한다. VMAPPLE 대조군만 syntax 통과하며,
  Exynos의 `processor not supported` 실패는 미해결 보드 설정의 증거로 유지한다. 상세 [xnu26/HEADERS.md](xnu26/HEADERS.md).
- 소스·문서·패치 입력 해시를 전후 비교한다. 생성기가 패치 바이트를 바꾸면 검사는 실패한다.

결과는 `private/predevice/report.json`, 각 단계 출력은 같은 폴더의 `.log`에 저장한다.
이전 결과를 재사용하지 않고, 실패 단계 이후의 의존 검사를 중단한다.

종료 코드는 **0을 사용하지 않는다**. `1`은 부품 검사 실패, `2`는 부품 검사 통과지만
적용 조건 미충족이다. `deployment_ready`는 현재 구현에서 항상 `false`다.
이 플래그를 수동 변경해도 준비 완료의 근거가 되지 않는다.
헤더 probe의 성공 또한 예상한 회귀 결과의 일치를 뜻하며 Exynos 컴파일 성공이 아니다.

## 남은 작업

| 조건 | 현재 상태 / 필요한 증거 |
|---|---|
| 전체 커널 | native config/header 생성·일부 C 컴파일 완료. Apple builtin·나머지 코드/생성 입력·플랫폼 archive·C++/ASM·전체 링크 미완료 |
| 메모리·진입 계약 | 실제 진입 EL, 안전한 RAM/예약 영역, MMU/cache/granule 및 진단 회수 경로 미확정 |
| GIC handoff | 사전 초기화된 상태의 실제 생산자·소유권·priority/trigger 설정 미확정 |
| 사용자 공간 | PAC 키/예외/loader 연결 및 iOS 프로세스 실행 미완료 |
| 장치 드라이버 | storage/APFS 부팅 경로, 화면·터치 등 통합 미완료 |
| 배포 산출물 | 링크된 커널, Samsung 부팅 이미지 및 복구 절차 검증 없음 |
| 소스 ABI | public 12377.121.6과 대상 12377.122.8의 차이 미검증 |

실기기에서만 확인 가능한 항목은 관측 없이 확정하지 않는다. PC 합성 검사 통과만으로
이 항목을 통과 처리하거나 임의 주소로 실행 이미지를 만들지 않는다.

## 추가 빌드 경로 조사

[darwin-xnu-build README](https://github.com/blacktop/darwin-xnu-build#build-the-xnu-library-macos-260)
확인 결과, 공개 `xnu-lib` bundle의 기본 archive는 커널 구현 전체가 아니라 qsort/version 부품과
생성 헤더·export 자료다. 따라서 이를 내려받아 전체 Exynos 커널 링크를 대체할 수 없다.
해당 프로젝트의 전체 빌드 절차 역시 Xcode를 요구한다. 현재 Windows NDK 부품 빌드를
전체 Darwin 빌드 환경 확보로 취급하지 않는다.
