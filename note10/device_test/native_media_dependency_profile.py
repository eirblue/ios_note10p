"""Fixed camera/codec removal closure with real shared media providers preserved."""
import hashlib
SLOT_BYTES=6291456
METADATA_BYTES=4096
SETTINGS={'LEDS_S2MPB02': 'n', 'MEDIA_CAMERA_SUPPORT': 'y', 'MEDIA_SUPPORT': 'y', 'VIDEO_EXYNOS_FIMC_IS2': 'n', 'VIDEO_EXYNOS_MFC': 'n'}
REMOVED={'LEDS_S2MPB02': 'n', 'VIDEO_EXYNOS_FIMC_IS2': 'n', 'VIDEO_EXYNOS_MFC': 'n'}
COMMON={'EXYNOS_NPU': 'y', 'MEDIA_CAMERA_SUPPORT': 'y', 'MEDIA_CONTROLLER': 'n', 'MEDIA_SUPPORT': 'y', 'VIDEOBUF2_CORE': 'y', 'VIDEOBUF2_DMA_SG': 'y', 'VIDEOBUF2_MEMOPS': 'y', 'VIDEO_DEV': 'y', 'VIDEO_EXYNOS': 'y', 'VIDEO_EXYNOS_SCALER': 'y', 'VIDEO_EXYNOS_SMFC': 'y', 'VIDEO_V4L2': 'y', 'VIDEO_V4L2_SUBDEV_API': 'n'}
MANDATORY={'NOTE10_V210_NATIVE_PREPARE': 'y', 'NOTE10_V154_LINUX_DIAGNOSTIC': 'y', 'NOTE10_BUILTIN_INIT_ROUTE': 'y', 'EXYNOS_REBOOT': 'y', 'SEC_REBOOT': 'y', 'EXYNOS_IVA': 'y', 'EXYNOS_IOMMU': 'y', 'EXYNOS_IOVMM': 'y', 'ION_EXYNOS': 'y', 'BCM_DHD_WLAN': 'y', 'BCMDHD_PCIE': 'y', 'EXYNOS_PCIE_IOMMU': 'y', 'BLK_DEV_INITRD': 'y', 'INITRAMFS_FORCE': 'y', 'RD_GZIP': 'y', 'SYSFS': 'y', 'PROC_FS': 'y', 'DEVTMPFS': 'y', 'CRYPTO_SHA256': 'y', 'CRYPTO_USER_API_HASH': 'y', 'KEXEC': 'n', 'KEXEC_FILE': 'n'}
DISPLAY={'LED_TRIGGER_PHY': 'n', 'DRM': 'n', 'DRM_LIB_RANDOM': 'n', 'FB': 'y', 'FB_CMDLINE': 'y', 'FB_NOTIFY': 'y', 'FB_DDC': 'n', 'FB_BOOT_VESA_SUPPORT': 'n', 'FB_CFB_FILLRECT': 'y', 'FB_CFB_COPYAREA': 'y', 'FB_CFB_IMAGEBLIT': 'y', 'FB_CFB_REV_PIXELS_IN_BYTE': 'n', 'FB_SYS_FILLRECT': 'n', 'FB_SYS_COPYAREA': 'n', 'FB_SYS_IMAGEBLIT': 'n', 'FB_PROVIDE_GET_FB_UNMAPPED_AREA': 'n', 'FB_FOREIGN_ENDIAN': 'n', 'FB_SYS_FOPS': 'n', 'FB_SVGALIB': 'n', 'FB_MACMODES': 'n', 'FB_BACKLIGHT': 'n', 'FB_MODE_HELPERS': 'y', 'FB_TILEBLITTING': 'n', 'FB_CIRRUS': 'n', 'FB_PM2': 'n', 'FB_ARMCLCD': 'n', 'FB_CYBER2000': 'n', 'FB_ASILIANT': 'n', 'FB_IMSTT': 'n', 'FB_OPENCORES': 'n', 'FB_S1D13XXX': 'n', 'FB_NVIDIA': 'n', 'FB_RIVA': 'n', 'FB_I740': 'n', 'FB_MATROX': 'n', 'FB_RADEON': 'n', 'FB_ATY128': 'n', 'FB_ATY': 'n', 'FB_S3': 'n', 'FB_SAVAGE': 'n', 'FB_SIS': 'n', 'FB_NEOMAGIC': 'n', 'FB_KYRO': 'n', 'FB_3DFX': 'n', 'FB_VOODOO1': 'n', 'FB_VT8623': 'n', 'FB_TRIDENT': 'n', 'FB_ARK': 'n', 'FB_PM3': 'n', 'FB_CARMINE': 'n', 'FB_S3C': 'n', 'FB_SMSCUFX': 'n', 'FB_UDL': 'n', 'FB_IBM_GXT4500': 'n', 'FB_VIRTUAL': 'n', 'FB_METRONOME': 'n', 'FB_MB862XX': 'n', 'FB_BROADSHEET': 'n', 'FB_AUO_K190X': 'n', 'FB_SIMPLE': 'y', 'EXYNOS_MIPI_DSIM': 'y', 'EXYNOS_DISPLAYPORT': 'y', 'EXYNOS_DSIM_DITHER': 'n', 'DECON_BTS_LEGACY': 'y', 'FB_TEST': 'n', 'DSIM_CMD_TEST': 'n', 'EXYNOS_DECON_LCD': 'y', 'EXYNOS_DECON_LCD_S6E3HA2K': 'n', 'EXYNOS_DECON_LCD_S6E3HF4': 'n', 'EXYNOS_DECON_LCD_S6E3HA6': 'n', 'EXYNOS_DECON_LCD_S6E3HA8': 'n', 'EXYNOS_DECON_LCD_S6E3HA9': 'y', 'EXYNOS_DECON_LCD_S6E3AA2': 'n', 'EXYNOS_DECON_LCD_EMUL_DISP': 'n', 'SEC_DISPLAYPORT_LOGGER': 'y', 'SEC_DISPLAYPORT_BIGDATA': 'y', 'EXYNOS_DECON_MDNIE_LITE': 'y', 'EXYNOS_DECON_LCD_SYSFS': 'y', 'EXYNOS_DECON_LCD_SPI': 'n', 'EXYNOS_DECON_LCD_COPR': 'y', 'EXYNOS_DECON_LCD_TUNING': 'n', 'PANEL_AID_DIMMING': 'y', 'SUPPORT_DISPLAY_PROFILER': 'n', 'EXYNOS_DECON_LCD_S6E3HF3': 'n', 'EXYNOS_DECON_LCD_S6E3FA7': 'n', 'PANEL_BACKLIGHT_PAC_3_0': 'y', 'DISPLAY_USE_INFO': 'y', 'PANEL_NOTIFY': 'y', 'FB_SSD1307': 'n', 'FB_SM712': 'n', 'BACKLIGHT_LCD_SUPPORT': 'y', 'LCD_CLASS_DEVICE': 'y', 'LCD_L4F00242T03': 'n', 'LCD_LMS283GF05': 'n', 'LCD_LTV350QV': 'n', 'LCD_ILI922X': 'n', 'LCD_ILI9320': 'n', 'LCD_TDO24M': 'n', 'LCD_VGG2432A4': 'n', 'LCD_PLATFORM': 'n', 'LCD_S6E63M0': 'n', 'LCD_LD9040': 'n', 'LCD_AMS369FG06': 'n', 'LCD_LMS501KF03': 'n', 'LCD_HX8357': 'n', 'BACKLIGHT_CLASS_DEVICE': 'y', 'BACKLIGHT_GENERIC': 'n', 'BACKLIGHT_PWM': 'n', 'BACKLIGHT_PM8941_WLED': 'n', 'BACKLIGHT_ADP8860': 'n', 'BACKLIGHT_ADP8870': 'n', 'BACKLIGHT_LM3630A': 'n', 'BACKLIGHT_LM3639': 'n', 'BACKLIGHT_LP855X': 'n', 'BACKLIGHT_GPIO': 'n', 'BACKLIGHT_LV5207LP': 'n', 'BACKLIGHT_BD6107': 'n', 'BACKLIGHT_ARCXCNN': 'n', 'SND_SOC_SAMSUNG_DISPLAYPORT': 'y', 'LEDS_CLASS': 'y', 'LEDS_CLASS_FLASH': 'n', 'LEDS_BRIGHTNESS_HW_CHANGED': 'n', 'LEDS_SEP': 'n', 'LEDS_BCM6328': 'n', 'LEDS_BCM6358': 'n', 'LEDS_LM3530': 'n', 'LEDS_LM3642': 'n', 'LEDS_PCA9532': 'n', 'LEDS_GPIO': 'n', 'LEDS_LP3944': 'n', 'LEDS_LP3952': 'n', 'LEDS_LP5521': 'n', 'LEDS_LP5523': 'n', 'LEDS_LP5562': 'n', 'LEDS_LP8501': 'n', 'LEDS_LP8860': 'n', 'LEDS_PCA955X': 'n', 'LEDS_PCA963X': 'n', 'LEDS_DAC124S085': 'n', 'LEDS_PWM': 'n', 'LEDS_REGULATOR': 'n', 'LEDS_BD2802': 'n', 'LEDS_LT3593': 'n', 'LEDS_TCA6507': 'n', 'LEDS_TLC591XX': 'n', 'LEDS_MAX77705_RGB': 'n', 'LEDS_LM355x': 'n', 'LEDS_KTD2692': 'n', 'LEDS_IS31FL319X': 'n', 'LEDS_IS31FL32XX': 'n', 'LEDS_BLINKM': 'n', 'LEDS_SYSCON': 'n', 'LEDS_USER': 'n', 'LEDS_S2MPB02_MULTI_TORCH_REAR2': 'n', 'LEDS_KTD2692_MULTI_TORCH_REAR3': 'n', 'LEDS_TRIGGERS': 'y', 'LEDS_TRIGGER_TIMER': 'n', 'LEDS_TRIGGER_ONESHOT': 'n', 'LEDS_TRIGGER_HEARTBEAT': 'n', 'LEDS_TRIGGER_BACKLIGHT': 'n', 'LEDS_TRIGGER_CPU': 'n', 'LEDS_TRIGGER_GPIO': 'n', 'LEDS_TRIGGER_DEFAULT_ON': 'n', 'LEDS_TRIGGER_TRANSIENT': 'n', 'LEDS_TRIGGER_CAMERA': 'n', 'LEDS_TRIGGER_PANIC': 'n', 'FB_SM750': 'n', 'FB_XGI': 'n', 'FB_TFT': 'n', 'PHY_EXYNOS_DISPLAYPORT': 'n'}
STOCK_GUARDS={'drivers/media/Kconfig': 'c6a05b05757cdf58df056f8cb9c57a2a88c622f20cca621d289b659724c69326', 'drivers/media/v4l2-core/Kconfig': '36f4b67f0e7edc6745cf0366b5465b4c4d7cc9758a0758047bc62d71fb7efb49', 'drivers/media/platform/Kconfig': '359e611b07e66f0d73126a362b1bdc5862ffa687a92996bb81f69aa219483b46', 'drivers/media/platform/Makefile': '0574ee707131d92ad83d5b130a1235150eda506576428444f940067bb5c0d54c', 'drivers/media/platform/exynos/fimc-is2/Kconfig': '5fc27fe1b951bd60ae1988008101c08b2993abda8452e4d2f6bb6a8a5cc2be96', 'drivers/media/platform/exynos/fimc-is2/vendor/mcd/fimc-is-sysfs.c': 'de133cb2c1e43f2951a550cc5d9f01761291e250d9100eaa19c2ed9a0dc7f924', 'drivers/media/platform/exynos/mfc/Kconfig': '5d80103e0ad44db70b061e90967ffa1de16173d4989c21f143e788bdebebcefb', 'drivers/media/platform/exynos/mfc/Makefile': '97af947861717642e70d98ff7fd5c1599399ae2f256fb65c8d061415d1128ba7', 'drivers/leds/Makefile': '886df59cc7faa23440a26c428f9c01a850d75c85199c2f3bac4261bd58eeb988', 'drivers/leds/leds-s2mpb02.c': 'baceeadc42e0e29f53a616237cc789460530857e8b8679175edf7a8acebc03ff', 'drivers/vision/npu/Kconfig': 'eef81e85ec724e32ab2edacc53412d80598b008de02b5459d56c6e51e9c645f1'}


