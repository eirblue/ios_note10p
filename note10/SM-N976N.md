# SM-N976N 대상 기록

연결된 Galaxy Note10+ 5G SM-N976N, Android 12, Exynos 9825를 ADB 및 실행 진단으로 확인했다.
조회 당시 설치 빌드/부트로더 N976NKSU2HWH5, flash locked=1, OEM unlock allowed=0이다.
제공 AP N976NKSU2HXJ2는 설치 빌드와 다르다. 기기 reg revision은 24이나 DTBO 선택에 바로 대응시키지 않았다.
커널 기기 구분은 d2x/d2xks 계열이며 live DT는 일반 ADB 권한으로 읽지 못했다. 실제 overlay 선택은 미확정이다.

## origin_firmware 분석

`origin_firmware/`에 있는 파일을 직접 확인했다. 제공된 펌웨어는 N976N 계열과 맞고, AP 아카이브에도 필요한 부팅 자료가 있다.

- AP: `N976NKSU2HXJ2`, 사용자 폴더명상 Android 12 패키지. `boot.img.lz4`, `recovery.img.lz4`, `dt.img.lz4`, `dtbo.img.lz4`, `vbmeta.img.lz4` 포함.
- 압축 해제된 `dt.img`: Android DT table, 8 MiB 패딩. 실제 단일 DTB entry 239,680 bytes. 문자열에서 `samsung,exynos9825` 확인.
- 압축 해제된 `dtbo.img`: Android DT table, 8 MiB 패딩. overlay 9개. `D2X`, `EXYNOS9825`, `KOR` 문자열 확인. 모델/지역 일치 근거다.
- boot 및 recovery 모두 `ANDROID!` 헤더로 시작한다. 헤더 시작 부분은 읽었지만 실제 로드 주소·Samsung 부팅 계약은 아직 완전히 판독하지 않았다.
- vbmeta의 AVB 매직 `AVB0` 확인.
- 현재 폴더 안에는 전체 5.45 GB AP tar 외에도 AP의 압축 해제 파일, BL, CP, CSC, HOME_CSC, USERDATA가 있다. 원본 아카이브는 보존한다.
- AP tar와 이미지별 SHA-256 기록은 대화 도구 출력에 있으나, 별도의 체크섬 매니페스트는 아직 저장하지 않았다.

다음 단계는 공통 Exynos 9825 DTB 및 한국형 DTBO overlay를 구조적으로 판독해 메모리, GIC, timer, framebuffer, UFS 정보를 정리하고, boot/recovery header와 비교하는 것이다. 이 분석만으로 XNU 부팅 성공이나 안전한 flash 경로가 확인되는 것은 아니다.

## 소스 조사

Android 12 계열의 공개 참조를 취득했다. 사용자 순정 펌웨어와 정확히 일치하는 소스라는 뜻은 아니다.

| 저장소 | 참조 커밋 | 용도 |
|---|---|---|
| LineageOS/android_device_samsung_d2x | c8cae97f0bbaa3a3eb6cb8a7f8f2f17418ce627f | d2x defconfig, 화면 구성 참조 |
| LineageOS/android_device_samsung_exynos9820-common | 0917d5a3da9d03eabbf3e5dc8d864b969a445ba1 | 공통 boot 이미지 및 DTB/DTBO 구성 |
| LineageOS/android_kernel_samsung_exynos9820 | 85599d66377445117cbfccad7151ddec7112b263 | DTS/드라이버 조사용, Windows 전체 checkout 실패 |

모두 lineage-19.1이다. 공통 BoardConfig에서는 boot header v1, 2048-byte pagesize, base 0x10000000, 별도 dtb.img 및 DTBO 구성을 사용한다.
이는 공개 Android 빌드의 설정으로, 순정 boot header나 네이티브 shim의 안전한 로드 주소가 입증된 것은 아니다.
V60 shim/build.sh의 boot header v2 / 4096-byte 설정을 그대로 사용할 근거가 없다.

## 원본 펌웨어

먼저 사용자 기기의 빌드번호 및 서비스 제공자 소프트웨어 버전을 확인한다. 같은 모델의 다른 빌드를 현재 기기와 동일하다고 취급하지 않는다.
현재 빌드의 AP_*.tar.md5 또는 그 안에 있는 다음 파일을 분석한다. 패키지에 따라 압축 확장자와 구성이 다를 수 있다.

- boot.img.lz4
- recovery.img.lz4
- dtb.img.lz4 (별도 포함 여부 확인)
- dtbo.img.lz4
- vbmeta.img.lz4

DTB가 다른 형태로 포함되어 있으면 실제 패키지 구성부터 조사한다. AP 전체에 사용자 데이터나 EFS 덤프를 추가할 필요는 없다.
원상복구에는 같은 빌드의 BL/AP/CP/CSC 패키지를 별도로 보관한다. 이 기록은 플래시 명령이 아니다.

## 언락과 현재 단계

OEM 잠금 해제 허용과 실제 부트로더 언락은 별도이다. 실제 언락에는 사용자 데이터 초기화가 수반된다.
현재 소스/펌웨어 분석에 언락은 필요하지 않으며, 아직 실행할 Note10+용 이미지도 없다.

근거:

- https://lineageos.github.io/lineage_wiki/devices/d2x/install/ — SM-N976N 지원 모델 구분 및 언락 절차
- https://twrp.me/samsung/samsunggalaxynote10plus5G.html — d2x, A-only/system-as-root 및 recovery/AVB 주의 사항
- https://github.com/LineageOS/android_device_samsung_d2x/tree/c8cae97f0bbaa3a3eb6cb8a7f8f2f17418ce627f
- https://github.com/LineageOS/android_device_samsung_exynos9820-common/blob/0917d5a3da9d03eabbf3e5dc8d864b969a445ba1/BoardConfigCommon.mk
