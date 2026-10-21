# SM-N976N 원본 펌웨어의 하드웨어 관측

입력: origin_firmware/AP_N976NKSU2HXJ2_CL27170661_QB92100536_REV01_user_low_ship_meta_OS12

`inspect_firmware.py`로 boot/recovery와 dt/dtbo/vbmeta의 LZ4 압축을 풀고 헤더 및 FDT 구조를 판독했다.
각 입력의 SHA-256, 해제된 이미지 SHA-256, 전체 속성 및 DT blob은 `note10/private/firmware/`에 저장했다.
현재 값은 **원본 펌웨어의 선언값**이며 live DT나 실제 레지스터를 읽은 결과가 아니다. DTBO overlay는 아직 base에 병합하지 않았다.

## 부팅 이미지

- boot: 57,671,680 bytes, Android header v1, page 2048, header size 1648.
- recovery: 67,633,152 bytes, 동일한 v1/page 2048.
- boot/recovery의 kernel payload SHA-256 동일: `5116059c2818bfae33edf5d397d88668e0649c084d0fb6b8135d8b8c569f0b92`.
- kernel_size 46,366,732 bytes; 선언 주소 0x10008000, tags 주소 0x10000100. 이 주소가 실제 실행 위치라는 의미는 아니다.
- ARM64 Image의 text_offset 0x80000, image_size 55,345,152. Samsung 부트로더의 실제 배치·압축 해제 동작 확인 필요.
- boot ramdisk_size 0. recovery ramdisk_size 15,311,675, 선언 주소 0x11000000.
- recovery 내 DTBO 크기 1,864,368, 파일 offset 61,683,712. 별도 dtbo 이미지와 동일 여부는 아직 확인하지 않았다.
- 헤더의 OS 12.0.0 / security patch month 2023-08. 이는 헤더 필드이며 전체 시스템 보안 패치 날짜를 대신하지 않는다.

## base DT 관측

| 장치 | 관측 |
|---|---|
| 인터럽트 | arm,cortex-a15-gic / arm,cortex-a9-gic; GICv2 계열 MMIO 인터페이스 |
| GIC distributor / CPU interface | 0x10101000 / 0x10102000, 각 0x1000 |
| GIC virtual control / virtual CPU | 0x10104000 / 0x10106000, 각 0x2000 |
| 타이머 | arm,armv8-timer, clock-frequency 26,000,000; 물리 타이머 사용 속성 |
| 타이머 인터럽트 | PPI 13/14/11/10 → INTID 29/30/27/26. 실제 사용 가능 여부 미검증 |
| PSCI | smc, CPU_ON 0xc4000003 |
| CPU reg | 0,1,2,3,4,5,0x100,0x101 |
| UFS | samsung,exynos-ufs, 첫 reg 0x13d60000 / size 0x200 |
| UFS 추가 reg | 0x13d61100/0x200, 0x13d50000/0x8000, 0x13d70000/0x100 |
| UFS PHY | 0x13d64000 / size 0x800 |
| watchdog | 0x10050000, 0x10060000; Samsung 드라이버 확인 필요 |
| DECON | 0x19030000, 0x19050000 |
| DSIM | 0x19080000 |

base DT의 정적 memory 노드는 0x80000000, 0x880000000, 0x900000000에 각 2 GiB를 선언한다. 이는 기기의 실제 RAM 용량·안전한 XNU 메모리 범위로 확정할 수 없다. 고정/동적 reserved-memory와 live DT를 대조해야 한다.
base DT에 바로 재사용 가능한 simple-framebuffer를 확인하지 못했다. DECON reg는 픽셀 버퍼 주소가 아니다.

## DTBO

한국형 D2X overlay 9개. hw_rev 범위는 0x02–0x0f, 0x10, 0x11, 0x12, 0x13–0x14, 0x15, 0x16, 0x17, 0x18–0xff.
실기기의 hw_rev를 모르므로 어느 하나를 선택하지 않았다.
마지막 overlay에는 sec,sec_ts touchscreen@48, D2용 tsp_sec/y771_d2.bin 및 s6e3ha9 계열 panel-lookup이 있다. fragment target와 fixup을 해석하기 전에는 실제 버스/핀 배치로 확정하지 않는다.

## V60에서 교체할 부분

V60의 shim/shim.c는 GICR와 ICC_* 시스템 레지스터 인터페이스를 사용한다. Note10+는 GICv2 MMIO CPU interface 경로가 필요하다. Qualcomm MMIO 주소나 타이머 주파수를 단순 치환하는 작업이 아니다.
UFS host/PHY, watchdog, 디스플레이 유지, 터치 및 PMIC 경로도 기기별 구현 대상이다.

분석 재실행:

```powershell
python -m pip install --target host-tools/python-packages lz4
python note10/inspect_firmware.py origin_firmware/AP_N976NKSU2HXJ2_CL27170661_QB92100536_REV01_user_low_ship_meta_OS12
```

형식 정의: https://android.googlesource.com/platform/system/tools/mkbootimg/+/refs/heads/main/include/bootimg/bootimg.h
및 https://android.googlesource.com/platform/system/libufdt/+/refs/heads/main/utils/src/dt_table.h
