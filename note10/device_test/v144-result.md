# v144 IVA buffer provider: host result

The import path checks the exact acquired DMA-buffer object against the selected ION exporter before native storage, attachment or private-data casts. Foreign references are released after the complete native ioctl body, including its locks, performance and logging tail. There is no second file-descriptor lookup and no native-object access after the final foreign callback.

The initial host compilation failed because test counters collided with standard-library symbols and the Windows host uses LLP64 pointer widths. The corrected R2 fixture passed 282 assertions with one compiler invocation and one fixture process. It reused the saved native transform; native transformation ran once overall, with three fail-closed transform checks. The failed compiler attempt is preserved. Previously passed tests were not rerun.

R2 changes only host counter names and explicit pointer-width bridges; production source signatures remain unchanged. The fixture covers five authentic native functions and both performance-tail variants. It does not establish actual AArch64 kernel integration, file/remove serialization, DMA or firmware termination. No Image, package or device action occurred; the physical IVA owner gate remains closed.
