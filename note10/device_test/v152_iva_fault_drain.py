"""Drain the bounded IVA-private fault token before native IVA teardown."""
from hashlib import sha256

IOMMU = 'drivers/iommu/exynos-iommu.c'
LOCAL_HEADER = 'drivers/iommu/exynos-iommu.h'
IOVMM = 'drivers/iommu/exynos-iovmm.c'
PUBLIC_HEADER = 'include/linux/exynos_iovmm.h'
CTRL = 'drivers/vision/iva/iva_ctrl.c'
NATIVE_SHA256 = {
    IOMMU: '67d9bfb7597ec7434fc07a7101e69c385ac4cb9e61ebd727f0bcd40d01f1bb0b',
    LOCAL_HEADER: 'f5f2be8937e8990672296e55d33bdbcd12244d0ab6aa8b8eef96de6717fadc11',
    IOVMM: 'caee87228dd9ba8b5ae742abcaa7e622d17384a60d6887efb230bcb024d51765',
    PUBLIC_HEADER: '30d9c75bba4bb1a97d972df4944e69a2c589d380f4a642e1e8a719bbb7425ec8',
    CTRL: 'bd25f242f96501d06e80da563cf4a3ba6dec5a85dd7e886411eeef6637f87562',
}
OLD_NOTIFIER = b'''static int sysmmu_fault_notifier(struct notifier_block *nb,
\t\t\t\t     unsigned long fault_addr, void *data)
{
\tstruct owner_fault_info *info;
\tstruct exynos_iommu_owner *owner = NULL;

\tinfo = container_of(nb, struct owner_fault_info, nb);
\towner = info->master->archdata.iommu;

\tif (owner && owner->fault_handler)
\t\towner->fault_handler(owner->domain, owner->master,
\t\t\tfault_addr, *(int *)data, owner->token);

\treturn 0;
}'''
NEW_NOTIFIER = b'''static int sysmmu_fault_notifier(struct notifier_block *nb,
\t\t\t\t     unsigned long fault_addr, void *data)
{
\tstruct owner_fault_info *info;
\tstruct exynos_iommu_owner *owner = NULL;
\tiommu_fault_handler_t handler;
\tvoid *token;
\tunsigned long flags;

\tinfo = container_of(nb, struct owner_fault_info, nb);
\towner = info->master->archdata.iommu;

\tif (owner) {
\t\tspin_lock_irqsave(&owner->lock, flags);
\t\thandler = owner->fault_handler;
\t\ttoken = owner->token;
\t\tspin_unlock_irqrestore(&owner->lock, flags);
\t\tif (handler)
\t\t\thandler(owner->domain, owner->master,
\t\t\t\tfault_addr, *(int *)data, token);
\t}

\treturn 0;
}'''
CLEAR = b'''/* Process context; caller serializes same-master set/clear through unbind. */
void exynos_iommu_clear_fault_handler(struct device *master)
{
\tstruct exynos_iommu_owner *owner = master->archdata.iommu;
\tunsigned long flags;

\tif (!has_sysmmu(master))
\t\treturn;

\tspin_lock_irqsave(&owner->lock, flags);
\towner->fault_handler = NULL;
\towner->token = NULL;
\tspin_unlock_irqrestore(&owner->lock, flags);
\tsynchronize_rcu();
}'''
WRAPPER = b'''void iovmm_clear_fault_handler(struct device *dev)
{
\texynos_iommu_clear_fault_handler(dev);
}'''
LOCAL_DECL = b'void exynos_iommu_clear_fault_handler(struct device *master);\n'
PUBLIC_DECL = b'''/* Process context; serialize same-device set/clear and keep the master alive. */
void iovmm_clear_fault_handler(struct device *dev);
'''
DISABLED = b'#define iovmm_clear_fault_handler(dev) do { } while (0)\n'
EDITS = {
    IOMMU: (
        (b'#include <linux/pm_runtime.h>\n', b'#include <linux/pm_runtime.h>\n#include <linux/rcupdate.h>\n'),
        (OLD_NOTIFIER, NEW_NOTIFIER),
        (b'\nint sysmmu_set_prefetch_buffer_property(', b'\n' + CLEAR + b'\n\nint sysmmu_set_prefetch_buffer_property('),
    ),
    LOCAL_HEADER: (
        (b'int exynos_iommu_add_fault_handler(struct device *dev,\n\t\t\t\tiommu_fault_handler_t handler, void *token);\n',
         b'int exynos_iommu_add_fault_handler(struct device *dev,\n\t\t\t\tiommu_fault_handler_t handler, void *token);\n' + LOCAL_DECL),
    ),
    PUBLIC_HEADER: (
        (b'void iovmm_set_fault_handler(struct device *dev,\n\t\t\t     iommu_fault_handler_t handler, void *token);\n',
         b'void iovmm_set_fault_handler(struct device *dev,\n\t\t\t     iommu_fault_handler_t handler, void *token);\n' + PUBLIC_DECL),
        (b'#define iovmm_set_fault_handler(dev, handler, token) do { } while(0)\n',
         b'#define iovmm_set_fault_handler(dev, handler, token) do { } while(0)\n' + DISABLED),
    ),
    CTRL: (
        (b'err_iovmm:\n\tpm_runtime_disable(dev);',
         b'err_iovmm:\n\tiovmm_clear_fault_handler(dev);\n\tpm_runtime_disable(dev);'),
        (b'#ifdef CONFIG_EXYNOS_IOVMM\n\tiovmm_deactivate(dev);',
         b'#ifdef CONFIG_EXYNOS_IOVMM\n\tiovmm_clear_fault_handler(dev);\n\tiovmm_deactivate(dev);'),
    ),
}


def patch_native(native):
    if set(native) != set(NATIVE_SHA256) or any(sha256(native[name]).hexdigest() != pin
                                               for name, pin in NATIVE_SHA256.items()):
        raise ValueError('exact five pinned provider/header/actual151 ctrl inputs required')
    outputs = {}
    for name, raw in native.items():
        for old, new in EDITS.get(name, ()):
            if raw.count(old) != 1:
                raise ValueError('exact unique native anchor required: ' + name)
            raw = raw.replace(old, new, 1)
        outputs[name] = raw + b'\n' + WRAPPER + b'\n' if name == IOVMM else raw
    return outputs