def require(ok,message):
    if not ok:raise ValueError(message)


def guard_source(raw,expected):
    require(type(raw)is bytes and type(expected)is str and hashlib.sha256(raw).hexdigest()==expected,'exact shared-provider/removal boundary required')


def effective(values,critical):
    require(type(values)is type(critical)is dict and all(critical.get(k)==v for k,v in MANDATORY.items()),'complete retained critical profile required')
    require(all(values.get(k,'n')==v for k,v in COMMON.items()),'shared V4L2/videobuf2/display supplier changed')
    require(all(values.get(k,'n')==v for k,v in DISPLAY.items()),'baseline212display/backlight/otherLED configuration changed')
    require(all(values.get(k,'n')==v for k,v in REMOVED.items()),'camera/codec/flash removal closure incomplete')
    require(all(values.get(k,'n')==v for k,v in critical.items()),'required prepare/return setting changed')
    return dict(selected_config=dict(SETTINGS),retained_common=dict(COMMON),display_reference=dict(DISPLAY),retained_critical=dict(critical))


def fit(member_bytes):
    require(type(member_bytes)is int and member_bytes>0,'completed member extent required')
    used=member_bytes+(-member_bytes%4)+METADATA_BYTES
    return dict(fit=used<=SLOT_BYTES,aligned_required_bytes=used,slot_bytes=SLOT_BYTES,
                metadata_budget_bytes=METADATA_BYTES,excess_bytes=max(0,used-SLOT_BYTES))


def linked_symbols(symbols):
    rows=[line.split()for line in symbols.splitlines()]
    names={row[2]for row in rows if len(row)==3 and row[1]not in ('U','u')}
    removed=('fimc_is_probe','fimc_is_debug_event','camera_class','mfc_probe','s2mpb02_led_probe')
    retained=('v4l2_subdev_init','v4l2_device_register','v4l2_device_unregister','v4l2_device_register_subdev_nodes',
              'v4l2_device_unregister_subdev','v4l2_device_register_subdev','v4l2_match_dv_timings','vb2_dma_sg_memops',
              'panel_probe','dpp_probe','dsim_probe','displayport_probe','decon_probe','iva_ctl_probe',
              'n210_read','n210_write','n210_publish','n154_require_return_armed','n154_return_init','exynos_sysmmu_probe','dhd_smmu_fault_handler')
    require(all(name not in names for name in removed),'removed camera/codec/flash object remains linked')
    require(all(name in names for name in retained),'real shared-provider/display/critical symbol missing')
    return dict(absent=list(removed),retained=list(retained))
