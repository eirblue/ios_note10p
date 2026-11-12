"""Fixed media-free diagnostic profile and six MiB neutral slot policy."""
import hashlib

SLOT_BYTES=6291456
METADATA_BYTES=4096
SETTINGS={'MEDIA_SUPPORT':'n'}
MEDIA_OFF=('MEDIA_SUPPORT','MEDIA_CAMERA_SUPPORT','MEDIA_CONTROLLER','VIDEO_DEV','VIDEO_V4L2','VIDEO_EXYNOS_FIMC_IS2','VIDEO_EXYNOS_MFC')
MANDATORY={'NOTE10_V210_NATIVE_PREPARE':'y','NOTE10_V154_LINUX_DIAGNOSTIC':'y','NOTE10_BUILTIN_INIT_ROUTE':'y',
           'EXYNOS_REBOOT':'y','SEC_REBOOT':'y','EXYNOS_IVA':'y','EXYNOS_IOMMU':'y','EXYNOS_IOVMM':'y','ION_EXYNOS':'y',
           'BCM_DHD_WLAN':'y','BCMDHD_PCIE':'y','EXYNOS_PCIE_IOMMU':'y','BLK_DEV_INITRD':'y','INITRAMFS_FORCE':'y',
           'RD_GZIP':'y','SYSFS':'y','PROC_FS':'y','DEVTMPFS':'y','CRYPTO_SHA256':'y','CRYPTO_USER_API_HASH':'y','KEXEC':'n','KEXEC_FILE':'n'}
STOCK_GUARDS={'drivers/media/Kconfig':'c6a05b05757cdf58df056f8cb9c57a2a88c622f20cca621d289b659724c69326',
              'drivers/media/platform/Makefile':'0574ee707131d92ad83d5b130a1235150eda506576428444f940067bb5c0d54c',
              'drivers/vision/iva/Kconfig':'fe3bff61d5fa3a816865b4fac35f66749e99a4f2a4543a35dd2bf9c57d7aeb7f'}


def require(ok,message):
    if not ok:raise ValueError(message)


def guard_source(raw,expected):
    require(type(raw)is bytes and type(expected)is str and hashlib.sha256(raw).hexdigest()==expected,'exact selected stock config boundary required')


def effective(values,critical):
    require(type(values)is type(critical)is dict and all(critical.get(k)==v for k,v in MANDATORY.items()),'complete unchanged critical profile required')
    require(all(values.get(k,'n')=='n' for k in MEDIA_OFF),'media subsystem must remain disabled')
    require(all(values.get(k,'n')==v for k,v in critical.items()),'required prepare/return profile setting changed')
    return dict(selected_config=dict(SETTINGS),media_disabled=list(MEDIA_OFF),retained_critical=dict(critical))


def fit(member_bytes):
    require(type(member_bytes)is int and member_bytes>0,'completed member extent required')
    required=member_bytes+(-member_bytes%4)+METADATA_BYTES
    return dict(fit=required<=SLOT_BYTES,aligned_required_bytes=required,slot_bytes=SLOT_BYTES,
                metadata_budget_bytes=METADATA_BYTES,excess_bytes=max(0,required-SLOT_BYTES))


def linked_symbols(symbols):
    rows=[line.split() for line in symbols.splitlines()]
    names={row[2] for row in rows if len(row)==3 and row[1]in ('t','T')}
    absent=('fimc_is_probe','v4l2_device_register')
    retained=('n210_read','n210_write','n210_publish','n154_require_return_armed','n154_return_init','exynos_sysmmu_probe','iva_ctl_probe','dhd_smmu_fault_handler')
    require(all(name not in names for name in absent),'media driver remains linked')
    require(all(name in names for name in retained),'required prepare/return/IOMMU/wireless anchor missing')
    return dict(absent=list(absent),retained=list(retained))
