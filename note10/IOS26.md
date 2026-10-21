# Active target: iOS 26.5.2 / iPhone18,1

사용자 요청에 따라 현재 대상을 `iPhone18,1_26.5.2_23F84_Restore.ipsw`로 변경했다.
`iPhone18,1`은 iPhone 17 Pro이며, 실제 모델 식별은 로컬 BuildManifest를 기준으로 한다.
활성 설정은 [target.json](target.json), 이전 iOS 27 기록은 [IOS27.md](IOS27.md)에 보존한다.

## 로컬 파일 검증

- ProductVersion 26.5.2, ProductBuildVersion 23F84, SupportedProductTypes iPhone18,1.
- 크기 11,321,477,590 bytes.
- SHA-256 `ac3b4e215772eb3e646a95427af6c99643fb01091f70162eb6dd4cf4f60a2cfb`.
- Customer Erase Install identity: v53ap, ApChipID 0x8150, ApBoardID 0x0C.
- `kernelcache.release.v53`와 `DeviceTree.v53ap.im4p` 추출. ZIP CRC 및 manifest SHA-384 digest 일치.
- 압축 해제한 커널의 버전 문자열:

```text
Darwin Kernel Version 25.5.0: Tue Jun  9 22:22:07 PDT 2026; root:xnu-12377.122.8~1/RELEASE_ARM64_T8150
```

커널 outer Mach-O subtype은 0xc0000002다. 새 사용자 공간 추출·명령 분석·부품 검사 결과는 [USERLAND26.md](USERLAND26.md)를 본다.
검증 기록은 `research/ios26/local-ipsw-verification.json`에 있다.
이 검사는 로컬 해시·manifest 일치 검사이며 Apple 서명 인증이나 부팅 검증이 아니다.

재현: `python note10/verify_target_ipsw.py`.

## 공개 XNU 확보

2026-10-21 Apple 공식 GitHub API 기준:

- 실제 커널의 `xnu-12377.122.8` 태그: 404.
- 근접 공개 태그 `xnu-12377.121.6`: 존재. 소스 archive 다운로드 및 압축 해제 완료.
- 고정 소스 커밋 `ac9718fb1af618d5ce8678d0dc6e8a58f252216f`.
- archive SHA-256 `577f4a220304296332e28c802779e7b5e6a27a46812315aacf61c0269a03e12a`.
- 소스 위치 `research/ios26/xnu-reference/xnu-ac9718fb1af618d5ce8678d0dc6e8a58f252216f`.
- 취득 URL·commit·hash·비일치 상태: `research/ios26/xnu-reference.json`.

[Apple 공개 태그](https://github.com/apple-oss-distributions/xnu/tree/xnu-12377.121.6),
[고정 소스](https://github.com/apple-oss-distributions/xnu/tree/ac9718fb1af618d5ce8678d0dc6e8a58f252216f).

같은 12377 계열 소스를 확보한 것은 진행점이다. 다만 `.121.6`을 IPSW의 `.122.8`과 동일한 소스로
취급하지 않는다. 근접 버전으로 빌드할 경우 사용자 공간 ABI 및 비공개 구성요소 차이를 별도 검증해야 한다.
기존 V60의 xnu-8796 패치를 새 소스에 적용하거나 빌드한 결과는 아직 없다.

## 이어서 필요한 작업

1. 새 IPSW의 OS 이미지 복호화와 launchd/dyld/SpringBoard 추출 및 의존성 분석.
2. 새 커널 소스의 빌드 의존성·도구 체인 및 Exynos 플랫폼 연결 지점 조사.
3. 새 바이너리로 명령·fixup corpus를 재생성하고 기존 부품의 실제 적용 범위를 재검증.

호환성 corpus 생성기와 Mach-O 보고서 기본 경로는 활성 target.json을 따른다.
26.5.2 사용자 공간 추출·새 corpus 생성 및 Android 부품 검사 5종을 완료했다.
세부 빌드 조사: [XNU26-BUILD.md](XNU26-BUILD.md). 이전 iOS 27 검사와 버전별 결과를 구분한다.
Apple 테스트용 fixup header의 고정 참조 위치는 별도이며 커널 버전 일치의 근거로 사용하지 않는다.

현재 Note10+용 XNU 전체 빌드·부팅 이미지·iOS 실행 결과는 없다.
