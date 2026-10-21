# SM-N976N 실기기 시험 1단계

**TWRP의 Linux 커널에서 실제 기기 정보를 수집하는 진단 패키지다. XNU/iOS를 실행하는 이미지가 아니다.**
이 결과로 실제 선택된 DT와 RAM/예약 영역을 확인한 뒤 XNU 진입용 로더를 구체화한다.
초기 EL/MMU/cache 레지스터와 전체 CPU의 16K 지원은 이 시험만으로 확정하지 않는다.

## 사용자 준비

1. 개인 데이터를 PC 등에 백업한다. 부트로더 언락은 데이터 초기화를 수반한다.
2. SM-N976N/d2x 및 설치 펌웨어에 맞는 절차로 언락하고, 호환 TWRP가 정상 부팅하는 상태를 만든다.
3. TWRP **홈 화면**에서 USB로 PC에 연결한다. ADB Sideload 화면이 아닌 일반 ADB 셸이 필요하다.
4. 진단을 위해 /data 복호화·포맷이나 시스템 파티션 수정을 할 필요는 없다.

TWRP 설치는 이 도구가 자동 수행하지 않는다. d2x의 A-only/recovery·AVB 제약은
[공식 기기 안내](https://twrp.me/samsung/samsunggalaxynote10plus5G.html)를 따른다.
다른 모델 d2s/d1x의 이미지를 대신 쓰지 않는다. [공식 d2x 다운로드](https://dl.twrp.me/d2x/).
PC에서 확인한 공식 참조 파일은 `twrp-3.7.0_9-1-d2x.img`이며 공식 SHA256과 일치했다.
이 확인은 사용자의 현재 펌웨어에서 해당 이미지가 실제 부팅한다는 검증은 아니다.

## 권장: PC에서 한 번에 실행·회수

압축을 풀고 PowerShell에서 실행한다. Python 3과 포함된 Windows ADB를 사용하며 관리자 권한은 필요하지 않다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\note10\device_test\run-probe.ps1
```

검사만 하려면 끝에 `-Check`를 추가한다. 프로젝트 원본에서도 같은 명령을 쓸 수 있다.
직접 Python으로 실행하는 경우:

```powershell
C:\Python314\python.exe -X utf8 note10/device_test/run_probe.py --run
```

도구는 TWRP/root/aarch64/SM-N976N 또는 d2x를 검사한 뒤 수집 스크립트를 `/tmp`에 전송한다.
새 세션의 결과를 PC `note10/private/device-observations/session-*/`로 내려받아 `analysis.json`을 만든다.
기기가 여러 대면 `--serial`로 하나를 지정한다. 잘못된 기기·일반 Android·순정 리커버리·sideload 상태에서는 거부한다.
`capture_downloaded=true`와 분석 파일을 확인하기 전에는 재부팅하지 않는다.

## 선택: TWRP에서 ZIP 실행

PC에서 RAM으로 전송한다. 기기 내부 저장소를 마운트할 필요가 없다.

```powershell
.\host-tools\platform-tools\adb.exe push .\note10-phase1-probe.zip /tmp/note10-phase1-probe.zip
```

TWRP Install에서 `/tmp/note10-phase1-probe.zip`을 선택한다. 이 ZIP은 서명되지 않은 자체 진단 패키지다.
부트로더 서명 검증/AVB와 별개인 TWRP의 ZIP 서명 검증이 켜져 있으면 이 ZIP은 거부된다.
출력은 `/tmp/note10-probe/session-*`에 남는다. TWRP 터미널이나 ADB로 세션 이름을 확인한다.

```powershell
.\host-tools\platform-tools\adb.exe shell ls /tmp/note10-probe
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\note10\device_test\run-probe.ps1 -Session session-실제번호
```

재부팅하면 RAM 결과가 사라진다. 이 ZIP을 설치한 것만으로 PC 회수가 끝난 것은 아니다.

## 관측 범위

- live FDT 또는 실제 devicetree 파일, 메모리·예약 영역, GIC/timer/PSCI/ramoops 선언.
- recovery Linux의 iomem/meminfo/config, 커널 로그, CPU cache sysfs 값.
- 관측 실패와 주소 가림을 그대로 기록한다. 동적 예약 영역을 추측하여 채우지 않는다.
- KEXEC 설정이 보여도 XNU로 넘어가는 로더가 구현·검증됐다는 의미는 아니다.
- 스크립트는 새 `/tmp` 세션에만 쓴다. 파티션 접근/마운트/플래시/재부팅/모듈 적재/kexec는 실행하지 않는다.

raw DT와 커널 로그에는 기기 식별 정보가 포함될 수 있다. 원본은 PC private 경로에 보관하며 자동 업로드하지 않는다.
PC 시험은 합성 DT·수집 파일시스템·ADB 응답으로 검증한 것이며, 실기기 실행 성공을 대신하지 않는다.

## 빌드·검증

```powershell
C:\Python314\python.exe -X utf8 note10/device_test/build_package.py
C:\Python314\python.exe -X utf8 note10/device_test/test_probe.py
C:\Python314\python.exe -X utf8 note10/device_test/build_bundle.py
```

생성 경로: `note10/private/device-test/`. ZIP은 재현 가능한 고정 타임스탬프로 만들며, 포함 파일 해시와 실행 범위를 기록한다.
TWRP ZIP 실행 인터페이스 참고: [TWRP Commandline Guide](https://twrp.me/faq/openrecoveryscript.html).
