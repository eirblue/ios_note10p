# iOS 27.0.1 사용자 공간 정적 분석

입력은 프로젝트 루트의 `iPhone19,2_27.0.1_24A446_Restore.ipsw`이다. 전체 파일 SHA-256은 이전 단계에서 배포 인덱스와 대조했다.
OS의 `SystemVersion.plist`에서도 ProductVersion 27.0.1 / ProductBuildVersion 24A446을 확인했다.

## 추출 경로

1. blacktop/ipsw v3.1.739 Windows x86_64 바이너리를 공식 GitHub Release에서 취득하고 릴리스 checksums.txt의 SHA-256과 대조했다.
2. IPSW의 OS 이미지 `043-69473-662.dmg.aea`를 선택적으로 추출했다.
3. AEA 헤더의 공개 FCS 정보로 도구가 키 자료를 취득했다. `ipsw fw aea --pem-db ...`의 pure Go 구현으로 복호화했다.
4. 해제된 파일은 10,548,674,560-byte APFS 이미지다. ipsw의 Windows DMG 마운트 경로는 실패했으나, 공식 7-Zip 26.04의 APFS 리더로 필요한 파일 4개를 직접 추출했다. 시스템에 파일시스템 드라이버를 설치하거나 기기를 변경하지 않았다.
5. 추출 대상: sbin/launchd, usr/lib/dyld, System/Library/CoreServices/SpringBoard.app/SpringBoard, SystemVersion.plist.

파일·해시·의존 라이브러리·명령어 예시는 `research/ios27/userland-report.json`에 기록했다.
재실행 도구 `inspect_macho.py`는 파일을 수정하지 않는다. 현재 Capstone 해석기의 미지원 바이트도 따로 기록한다.

## 확인 결과

세 실행 파일은 thin ARM64 Mach-O이며 CPU subtype은 **0x8000000c**다. ipsw는 이를 **ARM64e_X1 caps: USR00**으로 표시한다.
모두 LC_BUILD_VERSION의 minimum/SDK가 iOS 27.0.0이다. 세 파일 모두 chained fixup pointer format 12가 있다.

| 파일 | BRAA | BLRAA | 그 밖의 인증 분기/반환 |
|---|---:|---:|---|
| launchd | 629 | 61 | BRAAZ 6, BLRAAZ 81 |
| dyld | 75 | 562 | BRAAZ 25, BLRAAZ 82, RETAB 101 |
| SpringBoard | 1 | 0 | 작은 본체로 전체 GUI 코드 분석을 대신하지 않음 |

이는 instruction 표시가 있는 section의 정적 카운트다. 도달 가능성을 증명한 실행 결과는 아니다.
미해석 바이트는 launchd 11,028, dyld 22,732, SpringBoard 0이다. 따라서 이 표는 전체 명령어 요구사항 목록이 아니다.

독립적인 ipsw 디스어셈블러로 다음 원시 바이트를 재확인했다:

- launchd VA 0x100010748: `83 08 1f d7` → `braa x4, x3`
- dyld VA 0x1744: `14 09 3f d7` → `blraa x8, x20`

일부 PAC hint 명령이 구형 CPU에서 NOP처럼 처리될 수 있다는 사실만으로, 이들 인증 분기 및 포인터 fixup ABI가 호환된다고 결론낼 수 없다.

## 실제 기기 조회

사용자가 USB 디버깅을 허용한 SM-N976N에 ADB로 연결해 읽었다. 일반 샌드박스의 ADB 홈 경로 오류는 샌드박스 밖의 읽기 전용 실행으로 해결했다.

- product d2x / board exynos9825 / platform universal9825.
- 설치 버전 Android 12 / PDA와 bootloader **N976NKSU2HWH5** / 보안 패치 2023-08-01.
- 제공된 AP는 **N976NKSU2HXJ2**로 설치 버전과 다르다. 동일 모델의 분석 참조용이며 동일 펌웨어라고 취급하지 않는다.
- flash.locked=1, vbmeta.device_state=locked, verifiedbootstate=green, sys.oem_unlock_allowed=0.
- ro.revision=24. stock DTBO의 custom 범위가 같은 숫자를 사용한다는 부트로더 근거가 없으므로 이것만으로 overlay 선택을 확정하지 않았다.
- /proc/cpuinfo에 Cortex-A55(0xd05), Cortex-A75(0xd0a), Samsung(implementer 0x53, part 0x003) 코어가 보인다. Features에 paca/pacg가 없다.
- 이는 Android 커널이 노출하는 기능이다. 전체 하드웨어 기능 레지스터를 직접 읽은 결과가 아니며, PAC 부재의 단독 증명으로 취급하지 않는다.
- 일반 ADB에서 live DT 경로는 Permission denied. CPU 식별 레지스터 sysfs 경로는 존재하지 않았다. root 전환/부트로더 변경은 수행하지 않았다.

원본 조회 내용은 개인 자료용 `note10/private/device-report.json`에 저장했고 CPU serial 필드는 제외했다.

추가로 사용자 모드 CPU 진단을 직접 구현·빌드하여 기기에서 임시 실행했다. 8개 코어 모두 PACIA/XPACI에서 SIGILL. HWCAP PACA/PACG도 false였다. 자세한 실행 근거와 한계는 [CPU-PROBE.md](CPU-PROBE.md)를 본다.

## 이식 판단

최신 iPhone용 바이너리에는 초기 실행부터 인증 분기와 포인터 ABI 의존성이 있다. 현재 Exynos에서 동일한 기능을 실행할 수 있다는 증거가 없으므로 **원본 iOS 27 사용자 공간이 그대로 동작한다는 경로는 성립하지 않았다**.

다음 문제는 각각 별도 해결이 필요하다:

1. kernel/loader가 ARM64e_X1 바이너리 및 authenticated chained fixup을 처리하는 경로.
2. 대상 CPU에 없는 명령의 처리: 소프트웨어 예외 처리 또는 바이너리 변환을 구현한다면 성능, ABI, 모든 라이브러리의 동작을 검증해야 한다. 이는 아직 설계·구현되지 않았고 정상 구동 가능한 해법으로 확인된 것도 아니다.
3. 최신 dyld shared cache 전체, 추가 ISA 요구 및 서비스 의존성. 현재 세 실행 파일 분석이 이를 대체하지 않는다.
4. XNU 13432.2.10 대응 소스·빌드 경로와 Exynos GICv2/저장장치/화면 등의 네이티브 드라이버.
5. 실제 bootloader 진입 및 메모리 계약. 현재 기기는 locked라 임의 커널 부팅도 검증할 수 없다.

이 결과는 iOS 16으로 목표를 변경한 것이 아니다. 최신 IPSW를 우선 대상으로 유지하면서, 필요한 호환성 작업을 실측 근거에 따라 구분한 것이다.

## 재실행

```powershell
python -m pip install --target host-tools/python-packages capstone
python note10/inspect_macho.py research/ios27/userland/sbin/launchd research/ios27/userland/usr/lib/dyld research/ios27/userland/System/Library/CoreServices/SpringBoard.app/SpringBoard
```

참고: https://blacktop.github.io/ipsw/docs/guides/aea/
및 https://www.7-zip.org/download.html
