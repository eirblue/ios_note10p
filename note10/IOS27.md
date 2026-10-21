# 이전 대상 기록: iPhone 18 Pro / iOS 27.0.1

현재 활성 대상은 사용자 요청으로 [iOS 26.5.2 / iPhone18,1](IOS26.md)로 변경했다.
아래 내용과 이에 기반한 검사 결과는 이전 대상의 기록이다.

사용자 요청에 따라 네이티브 이식의 우선 분석 대상을 iPhone 18 Pro의 iOS 27.0.1로 지정했다. V60/iOS 16 코드는 하드웨어 이식 방식의 참고 자료다.
현재는 실행 가능성을 조사하는 단계이며, 이 IPSW를 Note10+에 그대로 설치할 수 있다는 뜻은 아니다.
사용자 공간 추출과 실제 기기 조회 결과는 [USERLAND27.md](USERLAND27.md)를 본다. OS AEA 복호화와 launchd/dyld/SpringBoard 추출은 완료되었고, ARM64e_X1 인증 분기 의존성을 확인했다.

## 실제 취득 및 확인

Apple CDN의 IPSW에서 HTTP Range로 ZIP 목록, BuildManifest.plist, Restore.plist, 커널 및 DeviceTree를 취득했다.
사용자가 프로젝트 루트에 넣은 전체 IPSW에서도 네 항목을 읽었고 다운로드한 항목과 바이트 단위로 동일함을 확인했다.

| 항목 | 실제 파일에서 읽은 값 |
|---|---|
| ProductType | iPhone19,2 |
| ProductVersion / Build | 27.0.1 / 24A446 |
| DeviceClass / ApChipID | v63ap / 0x8160 |
| KernelCache | kernelcache.release.v6x-pandia |
| 커널 버전 문자열 | Darwin 27.0.0 / xnu-13432.2.10~2 / RELEASE_ARM64_T8160 |
| 바깥 Mach-O fileset CPU subtype | 0xc000000c (정확한 의미는 대응 ABI 정의로 추가 확인 필요) |
| 내부 com.apple.kernel CPU subtype | 0xc0000002 (arm64e, 버전 포함 PAC ABI 비트 설정) |
| DeviceTree | Firmware/all_flash/DeviceTree.v63ap.im4p |
| OS 이미지 | 043-69473-662.dmg.aea (APFS, Restore.plist 기준) |
| Cryptex SystemOS | 043-70107-711.dmg.aea |

커널/DeviceTree는 IM4P의 OCTET STRING payload를 꺼내 LZFSE로 해제했다. 두 원본 IM4P의 SHA-384가 BuildManifest의 Digest와 일치했다.
전체 IPSW 해시 검증 결과는 `research/ios27/local-ipsw-verification.json`에 보관한다. 분석용 Apple 파일과 전체 IPSW는 Git에서 제외한다.

## 해결해야 하는 차이

1. **CPU/ABI**: 실제 커널은 arm64e이다. PAC를 사용하는 바이너리가 Exynos 9825에서 실행 가능한지는 별도 검증이 필요하다. CPU subtype 숫자를 바꾸거나 커널 설정에서 PAC를 끄는 것만으로 기존 바이너리의 명령어·포인터·dyld ABI가 호환되는 것은 아니다. 사용자 공간의 요구 명령어/ABI는 아직 조사하지 않았다.
2. **전체 커널 재빌드**: Apple 공식 XNU 저장소에서 `xnu-13432.2.10` 태그를 직접 조회했지만 404였다. 조회된 최신 태그는 `xnu-12377.121.6`이다. 정확히 대응하는 공개 소스·SDK·빌드 환경은 아직 확보되지 않았고, 버전이 다른 소스를 대응 소스라고 간주하지 않는다.
3. **기기 지원**: 원본 커널은 T8160용이다. Exynos GICv2, 메모리, 전원, UFS, 화면, 입력 지원을 별도로 구현해야 한다. Apple GPU/SEP 등 펌웨어를 Samsung 하드웨어용 드라이버로 사용할 수 없다.
4. **사용자 공간**: OS 및 SystemOS가 AEA 포장 이미지다. OS/APFS와 cryptex를 분석해 dyld/launchd/SpringBoard의 ABI 및 서비스를 확인해야 한다. 아직 복호화·마운트·실행하지 않았다.
5. **실기기 관측**: stock DT는 부팅 중 수정되기 전 자료다. 실제 CPU feature register, 선택된 overlay, RAM/예약 영역, framebuffer 및 부팅 진입 상태를 확인해야 한다.

동일 버전의 다른 iPhone IPSW가 위 문제를 줄이는지는 별도의 비교 대상이며, 사용자가 지정한 iPhone 18 Pro 대상을 임의로 교체하지 않는다. 최신 IPSW를 기준으로 조사하는 것과 정상 구동을 보장하는 것은 구분한다.

## 공개 근거

- Apple 배포 버전: https://support.apple.com/en-gb/149076
- Apple CDN (실제 취득 원본): https://updates.cdn-apple.com/2026FallFCS/8cd333d4-1025-4e89-99a2-1373d2b5bfcb/iPhone19,2_27.0.1_24A446_Restore.ipsw
- Apple PAC 설명: https://developer.apple.com/documentation/security/preparing-your-app-to-work-with-pointer-authentication
- CPU subtype 정의: https://github.com/apple-oss-distributions/xnu/blob/main/osfmk/mach/machine.h
- XNU 태그 조회: https://api.github.com/repos/apple-oss-distributions/xnu/git/ref/tags/xnu-13432.2.10

IPSW 인덱스는 다운로드 URL 발견과 전체 파일 SHA-256 대조에 사용했다: https://ipsw.me/download/iPhone19,2/24A446/
제품·버전·빌드·칩·커널 정보는 인덱스 설명 대신 실제 Apple 파일에서 읽었다.
