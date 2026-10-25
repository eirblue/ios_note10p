# Galaxy Note10+ 네이티브 iOS 포팅

목표는 Android 위의 앱이나 에뮬레이터가 아닌, 기기에서 XNU와 iOS 사용자 공간을 부팅하는 것이다.
현재 대상은 사용자 지정 **iPhone18,1 / iOS 26.5.2 (23F84)** 이다. 실제 취득/소스 상태는 [IOS26.md](IOS26.md),
활성 설정은 [target.json](target.json), Samsung 펌웨어 관측은 [HARDWARE.md](HARDWARE.md)를 본다.
이전 iOS 27 분석·검사 결과는 별도 역사 기록으로 보존한다.
현재 단계는 **하드웨어 분석 및 호환성·초기 플랫폼 부품 구현**이다. Android에서 부품 검사는 수행했지만,
합성 보드 입력을 사용한 ARM64 XNU 실행형 링크는 성공했다. XNU용 Samsung 부팅 이미지와 실제 iOS 실행 결과는 없다.
별도 Linux 커널 진단용 수동 BOOT 시험·복구 패키지는 [2단계 안내](device_test/LINUX-CAPS.md#수동-boot-시험-패키지)를 따른다.
최신 진행은 [STATUS.md](STATUS.md)를 본다.

실기기 적용 전까지의 현재 PC 작업 범위·재현 명령과 미완료 조건은 [PREDEVICE.md](PREDEVICE.md)에 있다.

## 기준 소스

- https://github.com/ch1tmdgus/ios-v60
- 조사한 커밋: `3ff7ba8d7f9f59a10b0497039b684e975cee0f91` (2026-10-20 복제)
- 상위 프로젝트: https://github.com/dipa-studio/ios-sweet

V60 동작 보고와 Note10+에서의 재현은 별개의 검증이다. 기준 저장소도 동작 boot2 이미지의 전체 빌드 재현은 미확인으로 명시한다. 고정 주소를 사용하는 touch 이미지 패처는 Note10+에 적용할 수 없다.

## 먼저 필요한 정보

연결된 기기는 **SM-N976N / Exynos 9825 / Android 12**로 확인했다. 설치 빌드 N976NKSU2HWH5,
제공 펌웨어 N976NKSU2HXJ2이며 서로 다르다. 조회 시 부트로더 locked, OEM unlock allowed=0이다.
일반 ADB로 live DT를 읽을 수 없었으므로 실제 선택된 overlay·메모리 배치는 미확정이다.

PC의 프로젝트 루트에서 읽기 전용 수집:

```powershell
python note10/collect_device.py
# 접근 권한이 있는 경우에만 실제 FDT도 수집 (개인 식별 정보 포함 가능)
python note10/collect_device.py --fdt
```

USB 디버깅 허용이 필요하다. 권한이 없는 항목은 실패를 기록하며, root 전환이나 언락을 수행하지 않는다.
결과는 Git 제외 경로 `note10/private/`에 보관한다. FDT, 펌웨어, 기기 덤프는 공개 커밋하지 않는다.

## 이식 대상과 근거

| 영역 | 기존 코드 | Note10+에서 필요한 확인 |
|---|---|---|
| 부팅 진입·이미지 포맷 | `shim/start.S`, `shim/build.sh` | 원본 boot/recovery 헤더, DTB/DTBO 위치, 진입 EL 및 부트로더 전달 값 |
| 메모리·MMU | `shim/mmu.c`, `tools/mkadt.py` | 실제 RAM/예약 영역, 로드 주소, CPU별 16 KiB 페이지 지원 |
| 인터럽트·타이머·SMP | `shim/shim.c`, XNU 패치 | GIC 종류/주소, 타이머 주파수·IRQ, PSCI 및 CPU 토폴로지 |
| 전원·watchdog | `shim/shim.c` | 기기별 watchdog/PMIC/reset 경로; Qualcomm MMIO 상수 재사용 금지 |
| 화면 | `shim/console.c`, `tools/mkadt.py`, XNU 패치 | 부트로더 framebuffer 유지 여부, 주소/stride/포맷, 패널 전원 |
| 저장장치 | `shim/ufs.c`, XNU 패치 | UFS host/PHY/clock/IOMMU, 읽기 전용 접근부터 확인 |
| 터치·버튼 | `v60-touch/`, XNU HID 패치 | 실제 컨트롤러, 버스, GPIO/IRQ, 좌표 변환 |
| 사용자 공간 | payload/ADT 도구 | 호환 iOS 빌드, root 이미지 구성, 필요한 Apple 파일 및 의존 서비스 |

Exynos 9825이면 Qualcomm용 저수준 드라이버 대부분을 대체해야 한다. Snapdragon 변형도 SM8250 V60의 주소·드라이버 호환성을 가정할 수 없다. 모델 확정 전에는 MMIO 주소를 임의로 작성하지 않는다.

참조 후보(기기와 펌웨어 일치 여부는 추후 확인):

- https://github.com/ExtremeXT/android_device_samsung_exynos9820 — d2s 등 기기 구분 및 recovery 구성
- https://github.com/ianmacd/d2s — Samsung d2 계열 커널 DTS 참고
- https://semiconductor.samsung.com/processor/mobile-processor/exynos-9825/ — SoC 설명

## 완료 기준과 순서

1. 모델·언락·원본 복원 경로와 기기별 하드웨어 자료 확정.
2. 기기별 최소 shim 진입 및 관측 가능한 로그 확보. 아직 iOS 부팅이 아님.
3. 예외/MMU/타이머 IRQ 검증 후 단일 코어 XNU 콘솔 진입.
4. 저장장치 읽기와 root 마운트, launchd 및 SpringBoard 진입.
5. 터치·버튼, 재부팅 반복 및 안정성 검증.
6. GPU, 충전·배터리·온도, 절전, 통신, 오디오, 카메라 등 정상 사용에 필요한 기능별 검증.

각 단계는 실제 로그와 테스트 결과가 있어야 통과한다. GUI 한 번 표시는 정상 구동 완료로 간주하지 않는다.
V60용 `fastboot boot` 명령을 Samsung 기기에 그대로 안내하지 않는다. 실제 기기의 다운로드/복구 경로를 먼저 확인한다.

## 파일 요청 규칙

공개 소스와 도구는 직접 취득한다. 사용자에게는 모델 확정 후 직접 취득할 수 없는 다음 항목만 구체적으로 요청한다.

- 현재 펌웨어와 일치하는 원본 boot/recovery/DTB/DTBO 및 필요한 패키지. 파일명, 빌드와 SHA-256을 기록한다.
- 일반 ADB 권한으로 읽을 수 없는 실제 DT 또는 하드웨어 관측 자료. 전체 userdata, EFS/IMEI/보정 파티션은 요청하지 않는다.
- 호환성이 정해진 후 필요한 Apple 사용자 공간·DeviceTree 파일. 우선 공개 공식 다운로드 가능 여부를 확인하고, 불가능한 항목의 정확한 빌드/파일명을 요청한다.
- 전체 XNU 빌드 재현에 필요한 macOS/Xcode 환경 또는 대응 빌드 산출물과 출처.

Platform-Tools 공식 출처: https://developer.android.com/tools/releases/platform-tools
이 프로젝트의 `host-tools/`에만 설치하며 전역 PATH를 변경하지 않는다.

## 실기기 첫 시험 패키지

TWRP가 정상 부팅한 SM-N976N에서 실행할 [RAM 전용 진단 패키지](device_test/README.ko.md)를 준비했다. 실제 DT·메모리·커널 로그를 PC로 회수하는 단계이며, XNU/iOS 실행이나 파티션 플래시를 수행하지 않는다.
