/* Fresh own-layout object; numeric oracle comes from the saved real header. */
#include "runtime_relocation.h"
const uint64_t n10_runtime_layout[] = {
 sizeof(struct n10_rt_boot_layout),
 offsetof(struct n10_rt_boot_layout,Revision), offsetof(struct n10_rt_boot_layout,Version),
 offsetof(struct n10_rt_boot_layout,virtBase), offsetof(struct n10_rt_boot_layout,physBase),
 offsetof(struct n10_rt_boot_layout,memSize), offsetof(struct n10_rt_boot_layout,topOfKernelData),
 offsetof(struct n10_rt_boot_layout,Video), offsetof(struct n10_rt_boot_layout,machineType),
 offsetof(struct n10_rt_boot_layout,deviceTreeP), offsetof(struct n10_rt_boot_layout,deviceTreeLength),
 offsetof(struct n10_rt_boot_layout,CommandLine), offsetof(struct n10_rt_boot_layout,bootFlags),
 offsetof(struct n10_rt_boot_layout,memSizeActual)
};
const struct n10_rt_boot_layout n10_runtime_fixture = {
 .Revision=2,.Version=2,.virtBase=UINT64_C(0xfffffff000000000),.physBase=UINT64_C(0x80000000),
 .memSize=UINT64_C(0x40000000),.topOfKernelData=UINT64_C(0x88004000),
 .Video={1,2,3,4,5,6},.machineType=7,
 .deviceTreeP=UINT64_C(0xfffffff006008000),.deviceTreeLength=0x1234,
 .CommandLine="debug=0x14e",.bootFlags=0,.memSizeActual=UINT64_C(0x40000000)
};
