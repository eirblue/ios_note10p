# iOS 26.5.2 사용자 공간 분석·부품 검사

활성 대상 iPhone18,1 / 23F84의 로컬 IPSW에서 OS AEA를 추출·복호화했다.
복호화된 APFS 이미지 크기는 9,571,401,728 bytes이며 SHA-384가 BuildManifest OS Digest와 일치한다.
이 OS 항목의 Digest는 AEA 포장본 전체가 아닌 **복호화 이미지**와 비교해야 했다.
AEA의 ZIP CRC는 별도로 검증했다. Apple 서명 인증을 수행했다는 뜻은 아니다.

7-Zip으로 launchd, dyld, SpringBoard 및 SystemVersion.plist를 선택 추출했다.
SystemVersion의 ProductVersion 26.5.2 / ProductBuildVersion 23F84를 확인했다.
Apple 이미지·바이너리·코드에서 생성한 자료는 Git 제외 경로에 보관한다.

## 실제 바이너리

세 바이너리 모두 thin ARM64, subtype **0x80000002 (arm64e)**, 최소 OS/SDK 26.5.0이다.
iOS 27 분석 당시의 ARM64e_X1 subtype과 다르지만 PAC 명령·인증 포인터 의존성은 남아 있다.

| 항목 | launchd | dyld | SpringBoard |
|---|---:|---:|---:|
| 지원된 legacy PAC/AUT/XPAC 명령 | 2,342 | 5,320 | 0 |
| 그중 hint 명령 | 1,785 | 2,372 | 0 |
| USERLAND24 fixup | 2,409 | 1,613 | 1 |
| 정적 decoder 미해석 bytes | 52 | 272 | 0 |

전체 분석 범위: 명령 section 240,338 words, 지원 legacy PAC 명령 7,662개, hint 4,157개.
Fixup format은 세 바이너리 모두 12이며, 9개 페이지에 포인터 4,023개, 그중 authenticated 형식 1,857개다.
실제 import 669개도 새 파일에서 파싱했다. 미해석 코드 및 추출하지 않은 shared cache/의존 라이브러리의
명령을 지원한다고 간주하지 않는다. 정적 결과는 코드 도달 가능성이나 실행 호환성의 증명이 아니다.

## SM-N976N 검사

새 입력으로 corpus를 재생성하고 기존 호환성 부품을 Android executable로 실행했다.

| 검사 | 입력/대상 | 통과 assertion |
|---|---|---:|
| 인증 분기 decoder·전이 | 275,202 oracle records | 859,150 |
| PAC/AUT/XPAC decoder·모델 | 278,959 oracle records | 917,857 |
| format 12 pointer/page | 24,038 records / 실제 fixup 4,023개 | 170,083 |
| loader 값·import 해석 | 실제 import 669개 | 88,326 |
| 등록된 hint 위치·slide·거부 조건 | 실제 위치 4,157개 | 469,955 |
| 합계 | 5종 모두 통과 | **2,505,371** |

기기의 시험 실행 파일과 입력 자료는 모두 삭제했다. 버전별 결과 및 실행 파일/입력 해시는
`note10/private/ios26-results/`에 저장했다. 실제 iOS 바이너리나 변환한 dyld를 기기에서 실행한 결과가 아니다.

등록 위치 manifest와 원본 복원 검증을 포함한 BRK 연구용 복사본도 새 자료로 생성했다.
변경한 launchd/dyld의 원래 코드 서명은 무효다. Apple PAC ABI·키 수명·전체 ISA·dyld cache·XNU 예외
연결·플랫폼 초기화·root 마운트는 미완료이며 부팅 이미지는 아직 없다.

## 재현

```powershell
python note10/extract_active_userland.py
python note10/inspect_macho.py research/ios26/userland/sbin/launchd research/ios26/userland/usr/lib/dyld research/ios26/userland/System/Library/CoreServices/SpringBoard.app/SpringBoard
python note10/compat/generate_oracle.py
python note10/compat/generate_pac_oracle.py
python note10/compat/collect_fixup24.py
python note10/compat/prepare_hint_copies.py
./note10/compat/build.ps1
# 연결·디버깅 허용된 SM-N976N에서 부품 검사만 실행하고 정리:
./note10/compat/run_target_tests.ps1
```

`extract_active_userland.py`는 ZIP CRC 및 복호화 OS hash를 검사한 뒤 필요한 파일만 추출한다.
기존 유효 이미지를 재사용하며 시스템 볼륨을 마운트하지 않는다.
활성 입력 helper는 SystemVersion·보고서 경로·파일 SHA-256을 검사해 다른 버전이나 변경된 자료를 거부한다.
