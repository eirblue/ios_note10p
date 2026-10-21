# SM-N976N 사용자 모드 CPU 명령 실행 진단

## 구현 및 실행

`cpu_probe.c`를 구현하고, 기존 설치된 Unity Android NDK의 Clang 9.0.8로 Android API 24 대상 AArch64 PIE 실행 파일을 빌드했다.
`-Wall -Wextra -Werror` 빌드 통과. 진단 ELF의 SHA-256:

`60145434d2a50e8df26fc6ae2622851b9cb044f49beff61e51346f3a844df5a3`

연결된 기기 모델이 SM-N976N임을 재확인한 뒤, 충돌하지 않는 새 경로 `/data/local/tmp/codex-note10-cpu-probe-60145434d2a5`에 임시 전송했다.
사용자 모드에서 scratch 레지스터에만 PACIA/XPACI 명령을 실행하고 SIGILL을 포착했다. 서명 결과를 메모리 주소나 분기 대상으로 사용하지 않는다.
각 코어로 프로세스 affinity를 설정하고 실행 코어를 확인했다. 종료 시 affinity 복구 성공. 출력 회수 후 기기의 임시 실행 파일을 삭제했다.
기기 reboot, root, unlock, flash는 수행하지 않았다.

## 관측

기기: SM-N976N / Exynos 9825 / Android 12 / N976NKSU2HWH5.

| 코어 | 요청/실행 affinity | PACIA x0,x1 | XPACI x0 |
|---|---|---|---|
| 0–3 | 각각 일치 | 모두 SIGILL | 모두 SIGILL |
| 4–5 | 각각 일치 | 모두 SIGILL | 모두 SIGILL |
| 6–7 | 각각 일치 | 모두 SIGILL | 모두 SIGILL |

- HWCAP: 0x111fff, PACA/PACG 모두 false.
- MRS ID_AA64ISAR1_EL1 커널 노출값: 모든 코어에서 0x1.
- MRS ID_AA64MMFR0_EL1 커널 노출값: 모든 코어에서 0xff000000.
- MRS는 Android 커널이 에뮬레이션·보정하는 값일 수 있다. 이 MMFR0 값으로 실제 16 KiB granule 지원 여부를 판정하지 않는다.
- 이것은 현재 Android 사용자 모드에서의 실행 결과다. EL1에서 직접 읽은 물리 CPU 레지스터나 임의 XNU 부팅 결과를 대신하지 않는다.

두 명령의 원시 opcode는 실행 전에 Capstone으로 교차 확인했다:

- 0xdac10020 → pacia x0, x1
- 0xdac143e0 → xpaci x0

원본 JSON: `note10/private/cpu-probe-result.json`.

## 포팅에 미치는 영향

iOS 27 launchd/dyld에는 이미 이 계열의 PAC 명령과 BRAA/BLRAA 등이 존재한다. 현재 환경에서 원본 바이너리를 수정 없이 실행하는 경로는 막힌다.
정상 구동을 위해서는 인증 포인터 fixup/loader ABI와 함께 명령어 호환성을 해결해야 한다. SIGILL을 무조건 건너뛰거나 opcode만 NOP으로 치환하는 처리는 구현하지 않았다.
향후 호환 계층이 생겨도 ARM64e_X1의 추가 명령어, shared cache, Mach 호출, 서비스 및 그래픽 드라이버 문제는 별도로 남는다.

## 재빌드

```powershell
./note10/build_cpu_probe.ps1
# 다른 Android NDK가 있을 경우:
./note10/build_cpu_probe.ps1 -NdkRoot C:/path/to/android-ndk
```

빌드 스크립트는 PC에서 ELF만 생성한다. 기기 전송·실행은 자동 수행하지 않는다.
