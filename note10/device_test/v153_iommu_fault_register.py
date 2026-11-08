"""Register at most one persistent fault notifier per existing SysMMU entry."""
from hashlib import sha256

IOMMU = 'drivers/iommu/exynos-iommu.c'
IOMMU_SHA256 = 'e365f1d2396b816fc6f9d4b56f0065de0c7af28448d171b0e68762c7a68a2487'
OLD_STRUCT = b'''struct sysmmu_list_data {
\tstruct device *sysmmu;
\tstruct list_head node;
};'''
NEW_STRUCT = b'''struct sysmmu_list_data {
\tstruct device *sysmmu;
\tstruct list_head node;
\tbool fault_notifier_registered;
};'''
OLD_LOOP = b'''\tlist_for_each_entry(list, &owner->sysmmu_list, node) {
\t\tinfo = kzalloc(sizeof(*info), GFP_ATOMIC);'''
NEW_LOOP = b'''\tlist_for_each_entry(list, &owner->sysmmu_list, node) {
\t\tif (list->fault_notifier_registered)
\t\t\tcontinue;
\t\tinfo = kzalloc(sizeof(*info), GFP_ATOMIC);'''
OLD_REGISTER = b'''\t\tatomic_notifier_chain_register(
\t\t\t\t&drvdata->fault_notifiers, &info->nb);'''
NEW_REGISTER = OLD_REGISTER + b'\n\t\tlist->fault_notifier_registered = true;'
EDITS = ((OLD_STRUCT, NEW_STRUCT), (OLD_LOOP, NEW_LOOP), (OLD_REGISTER, NEW_REGISTER))


def patch_native(iommu):
    if sha256(iommu).hexdigest() != IOMMU_SHA256:
        raise ValueError('actual152 exact composed native IOMMU input required')
    for old, new in EDITS:
        if iommu.count(old) != 1:
            raise ValueError('exact unique private struct/registrar anchor required')
        iommu = iommu.replace(old, new, 1)
    return {IOMMU: iommu}
